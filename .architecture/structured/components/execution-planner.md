# Component: Execution Planner

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Gauntlet concern parsing (mostly deprecated) |
| Entry | `GauntletConcernParser` at execution_planner/gauntlet_concerns.py |
| Key files | execution_planner/__init__.py, gauntlet_concerns.py |
| Depends on | Adversaries (for ADVERSARY_PREFIXES, generate_concern_id) |
| Used by | Debate Engine (optional, lazy-loaded) |

## What This Component Does

The execution planner was originally a full spec-to-task decomposition pipeline. **It is mostly deprecated** (Option B+ decision, Feb 2026). The pipeline approach was replaced by Claude creating plans directly using embedded guidelines in `phases/06-execution.md`. Dead modules have been deleted. Only `gauntlet_concerns.py` survives long-term — it parses structured gauntlet JSON to link concerns to spec sections.

## Data Flow

```
IN:  gauntlet concern JSON files
     └─> GauntletConcernParser.parse_file()

PROCESS:
     ├─> Parse concern JSON structure
     ├─> Match concern IDs to adversary prefixes
     └─> Link concerns to spec sections

OUT: list[GauntletConcern] with linked spec references
     └─> returned to caller
```

## Key Functions

| Function | Purpose | Location | Status |
|----------|---------|----------|--------|
| `GauntletConcernParser.parse_file()` | Parse gauntlet JSON | gauntlet_concerns.py | **KEEP** |
| `load_concerns_for_spec()` | Load all concerns for a spec hash | gauntlet_concerns.py | **KEEP** |

## LLM Notes

- Only `gauntlet_concerns.py` and `__init__.py` exist in this directory now. Dead modules were deleted in the execution planner deprecation (Feb 2026).
- `from execution_planner import ...` in debate.py is wrapped in try/except for graceful degradation.
- The `__init__.py` exports: GauntletConcern, GauntletConcernParser, GauntletReport, LinkedConcern, load_concerns_for_spec.
