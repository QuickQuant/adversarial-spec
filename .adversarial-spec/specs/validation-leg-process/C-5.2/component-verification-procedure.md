# C-5.2 Component Verification

Verification kind: verification
Altitude obligation: component
Verification mode: static-check
Verification scope: static

## What Runs

- `uv run pytest scripts/tests/test_validation_emission.py -k doc_error_codes -q`

## Evidence Required

Inspection/static evidence is the declared grep or pytest static check passing.

## Mapped Tests

- Test refs: TC-0.2
- Test files: skills/adversarial-spec/phases/08-implementation.md

## Acceptance Criteria Covered

- "Validation leg (system altitude)" close section = the ?8 close algorithm verbatim (single normative ordering, every step idempotent, re-entry at step 1; DD-2)
- ?10 error-code playbook: all 8 gate rejects + local codes each with documented conductor response (TC-0.2)
- Re-entry routing: NOTHING_TO_DIGEST + failed rows -> remediation, never emission (CB-5); self-check before MCP (INV-5); MCP wiring concrete (FM-8)

## Traceability

- Architecture refs: .architecture/filesystem-map.md, .architecture/structured/components/debate-engine.md
- Concern refs: DD-2, FM-8, CB-5, US-4-correction
- Invariant refs: INV-5, INV-A6
