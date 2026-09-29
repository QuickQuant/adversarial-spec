REJECT

Reviewed `85da68f..4c1e099`; routing changes considered only for AGY dispatch. Source paths below are relative to `skills/adversarial-spec/scripts/`; `T` means `tests/test_agy_sandbox.py`.
Evidence re-derived using `git rev-parse --short HEAD`, `git diff 7bd49ca..4c1e099 -- skills/adversarial-spec/scripts`, and `nl -ba` source reads.

| ID | Status | Source evidence and remaining defect | Regression test load-bearing? |
|---|---|---|---|
| R1 | PARTIAL | `agy_sandbox.py:788` latches before evidence I/O; `:796` converts persistence exceptions to STOP. However, failure of both persistence locations permits fresh dispatch; see N1. | Yes. `test_evidence_persistence_failure_is_terminal` (`T:1086`): all three cases fail on reverted source. Does not fail retention-marker writes. |
| R2 | FIXED | `agy_sandbox.py:742`, `:764`, `:774`, `:792`: byte capture, replacement decoding, inspection, raw-byte evidence. | Yes. `test_undecodable_output_still_inspected` (`T:1117`) fails on reverted source with `UnicodeDecodeError`. |
| R3 | FIXED | `agy_sandbox.py:602`, `:608`, `:625`, `:798`: root metadata and traversal failures trigger STOP and retention. | Yes. `test_uninspectable_workspace_is_terminal` (`T:1140`) fails on reverted source because STOP is absent. |
| R4 | FIXED | `agy_sandbox.py:735` holds the publication lock across `_admit(..., held=True)` and `Popen`; `:337` avoids nested acquisition; `:249` releases on exceptions. | Yes. `test_stop_published_at_final_admission_cannot_precede_launch` (`T:1158`) reverses its timestamp assertion on reverted source. Failed-spawn lock-release probe also passed. |
| R5 | FIXED | `gauntlet/orchestrator.py:307` checks admission before directory creation, prompt loading, resume, or provider dispatch. | Yes. `test_gauntlet_prior_stop_refused_before_any_progress` (`T:1189`) reaches the forbidden prompt-loading sentinel on reverted source. |
| R6 | FIXED | `agy_sandbox.py:554`, `:580`, `:584` resolve and mask directory/file targets; `:560` refuses unsupported types. | Yes. `test_symlinked_mask_targets_are_masked` (`T:1218`) exposes Herdr/profile contents on reverted source. |
| R7 | PARTIAL | `agy_sandbox.py:514` preserves marked roots. Failure to create that marker still allows evidence deletion; see N1. | Yes. `test_retained_evidence_root_survives_cleanup` (`T:1257`) loses its marked root on reverted source. Marker-write failure remains uncovered. |
| R8 | FIXED | `models.py:908`, `:1171`, `debate.py:1672` propagate refusal to exit 6; `agy_sandbox.py:821` classifies setup refusal before timeout retry. Gauntlet residue remains separate below. | Yes. `test_dispatch_time_refusal_refuses_round` (`T:1271`) returns 0 on reverted source; setup-timeout and typed-refusal tests also fail there. |
| R9 | FIXED | `T:411` puts the token in stderr; `:563` counts child launches; `:1085` exercises early evidence failures; `:281` guards fake identity; `:987` enumerates all configuration masks. | Yes. Moving the token back to stdout, disabling the fake guard, and removing the knowledge mask each caused its corresponding test to fail. Fresh-process 0/1 assertions also passed in the baseline suite. |

| New ID | Severity | File:line | Defect | Fix |
|---|---|---|---|---|
| N1 | Blocking | `agy_sandbox.py:842`, `:313`, `:514`, `:523` | The new fallback only warns when `retained.json` cannot be written. Induced STOP-state and marker I/O failures produced `DISPATCHED`, `LAUNCHES=1` in a fresh process. Marking the original owner dead then deleted its evidence. This leaves R1/R7 incomplete. | Provide a preallocated or otherwise durable fallback; fail closed when its state is unreadable. Never reclaim evidence whose STOP persistence failed. Add the combined-failure regression. |
| N2 | Should-fix | `agy_sandbox.py:789`, `models.py:1156`, `agy_sandbox.py:466` | A queued sibling can return the provisional latch before incident persistence finishes. The collector keeps that first STOP, whose `incident_dir` is `None`, discards the richer completed STOP, and silently drops late sibling output. Reproduced with two AGY seats and a delayed fake Claude seat. | Resolve provisional STOPs to completed incident metadata and buffer quarantine payloads until an evidence destination exists. |

