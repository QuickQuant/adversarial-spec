# A-7 Component Verification

Task: hardening_bootstrap.py (BOOT-* checks + live preflight)

Acceptance criteria:
- fresh-clone clean run under 5 minutes with named checks (TC-0.0)
- regime branch distinguishes legacy/hardened/corrupt (TC-0.4)
- every blocking check passes under denied socket/DNS (TC-2.3)
- blocking precedence: advisory+blocking => exit 2

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_hardening_bootstrap.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-002, INV-014; concerns FM-1, CB-1, US-3-theme.
