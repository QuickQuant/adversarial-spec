# W0-10 Component Verification

Task: MW-011 DurableOperationJournal

Acceptance criteria:
- crash before vs after dispatch distinguished by record presence (TC-8.12)
- same-id different-bytes retry = intent-mismatch
- DF-11 failure-injection table asserts owner/action/state

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_operation_journal.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-009, INV-017; concerns RC-2, FM-3, CB-1.
