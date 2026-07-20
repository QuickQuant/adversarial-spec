# Component: Plan Analysis and Execution Planner

> Derived from: `skills/adversarial-spec/scripts/dependency_semantics.py`, `execution_planner/gauntlet_concerns.py`, `adversarial-spec` phase references | Verified at: `ef18c66`
> If any derived-from file changed since `ef18c66`, trust source over this doc.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Inspect execution-plan dependency semantics and parse gauntlet concern reports |
| Entry | `analyze_plan()` at `dependency_semantics.py:82`; `GauntletConcernParser` at `execution_planner/gauntlet_concerns.py:111` |
| Key files | `dependency_semantics.py`, `execution_planner/gauntlet_concerns.py` |
| Depends on | JSON plan/report formats, gauntlet concern IDs |
| Used by | plan evaluation/execution workflow |
| Runtime status | partial |
| Architecture status | active_secondary |

## What This Component Does

`dependency_semantics` reads an execution plan and reports graph/ordering issues. `execution_planner.gauntlet_concerns` parses human/JSON gauntlet output into linked concern objects for planning. These are plan-side utilities, not the main debate or gauntlet execution engine.

## Contracts

### Boundary Field Contracts

Chain: plan JSON → analyzer → JSON report stdout.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| task list | required plan input | yes | mapping list | no | analyzer issue/error | plan document | `dependency_semantics.py:35-82,537-570` | verified |
| dependency edges | optional/derived | yes | known edge kinds | no | no declared edge; absence is not proof of no semantic dependency | plan/analyzer | `dependency_semantics.py:25-82` | verified |
| report schema version | always output | yes | versioned analyzer report | no | incompatible report | analyzer | `dependency_semantics.py:25,570` | verified |

## Invariants

- Dependency analysis is read-only and does not rewrite plan cards or source files (`dependency_semantics.py:525-575`).
- Gauntlet concern IDs are preserved when linking concern text to plan tasks (`execution_planner/gauntlet_concerns.py:111-302`).

## Data Flow

```text
IN: plan JSON / gauntlet report
PROCESS: parse -> normalize graph or concern records -> detect issues/link IDs
OUT: dependency report or linked concern objects
```

## Key Functions

| Function | Purpose | Location |
|---|---|---|
| `analyze_plan()` | graph/semantic analysis | `dependency_semantics.py:82` |
| `dependency_semantics.main()` | CLI I/O | `dependency_semantics.py:525` |
| `GauntletConcernParser.parse()` | report parsing | `execution_planner/gauntlet_concerns.py:111` |
| `load_concerns_for_spec()` | load linked report for spec | `execution_planner/gauntlet_concerns.py:302` |

## Error Handling

- Malformed plan fields become structured analyzer issues.
- Missing/ambiguous concern IDs are parser errors or unlinked records; they must not be silently assigned to unrelated tasks.

## Configuration

| Config | Source | Default | Precedence |
|---|---|---|---|
| report schema | `REPORT_SCHEMA_VERSION` | 1 | code/parser authority |
| edge kinds | `EDGE_KINDS` | fixed set | input must match known values |

## Integration Points

**Calls out to:** no external service; consumes plan/gauntlet files.

**Called by:** execution/planning workflow and tests.

## Active vs Target

- **Active consumers:** dependency analysis and concern parsing utilities.
- **Legacy consumers:** old execution-planner modules are not present in canonical source.
- **Target architecture:** align plan concern links with TMR/architecture contracts.

## LLM Notes

- Do not confuse a dependency report with an execution plan validator; it reports semantic issues but does not load cards or advance pipeline state.
