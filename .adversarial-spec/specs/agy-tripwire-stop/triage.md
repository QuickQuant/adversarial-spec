## Triage — AGY Tripwire Stop (2026-09-24)

Source: `orchestration/handoff-agy-tripwire-repair.md` (operator handoff), incident
`Brainquarters/.adversarial-spec/specs/jev-vocab-guard/process-failures/2026-09-24-roadmap-r1-agy-tripwire-and-timeout.md`,
review reports `agy-tripwire-review/orchestration/report-agy-tripwire-{codepath,recovery}.md`.
Clean-tree anchors verified at `da3c905`: tripwire `scripts/models.py:632-713`, dispatch `783-913`.

Complexity: medium — signals: integrations=3 internal (models.py dispatch/retry,
debate.py round + preflight, gauntlet catch sites) and no new external service;
unknowns=4 (structural attribution for a critic that ignores sandbox flags; whether agy
reads a prompt from a non-git temp workspace; cross-process stop persistence and its
operator clear; landing on a dirty user-owned live tree without overwriting it).

Root altitude: system — highest-blast item: the shared-worktree revert, because it
unlinks or overwrites bytes owned by another writer (orchestrator, Codex, checkpoint
writer, other sessions) in any consuming repository (Brainquarters incident
2026-09-24). That destruction crosses a repo/process boundary and a code revert of
adversarial-spec cannot restore the lost bytes. The retry path also re-spawns an
external critic after a STOP-class event, an outbound effect a revert cannot undo.

Tree:
  SYS  AGY critic safety contract                                  [system]
  ├─ SS  Stop propagation (STOP is terminal)                        [subsystem]
  │   ├─ C  typed stop signal + in-process dispatch latch            [component]
  │   ├─ C  terminal handlers: debate round, gauntlet, preflight     [component]
  │   └─ C  cross-process stop record + operator clear               [component]
  └─ SS  Attribution & non-destructive containment                  [subsystem]
      ├─ C  per-dispatch private critic workspace (+ prompt scratch) [component]
      └─ C  shared-tree sensor: evidence without destructive revert  [component]

Go / no-go: GO — system rigor: component + subsystem + end-to-end verification,
consequence-safety guardrails (no unattributed deletion; no dispatch after STOP) and a
manual go-live gate (integration onto the dirty live tree needs explicit operator
approval). Debate quorum 2 critics / 2 families / 2 rounds; gauntlet ≥2 adversaries,
≥2 families, ≥3 foci; full persona slate (shared infrastructure + concurrency).
Constraint carried forward: no Antigravity dispatch (preflight included) while the
defect is unresolved, so the Google family is unavailable to this session's own debate
and gauntlet; family diversity must come from the remaining registered families.
