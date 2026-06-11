# Validation-Leg Production Process — Implementation Plan

> STATUS: Phase 0 triage complete (2026-06-11). Purpose/scope below are the
> session's starting frame; work breakdown, verification ladder, and sequencing
> fill in through Phases 1–7. Template: `reference/plan-template.md`.

## Triage  *(from `phases/00-triage.md` — ran before any session machinery)*

- **Complexity:** medium — integrations=moderate (fizzy pipeline tools + Telegram
  human gate, no new external services), unknowns=several (artifact shape,
  producing phase, evidence contract, operational meaning of "validated").
- **Root altitude:** system — highest-blast item is the **cross-repo
  validation-evidence contract** (what evidence the skill must produce for
  fizzy's `mark_system_validation_complete` gate to accept), because it crosses
  the repo/process boundary and a bad contract strands every future
  system-altitude session at V-close; fixing it requires coordinated two-repo
  change with deploy ordering (ADR-0001-class).
- **Go/no-go:** GO.

## Purpose

Fizzy pipeline v5 arms `_node_owes_system_validation` for system-altitude
sessions: V-completeness requires `system_validation_complete` AND
`system_verification_complete` independently, and schema-3 plans must NOT carry
a `system_validation` binding (`VV_ABOVE_ALTITUDE`) — validation closes
card-side via `mark_system_validation_complete`. The skill has no phase that
produces validation artifacts or calls that tool. Now that Phase 0 triage
assigns `session_altitude`, the first `system`-altitude session will hit an
armed gate with no production line behind it. This session designs that
production line.

## Scope

**In:**
- ConOps artifact: format (NASA Appx S annotated outline already optionally
  emitted by Phase 7 as `conops-outline.md`, currently unbound), producing
  phase, refinement points.
- Validation ledger: schema, writer, where it lives.
- Human validation gate: operational definition of "validated" (human confirms
  against ConOps scenarios — likely Telegram-bridged), evidence contract.
- Phase-doc wiring: who calls `mark_system_validation_complete`, when, with
  what evidence recorded.
- The cross-repo contract statement: skill produces / fizzy gates (same split
  as ADR 0001).

**Out (now):**
- Fizzy-side gate changes (fizzy-pipeline-mcp owns the gate; this session may
  emit a handoff doc but changes there are their roadmap).
- Subsystem/component-altitude validation (v5 gate is system-altitude only).
- Retrofitting validation onto v4/grandfathered sessions.

## Open questions (Phase 1 interview seeds)

1. What is the validation artifact set — ConOps binding + ledger, or more?
2. Which phase produces ConOps (Phase 1 origin, Phase 4 refinement, Phase 7
   emission?) and which phase closes validation (end of Phase 8?)?
3. What does "validated" mean operationally — human-gated scenario walkthrough
   via Telegram bridge? What evidence is recorded?
4. Evidence contract for `mark_system_validation_complete` — what does fizzy
   accept/require today? (Verify against served code, not assumptions.)
