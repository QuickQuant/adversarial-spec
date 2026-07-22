# B-5 Component Verification

Task: promotion_gate.py local evaluation + intent construction

Acceptance criteria:
- end-to-end local/remote split proven (TC-8.2)
- gateway replay blocked (TC-8.3)
- null-seam records cannot escape the quantifier
- successor_transfer_set byte-identical to provisional plan or intent-mismatch

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_promotion_gate.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-018, INV-020, INV-021; concerns RC-1, CB-4, SEC-1.
