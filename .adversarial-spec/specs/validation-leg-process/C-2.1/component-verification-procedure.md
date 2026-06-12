# C-2.1 Component Verification

Verification kind: verification
Altitude obligation: component
Verification mode: automated-unit
Verification scope: targeted

## What Runs

- `uv run pytest scripts/tests/test_validation_emission.py -k conops -q`

## Evidence Required

Automated evidence is the declared pytest command passing with mapped TC coverage.

## Mapped Tests

- Test refs: TC-1.1, TC-1.2, TC-1.3, TC-G13
- Test files: scripts/tests/test_validation_emission.py

## Acceptance Criteria Covered

- Deterministic template derivation from manifest id/title/story + milestone context only; never invents stories (DD-7)
- Every US-\d+ appears as ### US-n heading; stray-id lint (TC-G13: "replaces US-99" -> exit 2, CB-11); duplicate ids -> exit 2
- Records full conops_hash + per-section story_hashes map (FM-3); re-derive refuses without --force when a ledger references prior hash

## Traceability

- Architecture refs: .architecture/structured/components/emission-toolchain.md, .architecture/structured/components/session.md, .architecture/patterns.md
- Concern refs: DD-7, CB-11, FM-3, SEC-9
- Invariant refs: INV-2, INV-8
