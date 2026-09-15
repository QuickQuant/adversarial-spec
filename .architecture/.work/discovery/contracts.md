# Discovery: Boundary Contracts

> Full nuke run. Original broad contracts explorer was manually interrupted without durable progress; a bounded replacement verified the following three boundaries source-first.

BOUNDARY_FIELD_CONTRACTS:

## validation-cli-envelope

Producer: `validation_emission.py:200-214,3423-3459` -> stdout JSON -> external caller.

| Field | Emitted | Consumer accepts | Persist | Absent means | Authority | Evidence |
|---|---|---|---|---|---|---|
| `status` | always | external caller | JSON output | not representable for `Envelope` | handler/help/error path | `validation_emission.py:203,208-214,3425-3459` |
| `code` | always; null by default | external caller | JSON output | unset is `null`, never omitted | `Envelope.code` | `validation_emission.py:204,208-214` |
| `issues` | always; `[]` default | external caller | JSON output | unspecified means empty list | `Envelope.issues` | `validation_emission.py:205,208-214` |
| `data` | always; `{}` default | external caller | JSON output | unspecified means empty object | `Envelope.data` | `validation_emission.py:206,208-214` |

## gauntlet-checkpoint-envelope

Producer: `persistence.save_checkpoint:560-583` -> locked atomic writer `124-142` -> `_load_checkpoint_envelope:281-325` -> phase resume.

| Field | Emitted | Consumer accepts | Persist | Absent means | Authority | Evidence |
|---|---|---|---|---|---|---|
| `_meta` | always | required except explicit plain-JSON compatibility mode | JSON envelope | ordinary resume ignores invalid envelope | producer metadata | `persistence.py:579-583,293-306` |
| `_meta.schema_version` | always | must equal current schema constant | meta | reject/ignore checkpoint | producer constant plus consumer check | `persistence.py:571-580,308-310` |
| `_meta.spec_hash` | always | must equal requested spec hash | meta | reject/ignore checkpoint | caller supplies expected identity | `persistence.py:563-574,312-314` |
| `_meta.config_hash` | always | checked when expected hash supplied | meta | reject when expected; otherwise unchecked | caller/consumer config | `persistence.py:563-575,316-318` |
| `_meta.phase` | always | no validation in inspected resume path | meta | no resume rejection from absence in inspected path | producer provenance | `persistence.py:568-581,303-325` |
| `_meta.data_hash` | always | recomputed when truthy | meta | missing/falsy skips integrity check | producer claim, consumer verifier | `persistence.py:570-581,320-323` |
| `data` | always | required envelope payload | JSON envelope | invalid envelope ignored; plain compatibility returns whole payload | checkpoint caller | `persistence.py:563,570-583,293-301` |

## hook-session-activity-log

Producer: `.claude/hooks/session_activity_logger.py:55-96` -> JSONL -> external reader.

| Field | Emitted | Consumer accepts | Persist | Absent means | Authority | Evidence |
|---|---|---|---|---|---|---|
| `ts` | every written line | external reader | append JSONL | none once entry built | hook clock | `session_activity_logger.py:76-83,92-95` |
| `session_id`, `event` | every written line | external reader | append JSONL | no entry is written when empty | hook input | `session_activity_logger.py:61-66,78-83` |
| `project` | every written line | external reader | append JSONL | no entry when root/.claude absent | discovered root | `session_activity_logger.py:68-83` |
| `source`, `model` | SessionStart only | external reader | SessionStart JSONL | omitted outside start; empty string means missing start input | hook input + event gate | `session_activity_logger.py:85-88,92-95` |
| `reason` | SessionEnd only | external reader | SessionEnd JSONL | omitted outside end; empty string means missing end input | hook input + event gate | `session_activity_logger.py:89-95` |

TYPE_CONTRACTS:
- `Envelope` — `validation_emission.py:200-220`; stdout status/code/issues/data boundary.
- `CheckpointMeta` envelope shape — `gauntlet/persistence.py:560-583`; resume integrity metadata.
- `Concern`, `Evaluation`, `FinalBossResult`, `GauntletResult` — `gauntlet/core_types.py:83-232`; cross-phase gauntlet domain chain.
- `TestMaturityRecord` — `tmr_schema.py:175-377`; strict registry record.

## Additional verified boundaries from durable broad scan

The full liveness/progress record is `.architecture/.work/discovery-progress/broad-contracts.md`. All rows below were verified by the re-launched broad scan.

### litellm-response-normalization

Producer `gauntlet/model_dispatch.py:138` -> dispatcher `125,139` -> Phase 1 consumer `phase_1_attacks.py:296` -> normalized tuple/raw artifact.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence |
|---|---|---|---|---|---|---|---|
| `choices[0].message.content` | provider-dependent | yes | JSON concern object or numbered-list fallback | derived | dispatcher raises before tuple | producer | `model_dispatch.py:138-139`, `phase_1_attacks.py:287,296` |
| `usage.prompt_tokens` | provider-dependent | yes | normalized int for tracker | ignored | normalized to `0` | adapter | `model_dispatch.py:140,142` |
| `usage.completion_tokens` | provider-dependent | yes | normalized int for tracker | ignored | normalized to `0` | adapter | `model_dispatch.py:141-142` |

### telegram-bot-http-roundtrip

