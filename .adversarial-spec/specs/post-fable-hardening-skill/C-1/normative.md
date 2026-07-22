# C-1 Component Mini-Spec

Title: reconcile_derived.py: 4 adapters + lineage + snapshot consistency

In-process adapter registry (tests-pseudo, tmr-registry, architecture-invariants, node-registry) with per-adapter dirty contracts + semantic_binding_fingerprint; reconciliation/lineage-map.json authored at refactor time, both-fingerprints-resolve validation; ONE immutable source snapshot per run with mixed-generation invalidation; envelope report bound to exact spec hash; --self-check for BOOT-RECON; hosts contract-list drift check.

Acceptance criteria:
- rename without lineage dirty despite resolving anchor (TC-13.3/13.5)
- snapshot consistency + lineage artifact (TC-13.7)
- unavailable adapter blocks dispatch and convergence

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task C-1.
Implementation status: greenfield — reconcile_derived.py absent (verified)
