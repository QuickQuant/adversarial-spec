# Structured Flows

> Every significant flow in structured notation. Optimized for LLM consumption.
> Generated: 2026-02-06T20:35:00Z | Git: e94ebfe

## Notation

```
FLOW: name
TRIGGER: what initiates this flow
ENTRY: function(file:line)
STEPS:
  1. action -> next_action
  2. action [condition] -> branch_a | branch_b
DATA_IN:
  - param_name: type (description)
DATA_OUT:
  - return_value: type (description)
EXITS_TO: destination_flow(s)
```

All 6 fields are required for every flow. If a field doesn't apply, write `none`.

---

## Lifecycle Flows

### FLOW: debate_startup

```
TRIGGER: User runs `debate.py critique` with spec input
ENTRY: main() (scripts/debate.py:1933)

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
ENTRY: load_or_resume_session() (scripts/debate.py:1630)

STEPS:
  1. SessionState.load(session_id) -> read JSON from sessions dir
  2. Validate session file exists and is not corrupted
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
ENTRY: run_critique() (scripts/debate.py:1689)

STEPS:
  1. [task tracking enabled] -> _create_round_task() | skip
  2. Build system prompt via get_system_prompt(doc_type, persona, focus)
  3. Build user message via REVIEW_PROMPT_TEMPLATE with spec + context
  4. call_models_parallel(models, system_prompt, user_message) -> list[ModelResponse]
  5. Filter successful responses (no errors)
  6. Extract agreement: all_agreed = all(r.agreed for r in successful)
  7. [any response has revised spec] -> update session.spec | keep current
  8. SessionState.save() -> persist round results
  9. save_checkpoint(round_num, spec) -> write .adversarial-spec-checkpoints/
  10. [telegram enabled] -> send_telegram_notification() | skip
  11. [all_agreed] -> output "All models agree!" | prepare next round
  12. [task tracking] -> _complete_round_task() | skip
  13. output_results() -> JSON or formatted text to stdout

DATA_IN:
  - session: SessionState (current spec, round number, models)
  - args: argparse.Namespace (CLI options)

DATA_OUT:
  - output: dict (JSON with responses, agreement status, cost)
  - side_effects: session file updated, checkpoint written

EXITS_TO: none (terminal) or loops back for next round
```

### FLOW: model_call

```
TRIGGER: Called from call_models_parallel() for each model
ENTRY: call_single_model() (scripts/models.py:470)

STEPS:
  1. [model starts with "codex/"] -> call_codex_model() | continue
  2. [model starts with "gemini-cli/"] -> call_gemini_cli_model() | continue
  3. litellm.completion(model, messages) -> raw response
  4. Extract response text from completion
  5. Detect agreement: search for "[AGREE]" marker
  6. [has [SPEC]...[/SPEC] tags] -> extract revised spec | spec=None
  7. cost_tracker.add(model, input_tokens, output_tokens)
  8. Return ModelResponse

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
TRIGGER: User runs `debate.py gauntlet` or `gauntlet.py`
ENTRY: run_gauntlet() (scripts/gauntlet.py)

STEPS:
  1. Parse adversary list and model selection
  2. Phase 1: Generate concerns (parallel per adversary)
     - For each adversary in ADVERSARIES:
       - Build adversary persona prompt
       - Call LLM -> extract Concern objects
  3. Phase 2: Filter duplicates and low-signal concerns
  4. Phase 3: Evaluate each concern via frontier model
     - LLM returns verdict: accepted|acknowledged|dismissed|deferred
  5. Phase 4: [rebuttal enabled] -> dismissed adversaries argue back | skip
     - Returns Rebuttal with sustained: bool
  6. Phase 5: Big Picture Synthesis
     - LLM analyzes all concerns holistically
     - Returns real_issues, hidden_connections, whats_missing, meta_concern
  7. Phase 6: Medal Awards
     - Rank adversaries by catch uniqueness + severity
     - Assign gold/silver/bronze medals
  8. format_gauntlet_report() -> formatted output
  9. Write JSON report to ~/.adversarial-spec-gauntlet/

DATA_IN:
  - spec: str (finalized specification)
  - adversaries: list[str] (adversary names to run)
  - models: list[str] (LLM models for concern generation)

DATA_OUT:
  - report: GauntletResult (concerns, evaluations, rebuttals, medals, big_picture)

EXITS_TO: execution_planning (optional) or terminal
```

### FLOW: execution_planning

