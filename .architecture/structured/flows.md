# Structured Flows

> Every significant flow in structured notation. Optimized for LLM consumption.
> Generated: 2026-03-21 | Git: 12c5d3f

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

### FLOW: debate_startup

```
TRIGGER: User runs `debate.py critique` with spec input
ENTRY: main() (scripts/debate.py:1493)
STATUS: implemented

STEPS:
  1. create_parser() -> parse CLI arguments
  2. [action == info_command] -> handle_info_command() | continue
  3. [action == utility_command] -> handle_utility_command() | continue
  4. [action == execution-plan] -> handle_execution_plan() | continue
  5. [action == gauntlet] -> handle_gauntlet() | continue
  6. apply_profile(args) -> merge profile settings into args
  7. parse_models(args) -> resolve model list
  8. [bedrock enabled] -> setup_bedrock() | continue
  9. validate_models_before_run() -> check API keys
  10. load_or_resume_session() -> get/create session state
  11. run_critique() -> enter debate loop

DATA_IN:
  - spec: str (markdown spec via stdin or --spec-file)
  - models: list[str] (from --models or profile)
  - doc_type: str (spec|prd|tech|debug)
  - focus: Optional[str] (focus area name)
  - persona: Optional[str] (persona name)

DATA_OUT:
  - none (outputs to stdout, session file, optional telegram)

EXITS_TO: debate_round_loop
```

### FLOW: session_resume

```
TRIGGER: User runs debate.py with --resume <session_id>
ENTRY: load_or_resume_session() (scripts/debate.py)
STATUS: implemented

STEPS:
  1. SessionState.load(session_id) -> read JSON from sessions dir
  2. Validate path is within SESSIONS_DIR (security check)
  3. Restore spec, round number, models, focus, persona
  4. [session has history] -> display last round summary | skip
  5. Return restored session state

DATA_IN:
  - session_id: str (session identifier)

DATA_OUT:
  - session: SessionState (restored state with spec, round, history)

EXITS_TO: debate_round_loop
```

---

## Data Processing Flows

### FLOW: debate_round_loop

```
TRIGGER: Called from debate_startup after session is loaded
ENTRY: run_critique() (scripts/debate.py:1206)
STATUS: implemented

STEPS:
  1. log_input_stats() -> calculate line count and SHA256 hash
  2. Build system prompt via get_system_prompt(doc_type, persona, focus)
  3. Build user message via REVIEW_PROMPT_TEMPLATE with spec + context
  4. call_models_parallel(models, system_prompt, user_message) -> list[ModelResponse]
  5. Filter successful responses (no errors)
  6. Extract agreement: all_agreed = all(r.agreed for r in successful)
  7. [any response has revised spec] -> update session.spec | keep current
  8. SessionState.save() -> persist round results
  9. save_checkpoint(round_num, spec) -> write .adversarial-spec-checkpoints/
  10. save_critique_responses(results, round_num) -> write critiques JSON
  11. [telegram enabled] -> send_telegram_notification() | skip
  12. output_results() -> JSON or formatted text to stdout

DATA_IN:
  - session: SessionState (current spec, round number, models)
  - args: argparse.Namespace (CLI options)

DATA_OUT:
  - output: dict (JSON with responses, agreement status, cost)
  - side_effects: session file updated, checkpoint written, critiques JSON saved

EXITS_TO: none (terminal - one round per invocation, user decides next round)
```

### FLOW: model_call

```
TRIGGER: Called from call_models_parallel() for each model
ENTRY: call_single_model() (scripts/models.py:619)
STATUS: implemented

STEPS:
  1. [model starts with "codex/"] -> call_codex_model() | continue
  2. [model starts with "gemini-cli/"] -> call_gemini_cli_model() | continue
  3. [model starts with "claude-cli/"] -> call_claude_cli_model() | continue
  4. litellm.completion(model, messages) -> raw response
  5. Extract response text from completion
  6. Detect agreement: search for "[AGREE]" marker
  7. [has [SPEC]...[/SPEC] tags] -> extract revised spec | spec=None
  8. cost_tracker.add(model, input_tokens, output_tokens)
  9. Return ModelResponse

DATA_IN:
  - model: str (model identifier)
  - system_prompt: str (instructions)
  - user_message: str (spec + prompt)

DATA_OUT:
  - response: ModelResponse (model, response, agreed, spec, tokens, cost)

EXITS_TO: debate_round_loop (collected by ThreadPoolExecutor)
```

### FLOW: gauntlet_pipeline

