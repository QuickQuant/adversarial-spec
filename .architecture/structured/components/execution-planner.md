# Component: Execution Planner

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Convert finalized specs into implementation task DAGs |
| Entry | `TaskPlanner` at execution_planner/task_planner.py |
| Key files | execution_planner/__init__.py, task_planner.py, gauntlet_concerns.py, spec_intake.py |
| Depends on | Adversaries (for concern linking) |
| Used by | Debate Engine (handle_execution_plan) |

## What This Component Does

The execution planner takes a finalized specification and optional gauntlet concerns, then produces a structured implementation plan with tasks, dependencies, test strategies, and parallelization advice. **This component is mid-deprecation** (Option B+ decision, Feb 2026). The pipeline approach is being replaced by Claude creating plans directly using embedded guidelines in `phases/06-execution.md`. Only `gauntlet_concerns.py` and its data models survive long-term.

## Data Flow

```
IN:  spec text + optional gauntlet concerns JSON
     └─> handle_execution_plan() (debate.py:724)

PROCESS:
     ├─> SpecIntake.parse() → Document (DEPRECATING)
     ├─> ScopeAssessor.assess() → ScopeAssessment (DEPRECATING)
     ├─> TaskPlanner.generate_from_tech_spec() → TaskPlan (KEEPING)
     ├─> TestStrategyManager.assign_strategies() (DEPRECATING)
     ├─> OverDecompositionGuard.check() (DEPRECATING)
     └─> ParallelizationAdvisor.analyze() (DEPRECATING)

OUT: TaskPlan as JSON or Markdown
     └─> stdout or --plan-output file
```

## Key Functions

| Function | Purpose | Location | Status |
|----------|---------|----------|--------|
| `GauntletConcernParser.parse_file()` | Parse gauntlet JSON, link to spec | gauntlet_concerns.py | **KEEP** |
| `GauntletConcernParser.link_to_spec()` | Map concerns to spec sections | gauntlet_concerns.py | **KEEP** |
| `TaskPlanner.generate_from_tech_spec()` | Mechanical task extraction | task_planner.py | **KEEP** |
| `TaskPlanner.auto_generate()` | LLM-based task generation fallback | task_planner.py | **KEEP** |
| `SpecIntake.parse()` | Document structure parsing | spec_intake.py | DEPRECATED |
| `ScopeAssessor.assess()` | Complexity assessment | (in __init__) | DEPRECATED |
| `TestStrategyManager.assign_strategies()` | Test-first/after assignment | (in __init__) | DEPRECATED |
| `OverDecompositionGuard.check()` | Too-many-tasks warning | (in __init__) | DEPRECATED |
| `ParallelizationAdvisor.analyze()` | Workstream identification | (in __init__) | DEPRECATED |

## Deprecation Status

Per `.adversarial-spec/specs/execution-planner-deprecation.md`:

**Phase 1** (DONE): Rewrote `06-execution.md` to guidelines-based approach
**Phase 2** (PENDING): Delete dead modules: spec_intake, agent_dispatch, execution_control, progress, llm_extractor, __main__
**Phase 3** (PENDING): Clean up __init__.py exports, update debate.py imports

## LLM Notes

- The `__init__.py` re-exports 30+ types. Most will be removed in Phase 2/3.
- `gauntlet_concerns.py` is the long-term survivor — it bridges gauntlet output to task planning.
- `from execution_planner import ...` in debate.py is wrapped in try/except for graceful degradation.
- The `EXECUTION_PLANNER_AVAILABLE` flag in debate.py controls feature gating.
