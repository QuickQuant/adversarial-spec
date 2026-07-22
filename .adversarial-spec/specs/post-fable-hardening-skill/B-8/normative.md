# B-8 Component Mini-Spec

Title: Spine artifacts: close-binding DAG + BOOT-SPINE

spine-core.json -> evidence-index.json -> spine-manifest.json with schema-enforced acyclic references and exact hash projections; BOOT-SPINE transitive validation (schema + spine_core_hash + evidence_index_hash + node-registry hash).

Acceptance criteria:
- reverse edge rejected (TC-10.3)
- DF-18 envelope-field mutations under real generators
- missing-with-predecessor blocks

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task B-8.
Implementation status: greenfield — no spine artifacts exist