```
TRIGGER: User runs `debate.py gauntlet` or `python -m gauntlet`
ENTRY: run_gauntlet() (scripts/gauntlet/orchestrator.py:116)
STATUS: implemented

STEPS:
  1. Build GauntletConfig from CLI params (timeout, reasoning, resume, unattended)
  2. Resolve models: attack_models (auto-select free CLI), eval_models (frontier)
  3. _validate_model_name() for each model (blocklist regex: shell metachar, flags, control chars)
  4. get_spec_hash(spec), get_config_hash(config) for checkpoint matching
  5. Phase 1: generate_attacks() (phase_1_attacks.py)
     - ThreadPoolExecutor per adversary, config.timeout per call
     - Persist concerns + raw responses to .adversarial-spec-gauntlet/
     - [config.resume and valid checkpoint exists] -> load from disk | generate
     - Emit PhaseMetrics to run manifest
  6. Phase 2: generate_big_picture_synthesis() (phase_2_synthesis.py)
     - LLM synthesizes patterns: real_issues, hidden_connections, meta_concern, high_signal
     - Uses config.eval_codex_reasoning for Codex calls
  7. Phase 3: filter_concerns_with_explanations() (phase_3_filtering.py)
     - Filter against resolved_concerns.json history
     - Returns filtered, dropped, noted lists
  8. Phase 3.5: cluster_concerns_with_provenance() (phase_3_filtering.py)
     - Semantic clustering via LLM, uses config.timeout
     - GauntletClusteringError on failure (no silent fallback - QUOTA BURN FIX 2)
     - save_partial_clustering() for checkpoint
     - [config.auto_checkpoint] -> checkpoint after clustering
  9. Phase 4: evaluate_concerns_multi_model() (phase_4_evaluation.py)
     - Batched (15 per batch), wave-based concurrency across eval models
     - Verdicts: accepted/dismissed/acknowledged/deferred
     - Uses config.eval_codex_reasoning, config.timeout
     - Persist evaluations checkpoint
  10. Phase 5: run_rebuttals() (phase_5_rebuttals.py)
      - Adversary rebuts dismissed concerns
      - Uses config.attack_codex_reasoning, config.timeout
      - Returns sustained: bool per rebuttal
  11. Phase 6: final_adjudication() (phase_6_adjudication.py)
      - Reviews sustained rebuttals
      - Uses config.eval_codex_reasoning, config.timeout
  12. Phase 7: [run_final_boss or interactive] -> run_final_boss_review() (phase_7_final_boss.py)
      - Final Boss (Opus 4.6) reviews holistically
      - Returns FinalBossVerdict: PASS/REFINE/RECONSIDER
  13. save_gauntlet_run(), update_adversary_stats(), calculate_medals()
  14. format_gauntlet_report() -> formatted output

DATA_IN:
  - spec: str (specification markdown)
  - adversaries: list[str] (adversary names, or "all")
  - attack_models: list[str], eval_models: list[str]
  - timeout: int, attack_codex_reasoning: str, eval_codex_reasoning: str
  - resume: bool, unattended: bool

DATA_OUT:
  - report: GauntletResult (concerns, evaluations, rebuttals, medals, big_picture, final_boss)
  - side_effects: run files in ~/.adversarial-spec/runs/, stats updated, manifest with PhaseMetrics

EXITS_TO: terminal (report output)
```

### FLOW: gauntlet_checkpoint_resume

```
TRIGGER: --resume flag (debate.py --gauntlet-resume or gauntlet/cli.py --resume)
ENTRY: load_partial_run() (scripts/gauntlet/persistence.py)
STATUS: implemented

STEPS:
  1. Compute spec_hash + config_hash from current inputs
  2. Look for .adversarial-spec-gauntlet/concerns-{hash}.json
  3. [found and schema_version matches] -> load concerns, skip Phase 1
  4. Look for clustered-concerns-{hash}.json
  5. [found] -> load clusters, skip Phases 1-3.5
  6. Look for evaluations-{hash}.json
  7. [found] -> load evaluations, skip Phases 1-4
  8. Return latest valid checkpoint data

DATA_IN:
  - spec_hash: str (SHA256 of spec)
  - config_hash: str (hash of GauntletConfig fields)

DATA_OUT:
  - partial_data: dict (loaded checkpoint data for resume)

EXITS_TO: gauntlet_pipeline (resumes from appropriate phase)
```

### FLOW: cost_tracking

```
TRIGGER: Every model call completion
ENTRY: CostTracker.add() (scripts/models.py:204)
STATUS: implemented

STEPS:
  1. Acquire threading.Lock
  2. Look up model in MODEL_COSTS dict (providers.py)
  3. Calculate: cost = (input_tokens/1M * input_rate) + (output_tokens/1M * output_rate)
  4. [CLI model (codex/, gemini-cli/, claude-cli/)] -> cost = 0 | standard rate
  5. Accumulate in global totals and per-model breakdown (by_model dict)
  6. Release lock
  7. [output requested] -> CostTracker.summary() formats human-readable string

DATA_IN:
  - model: str (model identifier)
  - input_tokens: int
  - output_tokens: int

DATA_OUT:
  - cost: float (accumulated in singleton, thread-safe)

EXITS_TO: included in debate output, gauntlet report, PhaseMetrics telemetry
```

