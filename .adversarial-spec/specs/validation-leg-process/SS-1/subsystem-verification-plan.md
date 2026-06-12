# SS-1 Subsystem Verification

Verification kind: verification
Altitude obligation: subsystem
Verification mode: automated-integration
Verification scope: full-suite

## What Runs

- `uv run pytest scripts/tests/test_validation_emission.py -q`

## Evidence Required

Automated evidence is the declared pytest command passing with mapped TC coverage. Child nodes must be integrated and the subsystem acceptance criterion must be satisfied.

## Mapped Tests

- Test refs: TC-3.9, TC-2.6
- Test files: scripts/tests/test_validation_emission.py

## Acceptance Criteria Covered

- shared ledger I/O foundation passes lock/corrupt/hash/path fixtures; blocks all feature subcommands until green.

## Traceability

- Architecture refs: .architecture/primer.md, .architecture/patterns.md, .architecture/structured/flows.md
- Concern refs: FM-5, FM-7, SEC-8, SEC-9, SEC-10, OP-3, OP-4, DD-6
- Invariant refs: INV-A1, INV-A2, INV-A3, INV-12
