# Guardrail Report — Round 1 (post-incorporation, spec-draft-v2.md)

> Session: adv-spec-202606151042-liveness-gate-test-ladder | Card 5715 | Round 1
> Evaluated inline by Claude (spec fits in context). CONS exempt on first draft.
> Inputs: spec-draft-v2.md, tests-pseudo.md, roadmap/manifest.json, requirements_summary,
> canonical TMR keystone (Brainquarters/shared-context/test-maturity-record-schema.md).

## CONS (consistency_auditor) — EXEMPT
First-draft exemption: CONS compares sections against each other; only meaningful after revision
introduces cross-section drift. Runs from R2 onward.

## SCOPE (scope_creep_detector) — PASS (1 note)
- Spec maps to requirements features A/B/C/D/F′/G/H/J/K + keystone + verification-tiers + version-fence.
- **Note (not a violation):** the R1-added `critical_seam` classification field (§3.3) is an in-scope
  refinement enabling feature D's `missing_liveness_test` to be operational — but it **expands the
  shared keystone TMR contract**, which the coordinated fizzy spec must mirror field-for-field.
  Tracked as the §12.7 coordination item. Approved as in-scope; flagged for cross-spec handshake.

## TRACE (requirements_tracer) — PASS (0 findings)
- All 15 user stories (US-1..US-15) retain a spec section AND a happy-path spine test (§13 coverage
  map intact; cross-checked against roadmap/manifest.json milestones[].user_stories[]).
- No requirement lost coverage in the v1→v2 incorporation.

## CANON (canonical_type_auditor) — 1 finding (ADDRESSED in-spec)
- **Finding:** §3.3 references a `critical_seam` field that is NOT present in the canonical keystone
  file. Referencing a field absent from the single-source contract is exactly the divergence this
  work exists to prevent (US-1).
- **Disposition:** ADDRESSED — §3.3 explicitly marks `critical_seam` as a **proposed keystone
  addition, pending field-for-field agreement with the fizzy spec** (schema-first handshake), not as
  an existing field. The canonical shared-context file is **not** edited unilaterally; the amendment
  rides the §12.7 coordination item. All other named enums (`maturity`, `data_strategy`,
  `live_or_induced`, `verification_mode`/scope/altitude/tested_by) verified to match the keystone
  field-for-field (code-confirmed against fizzy pipeline.py, lookup L4).

## TCOV (test_coverage_auditor) — 2 findings
- **(a) FOLDED:** TC-13.0 was a doc-lint that could flag machine tokens. Updated to lint **prose
  only** — the keystone tokens `spine`/`spine_steps`/`spine_step_ref`/`[spine]` are exempt (per spec
  §4.1 prose-vs-token rule). Resolved in this round's tests-pseudo update.
- **(b) DEFERRED → R2 sync:** §3.3 introduces fail-closed `criticality_unknown` behavior with no
  dedicated test yet. Add a TC asserting an un-classifiable system-altitude happy-path is treated as
  critical (fail-closed). Does not contradict v2; scheduled for the R2 Test-Spec Sync once
  `critical_seam` firms up via the fizzy handshake.
- Strengthened this round (from R1 critiques, now in tests-pseudo): TC-1.0 semantic round-trip +
  TC-1.2 missing-field; TC-3.0/3.1 MOCK-rule corrected; TC-7.0 re-tiered to code; TC-7.1 planted IDs
  + negative case; TC-8.4 duplicate-spine; TC-14.0 canonical mode; TC-15.1 affirmative-only.

## Summary
CONS exempt · SCOPE pass · TRACE pass · CANON 1 (addressed) · TCOV 2 (1 folded, 1 deferred R2).
No blocking guardrail failures. Cleared to record R1 and proceed to the Context Readiness Audit → R2.
