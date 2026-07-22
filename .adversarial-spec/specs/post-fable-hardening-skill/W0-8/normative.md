# W0-8 Component Mini-Spec

Title: MW-005 PromotionPredicates (pure)

predicates.py: pure functions over validated types. is_concrete exact enum equality; is_promotion_ready six typed conditions incl. provenance condition 6; is_obligation_satisfied with critical_seam != null precondition and independent skip/deferred disjuncts (provisional pre-commit / committed post-commit, parent-scoped); select_for_verification.

Acceptance criteria:
- DF-5 mutation matrix green (closed-enum rejection, null-seam override)
- TC-8.9 identity mutants rejected
- TC-7.3 selection-predicate mutants detected

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task W0-8.
Implementation status: greenfield — predicates exist only as spec prose; no predicates.py
