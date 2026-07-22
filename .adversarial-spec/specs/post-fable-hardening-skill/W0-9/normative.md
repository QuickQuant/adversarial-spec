# W0-9 Component Mini-Spec

Title: MW-009 AuthorizationSetBuilder

authorization_set.py: validates receipts + successor inherited-obligation records against ONE registry generation into immutable ValidatedAuthorizationSet with authorization_set_hash per the exact spec formula; consumes TrustPolicySnapshot; emits canonical provisional transfer plan; obligation policy vs trust policy separation.

Acceptance criteria:
- mixed-generation/caller-curated sets structurally impossible
- shuffled/duplicated facts rejected
- provisional vs committed sets hash differently (OR-1)

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task W0-9.
Implementation status: greenfield — no builder exists
