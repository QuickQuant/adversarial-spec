# Structured Flows

> Every significant flow in structured notation. Optimized for LLM consumption.
> Generated: 2026-04-16 | Git: 9ca3ccd

## Notation

```
FLOW: name
TRIGGER: what initiates this flow
ENTRY: function(file:line)
STATUS: implemented | partial | disabled
STEPS:
  1. action -> next_action
  2. action [condition] -> branch_a | branch_b
DATA_IN:
  - param_name: type (description)
DATA_OUT:
  - return_value: type (description)
EXITS_TO: destination_flow(s)
```

All 7 fields are required for every flow. If a field doesn't apply, write `none`.

---

## Lifecycle Flows

### FLOW: cli_action_routing

```
TRIGGER: CLI invocation `adversarial-spec <action>`
ENTRY: main() (debate.py:1493)
STATUS: implemented

STEPS:
  1. create_parser() -> parse args
  2. [action in info commands] -> handle_info_command() -> return
  3. [action in utility commands] -> handle_utility_command() -> return
  4. [action == "execution-plan"] -> handle_execution_plan() -> return
  5. [action == "gauntlet"] -> handle_gauntlet() -> return
  6. apply_profile() [if --profile] -> parse_models() -> setup_bedrock() [if --bedrock]
  7. validate_models_before_run() -> load_or_resume_session()
  8. [action == "send-final"] -> handle_send_final() -> return
  9. [action == "export-tasks"] -> handle_export_tasks() -> return
  10. run_critique() -> return

DATA_IN:
  - args: argparse.Namespace (CLI arguments)
  - stdin: str (spec text, for critique/gauntlet actions)

DATA_OUT:
  - stdout: str (critique responses, reports, info listings)
  - exit_code: int (0=success, 1=runtime error, 2=config error)

EXITS_TO: run_critique, handle_gauntlet, handle_info_command, handle_utility_command
```

### FLOW: gauntlet_pipeline_init

```
TRIGGER: handle_gauntlet() or direct run_gauntlet() call
ENTRY: run_gauntlet() (gauntlet/orchestrator.py:196)
STATUS: implemented

STEPS:
  1. build GauntletConfig from arguments
  2. resolve attack_models (explicit > adversary_model > auto-select)
  3. resolve eval_models (multi-model > single > auto-select)
  4. _validate_model_name() for all models
  5. [unattended == True] -> monkey-patch builtins.input
  6. create .adversarial-spec-gauntlet/ directory
  7. resolve and filter adversaries
  8. compute config_hash for checkpoint matching
  9. [resume == True] -> load_partial_run() -> skip completed phases
  10. execute phases 1-7 sequentially -> gauntlet_phase_execution

DATA_IN:
  - spec: str (specification text)
  - config: GauntletConfig (timeout, reasoning, resume flags)
  - adversaries: list[str] (adversary keys)
  - models: list[str] (model identifiers)

DATA_OUT:
  - result: GauntletResult (concerns, evaluations, rebuttals, verdict, cost)

EXITS_TO: gauntlet_phase_execution, checkpoint_persistence
```

---

## Data Processing Flows

### FLOW: debate_critique_round

```
TRIGGER: run_critique() called from main()
ENTRY: run_critique() (debate.py:1206)
STATUS: implemented

STEPS:
  1. load/create session state (or None)
  2. [optional] create MCP task for tracking
  3. [technical spec without context] -> warn user
  4. call_models_parallel(models, spec, round, doc_type, focus, persona, context)
  5. aggregate responses -> check consensus ([AGREE] flags)
  6. [all agree] -> save checkpoint -> return
  7. [not agreed] -> extract_spec() from best response
  8. prompt user "Continue to next round?"
  9. [user says no] -> save checkpoint -> return
  10. [user says yes] -> increment round -> goto step 4

DATA_IN:
  - spec: str (specification text)
  - models: list[str] (model identifiers)
  - round_num: int (current debate round)
  - session: SessionState (optional, for resume)

DATA_OUT:
  - responses: list[ModelResponse] (per-model critiques)
  - checkpoint: file (round spec + critiques JSON)

EXITS_TO: model_parallel_dispatch, session_persistence
```

### FLOW: model_parallel_dispatch

```
TRIGGER: run_critique() or gauntlet phase functions
ENTRY: call_models_parallel() (models.py:901)
STATUS: implemented

STEPS:
  1. create ThreadPoolExecutor(max_workers=len(models))
  2. for each model: submit(call_single_model, model, spec, ...)
  3. route by model prefix:
     a. [codex/] -> call_codex_model() with retry
     b. [gemini-cli/] -> call_gemini_cli_model() with retry
     c. [claude-cli/] -> call_claude_cli_model() with retry
     d. [other] -> litellm.completion()
  4. for each completed future: collect ModelResponse
  5. cost_tracker.add() per response (thread-safe via Lock)

DATA_IN:
  - models: list[str] (model identifiers)
  - system_prompt: str
  - user_prompt: str (spec + instructions)
  - timeout: int (seconds)

DATA_OUT:
  - responses: list[ModelResponse] (model, response, tokens, cost, agreed)

EXITS_TO: cost_tracking
```

