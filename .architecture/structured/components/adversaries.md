# Component: Adversaries

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Named attacker persona definitions with version tracking |
| Entry | `adversaries.py` (module-level ADVERSARIES dict) |
| Key files | adversaries.py |
| Depends on | None (leaf module) |
| Used by | Gauntlet Pipeline (all phases), Debate Engine, Execution Planner |
| Runtime status | implemented |
| Architecture status | active_primary |

## What This Component Does

Defines 9+ named adversary personas as frozen dataclasses. Each persona has a name, prefix, detailed persona prompt, and structured evaluation protocols (valid/invalid dismissal rules, valid acceptance criteria). The ADVERSARIES dict is the canonical source consumed by the gauntlet pipeline for attack generation and concern evaluation. AdversaryTemplate provides a v2.0 format with scope guidelines for dynamic prompt generation.

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `ADVERSARIES` | Dict of Adversary frozen dataclasses | adversaries.py (module-level) |
| `generate_concern_id()` | Stable hash-based ID for concerns | adversaries.py:~250 |
| `resolve_adversary_name()` | Canonicalize aliases to official keys | adversaries.py |
| `Adversary.content_hash()` | Detect persona changes for cache invalidation | adversaries.py:18 |

## Contracts

### Type Contracts

| Contract | Purpose | Owner | Consumed By |
|----------|---------|-------|-------------|
| `Adversary` | Frozen persona with evaluation protocols | adversaries.py:18 | All gauntlet phases, debate.py |
| `AdversaryTemplate` | v2.0 format with scope guidelines | adversaries.py:74 | Dynamic prompt generation |

## Integration Points

**Calls out to:**
- None (leaf module, no external dependencies)

**Called by:**
- `gauntlet/orchestrator.py` — resolve adversaries for pipeline
- `gauntlet/phase_1_attacks.py` — load persona for attack generation
- `gauntlet/phase_4_evaluation.py` — load evaluation protocols
- `execution_planner/gauntlet_concerns.py` — ADVERSARY_PREFIXES for ID generation

## LLM Notes

- This is a hub file (imported by 9+ others). Changes here affect the entire gauntlet pipeline.
- `content_hash()` enables detecting when a persona prompt changes, which should invalidate cached evaluations.
- AdversaryTemplate validates `scope_guidelines` keys against `VALID_SCOPE_KEYS`. Invalid keys raise at construction time.
