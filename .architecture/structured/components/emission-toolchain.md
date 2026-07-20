# Component: Plan and Validation Emission Toolchain

> Derived from: `skills/adversarial-spec/scripts/mini_spec_emission.py`, `dependency_semantics.py`, `validation_emission.py`, `tmr_compile_step.py` | Verified at: `ef18c66`
> If any derived-from file changed since `ef18c66`, trust source over this doc.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Emit/validate plan artifacts and bridge prose/registry/evidence formats |
| Entry | `emit_fizzy_plan()` in `mini_spec_emission.py`; validation CLI `main()` at `validation_emission.py:3423` |
| Key files | `mini_spec_emission.py`, `validation_emission.py`, `tmr_compile_step.py` |
| Depends on | JSON schemas, TMR/compiler, Fizzy plan contract |
| Used by | execution planning and validation-leg workflow |
| Runtime status | implemented |
| Architecture status | active_primary |

## Contracts

| Contract | Purpose | Owner | Consumed By |
|---|---|---|---|
| Fizzy plan schema | card/task emission shape | `mini_spec_emission.py` | pipeline loader/self-check |
| validation `Envelope` | stable CLI result shape | `validation_emission.py:200-220` | automation |
| TMR registry | authoritative test records | `tmr_compile_step.py:64-156` | parser/promotion |

## Invariants

- Offline self-check mirrors live plan validation reject codes (`mini_spec_emission.py` functions and constants).
- Structured registries are authoritative over prose views.
- Emission must preserve dependency/acceptance fields because downstream pipeline loading validates them.

## Data Flow

```text
IN: roadmap/prose/candidate records
PROCESS: normalize -> schema/self-check -> emit plan/registry -> derived views
OUT: Fizzy plan JSON, TMR registry, validation Envelope
```

## Integration Points

**Calls out to:** Fizzy pipeline contract and local schema/test fixtures.

**Called by:** planning, validation, and test tooling.

## Active vs Target

- **Active consumers:** mini-spec and validation-leg paths.
- **Target architecture:** one canonical compilation/validation chain with explicit external schemas.

## LLM Notes

- Emission is a boundary adapter; a locally valid artifact can still fail if Fizzy’s external contract differs. Keep the self-check and contract version synchronized.
