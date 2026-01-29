# Checkpoint: Legacy Cleanup and Execution Gate

**Date:** 2026-01-28
**Session:** Adversarial-Spec Skill Development
**Phase:** complete (with open issue)

## Summary

This session addressed Process Failure Report #2 findings:

### Completed

1. **Legacy prd/tech removal**
   - `prompts.py`: Renamed `SYSTEM_PROMPT_PRD/TECH` → `SYSTEM_PROMPT_SPEC_PRODUCT/TECHNICAL`
   - `debate.py`: Removed `prd`/`tech` from `--doc-type` choices
   - All phase docs: Updated terminology to unified spec model

2. **Phase 5 (PRD→Tech) deleted**
   - Obsolete with unified `--depth` flag
   - Use `--depth full` instead of PRD→Tech continuation
   - Renumbered: Phase 5=Execution, Phase 6=Implementation

3. **Execution phase gate added**
   - SKILL.md: Added "CRITICAL: Phase Transition Rules"
   - Cannot mark `complete` without going through execution
   - 0-task warning requires user acknowledgment

### NOT Fixed (Open Issue)

**Spec format incompatibility with execution planner**

The execution planner parser expects:
```markdown
## 2. Goals
### 4.1 ModelName
US-1: User Story
FR-1: Functional Requirement
```

The debate generates:
```markdown
## Goals
### EndpointItem (for OpenAPI sources)
(no prefixes, no numbered sections)
```

Result: 56 gauntlet concerns → 0 tasks generated

**Recommended fixes (user must choose):**
1. Template-based generation - Force parseable format during debate
2. Pre-finalize validation - Check format before marking spec complete
3. Smarter parser - Make execution_planner handle narrative format

## Files Changed

| File | Change |
|------|--------|
| `prompts.py` | Renamed constants, removed legacy code paths |
| `debate.py` | Removed prd/tech from CLI, updated docs |
| `01-init-and-requirements.md` | Deleted Phase 5, renumbered phases |
| `05-finalize.md` | Removed Step 9, updated terminology |
| `06-execution.md` | Updated PRD/tech references |
| `SKILL.md` | Added execution phase gate |

## Next Action

Choose approach for format compatibility fix, then test with documentation_master.
