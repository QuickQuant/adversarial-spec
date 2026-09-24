# Test Pseudocode — AGY Tripwire Stop

> v4 — 2026-09-24. **Authorized test contract** for the focused fix (operator redirect
> `/home/jason/PycharmProjects/adversarial-spec.worktrees/agy-tripwire-fix/orchestration/redirect-focused-fix-2026-09-24.md`).
> v4 applies R2 rulings 1–5 and the host-socket requirement. It supersedes v3, v2 and v1.
> The suite file is `skills/adversarial-spec/scripts/tests/test_agy_sandbox.py`; every case below names its test function.
>
> **Harness.** Each case builds real git repos (and linked worktrees) under a fixture root in `~/.cache`,
> never under `/tmp`, because `/tmp` is masked inside the sandbox. It runs the **real bwrap sandbox** through the
> real dispatch, debate and gauntlet code. The only replaced component is the critic. A scripted fake `agy`
> executable sits first on `PATH` and performs its scripted side effects *inside* the sandbox: workspace writes,
> absolute-path write attempts, sleep, exit code, stdout, stderr. The real kernel boundary judges every write.
> Launch counting wraps the module's single spawn point, so it observes real launches. Timeouts and retry
> delays are injected.
> **Data strategy vocabulary.**
> - REAL-DATA: real repo, real bwrap, real files.
> - MOCK-EXTERNAL: the fake critic's behaviour. why_impossible_to_reproduce_live: the operator forbids agy dispatch
>   until the supervised canary, and a live critic's writes cannot be forced deterministically.
> - SYNTHETIC: a deliberately broken sandbox profile or state.
> **Paired negative oracle.** Every positive case has a sibling in which the trigger is absent and the behaviour MUST NOT occur.
> Removing the behaviour under test makes one side of each pair fail.

Outcomes (typed; control flow never matches message text):
- `AgyStop` (BaseException) with `kind ∈ {critic, boundary_failure, tamper, blocked, latched}`. It is never retried and is not absorbed by
  `except Exception`. `debate.py` exits 4, or 5 when `kind == blocked`. The gauntlet records `status: agy_stop` and exits 4.
- `AgyDispatchRefusedError` (RuntimeError) covers: sandbox unavailable, bwrap setup failure, no git repo. There is no spawn, no retry and
  no durable record. `debate.py` refuses the round before any dispatch, naming the seat and the reason (exit 6).
- Stop state lives in `<git-common-dir>/adversarial-spec-agy/`: `incidents/<id>/`, `stop.json` (index),
  `clears.jsonl`, `windows.jsonl` (co-tenant + blocked-write log), and a lock.

## US-0 Offline suite
- **TC-0.0** `test_suite_uses_fake_critic_only` — REAL-DATA. Every launch in the suite resolves `agy` to the fake path.
  Negative: an `agy` resolving to any other path aborts the test harness before a launch (TC-0.1 `test_fake_guard_rejects_real_agy`).
- **TC-0.2** `test_sandbox_unavailable_reported` — SYNTHETIC. PATH has no bwrap → `AgyDispatchRefusedError("sandbox unavailable: bwrap
  not found")` and 0 launches. Paired: with bwrap present, `sandbox_unavailable_reason()` returns `None`.

## US-1 Debate STOP is terminal
- **TC-1.0** `test_debate_critic_write_stops_round` — MOCK-EXTERNAL. The fake critic writes into its workspace, and
  `debate.py critique` runs with that critic. Outcome: exit 4 and one launch. The incident has kind `critic` and the written bytes. The stop record exists.
  There is no round checkpoint and no critiques file. Negative (same file): a clean critic → exit 0, a round checkpoint exists, and no stop state exists.
- **TC-1.1** `test_nonmutation_failure_still_retried` — MOCK-EXTERNAL. The fake exits 1 with no writes → `MAX_RETRIES` launches,
  `ModelResponse.error` set, and no incident. Paired with TC-1.0: a workspace write → exactly 1 launch.
