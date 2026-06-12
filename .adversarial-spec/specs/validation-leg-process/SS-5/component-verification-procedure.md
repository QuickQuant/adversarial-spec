# SS-5 Component Verification

Verification kind: verification
Altitude obligation: subsystem
Verification mode: automated-integration
Verification scope: full-suite

## What Runs

- `uv run pytest scripts/tests/test_validation_emission.py -q`

## Evidence Required

Automated evidence is the declared pytest command passing with mapped TC coverage.

## Mapped Tests

- Test refs: TC-0.1, TC-0.2, TC-4.1
- Test files: scripts/tests/test_validation_emission.py

## Acceptance Criteria Covered

- docs wire the process + dogfood proves on self.

## Traceability

- Architecture refs: .architecture/filesystem-map.md, .architecture/access-guide.md
- Concern refs: DD-2, FM-8, US-0, US-10, ACK-4, OP-10
- Invariant refs: INV-5, INV-7, INV-A5, INV-A6
