# B-11 Component Verification

Task: Phase 8 verification-subflow migration (OR-3 / DF-20)

Acceptance criteria:
- all four DF-20 guarantees red-green
- resume checker passes implementation -> (subflow) -> complete journey
- migrated session resumes cleanly

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_phase8_subflow_migration.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-002; concerns n/a.
