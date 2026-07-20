# Component: TMR and Evidence Toolchain

> Derived from: `skills/adversarial-spec/scripts/tmr_schema.py`, `tmr_parser.py`, `tmr_compile_step.py`, `phase8_promotion.py`, `tcov_liveness.py`, `criticality_classifier.py`, `spine_coverage_checker.py` | Verified at: `ef18c66`
> If any derived-from file changed since `ef18c66`, trust source over this doc.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Define, compile, validate, classify, and promote Test Maturity Records |
| Entry | `compile_tmr_records()` at `tmr_compile_step.py:64` |
| Key files | `tmr_schema.py`, `tmr_compile_step.py`, `phase8_promotion.py`, liveness/classifier modules |
| Depends on | Pydantic, JSON/hashlib, validation/provenance artifacts |
| Used by | Phase 8, guardrails, tests, validation emission |
| Runtime status | implemented |
| Architecture status | active_primary |

## What This Component Does

This is the schema-first test-evidence layer. It validates strict TMR records, keeps stable ULID identity, calculates maturity/data/liveness/criticality coordinates, checks happy-path spine coverage, and evaluates whether critical records have enough evidence to close implementation work.

## Contracts

### Boundary Field Contracts

Chain: candidates → compiler → `tmr-registry.json` → parser/promotion.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `tmr_uid` | always after compile | yes | strict identity | required registry | compile mints missing candidate identity; confirmed absence invalid | compiler/schema | `tmr_compile_step.py:158-170`, `tmr_schema.py:175-377` | verified |
| `maturity` | always for valid record | yes | `nl`/`acceptance`/`concrete` | required | schema error; no maturity inference | schema | `tmr_schema.py:28-30,175-345` | verified |
| `live_or_induced` | conditional for evidence-sensitive records | yes | enumerated technique | required when applicable | liveness not proven | schema/promotion | `tmr_schema.py:38-50,124-174`, `phase8_promotion.py:243-259` | verified |
| `run_evidence` | conditional by verification mode | yes | strict evidence union | required for concrete/critical paths as configured | promotion may block | schema/promotion | `tmr_schema.py:124-174`, `phase8_promotion.py:162-243` | verified |
| `spine`/`spine_of` | conditional designation | yes | coverage checker | registry | no happy-path spine designation; checker may report coverage gap | coverage checker | `spine_coverage_checker.py:27-105` | verified |

### Type Contracts

| Contract | Purpose | Owner | Consumed By |
|---|---|---|---|
| `TestMaturityRecord` | strict TMR schema | `tmr_schema.py:175-345` | parser/compiler/promotion |
| `SchemaValidationError` | named schema failure | `tmr_schema.py:347-377` | parser/CLI/tests |
| `TmrCompileResult` | compile records/diffs | `tmr_compile_step.py:47-62` | compiler callers |
| `Phase8PromotionReport` | close/promotion result | `phase8_promotion.py:62-72` | Phase 8 workflow |

## Invariants

- `StrictSchemaModel` forbids extra fields, so schema changes must be versioned and copied schemas checked (`tmr_schema.py:88`, `430-481`).
- The registry is authoritative; the prose view is derived by `render_prose_view` (`tmr_compile_step.py:139`).
- TMR identity is stable across updates; diffs are keyed by `tmr_uid` (`tmr_compile_step.py:224-249`).
- Critical/spine real-data records cannot close from mock-only or non-live evidence (`phase8_promotion.py:243-271`).

## Data Flow

```text
IN: candidate prose/JSON + existing registry + run evidence
    └─> compile -> validate -> classify/coverage -> promotion
PROCESS: strict coercion, hash/identity, schema validation, liveness checks
OUT: TMR registry, derived prose, promotion report, coverage findings
```

## Key Functions

| Function | Purpose | Location |
|---|---|---|
| `validate_tmr_record()` | strict schema validation | `tmr_schema.py:377` |
| `lint_tmr_schema_copies()` | detect stale copies | `tmr_schema.py:430` |
| `compile_tmr_records()` | candidate-to-registry compiler | `tmr_compile_step.py:64` |
| `write_confirmed_registry()` | persist registry | `tmr_compile_step.py:123` |
| `check_spine_coverage()` | designation coverage rule | `spine_coverage_checker.py:96` |
| `evaluate_phase8_close()` | promotion gate | `phase8_promotion.py:162` |

## Error Handling

- Strict schema errors are typed and should stop compilation rather than coerce unknown fields (`tmr_schema.py:347-377`).
- Coverage/liveness/promotion gaps become structured issues, not silent downgrades (`phase8_promotion.py:162-271`).
- Schema-copy drift is an explicit lint result (`tmr_schema.py:430-481`).

## Concurrency Concerns

| Resource | Callers | Synchronization | Risk |
|---|---|---|---|
| confirmed TMR registry | compiler/provenance/promotion | provenance layer provides multi-file locks; compiler direct write requires caller discipline | concurrent compile and lineage updates can conflict |

## Configuration

| Config | Source | Default | Precedence |
|---|---|---|---|
| schema contract | `CONTRACT_VERSION`, constants | `tmr.v1` | code/schema version |
| maturity/data/liveness values | module enumerations | strict sets | record values must be in enumerations |
| promotion evidence | record fields + Phase 8 rules | block when required proof absent | stricter critical/spine rules override general close |

## Integration Points

**Calls out to:** validation emission for run evidence; provenance journal for lineage; guardrail/orchestration for structured checks.

**Called by:** Phase 8 promotion, parser/compiler callers, tests.

## Active vs Target

- **Active consumers:** validation-leg and Phase 8 code/tests.
- **Legacy consumers:** Markdown pseudo-test views and older manifests remain read-only/derived.
- **Target architecture:** one registry and schema authority across planning, execution, and validation.

## LLM Notes

- Do not patch `tests-pseudo.md` to fix a TMR field; update the registry/compiler/schema path and regenerate the view.
