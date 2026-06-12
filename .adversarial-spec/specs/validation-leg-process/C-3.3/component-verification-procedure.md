# C-3.3 Component Verification

Verification kind: verification
Altitude obligation: component
Verification mode: automated-unit
Verification scope: targeted

## What Runs

- `uv run pytest scripts/tests/test_validation_emission.py -k "record_send or cancel" -q`

## Evidence Required

Automated evidence is the declared pytest command passing with mapped TC coverage.

## Mapped Tests

- Test refs: TC-G1
- Test files: scripts/tests/test_validation_emission.py

## Acceptance Criteria Covered

- record-send records per-part delivery + message_id; flips batch to sent only when ALL parts sent (RC-2)
- cancel-batch requires --reason; rows return to delta pool; audit-logged; cancellation notice if parts were sent (FM-12)
- Bulk verdicts gated on sent status (INV-16)

## Traceability

- Architecture refs: .architecture/structured/components/harness-hooks.md, .architecture/structured/components/emission-toolchain.md
- Concern refs: RC-2, FM-6, FM-12, OP-7
- Invariant refs: INV-16, INV-A6
