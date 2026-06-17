# Guardrail Report — Round 2 (post-incorporation, spec-draft-v3.md)

> Session: adv-spec-202606151042-liveness-gate-test-ladder | Card 5715 | Round 2 (architecture)
> Evaluated inline by Claude. CONS now ACTIVE (v3 is a revision of v2).
> Inputs: spec-draft-v3.md, tests-pseudo.md, roadmap/manifest.json, requirements_summary,
> canonical TMR keystone (now incl. critical_seam + criticality_source).

## CONS (consistency_auditor) — PASS (0 findings)
- The one v2 internal inconsistency (R2-M1: §2.1 "≥acceptance" vs §6/TC-8.2 "nl passes") is
  reconciled — F′ accepts `nl|acceptance|concrete` at debate→gauntlet everywhere.
- §3.1 enum table (now incl. `critical_seam`/`criticality_source`/`binding_status`) consistent with
  §3.3 and the keystone; §6 skill-side-primary placement consistent with §12.9; §4.2 structured TMR
  block consistent with §6 parse + TC-8.0 exemplar; §7.1 journal-from-state-changes consistent with
  §7.2 node drivers; §12.10 resolution (no subject_type:session) consistent with §7. No duplicate
  numbering / arithmetic drift.

## SCOPE (scope_creep_detector) — PASS (0 findings)
- `critical_seam`/`criticality_source` are in-scope enablers of feature D (`missing_liveness_test`),
  now promoted to real keystone fields — no new scope.
- The journal `subject_type:session` expansion (gemini R2-H5) was **actively rejected** to avoid
  scope-creeping the provenance journal; overrides stay in decisions.log. Net scope unchanged.

## TRACE (requirements_tracer) — PASS (0 findings)
- All 15 user stories retain a spec section + a happy-path spine test (§13 map intact).

## CANON (canonical_type_auditor) — PASS (R1 finding CLOSED)
- The R1 CANON drift (spec referenced `critical_seam`, absent from the canonical contract) is
  **resolved**: `critical_seam` + `criticality_source` were added to the canonical keystone
  (`…/test-maturity-record-schema.md` §1 enums + §2 TMR + decision-6 marker). The spec no longer
  references any field absent from the single-source contract. All other enums verified to match.
- Open: fizzy P0 must validate the two new fields (coordination item §12.7) — cross-spec, not a drift
  in this spec.

## TCOV (test_coverage_auditor) — findings DEFERRED to R3 (none contradict v3)
- (a) **Full structured-`TMR:`-block conversion of remaining TCs** — §4.2 now requires the block per
  test; TC-8.0 carries the exemplar. Converting all ~30 TCs is an `acceptance`-maturity activity
  (they are `nl` now); schedule in R3/early-execution. Not blocking at debate.
- (b) **ORCH fail-closed test** — §5.1 adds a synthetic blocking `ORCH` finding on subagent
  death/timeout/invalid-JSON; add a test (block on gauntlet, warn on critique). → R3 sync.
- (c) **Conflict-state test** — §5.1 adds a `conflict` aggregation state; add a test that conflicting
  `required_action`s on the same target+field require disposition before any journaled transition.
  → R3 sync.
- Added this round: TC-7.2 (criticality_unknown fail-closed), TC-8.0 structured TMR exemplar +
  skill-side-primary placement.

## Summary
CONS pass · SCOPE pass · TRACE pass · CANON pass (R1 finding closed) · TCOV 3 deferred-to-R3.
No blocking guardrail failures. Cleared to record R2. Convergence NOT declared (both critics
agreed=false; R2 findings were all design-refinements, both models agreeing — strong convergence
trend: R1 12 findings → R2 ~9 refinements). Next: R3 (refinement) — expected convergence round.
