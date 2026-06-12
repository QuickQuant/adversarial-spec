# Handoff C: Fix Validate-Loop Rejects in the Emission (Codex)

You are Codex in repo root `/home/jason/PycharmProjects/adversarial-spec`. You (a prior
Codex run) authored `.adversarial-spec/specs/validation-leg-process/orchestration/emit_driver.py`
which emitted `fizzy-plan.json`. The live `pipeline_validate_plan` gate rejected it with
44 structured issues (2 classes). Local `self_check_plan` does not cover these checks
(known parity gap). Fix the DRIVER (durable), re-emit, re-verify. Local only — no MCP,
no board, no commit.

## The served contract (read from fizzy-pipeline-mcp/src/fizzy_pipeline_mcp/pipeline.py — paths below are in THAT repo, read-only for you)

1. **`MATURITY_FLOOR_VIOLATION` (24 tasks)** — `implementation_status` must be EXACTLY
   one of the enum tokens `greenfield | partial | already-built`
   (`MATURITY_RANK`, pipeline.py L285-292; check at L5017-5022). The current plan has
   prose like `greenfield — "validation_emission.py absent (ls 2026-06-11)"` and even
   `·`-joined field runs. Fix: emit the bare token. The evidence prose stays in
   execution-plan.md (its home); do NOT invent a new plan field for it.
   Mapping per execution-plan.md: `partial` for SS-5, C-5.1, C-5.2; `greenfield` for
   everything else (the one task already emitting bare `greenfield` is why only 24 of
   25 flagged).

2. **`missing_required_verify_commands` (20 tasks)** — behavior-changing tasks with an
   automated verification_mode require a TOP-LEVEL `verify_commands` field: non-empty
   list of strings, each ≤512 chars (pipeline.py L4716-4723; nesting inside
   verification_binding does not satisfy it). Flagged tasks:
   SYS, SS-1, SS-2, SS-3, SS-4, C-1-1..C-1-4, C-2-1..C-2-3, C-3-1..C-3-3, C-4-1..C-4-5.
   - Components: use the per-node `verify_commands` line VERBATIM from
     execution-plan.md (e.g. C-1.1 → `uv run pytest scripts/tests/test_validation_emission.py -k envelope -q`).
   - SYS and SS-1..SS-4 (scope full-suite, no explicit line in the plan):
     `uv run pytest scripts/tests/test_validation_emission.py -q`.
   - C-4-6 is behavior_change=false → warn-only; adding its `-k status` command anyway
     is fine and preferred.

## Task-id constraint (already fixed once — keep it fixed)
The gate's `RE_TASK_ID` is `^[A-Za-z0-9_-]{1,32}$` — NO DOTS. The plan on disk was
already normalized (C-1.1 → C-1-1) by
`orchestration/fix_task_ids.py`. Your driver still emits dotted ids. Choose ONE:
  (a) patch the driver to emit dash-form ids natively (preferred; if artifact dir
      names/paths derive from task_id and therefore change, ensure the emitted paths
      point at the files actually written, and remove orphaned dotted dirs you replace), or
  (b) keep dotted ids internally and run
      `python3 .adversarial-spec/specs/validation-leg-process/orchestration/fix_task_ids.py`
      after every emission.
End state must satisfy: every task_id matches RE_TASK_ID; every spec_refs /
verification_binding path resolves to a real file; hashes re-derived from real files.

## Required end state (verify before finishing)
1. Re-emit `fizzy-plan.json` via the patched driver (+ fix script if route (b)).
2. `self_check_plan()` → `{"valid": true, "issues": []}`.
3. Assert ALL 25 `implementation_status` values ∈ {greenfield, partial, already-built}.
4. Assert the 20 flagged tasks (+ C-4-6 if you add it) have non-empty top-level
   `verify_commands`, every entry ≤512 chars.
5. Assert no task_id contains a dot; spot-check 3 random verification_binding paths exist.
6. Append a `## Validate-loop round 1 fixes` section to
   `orchestration/emission-report.md`: what changed in the driver, which route (a/b)
   you took, assertion outputs.

Full reject detail (if needed): `orchestration/validate-rejects.json`.

Final message: ≤8 lines — route taken, assertion results, any deviation.
