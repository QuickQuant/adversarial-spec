# B-1 Component Verification

Task: TMR keystone-first schema extension (obligation fields)

Acceptance criteria:
- keystone edited before mirror (provable commit order)
- strict schema round-trip green
- obligation-identity projection hash stable under evidence-field changes

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_tmr_obligation_fields.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-024; concerns CB-2, DD-3.