Producer `telegram_bot.py:89,197` -> URL adapter `47,63,70` -> Telegram API / local poll consumer `94,203`.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence |
|---|---|---|---|---|---|---|---|
| `chat_id`, `text`, `parse_mode` | always for send call | yes | URL-encoded request | ignored | no local omission path | producer | `telegram_bot.py:89,92,63-65` |
| `result.ok` | response-dependent | yes | `send_message` returns boolean | ignored | send is unsuccessful | producer | `telegram_bot.py:70,94` |
| `result[].update_id` | update-dependent | yes | poll advances offset | ignored | no offset advance | producer | `telegram_bot.py:202,205-206` |
| `result[].message.chat.id`, `.text` | update-dependent | yes | matching chat + nonempty text becomes feedback | ignored | empty/default values are ignored | producer | `telegram_bot.py:207-211` |

### fizzy-pretool-guard-decision

Hook host (`.claude/settings.json:107`) -> `fizzy_payload_guard.py:86` -> hook stdout / optional decision log.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence |
|---|---|---|---|---|---|---|---|
| `tool_name` | host-dependent | yes | selects guard category | ignored | no named guard rule; allow | producer | `fizzy_payload_guard.py:88,92,109,120` |
| `tool_input` | host-dependent | yes | defaults to `{}` for all guard arguments | ignored | no scope/caller/metadata/content | producer | `fizzy_payload_guard.py:93,110,127` |
| `metadata.intent`, `process_failure_path` | override-only | yes | requires sufficient intent and fresh note | derived | override unavailable; deny rules remain | producer | `fizzy_payload_guard.py:60,64,70,102` |
| `decision`, `reason` | denial-only | n/a | hook host reads block JSON | ignored | exit 0 without decision permits tool action | adapter | `fizzy_payload_guard.py:51-53,147` |

### debate-session-state-resume

`debate.py:1068` -> `session.py:46,53` -> `debate.py:1040` -> `~/.config/adversarial-spec/sessions/{id}.json`.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence |
|---|---|---|---|---|---|---|---|
| `session_id` | always | yes | constrained path must exist | required | cannot select/construct resume state | producer | `session.py:34,50,58,61` |
| `spec` | always | yes | replaces stdin spec | required | dataclass load fails | producer | `session.py:35,53`, `debate.py:1047` |
| `round`, `doc_type`, `models` | always | yes | overwrite CLI run state | required | dataclass load fails | producer | `session.py:36-38`, `debate.py:1048,1050` |
| `focus`, `persona`, `preserve_intent` | always/defaulted | yes | nonempty/true values apply | preserve-on-absent | defaults None/None/false | producer | `session.py:39,41`, `debate.py:1051,1055` |

### tmr-registry-to-spine-gate

Compiler `tmr_compile_step.py:123` -> parser `tmr_parser.py:43` -> gate `gauntlet_check_cli.py:156` -> registry JSON/gate result.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence |
|---|---|---|---|---|---|---|---|
| `records[]` | always on confirmed write | yes | JSON array/objects; no duplicate keys/null-like strings | required | schema-error gate path | adapter | `tmr_compile_step.py:136`, `tmr_parser.py:43-47`, `gauntlet_check_cli.py:154` |
| `tmr_uid` | always | yes | unique string identity | required | strict schema rejection | adapter | `tmr_compile_step.py:95,103`, `tmr_parser.py:71`, `tmr_schema.py:178` |
| `status`, `spine`, `user_story` | always | yes | only active + spine + scalar story counts | required | schema rejects before coverage | producer | `tmr_schema.py:181,192,212`, `spine_coverage_checker.py:60` |
| `tombstoned_at`, `run_evidence` | conditional | yes | status/maturity invariants enforce valid values | preserve-on-absent | allowed only in stated active/exempt modes | consumer | `tmr_schema.py:225,287,290,317,327` |

### gauntlet-check-cli-json-envelope

Gate `gauntlet_check_cli.py:181` -> `gate_result.py:83` -> parent `debate.py:1578` -> child stdout/exit status.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence |
|---|---|---|---|---|---|---|---|
| `outcome` | always in JSON mode | yes | parent relies on process exit equivalent | ignored | decoded object defaults empty; exit remains authority | producer | `gate_result.py:63,83`, `debate.py:1578,1596` |
| `findings[]` | always | yes | parent defaults missing list to `[]` and renders entries | ignored | no finding diagnostics | producer | `gate_result.py:66`, `debate.py:1582,1589` |
| `findings[].code`, `.message` | per finding | yes | defaults in parent display | ignored | `<unknown>` / `<no message>` diagnostic | producer | `gate_result.py:48-49`, `debate.py:1591` |
| `override_eligible` | always | yes | parent does not inspect it | ignored | Pydantic default false | consumer | `gate_result.py:67,69,83` |

### validation-cli-stdout-envelope

`validation_emission.py:3423` -> `Envelope.as_dict:208` / `_emit:3418` -> execution conductor `phases/07-execution.md:937` -> stdout/exit status.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence |
|---|---|---|---|---|---|---|---|
| `status` | always | yes | advance only when `ok` and zero issues | ignored | invalid discriminator | producer | `validation_emission.py:203,209,217`, `phases/07-execution.md:937` |
| `code` | always | yes | remediation code for non-ok state | ignored | null means no stable code | producer | `validation_emission.py:204,211`, `phases/07-execution.md:899` |
| `issues[]` | always | yes | success requires empty list | ignored | no reported validation issue | producer | `validation_emission.py:194,205,212`, `phases/07-execution.md:937` |
| `data` | always | yes | subcommand-specific result | ignored | empty object means no additional payload | producer | `validation_emission.py:206,213`, `phases/07-execution.md:918` |
