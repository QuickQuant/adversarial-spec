# Proposal: Two-matrix ownership tracking for CONS/CANON/SCOPE/TRACE

Status: **proposed, not implemented** — awaiting Jason's go/no-go.
Origin: 2026-07-09 prediction-prime session. Root incident: `exit_preview_records` was homed
in Convex (§10.5 "server-persisted") AND gateway SQLite (§18a migration-list placement) from
spec v3 through v4-finalize; CONS ran twice and never flagged it. Persona-level fix (category 7
SINGLE OWNER/HOME + structural-placement-is-a-claim + ENTITIES CHECKED tabulation) was applied
to `adversaries.py` same day — this proposal is the systematic upgrade on top of it.

## Design (verbatim from the review agent, wiring verified against guardrail_orchestration.py)

`guardrail_orchestration.py` passes a `content_bundle: dict[str, str]` to every guardrail, so
both files drop in with zero plumbing changes beyond bundling.

### Matrix A — baseline: `.architecture/ownership-baseline.md`
- Written only by mapcodebase; immutable until the next map. Provenance = map run date/commit.
- One row per artifact, capped to seam-bearing kinds: persisted tables, HTTP/WS endpoints,
  mutations/actions with cross-runtime effects, cross-cutting computations. Target ≤40 rows —
  brevity is the alerting mechanism.

```
| entity               | kind  | owner   | provenance            |
| exit_preview_records | table | gateway | map 2026-07-07 126da |
```

### Matrix B — live: `.architecture/ownership-live.md`
- Overwritten to equal A at every mapcodebase (prior versions survive in git history).
- Amended during every guardrail round. The guardrail subagent does NOT write the file
  (parallel guardrails would race it) — it returns structured `matrix_update` findings; the
  orchestration step applies them serially, appending a provenance note per edit:
  `[CONS 2026-07-09 exit-viewer r3 §18a: confirmed gateway; spec §10.5 said "server" — resolved]`.

### Redundancy payoff
- Spec vs both-agree → contradiction finding, **blocking**. Kills the exit_preview_records class at birth.
- Spec vs A-B-diverge → seam under active negotiation; CONS must cite the live provenance note
  and confirm or escalate.
- Every round: deterministic `diff` of B against A in the orchestration step (not LLM), delta
  printed in round output. Growing delta = seams alarm; empty delta = one line.
- At next mapcodebase: final A-vs-B diff handed to the mapper as "ownership moved since last
  map — verify against source before baselining," then B resets. Drift feeds the map.

### Consumers
Both files ride the shared `content_bundle`: CANON (spec ownership vs canonical architecture),
SCOPE (silent re-homing = scope change), TRACE — all get them for free. CONS category 7 gets
rewritten to check every ownership claim against both matrices; "server"-without-runtime stays
a finding in its own right.

### Acceptance test
Frozen `spec-draft-v4.md` + a baseline matrix containing `exit_preview_records → gateway` must
produce the blocking finding, and the live matrix must gain the provenance note.

## Relationship to the applied persona patch (reconciled 2026-07-09)

The persona patch is the **self-consistency** layer — catches ownership conflicts when both
sections live in the same document. The matrices are the **ground-truth and memory** layer,
covering two modes the persona patch structurally cannot: (1) a spec that is internally
consistent but wrong about ownership (every section says Convex; the codebase says gateway —
category 7 sees no contradiction), and (2) drift across rounds/sessions (guardrail runs are
memoryless; the live matrix's provenance notes are the only carrier of a resolved seam to the
next round). Delta when matrices land: one additive line to category 7 — "check every
ownership claim against ownership-baseline.md and ownership-live.md in your bundle; both-agree
+ spec-differs is a blocking finding." The v4 regression fixture doubles as the matrix layer's
acceptance baseline (seed `exit_preview_records → gateway` in the baseline matrix).

## Touch points when approved
1. mapcodebase skill: emit Matrix A, reset Matrix B at map time.
2. `guardrail_orchestration.py`: bundle both files; apply `matrix_update` findings; print A/B diff.
3. CONS persona: category 7 rewrite to matrix-checking form.

## Related follow-up (separate decision)
`guardrail_orchestration.py` marks CONS failures `severity="warning"` for critique actions
(blocking only for gauntlet) — a contradiction can survive to finalize BY DESIGN. Decide
whether ownership-class findings should be blocking everywhere.