### FLOW: gauntlet_phase_execution

```
TRIGGER: run_gauntlet() after init
ENTRY: run_gauntlet() (gauntlet/orchestrator.py:331)
STATUS: implemented

STEPS:
  1. Phase 1: generate_attacks(spec, adversaries, models, config)
     -> save_checkpoint("concerns", concerns)
  2. Phase 2: generate_big_picture_synthesis(concerns, spec)
     -> save_checkpoint("synthesis", synthesis)
  3. Phase 3: filter_concerns_with_explanations(concerns, resolved_db)
     -> save_checkpoint("clustered-concerns", filtered)
     NOTE: Phase 3.5 clustering was removed (lost 48% of concerns). Pass-through now.
  4. Phase 4: evaluate_concerns[_multi_model](filtered, spec, eval_models, config)
     -> save_checkpoint("evaluations", evaluations)
  5. Phase 5: run_rebuttals(dismissed_evals, spec, adversaries)
  6. Phase 6: final_adjudication(evaluations, rebuttals)
     -> calculate_medals() -> save medal reports
  7. Phase 7: [optional] run_final_boss_review(result, spec, config)
     -> save_checkpoint("final-boss", final_result)
  8. auto-save dismissed concerns to resolved database
  9. update adversary statistics -> save_run_manifest() -> return GauntletResult

DATA_IN:
  - spec: str
  - adversaries: list[str]
  - models: list[str]
  - config: GauntletConfig

DATA_OUT:
  - result: GauntletResult (all phase outputs aggregated)

EXITS_TO: checkpoint_persistence, model_parallel_dispatch
```

### FLOW: attack_generation

```
TRIGGER: Phase 1 of gauntlet
ENTRY: generate_attacks() (gauntlet/phase_1_attacks.py:24)
STATUS: implemented

STEPS:
  1. group (adversary, model) pairs by provider
  2. create ThreadPoolExecutor(max_workers=min(32, len(pairs)))
  3. for each provider group: batch by rate limit
  4. for each batch: submit run_adversary_with_model() futures
  5. collect results via as_completed()
  6. parse responses -> extract Concern objects
  7. generate stable concern IDs via generate_concern_id(adversary, text)
  8. deduplicate by text normalization

DATA_IN:
  - spec: str
  - adversaries: list[str] (adversary keys)
  - models: list[str] (model identifiers)
  - config: GauntletConfig

DATA_OUT:
  - concerns: list[Concern] (adversary, text, severity, id)
  - timing: dict[str, float] (per-adversary timing)
  - raw_responses: dict[str, str] (raw model output)

EXITS_TO: checkpoint_persistence
```

### FLOW: concern_evaluation

```
TRIGGER: Phase 4 of gauntlet
ENTRY: evaluate_concerns() (gauntlet/phase_4_evaluation.py:23)
STATUS: implemented

STEPS:
  1. format concerns as markdown (### Concern N from adversary_X)
  2. extract evaluation protocols from Adversary definitions
  3. construct system prompt with valid/invalid dismissal rules
  4. call_model() to frontier model (Claude Opus or Codex)
  5. regex parse verdict: DISMISS|ACCEPT|ACKNOWLEDGE|DEFER
  6. extract reasoning text
  7. normalize verdict: "dismiss" -> "dismissed", etc.
  8. create Evaluation(concern, verdict, reasoning)

DATA_IN:
  - concerns: list[Concern]
  - spec: str
  - model: str (frontier model identifier)
  - config: GauntletConfig

DATA_OUT:
  - evaluations: list[Evaluation] (concern, verdict, reasoning)

EXITS_TO: checkpoint_persistence
```

### FLOW: pre_gauntlet_context_collection

```
TRIGGER: gauntlet/cli.py with --pre-gauntlet flag
ENTRY: PreGauntletOrchestrator.run() (pre_gauntlet/orchestrator.py:51)
STATUS: implemented

STEPS:
  1. [disabled by config or doc_type] -> return spec as-is
  2. extract_spec_affected_files() -> list of files mentioned in spec
  3. [require_git] -> GitPositionCollector.collect() -> git position + concerns
  4. [require_build/schema/trees] -> SystemStateCollector.collect() -> system state
  5. build_context(git_position, system_state, spec, max_chars=200k)
  6. [priming_context exists] -> prepend to context markdown
  7. return PreGauntletResult with context_markdown

DATA_IN:
  - spec_text: str
  - doc_type: str
  - repo_root: Path

DATA_OUT:
  - result: PreGauntletResult (status, context_markdown, concerns, timings)

EXITS_TO: none (result consumed by gauntlet pipeline)
```

