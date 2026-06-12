# SS-2 Subsystem Mini-Spec

Title: drafting-leg
Altitude: subsystem
Parent: SYS
Children: C-2.1, C-2.2, C-2.3
Realizes refs: US-1, US-2, US-3, US-4
Requirement ID: SS-2

## Requirement Statement

The subsystem shall satisfy the approved drafting leg acceptance criteria.

## Scope

- Implementation status: greenfield
- Behavior change: true
- Verification mode: automated-integration
- Verification scope: full-suite
- Strategy: test-first
- Surface scope: cli_command

## Traceability

- Architecture refs: .architecture/structured/components/emission-toolchain.md, .architecture/primer.md
- Concern refs: DD-7, DD-8, CB-7, CB-10, CB-11, SEC-7
- Invariant refs: INV-6, INV-7, INV-8, INV-11
- Test refs: TC-1.1, TC-2.1

## Acceptance Criteria

- Phase-7 production path derive->normalize->check clean on the session's real roadmap.

## Verification Summary

Automated evidence is the declared pytest command passing with mapped TC coverage.
