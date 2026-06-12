# C-2.2 Component Verification

Verification kind: verification
Altitude obligation: component
Verification mode: automated-unit
Verification scope: targeted

## What Runs

- `uv run pytest scripts/tests/test_validation_emission.py -k normalize -q`

## Evidence Required

Automated evidence is the declared pytest command passing with mapped TC coverage.

## Mapped Tests

- Test refs: TC-G11
- Test files: scripts/tests/test_validation_emission.py

## Acceptance Criteria Covered

- Sole producer of row_hash/story_hash (CB-7); conductor never writes hex
- Stamps schema fields; validates row_id format r-US<n>-<k> + global uniqueness + story-prefix match
- Mutating subcommand - holds lock, atomic write (INV-A2)

## Traceability

- Architecture refs: .architecture/structured/components/emission-toolchain.md, .architecture/structured/components/gauntlet.md
- Concern refs: CB-7, DD-4
- Invariant refs: INV-A1, INV-12
