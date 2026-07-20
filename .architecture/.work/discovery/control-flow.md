# Phase 1 Discovery: Control Flow

> Architecture verified at `ef18c66`. Delegated explorers timed out; this
> fallback records current source-backed lifecycle and hazard evidence.

## Lifecycle and state flows

FLOW: debate_round_lifecycle
TYPE: lifecycle
SEQUENCE:
  1. parse CLI/profile/session/gauntlet options (`debate.py:525-611`)
  2. apply profile and resolve model list (`debate.py:733-824`)
  3. validate credentials and preflight models (`debate.py:1312`, `models.py:1088`)
  4. load/resume session or read new spec (`debate.py:1026`)
  5. dispatch parallel critiques and synthesize own response (`debate.py:1086`)
  6. persist checkpoints/output and optionally return for another round (`debate.py:1227`, `session.py:45`)
TRIGGERS:
  - installed CLI invocation
EXITS:
  - consensus/output, user review, error, or checkpoint/resume
NOTES: pipeline-card and staleness gates can stop execution before model calls (`debate.py:1366`).

FLOW: gauntlet_pipeline
TYPE: lifecycle
SEQUENCE:
  1. resolve config/prompts/adversaries (`orchestrator.py:125-205`)
  2. gauntlet-internal phase 1 attacks (`phase_1_attacks.py:323`)
  3. gauntlet-internal phase 2 synthesis and phase 3 filtering (`phase_2_synthesis.py`, `phase_3_filtering.py:130`)
  4. gauntlet-internal phase 3.5 clustering (`clustering.py`, `persistence.py:587`)
  5. gauntlet-internal phase 4 evaluation, phase 5 rebuttals, phase 6 adjudication (`phase_4_evaluation.py:118`, `phase_5_rebuttals.py:1`, `phase_6_adjudication.py:1`)
  6. gauntlet-internal phase 7 final boss and verdict (`phase_7_final_boss.py:1`)
  7. persist result/stats/medals/run manifest (`persistence.py:469-629`, `medals.py:220`)
TRIGGERS:
  - `debate.handle_gauntlet` or `gauntlet.cli.main`
EXITS:
  - `GauntletResult`, resume checkpoint, or typed execution error
NOTES: phase checkpoints are integrity-checked and can resume from partial runs.

FLOW: validation_ledger_state_machine
TYPE: state_machine
STATES:
  - assembled -> [send] -> sent
  - sent -> [parse reply] -> processed or reprompt/error
  - failed/stale -> [reset/cancel] -> terminal batch state
  - ledger row -> [evidence/promotion] -> updated TMR/evidence state
TRIGGERS:
  - validation_emission subcommands (`validation_emission.py:67`, `3255`)
EXITS:
  - one-line `Envelope` and process exit code
NOTES: allowed statuses and issue exit mapping are constants at `validation_emission.py:51-67`; lock contention is explicit.

FLOW: phase8_promotion_gate
TYPE: state_machine
STATES:
  - non-concrete TMR -> [build request] -> PromotionRequest
  - PromotionRequest -> [capture run] -> RunExecution/evidence
  - TMR -> [evaluate close] -> promoted or blocking PromotionIssue
TRIGGERS:
  - Phase 8 implementation close checks (`phase8_promotion.py:74-162`)
EXITS:
  - `Phase8PromotionReport` with issues and promotion requests
NOTES: critical/spine real-data records require live or induced evidence, negative oracle, and boundary-mock lint.

FLOW: hook_decision
TYPE: branch
SEQUENCE:
  1. receive tool event on stdin (`codex_pretool_combined.py:57`)
  2. run sub-hooks in configured order (`codex_pretool_combined.py:18-26`)
  3. classify as allow, warn, deny, or system message (`fizzy_payload_guard.py:51-86`, `dispatch_check.py:86`)
  4. emit JSON decision on stdout
TRIGGERS:
  - Claude Code hook lifecycle
EXITS:
  - tool proceeds, is blocked, or operator receives a system message
NOTES: some hooks are safety gates, others are coordination/notification side effects.

## Concurrency and shared-state evidence

HAZARD: parallel model responses share partial-result and token accounting state
RESOURCE: partial result files and process-wide token tracker
CALLERS:
  - `call_models_parallel` worker futures (`models.py:1114`)
  - `_save_partial_result` (`models.py:1170`)
  - `TokenTracker` updates from model calls (`token_tracking.py:19`)
SYNCHRONIZATION: token tracker uses a `threading.Lock` (`token_tracking.py:19`); partial-result filenames are per-model but failure recovery needs targeted review
CONSEQUENCE: duplicate/overwritten partial artifacts or inconsistent totals if a new caller reuses a result path

HAZARD: validation ledger and provenance writers have competing file writers
RESOURCE: validation ledger/batches and TMR registry/journal/index
CALLERS:
  - `mutate_ledger` (`validation_emission.py:1337`)
  - `ProvenanceJournalWriter.append` path (`provenance_journal.py:112`, `581`)
SYNCHRONIZATION: FileLock for ledger (`validation_emission.py:959`, `1337`); ordered multi-file locks for provenance (`provenance_journal.py:581-596`)
CONSEQUENCE: lock contention is surfaced as a typed issue; stale expected coordinates reject lost updates.

HAZARD: gauntlet stats/medals/run artifacts have multiple writers
RESOURCE: `.adversarial-spec-gauntlet` and home stats/medal files
CALLERS:
  - checkpoint/run persistence (`persistence.py:469-629`)
  - medals writes (`medals.py:220-240`)
  - filtering stats append (`phase_3_filtering.py:217-233`)
SYNCHRONIZATION: persistence uses per-file FileLock (`persistence.py:74-137`); filtering stats write path has no shared lock visible in the current source
CONSEQUENCE: concurrent gauntlet runs may race on stats append; run-specific artifacts are safer than shared stats.
