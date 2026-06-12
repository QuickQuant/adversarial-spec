# SS-4 Subsystem Mini-Spec

Title: judgment-and-close
Altitude: subsystem
Parent: SYS
Children: C-4.1, C-4.2, C-4.3, C-4.4, C-4.5, C-4.6
Realizes refs: US-7, US-8, US-9, US-11, US-12
Requirement ID: SS-4

## Requirement Statement

The subsystem shall satisfy the approved judgment and close acceptance criteria.

## Scope

- Implementation status: greenfield
- Behavior change: true
- Verification mode: automated-integration
- Verification scope: full-suite
- Strategy: test-first
- Surface scope: cli_command, outbound_integration

## Traceability

- Architecture refs: .architecture/structured/components/harness-hooks.md, .architecture/structured/components/emission-toolchain.md
- Concern refs: CB-1, CB-9, SEC-1, SEC-2, RC-1, FM-10, DD-2
- Invariant refs: INV-1, INV-3, INV-5, INV-11, INV-13, INV-15, INV-17, INV-A1, INV-A4, INV-A5, INV-A7
- Test refs: TC-3.2, TC-3.3

## Acceptance Criteria

- reply->judgment->emission->gate-parity close path correct on fixtures.

## Verification Summary

Automated evidence is the declared pytest command passing with mapped TC coverage.
