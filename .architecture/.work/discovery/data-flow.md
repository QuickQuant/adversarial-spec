# Phase 1 Discovery: Data Flow

> Architecture verified at `ef18c66`. Local fallback after five delegated
> discovery explorers were shut down for timeout; anchors are from current source.

## Debate and model dispatch

PATH: debate_spec_to_model_results
SOURCE: CLI arguments/stdin/file loading through `skills/adversarial-spec/scripts/debate.py:525-611`
TRANSFORMS:
  1. `create_parser` and argument handlers normalize command/profile/gauntlet options (`debate.py:525`)
  2. `parse_models` resolves explicit/default provider models (`debate.py:757`)
  3. `validate_models_before_run` checks credentials/availability (`debate.py:1312`)
  4. `preflight_models` optionally pings model routes (`models.py:1088`)
  5. `call_models_parallel` dispatches independent model calls (`models.py:1114`)
  6. `call_single_model` selects CLI, Bedrock, or LiteLLM adapter (`models.py:688`)
SINK: `output_results` plus session/checkpoint/Telegram output (`debate.py:1227`, `session.py:45-133`)
DATA_SHAPE: spec/context text in; `ModelResponse` objects and model-specific text/usage out (`models.py:141-151`)
NOTES: model calls run in a `ThreadPoolExecutor`; partial results are persisted on failure (`models.py:1170-1197`).

PATH: gauntlet_spec_to_verdict
SOURCE: `skills/adversarial-spec/scripts/gauntlet/orchestrator.py:205`
TRANSFORMS:
  1. load approved prompts and resolve enabled adversaries (`orchestrator.py:125-200`)
  2. generate adversarial concerns in parallel (`phase_1_attacks.py:323-363`)
  3. synthesize/filter concerns (`phase_2_synthesis.py:1`, `phase_3_filtering.py:130`)
  4. cluster near-duplicates and persist clustering state (`clustering.py:1`, `persistence.py:587`)
  5. evaluate concerns in tiered parallel batches (`phase_4_evaluation.py:118-245`)
  6. collect rebuttals, adjudicate, and run final boss (`phase_5_rebuttals.py:1`, `phase_6_adjudication.py:1`, `phase_7_final_boss.py:1`)
SINK: `GauntletResult`, run manifest, checkpoint/raw-response/spec artifacts (`core_types.py:232`, `persistence.py:469-629`)
DATA_SHAPE: spec text -> `Concern`/`Evaluation`/`Rebuttal`/verdict dataclasses (`core_types.py:83-232`)
NOTES: FileLock and integrity hashes protect checkpoint/run writes; retry and partial-resume paths exist.

PATH: pre_gauntlet_compatibility
SOURCE: `skills/adversarial-spec/scripts/pre_gauntlet/orchestrator.py:207`
TRANSFORMS:
  1. load compatibility configuration from `pyproject.toml` (`orchestrator.py:254`)
  2. collect git/system context (`collectors/git_position.py:30`, `collectors/system_state.py:33`)
  3. discover services and build context (`pre_gauntlet/discovery.py:44`, `context_builder.py:17`)
  4. run configured build/schema/validation checks
SINK: `PreGauntletResult` serialized by `save_report` (`orchestrator.py:293`)
DATA_SHAPE: spec and repo configuration -> compatibility status plus findings
NOTES: blocker status enters Alignment Mode; exit code is selected by `get_exit_code` (`orchestrator.py:317`).

PATH: tmr_prose_to_registry
SOURCE: candidate records supplied to `tmr_compile_step.compile_tmr_records` (`tmr_compile_step.py:64`)
TRANSFORMS:
  1. coerce candidate/accessor shapes and resolve identity (`tmr_compile_step.py:183-222`)
  2. mint/validate ULID identity where missing (`tmr_compile_step.py:158-170`)
  3. diff by `tmr_uid` and emit semantic diff events (`tmr_compile_step.py:224-249`)
  4. validate every record against strict Pydantic schema (`tmr_schema.py:175-377`)
SINK: confirmed `tmr-registry.json` and regenerated prose view (`tmr_compile_step.py:123-156`)
DATA_SHAPE: candidate mappings -> `TestMaturityRecord` JSON with schema/identity/lineage fields
NOTES: registry is authoritative once present; prose view is derived.

PATH: validation_ledger_lifecycle
SOURCE: JSON/CLI input to `validation_emission.main` (`validation_emission.py:3423`)
TRANSFORMS:
  1. parse subcommand and resolve paths under the spec root (`validation_emission.py:3255`, `312`)
  2. normalize/lint rows and compute canonical row/story/conops hashes (`validation_emission.py:397-457`, `1093`)
  3. mutate ledger under FileLock with atomic replacement (`validation_emission.py:1337`, `1048`)
  4. assemble/send/parse Telegram digest batches or record system-validation evidence (`validation_emission.py:1528`, `1757`, `2348`, `2606`)
  5. run self-check/status and emit an `Envelope` (`validation_emission.py:2888`, `3102`, `200`)
SINK: ledger, evidence artifacts, batch state, and one-line stdout envelope
DATA_SHAPE: bounded JSON objects/Markdown replies -> normalized rows, hashes, evidence records, status envelope
NOTES: duplicate IDs, stale hashes, lock contention, oversized input, secrets, and stale batches have explicit issue codes.

PATH: provenance_transition
SOURCE: registry/journal inputs to `ProvenanceJournalWriter` (`provenance_journal.py:112`)
TRANSFORMS:
  1. validate subject and event types (`provenance_journal.py:19-40`)
  2. check expected coordinates/lineage and build transition record (`provenance_journal.py:54`, `460`)
  3. acquire ordered locks for registry, journal, and index (`provenance_journal.py:581-596`)
  4. atomically write registry/journal/index and restore previous bytes on failure (`provenance_journal.py:522-573`)
SINK: TMR registry, append-only decision/journey log, and provenance index
DATA_SHAPE: transition command -> immutable event/receipt (`AppendReceipt` at `provenance_journal.py:105`)
NOTES: `expected_from` rejects stale writers; tombstone/rename are explicit events.

PATH: hook_stdio_decision
SOURCE: Claude hook JSON stdin (`.claude/hooks/codex_pretool_combined.py:57`)
TRANSFORMS:
  1. decode input and invoke configured sub-hooks (`codex_pretool_combined.py:26-65`)
  2. classify command/payload/role via safety and pipeline hook modules
  3. append local activity/dispatch or send Telegram notifications when configured
SINK: JSON decision/systemMessage on stdout; optional local logs/Telegram side effects
DATA_SHAPE: hook event JSON -> allow/deny/warn decision envelope
NOTES: hook outputs must remain machine-readable; failures should fail closed for safety hooks.

PATH: plan_to_dependency_report
SOURCE: plan JSON consumed by `dependency_semantics.main` (`dependency_semantics.py:525-575`)
TRANSFORMS: parse tasks, normalize edge kinds/waves, topologically profile dependencies (`dependency_semantics.py:35-82`)
SINK: JSON report to stdout (`dependency_semantics.py:570`)
DATA_SHAPE: execution-plan task graph -> report schema version 1 with issues and profiles
NOTES: no persistent write path.
