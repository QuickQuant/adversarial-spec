# B-7 Component Verification

Task: ConOps walkthrough: script gen + typed predicates + evidence binding

Acceptance criteria:
- swapped/stale evidence rejected (TC-9.3)
- typed-predicate mismatch + human-judgment routing (TC-9.4)
- worked-fine prose fails
- conductor-only critical evidence insufficient

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_conops_walkthrough.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-013, INV-021; concerns SEC-3, DD-3.
