# SS-3 Component Verification

Verification kind: verification
Altitude obligation: subsystem
Verification mode: automated-integration
Verification scope: full-suite

## What Runs

- `uv run pytest scripts/tests/test_validation_emission.py -q`

## Evidence Required

Automated evidence is the declared pytest command passing with mapped TC coverage.

## Mapped Tests

- Test refs: TC-3.1, TC-3.7
- Test files: scripts/tests/test_validation_emission.py

## Acceptance Criteria Covered

- evidence->digest->delivery path correct on fixtures + real bridge at dogfood.

## Traceability

- Architecture refs: .architecture/primer.md, .architecture/structured/components/harness-hooks.md
- Concern refs: FM-2, DD-1, RC-2, SEC-4, FM-9
- Invariant refs: INV-4, INV-9, INV-10, INV-12, INV-16, INV-A6
