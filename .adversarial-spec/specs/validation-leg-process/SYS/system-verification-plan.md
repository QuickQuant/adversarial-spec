# SYS System Verification

Verification kind: verification
Altitude obligation: system
Verification mode: automated-integration
Verification scope: full-suite

## What Runs

- `uv run pytest scripts/tests/test_validation_emission.py -q`

## Evidence Required

Automated evidence is the declared pytest command passing with mapped TC coverage. The full validation-leg close path must pass on the dogfood session without a system_validation plan binding.

## Mapped Tests

- Test refs: TC-4.1
- Test files: scripts/tests/test_validation_emission.py

## Acceptance Criteria Covered

- Full pytest suite green (deterministic markers) across all subcommands
- System verification = the integration close path runs end-to-end on fixtures
- System validation deferred to dogfood C-5.3 (v4 is verification-only - no system_validation plan binding; VV_ABOVE_ALTITUDE guard)

## Traceability

- Architecture refs: .architecture/primer.md, .architecture/overview.md, .architecture/structured/components/emission-toolchain.md
- Concern refs: (aggregate)
- Invariant refs: INV-A1, INV-A2, INV-A3, INV-A4, INV-A5, INV-A6, INV-A7
