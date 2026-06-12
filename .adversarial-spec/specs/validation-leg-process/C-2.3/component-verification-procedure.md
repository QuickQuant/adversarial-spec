# C-2.3 Component Verification

Verification kind: verification
Altitude obligation: component
Verification mode: automated-unit
Verification scope: targeted

## What Runs

- `uv run pytest scripts/tests/test_validation_emission.py -k "check_rows or oracle" -q`

## Evidence Required

Automated evidence is the declared pytest command passing with mapped TC coverage.

## Mapped Tests

- Test refs: TC-2.1, TC-2.2, TC-2.3, TC-2.4
- Test files: scripts/tests/test_validation_emission.py

## Acceptance Criteria Covered

- --conops required; coverage uses exact-token equality conops_ref=="US-n" (CB-10); --draft relaxes coverage to advisory (DD-8)
- Oracle layer-2 lint rejects banned phrases ("tests pass" + synonyms) and vague terminals unless paired with concrete observable; requires literal iff + named US-n (INV-6, TC-2.3)
- Anti-relabeling: validation test_targets not identical/subset/overlapping verification targets without rationale (INV-11, SEC-7)
- Structural only - semantics human-owned (documented scope honesty)

## Traceability

- Architecture refs: .architecture/structured/components/emission-toolchain.md, .architecture/patterns.md
- Concern refs: CB-10, DD-8, SEC-7, DIS-2, OP-2
- Invariant refs: INV-6, INV-7, INV-11
