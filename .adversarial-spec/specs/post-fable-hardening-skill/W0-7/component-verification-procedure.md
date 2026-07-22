# W0-7 Component Verification

Task: MW-004 ReceiptVerifier + TrustPolicy

Acceptance criteria:
- wrong-purpose key rejected across all receipt kinds (TC-15.8)
- DF-2 rotation/wrong-root/epoch-chain cases green
- signature validity without purpose authorization never authorizes

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_receipt_verifier.py skills/adversarial-spec/scripts/tests/test_trust_policy.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-006, INV-010, INV-024; concerns SEC-1, SEC-2, SEC-4.
