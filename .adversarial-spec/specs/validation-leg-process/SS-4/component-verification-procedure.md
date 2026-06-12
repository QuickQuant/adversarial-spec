# SS-4 Component Verification

Verification kind: verification
Altitude obligation: subsystem
Verification mode: automated-integration
Verification scope: full-suite

## What Runs

- `uv run pytest scripts/tests/test_validation_emission.py -q`

## Evidence Required

Automated evidence is the declared pytest command passing with mapped TC coverage.

## Mapped Tests

- Test refs: TC-3.2, TC-3.3
- Test files: scripts/tests/test_validation_emission.py

## Acceptance Criteria Covered

- reply->judgment->emission->gate-parity close path correct on fixtures.

## Traceability

- Architecture refs: .architecture/structured/components/harness-hooks.md, .architecture/structured/components/emission-toolchain.md
- Concern refs: CB-1, CB-9, SEC-1, SEC-2, RC-1, FM-10, DD-2
- Invariant refs: INV-1, INV-3, INV-5, INV-11, INV-13, INV-15, INV-17, INV-A1, INV-A4, INV-A5, INV-A7
