# Component: Adversaries

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Named attacker persona definitions for gauntlet stress-testing |
| Entry | `ADVERSARIES` dict at scripts/adversaries.py |
| Key files | adversaries.py (914 lines) |
| Depends on | Standard library only (hashlib, dataclasses, datetime) |
| Used by | Gauntlet, Debate Engine, Execution Planner (gauntlet_concerns) |

## What This Component Does

Adversaries is a pure data module that defines named attacker personas used in the gauntlet pipeline. Each adversary has a name, attack focus area, prompt prefix, and detailed persona description. The module also provides the concern ID generation function and adversary prefix mappings used by the gauntlet concern parser. Key personas include PARANOID_SECURITY, BURNED_ONCALL, FINAL_BOSS, and PRE_GAUNTLET.

## Data Flow

```
IN:  none (pure data module)

PROCESS:
     ├─> Define Adversary dataclass with name, prefix, persona
     ├─> Build ADVERSARIES dict mapping names to Adversary instances
     └─> Provide generate_concern_id() for unique concern identification

OUT: Adversary definitions + utility functions
     └─> imported by gauntlet.py, debate.py, execution_planner/
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `generate_concern_id()` | Generate unique concern ID from adversary + text hash | adversaries.py |
| `Adversary` dataclass | Data structure: name, prefix, persona fields | adversaries.py |

## Key Data

| Constant | Purpose |
|----------|---------|
| `ADVERSARIES` | Dict mapping adversary names to Adversary instances |
| `PARANOID_SECURITY` | Security-focused adversary |
| `BURNED_ONCALL` | Operations/reliability adversary |
| `FINAL_BOSS` | Holistic UX reviewer (issues PASS/REFINE/RECONSIDER) |
| `PRE_GAUNTLET` | Pre-debate context-focused adversary |
| `ADVERSARY_PREFIXES` | Maps concern ID prefixes to adversary names |

## Integration Points

**Calls out to:**
- Nothing (leaf module, no internal imports)

**Called by:**
- `gauntlet.py` — persona definitions for attack generation
- `debate.py` — adversary listing and stats
- `execution_planner/gauntlet_concerns.py` — ADVERSARY_PREFIXES for concern linking

## LLM Notes

- This is a leaf module with no internal dependencies — safe to modify without cascading effects.
- Adding a new adversary: create an Adversary instance, add to ADVERSARIES dict, optionally add prefix to ADVERSARY_PREFIXES.
- The FINAL_BOSS adversary is special — it runs after all other phases and issues system-level verdicts (PASS/REFINE/RECONSIDER).
- Concern IDs use a hash of adversary prefix + concern text for deduplication across runs.
