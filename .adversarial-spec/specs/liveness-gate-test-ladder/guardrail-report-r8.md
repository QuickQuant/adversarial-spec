# Guardrail report — R8 incorporation (spec-draft-v10) — 2026-06-16

Spec: spec-draft-v10.md (1139L) | Tests: tests-pseudo.md (460L)
Round 8 critics: codex/gpt-5.5 (10) + claude-opus-4.7 (4); gemini-3.1-pro quota-substituted.
v10 = v9 + 19 R8 patches (11 spec-side a-k, 8 test-side l-s). Authored by delegated subagent,
conductor-validated (US-8 morph + §3.1 status/partition + §8.1 matrix + ULID + §6 trust-model-intact
spot-checked via grep + targeted reads).

Morph gate-in (Test-Spec Sync Step 0): a SECOND user-story morph was caught (US-8, both critics) and
reconciled via reference/morph-reconciliation.md — Fate = Re-centered (TC-8.0 + TC-INV-001 re-centered
on the Fizzy mechanical gauntlet-entry gate; skill-side advisory; negative oracle added). 0 orphaned spines.

## Results

| Guardrail | Verdict | Notes |
|---|---|---|
| CONS | PASS | override-floor consistent (no live ≥50; only frozen v7 changelog + v10 "fixed" note); tmr_uid identity consistent §3/§4.2/§7; status enum §3.1/§4.2/§6; run_evidence union §3.1/§8.1/tests; §8.1 matrix replaced prose (no dup) |
| SCOPE | PASS | all edits are corrections to existing US/sections; TC-3.2 tests existing DR-8; no new capability |
| TRACE | PASS | 15/15 US covered; §13 map intact; TC-8.0 still US-8 spine (re-centered, not removed) |
| CANON | PASS (1 tracked) | v10 FIXED a missing-enum drift (status was absent from §3.1). TRACKED to finalize: mirror `status`/lifecycle into architecture-invariants.json + regenerate §3.1 schema_sha256 snapshot (same class as CANON-r4-1). Non-blocking. |
| TCOV | PASS (improved) | orphaned_spine oracle: 0 orphaned spines; DR-8 negative (TC-3.2) added; US-8 Fizzy-refuses-advance negative oracle added; run_evidence union shapes fixed across tests |

## Tracked-to-finalize (non-blocking)
- CANON: architecture-invariants.json `status`/lifecycle mirror + §3.1 `schema_sha256` regen (folds with CANON-r4-1).
- §12 open item 11: 14 spine tests still need tmr-registry.json records (R4-4 compile) — pre-existing, unchanged by R8.

## Verdict
v10 incorporation clean. Ready to record R8 (convergence=false) and dispatch R9.
