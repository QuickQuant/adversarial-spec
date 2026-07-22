# W0-12 Component Verification

Task: MW-007 RemoteAuthorityClient

Acceptance criteria:
- success tokens are real values, never exception-shaped (TC-8.11)
- fingerprint drift detected as state-stale (DF-3)
- recorded-fixture probes for all 9 consumed contracts (hermetic)

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_remote_authority_client.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-004, INV-007, INV-017, INV-019; concerns CB-1, SEC-5, RC-1, FM-3.
