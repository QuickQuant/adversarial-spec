# W0-11 Component Verification

Task: MW-006 LocalCapabilityVerifier + trusted-time watermark

Acceptance criteria:
- wall-clock rollback cannot extend authorization, incl. across restarts
- DF-2 skew + missing-release cases green
- TC-3.3 local deferred-for-live-preflight distinguished from remote tokens

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_local_capability_verifier.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-013, INV-014; concerns SEC-2, FM-1, CB-1.
