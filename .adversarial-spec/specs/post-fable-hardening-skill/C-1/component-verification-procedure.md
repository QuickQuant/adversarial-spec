# C-1 Component Verification

Task: reconcile_derived.py: 4 adapters + lineage + snapshot consistency

Acceptance criteria:
- rename without lineage dirty despite resolving anchor (TC-13.3/13.5)
- snapshot consistency + lineage artifact (TC-13.7)
- unavailable adapter blocks dispatch and convergence

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_reconcile_derived.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-013, INV-022; concerns US-3-theme, DD-3.
