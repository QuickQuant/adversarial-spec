# Component: Emission Toolchain

> Added 2026-06-11 (incremental f198887). Owner file: skills/adversarial-spec/scripts/mini_spec_emission.py

| | |
|---|---|
| Entry | `emit_fizzy_plan()` (:355), `self_check_plan()` (:411), `altitude_spec_shape()` (:99) |
| Purpose | Doc-driven process, code-checked shapes: emit Phase-7 execution plans in the fizzy v3 plan contract and offline-mirror the live altitude validation |
| Key files | mini_spec_emission.py (stdlib-only) |
| Depends on | nothing internal (deliberately standalone) |
| Used by | debate.py Phase-7 flows; conductor LLM during execution planning |

## Data Flow
IN: altitude tree dict (system→subsystem→component nodes) + session metadata → PROCESS: shape validation per ALTITUDE_OBLIGATIONS, requirement lint (advisory, shall/will/should tiers), artifact writes with 12-char sha256 plan_hash → OUT: fizzy-plan.json (PLAN_SCHEMA_VERSION=3) + spec/verification artifacts + self-check verdict {valid, issues[{code, task_id}]}.

## Contracts
- PLAN_SCHEMA_VERSION=3 must equal fizzy-pipeline-mcp V4_PLAN_SCHEMA_VERSION.
- ALTITUDE_OBLIGATIONS: component→{component_verification}; subsystem adds subsystem_verification; system adds system_verification. v4 is VERIFICATION-ONLY — no system_validation binding (the validation-leg spec on card 5604 adds validation_emission.py as a sibling following this exact pattern).
- REQUIREMENT_ID_RE `^[A-Z]+-R?\d+$` for machine-extractable requirement ids.
- self_check_plan reject codes mirror live pipeline_validate_plan: WRONG_SCHEMA_VERSION, NO_ROOT, MULTIPLE_ROOTS, ROOT_NOT_SYSTEM, INVALID_ALTITUDE, MISSING_LEVEL_VV, VV_ABOVE_ALTITUDE, VV_KIND_MISMATCH, ORPHAN_REALIZATION, UNDECOMPOSED_REQUIREMENT.

## Notes for LLMs
- Self-check is an offline preflight, not a substitute for the live dry-run.
- Lint is advisory-by-design (:148) — never blocks emission.
- Pure functions; no locking needed (writes go through atomic helpers when artifact_root supplied).
