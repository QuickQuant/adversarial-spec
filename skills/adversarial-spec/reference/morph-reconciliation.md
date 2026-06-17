# User-Story Morph Reconciliation

> Load when incorporating a spec revision (debate-round, gauntlet fold, Phase-4 arch
> reconcile) that **deletes, relocates, or absorbs a capability**. Invoked from
> `03-debate.md` (Test-Spec Sync gate) and `05-gauntlet.md` (Step 6b synthesis). Glossary:
> "user-story morph" in `CONTEXT.md`.

## The class

A **user-story morph**: a design decision (a gauntlet concern fold, a `DR-N`, a debate
critique, an architecture invariant change, a lookup resolution, an operator fork, a
cross-spec scope split) changes the spec so a user story's **center of gravity moves** —
but the US's *anchor artifacts* keep pointing at the old center:

- its **scope statement** (the `## N. …` section / `<!-- Addresses US-x -->`),
- its **coverage-map row** (the §-coverage-map: US → section → spine test),
- and above all its **happy-path spine test** (`TC-N.0 [spine]`).

The US did not disappear and its tests did not dangle a deleted *identifier* — so the
ordinary consistency check ("0 live refs to deleted machinery", a grep) sails past it.
The failure is **semantic, not lexical**: the spine test still parses, still names no
dead symbol, but its *premise* is a behavior the spec no longer has.

**Canonical incident:** v8→v9 of the liveness-gate spec. `DR-5` deleted
`TestInputCollector` (raw test-source ingestion) and relocated coverage to the shared
`SpineCoverageChecker` (US-8 / F′). US-7's spine `TC-7.0` ("TCOV ingests standalone test
files into its input manifest") was left testing the deleted behavior. The v9 consistency
check claimed "0 live refs" because `TC-7.0` said *"ingests standalone files"*, never
`"TestInputCollector"`. Grep-clean, semantically rotten — the exact drift this whole spec
exists to prevent, reproduced in the spec's own test ladder.

## WHEN a morph can occur

The cross-product of **where the decision comes from** × **what it does to a capability**.

**Decision sources** (every pipeline event that revises the spec):
1. **Debate-round incorporation** (Phase 3) — a critic merges/relocates/removes a capability.
2. **Guardrail disposition** (Phase 3) — SCOPE→remove, CANON→contract moved, TRACE→coverage reorg.
3. **Gauntlet concern fold** (Phase 5) — an accepted concern deletes/relocates a capability.
4. **Target-architecture reconciliation** (Phase 4) — an invariant change re-homes a capability.
5. **Lookup resolution** (cross-phase) — a lookup reveals the capability already exists or
   lives elsewhere → a build-US becomes a verify/port-US (a **phantom-hole**), or externalizes.
6. **Operator design fork** (any phase) — a settled fork deletes/moves a capability.
7. **Cross-spec scope split** (any phase) — a capability is reassigned to a sibling spec/repo.

**Morph verbs** (what the disposition does to the capability):
`delete` · `relocate` (intra-spec) · `externalize` (to another spec/repo) · `absorb`/`merge`
· `split` · `reframe` (meaning flips, mechanism stays — e.g. a "security control" becomes a
"correctness rule").

**Detection is two-layer (push + pull) so it does not rely on memory:**
- **Push (decision-time):** every logged decision (`DR-N`, concern disposition, guardrail
  finding) carries a disposition. **If the disposition's verb is in the morph-verb set and
  names a capability → a morph is possible → run the procedure.**
- **Pull (gate-time backstop):** the Step-5 verification oracle (`orphaned_spine`) **also
  runs standalone every round** via the TCOV guardrail. If push detection is missed (a
  disposition went un-tagged), the next round's scan catches the orphaned spine anyway.
  Defense in depth — the same fail-closed posture the pipeline preaches.

## The procedure

Runs as a sub-step of every spec-revision incorporation.

**Step 0 — Gate-in (detect).** After applying a decision set to the body, scan dispositions
for a morph verb on a named capability. None → no morph; skip. Any → run Steps 1–5 per
affected capability.

**Step 1 — Migration ledger.** Write `capability → disposition`
(`deleted` | `relocated→US-x` | `externalized→repo` | `absorbed→US-x` | `split→{US-a,US-b}`
| `reframed`) **and** `which user stories anchored it` (from the coverage map + scope
statements).

**Step 2 — Classify each affected US's fate.** Decision rule: *does a distinctive
deliverable survive in this US that no other US owns?*

| Fate | Condition | Action |
|---|---|---|
| **Intact** | only a peripheral part was touched | prune dangling refs only |
| **Re-centered** | a distinctive survivor exists and becomes the new primary | keep the number; rewrite scope + **spine** to the survivor; demote leftovers to secondary |
| **Absorbed / Dissolved** | nothing distinctive survives (all pieces have homes elsewhere) | redistribute pieces; delete the US; renumber the coverage map |
| **Split** | the decision fractured one US into two distinct concerns | two user stories, two spines |

**Step 3 — Reconcile artifacts in fixed order** (so nothing is skipped):
scope statement → **spine test** → coverage-map row → branch tests →
cross-refs (information-flow table, invariants/architecture, glossary, coverage caveats).

**Step 4 — Record the morph (lineage).** Tombstone the dead spine; supersede with the new
one; journal the morph with `driver = <decision id>`. Use the spec's own lineage primitives
where they exist (a `status: tombstoned` / `supersedes` field, a rename/split/merge journal
record, a provenance-journal entry). Where they do not, one line in the spec changelog +
`sessions/<id>.decisions.log`.

**Step 5 — Verify (the oracle that was missing).** A hard + soft pair:
- **hard:** no test references a deleted identifier (the grep).
- **soft (LLM):** for every US, its spine's premise must resolve to a capability the
  *current* spec body still describes. New finding type: `orphaned_spine` /
  `spine_subject_relocated` (lives in the TCOV guardrail, §`adversaries.py`).

Any `orphaned_spine` finding → back to Step 2 for that US.

## Worked example — US-7 (Re-centered)

- **Step 1:** `coverage → relocated→US-8`; `TestInputCollector → deleted`; both anchored US-7.
- **Step 2:** distinctive survivor = `missing_liveness_test` (owned by no other US) →
  **Re-centered**.
- **Step 3:** rewrite `TC-7.0` from the deleted ingest-files behavior to the liveness
  happy-path (a critical seam *with* a real/induced test passes TCOV — the positive
  counterpart to `TC-7.1`'s `LIV-POS/LIV-NEG`); fix the §13 coverage-map row
  (`ingest-all` → the liveness deliverable); demote promoter (rule lives in US-4) and
  `data_strategy_mismatch` (rule lives in US-3) to secondary TCOV findings.
- **Step 4/5:** record the morph in the changelog; confirm hard grep + soft scan show 0
  orphaned spines.

## Deferred formalization (do not over-box yet)

This flow is structurally identical to the spec's own lineage model: a re-centered spine is
a `tombstone` + `supersedes`; a morph is a `rename`/`split`/`merge` event; the driver is a
provenance-journal record. The eventual schema home is `subject_type: user_story` alongside
`{test, node}` in the provenance journal (the journal already generalizes over subject
types). Capture the **workflow** (this doc + the phase-doc hooks + the TCOV oracle) now;
formalize the **schema** after it proves out.