- **TC-1.2** `test_stopped_round_quarantines_sibling_output` — MOCK-EXTERNAL. A non-agy sibling (claude-cli fake) is still
  running when agy trips. Its result is written under `incidents/<id>/quarantine/`, not as a partial checkpoint. A sibling
  that finished before the trip keeps its partial checkpoint.
- **TC-1.3** `test_stop_escapes_generic_except` — SYNTHETIC. A caller wraps dispatch in `except Exception` and the STOP still propagates.
  Negative: the same wrapper absorbs an ordinary non-mutation failure.
- **TC-1.4** `test_stop_independent_of_message_text` — SYNTHETIC. The STOP message is randomised and the outcome is unchanged. Negative: an
  ordinary `RuntimeError("AGY_MUTATION_DETECTED …")` from a failing critic is retried like any other error.
- **TC-1.5** `test_latch_blocks_later_dispatch_in_process` — MOCK-EXTERNAL. After a STOP, the next agy call in the same
  process raises `AgyStop(kind=latched)` with 0 new launches. Paired: without a prior STOP, the call launches.

## US-2 Gauntlet STOP blocks siblings and later phases
- **TC-2.0** `test_gauntlet_attack_stop_blocks_queued_siblings` — MOCK-EXTERNAL. Phase-1 attacks run with 3 agy pairs, and the first
  one writes. The queued pairs raise `latched` with no launch, and `run_gauntlet` sets the manifest `status: agy_stop` and exits 4.
  Paired `test_gauntlet_clean_agy_attacks_complete`: all 3 launch and there is no stop state.
- **TC-2.1** `test_running_sibling_finishes_and_is_inspected` — MOCK-EXTERNAL. A sibling that is already running is not signalled.
  Its inspection runs, and a second write by it becomes a second incident. Neither sibling yields concerns.

## US-3 Preflight is a real dispatch
- **TC-3.0** `test_preflight_uses_round_cwd` — REAL-DATA. The process cwd is repo A and `--cwd` is repo B. A preflight critic write is filed under
  B's common dir and nothing is filed under A. Negative: without `--cwd`, it is filed under A.
- **TC-3.1** `test_preflight_stop_is_stop` — MOCK-EXTERNAL. A preflight write → exit 4 (not 2) and no critique dispatch.
  Paired: a preflight rc≠0 without writes → exit 2 "preflight failed".
- **TC-3.2 / 3.3** `test_blocked_repo_refuses_with_and_without_preflight` — REAL-DATA. With a stop record present, critique
  exits 5 with 0 launches, whether or not `--skip-preflight` is passed.
- **TC-3.4** `test_round_refuses_unavailable_agy_seat` — SYNTHETIC. With the sandbox unavailable, `debate.py critique` exits 6
  before any launch of any model and names the seat. Paired: a round without an agy seat is unaffected.

## US-4 STOP survives the process; tamper detection (R2-3)
- **TC-4.0** `test_fresh_process_blocked_until_clear` — REAL-DATA. Process 1 stops. Process 2 raises `blocked` with 0 launches, and its
  message names the record and the incident. After the clear, process 3 launches. Incident bytes are unchanged.
- **TC-4.1** `test_other_repo_not_blocked` — REAL-DATA.
- **TC-4.2** `test_state_outside_every_worktree` — REAL-DATA. The stop state lives under `--git-common-dir`. `git status -uall` of the main
  worktree and of a linked worktree shows none of it.
- **TC-4.3** `test_corrupt_record_fails_closed` — SYNTHETIC. An unparseable `stop.json` → refusal (`blocked`) naming the path.
- **TC-4.6** `test_linked_worktree_blocked` — REAL-DATA. A stop from W1 blocks W2 of the same repo.
- **TC-4.7** `test_stop_between_prepare_and_launch_blocks` — SYNTHETIC. A stop recorded after workspace preparation and before
  launch → 0 launches (admission is re-checked immediately before the spawn).
- **TC-10.3** `test_deleted_record_without_clear_is_tamper_stop` — SYNTHETIC. The incident exists and `stop.json` has been deleted
  without a logged clear → `AgyStop(kind=tamper)`, `stop.json` is re-created, 0 launches. Paired: after a logged clear, the same
  deletion state admits dispatch.

