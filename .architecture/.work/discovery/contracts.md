# Phase 1 Discovery: Contracts

> Architecture verified at `ef18c66`. This is a source-backed local fallback;
> delegated contract exploration timed out. Secret values are intentionally absent.

## Type contracts

- `ModelResponse` (`skills/adversarial-spec/scripts/models.py:141-151`): model name, text, token counts, cost, raw response/error metadata. Consumers are debate output and token accounting.
- Gauntlet chain (`gauntlet/core_types.py:83-232`): `Concern` -> `Evaluation` -> `Rebuttal` -> `FinalBossResult` -> `GauntletResult`; `normalize_verdict` centralizes accepted/dismissed/acknowledged/deferred normalization (`core_types.py:72`).
- `GauntletConfig`, `CheckpointMeta`, and `PhaseMetrics` (`core_types.py:424-482`) carry run defaults, integrity metadata, and phase telemetry.
- `TestMaturityRecord` (`tmr_schema.py:175-345`) is strict (`extra=forbid` through `StrictSchemaModel:88`) and carries TMR identity, maturity, data/liveness, binding, criticality, and run evidence.
- `GateResult`/`GateFinding` (`gate_result.py:54-123`) normalize gate outcomes and exit/MCP mappings; non-overridable outcomes are `schema_error`, `setup_error`, `orch_error` (`gate_result.py:40`).
- `Envelope` (`validation_emission.py:200-220`) is the validation CLI wire format; statuses are `ok`, `issues`, `reprompt`, `error` and process exit mapping is at `validation_emission.py:186-198`.
- `Phase8PromotionReport`/`PromotionRequest`/`RunExecution` (`phase8_promotion.py:15-72`) define the Phase 8 promotion gate and evidence payload.

## Boundary field contracts

