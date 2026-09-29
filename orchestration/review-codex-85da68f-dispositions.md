# Dispositions: codex review of 85da68f (REJECT, 6 blocking + 3 should-fix)

Review: `orchestration/review-codex-85da68f.md`. Owner: adv-spec-lead, 2026-09-27. No agy dispatch was made; every
case uses the offline harness: real bwrap, real git, real dispatch code, and a scripted fake critic.

## Test-first evidence
- Tests were written only through `pipeline_create_test` (lease `auth-47c7eb4c5416`, run status `red`). The gate
  refuses worktree paths (`INVALID_TEST_PATH: escapes root`). So the tests were written at the main-tree path,
  committed as `7bd49ca`, and fast-forwarded into this branch. Nothing bypassed the gate.
- Failing first: `orchestration/logs/agy-review-85da68f-failing-first.log` (pre-fix source: 13 failed, 52 passed).
- Green: `orchestration/logs/agy-review-85da68f-green*.log` (65 passed; repeated runs with `TMPDIR` set to a
  writable scratch dir under `~/.cache`).
- Paired negative oracle: every new test also asserts the contrasting non-triggering case, noted per row below.
  Each new test is also red on the pre-fix source, which proves it catches the defect.

## Findings

| ID | Disposition | Fix | Regression test (paired case) |
|---|---|---|---|
| R1 | **Accepted, fixed** | Before any evidence I/O, the process latches a provisional STOP and keeps the root. `record_incident` never raises `OSError`: it reports failures in `errors` and whether `stop.json` was written, and it always attempts `stop.json`. Any persistence failure ends in `AgyStop`, never the generic retry. A retained root gets a `retained.json` marker. `stop_recorded: false` blocks admission for the repo (from the dispatch base) until an operator runs `agy_sandbox.py release`. | `test_evidence_persistence_failure_is_terminal[incident_dir, incident_meta, all_state_writes]`: one launch, STOP, workspace and marker kept, fresh process blocked with `LAUNCHES=0`. Pair: TC-6.3, where a clean dispatch leaves no root and no state. |
| R2 | **Accepted, fixed** | Output is captured as bytes. The critic's streams are decoded with `errors="replace"`, and evidence keeps the raw bytes. A non-timeout exception during the wait is held until the workspace is inspected. | `test_undecodable_output_still_inspected`: invalid UTF-8 plus a write gives a one-launch STOP whose `agy-stdout.txt` holds the raw bytes. Pair: the same bytes without a write return normally. |
| R3 | **Accepted, fixed** | `os.walk` errors, a failing per-directory `iterdir`, and a changed workspace-root mode or type are all terminal. The inspection is kind `critic`, and the root is kept with the evidence in place. | `test_uninspectable_workspace_is_terminal`: write then `chmod . 0` gives a STOP with the root kept. Pair: a read-only critic returns normally. |
| R4 | **Accepted, fixed** | The final `_admit` (now `held=True`) and `subprocess.Popen` run inside `_locked(state)`, the same lock under which `record_incident` publishes. The lock is released right after the spawn, so parallel critics are not serialized. | `test_stop_published_at_final_admission_cannot_precede_launch`: the exact interleaving (publisher started right after the final check) now lands after the launch time. Pair: TC-4.7, where a STOP published before the check means zero launches. |
| R5 | **Accepted, fixed** | Gauntlet Step 3 runs `check_admission` whenever any attack or eval seat is AGY. It runs before prompt loading, gauntlet-dir creation, resume, or any provider dispatch. Exit 5 for blocked, 4 otherwise. | `test_gauntlet_prior_stop_refused_before_any_progress`: exit 5 with no progress. Pair: the same stopped repo with no AGY seat proceeds. |
| R6 | **Accepted, fixed** | `_mask_target` resolves symlinks and masks the resolved target, so every alias is hidden. A dangling symlink needs no mask. A target of the wrong type refuses the dispatch. This applies to tmpfs masks and throwaway file binds alike. | `test_symlinked_mask_targets_are_masked`: symlinked herdr, browser profile, knowledge and history are masked by alias and by target. Pair: an unmasked symlinked directory stays listable. |
| R7 | **Accepted, fixed** | `_cleanup_stale_roots` skips any root with `retained.json`. Only `release` removes the marker; it logs `released.json` and appends to `clears.jsonl` when it can. | `test_retained_evidence_root_survives_cleanup`: a dead-owner root with the marker is kept. Pair: one without the marker is reclaimed. The TC-6.4 kept root now carries the marker. |
| R8 | **Accepted, fixed** | `call_single_model` re-raises `AgyDispatchRefusedError`. `call_models_parallel` re-raises it after siblings return. `debate.main` exits 6 (`EXIT_AGY_REFUSED`) with no round checkpoint and no STOP. Review item 4 is fixed too: not-ready is classified before timeout, so a setup that times out is a refusal. | `test_dispatch_time_refusal_refuses_round`: `--skip-preflight` plus a setup failure gives exit 6. Pair: the same roster with a working sandbox completes. `test_setup_timeout_before_ready_is_refusal`: pair is TC-6.2 negative. TC-7.1 now asserts the typed refusal. |
| R9 | **Accepted, fixed** | The legacy token now goes to stderr, and the test asserts it is in the ordinary error. Fresh-process tests count launches at the child's own `Popen` (`LAUNCHES=0/1`). The harness counts every spawn through `subprocess.Popen`, with timestamps. R1 now induces failures at incident creation and at the initial metadata write. TC-0.1 negative guard added (`test_fake_guard_rejects_real_agy`). Config coverage spells out all 10 throwaway dirs and both throwaway files. | See the named tests. |

