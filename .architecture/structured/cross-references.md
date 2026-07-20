# Cross References

> Calls, data paths, boundaries, and dependency lookups. Generated at `ef18c66`; if a cited source file changes, trust source over this document.

## Function Call Graph

### Debate / model routing

```text
debate.main() (debate.py:1623)
  ├── calls: create_parser(), apply_profile(), parse_models(), handle_gauntlet(), run_critique(), output_results()
  ├── called_by: console script, direct module invocation
  └── async: no

run_critique() (debate.py:1086)
  ├── calls: load_or_resume_session(), validate_models_before_run(), call_models_parallel(), output_results()
  ├── called_by: debate.main()
  └── async: no; model workers are threaded below

call_models_parallel() (models.py:1114)
  ├── calls: call_single_model(), _save_partial_result(), TokenTracker updates
  ├── called_by: debate.run_critique()
  └── async: no; ThreadPoolExecutor workers

gauntlet.model_dispatch.call_model() (gauntlet/model_dispatch.py:64)
  ├── calls: CLI adapters from models.py, LiteLLM completion(), TokenTracker updates
  ├── called_by: gauntlet phase modules
  └── async: caller-controlled worker pools
```

### Gauntlet

```text
run_gauntlet() (gauntlet/orchestrator.py:205)
  ├── calls: prompt/adversary resolution, phase_1_attacks, phase_2_synthesis, phase_3_filtering, clustering, phase_4_evaluation, phase_5_rebuttals, phase_6_adjudication, phase_7_final_boss
  ├── called_by: debate.handle_gauntlet(), gauntlet.cli.main()
  └── async: phase modules use worker pools

phase_1_attacks.generate_attacks() (gauntlet/phase_1_attacks.py:323)
  ├── calls: model_dispatch.call_model(), prompt/parsing helpers
  ├── called_by: orchestrator.run_gauntlet()
  └── async: yes, ThreadPoolExecutor

save_checkpoint() (gauntlet/persistence.py:560)
  ├── calls: _lock_for(), _write_json_atomic(), envelope/hash helpers
  ├── called_by: orchestrator and phase recovery paths
  └── async: no; FileLock protected
```

### Evidence / validation

```text
compile_tmr_records() (tmr_compile_step.py:64)
  ├── calls: _parse_records(), _resolve_accessors(), _diff_by_tmr_uid(), validate_tmr_record()
  ├── called_by: compiler callers/tests
  └── async: no

validation_emission.main() (validation_emission.py:3423)
  ├── calls: build_parser(), HANDLERS[subcommand], _emit()
  ├── called_by: direct CLI/module invocation
  └── async: no; ledger handlers acquire FileLock

ProvenanceJournalWriter (provenance_journal.py:112)
  ├── calls: ordered locks, atomic JSON writes, transition validators
  ├── called_by: evidence/promotion/disposition callers
  └── async: no; multi-file lock ordering
```

### Hooks

```text
codex_pretool_combined.main() (.claude/hooks/codex_pretool_combined.py:57)
  ├── calls: load_and_run() for SUB_HOOKS
  ├── called_by: Claude Code hook runner
  └── async: no

pipeline_notifications.main() (.claude/hooks/pipeline_notifications.py:392)
  ├── calls: _extract_event(), _handle_complete_task(), _handle_review(), _telegram_send()
  ├── called_by: Claude Code hook runner
  └── async: no
```

## Data Path Summary

| Data path | Source | Transforms | Sink |
|---|---|---|---|
| `debate-spec-to-responses` | CLI/stdin/file | parse → provider validation → preflight → model adapters | ModelResponse/output/session |
| `gauntlet-to-verdict` | spec text | attacks → synthesis/filter → cluster → evaluate → rebut/adjudicate/final boss | GauntletResult + run files |
| `tmr-candidate-to-registry` | candidate records | identity/accessor resolution → strict schema → diff | `tmr-registry.json` + prose view |
| `ledger-to-evidence` | validation CLI payload | normalize → hash → lock/mutate → digest/reply/system validation | ledger/evidence/Envelope |
| `transition-to-lineage` | JournalTransition | expected-from check → ordered locks → atomic write | registry/journal/index |
| `hook-event-to-decision` | Claude Code stdin JSON | sub-hook classifiers → exit/stdout protocol | tool decision/systemMessage |