BOUNDARY_FIELD_CONTRACTS:
  - boundary: validation-cli-stdout
    producer: skills/adversarial-spec/scripts/validation_emission.py:200-220,3423-3428
    adapters: none (direct stdout)
    consumer: shell/MCP/automation caller
    sink: process exit code and caller-owned artifact handling
    fields:
      - field: status
        emitted: always for successful command dispatch and handled validation errors
        adapter_forwards: n/a
        consumer_accepts: yes; status is one of ok/issues/reprompt/error
        persistence: not persisted by the CLI itself
        absent_means: malformed/non-envelope stdout; caller must treat as execution failure
        authority: validation_emission handler
        evidence: [validation_emission.py:51-67,186-220,3418-3428]
        verification: verified
      - field: issues
        emitted: conditional when validation finds defects or command fails
        adapter_forwards: n/a
        consumer_accepts: yes; list of issue objects
        persistence: caller decides whether to retain; ledger changes are separate
        absent_means: no reported issue list; not equivalent to a successful ledger mutation unless status=ok
        authority: validation handler
        evidence: [validation_emission.py:194-220]
        verification: verified
      - field: data
        emitted: conditional command-specific payload
        adapter_forwards: n/a
        consumer_accepts: command-specific
        persistence: may identify written artifact, ledger, digest, or report
        absent_means: command has no data payload; inspect status/issues
        authority: command handler
        evidence: [validation_emission.py:200-220,688-715,1528-1550,2888-2908]
        verification: verified

  - boundary: hook-stdio
    producer: Claude Code hook runner
    adapters: codex_pretool_combined.py:18-65 and configured sub-hooks
    consumer: Claude Code hook protocol
    sink: tool allow/deny/warn decision and optional systemMessage
    fields:
      - field: decision
        emitted: conditional; deny-capable sub-hooks print a JSON decision, while the combined adapter uses process exit 0 as allow/no-output
        adapter_forwards: yes for deny JSON; allow is represented by exit code rather than a field
        consumer_accepts: yes through Claude Code hook protocol
        persistence: not durable; notification/activity hooks may write side logs
        absent_means: allow/no-op for the combined safety hook when process exit is 0; it must not be inferred as a pipeline transition
        authority: Claude Code hook contract plus sub-hook exit/JSON behavior
        evidence: [codex_pretool_combined.py:26-72, fizzy_payload_guard.py:51-86, dispatch_check.py:86-158]
        verification: verified
      - field: systemMessage
        emitted: conditional by pipeline/coordination hooks
        adapter_forwards: yes when generated
        consumer_accepts: yes if hook protocol accepts message
        persistence: transient; notifications may also append dispatch logs
        absent_means: no operator-facing message, not necessarily no hook action
        authority: hook implementation
        evidence: [pipeline_continue.py:70-121, pipeline_idle_retry.py:73-159, pipeline_notifications.py:392-440]
        verification: verified

  - boundary: tmr-registry-prose-view
    producer: `tmr_compile_step.compile_tmr_records` and `write_confirmed_registry` (`tmr_compile_step.py:64-156`)
    adapters: `render_prose_view` (`tmr_compile_step.py:139`)
    consumer: `TmrParser`/`validate_tmr_record` (`tmr_parser.py:21`, `tmr_schema.py:377`)
    sink: local `tmr-registry.json` and derived `tests-pseudo.md`
    fields:
      - field: tmr_uid
        emitted: always for confirmed registry records; minted when candidate omits it
        adapter_forwards: yes
        consumer_accepts: required identity field
        persistence: authoritative in registry; prose is derived
        absent_means: candidate needs ULID allocation; absence in a confirmed record is schema-invalid
        authority: registry/compiler
        evidence: [tmr_compile_step.py:158-170,224-249, tmr_schema.py:175-345]
        verification: verified
      - field: maturity/data_strategy/live_or_induced/run_evidence
        emitted: based on candidate and evidence fields
        adapter_forwards: yes through JSON registry; prose view may summarize rather than retain all fields
        consumer_accepts: strict schema validation
        persistence: registry preserves structured values; prose view is non-authoritative
        absent_means: field-specific schema/default semantics; validation rejects required omissions
        authority: TMR schema/registry
        evidence: [tmr_schema.py:175-345, tmr_compile_step.py:64-156]
        verification: verified

  - boundary: gauntlet-check-gate
    producer: `gauntlet_check_cli.main` (`gauntlet_check_cli.py:27`)
    adapters: stdout JSON or MCP caller
    consumer: pipeline gate/CLI caller
    sink: process exit code and `GateResult` envelope
    fields:
      - field: outcome
        emitted: always on handled gate result
        adapter_forwards: yes via `to_envelope`
        consumer_accepts: normalized gate outcome vocabulary
        persistence: caller-owned logs/evidence
        absent_means: invalid gate response; no pass should be inferred
        authority: gate_result model
        evidence: [gate_result.py:54-123, gauntlet_check_cli.py:264-295]
        verification: verified
      - field: findings
        emitted: conditional when gate detects issues
        adapter_forwards: yes
        consumer_accepts: list of structured GateFinding objects
        persistence: caller-owned
        absent_means: no findings only when outcome itself is pass/warn with no details; inspect outcome
        authority: gate implementation
        evidence: [gate_result.py:43-85, gauntlet_check_cli.py:264-295]
        verification: verified

## File and configuration contracts

- Gauntlet checkpoint envelope: `_meta` schema/spec/config/data hashes plus `data`; serialization and validation are centralized in `persistence.py:79-137` and `281-333`.
- Provider config precedence: environment availability/model constants, global config path, then named profile path (`providers.py:22-25`, `125-250`).
- Hook configuration is resolved from project root/user config by `_resolve_config.resolve_config` (`.claude/hooks/_resolve_config.py:39`).
- File writes in validation/provenance are atomic and lock-protected; absence of a lock is a defect candidate only where the current source demonstrates concurrent shared writes (filtering stats append at `phase_3_filtering.py:217-233`).
