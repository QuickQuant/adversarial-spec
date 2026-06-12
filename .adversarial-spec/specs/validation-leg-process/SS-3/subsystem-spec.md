# SS-3 Subsystem Mini-Spec

Title: evidence-and-digest
Altitude: subsystem
Parent: SYS
Children: C-3.1, C-3.2, C-3.3
Realizes refs: US-5, US-6, US-13
Requirement ID: SS-3

## Requirement Statement

The subsystem shall satisfy the approved evidence and digest acceptance criteria.

## Scope

- Implementation status: greenfield
- Behavior change: true
- Verification mode: automated-integration
- Verification scope: full-suite
- Strategy: test-first
- Surface scope: cli_command, outbound_integration

## Traceability

- Architecture refs: .architecture/primer.md, .architecture/structured/components/harness-hooks.md
- Concern refs: FM-2, DD-1, RC-2, SEC-4, FM-9
- Invariant refs: INV-4, INV-9, INV-10, INV-12, INV-16, INV-A6
- Test refs: TC-3.1, TC-3.7

## Acceptance Criteria

- evidence->digest->delivery path correct on fixtures + real bridge at dogfood.

## Verification Summary

Automated evidence is the declared pytest command passing with mapped TC coverage.
