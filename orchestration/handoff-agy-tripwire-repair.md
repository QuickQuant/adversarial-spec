# Goal

Create and own a distinct adversarial-spec session for repairing the shared Antigravity critic safety contract. The completed change must preserve detection and evidence capture for real critic mutations, prevent unrelated orchestrator/Codex/checkpoint writes from being silently deleted or blamed on the critic, and make any STOP-class mutation event terminal before another Antigravity dispatch can occur. It must be planned, debated, tested, and integrated deliberately; no direct deployment into the user-owned live source worktree.

# Non-Goals

- Do not resume, mutate, or complete the active `adv-spec-202607060132-post-fable-hardening-skill` session — it is unrelated in-flight work.
- Do not modify `/home/jason/PycharmProjects/adversarial-spec`, `~/.claude/skills/adversarial-spec`, or any user-owned dirty file there — this worktree is an isolated branch and deployment requires a later explicit integration gate.
- Do not resume or alter Brainquarters’ Jev session, its records, its dashboard, or its source; read its incident only as evidence.
- Do not dispatch Antigravity while this safety defect is unresolved, including preflight; do not treat a procedural workaround as a substitute for the repaired stop contract.
- Do not weaken real-mutation containment, hide attribution uncertainty, string-match errors as the sole stop protocol, alter model routing broadly, touch secrets/configuration, or use global process kills.
- Do not author vanity tests, mock echoes, or tests before the active pipeline authorizes their contract.

# Acceptance Criteria

- A new session/card exists on board `03fw5alxw15iqwh6hq15vfdsb`, preserves the existing session pointer/history, and follows the full required pipeline rather than patching source ad hoc.
- The specification defines explicit outcomes for: real critic mutation; non-critic shared-worktree mutation; timeout; parallel/sibling dispatch; oversized-prompt scratch; preflight; and a fresh process after a prior stop.
- The approved implementation contract prevents a STOP event from entering generic retry/synthesis/checkpoint paths, never deletes an unattributed writer’s bytes, and keeps real critic-mutation evidence plus fail-stop behavior.
- Test specifications use observable behavior and paired negative oracles; the eventual regression suite proves no automatic re-dispatch after a stop and distinguishes attribution without network or live critic calls.
- The final integration plan names the exact reconciliation/deployment gate for the dirty live source and verifies that no unrelated user change is overwritten.

# Facts & Anchors

- Current session under repair was blocked by a false-positive roadmap R1 tripwire in Brainquarters: `/home/jason/PycharmProjects/Brainquarters/.adversarial-spec/specs/jev-vocab-guard/process-failures/2026-09-24-roadmap-r1-agy-tripwire-and-timeout.md:5-24`.
- Live installed source is `/home/jason/.claude/skills/adversarial-spec` (symlinked from the user-owned dirty repository `/home/jason/PycharmProjects/adversarial-spec`, branch `bounded-pipeline-reform`). It has dirty edits overlapping `models.py`, `debate.py`, gauntlet files, and `tests/test_models.py`.
- `models.py:725-818` snapshots all dirty/untracked paths under the caller git root, treats every delta during an AGY dispatch as critic-authored, reverts/unlinks it, and raises ordinary `RuntimeError`.
- `models.py:888-1018` dispatches AGY and runs the tripwire on return/timeout; `models.py:1235-1286` catches every exception and retries up to three times. `debate.py:1207-1227` treats model errors as warnings and continues checkpoint/critique writes.
- `models.py:1499-1536` writes partial results while sibling critics may still run. `debate.py:1697-1725` invokes AGY preflight without forwarding `--cwd`.
- Independent review reports, read-only: `/home/jason/PycharmProjects/adversarial-spec.worktrees/agy-tripwire-review/orchestration/report-agy-tripwire-codepath.md` and `report-agy-tripwire-recovery.md`.
- The codepath review recommends a typed/latching stop boundary plus per-dispatch private workspace and non-destructive unattributed shared-tree evidence. Treat it as a proposal, not a decision; test source and pipeline contracts before adopting it.
- This clean branch/worktree is `/home/jason/PycharmProjects/adversarial-spec.worktrees/agy-tripwire-fix`, branch `adv-spec/agy-tripwire-stop-20260924`, from `da3c905`.
- If any derivation conflicts with these facts, stop and report it; do not force a patch.

# Deliverables

- Normal new-session artifacts under `.adversarial-spec/specs/agy-tripwire-stop/` plus the phase-owned Fizzy records.
- A concise final report at `orchestration/report-agy-tripwire-repair.md` (≤60 lines): artifacts, decisions, verified evidence, exact integration blocker, and no optimistic deployment claim.

# Boundaries

- Work only in this clean worktree, except read-only access to the two reports and Brainquarters incident named above.
- No commits/pushes, deployment, service control, credential inspection, global settings edits, or edits outside this worktree without a later explicit human integration approval.
- Use the explicit board ID above for all Fizzy calls. Never hand-edit pipeline/card/session state to bypass a phase gate.
