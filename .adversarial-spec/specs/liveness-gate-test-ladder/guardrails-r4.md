# Guardrail Report — Round 4 (post-gauntlet incorporation, spec-draft-v4.md)

> Session: adv-spec-202606151042-liveness-gate-test-ladder | Card 5715 | Post-gauntlet
> Evaluated inline by Claude (spec fits in context). Trigger: gauntlet Step 7 — CONS always;
> CANON (named types changed) + TCOV (test-parsing changed) conditionally required.
> Incorporated this pass: CB-1..7 (self-contradictions) + trust-model reframe (SEC-1/2/3/4, DD-1).

## CONS (consistency_auditor) — PASS (2 fixes applied inline)

Cross-section consistency verified after the trust-model reframe:
- §0.2 "impossible (via Fizzy-enforced path)" ↔ §1 "fizzy hard dependency" ↔ §6 "Fizzy-side mechanical
  gate" ↔ §1.1 non-goal ↔ §12.9 — **consistent** (skill-side = fail-fast everywhere).
- §3 piece-1 "tmr-registry.json system of record / tests-pseudo.md generated view" ↔ §4.2 ↔ §6 "F′ parses
  registry" ↔ §11 flow ↔ §12.11/13 — **consistent**; resolves the v3 §3-vs-§4.2 source-of-truth contradiction.
- §8.1 run_evidence typed receipt ↔ §3.1 receipt row (field lists match) — **consistent**.
- §8.2 ContractVersionResolver ↔ §12.4 resolved ↔ header changelog — **consistent**.

**Fixed inline (sequencing ripples — CB landed before DD-1):**
1. §2 step 2 referenced an embedded `TMR:` block (CB-7 wording) — corrected to a `tmr-registry.json` record
   (DD-1); flagged authoring-UX as §12.13.
2. §2 step 5 implied the skill-side gate was authoritative — annotated as the fail-fast advisory; mechanical
   block is Fizzy-side (SEC-1).

**Residual (LOW — deferred, tracked):** the §2 Getting Started bootstrap still describes the pre-DD-1 authoring
flow at a high level and needs a fuller registry-aware rewrite once §12.13 (authoring UX) is decided. Not a
contradiction now (annotated), but a completeness gap. → next pass.

## CANON (canonical_consistency) — 1 MEDIUM finding

New named types introduced this pass are used consistently within the spec: `tmr-registry.json` (×8),
`TmrParser` (= MW-001, consistent with `middleware-candidates.json`), `ContractVersionResolver`,
`fence_cutover_ts`, the run_evidence typed-receipt field set (§3.1 row == §8.1 list). ✓

**CANON-r4-1 (MEDIUM): cross-artifact invariant drift.** The INV-003 reframe (skill-side PRIMARY →
Fizzy-side mechanical; SEC-1) and the new named types live only in `spec-draft-v4.md`. The published
`target-architecture.md` + `architecture-invariants.json` still carry the **old** INV-003 ("no dispatch path
bypasses all three layers") and the embedded-TMR-block model (DD-1). These must be mirrored or the architecture
artifacts contradict the spec the gauntlet just hardened. → **action:** update target-architecture invariants
(INV-003 reframe; INV-008/009 if affected by registry + classifier) before finalize. *(Carried to §12.12 scope.)*

## TCOV (test_coverage_auditor) — 1 MEDIUM finding

**TCOV-r4-1 (MEDIUM): test ladder references the superseded embedded-YAML model.** DD-1 moved TMR records to
`tmr-registry.json`, but `tests-pseudo.md` TC-1.0 ("parse a real tests-pseudo `TMR:` YAML block") and the TC-8.0
exemplar are written against embedded markdown YAML. Post-DD-1 the oracle is "parse a registry record." →
**action:** rewrite TC-1.0/TC-8.0 (and the 14 other `[spine]` tests) against the registry + add a prose-view
round-trip test. Already tracked as **§12.11** (test-ladder → registry migration). No weakened oracle introduced
by the spec edits themselves; this is migration debt the storage decision creates.

## SCOPE / TRACE — not run (not applicable this pass)

Gauntlet fixes were evaluated by Claude (not automated scope additions); no user-visible scope expansion and no
requirement-coverage change beyond the tracked open items. Per gauntlet Step 7, SCOPE/TRACE are not required here.

---

## Verdict

CONS **pass** (2 inline fixes). CANON + TCOV each surface **1 MEDIUM** — both are *cross-artifact migration
debt* the trust-model decisions create (architecture invariants + test ladder must follow the spec), not
contradictions inside v4. Both are tracked (§12.11, §12.12). The spec is internally consistent; the medium
findings are the honest cost of the registry + Fizzy-gate decisions and belong in the next incorporation pass.
