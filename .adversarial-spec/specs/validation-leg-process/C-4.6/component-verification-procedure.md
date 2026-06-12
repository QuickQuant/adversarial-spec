# C-4.6 Component Verification

Verification kind: verification
Altitude obligation: component
Verification mode: automated-unit
Verification scope: targeted

## What Runs

- `uv run pytest scripts/tests/test_validation_emission.py -k status -q`

## Evidence Required

Automated evidence is the declared pytest command passing with mapped TC coverage.

## Mapped Tests

- Test refs: TC-G12
- Test files: scripts/tests/test_validation_emission.py

## Acceptance Criteria Covered

- Read-only: ledger bytes unchanged (TC-G12); reports active batch + age (>48h flagged), per-part send state, unjudged rows, judged summary, coverage state, blockers, next close-algorithm step
- No mutation path (INV-A2 read-only side)

## Traceability

- Architecture refs: .architecture/structured/components/emission-toolchain.md, .architecture/structured/components/debate-engine.md
- Concern refs: FM-5, OP-7, OP-8
- Invariant refs: INV-A7
