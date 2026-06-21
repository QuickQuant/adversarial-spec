# Maintain the altitude tree as a living per-round structured artifact

The **altitude tree** (system → subsystem → component nodes, `decomposes_into` edges,
`realizes_refs` to user stories, per-node spec paths and verification bindings) is today
**sketched as prose** in `target-architecture.md` at Phase 4, and only becomes a structured
JSON artifact at Phase 7 (`fizzy-plan.json`). The architecture artifacts are already revised
per spec round (`architecture-invariants.json` carries `generated_for_spec` / `spec_version`
and a reconciliation block), but the *tree itself* is not machine-readable until the end.

Decision: **emit the altitude tree as a structured `altitude-tree.json` from Phase 4 onward,
re-synced each spec round** as the design firms up (it is expected to shift a little per
round). `fizzy-plan.json` becomes the **frozen Phase-7 snapshot** of that living tree — the
point where the binding hashes lock in — rather than the first time the tree exists in
structured form.

Rationale: (a) it lets debate and the gauntlet run **at the subsystem/component altitude** —
the altitude-scaled quorum/intensity tables already exist in code but can't fire without a
per-altitude structure to review; (b) it lets the board **surface the decomposition early**
(the fizzy `stacked-card-visibility` pre-plan depends on a structured early tree); (c) it
keeps churn **cheap** — a JSON doc revised per round, not materialized cards thrashing on an
unstable spec.

## Considered options

- **3a — structured `altitude-tree.json` from Phase 4, re-synced per round; `fizzy-plan.json`
  = the Phase-7 snapshot (chosen).** Gets early, machine-readable structure at document cost;
  the existing Phase-7 reconciliation becomes a snapshot rather than a rescue.
- **3b — status quo: tree stays prose until Phase 7.** Rejected: compresses the V's whole
  descending arm into one step; review is monolithic (one spec, one debate, one gauntlet);
  the board has nothing structured to render during the session.
- **3c — materialize the tree as board *cards* at Phase 4.** Rejected: every
  architecture-changing debate round would churn the card tree (orphans, re-parenting, broken
  bindings) — the exact reason materialization currently waits for Finalization. The
  structured-JSON form gets the early structure without the card churn.

## Consequences

- Phase 4 gains a structured emit; Phase 7's `fizzy-plan.json` emission **re-roots on the
  snapshot** instead of re-deriving the tree from prose.
- The tree is **provisional until the Phase-7 snapshot** — consumers (including the board)
  must treat pre-snapshot structure as subject to change each round.
- **Unblocks** per-altitude debate/gauntlet and the fizzy stacked-card-visibility feature.
- The structured tree is now a **cross-repo contract** the board reads — version/stabilize
  its schema as we do for `fizzy-plan.json`.
