# W0-1 Component Verification

Task: Scaffold hardening package + Python 3.14 floor

Acceptance criteria:
- hardening package imports cleanly on 3.14
- uv run adversarial-spec --help still works (symlink bridge preserved)
- clean-env wheel-install test green

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_hardening_package.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants n/a; concerns n/a.