## Message Formats

| Message type | Direction | Format | Used by |
|---|---|---|---|
| `ModelResponse` | model → orchestration | dataclass with text/usage/error fields | debate, gauntlet, token tracking |
| `Envelope` | validation CLI → caller | `{status, code, issues, data}` | validation automation |
| `GateResult` | gate CLI → caller | `{outcome, findings, override_eligible}` | `gauntlet-check`, pipeline gate |
| `Hook decision` | hook → Claude Code | conditional JSON `{decision, reason}` and/or `{systemMessage}`; allow may be exit 0/no output | Claude Code hook runner |
| `TMR` | compiler → registry | strict JSON schema `tmr.v1` | parser, promotion, provenance |

## Boundary Field Contracts

### `validation-cli-stdout`: validation handler → `_emit` → CLI/MCP caller

Chain: `validation_emission.py:688-3102` → `_emit` `validation_emission.py:3418` → caller → process exit code.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `status` | always for handled invocation | yes | `ok`, `issues`, `reprompt`, `error` | no | malformed/non-envelope output; do not infer success | handler | `validation_emission.py:51-67,200-220,3418-3428` | verified |
| `code` | conditional on issue/error or command-specific result | yes | string or null | no | no finer-grained code; inspect status/issues | handler | `validation_emission.py:194-220,3423-3460` | verified |
| `issues` | always structurally, often empty | yes | list of issue objects | caller-owned | empty issue list; not proof of mutation success without `status` | handler | `validation_emission.py:194-220` | verified |
| `data` | always structurally, command-dependent content | yes | mapping | command-specific | no command payload; inspect status/code | handler | `validation_emission.py:200-220,2888-2908` | verified |

### `hook-stdio`: Claude Code → combined/sub-hooks → Claude Code

Chain: hook runner stdin → `codex_pretool_combined.py:26-72` → individual hook stdout/exit → Claude Code.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `decision` | only deny-capable hook emits JSON decision | yes for emitted JSON; allow uses exit 0 | hook protocol | no | allow/no-op for combined safety path when exit 0; not a pipeline transition | hook protocol + sub-hook | `codex_pretool_combined.py:26-72`, `fizzy_payload_guard.py:51-86` | verified |
| `reason` | conditional with block decision | yes | hook protocol | no | no diagnostic detail | sub-hook | `fizzy_payload_guard.py:51-60,105-149` | verified |
| `systemMessage` | conditional pipeline hook output | direct | hook protocol | transient | no operator/worker message; hook may still act/log | pipeline hook | `pipeline_continue.py:70-121`, `pipeline_idle_retry.py:130-159` | verified |

### `tmr-registry-prose-view`: compiler → registry/prose → parser/promotion

Chain: candidates → `tmr_compile_step.py:64-156` → `tmr-registry.json` / `render_prose_view` → `tmr_schema.py:377` and promotion.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `tmr_uid` | required after compile; minted when missing | yes in registry; prose may summarize | strict identity field | required in registry | missing candidate identity triggers ULID allocation; missing confirmed identity is schema-invalid | compiler/registry | `tmr_compile_step.py:158-170`, `tmr_schema.py:175-377` | verified |
| `maturity` | candidate/schema field | yes | `nl`, `acceptance`, `concrete` | required/schema-controlled | invalid or missing maturity rejects record | TMR schema | `tmr_schema.py:28-30,175-345` | verified |
| `run_evidence` | conditional by maturity/verification needs | yes in registry; prose view derived | strict union types | preserve structured evidence | no run proof; promotion may block critical/spine close | TMR schema/promotion | `tmr_schema.py:124-174`, `phase8_promotion.py:162-243` | verified |

### `gauntlet-check-gate`: gate implementation → envelope → pipeline caller

