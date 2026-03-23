# Component: Execution Planner

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Gauntlet concern parsing (mostly deprecated) |
| Entry | `execution_planner/gauntlet_concerns.py` |
| Key files | execution_planner/__init__.py, execution_planner/gauntlet_concerns.py |
| Depends on | Adversaries |
| Used by | Execution plan generation |
| Runtime status | partial |
| Architecture status | deprecated |

## What This Component Does

Originally a full execution planning pipeline, most modules were deleted in Feb 2026 as part of the execution-planner-deprecation spec. Only `gauntlet_concerns.py` remains, providing `GauntletConcernParser` for parsing gauntlet JSON output and linking concerns to spec sections. The `__init__.py` still exports types but Phase 3 cleanup (removing unused exports) is still pending.

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `GauntletConcernParser` | Parse gauntlet JSON, link to spec sections | gauntlet_concerns.py |
| `load_concerns_for_spec()` | Load concerns for a spec file | gauntlet_concerns.py |

## Contracts

### Type Contracts

| Contract | Purpose | Owner | Consumed By |
|----------|---------|-------|-------------|
| `GauntletConcern` | Parsed concern with section refs | gauntlet_concerns.py:30 | Execution plan generation |
| `LinkedConcern` | Concern linked to spec section | gauntlet_concerns.py:66 | Execution plan generation |

## LLM Notes

- This component is deprecated. Do not add new features here.
- Phase 3 of the deprecation spec (cleanup exports in __init__.py) is still pending.
- `GauntletConcern` is different from `gauntlet/core_types.Concern`. The former has section_refs, title, failure_mode, etc.
