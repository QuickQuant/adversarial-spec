# W0-14 Component Verification

Task: Authority-matrix lint + consumer tests

Acceptance criteria:
- DF-9 complete row coverage
- lint catches a fixture module reading a mirror directly

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_authority_matrix.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-003; concerns US-4-theme.
