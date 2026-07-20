# Structured Flows

> Every significant flow uses the full eight-field notation. Generated at `ef18c66`; if cited source files change, trust source over this document.

## Lifecycle Flows

### FLOW: debate-round-lifecycle

```text
TRIGGER: installed `adversarial-spec` CLI invocation
ENTRY: debate.main() (skills/adversarial-spec/scripts/debate.py:1623)
STATUS: implemented
STEPS:
  1. create_parser() -> apply_profile() -> parse_models()
  2. validate_models_before_run() -> preflight_models()
  3. load_or_resume_session() -> run_critique()
  4. run_critique() -> output_results() -> checkpoint/next round
DATA_IN:
  - argv/stdin/spec file: CLI options and specification text
  - profile/config: model/provider selection
DATA_OUT:
  - critique/spec/task output: text plus ModelResponse metadata
  - session checkpoint: JSON state when resumability is enabled
EXITS_TO: gauntlet-pipeline, user-review, session-resume, cli-error
BOUNDARIES: model-cli-stdio, model-litellm, session-files, telegram-http
```

### FLOW: gauntlet-pipeline

```text
TRIGGER: `--gauntlet` through debate CLI or `python -m gauntlet`
ENTRY: run_gauntlet() (skills/adversarial-spec/scripts/gauntlet/orchestrator.py:205)
STATUS: implemented
STEPS:
  1. resolve config/prompts/adversaries -> attack generation
  2. phase_1_attacks -> phase_2_synthesis -> phase_3_filtering
  3. clustering -> tiered evaluation -> rebuttals
  4. adjudication -> final boss -> GauntletResult
  5. save checkpoint/run manifest/stats/medals -> render report
DATA_IN:
  - spec: text to attack
  - GauntletConfig: models, adversaries, thresholds, resume/options
DATA_OUT:
  - GauntletResult: concerns, evaluations, rebuttals, verdict, metrics
  - run artifacts: JSON/Markdown checkpoints and reports
EXITS_TO: debate-output, gauntlet-resume, gauntlet-error
BOUNDARIES: model-cli-stdio, model-litellm, gauntlet-file-state
```

### FLOW: pre-gauntlet-compatibility

```text
TRIGGER: compatibility check requested before gauntlet
ENTRY: run_pre_gauntlet() (skills/adversarial-spec/scripts/pre_gauntlet/orchestrator.py:207)
STATUS: implemented
STEPS:
  1. load_config_from_pyproject() -> collect git/system context
  2. discover services -> build compatibility context
  3. execute configured build/schema/validation commands
  4. aggregate findings -> save_report() -> select exit status
DATA_IN:
  - spec: proposed specification
  - repo_root/CompatibilityConfig: repository and configured checks
DATA_OUT:
  - PreGauntletResult: status, checks, findings, alignment data
EXITS_TO: gauntlet-pipeline, alignment-review, pre-gauntlet-error
BOUNDARIES: pre-gauntlet-subprocess, pre-gauntlet-report
```

## Data Processing Flows

### FLOW: tmr-compile-and-validate

```text
TRIGGER: candidate TMR records are compiled
ENTRY: compile_tmr_records() (skills/adversarial-spec/scripts/tmr_compile_step.py:64)
STATUS: implemented
STEPS:
  1. coerce candidate -> resolve accessors/identity
  2. mint missing ULID -> diff by tmr_uid
  3. validate strict TestMaturityRecord -> write confirmed registry
  4. render prose view from confirmed records
DATA_IN:
  - candidates: prose-derived or structured candidate mappings
  - existing_registry: optional prior TMR records
DATA_OUT:
  - confirmed_records: schema-valid TMR JSON
  - semantic_diff_events: created/updated/unchanged record changes
  - prose_view: derived Markdown
EXITS_TO: phase8-promotion, provenance-transition, compile-error
BOUNDARIES: tmr-registry-prose-view
```

### FLOW: validation-ledger-lifecycle

```text
TRIGGER: validation-emission subcommand invocation
ENTRY: validation_emission.main() (skills/adversarial-spec/scripts/validation_emission.py:3423)
STATUS: implemented
STEPS:
  1. parse subcommand -> resolve spec-root paths and enforce bounds
  2. normalize/lint rows -> compute canonical hashes
  3. mutate ledger under FileLock -> assemble/send/parse evidence batch
  4. record system-validation evidence or self-check -> emit Envelope
DATA_IN:
  - argv: subcommand and bounded paths/payloads
  - ledger/reply/artifact: JSON/Markdown evidence inputs
DATA_OUT:
  - Envelope: status/code/issues/data on stdout
  - ledger/evidence: atomic file updates when command mutates state
EXITS_TO: phase8-promotion, telegram-reply, validation-error
BOUNDARIES: validation-cli-stdout, validation-ledger-files, telegram-http
```

