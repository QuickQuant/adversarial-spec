# C-5.1 Component Mini-Spec

Title: doc-07-execution-validation-leg
Altitude: component
Parent: SS-5
Children: none
Realizes refs: US-0
Requirement ID: C-R501

## Requirement Statement

The component shall satisfy the approved doc 07 execution validation leg acceptance criteria.

## Scope

- Implementation status: partial
- Behavior change: false
- Verification mode: artifact-sync
- Verification scope: static
- Strategy: spike
- Surface scope: cli_command

## Traceability

- Architecture refs: .architecture/filesystem-map.md, .architecture/structured/components/debate-engine.md
- Concern refs: US-0, CB-7, DD-10, OP-11
- Invariant refs: INV-7, INV-A5
- Test refs: TC-0.1
- Exemption reason: Phase-7 doc section (process narrative, no runtime behavior); cold-read usability verified at dogfood TC-0.1 (fresh agent reaches check-rows-clean draft <30 min), not a CI unit test.

## Acceptance Criteria

- "Validation leg (system altitude)" section added after execution plan, before pipeline_load; gated on session_altitude=="system" (read via MCP card metadata, US-2)
- Documents order derive-conops -> draft rows -> normalize-rows -> check-rows; ?3 minimal-row standard; ONE good + ONE rejected row example (CB-7 normalize in sequence)
- Records drafted_baseline_hash; anti-hindsight note (rows precede implementation)

## Verification Summary

Artifact evidence is the documented Phase 7 section plus dogfood TC-0.1 cold-read proof.
