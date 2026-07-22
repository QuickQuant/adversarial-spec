# B-3 Component Verification

Task: record_verification_evidence.py write-back + maturity authority

Acceptance criteria:
- card completion without registry update cannot count promotion-ready
- concurrency conflict retries from fresh read
- green-but-wrong evidence rejected (TC-8.4)

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_record_verification_evidence.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-003, INV-009; concerns RC-3, DD-3.
