# SS-2 Subsystem Verification

Verification kind: verification
Altitude obligation: subsystem
Verification mode: automated-integration
Verification scope: full-suite

## What Runs

- `uv run pytest scripts/tests/test_validation_emission.py -q`

## Evidence Required

Automated evidence is the declared pytest command passing with mapped TC coverage. Child nodes must be integrated and the subsystem acceptance criterion must be satisfied.

## Mapped Tests

- Test refs: TC-1.1, TC-2.1
- Test files: scripts/tests/test_validation_emission.py

## Acceptance Criteria Covered

- Phase-7 production path derive->normalize->check clean on the session's real roadmap.

## Traceability

- Architecture refs: .architecture/structured/components/emission-toolchain.md, .architecture/primer.md
- Concern refs: DD-7, DD-8, CB-7, CB-10, CB-11, SEC-7
- Invariant refs: INV-6, INV-7, INV-8, INV-11
