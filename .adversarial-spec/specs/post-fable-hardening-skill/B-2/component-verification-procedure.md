# B-2 Component Verification

Task: verification_cards.py deterministic emitter + board upsert

Acceptance criteria:
- identity stable across registry churn, zero duplicates (TC-7.4)
- empty selection emits no-op artifact with registry path+hash
- DF-7 stateful board fixture green

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_verification_cards.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-003, INV-013; concerns DD-3, RC-3.
