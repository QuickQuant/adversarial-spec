# C-2 Component Verification

Task: Debate node registry: snapshot + hash-chained event log

Acceptance criteria:
- chain break detected (TC-12.3)
- corrupt artifacts preserved in place with named quarantine status
- resume restores the settled/volatile/derived split exactly

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_node_registry.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-008, INV-013; concerns RC-3.
