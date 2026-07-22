# W0-13 Component Verification

Task: MW-010 TmrRegistryWriter + sole-writer lint

Acceptance criteria:
- DF-7 stale-revision + same-txn invalidation green
- sole-writer lint catches a violating fixture module
- serves both mutation-kind owners

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_tmr_registry_writer.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-003, INV-008; concerns RC-3, DD-3.
