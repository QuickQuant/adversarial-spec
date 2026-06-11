# Discovery: Control Flow (incremental 9ca3ccd→f198887, 2026-06-11)

FLOW: gauntlet_execution_phases | TYPE: lifecycle
SEQ: run_gauntlet (orchestrator.py:205) → config+unattended (:253-303) → resolve/validate models (:266-294) → adversaries+approved prompts (:308-312) → spec_as_gauntleted + manifest (:321-326) → resume load (:335-349) → P1 generate_attacks (:360-439) → P2 synthesis (:441-472) → P3 filter (:474-508) → P3.5 cluster (:513-564) → P4 evaluate [multi-model if >=2 eval models] (:581-680) → P5 rebuttals (:696-720) → P6 adjudication (:722-748) → P7 final boss optional (:776-885) → result+stats+medals (:887-959) → finally restore input() (:971-975)
EXITS: KeyboardInterrupt → "interrupted" exit 130 (:965-969); GauntletExecutionError on P1 quality gate (:414-419)
NOTES: spec hash once (:251); config_hash gates resume; manifest updated per phase; phase status completed|skipped_resume.

FLOW: rate_limited_batch_dispatch_phase_1 | TYPE: loop
SEQ: build (adv,model) pairs (phase_1_attacks.py:315) → group by provider (:317-319) → per provider get_rate_limit_config (model_dispatch.py:274): gemini free (1,15s)/paid (10,2); claude free (5,5)/paid (20,1); codex (10,2); default (3,10) → sleep before each batch (:336-342) → ThreadPoolExecutor max_workers=min(32,len) (:328) → collect futures (:348-350)
NOTES: pause is synchronous BEFORE submission; PROGRAMMING_BUGS re-raised (:306-307); per-pair timing dict (:324); resume runs only missing adversaries (orchestrator.py:364-382).

FLOW: pipeline_idle_retry_loop | TYPE: loop (hook)
SEQ: PostToolUse do_next_task → action==idle? → counter file → backoff schedule by hour (active 07-22 [30,60,120,240]; overnight + [480,960]) → time.sleep (blocks) → >=6 idles → dispatch status record → systemMessage forces retry.

FLOW: concern_verdict_state | TYPE: state_machine
STATES: accepted | dismissed | acknowledged | deferred (normalize_verdict core_types.py:72-74; Evaluation.__post_init__ :107-110)
TRANSITIONS: dismissed → [P5 rebuttal sustained] → P6 adjudication may overturn → technical_concerns; not sustained → resolved_concerns DB. FinalBossVerdict PASS|REFINE|RECONSIDER (core_types.py:47-51); REFINE/RECONSIDER mint synthetic ux_architect concerns.

HAZARD: parallel_model_call_partial_result_race
RESOURCE: round-{N}-{model}.json partials | CALLERS: call_models_parallel threads (models.py:948→1000)
SYNC: FileLock + tmp+rename + fsync (persistence.py:74-142) | CONSEQUENCE: serialized writes; stale .tmp on kill ignored.

HAZARD: gauntlet_checkpoint_resume_validity
RESOURCE: phase checkpoints | GATES: schema_version (persistence.py:308), spec_hash (:312), config_hash (:316-318), data_hash (:320-323), P4 concern-ID alignment (orchestrator.py:617-633)
CONSEQUENCE: any mismatch → fresh start (warn); config change forces P4 re-eval.

FLOW: multi_model_evaluation_dispatch | TYPE: branch (orchestrator.py:625-643)
use_multi_model && >=2 eval models → evaluate_concerns_multi_model w/ pick_eval_batch_arg (power_law_length tiers vs flat; min_concerns fallback) (:591-613).

FLOW: pipeline_card_gate_and_staleness_check | TYPE: branch (debate.py:1374-1497)
SEQ: require --pipeline-card (exit 2) → IntentionalOverride needs >=50-char reason → card format validation → session fizzy_card_id match → tests-pseudo staleness (spec mtime > tests mtime → exit 2 unless --accept-tests-stale/override).

FLOW: phase1_quality_gate_error_handling | TYPE: error_recovery
check_phase1_quality (phase_1_attacks.py:371): non-empty response + 0 parsed → save raw-responses + raise GauntletExecutionError (orchestrator.py:400-419). FATAL by design (no silent data loss). Recovery: manual extraction → patch concerns checkpoint → --resume.

FLOW: unattended_mode_enforcement | TYPE: error_recovery
input() monkey-patched to RuntimeError (orchestrator.py:299-303), restored in finally (:973-975); final boss falls back to skip on EOF/RuntimeError (:796); auto_checkpoint implied (:258).

FLOW: pipeline_continue_injection | TYPE: branch (hook)
PostToolUse complete_task/review/test + ok==true → systemMessage "DO NOT STOP. Call pipeline_do_next_task" with role; failure → no injection.

FLOW: phase_metrics_capture | TYPE: logging
_start_phase_capture → _build_phase_metrics (elapsed, token delta, models, status, extras) → update_run_manifest (incremental, crash-surviving). Adversary stats incremental update (persistence.py:352-414): signal_score, dismissal_effort, rebuttals.

FLOW: checkpoint_validity_chain | TYPE: validation (persistence.py:688 load_partial_run)
config_hash includes timeout + attack/eval codex reasoning; excludes auto_checkpoint/resume. Envelope {_meta, data}; legacy list checkpoints recognized not resumable; allow_plain_json for raw-responses.
