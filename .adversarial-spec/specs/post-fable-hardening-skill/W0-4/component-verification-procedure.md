# W0-4 Component Verification

Task: MW-002 DurableStateStore + StateTransaction

Acceptance criteria:
- DF-6 completeness matrix green (reversed-lock-order, held-lock timeout, sidecar attacks, GC-vs-lease)
- crash at every protocol boundary recovers or quarantines, never mixed state
- readers never observe two generations

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_durable_state_store.py skills/adversarial-spec/scripts/tests/test_state_transaction.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-008, INV-012; concerns RC-3, CB-2.
