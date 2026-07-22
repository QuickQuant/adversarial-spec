# B-7 Component Mini-Spec

Title: ConOps walkthrough: script gen + typed predicates + evidence binding

conops-walkthrough.md generated from happy-path spine tests deriving rows SOLELY from roadmap/conops.md; typed expected-observation predicates per class (API/CLI/GUI/human-judgment routes to rubric); evidence binding (row_id, script hash, operator identity, timestamp, artifact hash, provenance class); close-verifier rejection of stale/swapped/wrong-script evidence; canonical hash-regeneration order.

Acceptance criteria:
- swapped/stale evidence rejected (TC-9.3)
- typed-predicate mismatch + human-judgment routing (TC-9.4)
- worked-fine prose fails
- conductor-only critical evidence insufficient

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task B-7.
Implementation status: partial — Phase 7 ConOps derive exists (validation_emission.py:688 handle_derive_conops); walkthrough layer new, EXTENDS it
