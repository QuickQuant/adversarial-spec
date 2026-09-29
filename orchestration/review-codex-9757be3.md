REJECT

Reviewed `4c1e099..9757be3`. N1 remains incomplete; two new blocking defects reproduced. Source anchors verified with `git diff` and `nl -ba`; `T` denotes `tests/test_agy_sandbox.py`.

| Item | Status | Evidence | Regression load-bearing? |
|---|---|---|---|
| N1 | PARTIAL — blocking | `agy_sandbox.py:327,567` inspect only workspace evidence. With a boundary-probe STOP, empty workspace, and both persistence writes failing, a fresh process printed `DISPATCHED; LAUNCHES=1`; dead-owner cleanup deleted the retained root. | Yes: `T:1311` fails reverted and passes restored, but covers only workspace-write STOPs. |
| N2 | FIXED | `agy_sandbox.py:195`, `models.py:1170` resolve provisional STOPs after workers finish, then quarantine buffered output. The induced race returned completed incident metadata and retained the late sibling critique. | Yes: `T:1348` fails reverted and passes restored. |
| Gauntlet refusal | FIXED for refusal-only runs | `gauntlet/core_types.py:27`, `gauntlet/orchestrator.py:992` propagate refusal through all eight tested caller paths. End-to-end refusal exits 6, records `agy_refused`, and reaches no checkpoint or zero-concern result. Mixed STOP/refusal remains defective below. | Yes: eight cases at `T:1422`, plus `T:1448`, all fail reverted and pass restored. |

| New ID | Severity | Evidence and mechanism | Required correction |
|---|---|---|---|
| N3 | Blocking | `gauntlet/phase_1_attacks.py:322`, `gauntlet/orchestrator.py:992`: the first refusal unwinds future collection; executor shutdown waits for a sibling’s real STOP but never retrieves it. Reproduced exit 6/`agy_refused` despite a critic STOP in the latch and on disk. Reverted code reports exit 4/`agy_stop`. | Drain sibling outcomes and give STOP precedence over refusal. |
| N4 | Blocking | `agy_sandbox.py:332,361`: a clean sibling removes its root between existence checking and inspection. ENOENT becomes “evidence”; missing repository metadata broadens the block. Reproduced false `blocked` STOP, then `latched` on the next dispatch, with zero launches. Reverted code permits clean dispatch. | Coordinate scanning with cleanup; avoid latching evidence attributed to a vanished root. |

AGY suite: **71 passed, 0 failed, 5 skipped**.
Reversion proof: **11 failed** against `4c1e099` production files; **11 passed** after byte-for-byte restoration.
Additional probes: both N1 boundary cases fail; N3/N4 fail on `9757be3` and pass on `4c1e099`. Logs and archived probe sources: `.scratch/rereview-9757be3/`.

Commands executed:
```bash
export TMPDIR=$PWD/.scratch/tmp UV_CACHE_DIR=$PWD/.scratch/uv-cache
export UV_PROJECT_ENVIRONMENT=/home/jason/PycharmProjects/adversarial-spec/.venv UV_OFFLINE=true
export PYTHONDONTWRITEBYTECODE=1 LITELLM_LOCAL_MODEL_COST_MAP=True
uv run --no-sync pytest skills/adversarial-spec/scripts/tests/test_agy_sandbox.py -q -p no:cacheprovider
uv run --no-sync python .scratch/rereview-9757be3/revert_checks.py
git diff --exit-code 9757be3 -- skills/adversarial-spec/scripts .adversarial-spec/sessions/adv-spec-202607060132-post-fable-hardening-skill.decisions.log
```

Harness fixtures temporarily redirected into this worktree. All source/test edits and test-written decisions restored; final diff check passed. Temporary probe programs archived as `.py.txt`. No real dispatch or commit.