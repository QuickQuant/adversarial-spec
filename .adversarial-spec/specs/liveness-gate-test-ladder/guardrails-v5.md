# Guardrails — spec-draft-v5 (post-R4 reframe-validation)

> Round: R4 (focused trust-model-reframe validation) | Spec: spec-draft-v5.md
> Inputs: v5 spec text + requirements_summary (SCOPE) + roadmap manifest/US (TRACE/TCOV) + canonical
> contract index / architecture-invariants.json (CANON/TCOV). Run inline by Claude (final evaluator).

## CONS (consistency_auditor) — PASS (1 inline fix)
Scanned for reframe residue (skill-side-"mechanical" / "tests-pseudo.md authoritative-or-emit" leftovers):
- §6 head, coverage-check bullet, dependency bullet: now consistently "advisory + parses `tmr-registry.json`"
  (no skill-side-mechanical or `tests-pseudo.md`-spine-tag residue). ✓
- §0.2 goal-1 ↔ §1 activation rule ↔ §6 placement: aligned (impossibility valid only post-Fizzy-gate). ✓
- §8.2 resolver ↔ §12.4: aligned (Fizzy-card-ts authoritative). ✓
- **FIX:** §11 "TMR emission → validation" row said "skill (`tests-pseudo.md` emit)" — contradicts DD-1/R4-4
  (emission is registry records, LLM-compiled from prose). Corrected inline to
  "skill (`tmr-registry.json` records, LLM-compiled from prose)."

## SCOPE (scope_creep_detector) — PASS
v5's new surface (activation rule; normative checker CLI/exit-code/JSON contract; `version_fence_error`;
prose→LLM-compile authoring + echo-diff) are **specifications of existing requirements**, not new scope:
- activation rule + checker contract → harden **US-8** (deterministic F′ gate).
- Fizzy-ts fence + `version_fence_error` → harden **US-12** (version fence).
- prose+LLM-compile authoring → harden **US-15** (bootstrap) / **US-2** (authoring).
- handshake resolution → harden **US-1** (schema-first contract).
No new user stories; no out-of-scope additions.

## TRACE (requirements_tracer) — PASS 15/15
All 15 US retain a spec section + spine test (coverage map §13 intact). No coverage lost; R4 edits
strengthen US-1/8/12/15. The §13 coverage caveat (registry not yet populated for 14 spine tests) is a
known fixture-migration gap (§12.11), not a traceability break.

## CANON (canonical_type_auditor) — 1 FINDING (tracked: CANON-r4-1)
The INV-003 reframe + the new named types finalized in v5 are **NOT yet mirrored** into
`target-architecture.md` / `architecture-invariants.json`:
- `INV-003` still encodes the pre-reframe "skill-side primary / no dispatch path bypasses all layers."
- New named types absent from the invariants file: the `gauntlet-check` **F′ checker contract**
  (CLI + exit-code taxonomy 0/2/3/4 + output-JSON schema), `ContractVersionResolver`, `version_fence_error`.
→ **Spec-vs-architecture drift. Tracked remediation CANON-r4-1**: mirror INV-003 reframe + the new named
  types/exit-code taxonomy into `architecture-invariants.json` and `target-architecture.md` (next pass,
  per session next_action). Expected debt, surfaced — not silently passed.

## TCOV (test_coverage_auditor) — 1 FINDING (deliberately folded into TCOV-r4-1)
v5's new behaviors lack falsifying oracles in `tests-pseudo.md`:
(a) checker exit-code taxonomy 0/2/3/4 + Fizzy **fail-closed** on each non-pass (not-found/timeout/bad-JSON/
    version-mismatch/stale-hash);
(b) `ContractVersionResolver` read-order — Fizzy-ts authoritative; card-present-but-unfetchable →
    fail-closed + `version_fence_error`; cardless → local fallback; missing/malformed → fail-closed;
(c) activation-rule **integration test** — direct `pipeline_advance` fails closed without F′ evidence
    (Fizzy-owned, but referenced as a release-gate);
(d) prose→LLM-compile **validate-on-emit** (malformed → `schema_error`) + **round-trip echo-diff** guard.
→ **Deliberately deferred into tracked TCOV-r4-1** (§12.11 registry migration): `tests-pseudo.md` is being
  migrated to `tmr-registry.json` under R4-4, so these R4 test cases are authored **during** that migration,
  not before — avoids writing tests in the about-to-be-replaced markdown format. Gap surfaced + tracked.

## Verdict
v5 internally consistent (1 CONS fix applied). 2 tracked items carried forward (both expected, neither
blocks): **CANON-r4-1** (architecture mirror) and **TCOV-r4-1** (R4 oracles, folded into the registry
migration). Trust-model reframe **validated by R4 and hardened**; no design reversal.