```
TRIGGER: User runs `debate.py execution-plan`
ENTRY: handle_execution_plan() (scripts/debate.py:724)

STEPS:
  1. Read spec from file or stdin
  2. [gauntlet JSON exists] -> load concerns | skip
  3. SpecIntake.parse(spec) -> Document with data models, endpoints, stories
  4. ScopeAssessor.assess(doc) -> ScopeAssessment (small/medium/large)
  5. TaskPlanner.generate_from_tech_spec(doc, gauntlet_report) -> TaskPlan
  6. [0 tasks generated] -> TaskPlanner.auto_generate() via LLM | continue
  7. TestStrategyManager.assign_strategies(plan) -> test-first/test-after per task
  8. OverDecompositionGuard.check(plan, doc) -> warn if too many tasks
  9. ParallelizationAdvisor.analyze(plan) -> workstreams, merge sequence
  10. Output as JSON or Markdown

DATA_IN:
  - spec: str (finalized spec)
  - gauntlet_concerns: Optional[list[Concern]] (from gauntlet JSON)

DATA_OUT:
  - plan: TaskPlan (tasks with dependencies, test strategies, parallelization)

EXITS_TO: implementation phase or terminal
```

### FLOW: cost_tracking

```
TRIGGER: Every model call completion
ENTRY: CostTracker.add() (scripts/models.py:101)

STEPS:
  1. Look up model in MODEL_COSTS dict (providers.py)
  2. Calculate: cost = (input_tokens/1M * input_rate) + (output_tokens/1M * output_rate)
  3. Accumulate in global totals and per-model breakdown
  4. [output requested] -> CostTracker.summary() formats human-readable string

DATA_IN:
  - model: str (model identifier)
  - input_tokens: int
  - output_tokens: int

DATA_OUT:
  - cost: float (accumulated in singleton)

EXITS_TO: included in debate output, telegram notifications
```

---

## Background Flows

### FLOW: telegram_notification

```
TRIGGER: Round completion when --telegram flag is set
ENTRY: send_telegram_notification() (scripts/debate.py:182)

STEPS:
  1. Format round results into message text
  2. telegram_bot.send_long_message() -> split at 4096 char boundaries
  3. For each chunk: api_call("sendMessage", {chat_id, text}) -> HTTP POST
  4. [poll_timeout > 0] -> poll_for_reply() with getUpdates | skip
  5. [reply received] -> return user feedback text | return None

DATA_IN:
  - models: list[str]
  - round_num: int
  - results: list[ModelResponse]
  - poll_timeout: int (seconds)

DATA_OUT:
  - feedback: Optional[str] (user's Telegram reply)

EXITS_TO: debate_round_loop (feedback incorporated into next round)
```

---

## Error Recovery Flows

### FLOW: model_call_retry

```
TRIGGER: Model call failure (timeout, API error)
ENTRY: call_single_model() retry loop (scripts/models.py:522)

STEPS:
  1. Attempt model call
  2. [success] -> return ModelResponse | continue
  3. [attempt < MAX_RETRIES (3)] -> wait 2^attempt seconds -> retry | fail
  4. [all retries exhausted] -> return ModelResponse with error field set

DATA_IN:
  - model: str
  - messages: list[dict]

DATA_OUT:
  - response: ModelResponse (may have error field populated)

EXITS_TO: call_models_parallel (error responses filtered by debate loop)
```

### FLOW: pre_gauntlet_error_handling

```
TRIGGER: Infrastructure failure during context collection
ENTRY: PreGauntletOrchestrator.run() (scripts/pre_gauntlet/orchestrator.py:51)

STEPS:
  1. [git collection fails with GitCliError] -> return INFRA_ERROR result | continue
  2. [system state collection fails] -> return INFRA_ERROR result | continue
  3. [spec file extraction fails] -> log warning, continue with empty list
  4. [alignment mode fails] -> log warning, proceed without alignment

DATA_IN:
  - spec_text: str
  - doc_type: DocType

DATA_OUT:
  - result: PreGauntletResult (status may be INFRA_ERROR)

EXITS_TO: debate_round_loop (caller decides whether to proceed)
```

### FLOW: session_state_persistence

```
TRIGGER: Round completion, session save, or checkpoint
ENTRY: SessionState.save() (scripts/session.py)

STEPS:
  1. Serialize session state to JSON
  2. Validate path is within SESSIONS_DIR (prevent directory traversal)
  3. Write JSON to sessions/{session_id}.json
  4. [checkpoint] -> write spec to .adversarial-spec-checkpoints/round-{N}.md

DATA_IN:
  - session: SessionState

DATA_OUT:
  - none (file system side effects)

EXITS_TO: none
```
