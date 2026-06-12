# C-1.4 Component Mini-Spec

Title: path-containment-bounds
Altitude: component
Parent: SS-1
Children: none
Realizes refs: US-7
Requirement ID: C-R104

## Requirement Statement

The component shall satisfy the approved path containment bounds acceptance criteria.

## Scope

- Implementation status: greenfield
- Behavior change: true
- Verification mode: automated-unit
- Verification scope: targeted
- Strategy: test-first
- Surface scope: cli_command

## Traceability

- Architecture refs: .architecture/structured/components/session.md, .architecture/patterns.md
- Concern refs: SEC-9, SEC-10, OP-3
- Invariant refs: INV-A3
- Test refs: TC-2.6, TC-1.4

## Acceptance Criteria

- Subcommands resolve artifact paths under spec root via realpath; symlinks/escapes rejected (SEC-9)
- Input bounds enforced: reply 16KB, justification 2KB, ledger 5MB, ConOps 1MB -> structured exit-2 (SEC-10)
- row_id global uniqueness incl. superseded; duplicate manifest story ids -> exit 2

## Verification Summary

Automated evidence is the declared pytest command passing with mapped TC coverage.
