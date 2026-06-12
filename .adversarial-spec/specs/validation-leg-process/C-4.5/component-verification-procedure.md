# C-4.5 Component Verification

Verification kind: verification
Altitude obligation: component
Verification mode: automated-unit
Verification scope: targeted

## What Runs

- `uv run pytest scripts/tests/test_validation_emission.py -k self_check -q`

## Evidence Required

Automated evidence is the declared pytest command passing with mapped TC coverage.

## Mapped Tests

- Test refs: TC-3.3, TC-INV-A5, TC-G10
- Test files: scripts/tests/test_validation_emission.py

## Acceptance Criteria Covered

- Mirrors all 8 gate reject classes (fizzy-validation-contract.md): kind, conops_hash prefix-match (<12 reject), rows non-empty, per-row fields, result enum, all-pass, anti-relabeling, US coverage regex \bUS-\d+\b
- Strictly stricter: rejects identical-set AND unjustified-overlap test_targets locally (INV-11); verdict parity is a pinned test (TC-3.3)
- --verification-ledger required when verification artifacts exist; absent -> ANTI_RELABELING_UNCHECKED warning, never silent pass
- Runs on exact emitted bytes immediately before MCP; artifact sha256 re-verified at call time (INV-5, RC-1 TOCTOU)

## Traceability

- Architecture refs: .architecture/structured/components/emission-toolchain.md, .architecture/primer.md
- Concern refs: RC-1, SEC-7, CB-5, DD-2
- Invariant refs: INV-5, INV-11, INV-A5
