# Discovery: Data Flow

> Full nuke run; normalized from a delegated explorer. All anchors were reported from source.

PATH: debate-cli-to-model-output
SOURCE: stdin/session JSON (`debate.py:1026-1062`) and optional context files (`models.py:154`)
TRANSFORMS: session load; context wrapping; parallel `call_models_parallel` (`models.py:1114`); provider routing (`models.py:298-596,952`)
SINK: stdout (`debate.py:1227`), session/checkpoint files (`session.py:46-120`), per-model partial files (`models.py:1170`)
DATA_SHAPE: spec/options -> `ModelResponse {model,response,agreed,spec,error,input_tokens,output_tokens,cost}` -> results/cost output
NOTES: three retry attempts with exponential delays; partial persistence is best effort.

PATH: gauntlet-spec-to-verdict
SOURCE: CLI spec file/stdin (`gauntlet/cli.py:189`) or legacy debate CLI (`debate.py:921`)
TRANSFORMS: `run_gauntlet` (`orchestrator.py:205`); attacks (`phase_1_attacks.py:219`); filtering/clustering (`orchestrator.py:479-518`); multi-model evaluation (`phase_4_evaluation.py:118`); rebuttal/adjudication (`orchestrator.py:696-722`)
SINK: formatted report/stdout (`debate.py:973`) and resumable artifacts
DATA_SHAPE: spec -> `Concern[]` -> `Evaluation[]` -> final concerns
NOTES: non-empty unparseable attack output is fatal; evaluation parse failures defer a batch conservatively.

PATH: gauntlet-resume-and-artifacts
SOURCE: exact spec, phase results, resume request
TRANSFORMS: canonical serialization/hash (`gauntlet/persistence.py:79-106`); checkpoint validation (`persistence.py:281-325`); atomic locked writer (`persistence.py:124-152`)
SINK: `.adversarial-spec-gauntlet/` checkpoint, manifest, raw-response and report files (`orchestrator.py:305-533`)
DATA_SHAPE: `{_meta:{schema_version,spec_hash,config_hash,phase,data_hash},data}` envelope
NOTES: incompatible/corrupt checkpoints are ignored rather than resumed.

PATH: pre-gauntlet-grounding
SOURCE: spec, repo files, git state, configured commands
TRANSFORMS: affected-file extraction; git/system collectors; bounded context construction (`pre_gauntlet/orchestrator.py:85-204`)
SINK: `PreGauntletResult.context_markdown` and optional JSON report (`orchestrator.py:293`)
DATA_SHAPE: spec + repository observations -> typed concerns/state -> bounded markdown
NOTES: process runner validates arrays, redacts and truncates output (`integrations/process_runner.py:56-115`).

PATH: validation-manifest-to-conops
SOURCE: roadmap-manifest JSON (`validation_emission.py:688`)
TRANSFORMS: JSON/story validation, deterministic Markdown render, containment/byte/hash checks (`validation_emission.py:480-701`)
SINK: atomic ConOps file and stdout envelope
DATA_SHAPE: stories/milestones -> ConOps text plus full/per-story hashes
NOTES: overwrite is refused when an existing ledger binds the old hash unless forced.

PATH: validation-rows-and-evidence-ledger
SOURCE: ledger, ConOps, row/evidence CLI inputs
TRANSFORMS: row validation/normalization/evidence binding; sole `mutate_ledger` write path (`validation_emission.py:715-1372`)
SINK: `validation-rows.json`, per-row evidence files, stdout envelope
DATA_SHAPE: ledger rows/hash bindings -> normalized rows/evidence
NOTES: writer has lock+temp+fsync+replace; corrupt ledger is quarantined.

PATH: validation-digest-to-human-judgment
SOURCE: unjudged rows/evidence/ConOps and terminal or raw Telegram reply
TRANSFORMS: digest assembly (`validation_emission.py:1528`); send record; sender/reply/replay validation (`2348-2552`)
SINK: digest parts and ledger batch/judgment/security fields
DATA_SHAPE: rows -> multipart digest -> authenticated reply -> judgments
NOTES: secret-like digest content blocks emission; reply application is all-or-nothing.

PATH: tmr-registry-and-provenance
SOURCE: compile candidates, typed TMR records, registry JSON
TRANSFORMS: strict TMR validation/compile (`tmr_compile_step.py:64-156`); provenance transition/rollback (`provenance_journal.py:173-362`)
SINK: confirmed registry, append-only journal and index, conflict store
DATA_SHAPE: candidates -> TMR records/diff -> immutable transition records
NOTES: registry writes need confirmation; transitions use ordered locks/idempotency.

PATH: hook-protocol-and-telemetry
SOURCE: hook stdin JSON / successful pipeline tool result
TRANSFORMS: Fizzy input guard (`fizzy_payload_guard.py:86`), event extraction/dispatch (`pipeline_notifications.py:188-437`), session logger (`session_activity_logger.py:55-96`)
SINK: JSONL dispatch/activity logs and optional notification subprocess
DATA_SHAPE: hook payload -> normalized event / session activity line
NOTES: notification is non-blocking; pre-tool guard is authoritative for denial.

PATH: usage-aware-router
SOURCE: local headroom snapshot (`usage_router.py:36-64`) and optional prompt
TRANSFORMS: usage extraction/routing (`usage_router.py:64-121`)
SINK: stdout decision/response, optional Telegram sender
DATA_SHAPE: account usage -> `Route` -> optional Codex response
NOTES: stale/unavailable usage fails open to default route.
