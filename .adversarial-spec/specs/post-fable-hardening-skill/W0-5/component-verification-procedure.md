# W0-5 Component Verification

Task: Safe-path resolver + filesystem capability probes

Acceptance criteria:
- intermediate-symlink substitution blocked (TC-1.5)
- induced submount rejected (DF-8)
- unsupported filesystem is a named capability failure, never silent

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_safe_paths.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-006, INV-012; concerns US-1-theme.
