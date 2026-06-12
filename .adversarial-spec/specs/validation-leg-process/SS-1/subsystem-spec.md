# SS-1 Subsystem Mini-Spec

Title: ledger-core
Altitude: subsystem
Parent: SYS
Children: C-1.1, C-1.2, C-1.3, C-1.4
Realizes refs: US-0, US-3, US-7, US-8
Requirement ID: SS-1

## Requirement Statement

The subsystem shall satisfy the approved ledger core acceptance criteria.

## Scope

- Implementation status: greenfield
- Behavior change: true
- Verification mode: automated-integration
- Verification scope: full-suite
- Strategy: test-first
- Surface scope: cli_command

## Traceability

- Architecture refs: .architecture/primer.md, .architecture/patterns.md, .architecture/structured/flows.md
- Concern refs: FM-5, FM-7, SEC-8, SEC-9, SEC-10, OP-3, OP-4, DD-6
- Invariant refs: INV-A1, INV-A2, INV-A3, INV-12
- Test refs: TC-3.9, TC-2.6

## Acceptance Criteria

- shared ledger I/O foundation passes lock/corrupt/hash/path fixtures; blocks all feature subcommands until green.

## Verification Summary

Automated evidence is the declared pytest command passing with mapped TC coverage.
