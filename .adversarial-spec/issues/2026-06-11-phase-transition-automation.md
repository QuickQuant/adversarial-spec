---
date: 2026-06-11
card_id: "5604"
session_id: adv-spec-202606110339-validation-leg-process
would_have_used: pipeline_phase4_lightweight_advance
---

# Phase Transition Automation (2026-06-11)

## Failure
`pipeline_advance` moved card to Pre-Gauntlet (not Target-Architecture). The Phase 4 lightweight route (extends_existing verdict) has no dedicated lane; FSM transitions debate directly to pre-gauntlet.

## Gate Circumvented
Phase 4 / Step 1: lightweight architecture review (no separate card lane).

## Workaround
Patch session state to `current_phase: target-architecture` to track the lightweight review period before gauntlet prep.

## Permanent Fix
Define Phase 4 lightweight lane in Fizzy FSM, or document that extends_existing specs skip the physical lane and only update state via patch_state.
