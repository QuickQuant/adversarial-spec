# W0-9 Component Verification

Task: MW-009 AuthorizationSetBuilder

Acceptance criteria:
- mixed-generation/caller-curated sets structurally impossible
- shuffled/duplicated facts rejected
- provisional vs committed sets hash differently (OR-1)

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_authorization_set_builder.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-020, INV-024; concerns SEC-1, CB-2.
