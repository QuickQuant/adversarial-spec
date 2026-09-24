# Report: v6 Debate fan-out (handoff-v6-debate-fanout.md)

Status: all 7 AC have evidence. One follow-up is blocked (E2E pin, see Contradictions #5). No Fizzy board calls; nothing written under ETB.

## Files changed
- **fizzy-pipeline-mcp @ `7c3ac97`** (`feat(v6): refuse session-card debate rounds; route Debate to leaf fan-out`): `pipeline.py` +2059-2065 (lane-state attention), +2236-2238 (next_actions), +9737-9830 (`_v6_debate_guidance`, `_v6_session_debate_guidance`), +21624-21632 (`begin_debate_round` guard, code `V6_DEBATE_IS_LEAF_FANOUT`); `tests/test_pipeline_guards.py` +3313-3511 (10 tests); `agents.py` +175-186 (the kept `claude-opus-5-5` entry); `orchestration/logs/v6-debate-*.log`.
- **adversarial-spec**: new `skills/adversarial-spec/scripts/d0_to_load_plan.py` (330 lines) and `scripts/tests/test_d0_to_load_plan.py` (121 lines); `phases/03-debate.md` +1-96 (v6 section, then a `## Pre-v6 sessions` heading; 0 lines deleted); `SKILL.md` +524-534 (**left uncommitted**: the file also has another session's hunk at 105-110); `orchestration/logs/` holds the dry-run plan, harness, and logs. Committed together with this report.

## Acceptance criteria
1. **Refusal, test-first.** A v6 card in Debate is refused in all three states: `d0_closed=false` (message names `pipeline_mark_decomposition_complete`, and says to backtrack to Decomposition first); no inventory (message names the bounded leaf plan and `pipeline_load`); inventory present (message names the A->S cycles and Pre-Gauntlet). v4 and v5 still succeed. Grep result: the only "v6" callers of `begin_debate_round` are stale v5-contract live E2Es, not legitimate v6 use (see #5). Evidence: fizzy `orchestration/logs/v6-debate-guard-failing-first.log` (3 begin tests plus 4 attention tests red before the change) and `v6-debate-guard-green.log`.
2. **Lane-state attention.** `pipeline_lane_state` (both `session` and `task`) and `pipeline_next_actions` return `attention.session_context.kind = v6_debate_leaf_plan_not_loaded` plus `session_next_action`, naming the converter, `pipeline_validate_plan`, and `pipeline_load`. The same function (`_v6_debate_guidance`) supplies the refusal message, so the two surfaces cannot drift apart. Tests: `test_lane_state_v6_*`, `test_next_actions_v6_*`, `test_lane_state_pre_v6_*`.
3. **Full fizzy suite:** 1055 passed, 422 skipped, 2 failed (`v6-debate-full-suite.log`). Both failures (`test_dispatch_single_agent_debate_{records_registry_identity,reads_spec_path}`) fail identically on an unmodified HEAD copy: `v6-debate-baseline-head-full-suite.log` (b222126 in /tmp; its 2 extra `test_merge_contract` failures are only because the copy ran from /tmp) and `v6-debate-baseline-preexisting-failures.log` (cffe0ef). `ruff` is clean.
4. **D0 → load-plan converter.** Unit tests: 4 passed (`orchestration/logs/d0-to-load-plan-tests.log`). ETB dry run: `orchestration/logs/etb-d0-plan-dryrun.json` has 9 tasks, namely the `SYS-SR` aggregate root plus leaves **L1–L8**. fizzy's `validate_plan` was imported and run in-process: `valid: true, issues: [], warnings: []`. Every node's binding lift (`_derive_v4_node_lift`) also succeeds. Evidence: `etb-d0-plan-validate.log` from `etb_d0_dryrun_harness.py`, which uses an in-memory board with no network access.
5. **Phase doc.** The `03-debate.md` v6 section covers:
   - the kind→next-action table;
   - V1–V6: converter → `pipeline_validate_plan` → `pipeline_load` → per-leaf A/B/C/D-E/S-F mapped to `pipeline_record_ab_closure` / `_create_middleware_fanout` / `_pickup`/`_complete_middleware_impl` / `_middleware_judge` / `_promote_middleware_winner`, plus `pipeline_record_leaf_exception`, seam closure/deferral, and `pipeline_advance` through the barrier;
   - an ETB resume example with the first three calls.

   Every tool name and required argument was checked against `server.py` signatures.
6. **Resume rule** added to SKILL.md in the v6 router bullets. The skill has no resume doc in `reference/`, and `checkpoint-workflow` is not in this repo, so SKILL.md is the only place it was added.
7. **Walkthrough** (fresh agent reading ETB state from the updated docs). The harness replays card 21605's pipeline state: v6, subsystem, d0_closed, Debate, `last_completed_round=28`, no inventory.
   - (a) Doc says the first call is `pipeline_lane_state`. It returns `kind=v6_debate_leaf_plan_not_loaded` and "the bounded leaf plan has not been loaded … d0_to_load_plan.py … pipeline_validate_plan, then pipeline_load".
   - (b) An agent that tries round 29 anyway gets `begin_debate_round` refused with `V6_DEBATE_IS_LEAF_FANOUT` and the same load instruction.
   - (c) V1–V3: converter → `validate_plan` valid → `load_plan` into the in-memory board gives `Specifying: L1…L8`, `Decomposed: SYS-SR`, and `debate_leaf_inventory=[L1…L8]`. Lane state then flips to `v6_debate_leaf_fanout`, which points at the A->S cycles and the barrier. Output: `etb-d0-plan-validate.log` ends with `DRY RUN: PASS`.

## Contradictions found
1. fizzy HEAD is `b222126`, not `cffe0ef`. The two newer commits touch only hooks. An earlier, interrupted executor pass (logs timed 07:44–07:47) had already left this handoff's guard and tests uncommitted in the tree. I verified them and finished the work rather than rewriting it.
2. The metadata field is `debate_leaf_inventory`. `debate_inventory` is only the name of `load_plan`'s local patch variable. Line anchors have shifted by about 100 lines.
3. `pipeline_mark_decomposition_complete` only runs in the `Decomposition` lane, so a v6 card sitting in Debate with `d0_closed=false` must be backtracked first. The guard message and the doc say so.
4. The validator needs data that D0 does not contain. None of it is blocking:
   - `test_targets` / `verify_commands` use provisional defaults (`tests/`, `uv run pytest tests/ -q`), overridable on the CLI; the authoritative suite is bound at A/B closure.
   - The definition document is the manifest's `requirements_summary_path`, because ETB's `spec_path` is null.
   - effort / strategy / mode / `tested_by` are constants copied from the loaded v6 precedent `fizzy-pipeline-mcp/.adversarial-spec/specs/test-governance-anti-divergence/fizzy-plan.json`.
5. `tests/test_e2e_altitude_debate.py` (live only; skipped offline) creates sessions at `CURRENT_PIPELINE_VERSION`=6 (its docstring still says 5) and calls `begin_debate_round`. Run with `FIZZY_E2E=1`, it will now hit `V6_DEBATE_IS_LEAF_FANOUT`. The fix is to pin `pipeline_version: 5` in `_move_to_debate`, but `governance_test_gate` (committed today) blocked the edit. It needs an approved test_spec lease. Not run live.
6. The skill suite has 1 failure unrelated to this change: `test_keystone_file_pin_matches_the_mirror_constant`, caused by drift in the external Brainquarters keystone schema (`orchestration/logs/skill-suite.log`).

## Do the fan-out tools block like debate dispatch? (Non-Goal 2: reported, not fixed)
No model or test work runs inside the `create_middleware_fanout` / `pickup` / `complete` / `judge` / `promote` calls; candidates run outside the MCP call. The only subprocess work inside those calls is bounded `git` queries (`_git_query`, 15 s timeout each). They are synchronous `subprocess.run` calls on the event loop, used for worktree and commit verification. `dispatch_single_agent_debate` is the only tool that runs a long subprocess inside the call. So the dispatch_id-loss failure has no analogue here. [INFERENCE: worst-case latency is several 15 s git timeouts in a row; I did not measure it.]

## Scope NOT done
- **E2E pin:** operator approved 2026-09-23. `pipeline_create_test` from this repo's MCP refuses fizzy paths (`INVALID_TEST_PATH`: its root is adversarial-spec). The ready payload is `orchestration/e2e-altitude-pin-create-test.json`: submit it from a session whose fizzy MCP runs in fizzy-pipeline-mcp, then commit that file.
- **Live E2E and real ETB load:** not run, because the Boundaries forbid board calls.
- **MCP server:** not reloaded. The operator starts a fresh session.
- **Research-only leaves:** there is no research-only leaf flow. A leaf like L7 (preregistration protocol) must either go through fan-out with a committed artifact or get an operator `DEFERRED`/`NO_GO` exception. I reported this rather than inventing a flow.
- **Aggregate-root verification format:** the converter points root/leaf `definition_artifact` at markdown. So subsystem verification later takes the markdown requirement-ID path, not the v6 D0-JSON `leaves[{id,contract_tests}]` aggregate path.
- **Uncommitted:** `SKILL.md`, per the Boundaries.
