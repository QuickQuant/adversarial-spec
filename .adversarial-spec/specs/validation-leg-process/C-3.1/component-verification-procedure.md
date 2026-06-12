# C-3.1 Component Verification

Verification kind: verification
Altitude obligation: component
Verification mode: automated-unit
Verification scope: targeted

## What Runs

- `uv run pytest scripts/tests/test_validation_emission.py -k evidence -q`

## Evidence Required

Automated evidence is the declared pytest command passing with mapped TC coverage.

## Mapped Tests

- Test refs: TC-3.7, TC-G4
- Test files: scripts/tests/test_validation_emission.py

## Acceptance Criteria Covered

- Scaffolds validation-evidence/<row_id>/evidence.md canonical front-matter (hashes stamped by module, FM-2); exact keys/order, distinct codes for missing/malformed/hash-mismatch
- Records conductor evidence_summary into ledger row (mutating); binds row_hash+story_hash+commit (INV-9, INV-12)
- Per-story binding: editing one story invalidates only that story's evidence (FM-3/G4)

## Traceability

- Architecture refs: .architecture/structured/components/emission-toolchain.md, .architecture/structured/components/gauntlet.md
- Concern refs: FM-2, FM-4, DD-9, OP-2
- Invariant refs: INV-4, INV-9, INV-12
