# Adversarial-Spec Pipeline — Shortcomings vs the NASA V-Model

> 2026-05-30. Written from the take/take chunk session (`adv-spec-202605281906-…`) at Phase 7 entry,
> after a full read of `spec-draft-v18.md` and the V-model comparison.
> Purpose: seed a future **recursive overhaul** — run adversarial-spec ON adversarial-spec itself.
> Every item names the specific file/procedure an overhaul would touch.

The pipeline maps the V's **left arm** (definition/decomposition) and **horizontal V&V-plan authoring**
very well, and adds adversarial iteration the classic V lacks. The gaps are concentrated in the
**ascending right arm** (verification → validation → commissioning) and in **enforcing traceability
bidirectionally**. The seven below are ordered by leverage.

---

## 1. Traceability is authored but not bidirectionally ENFORCED (the A1 defect class)
**V-model element:** the horizontal dashed arrows + the Traceability box — a requirement change must
propagate to its verification plan at the same level.
**What happened:** OD-1 reversed "command-freshness fail-closed in both postures." Its `Modifies:` list
named the requirement sections but omitted the Behavior Test Matrix, so **Tests 58 + 89 + summary L349
still encode the superseded rule** — Test 58 would now FAIL a correct implementation. No gate caught it.
**Files/procedures:**
- `debate.py` **Test-Spec Sync gate** — today it is an *mtime* comparison (`spec_path` mtime vs
  `tests_pseudo_path` mtime). Pure staleness, no content linkage.
- TRACE guardrail in `phases/03-debate.md`.
- The `Modifies:`/`Oracle:` convention emitted by `phases/05-gauntlet.md` → `phases/06-finalize.md`.
**Overhaul hook:** give every test a structured `verifies: <req/section/invariant id>` back-reference;
upgrade the Test-Spec Sync gate to a **supersession-propagation lint** — when a rule says "supersedes X"
or "Modifies §Y," fail finalize unless every test with `verifies: X|§Y` shows a delta or an explicit
"re-confirmed unchanged." This single change prevents the entire A1 class.

## 2. `Modifies:` / `Oracle:` are freeform prose, not validated links
**V-model element:** same traceability arrows — they must resolve to real targets.
**What happened:** "`Modifies:` Decision Algorithm Step 1, Step 11, Durable Authority…" is unparseable
prose, so the omission of the test matrix was invisible. Ironically our own spec's **DD-3** flags the
identical disease (flat-string `blockedReason` → `{category, code}`) — the spec metalanguage has the bug
it tells implementers to fix.
**Files:** the hardening-fold step in `phases/05-gauntlet.md` / `phases/06-finalize.md`.
**Overhaul hook:** make `Modifies:` a list of spec anchors and `Oracle:` a list of test ids, both
validated at finalize against a spec anchor-index + the test-matrix id set. Unresolved target → finalize
gate fails. (Apply DD-3 to ourselves.)

## 3. DD-2 "clean normative merge" is deferred to finalize but finalize never enforces it
**V-model element:** the left arm must END at a clean, current detailed design — not an archaeological
layer cake.
**What happened:** 14 debate rounds + gauntlet left v18 as nested "R8 supersedes R7 / OD-1 supersedes R8"
annotations across 1475 lines; the body is *intentionally stale* and a reader can't separate live rules
from history without the manual audit I just did (`v18-conflict-audit.md`, 12 catalogued body-vs-hardening
supersessions). `manifest.json` shows `blessed_final: true` WITH "DD-2 clean normative merge" still in
`deferred_followups` — finalize blessed a spec it admits is unmerged.
**Files:** `phases/06-finalize.md`; the manifest `blessed_final`/`deferred_followups` contract.
**Overhaul hook:** either (a) make `blessed_final: true` impossible while a clean-merge follow-up is open,
or (b) split artifacts from the start — `normative.md` (current rules only) vs `debate-history.md`
(the supersession lineage) — so supersession annotations never pollute the live spec. The V model's
detailed-design block is singular and current; ours accretes.

## 4. No ascending-arm phases: subsystem / system verification & validation as distinct gates
**V-model element:** Component → Subsystem → System Verification → System Validation (vs ConOps).
**What's missing:** the router goes `execution → implementation → complete`. Phase 8 + the fizzy
review/test lanes do per-**card** (component) verification only. Nothing (a) runs the full
`test-matrix.md` as a system-verification suite gating `complete`, or (b) re-validates against ConOps —
re-deriving pass/fail from the **User Journey** (`spec-draft-v18.md` L125-136) and **User Stories US-0..34**
end-to-end. The top dashed arrow (System Validation Plan ↔ ConOps) has no analog.
**Files:** `phases/08-implementation.md`; the `complete` row of the router in the skill body; fizzy
`pipeline_sweep` / `pipeline_review` lanes.
**Overhaul hook:** add `phases/09-system-verification.md` with two gates — *system verification*
(execute the entire matrix, gate `complete` on green) and *system validation* (assert every User Story +
invariant has a passing end-to-end test, not just per-card AC). Add the artifact to the per-phase
required-artifact table so `any → complete` blocks without it.

