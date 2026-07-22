# B-6 Component Verification

Task: Promotion remote sequence + authority-committed inheritance

Acceptance criteria:
- prepare without registered snapshot rejected (TC-8.10)
- parent completion never observable without transfer facts (TC-8.13)
- rematerialization path green (TC-8.14)
- retention/GC protection (TC-8.15)

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_promotion_sequence.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-017, INV-019, INV-020; concerns RC-1, SEC-3, FM-3.
