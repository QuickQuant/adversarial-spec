# Component: Prompts

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Centralized prompt templates, focus areas, and persona definitions |
| Entry | `prompts.py` (module-level dicts and functions) |
| Key files | prompts.py |
| Depends on | None (leaf module) |
| Used by | Models, Debate Engine |
| Runtime status | implemented |
| Architecture status | active_primary |

## What This Component Does

Centralized repository of system prompts, focus area definitions, and persona templates. `get_system_prompt()` assembles the system message sent to models, combining the base prompt with optional focus area and persona overlays. Also provides `PRESERVE_INTENT_PROMPT` for intent-preservation mode and various info-listing functions.

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `get_system_prompt()` | Assemble system prompt from focus + persona | prompts.py |
| `FOCUS_AREAS` | Dict of focus area definitions | prompts.py |
| `PERSONAS` | Dict of persona definitions | prompts.py |
| `PRESERVE_INTENT_PROMPT` | Intent preservation overlay | prompts.py |

## Integration Points

**Called by:**
- `models.py` — system prompt assembly before completion() calls
- `debate.py` — focus area and persona listing commands

## LLM Notes

- This is a data module. No complex logic. Changes here affect prompt quality across the system.
