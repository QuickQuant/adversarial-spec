# W0-6 Component Verification

Task: MW-003 HashChainedJournal

Acceptance criteria:
- chain break detected at unit level
- anchored-head verification round-trips

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_hash_chained_journal.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-009, INV-013; concerns SEC-3, RC-3.