## US-5 Co-tenant writes: untouched, recorded, non-halting (R2-2 narrowing: no watcher)
- **TC-5.0** `test_cotenant_write_preserved_and_logged` — REAL-DATA. This replays the incident. During the critic's sleep a separate writer
  creates N (2,519 bytes), edits dirty tracked file D, and deletes dirty file E; untracked U already exists. After the dispatch: all bytes
  are the writer's, E stays deleted, U is untouched. `windows.jsonl` lists N, D and E as `co_tenant`. The response is returned, with no incident
  and no stop record. Negative: no path in the repo is unlinked, overwritten, or `git checkout`-ed.
- **TC-5.1** `test_partial_checkpoint_is_cotenant` — REAL-DATA. A partial result saved into the repo mid-window → no stop.

## US-6 Critic write captured, workspace discarded, STOP
- **TC-6.0** `test_workspace_write_captured_and_discarded` — MOCK-EXTERNAL. The incident is `critic`, and its captured bytes equal
  the written bytes for both a created file and a file in a created subdirectory. Critic stdout/stderr are captured. The dispatch root is gone.
- **TC-6.1** `test_repo_write_attempt_blocked_and_logged` — MOCK-EXTERNAL. The fake writes into the repo by absolute path
  and exits 0. The repo bytes are unchanged (the kernel returns EROFS). The response is returned and there is no STOP. `windows.jsonl` records the blocked attempt
  from stderr (R2-2: blocked attempts are recorded, non-halting).
- **TC-6.2** `test_timeout_after_write_is_stop` — MOCK-EXTERNAL. The fake writes, then sleeps past the timeout → STOP (not a timeout
  error) with 1 launch and the process tree gone. Negative `test_clean_timeout_is_retried`: a sleep with no write → an ordinary timeout
  error, `MAX_RETRIES` launches, no incident.
- **TC-6.3** `test_clean_dispatch_returns_response` — MOCK-EXTERNAL. The response is returned, the dispatch root is removed, and there is no stop state.
- **TC-6.4** `test_evidence_failure_keeps_workspace_and_stops` — SYNTHETIC. With the incident dir unwritable, a STOP is still
  raised and says `evidence incomplete`, and the dispatch root is left in place.

## US-7 Boundary failure vs refusal (R2-5)
- **TC-7.0** `test_every_launch_is_sandboxed` — REAL-DATA. For every launch in the suite, argv[0] is bwrap and the profile contains
  `--ro-bind / /`, `--clearenv`, `--unshare-pid` and `--die-with-parent`.
- **TC-7.1** `test_bwrap_setup_failure_is_refusal_only` — SYNTHETIC. A bind source that does not exist → `AgyDispatchRefusedError`.
  There is no incident, no stop record, and no retry.