### FLOW: provenance-transition

```text
TRIGGER: a TMR/node transition or disposition must be recorded
ENTRY: ProvenanceJournalWriter (skills/adversarial-spec/scripts/provenance_journal.py:112)
STATUS: implemented
STEPS:
  1. validate subject/event -> check expected coordinates
  2. acquire ordered locks -> append journal transition
  3. atomically update registry/index -> return AppendReceipt
  4. restore prior bytes on failure -> raise typed provenance error
DATA_IN:
  - transition: typed JournalTransition
  - registry/journal/index: current file-backed state
DATA_OUT:
  - receipt: append identity and resulting state
  - registry/journal/index: updated lineage artifacts
EXITS_TO: phase8-promotion, provenance-conflict
BOUNDARIES: provenance-files
```

### FLOW: plan-dependency-analysis

```text
TRIGGER: plan dependency report requested
ENTRY: analyze_plan() (skills/adversarial-spec/scripts/dependency_semantics.py:82)
STATUS: implemented
STEPS:
  1. parse plan tasks/edges -> normalize edge kinds and waves
  2. topological profile -> detect semantic/ordering issues
  3. serialize report -> stdout
DATA_IN:
  - plan: execution-plan JSON
  - semantics: optional semantic-document JSON
DATA_OUT:
  - report: schema-versioned dependency analysis JSON
EXITS_TO: plan-review, plan-error
BOUNDARIES: plan-json-stdio
```

## Background Flows

### FLOW: parallel-model-dispatch

```text
TRIGGER: debate or gauntlet requests multiple model calls
ENTRY: call_models_parallel() (skills/adversarial-spec/scripts/models.py:1114)
STATUS: implemented
STEPS:
  1. create worker futures -> call_single_model() per route
  2. collect ModelResponse or timeout/error -> update TokenTracker
  3. save partial results on failure -> return ordered responses
DATA_IN:
  - models: model route names
  - prompt/context: text payload and optional context files
DATA_OUT:
  - responses: list of ModelResponse
  - partial artifacts: per-call failure recovery files
EXITS_TO: debate-round-lifecycle, gauntlet-pipeline, model-error
BOUNDARIES: model-cli-stdio, model-litellm
```

### FLOW: hook-decision

```text
TRIGGER: Claude Code invokes a configured hook with JSON on stdin
ENTRY: codex_pretool_combined.main() (.claude/hooks/codex_pretool_combined.py:57)
STATUS: implemented
STEPS:
  1. json.load(stdin) -> invoke SUB_HOOKS sequentially
  2. first non-zero sub-hook exit -> stop and preserve hook output
  3. successful pipeline event -> optional systemMessage/notification hook
  4. emit protocol JSON or exit 0/no output
DATA_IN:
  - hook_event: tool name, tool input, tool result, role metadata
DATA_OUT:
  - decision: conditional block/warn/allow behavior
  - systemMessage: conditional operator/worker instruction
EXITS_TO: tool-execution, tool-blocked, pipeline-idle
BOUNDARIES: hook-stdio, fizzy-mcp-boundary, telegram-http
```

## Error Recovery Flows

### FLOW: gauntlet-resume

```text
TRIGGER: a prior gauntlet checkpoint or partial run is selected
ENTRY: load_partial_run() (skills/adversarial-spec/scripts/gauntlet/persistence.py:688)
STATUS: implemented
STEPS:
  1. resolve checkpoint path -> load envelope under lock
  2. validate schema/spec/config/data hashes -> reject mismatch
  3. restore phase state -> continue from next incomplete phase
  4. persist replacement checkpoint/manifest -> return result or typed error
DATA_IN:
  - checkpoint: JSON integrity envelope
  - spec/config: current hashes for compatibility
DATA_OUT:
  - resumed state: phase data and metrics
  - error: mismatch/corruption/lock failure
EXITS_TO: gauntlet-pipeline, gauntlet-error
BOUNDARIES: gauntlet-file-state
```

### FLOW: phase8-promotion-gate

```text
TRIGGER: Phase 8 attempts to close implementation work
ENTRY: evaluate_phase8_close() (skills/adversarial-spec/scripts/phase8_promotion.py:162)
STATUS: implemented
STEPS:
  1. select critical/spine records -> require promotion/evidence checks
  2. build PromotionRequest -> capture RunExecution evidence
  3. reject missing liveness/negative oracle/boundary mock lint -> or accept close
DATA_IN:
  - records: TMR registry rows and run evidence
DATA_OUT:
  - Phase8PromotionReport: requests, issues, promotable rows
EXITS_TO: provenance-transition, implementation-close, phase8-blocked
BOUNDARIES: tmr-registry-prose-view, provenance-files, validation-cli-stdout
```
