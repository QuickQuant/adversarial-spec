# B-9 Component Mini-Spec

Title: Contract boundary: registry, capability probes, plan lint

Probe implementation for all 9 consumed contracts (signed challenge-response + negative probes + schema_sha256 behavior-fingerprint pinning + prepare/commit revalidation); registry-vs-contract-boundary.md drift check; execution-plan lint failing fizzy-repo-scoped tasks; per-delta G3 tracking pointers.

Acceptance criteria:
- incompatible contract blocks advance (TC-16.3)
- live-preflight-unavailable vs local deferred distinguished (TC-3.3)
- fingerprint drift = state-stale (DF-3)
- contract-list drift fails reconciliation (DF-16)

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task B-9.
Implementation status: partial — contract-boundary.md EXISTS (Phase 4 artifact, hash-bound); probe CODE + lint new
