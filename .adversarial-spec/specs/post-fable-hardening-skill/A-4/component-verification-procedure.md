# A-4 Component Verification

Task: competence_harness.py + baselines + coverage manifest

Acceptance criteria:
- vacuous [] fails critical fixtures (TC-6.4)
- missing/incompatible baseline blocks (TC-6.5)
- 2-pass/2-fail scores exactly 50
- fingerprint drift => not-comparable (DF-12)

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_competence_harness.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-010; concerns OP-1.
