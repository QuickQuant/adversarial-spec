# C-4.3 Component Verification

Verification kind: verification
Altitude obligation: component
Verification mode: automated-unit
Verification scope: targeted

## What Runs

- `uv run pytest scripts/tests/test_validation_emission.py -k "reset or supersede" -q`

## Evidence Required

Automated evidence is the declared pytest command passing with mapped TC coverage.

## Mapped Tests

- Test refs: TC-2.5, TC-3.8, TC-G5
- Test files: scripts/tests/test_validation_emission.py

## Acceptance Criteria Covered

- reset-failed: judged-fail result->history (append-only INV-14), nulls result/judgment, renames evidence .invalidated-<ts> (FM-4); --remediation-ref REQUIRED, conductor-verified assertion (FM-1)
- supersede-row: legal from ANY state incl judged-pass (CB-1/INV-13); full snapshot to superseded; transactional replacement in one invocation (no coverage gap, INV-7); approval_ref always required (INV-3)
- Allowed-reason enum enforced; disallowed (impl failed / evidence missing / prior negative judgment) -> REFRESH_DISALLOWED (TC-2.5b/G5)

## Traceability

- Architecture refs: .architecture/structured/components/emission-toolchain.md, .architecture/structured/components/gauntlet.md
- Concern refs: CB-1, DD-1, FM-1, FM-4, DD-10
- Invariant refs: INV-3, INV-13, INV-14, INV-A7