Chain: `gauntlet_check_cli.py:27-264` → `GateResult.to_envelope` → CLI/MCP caller.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `outcome` | always on handled gate result | yes | enumerated GateResult outcome | caller-owned | invalid result; no pass inference | `gate_result.py` | `gate_result.py:13-85`, `gauntlet_check_cli.py:264-295` | verified |
| `findings` | always structurally, empty when no findings | yes | list of strict GateFinding | caller-owned | no finding details; outcome still controls gate | gate implementation | `gate_result.py:43-85` | verified |
| `override_eligible` | always structurally | yes | boolean with model validator constraints | caller-owned | false/absent is non-override path | gate result | `gate_result.py:54-85` | verified |

### `model-cli-stdio`: model router → CLI subprocess → model router

Chain: `models.call_single_model` `models.py:688` → CLI adapter `models.py:298-688` → subprocess stdout/stderr → parser.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `text` | provider-dependent successful response | yes after adapter parsing | `ModelResponse.text` | output/session may persist | empty/invalid response becomes model error or empty critique | provider adapter/parser | `models.py:141-151,298-688` | verified |
| `usage` | provider-dependent; CLI may omit | adapter normalizes when available | token/cost tracker accepts optional counts | optional | zero/absent usage means unknown/zero-cost route; do not treat as provider billing proof | adapter/provider | `models.py:141-151,688-711`, `token_tracking.py:19-70` | verified |

### `telegram-http`: Telegram helper → Telegram Bot API

Chain: `telegram_bot.api_call` `telegram_bot.py:47` → HTTPS request `telegram_bot.py:69-75` → Telegram API.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `chat_id` | required for send/poll operations | yes | Telegram API request | no local authority | missing config blocks helper; no message target | caller/config | `telegram_bot.py:36-47,266-365` | verified |
| `text` | required for send/notify, split when oversized | yes | Telegram message payload | no | empty message is rejected/has no useful notification | caller | `telegram_bot.py:78-136` | verified |

### `gauntlet-file-state`: orchestrator → lock/hash persistence → run artifacts

Chain: phase state → `persistence.py:74-137,560-688` → `.adversarial-spec-gauntlet`/home stats files.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `_meta.schema_version` | always in checkpoint envelope | yes | exact supported checkpoint schema | required | cannot safely resume | persistence module | `persistence.py:45,79-137,281-333` | verified |
| `spec_hash` | always in checkpoint/run identity | yes | must match current spec for resume | required | checkpoint is unbound to spec; reject resume | persistence module | `persistence.py:171-212,281-333,792` | verified |
| `data_hash` | always in checkpoint metadata | yes | must match serialized data | required | integrity cannot be established; reject/repair | persistence module | `persistence.py:99-137,281-333` | verified |

### `provenance-files`: transition writer → registry/journal/index

Chain: `ProvenanceJournalWriter` `provenance_journal.py:112` → ordered locks `581-596` → atomic file writes `522-573`.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `expected_from` | conditional on caller providing optimistic coordinates | yes | writer validates when present | preserve lineage | absent means no optimistic fence requested; stale-writer protection is weaker | caller/writer | `provenance_journal.py:54-105,112-400` | verified |
| `event_type` | required transition field | yes | allowed event enum | append-only | missing/unknown event cannot be applied | journal writer | `provenance_journal.py:19-40,460-479` | verified |

### `pre-gauntlet-subprocess`: compatibility runner → configured command

Chain: pre-gauntlet orchestration `orchestrator.py:207-254` → configured build/schema/validation command → captured result.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `command` | only for configured check | yes | subprocess runner | report only | no check executed; status may remain incomplete | pyproject config | `orchestrator.py:254-293` | verified |
| `environment` | optional config field | yes | result metadata | report only | environment unknown; do not assume production/development | config/runner | project config loader and `orchestrator.py:254-293` | verified |

### `plan-json-stdio`: plan file → dependency analyzer → report stdout

