# Component: Prompts

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Centralized prompt templates, focus areas, and personas |
| Entry | `get_system_prompt()` at scripts/prompts.py:125 |
| Key files | prompts.py (505 lines) |
| Depends on | Standard library only |
| Used by | Models, Providers, Debate Engine, Gauntlet |

## What This Component Does

Prompts is a pure data/function module that provides all prompt templates used across the system. It defines system prompts by doc type and depth, review/press prompt templates, focus areas (specialized critique angles), personas (reviewer personalities), and utility prompts for task extraction and diff generation. It's the most-imported module in the codebase.

## Data Flow

```
IN:  doc_type, depth, persona, focus parameters
     └─> get_system_prompt() (prompts.py:125)

PROCESS:
     ├─> Select system prompt by doc_type (spec, debug, etc.)
     ├─> Apply depth modifier (product, technical, full)
     └─> Combine with focus area and persona if specified

OUT: Formatted prompt strings
     └─> consumed by models.py for LLM calls
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `get_system_prompt()` | Select and format system prompt by doc_type/depth | prompts.py:125 |
| `get_doc_type_name()` | Human-readable doc type name | prompts.py |

## Key Data

| Constant | Purpose |
|----------|---------|
| `FOCUS_AREAS` | Dict of specialized critique angles (security, performance, etc.) | prompts.py:31-110 |
| `PERSONAS` | Dict of reviewer personalities | prompts.py:112-123 |
| `REVIEW_PROMPT_TEMPLATE` | Standard review round template |
| `PRESS_PROMPT_TEMPLATE` | Press (adversarial pressure) template |
| `PRESERVE_INTENT_PROMPT` | Instruction to preserve original intent |
| `EXPORT_TASKS_PROMPT` | Task extraction template |
| `SYSTEM_PROMPT_*` | System prompts by doc type |

## Integration Points

**Calls out to:**
- Nothing (leaf module, no internal imports)

**Called by:**
- `models.py` — prompt construction for LLM calls
- `providers.py` — FOCUS_AREAS and PERSONAS for listing
- `debate.py` — doc type names and prompt formatting
- `gauntlet` phase modules — gauntlet-specific prompt selection

## LLM Notes

- This is a leaf module with no internal dependencies — highest import count in the codebase (5+).
- Focus areas are specialized critique angles like "security", "performance", "api-design" — they modify the system prompt to bias the reviewer.
- Personas are reviewer personalities like "senior-engineer", "product-manager" — they change the tone and perspective.
- Template substitution uses Python `.format()` with named placeholders: {round}, {doc_type_name}, {spec}, {focus_section}, {context_section}.
