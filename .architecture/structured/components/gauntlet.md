# Component: Gauntlet Pipeline

> Derived from: `skills/adversarial-spec/scripts/gauntlet/*.py`, `adversaries.py`, `models.py` | Verified at: `ef18c66`
> If any derived-from file changed since `ef18c66`, trust source over this doc.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Turn an agreed spec into adversarial concerns and a final verdict |
| Entry | `run_gauntlet()` at `gauntlet/orchestrator.py:205` |
| Key files | `orchestrator.py`, `core_types.py`, phase modules, `model_dispatch.py` |
| Depends on | Models/providers, adversaries/prompts, persistence |
| Used by | Debate Engine, standalone gauntlet CLI |
| Runtime status | implemented |
| Architecture status | active_primary |

## What This Component Does

The Gauntlet Pipeline executes the adversarial stress-test after a spec has been prepared. It generates concerns from named adversaries, synthesizes and clusters them, evaluates dispositions, allows rebuttals, adjudicates, and asks a final boss for an overall verdict.

## Contracts

### Type Contracts

| Contract | Purpose | Owner | Consumed By |
|---|---|---|---|
| `Concern` | adversary observation with stable ID | `core_types.py:83-98` | synthesis/filter/evaluation |
| `Evaluation` | model disposition and confidence | `core_types.py:99-113` | rebuttal/adjudication |
| `Rebuttal` | adversary response to dismissal | `core_types.py:114-122` | adjudication |
| `GauntletResult` | complete run output | `core_types.py:232-423` | persistence/reporting/CLI |
| `GauntletConfig` | run knobs and thresholds | `core_types.py:424-455` | orchestrator/phases |

### Boundary Field Contracts

Chain: spec → phase modules → persistence/reporting.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| concern ID | generated for each accepted concern | yes across phases | `Concern.id` and downstream maps | required in run artifacts | concern cannot be joined across phases | `generate_concern_id`/Concern | `adversaries.py:1535`, `core_types.py:83-98` | verified |
| verdict | final-boss/normalized disposition | yes | normalized outcome vocabulary | result/manifest | no overall verdict; run is incomplete | `normalize_verdict`/final boss | `core_types.py:47-81,207-232` | verified |
| phase metrics | emitted per phase | yes into result/manifest | reporting/persistence | manifest | missing metrics reduces observability, not concern semantics | orchestrator/persistence | `orchestrator.py:84-123`, `core_types.py:482` | verified |

## Invariants

- Every phase consumes typed objects from the previous phase; raw model text is parsed before it enters the typed chain (`phase_1_attacks.py:39-60`, `core_types.py:83-232`).
- Concern IDs are deterministic from adversary/text and are used for cross-run linking (`adversaries.py:1535`).
- A text response containing no parseable concerns is a fatal Phase 1 condition by design; raw response artifacts are retained for recovery (`phase_1_attacks.py:39-60`).
- Resume state must pass checkpoint schema/spec/config/data hash validation before a later phase runs (`persistence.py:281-333`).

## Data Flow

```text
IN: spec + GauntletConfig
    └─> orchestrator.run_gauntlet() (orchestrator.py:205)
PROCESS:
    ├─> adversary attacks
    ├─> synthesis/filter/clustering
    ├─> tiered evaluation/rebuttal/adjudication
    └─> final-boss verdict
OUT: GauntletResult + checkpoint/run/medal/report artifacts
     └─> persistence.py:469-629; reporting.py
```

## Key Functions

| Function | Purpose | Location |
|---|---|---|
| `run_gauntlet()` | phase orchestration/resume path | `orchestrator.py:205` |
| `generate_attacks()` | parallel adversary calls/parsing | `phase_1_attacks.py:323` |
| `filter_concerns_with_explanations()` | explanation matching/filter | `phase_3_filtering.py:130` |
| `evaluate_concerns_multi_model()` | tiered parallel evaluation | `phase_4_evaluation.py:118` |
| `normalize_verdict()` | canonical disposition normalization | `core_types.py:72` |
| `call_model()` | gauntlet-specific model selection/dispatch | `model_dispatch.py:64` |

## Common Patterns

- **Phase functions are data-transform stages:** orchestration owns sequencing; phase modules own transformations.
- **Parallel batches:** attacks, evaluations, and rebuttals use bounded ThreadPoolExecutor pools.
- **Integrity-aware resume:** persistence helpers are called at phase boundaries and preserve raw failures.

## Error Handling

- Known programming errors are isolated by `PROGRAMMING_BUGS` (`core_types.py:23`).
- Model parse errors retain raw responses and can abort a phase rather than silently fabricating concerns (`phase_1_attacks.py:39-60`).
- Checkpoint mismatches raise typed persistence errors (`persistence.py:281-333`).

## Concurrency Concerns

| Resource | Callers | Synchronization | Risk |
|---|---|---|---|
| phase worker pools | attack/evaluation/rebuttal functions | executor boundaries; result collection | provider rate limits and partial results must be handled consistently |
| shared stats files | filtering/orchestrator/medals | persistence FileLock, but filtering append lacks an obvious lock | concurrent runs can lose/update stats inconsistently (`phase_3_filtering.py:217-233`) |

## Configuration

| Config | Source | Default | Precedence |
|---|---|---|---|
| adversaries/prompts | module registries + approved prompt file | built-in/default | configured approved prompts/adversary selection |
| model tiers/rate limits | `model_dispatch.py:194-309` and env availability | defaults | explicit config/available model selection |
| checkpoint/resume | CLI and persistence paths | fresh run | explicit resume path/hash overrides |

## Integration Points

**Calls out to:** `models`/provider transports, `persistence`, adversary/prompt registries.

**Called by:** `debate.handle_gauntlet()` and `gauntlet.cli.main()`.

## Active vs Target

- **Active consumers:** Debate CLI and standalone `gauntlet` module.
- **Legacy consumers:** historical monolith artifacts are not active import targets.
- **Target architecture:** keep one typed phase pipeline with shared model/persistence boundaries.
- **Drift note:** two CLI surfaces and separate top-level/gauntlet model selection remain live.

## LLM Notes

- Internal gauntlet phase names (`phase_1_attacks` etc.) are not the eight adversarial-spec pipeline phases; qualify them in prose.