Network residue — **BLOCKING for canary readiness, static isolation judgment**: `agy_sandbox.py:569` retains host networking without an endpoint policy. API access needs controlled egress, not unrestricted access to host services. Actual TCP/abstract-socket exploitability is unverified; no TCP/abstract-socket probes were run.
Gauntlet refusal residue — **BLOCKING**: `gauntlet/phase_1_attacks.py:321` absorbs refusal, `gauntlet/orchestrator.py:410` checkpoints, and `:977` marks completion. Induced setup failure returned a completed zero-concern result. Propagate typed refusal through every gauntlet caller and refuse the run.

Additional checks: failed spawn released the lock without latching; releasing one retained root preserved another root's marker and existing uncleared incidents; releasing an isolated fallback STOP permitted recovery. All three probes passed. A `history.jsonl -> /dev/null` alias refuses at `agy_sandbox.py:560`: an intentional fail-closed compatibility limitation, not an isolation bypass. No false STOP appeared in the clean/setup-failure controls.

The requested initial `uv run pytest ...` failed before collection: downloading `mcp==1.26.0` required unavailable DNS/network access. Cached-environment commands:
```bash
export TMPDIR=$PWD/.scratch/tmp UV_CACHE_DIR=$PWD/.scratch/uv-cache
export UV_PROJECT_ENVIRONMENT=/home/jason/PycharmProjects/adversarial-spec/.venv UV_OFFLINE=true
export PYTHONDONTWRITEBYTECODE=1 LITELLM_LOCAL_MODEL_COST_MAP=True
uv run --no-sync pytest skills/adversarial-spec/scripts/tests/test_agy_sandbox.py -q -p no:cacheprovider
uv run --no-sync pytest -q -p no:cacheprovider
```

- AGY suite: **60 passed, 0 failed, 5 skipped**. All five socket probes lacked a successful unmasked control here; socket isolation remains unverified on this host.
- Full suite: **1,110 passed, 3 failed, 7 skipped**. Two packaging tests lacked cached `setuptools`; the containment test assumes temporary files are outside the working directory, contradicted by the requested `TMPDIR`. Running that test from `.scratch/rereview` passed (**1 passed**).
- Reversion experiment: `uv run --no-sync python .scratch/rereview/revert_check.py` temporarily restored four production files to `7bd49ca`; **12 failed, 53 deselected**, at the expected defect assertions. All four files restored byte-for-byte afterward.
- R9 experiments: `uv run --no-sync python .scratch/rereview/r9_checks.py`; **1 failed, 64 deselected** for each of three deliberate mutations. Each mutation restored.
- Additional probes: `uv run --no-sync pytest .scratch/rereview/test_review_hypotheses.py -q -p no:cacheprovider`; **3 passed, 4 failed**: N1, N2, gauntlet refusal, and the deliberate `/dev/null` compatibility expectation.

Logs and archived probe programs: `.scratch/rereview/` (`agy-suite-cached.log`, `full-suite.log`, `reverted-regressions.log`, `r9-*.log`, `hypotheses-final.log`, `probe-sources.log`).
The harness fixture base was temporarily redirected from `~/.cache` into this worktree. Restored that edit, every mutation, and test-written decisions-log entries; removed temporary probe programs after archiving their text. `git diff --exit-code 4c1e099 -- skills/adversarial-spec/scripts .adversarial-spec/sessions/adv-spec-202607060132-post-fable-hardening-skill.decisions.log` passed. Pre-existing activity-log/handoff changes preserved. No real critic dispatch, commit, or push.