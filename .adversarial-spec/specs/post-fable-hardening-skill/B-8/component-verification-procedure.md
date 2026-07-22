# B-8 Component Verification

Task: Spine artifacts: close-binding DAG + BOOT-SPINE

Acceptance criteria:
- reverse edge rejected (TC-10.3)
- DF-18 envelope-field mutations under real generators
- missing-with-predecessor blocks

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_spine_artifacts.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-018; concerns CB-3.
