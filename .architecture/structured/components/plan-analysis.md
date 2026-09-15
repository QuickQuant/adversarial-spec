# Component: Plan Analysis

> Derived from: `execution_planner/`, `skills/adversarial-spec/scripts/dependency_semantics.py`, `gauntlet_concerns.py` | Verified at: `2433efa`
> If a derived-from file changed since `2433efa`, trust source over this document.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Parse gauntlet concerns and compute plan dependency semantics. |
| Entry | `dependency_semantics.main()` at `dependency_semantics.py:525` |
| Depends on | plan JSON, concern parser, adversary ID helper |
| Used by | execution planning/gate review |
| Runtime / architecture | partial / active_secondary |

## Contracts

### Type Contracts

| Contract | Purpose | Owner | Consumed By |
|---|---|---|---|
| concern parser output | parsed concern IDs/categories | `execution_planner/gauntlet_concerns.py` | `load_concerns_for_spec()` |
| dependency report | graph issues/profiles | `dependency_semantics.py:35-82` | CLI stdout |

## Invariants

- The CLI reads plan JSON and writes analysis JSON; it is a read-only analysis surface (`dependency_semantics.py:525`).
- Concern ID generation is shared with adversary code through an injected scripts path, a fragile packaging coupling (`gauntlet_concerns.py:17-26`).

## Data Flow

`plan JSON -> task/edge normalization -> dependency profiles/issues -> stdout JSON`.

## Key Functions

| Function | Purpose | Location |
|---|---|---|
| `analyze_plan()` | graph semantics | `dependency_semantics.py:82` |
| `main()` | CLI JSON envelope/exit | `dependency_semantics.py:525` |
| `load_concerns_for_spec()` | discover parsed concern data | `execution_planner/__init__.py:14` |

## LLM Notes

- This is not the old full execution planner; its package surface is deliberately narrower and should be treated as partial architecture.
