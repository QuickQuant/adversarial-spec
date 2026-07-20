# Component: Prompt Registry

> Derived from: `skills/adversarial-spec/scripts/prompts.py`, `gauntlet/prompts.py`, `debate.py` | Verified at: `ef18c66`
> If any derived-from file changed since `ef18c66`, trust source over this doc.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Centralize debate prompt templates, focus areas, and gauntlet prompt text |
| Entry | prompt constants consumed by model callers |
| Key files | `prompts.py`, `gauntlet/prompts.py` |
| Depends on | no runtime service |
| Used by | Debate Engine, Gauntlet Pipeline, model adapters |
| Runtime status | implemented |
| Architecture status | active_primary |

## What This Component Does

Top-level prompts build debate system messages and overlays; package-local gauntlet prompts define attack, evaluation, rebuttal, and final-boss formats. The modules are separate despite similar names.

## Contracts

| Contract | Purpose | Owner | Consumed By |
|---|---|---|---|
| debate prompt templates | critique/synthesis instructions | `prompts.py` | `debate.py`, `models.py` |
| gauntlet prompt templates | attack/evaluation/rebuttal/final-boss instructions | `gauntlet/prompts.py` | phase modules |

## Invariants

- Top-level `prompts.py` and package-local `gauntlet/prompts.py` have distinct roles; sys.path shadowing can select the wrong module.
- Prompt changes affect model output contracts and should be reviewed as behavior changes.

## Data Flow

```text
IN: spec, persona, phase context
PROCESS: template interpolation -> model adapter
OUT: model prompt text
```

## Key Functions

| Function | Purpose | Location |
|---|---|---|
| `get_system_prompt()` | assemble debate system prompt | `prompts.py` |
| `FOCUS_AREAS`/`PERSONAS` | reusable prompt inputs | `prompts.py` |
| gauntlet prompt constants | phase-specific prompt contracts | `gauntlet/prompts.py` |

## Integration Points

**Called by:** Debate Engine, Gauntlet phase modules, model dispatch.

## Active vs Target

- **Active consumers:** both debate and gauntlet routes.
- **Target architecture:** explicit qualified imports for top-level versus gauntlet prompt modules.

## LLM Notes

- A prompt template is a behavior contract; changing required output fields can break downstream parsers.
