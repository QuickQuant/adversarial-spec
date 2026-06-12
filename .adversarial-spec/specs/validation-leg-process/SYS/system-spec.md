# SYS System Mini-Spec

Title: validation-leg-process
Altitude: system
Parent: null
Children: SS-1, SS-2, SS-3, SS-4, SS-5
Realizes refs: US-0, US-1, US-2, US-3, US-4, US-5, US-6, US-7, US-8, US-9, US-10, US-11, US-12, US-13
Requirement ID: SYS-1

## Requirement Statement

The system shall satisfy the approved validation leg process acceptance criteria.

## Scope

- Implementation status: greenfield
- Behavior change: true
- Verification mode: automated-integration
- Verification scope: full-suite
- Strategy: test-first
- Surface scope: cli_command, outbound_integration

## Traceability

- Architecture refs: .architecture/primer.md, .architecture/overview.md, .architecture/structured/components/emission-toolchain.md
- Concern refs: (aggregate)
- Invariant refs: INV-A1, INV-A2, INV-A3, INV-A4, INV-A5, INV-A6, INV-A7
- Test refs: TC-4.1

## Acceptance Criteria

- Full pytest suite green (deterministic markers) across all subcommands
- System verification = the integration close path runs end-to-end on fixtures
- System validation deferred to dogfood C-5.3 (v4 is verification-only - no system_validation plan binding; VV_ABOVE_ALTITUDE guard)

## Verification Summary

Automated evidence is the declared pytest command passing with mapped TC coverage.
