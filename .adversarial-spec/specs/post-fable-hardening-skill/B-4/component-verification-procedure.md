# B-4 Component Verification

Task: criticality_classifier.py resolution extension

Acceptance criteria:
- sole-writer enforced by lint + runtime (TC-7.5)
- never defaults to false
- resolution records carry rule version + source hash

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_criticality_resolution.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-003; concerns CB-4, DD-3.
