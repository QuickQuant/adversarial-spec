# A-5 Component Verification

Task: Phase-doc spine units + 09-verification relocation

Acceptance criteria:
- doclint pointer closure: zero dangling, exactly one owner
- 09-verification.md gone from old path; router resolves (TC-4.x/5.x)
- context-load-manifest records resolved unit identities + hashes

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_spine_units_closure.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-001, INV-013; concerns US-3-theme.
