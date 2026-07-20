# Component: Execution Planner Concern Parsing

> Derived from: `execution_planner/gauntlet_concerns.py`, `skills/adversarial-spec/scripts/dependency_semantics.py` | Verified at: `ef18c66`
> If any derived-from file changed since `ef18c66`, trust source over this doc.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Parse gauntlet concerns for plan linkage and report dependency semantics |
| Entry | `GauntletConcernParser` at `execution_planner/gauntlet_concerns.py:111` |
| Key files | `execution_planner/gauntlet_concerns.py`, `dependency_semantics.py` |
| Depends on | Gauntlet report shapes, plan JSON |
| Used by | planning/plan evaluation |
| Runtime status | partial |
| Architecture status | active_secondary |

## What This Component Does

`GauntletConcernParser` parses gauntlet output into linked concern objects. `dependency_semantics` reads execution plans and reports graph/ordering issues. Neither executes gauntlet phases or advances cards.

## Contracts

| Contract | Purpose | Owner | Consumed By |
|---|---|---|---|
| `GauntletConcern`/`LinkedConcern` | preserve concern identity and task link | `gauntlet_concerns.py:30-78` | plan generation |
| dependency report | structured graph analysis | `dependency_semantics.py:25-82` | plan review |

## Invariants

- Concern IDs remain source identifiers; parser does not invent unrelated semantic IDs (`gauntlet_concerns.py:111-302`).
- Dependency analysis is read-only and emits a versioned report (`dependency_semantics.py:25,570`).

## Integration Points

**Called by:** execution/planning workflow; not used by gauntlet execution.

## Active vs Target

- **Active consumers:** secondary plan tooling.
- **Target architecture:** align plan concern links with the architecture/TMR corpus.

## LLM Notes

- This component is not the pipeline task system; it only parses/analyzes plan data.
