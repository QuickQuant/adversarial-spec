# C-4.6 Component Mini-Spec

Title: status
Altitude: component
Parent: SS-4
Children: none
Realizes refs: US-8
Requirement ID: C-R406

## Requirement Statement

The component shall satisfy the approved status acceptance criteria.

## Scope

- Implementation status: greenfield
- Behavior change: false
- Verification mode: automated-unit
- Verification scope: targeted
- Strategy: test-after
- Surface scope: cli_command

## Traceability

- Architecture refs: .architecture/structured/components/emission-toolchain.md, .architecture/structured/components/debate-engine.md
- Concern refs: FM-5, OP-7, OP-8
- Invariant refs: INV-A7
- Test refs: TC-G12

## Acceptance Criteria

- Read-only: ledger bytes unchanged (TC-G12); reports active batch + age (>48h flagged), per-part send state, unjudged rows, judged summary, coverage state, blockers, next close-algorithm step
- No mutation path (INV-A2 read-only side)

## Verification Summary

Automated evidence is the declared pytest command passing with mapped TC coverage.
