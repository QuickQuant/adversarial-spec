# W0-3 Component Verification

Task: MW-008 CliBoundary

Acceptance criteria:
- abbreviation and unknown args rejected with envelope output
- every invocation emits exactly one result envelope
- --help is a successful help result

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_cli_boundary.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-004, INV-010, INV-016; concerns CB-1, FM-3.