---

## Background Flows

### FLOW: checkpoint_persistence

```
TRIGGER: After each gauntlet phase completes
ENTRY: save_checkpoint() (gauntlet/persistence.py:250)
STATUS: implemented

STEPS:
  1. serialize dataclasses to dicts (_serialize_dataclass)
  2. canonical JSON form (deterministic ordering)
  3. compute SHA256 integrity hash
  4. acquire FileLock for target path
  5. create NamedTemporaryFile in same directory
  6. json.dump(data, tmp) -> flush -> fsync
  7. os.replace(tmp, target) (atomic rename)
  8. release FileLock

DATA_IN:
  - phase: str (phase identifier)
  - data: dataclass (phase output)
  - spec_hash: str
  - config_hash: str

DATA_OUT:
  - checkpoint_file: file (.adversarial-spec-gauntlet/{phase}-{hash}.json)

EXITS_TO: none
```

### FLOW: session_persistence

```
TRIGGER: After each debate round in run_critique()
ENTRY: SessionState.save() (session.py:42)
STATUS: implemented

STEPS:
  1. set updated_at to current timestamp
  2. validate session_id (path traversal check via is_relative_to)
  3. serialize SessionState to JSON dict
  4. write to ~/.config/adversarial-spec/sessions/{session_id}.json

DATA_IN:
  - session: SessionState (session_id, spec, round, models, history)

DATA_OUT:
  - session_file: file (~/.config/adversarial-spec/sessions/{id}.json)

EXITS_TO: none
```

### FLOW: cost_tracking

```
TRIGGER: Every model call completion
ENTRY: cost_tracker.add() (models.py:165)
STATUS: implemented

STEPS:
  1. lookup MODEL_COSTS by model name
  2. calculate: (input_tokens / 1M) * input_rate + (output_tokens / 1M) * output_rate
  3. acquire threading.Lock
  4. add to totals (total_input_tokens, total_output_tokens, total_cost)
  5. add to by_model[model] dict
  6. release Lock
  7. return cost

DATA_IN:
  - model: str
  - input_tokens: int
  - output_tokens: int

DATA_OUT:
  - cost: float (cost for this call)

EXITS_TO: none
```

---

## Error Recovery Flows

### FLOW: checkpoint_resume

```
TRIGGER: run_gauntlet() with resume=True
ENTRY: load_partial_run() (gauntlet/persistence.py:675)
STATUS: implemented

STEPS:
  1. compute spec_hash and config_hash
  2. for each known phase (1, 2, 3.5, 4, 7):
     a. construct checkpoint filename
     b. _load_json_safe(path) with FileLock
     c. validate checkpoint version == CHECKPOINT_SCHEMA_VERSION
     d. validate data_hash matches stored hash
     e. [valid] -> add to partial[phase_name]
     f. [invalid/missing] -> skip
  3. return partial dict (empty if no valid checkpoints)

DATA_IN:
  - spec_hash: str
  - config_hash: str
  - gauntlet_dir: Path

DATA_OUT:
  - partial: dict[str, dict] (phase_name -> {data, timing})

EXITS_TO: gauntlet_pipeline_init (informs which phases to skip)
```

### FLOW: model_call_retry

```
TRIGGER: call_single_model() encounters exception
ENTRY: call_single_model() (models.py:678)
STATUS: implemented

STEPS:
  1. for attempt in range(MAX_RETRIES=3):
     a. call provider function
     b. [success] -> return ModelResponse
     c. [exception] -> log error
     d. sleep(RETRY_BASE_DELAY * 2^attempt) [1s, 2s, 4s]
  2. [all retries exhausted] -> return error ModelResponse

DATA_IN:
  - model: str
  - system_prompt: str
  - user_prompt: str

DATA_OUT:
  - response: ModelResponse (with error field if all retries failed)

EXITS_TO: model_parallel_dispatch (collected by executor)
```

### FLOW: unattended_mode_guard

```
TRIGGER: --unattended CLI flag
ENTRY: run_gauntlet() (gauntlet/orchestrator.py:277)
STATUS: implemented

STEPS:
  1. save original builtins.input
  2. replace builtins.input with lambda raising RuntimeError
  3. [Phase 7 calls input()] -> caught as (EOFError, RuntimeError) -> skip Final Boss
  4. finally: restore builtins.input = original_input

DATA_IN:
  - config.unattended: bool

DATA_OUT:
  - none (side effect: input() blocked during pipeline)

EXITS_TO: none
```