## 5. Verification EXECUTION evidence isn't traced back to close the V
**V-model element:** the ascending arrow verifies the SAME artifact the descending arrow planned.
**What's missing:** Phase 7 authors `verification_mode` / `test_refs` / `verify_commands` (down arrow),
Phase 8 produces evidence — but the existence of `pipeline_backfill_verification_evidence` implies
evidence routinely arrives detached from its declaration, and there's no requirement-level ledger closing
"test passed ⇒ requirement X verified."
**Files:** fizzy `pipeline_attest_task` / `pipeline_attest_steps` / `pipeline_backfill_verification_evidence`
/ `pipeline_commit_status`; the `declared_*`-vs-evidence field mapping in `phases/07-execution.md` L315-326.
**Overhaul hook:** a per-requirement verification ledger `{requirement/invariant/US → declared test ids →
execution results → verified?}`, rolled up at `complete`. That rollup IS the "System Verification Plan ✓"
checkmark the V expects and we never emit.

## 6. Gate enforcement is LLM honor-system, not programmatic
**What's wrong:** `phases/07-execution.md` states outright that gates V1-V4 are "LLM-enforced process
gates… not runtime-validated by fizzy-pipeline-mcp." A gate can be marked complete without its condition
truly holding; A1-class drift survives because nothing mechanically checks requirement↔test consistency.
**Files:** the "Nature of this gate" notes in `phases/07-execution.md`; `pipeline_validate_plan`
(exists, but plan-schema validation is advisory/warns, not a hard reject).
**Overhaul hook:** move the mechanically-checkable invariants into `pipeline_validate_plan` as hard
rejects — coverage non-empty, mode↔scope matrix valid, paths repo-relative, **every invariant covered by
≥1 task**, **every System-Level Requirement has ≥1 test_ref**. The V's rigor comes from plans being
checked artifacts, not intentions.

## 7. Adversarial pressure hits the spec, never the tests or the plan
**What's missing:** the gauntlet (9 adversaries) attacks `spec-draft-vN.md`. Nothing adversarially
attacks `test-matrix.md` ("does any oracle contradict a requirement or another oracle? is it falsifiable?
does it cover its requirement?") or `fizzy-plan.json` ("does this decomposition leave an invariant
uncovered?"). **A1 is exactly a test-suite self-contradiction a test-gauntlet would have caught.**
**Files:** `phases/05-gauntlet.md`; `debate.py gauntlet`; the personas in `reference/gauntlet-details.md`.
**Overhaul hook:** a `--target tests|plan` gauntlet mode reusing the adversary harness against the matrix
and the plan, with personas like "the oracle that contradicts its requirement," "the uncovered
invariant," "the unfalsifiable AC." This is the recursive-improvement move: point the program at its own
intermediate artifacts.

## (Bonus, lower leverage)
- **No commissioning / O&M bridge.** Pipeline ends at `complete`; the spec's own "Residual
  (post-implementation tuning)" (L1062-1064) + the 6 strong-guess defaults
  (`manifest.json:strong_guess_decisions_pending_operator_review`) have nowhere to land. Overhaul:
  `complete` emits an operations-handoff artifact (tuning list + monitoring oracles) into GitHub Issues
  (per `CLAUDE.md` issue-tracker).
- **Resume checks validate structure, not content freshness.** The canonical-phase-order +
  required-artifact table (skill body) confirm artifacts *exist*; only Phase 4's `spec_fingerprint` check
  verifies *currency*. Overhaul: generalize that fingerprint pattern to a resume-time **consistency matrix**
  (spec↔tests, spec↔user-stories, spec↔invariants); any drift flags dependents.

---

## The recursive-overhaul shortlist (highest leverage first)
1. **Bidirectional traceability lint** (#1+#2) — kills the A1 class. Touch `debate.py` Test-Spec Sync +
   the `Modifies:`/`Oracle:` format.
2. **finalize merge gate** (#3) — `blessed_final` can't coexist with an open clean-merge follow-up.
3. **Programmatic plan validation** (#6) — promote checkable gates into `pipeline_validate_plan`.
4. **Ascending-arm phase 09** (#4+#5) — system verification + ConOps validation + a verification ledger.
5. **Gauntlet the tests and the plan** (#7) — adversarial-spec applied to its own artifacts.
