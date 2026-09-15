# Cross References

> Calls, data paths, contracts and configuration. Generated: 2026-07-20T14:44:38-05:00 | Git: `2433efa`.

## Call Graphs

### Debate/session

```
main() (scripts/debate.py:1623)
  ├── enforce_pipeline_card_gate()
  ├── load_or_resume_session()
  ├── validate_models_before_run()/preflight_models()
  ├── run_critique() -> call_models_parallel()
  └── handle_gauntlet() -> gauntlet.run_gauntlet()
```

### Gauntlet

```
run_gauntlet() (gauntlet/orchestrator.py:205)
  ├── phase_1_attacks.generate_attacks() -> model_dispatch.call_model()
  ├── phase_3_filtering/filter + clustering
  ├── phase_4_evaluation.evaluate_concerns_multi_model()
  ├── phase_5_rebuttals / phase_6_adjudication / phase_7_final_boss
  └── persistence.save_checkpoint()/save_gauntlet_run()
```

### Validation/TMR

```
validation_emission.main() (validation_emission.py:3423)
  ├── HANDLERS[subcommand]
  ├── mutate_ledger() -> locked atomic JSON
  └── _emit(Envelope) -> stdout/exit status

compile_tmr_records() (tmr_compile_step.py:64)
  └── TmrParser.parse_file() -> SpineCoverageChecker.check() -> gauntlet_check_cli
```

## Data Path Summary

| Path | Source | Main transforms | Sink |
|---|---|---|---|
| Debate critique | stdin/session | model prompt/adapters/aggregate | stdout + session/partials |
| Gauntlet run | spec CLI | phases 1–7, hash/checkpoint | run reports/checkpoints |
| Validation close | ConOps/ledger/evidence | locked mutation/digest/judgment | system-validation artifact |
| TMR gate | candidates/registry | compile/strict parse/spine count | gate JSON/exit |
| Hooks | hook stdin JSON | guard/notification normalization | block decision or JSONL |

## Boundary Field Contracts

### gauntlet-checkpoint-envelope

Chain: `gauntlet/orchestrator.py:394` -> `persistence.save_checkpoint:560` -> atomic writer `:124` -> loader `:281` -> phase resume `:706`.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `_meta` | always | yes | dict with required metadata | required | invalid checkpoint ignored | producer | `persistence.py:571,579,296` | verified |
| `schema_version` | always | yes | exact current constant | required | unsupported schema ignored | producer | `persistence.py:45,572,308` | verified |
| `spec_hash`, `config_hash` | always | yes | current expected hashes | required | mismatched run/config not resumed | producer | `persistence.py:573-574,312,316` | verified |
| `data_hash` | always | yes | canonical data hash when truthy | required | integrity comparison skipped for legacy-like metadata | adapter | `persistence.py:106,577,320` | verified |
| `data` | always | yes | phase payload | required | invalid checkpoint ignored | producer | `persistence.py:581,325,712` | verified |

### litellm-response-normalization

Chain: provider response -> `model_dispatch.py:125,139` -> Phase 1 parser `phase_1_attacks.py:296` -> normalized tuple/raw artifact.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `choices[0].message.content` | provider-dependent | yes | JSON concerns or numbered-list fallback | derived | dispatcher raises | producer | `model_dispatch.py:138-139`, `phase_1_attacks.py:287,296` | verified |
| `usage.prompt_tokens` | provider-dependent | yes | normalized tracker count | ignored | `0` | adapter | `model_dispatch.py:140,142` | verified |
| `usage.completion_tokens` | provider-dependent | yes | normalized tracker count | ignored | `0` | adapter | `model_dispatch.py:141-142` | verified |

### telegram-bot-http-roundtrip

Chain: `telegram_bot.py:89,197` -> URL adapter `:47,63,70` -> Telegram API -> poll consumer `:94,203`.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `chat_id`, `text`, `parse_mode` | always for send | yes | URL encoded request | ignored | no local omission path | producer | `telegram_bot.py:89,92,63-65` | verified |
| `result.ok` | response-dependent | yes | returns bool | ignored | failed send | producer | `telegram_bot.py:70,94` | verified |
| `update_id` | update-dependent | yes | advances offset | ignored | no advance | producer | `telegram_bot.py:202,205-206` | verified |
| message chat/text | update-dependent | yes | configured chat + nonempty text | ignored | update ignored | producer | `telegram_bot.py:207-211` | verified |

### fizzy-pretool-guard-decision

Chain: hook host `.claude/settings.json:107` -> `fizzy_payload_guard.py:86` -> hook stdout/decision log.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `tool_name` | host-dependent | yes | selects guard rule | ignored | no named guard; allow | producer | `fizzy_payload_guard.py:88,92,109,120` | verified |
| `tool_input` | host-dependent | yes | guard args default `{}` | ignored | no scope/metadata | producer | `fizzy_payload_guard.py:93,110,127` | verified |
| override metadata | conditional | yes | intent + fresh note required | derived | ordinary deny remains | producer | `fizzy_payload_guard.py:60,64,70,102` | verified |
| `decision`, `reason` | denial-only | n/a | host consumes block JSON | ignored | exit with no decision permits action | adapter | `fizzy_payload_guard.py:51-53,147` | verified |

