# B-9 Component Verification

Task: Contract boundary: registry, capability probes, plan lint

Acceptance criteria:
- incompatible contract blocks advance (TC-16.3)
- live-preflight-unavailable vs local deferred distinguished (TC-3.3)
- fingerprint drift = state-stale (DF-3)
- contract-list drift fails reconciliation (DF-16)

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_contract_boundary.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-007, INV-010; concerns SEC-5, CB-1, DD-3.