## Review summary items not in R1-R9
- **3, isolation (network):** not addressed. agy needs network access to its API, so `--unshare-net` would break
  every dispatch. Host Unix sockets that matter (herdr, `/run/user/<uid>`, SSH agent, DBus) are masked and tested
  (TC-12). Other abstract or TCP endpoints remain reachable. Carried as residue for the canary review.
- **4, setup timeouts:** fixed under R8 (see above).
- **Gauntlet dispatch-time refusal:** watchlisted at 4c1e099. Superseded: ruled blocking and fixed (see the
  re-review section below).

## Not done
- No agy dispatch or canary: operator approval is still pending.
- No push.

# Dispositions: codex re-review of 4c1e099 (REJECT, narrower)

Re-review: `orchestration/review-codex-4c1e099.md` (copied from the `agy-rereview-4c1e099` worktree). R2–R6, R8 and
R9 were confirmed FIXED with load-bearing tests. Owner: adv-spec-lead, 2026-09-29. No agy dispatch was made.

## Test-first evidence
- Tests written only through `pipeline_create_test` (lease `auth-4114de3651a6`, run status `red`), at the
  main-tree path because the gate refuses worktree paths. Committed as `32d9385` and fast-forwarded into this
  branch.
- Failing first on `4c1e099`: 11 failed, 65 passed (`orchestration/logs/agy-rereview-4c1e099-failing-first.log`).
- Green: `orchestration/logs/agy-rereview-4c1e099-green-run*.log` (76 passed, repeated runs with `TMPDIR` set to a
  writable scratch dir under `~/.cache`).

| ID | Disposition | Fix | Regression test (paired case) |
|---|---|---|---|
| N1 (completes R1/R7) | **Accepted, fixed** | Each dispatch root records its repository in `dispatch.json` before launch. After that, persistence failure at STOP time cannot hide the root. Admission is refused (`blocked`) when a root exists that is unreleased and still holds critic evidence without a durable STOP. That covers a marker with `stop_recorded: false`, an unreadable marker, or no marker at all over a workspace with content. Admission fails closed for every repository when the root's owner is unknown. Stale cleanup never reclaims a root that holds evidence or a marker. Only `agy_sandbox.py release`, which works on any dispatch root and logs `released.json`, makes it reclaimable. Interrupted dispatches whose critic left writes are therefore held too (a deliberate tightening of R2-4); empty ones are still cleaned. | `test_unpersisted_stop_blocks_and_evidence_is_never_reclaimed`: `_write_json` and marker writes both fail. Result: STOP, a fresh process gets `STOP blocked`/`LAUNCHES=0`, and the evidence survives cleanup after its owner dies. Pair: a dead-owner empty root is reclaimed. |
| Gauntlet refusal residue (ruled blocking) | **Accepted, fixed** | `gauntlet.core_types.NEVER_ABSORBED = PROGRAMMING_BUGS + (AgyDispatchRefusedError,)` is used by every model-caller handler in phases 1–6 (9 sites). Phase 7 re-raises the refusal explicitly. `run_gauntlet` catches the refusal, marks the manifest `agy_refused`, and exits 6. Readiness refusal (Step 3) now also exits 6 instead of raising a traceback. | `test_every_gauntlet_caller_propagates_refusal[8 callers]`: the refusal escapes each caller. Pair: an ordinary failure is still absorbed. `test_gauntlet_dispatch_refusal_refuses_run`: exit 6, `agy_refused`, no phase-1 checkpoint, one launch, no STOP. Pair: a working sandbox reaches the checkpoint. |
| N2 | **Accepted, fixed** | The provisional latch is flagged `provisional` and carries `evidence_root`. `agy_sandbox.resolve_stop()` returns the final latch once recording finishes. `call_models_parallel` buffers late sibling results, resolves the STOP after every worker returns, and then quarantines into the recorded incident. The fallback destination is the retained root; if both are missing, the payload goes to stderr rather than being dropped silently. Debate and gauntlet handlers report the resolved STOP. | `test_provisional_stop_resolves_to_incident_and_keeps_late_sibling_output`: the reviewer's interleaving, where the raised STOP is `critic` with the recorded `incident_dir` and the late Claude output is quarantined. Pair: TC-1.2 unchanged. |

## Not touched (per coordinator)
- The network-namespace residue is a user design decision. The re-review rates it BLOCKING for canary readiness.
- The `history.jsonl -> /dev/null` alias still refuses the dispatch (fail closed). The re-review judged this an
  intentional compatibility limit.