### debate-session-state-resume

Chain: `debate.py:1068` -> `session.py:46,53` -> `debate.py:1040` -> per-user session JSON.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `session_id` | always | yes | constrained existing path | required | no resume selection | producer | `session.py:34,50,58,61` | verified |
| `spec` | always | yes | replaces stdin | required | load fails | producer | `session.py:35,53`, `debate.py:1047` | verified |
| `round`, `doc_type`, `models` | always | yes | overwrite run state | required | load fails | producer | `session.py:36-38`, `debate.py:1048,1050` | verified |
| focus/persona/preserve intent | defaults | yes | nonempty/true values apply | preserve-on-absent | None/None/false defaults | producer | `session.py:39,41`, `debate.py:1051,1055` | verified |

### tmr-registry-to-spine-gate

Chain: compiler `tmr_compile_step.py:123` -> parser `tmr_parser.py:43` -> gate `gauntlet_check_cli.py:156` -> registry/gate result.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `records[]` | confirmed write | yes | strict JSON array/object parse | required | schema-error gate path | adapter | `tmr_compile_step.py:136`, `tmr_parser.py:43-47` | verified |
| `tmr_uid` | always | yes | unique string | required | schema reject | adapter | `tmr_compile_step.py:95,103`, `tmr_schema.py:178` | verified |
| status/spine/story | always | yes | active spine scalar story count | required | schema reject | producer | `tmr_schema.py:181,192,212`, `spine_coverage_checker.py:60` | verified |
| tombstone/evidence | conditional | yes | maturity/status invariants | preserve-on-absent | only active/exempt mode allowed | consumer | `tmr_schema.py:225,287,317,327` | verified |

### gauntlet-check-cli-json-envelope

Chain: `gauntlet_check_cli.py:181` -> `gate_result.py:83` -> `debate.py:1578` -> child stdout/exit.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `outcome` | always JSON mode | yes | exit status is equivalent parent authority | ignored | only exit status remains | producer | `gate_result.py:63,83`, `debate.py:1578,1596` | verified |
| `findings[]` | always | yes | missing defaults empty | ignored | no diagnostics | producer | `gate_result.py:66`, `debate.py:1582,1589` | verified |
| finding code/message | conditional | yes | parent uses display defaults | ignored | placeholder diagnostics | producer | `gate_result.py:48-49`, `debate.py:1591` | verified |
| `override_eligible` | always | yes | not read by parent | ignored | default false | consumer | `gate_result.py:67,69,83` | verified |

### validation-cli-stdout-envelope

Chain: `validation_emission.main:3423` -> `Envelope.as_dict:208` / `_emit:3418` -> execution conductor `phases/07-execution.md:937` -> stdout/exit.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `status` | always | yes | advance only `ok` + no issues | ignored | invalid discriminator | producer | `validation_emission.py:203,209,217`, `07-execution.md:937` | verified |
| `code` | always | yes | remediation code | ignored | no stable code | producer | `validation_emission.py:204,211`, `07-execution.md:899` | verified |
| `issues[]` | always | yes | success needs empty list | ignored | no validation issue | producer | `validation_emission.py:194,205,212` | verified |
| `data` | always | yes | subcommand payload | ignored | no extra payload | producer | `validation_emission.py:206,213`, `07-execution.md:918` | verified |

## Type Contracts

| Contract | Owner | Consumed by | Notes |
|---|---|---|---|
| `Concern`, `Evaluation`, `FinalBossResult`, `GauntletResult` | `gauntlet/core_types.py:83-232` | gauntlet phases/persistence/reporting | cross-phase chain |
| `Envelope` | `validation_emission.py:200-220` | conductor/external callers | exactly four serialized fields |
| `TestMaturityRecord` | `tmr_schema.py:175-377` | compiler/parser/spine/promotion | strict evidence/state invariants |
| `GateResult` | `gate_result.py:54-83` | gate CLI/debate subprocess parent | JSON + exit semantics |
| `SessionState` | `session.py:31-64` | debate resume/session listing | file-backed resume state |

## Hub Files

| File | Importers | Role |
|---|---:|---|
| `gauntlet/core_types.py` | 24 | central typed gauntlet contracts |
| `tmr_schema.py` | 16 | strict registry schema |
| `adversaries.py` | 15 | adversary identity/content |
| `gauntlet/model_dispatch.py` | 8 | provider model invocation |
| `token_tracking.py` | 8 | shared cost/token aggregate |
| `gauntlet/persistence.py` | 7 | artifact/resume substrate |

## Config Sources

Only names/locations are recorded: provider env/profile config (`providers.py:15-23,297-566`), rate flags (`gauntlet/model_dispatch.py:155-306`), Telegram names (`telegram_bot.py:36-44`), hook role/config resolution (`.claude/hooks/_resolve_config.py:9-71`), and consumer compatibility TOML (`pre_gauntlet/orchestrator.py:237-290`).
