# B-10 Component Verification

Task: Regime lifecycle (spec 18): attestation, backfill, cross-regime transfer

Acceptance criteria:
- regime branch distinguishes by attestation never absence (TC-0.4)
- epoch-zero provisioning + immutable pre-rollout (TC-0.10)
- DF-10 regime-pair transfer matrix green
- local timestamp/manifest rewrite cannot decide regime

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_regime_lifecycle.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-002, INV-003, INV-014; concerns FM-1, FM-2, US-2-theme.
