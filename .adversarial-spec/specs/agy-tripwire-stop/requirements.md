# RequirementsSummary — AGY Tripwire Stop

Session `adv-spec-202609240523-agy-tripwire-stop` · card 21616 · altitude `system` · doc `spec/technical`.
Input authority: operator handoff `orchestration/handoff-agy-tripwire-repair.md`; evidence from the
Brainquarters incident (2026-09-24) and the two read-only review reports. Interview: not run —
the handoff is the operator's requirements statement; gaps are listed as unknowns below.

## Problem (evidence)
- Attribution is timing-only: every dirty/untracked delta in the caller's git root during an agy
  window is blamed on the critic (`scripts/models.py:645-663`), reverted by overwrite or `unlink`
  (`:691-703`). Incident: the orchestrator's own 2,519-byte critique was deleted.
- STOP is an ordinary `RuntimeError` (`:706-713`); the agy branch of `call_single_model` catches every
  `Exception` and re-dispatches up to `MAX_RETRIES` (`:1161-1174`). Incident: attempt 2 ran after STOP.
- After retries the STOP survives only as `ModelResponse.error` text; `debate.py:1184-1191` warns and
  continues to synthesis/checkpoint writes. Preflight swallows it into a string (`models.py:1312-1313`)
  and `debate.py:1665-1667` does not forward `--cwd`.
- Tool writes inside the window (`_save_partial_result`, `models.py:1391-1426`) and co-tenant Codex
  (`workspace-write`, same cwd) are indistinguishable from critic writes.

## User types
- **Orchestrator agent** (Claude/Codex/Gemini seat running a debate or gauntlet) — writes into the same
  worktree while critics run; must never lose bytes or be blamed.
- **Operator (Jason)** — sole authority to clear a STOP; needs evidence sufficient to decide.
- **Consuming projects** (Brainquarters, fizzy-pipeline-mcp, …) — dirty shared worktrees with other
  sessions' in-flight work.
- **Future maintainers** — must not be able to reopen the retry path by adding a new catch site.

## Scenario outcomes (current: operator redirect 2026-09-24 + tests-pseudo v4)
| ID | Scenario | Required outcome |
|---|---|---|
| SC-1 | Real critic mutation | The critic can only write its sandbox workspace. Retained workspace writes are captured and the workspace is discarded; STOP `critic`; durable record; no further agy dispatch |
| SC-2 | Non-critic write to the shared worktree during the window | Bytes untouched; recorded as `co_tenant` in `windows.jsonl`; never halts; never labelled critic |
| SC-3 | Timeout | Workspace inspected before the timeout is reported; a write means STOP; a clean timeout is an ordinary retryable failure |
| SC-4 | Parallel/sibling agy dispatches | A STOP latches the process, so queued siblings do not launch. Running siblings finish, are inspected, and are quarantined. Siblings cannot see each other's roots |
| SC-5 | Oversized-prompt scratch | Lives in the dispatch root outside every repository and is bound read-only; the root is removed afterwards |
| SC-6 | Preflight | Sandboxed dispatch for the round `--cwd`; obeys the latch and the record; STOP surfaces as STOP |
| SC-7 | Fresh process after a prior STOP | Refused before launch in every worktree of the repo until a logged operator clear; a deleted record without a clear is a `tamper` STOP |

## Features (functional; current)
- F-1 Typed, terminal `AgyStop` (BaseException) that generic `except Exception` handlers cannot absorb.
- F-2 In-process dispatch latch: once set, every agy entry point refuses before launch.
- F-3 Durable stop state in the git common dir. Incident directories are the authority, with a `stop.json` index. Clear is logged in
  `clears.jsonl` and must name the full uncleared set. A missing record without a clear is a tamper STOP.
- F-4 Terminal handlers: debate exits 4 (5 when blocked) with no synthesis and no round checkpoint; gauntlet sets manifest `agy_stop` and exits
  4; preflight propagates STOP; an unavailable agy seat refuses the round (exit 6).
- F-5 bwrap sandbox for every agy launch: `/` read-only, per-dispatch workspace writable, prompt and inputs bound read-only into the
  workspace. Config dirs are read-only with named throwaway paths. Host sockets are masked (herdr, `/run/user/<uid>`, `/tmp`) and the
  environment is an allowlist. No unsandboxed fallback.
- F-6 Shared-tree deltas and blocked write attempts are logged, not halted, and nothing in a repository is ever reverted.
- F-7 Non-mutation failures (rc≠0, empty output, clean timeout) keep today's bounded retry.

> Superseded v1 rows (restore, `unattributed`, tool-owned exclusions) are retired. See the decisions log.

## Non-functional
- NF-1 Regression suite runs offline: no network, no live critic; fake agy via subprocess side effects.
- NF-2 Tests assert observable behavior with paired negative oracles; no mock echoes or source-text pins.
- NF-3 STOP message stays human-readable, but no control flow depends on string matching.
- NF-4 Integration onto the user-owned dirty live tree only through a named, operator-approved gate
  that proves no user hunk is overwritten.

## Integrations (internal)
`scripts/models.py` (dispatch, tripwire, retry, preflight, parallel save), `scripts/debate.py`
(critique round, preflight wiring, exit codes), `scripts/gauntlet/*` (model dispatch + 8 generic catch
sites + orchestrator stop handling), `scripts/session.py` (checkpoint dir), tests under
`scripts/tests/` / `tests/`.

## Unknowns (to resolve in roadmap/debate, not assumed)
- U-1 **Resolved by design (G1 redirect):** prompt and inputs are bind-mounted read-only into the sandbox workspace. The live
  proof is the supervised post-landing canary (residue). If agy cannot run that way, agy dispatch stays refused.
- U-2 ~~halt unattributed~~ **Superseded (operator G1 redirect, 2026-09-24):** attribution is structural via bwrap
  (repo read-only to the critic). A shared-tree delta is `co-tenant`: preserved, recorded, never halting. A fail-closed STOP
  happens only on boundary-failure evidence.
- U-3 **Decided:** the stop record is per repository and lives in the git common dir (U-8). Every worktree of the repo is blocked.
- U-4 **Decided:** siblings already running at STOP time finish, are inspected, and are quarantined.
- U-7 **Decided (narrowed at G1):** the durable operator-clear STOP applies only to critic mutation or boundary failure.
- No-fallback **Decided:** if bwrap is unavailable, dispatch refuses. Never unsandboxed.
- Commits **Decided:** local commits are allowed on the session branch and on per-candidate branches off it. Nothing is pushed
  or merged before integration approval (this relaxes handoff line 42).
- Full decision trail: `.adversarial-spec/sessions/adv-spec-202609240523-agy-tripwire-stop.decisions.log`.
- U-5 Landing path: live tree `bounded-pipeline-reform` carries dirty overlapping hunks in `models.py`,
  `debate.py`, gauntlet files, `tests/test_models.py`; exact reconciliation order.
- U-6 fizzy-pipeline-mcp has its own agy runner; out of this worktree → recorded as residue, not fixed here.

## Out of scope
Post-Fable session, Brainquarters Jev session/records, live source, deployment, model-routing changes,
secrets/config, global process control.
