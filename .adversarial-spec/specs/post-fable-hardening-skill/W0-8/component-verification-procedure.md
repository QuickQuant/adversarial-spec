# W0-8 Component Verification

Task: MW-005 PromotionPredicates (pure)

Acceptance criteria:
- DF-5 mutation matrix green (closed-enum rejection, null-seam override)
- TC-8.9 identity mutants rejected
- TC-7.3 selection-predicate mutants detected

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_promotion_predicates.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-021; concerns CB-4, RC-1.
