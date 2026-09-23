# User-Story Morph Reconciliation

> Load when a debate revision, architecture reconciliation, or gauntlet fold
> deletes, relocates, absorbs, splits, or reframes a capability. Phase 3 invokes
> this at Test-Spec Sync; Phase 5 invokes it during synthesis. See
> `CONTEXT.md` for the glossary definition.

## Trigger

A **user-story morph** occurs when a decision moves a user story's center of
gravity while its anchor artifacts still describe the old capability:

- scope statement (`## N. …` / `<!-- Addresses US-x -->`);
- coverage-map row (user story → section → happy-path spine test); or
- happy-path spine test (`TC-N.0 [spine]`).

This is semantic drift. A deleted identifier may have zero live references while
the happy-path spine test still asserts behavior the current specification no
longer provides.

### Decision sources

Check every spec-changing event:

1. debate-round incorporation;
2. guardrail disposition;
3. gauntlet concern fold;
4. target-architecture reconciliation;
5. lookup resolution that moves or externalizes ownership;
6. operator design fork; and
7. cross-spec or cross-repository scope split.

Morph verbs are `delete`, `relocate`, `externalize`, `absorb`, `merge`, `split`,
and `reframe`.

### Detection

- **Push at decision time:** if a disposition uses a morph verb on a named
  capability, run this procedure for every affected user story.
- **Pull at gate time:** run the TCOV `orphaned_spine` oracle after every round.
  This catches a morph whose disposition was not tagged.

## Procedure

### 0. Gate in

After applying the decision set to the document body, scan its dispositions.
No morph verb on a named capability means no reconciliation. Otherwise continue
for each affected capability.

### 1. Write the migration ledger

Record `capability → disposition` and the user stories that anchored it, using
the coverage map and scope statements. Valid dispositions are:

`deleted` · `relocated→US-x` · `externalized→repo` · `absorbed→US-x` ·
`split→{US-a,US-b}` · `reframed`

### 2. Classify each affected user story

Ask whether a distinctive deliverable survives that no other user story owns.

| Fate | Condition | Required action |
|---|---|---|
| **Intact** | Only a peripheral part changed. | Prune dangling references. |
| **Re-centered** | A distinctive survivor becomes primary. | Keep the number; rewrite scope and happy-path spine test; demote leftovers. |
| **Absorbed / Dissolved** | No distinctive deliverable remains. | Redistribute surviving pieces, delete the user story, and update the coverage map. |
| **Split** | Two distinct deliverables now exist. | Create two user stories and one happy-path spine test for each. |

### 3. Reconcile in fixed order

Update scope statement → happy-path spine test → coverage-map row → branch tests
→ cross-references (information flow, invariants/architecture, glossary, and
coverage caveats).

### 4. Record lineage

Where the current test/node lineage primitives apply, tombstone the obsolete
test, link its replacement with `supersedes`, and journal the morph with
`driver = <decision id>`. Otherwise record one concise entry in the spec
changelog and `sessions/<id>.decisions.log`.

### 5. Verify

Run both checks:

- **Hard:** no test references a deleted identifier.
- **Semantic:** every user story's happy-path spine premise resolves to a
  capability the current specification still describes. Use
  `orphaned_spine` / `spine_subject_relocated` findings.

Any `orphaned_spine` finding returns that user story to Step 2.

## Future provenance extension

**Design intent — not implemented:** add `subject_type: user_story` to the
provenance journal before recording user-story transitions there. The current
`SUBJECT_TYPES` and `JournalTransition.subject_type` accept only `test` and
`node`; do not write unsupported records in the meantime.
