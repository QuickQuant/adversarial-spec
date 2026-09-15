# Discovery: Control Flow and Hazards

> Full nuke run; normalized from a delegated explorer.

FLOW: skill-session-phase-lifecycle
TYPE: lifecycle
SEQUENCE: register role/listener -> validate session pointer, journey and phase artifacts -> requirements through implementation -> verification/closure
TRIGGERS: skill invocation or resume pointer
EXITS: missing artifact/order anomaly stops for operator direction; Phase 9 pass permits closure
NOTES: `skills/adversarial-spec/SKILL.md:50-145`, Phase 8/9 docs; documented sequence omits verification while Phase 9 requires it.

FLOW: debate-round-dispatch-and-checkpoint
TYPE: lifecycle
SEQUENCE: pipeline gate -> model/profile validation -> session load -> parallel critique -> partial result save -> session/checkpoint write -> optional Telegram
TRIGGERS: `debate.py critique`
EXITS: gates/preflight failures abort; individual model failures remain per-result errors
NOTES: `debate.py:1026-1214,1366-1675`; `models.py:741-790,1114-1199`.

FLOW: fizzy-managed-debate-round
TYPE: lifecycle
SEQUENCE: create workspace/checklist -> dispatch isolated critics -> register returned artifacts -> recover timed-out wrapper by polling expected result directory
TRIGGERS: Phase 3 debate
EXITS: rejection/recovery procedure ends standalone fallback
NOTES: `phases/03-debate.md:459-534`; timeout means ambiguous launch state, not permission to redispatch.

FLOW: gauntlet-seven-phase-orchestration
TYPE: lifecycle
SEQUENCE: config/hash/manifest -> compatible resume -> attacks -> synthesis/filter/cluster -> evaluation -> rebuttal/adjudication -> optional Final Boss -> persist result
TRIGGERS: standalone gauntlet CLI or debate gauntlet
EXITS: interrupt writes status and exits 130; invalid config fails before phases
NOTES: `gauntlet/orchestrator.py:250-975`; persistence is locked/atomic per target file.

FLOW: parallel-gauntlet-model-work
TYPE: loop
SEQUENCE: provider-bounded attack batches -> concurrent filtering -> concurrent evaluation waves -> optional concurrent rebuttals
TRIGGERS: selected models and nonempty concern list
EXITS: parse/operational failures defer or retain concerns conservatively
NOTES: `phase_1_attacks.py:321-384`, `phase_4_evaluation.py:73-324`, `phase_5_rebuttals.py:74-90`; token tracker has a lock.

FLOW: pre-gauntlet-alignment
TYPE: state_machine
STATES: COMPLETE, NEEDS_ALIGNMENT, ABORTED, INFRA_ERROR
TRIGGERS: gauntlet `--pre-gauntlet`
EXITS: non-complete maps to CLI exit code; complete enriches spec
NOTES: `pre_gauntlet/orchestrator.py:67-325`, `alignment_mode.py:60-177`.

FLOW: validation-close
TYPE: state_machine
STATES: drafted -> evidence-attached -> digested -> judged-pass/fail/na -> remediation/re-execution or superseded
TRIGGERS: implementation close leg
EXITS: all required rows must pass/supersede before artifact/check/MCP close
NOTES: `phases/08-implementation.md:331-498`, `validation_emission.py:956-1372`.

FLOW: hook-dispatch-and-telemetry
TYPE: loop
SEQUENCE: hook stdin JSON -> payload validation/event extraction -> optional notification/dispatch/activity append
TRIGGERS: hook lifecycle and Fizzy tool events
EXITS: invalid/missing inputs exit without output side effects
NOTES: `.claude/hooks/fizzy_payload_guard.py:86`, `pipeline_notifications.py:392-437`, `session_activity_logger.py:55-96`.

## Hazards

HAZARD: gauntlet-sidecar-overwrite
RESOURCE: raw responses, cluster reports, dedup stats for a spec hash
CALLERS: `run_gauntlet` direct sidecar writes (`orchestrator.py:399-403,533-556`); `_track_dedup_stats` (`phase_3_filtering.py:211-233`)
SYNCHRONIZATION: none
CONSEQUENCE: concurrent same-spec runs can overwrite recovery artifacts or lose stats.

HAZARD: resolved-concern-counter-lost-update
RESOURCE: `resolved_concerns.json` match counters
CALLERS: concurrent Phase-3 futures and `record_explanation_match` (`phase_3_filtering.py:155-165`, `persistence.py:927-935`)
SYNCHRONIZATION: lock does not span read-modify-write
CONSEQUENCE: historical match count can undercount.

HAZARD: session-state-concurrent-write
RESOURCE: session JSON and round checkpoints
CALLERS: session updates and parallel partial model completions (`session.py:46-134`, `models.py:1163-1199`)
SYNCHRONIZATION: none
CONSEQUENCE: concurrent resumes can overwrite session history/latest spec.

HAZARD: hook-idle-counter-cross-session
RESOURCE: `/tmp/pipeline-idle-count-<project>-<role>.txt`
CALLERS: idle-hook executions (`pipeline_idle_retry.py:73-156`)
SYNCHRONIZATION: none; key omits session ID
CONSEQUENCE: same-role workers alter each other’s backoff state.

HAZARD: review-dispatch-replay
RESOURCE: `.conductor/dispatch/<agent>/updates.jsonl`
CALLERS: completion/review notification hooks (`pipeline_notifications.py:275-346`)
SYNCHRONIZATION: no event ID/deduplication
CONSEQUENCE: replayed hooks create duplicate dispatch messages.

HAZARD: canonical-phase-order-mismatch
RESOURCE: session journey validation
CALLERS: resume checker and Phase 8/9 workflow documents
SYNCHRONIZATION: documentation/state-contract mismatch
CONSEQUENCE: a recorded verification transition can be falsely flagged as out of order (`SKILL.md:75-108`, `phases/08-implementation.md:268-277`, `phases/09-verification.md:184-198`).
