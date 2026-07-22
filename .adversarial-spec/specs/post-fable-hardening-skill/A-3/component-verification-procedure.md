# A-3 Component Verification

Task: Judgment-gate corpus (rubrics + fixtures)

Acceptance criteria:
- every judgment row in gates.json has rubric + fixture
- fixtures schema-valid (TC-3.2)

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_judgment_corpus.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-001; concerns n/a.