### FLOW: pre_gauntlet_context

```
TRIGGER: Called before gauntlet run when pre-gauntlet is enabled
ENTRY: PreGauntletOrchestrator.run() (scripts/pre_gauntlet/orchestrator.py:51)
STATUS: implemented

STEPS:
  1. Check if pre-gauntlet enabled for doc type (config.get_doc_type_rule)
  2. Extract spec-affected files (regex analysis of spec)
  3. [require_git] -> GitPositionCollector.collect() | skip
     - Current branch, commits, staleness check
  4. [require_build] -> SystemStateCollector.collect() | skip
     - Run build command with timeout, extract schemas, walk dirs
  5. build_context() -> assemble markdown document
  6. [alignment_mode] -> run_alignment_mode() (LLM confirms context matches spec) | skip

DATA_IN:
  - spec_text: str (specification)
  - doc_type: DocType
  - config: CompatibilityConfig

DATA_OUT:
  - result: PreGauntletResult (status, context_markdown, concerns, timings)

EXITS_TO: gauntlet_pipeline (context passed as additional input)
```

---

## Background Flows

### FLOW: telegram_notification

```
TRIGGER: Round completion when --telegram flag is set
ENTRY: send_telegram_notification() (scripts/debate.py:185)
STATUS: implemented

STEPS:
  1. Format round results into message text
  2. telegram_bot.send_long_message() -> split at 4096 char boundaries
  3. For each chunk: api_call("sendMessage", {chat_id, text}) -> HTTP POST
  4. [poll_timeout > 0] -> poll_for_reply() with getUpdates | skip
  5. [reply received] -> return user feedback text | return None

DATA_IN:
  - results: list[ModelResponse]
  - round_num: int
  - poll_timeout: int (seconds)

DATA_OUT:
  - feedback: Optional[str] (user's Telegram reply)

EXITS_TO: debate_round_loop (feedback available for next round)
```

---

## Error Recovery Flows

### FLOW: model_call_retry

```
TRIGGER: Model call failure (timeout, API error, subprocess error)
ENTRY: call_single_model() retry loop (scripts/models.py:619)
STATUS: implemented

STEPS:
  1. Attempt model call
  2. [success] -> return ModelResponse | continue
  3. [attempt < MAX_RETRIES (3)] -> sleep(RETRY_BASE_DELAY * 2^attempt) -> retry | fail
  4. [all retries exhausted] -> return ModelResponse with error field set

DATA_IN:
  - model: str
  - system_prompt: str
  - user_message: str

DATA_OUT:
  - response: ModelResponse (may have error field populated)

EXITS_TO: call_models_parallel (error responses filtered by debate loop)
```

### FLOW: gauntlet_clustering_failure

```
TRIGGER: Phase 3.5 clustering LLM returns unparseable result
ENTRY: cluster_concerns_with_provenance() (scripts/gauntlet/phase_3_filtering.py)
STATUS: implemented

STEPS:
  1. Attempt clustering via LLM
  2. [parse failure] -> retry once with different prompt formatting
  3. [second failure] -> raise GauntletClusteringError (QUOTA BURN FIX 2)
  4. Pipeline halts with exit code 3

DATA_IN:
  - concerns: list[Concern]
  - config: GauntletConfig

DATA_OUT:
  - error: GauntletClusteringError (no silent fallback to singleton clusters)

EXITS_TO: terminal (sys.exit(3))
```

### FLOW: session_state_persistence

```
TRIGGER: Round completion, session save, or checkpoint
ENTRY: SessionState.save() (scripts/session.py:32)
STATUS: implemented

STEPS:
  1. Serialize session state to JSON
  2. Validate path is within SESSIONS_DIR (prevent directory traversal via is_relative_to)
  3. Write JSON to sessions/{session_id}.json
  4. [checkpoint] -> write spec to .adversarial-spec-checkpoints/round-{N}.md
  5. [critique responses] -> write JSON to checkpoints/round-{N}-critiques.json

DATA_IN:
  - session: SessionState

DATA_OUT:
  - none (file system side effects)

EXITS_TO: none
```

### FLOW: provider_validation

```
TRIGGER: Before model calls in debate startup
ENTRY: validate_model_credentials() (scripts/providers.py)
STATUS: implemented

STEPS:
  1. For each model: determine provider from prefix (gpt-, claude-, gemini/, etc.)
  2. Check required env var (OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, etc.)
  3. [CLI tool model] -> check shutil.which() for binary availability | check env var
  4. [bedrock mode] -> resolve friendly name to Bedrock model ID, check AWS config
  5. Return (valid_models, invalid_models)
  6. [any invalid] -> print error, sys.exit(2) | continue

DATA_IN:
  - models: list[str] (model identifiers)

DATA_OUT:
  - valid_models: list[str]
  - invalid_models: list[str]

EXITS_TO: debate_round_loop (if all valid) or sys.exit(2)
```
