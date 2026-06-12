---
date: 2026-06-11
card_id: "5604"
session_id: adv-spec-202606110339-validation-leg-process
would_have_used: pipeline_finalize_complete_with_acceptance
---

# Phase Transition: Finalize → Execution (Card 5604)

> The original `pipeline_patch_state` escape-hatch call recorded its `process_failure_path`
> as `/tmp/process_failure.md` (ephemeral). This file is the durable re-filing of that note.

## Context
Session: adv-spec-202606110339-validation-leg-process
Card: 5604 (Fizzy board 03fw5alxw15iqwh6hq15vfdsb)

## Situation
Spec ACCEPTED by Jason after final guardrails pass and tests-spec.md promotion.
Phase 6 (finalize) work complete. Ready to advance to Phase 7 (execution).

## Action
Using pipeline_patch_state escape hatch to record phase transition and acceptance flag
because the normal pipeline gate flow is being superseded by direct state mutation for
session continuity (v4 altitude session, plan_schema_version 3 emission).

## Permanent Fix
Pipeline should have a formal `pipeline_finalize_complete` transition tool (or similar)
that handles acceptance flag + phase advance atomically without requiring process_failure_path.
Currently using generic escape hatch for a legitimate workflow event.