- **TC-7.2** `test_probe_write_success_is_boundary_stop` — SYNTHETIC. A broken profile makes the repo writable. The in-sandbox
  probe succeeds, and the critic never starts (the fake's start marker is absent) → `boundary_failure` STOP plus a record. The probe's own
  nonce file is gone. Paired: with the correct profile the probe fails and the critic starts.
- **TC-7.3** `test_sentinel_change_is_boundary_stop` — SYNTHETIC. A broken profile binds the sentinel writable and the fake
  changes it → `boundary_failure`.

## US-9 / US-10 Operator evidence and clear (R2-3: procedural + tamper detection)
- **TC-9.1** `test_stop_output_names_evidence_and_clear` — MOCK-EXTERNAL. Debate stderr names the incident path, the kind, the
  path count, the stop record path and the clear command. It contains no "Retrying".
- **TC-10.0** `test_clear_records_and_keeps_evidence` — REAL-DATA. The clear names the full set of uncleared incidents, the operator and
  the reason. It writes a `clears.jsonl` entry and removes `stop.json`, and the incident dir stays byte-identical.
- **TC-10.1** `test_clear_with_wrong_incident_refused` — REAL-DATA. A missing or extra id → refused, with the state unchanged.

## US-11 Inputs and config dirs (R2-1)
- **TC-11.0** `test_prompt_bound_readonly_in_workspace` — MOCK-EXTERNAL. The fake reads `<ws>/inputs/prompt.md` and echoes its
  sha256, which equals the prompt's. Its attempt to modify the prompt fails, and no repo path is created.
- **TC-11.1** `test_oversized_prompt_never_in_repo` — SYNTHETIC [BVA]. A prompt of `inline_max+1` bytes → pointer transport, with the
  file under the dispatch root. A prompt of exactly `inline_max` bytes → inline. In both cases the repo porcelain is unchanged and the dispatch
  root is gone afterwards.
- **TC-11.2** `test_siblings_cannot_see_each_other` — REAL-DATA. Inside dispatch A, dispatch B's root is not visible,
  because the dispatch base is tmpfs-masked.
- **TC-11.3** `test_config_dirs_readonly_and_throwaway` — REAL-DATA, run against a fixture HOME. Inside the sandbox:
  - writes to `~/.gemini/settings.json`, `~/.gemini/antigravity-cli/mcp_config.json`, `~/.antigravity/argv.json` and the oauth token → EROFS;
  - writes into `antigravity-cli/{brain,…,knowledge}`, `history.jsonl` and `conversation_summaries.db` succeed and leave the host copies unchanged;
  - `antigravity-browser-profile` appears empty.

## US-12 Host sockets (hard requirement)
- **TC-12.0** `test_herdr_socket_unreachable_in_sandbox` / **TC-12.1** `test_ssh_agent_unreachable_in_sandbox` /
  **TC-12.2** `test_dbus_session_unreachable_in_sandbox` — REAL-DATA. Each probe fails inside the dispatch profile:
  `herdr agent list`, `ssh-add -l`, `busctl --user list`. Paired: the same probe inside bwrap with `--ro-bind / /` and the host env (no masks)
  succeeds. If the paired probe is unreachable on the host, the case is skipped with an explicit reason (never passed vacuously).
- **TC-12.3** `test_env_is_allowlist` — REAL-DATA. `env` inside the sandbox contains no `SSH_AUTH_SOCK`, `DBUS_SESSION_BUS_ADDRESS`,
  `HERDR_*` or `XDG_RUNTIME_DIR`, but does contain `HOME` and `PATH`.

## Operator-gated (not in the offline suite)
- US-8 landing onto the dirty live tree, and the supervised canary (U-1 live read path, U-10 no out-of-sandbox helper, U-11 agy runtime
  byproducts, oauth token write-back). Both are separate operator approvals per the redirect.

### Decision table — delta classification
| Change | Outcome | Test |
|---|---|---|
| critic workspace (beyond empty `inputs/` mountpoint) | STOP `critic` + record | TC-6.0 |
| watched repo (any writer) | `windows.jsonl` co-tenant, no halt | TC-5.0 |
| critic abs-path repo write | EROFS; blocked attempt logged, no halt | TC-6.1 |
| sentinel changed / probe write succeeded | STOP `boundary_failure` + record | TC-7.2, TC-7.3 |
| bwrap setup failed / bwrap missing / no git repo | refusal, no record | TC-7.1, TC-0.2 |
| none | response | TC-6.3 |

### State table (per repository, git common dir)
| From | Event | To | Test |
|---|---|---|---|
| CLEAR | critic write / boundary failure | STOPPED | TC-6.0, TC-7.2 |
| CLEAR | co-tenant delta, blocked attempt, clean run | CLEAR | TC-5.0, TC-6.1, TC-6.3 |
| STOPPED | dispatch (same process) | STOPPED (`latched`) | TC-1.5 |
| STOPPED | dispatch (fresh process, any worktree) | STOPPED (`blocked`) | TC-4.0, TC-4.6 |
| STOPPED | record deleted, no clear | STOPPED (`tamper`) | TC-10.3 |
| STOPPED | clear naming full incident set | CLEAR | TC-10.0 |
| STOPPED | clear with wrong set | STOPPED | TC-10.1 |
