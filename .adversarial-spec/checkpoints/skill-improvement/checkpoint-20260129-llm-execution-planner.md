# Checkpoint: LLM-Based Execution Planner

**Date:** 2026-01-29
**Context:** Adversarial-Spec Skill Development
**Phase:** Complete

## Summary

Implemented LLM-based task extraction for the execution planner, replacing the regex-based approach that couldn't handle narrative specs.

## What Was Done

### 1. Debated Spec→Execution Workflow
- Ran debate with Gemini + Codex on format compatibility issue
- Initial consensus: Option 2 (post-processing converter with structured-v1 JSON schema)
- User challenged: "Why not just go direct?"
- Final decision: LLM extracts tasks directly from narrative specs, no intermediate format

### 2. Built LLM Extractor (`execution_planner/llm_extractor.py`)
- Supports Gemini CLI (free, uses Google account)
- Supports Codex CLI (free, uses ChatGPT subscription)
- Falls back to litellm (API keys required)
- Auto-fallback on JSON parse failures
- Extracts tasks with: title, description, acceptance_criteria, effort, risk, dependencies

### 3. Updated Task Planner
- Added `TaskPlanner.generate_from_narrative()` - LLM-based extraction
- Added `TaskPlanner.auto_generate()` - single entry point for any spec
- Removed regex-first approach (just uses LLM directly)

### 4. Tested with Docmaster Spec
- `spec-output-docmaster.md` → 15 tasks extracted via Gemini CLI
- Validated task structure and dependencies

### 5. Exported to MCP Tasks
- Created tasks #100-114 under "Docmaster Specification" context
- Set up dependencies (project setup → models → parsers → indexer → searcher → commands)
- Archived task #93 (superseded by detailed breakdown)

## Files Changed

| File | Change |
|------|--------|
| `execution_planner/llm_extractor.py` | NEW - LLM extraction with CLI fallback |
| `execution_planner/task_planner.py` | Added generate_from_narrative, auto_generate |
| `execution_planner/__init__.py` | Added llm_extractor exports |
| `execution_planner/__main__.py` | Uses auto_generate |
| `.adversarial-spec/specs/structured-spec-bridge.md.rejected` | Rejected spec (over-engineered) |

## Lessons Learned

1. **Over-engineering detection**: The debate produced a complex solution (converter + schema + migration). User's simple "why not direct?" revealed it was unnecessary.

2. **Gauntlet on solutions**: `lazy_developer` would have caught this. Run gauntlet on proposed technical solutions, not just product specs.

3. **Narrative specs are complete**: The docmaster spec has everything needed (goals, commands, models, errors) without formal US-X/FR-X labels. Labels are for dumb parsers.

## Next Steps

1. **Start docmaster implementation** - Task #100 (Set up project structure) is ready
2. **Find docmaster gauntlet concerns** - User said they ran gauntlet, link concerns to tasks
3. **Copy skill changes to ~/.claude/skills/** - Deploy updated execution planner

## Open Items

- [ ] Deploy execution_planner changes to skill directory
- [ ] Run docmaster gauntlet concerns through task linking
- [ ] Consider adding gauntlet step for technical solution proposals
