# Component: Adversary Registry

> Derived from: `skills/adversarial-spec/scripts/adversaries.py`, gauntlet phase modules | Verified at: `ef18c66`
> If any derived-from file changed since `ef18c66`, trust source over this doc.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Define named gauntlet personas, templates, scope rules, and stable concern IDs |
| Entry | `resolve_adversary_name()` at `adversaries.py:1357` |
| Key files | `adversaries.py`, gauntlet phases |
| Depends on | dataclasses/regex/hashlib |
| Used by | Gauntlet attack generation, core types, medals, planning |
| Runtime status | implemented |
| Architecture status | active_primary |

## What This Component Does

It defines frozen attacker personas and prompt templates consumed by the gauntlet. It also provides deterministic concern IDs so a concern can be linked across phases, checkpoints, and planning.

## Contracts

| Contract | Purpose | Owner | Consumed By |
|---|---|---|---|
| `Adversary` | frozen persona metadata/scope | `adversaries.py:18` | phase 1/prompts |
| `AdversaryTemplate` | prompt/template shape | `adversaries.py:74` | attack generation |
| concern ID | deterministic cross-phase identity | `adversaries.py:1535` | core types/persistence |

## Invariants

- Persona scope guidelines are validated at construction (`adversaries.py:48`).
- Concern IDs are deterministic from adversary and concern text (`adversaries.py:1535`); do not replace them with random IDs.
- Version manifest tracks persona/template changes (`adversaries.py:1560`).

## Data Flow

```text
IN: configured adversary name + spec
PROCESS: resolve -> template -> model attack -> stable ID
OUT: Concern records
```

## Key Functions

| Function | Purpose | Location |
|---|---|---|
| `resolve_adversary_name()` | alias/name resolution | `adversaries.py:1357` |
| `generate_concern_id()` | stable ID | `adversaries.py:1535` |
| `get_adversary()` | lookup | `adversaries.py:1550` |
| `get_version_manifest()` | version metadata | `adversaries.py:1560` |

## Error Handling

- Invalid persona scope/config fails validation before attack generation.

## Integration Points

**Calls out to:** no external service.

**Called by:** gauntlet phase 1, core types, medals, planning.

## Active vs Target

- **Active consumers:** gauntlet package.
- **Target architecture:** one immutable persona registry used by all attack/report paths.

## LLM Notes

- “Adversary” means a hostile gauntlet persona; debate participants are opponents and should not be conflated with this registry.
