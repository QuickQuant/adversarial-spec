# C-1.3 Component Verification

Verification kind: verification
Altitude obligation: component
Verification mode: automated-unit
Verification scope: targeted

## What Runs

- `uv run pytest scripts/tests/test_validation_emission.py -k hash -q`

## Evidence Required

Automated evidence is the declared pytest command passing with mapped TC coverage.

## Mapped Tests

- Test refs: TC-2.6
- Test files: scripts/tests/test_validation_emission.py

## Acceptance Criteria Covered

- row_hash = sha256 over json.dumps([conops_ref,scenario,oracle,evidence_type],ensure_ascii=False,separators=(",",":")) with all 4 NFC-normalized; FULL 64-hex stored
- evidence_rationale + test_targets EXCLUDED from row_hash (TC-2.6); hash changes when scenario/oracle/conops_ref/evidence_type change
- conops_hash = sha256 of conops.md bytes; story_hashes per-section; 12-hex prefix emitted only at artifact boundary; self-check rejects prefixes <12 (SEC-8)
- Hashes computed ONLY by the module; lengths/constants pinned by tests

## Traceability

- Architecture refs: .architecture/structured/components/emission-toolchain.md, .architecture/structured/components/gauntlet.md
- Concern refs: SEC-8, DD-5, RC-3
- Invariant refs: INV-12, INV-A1