Chain: `dependency_semantics.main` `dependency_semantics.py:525-575` → `analyze_plan` `:82` → JSON stdout `:570`.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `tasks` | required plan input | yes | list of task mappings | no | schema/analysis error | plan author | `dependency_semantics.py:35-82,537-570` | verified |
| `edges` | optional/derived per task | yes | known edge kinds | no | no dependency edge; not proof of independence if omitted by malformed plan | analyzer | `dependency_semantics.py:25-82` | verified |

### `model-litellm`: model router → LiteLLM/provider API → model router

Chain: `models.call_single_model` `models.py:688` → LiteLLM/provider transport → `ModelResponse`.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| prompt/messages | always for call | yes | provider API | no | no model request; call must fail | model caller | `models.py:688-711` | verified |
| content | provider-success dependent | normalized | `ModelResponse.text` | output conditional | provider error/empty content; inspect error | provider | `models.py:141-151,688-711` | verified |
| usage | provider-dependent | best effort | optional tracker fields | optional | unknown usage; no billing inference | provider/adapter | `models.py:141-151,688-711`, `token_tracking.py:19-70` | verified |

### `session-files`: debate state → session JSON → resume loader

Chain: `SessionState.save` `session.py:42` → session JSON → `SessionState.load`.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| session identity | required for named session | yes | path-safe loader | required | no resumable identity; start/new session path | session module | `session.py:17,42-133` | verified |
| round/history | conditional by progress | yes | SessionState fields | preserve | fresh/partial round state; not consensus | session/debate | `session.py:17-133` | verified |

### `validation-ledger-files`: validation command → locked ledger → evidence handlers

Chain: validation handlers → `mutate_ledger` `validation_emission.py:1337` → ledger/batches/evidence files.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| row identity/hash | always for normalized row | yes | ledger row key/hash | required | row cannot be updated/idempotently matched | validation module | `validation_emission.py:359-457,1093-1182` | verified |
| batch status | conditional after digest/send | yes | batch state machine | required when batch exists | no batch action; do not infer send | validation module | `validation_emission.py:300-310,1528-1885` | verified |
| evidence ref | conditional after evidence recording | yes | TMR/evidence consumer | required for recorded evidence | no proof attached; promotion may block | validation/promotion | `validation_emission.py:1183-1337,2606-2750` | verified |

### `pre-gauntlet-report`: compatibility checks → serialized report → operator/gauntlet caller

Chain: `run_pre_gauntlet` `orchestrator.py:207` → `save_report` `orchestrator.py:293` → caller.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| status | always on completed orchestration | yes | typed status/exit mapping | report | no compatibility conclusion | orchestrator | `orchestrator.py:310-327` | verified |
| findings/checks | conditional per configured checks | yes | result/report lists | report | no finding/check detail; status still controls | orchestrator/checks | `orchestrator.py:207-309` | verified |

### `fizzy-mcp-boundary`: hook payload guard → Fizzy MCP caller

Chain: Claude tool event → `fizzy_payload_guard.main` `fizzy_payload_guard.py:86` → Fizzy MCP tool call.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `tool_name` | required for guard classification | yes | Fizzy tool router | no | guard no-op/allow path; caller must still validate tool | hook/MCP protocol | `fizzy_payload_guard.py:86-105` | verified |
| scoped limit/filter | conditional by tool | yes | tool-specific args | no | unbounded call may be denied | hook rule/MCP tool | `fizzy_payload_guard.py:31-44,105-149` | verified |
| override metadata | conditional for override | yes | guard only | override log conditional | no valid override; deny stands | hook process-failure policy | `fizzy_payload_guard.py:60-84` | verified |

## Type Contracts

| Contract | Owner | Consumed by | Notes |
|---|---|---|---|
| `ModelResponse` | `models.py:141-151` | debate, gauntlet dispatch, token tracker | usage/error fields may be provider-dependent |
| `Concern`, `Evaluation`, `Rebuttal`, `GauntletResult` | `gauntlet/core_types.py:83-232` | all gauntlet phases/persistence/reporting | verdict normalization is centralized |
| `GauntletConfig`, `CheckpointMeta`, `PhaseMetrics` | `gauntlet/core_types.py:424-482` | orchestrator/persistence/CLI | config and integrity metadata travel with a run |
| `TestMaturityRecord` | `tmr_schema.py:175-377` | compiler/parser/promotion/journal/tests | strict schema; registry authoritative |
| `GateResult` | `gate_result.py:54-123` | gate CLI/pipeline callers | `outcome` is canonical; `result` is not an alias |
| `Envelope` | `validation_emission.py:200-220` | validation automation | stdout shape stays stable on handled exceptions |
| `Phase8PromotionReport` | `phase8_promotion.py:62-72` | Phase 8 close | issues are blocking evidence gaps |

