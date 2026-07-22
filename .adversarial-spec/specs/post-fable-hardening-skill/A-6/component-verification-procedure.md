# A-6 Component Verification

Task: Waiver flow: challenge, receipt acceptance, audit cache

Acceptance criteria:
- full 5.4 rejection set green (TC-15.x)
- wrong-block/reused-nonce replay rejected (TC-15.4)
- lost response returns original receipt by operation_id (TC-15.7)

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_waiver_flow.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-002, INV-006; concerns SEC-4.