## Data Model / Access Boundaries

| Surface | Kind | Owned by | Readers/writers | Access |
|---|---|---|---|---|
| Gauntlet checkpoint envelope | file schema | `gauntlet/persistence.py` | orchestrator/CLI/resume | local process/file lock |
| Gauntlet run manifest/raw artifacts | files | `gauntlet/persistence.py` | phases/reporting/operators | local filesystem |
| TMR registry | JSON registry | `tmr_schema.py`/compiler | compiler/parser/promotion/provenance | local filesystem + ordered locks |
| Validation ledger/batches | JSON ledger | `validation_emission.py` | validation commands/evidence workflow | local filesystem + FileLock |
| Provenance journal/index | JSON/event log | `provenance_journal.py` | promotion/disposition/reporting | local filesystem + multi-file lock |
| Hook stdin/stdout | process protocol | Claude Code | hooks/Claude Code | process boundary |

## Hub Files

| File | Imported-by status | Why it matters |
|---|---|---|
| `gauntlet/core_types.py` | high fan-in across gauntlet package/tests | shared phase dataclasses/enums/config |
| `gauntlet/persistence.py` | high fan-in across phases/CLI/reporting | integrity/checkpoint/run state |
| `models.py` | debate and gauntlet model callers | provider adapter and parallel dispatch |
| `providers.py` | models/token tracking/debate | model constants, credentials, profiles, costs |
| `tmr_schema.py` | compiler/parser/promotion/classifiers/tests | strict evidence contract |
| `validation_emission.py` | standalone CLI/test surfaces | ledger and external evidence protocol |

## Shared Utilities

| Utility | File:line | Used by |
|---|---|---|
| `generate_concern_id()` | `adversaries.py:1535` | attack generation, core types, medals |
| `normalize_verdict()` | `gauntlet/core_types.py:72` | evaluation/adjudication/final boss |
| `TokenTracker` | `token_tracking.py:19` | model workers and output reporting |
| `validate_tmr_record()` | `tmr_schema.py:377` | compiler/parser/promotion/tests |
| `exit_code_for_outcome()` | `gate_result.py:87` | gate callers |
| `exit_code_for_status()` | `validation_emission.py:186` | validation Envelope |

## External Dependencies

| Package/system | Used for | Key usage sites |
|---|---|---|
| `litellm` | hosted model calls | `models.py`, `gauntlet/model_dispatch.py` |
| `filelock` | file-state synchronization | `gauntlet/persistence.py:74`, `validation_emission.py:959`, `provenance_journal.py:581` |
| `pydantic` | strict TMR/gate contracts | `tmr_schema.py:88`, `gate_result.py:54` |
| Codex/Gemini/Claude/Antigravity CLIs | alternate model transports | `models.py:298-688` |
| Telegram Bot API | human replies/notifications | `telegram_bot.py:47-136`, `pipeline_notifications.py:44` |

## Config Sources

| Config | Source | Accessed by |
|---|---|---|
| provider API-key names | process environment | `providers.py:16,299-340`, `gauntlet/model_dispatch.py:160-301` |
| global provider config | `~/.claude/adversarial-spec/config.json` | `providers.py:22-25,125-142` |
| named profiles | `~/.config/adversarial-spec/profiles/` | `providers.py:22-25,225-250` |
| compatibility config | project `pyproject.toml` | `pre_gauntlet/orchestrator.py:254-293` |
| hook config | `.claude/hooks/hook_config.json` plus resolved user/project config | `.claude/hooks/_resolve_config.py:39`, hook modules |
