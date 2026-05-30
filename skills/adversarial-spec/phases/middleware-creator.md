> **FIRST ACTION upon entering this phase:** Create this TodoWrite immediately.
> Do NOT read further until the TodoWrite is active.
> Every `[GATE]` item must be marked completed before proceeding past it.

```
TodoWrite([
  {content: "Verify middleware candidates and finalized spec [GATE]", status: "in_progress", activeForm: "Verifying middleware candidates"},
  {content: "Confirm middleware materialization decision", status: "pending", activeForm: "Confirming middleware materialization"},
  {content: "Ensure execution plan and Fizzy source task cards exist [GATE]", status: "pending", activeForm: "Ensuring source task cards exist"},
  {content: "Verify per-middleware test suite paths [GATE]", status: "pending", activeForm: "Verifying middleware test suites"},
  {content: "Create middleware fanouts in dependency order", status: "pending", activeForm: "Creating middleware fanouts"},
  {content: "Monitor middleware implementation and judge cards [GATE]", status: "pending", activeForm: "Monitoring middleware cards"},
  {content: "Promote judged winners to canonical source task paths [GATE]", status: "pending", activeForm: "Promoting judged middleware winners"},
  {content: "Record selected implementations and benchmark metrics", status: "pending", activeForm: "Recording middleware results"},
  {content: "Transition back to execution/implementation", status: "pending", activeForm: "Transitioning after middleware pass"},
])
```

Mark each step `completed` as you finish it. Mark the current step `in_progress`.

---

# Middleware Creator Phase

This optional phase materializes Phase 4 `middleware-candidates.json` into competitive Fizzy middleware fanouts.

It is a **post-execution, pre-implementation gate**:

1. Phase 4 identifies reusable middleware candidates.
2. Phase 5/6 gauntlet and finalization validate that those candidates still belong in the spec.
3. Phase 7 creates and loads the execution plan so every candidate has a source task card already on the board.
4. Middleware Creator launches competitive fanouts before normal implementation pickup begins.
5. The judge selects a winning implementation and locks the source task in `awaiting_promotion`.
6. The selected implementation is promoted to the canonical source task path before normal Review begins.

This phase activates between `execution` (Phase 7) and `implementation` (Phase 8) in the router. By the time it runs, `pipeline_create_middleware_fanout`'s required substrate — typed source task cards, test suite paths, `fizzy-plan.json` — already exists from Phase 7. If any of those are missing on entry, the correct action is to **return to `execution`**, not to run a partial Phase 7 pass from inside this phase.

---

## Required Inputs

Load only the files needed for the current session:

- Session detail JSON and `.adversarial-spec/session-state.json`
- Final spec path from session state (`spec_path`)
- `.adversarial-spec/specs/<slug>/middleware-candidates.json`
- `.adversarial-spec/specs/<slug>/target-architecture.md`
- `.adversarial-spec/specs/<slug>/tests-spec.md` when present
- Execution plan path from session state (`execution_plan_path`) when present
- `fizzy-plan.json` path from session state or Phase 7 output when present
- Board id from `projects.yaml`; never rely on default board state

Skip this phase only when:

- No `middleware-candidates.json` exists.
- The candidate file exists but contains no materializable candidates.
- The user explicitly chooses to skip middleware materialization.

When skipped, update session state with `middleware_creator_status: "skipped"` and transition to Phase 7 execution planning.

---

## Step 1: Validate Candidate Artifact [GATE]

Read `middleware-candidates.json` and validate it before doing any pipeline work.

Required candidate fields:

- `id`
- `name`
- `purpose`
- `inputs`
- `outputs`
- `sync_async`
- `depends_on`
- `linked_user_stories`
- `linked_goals`
- `linked_invariants`

Validation rules:

- Candidate IDs must be unique and stable.
- `depends_on` must reference candidate IDs in the same file.
- Dependency graph must be acyclic.
- Each candidate must trace to at least one user story or goal.
- Each candidate must trace to at least one active architecture invariant unless Phase 4 explicitly marked the candidate as lightweight advisory.
- Candidate scope must still match the finalized spec. If the final spec removed the behavior, do not materialize it.

If validation fails, stop and report the exact candidate ID and field. Do not create partial fanouts.

---

## Step 2: Confirm Materialization Decision

Present a concise summary before launching fanouts:

```markdown
Middleware Pass
───────────────────────────────────────
Candidates: N
Dependency layers: L
Requires execution cards: yes
Requires test suite paths: yes

I will create one Fizzy fanout per candidate:
- N implementation cards assigned to the configured models
- 1 judge card assigned to the conductor
- source task locked with middleware fanout metadata until judging completes
```

Ask the user whether to materialize now, skip, or return to execution planning if source cards are missing.

Do not launch fanouts silently. This phase can multiply work across agents and must be an explicit user decision.

---

## Step 3: Ensure Execution Substrate Exists [GATE]

`pipeline_create_middleware_fanout` requires a `source_task_card_id` whose card state has `card_type: "task"` and whose lane is `New Todo` or `Failed Review`.

Before calling it:

1. Verify `execution_plan_path` exists.
2. Verify `fizzy-plan.json` exists or can be generated from the approved execution plan.
3. Verify `pipeline_load` has created source task cards.
4. Verify each middleware candidate maps to exactly one source task card.

Mapping guidance:

- Prefer an explicit candidate ID in the task title, description, or metadata.
- Otherwise map by declared implementation path, package/module scope, and linked invariant IDs.
- If no source task maps cleanly, return to Phase 7 and amend the execution plan. Do not create ad hoc cards with `add_card`; raw cards will fail the middleware fanout gate because they are not typed pipeline task cards.
- If multiple tasks map to one candidate, split or annotate the execution plan before proceeding.

Normal implementation pickup must not start while a candidate's source task is in `fanout_active` or `awaiting_promotion` state.

---

## Step 4: Verify Test Suite Paths [GATE]

The Fizzy MCP fanout API validates `test_suite_path` before creating cards. The file must exist and must stay within `PIPELINE_TEST_ROOT` or the current process root when `PIPELINE_TEST_ROOT` is unset.

For each candidate:

1. Identify the deterministic test suite path that will judge implementations.
2. Ensure the path exists on disk.
3. Ensure the path is inside the allowed test root.
4. Ensure the test suite covers the candidate's typed inputs, outputs, error modes, dependency assumptions, and invariant links.

Current limitation: the MCP fanout implementation does not generate a test-consensus suite by itself. If no test suite exists, create or route back to execution planning to create one before launching the fanout.

Acceptable test suite sources:

- Existing project test file dedicated to the middleware contract.
- `tests-spec.md` section promoted into a concrete project test file.
- Candidate-specific test spec file under `.adversarial-spec/specs/<slug>/middleware-tests/` when the project implementation task will later turn it into executable tests.

Prefer executable project tests when implementation agents can run them. Use markdown test specs only when the middleware contract is intentionally language/tool agnostic and record the limitation in the source task comments.

---

## Step 5: Create Fanouts

Only the conductor model may create or cancel fanouts. Workers implement assigned middleware cards but do not create fanouts for themselves.

Call `pipeline_create_middleware_fanout` once per candidate in topological dependency order:

```text
mcp__fizzy__pipeline_create_middleware_fanout(
  board_id=<explicit board id>,
  session_id=<session id>,
  agent=<conductor alias>,
  source_task_card_id=<typed source task card>,
  middleware_id=<candidate id>,
  middleware_name=<candidate name>,
  purpose=<candidate purpose>,
  test_suite_path=<existing path>,
  models=<configured implementation models>
)
```

Default implementation model set: use the session's configured model pool. If no session-specific pool exists, use the project standard for middleware fanouts and record the chosen model list in the session journey log (`sessions/<id>.journey.log`).

After each fanout:

- Confirm implementation cards were created.
- Confirm one judge card was created.
- Confirm source task metadata shows `extensions.middleware.status: "fanout_active"`.
- Add a concise source-card comment linking candidate ID, test suite path, dependency layer, and expected judge criteria.

If any fanout creation fails, stop. Do not continue to later dependency layers until the failure is resolved.

---

## Step 6: Monitor Implementation and Judge Cards [GATE]

Implementation agents should use the middleware-specific pipeline tools:

- `pipeline_pickup_middleware_impl`
- `pipeline_complete_middleware_impl`
- `pipeline_drop_middleware_impl` when an implementation is intentionally abandoned

Implementation completion must include:

- `impl_path`
- `commit_hash`
- `tests_passed`
- `tests_failed`
- `time_seconds`
- `lines`
- `chars`
- Optional `test_dispute` when tests are incomplete, unavailable, or contested

The judge should call `pipeline_middleware_judge` only after all viable implementation cards are complete or intentionally dropped. The default winner should be the smallest passing implementation by the pipeline's judge criteria unless there is a documented correctness, maintainability, or integration reason to override.

After judging:

- The selected implementation card should move to the appropriate passed lane.
- Losing implementation cards should be completed/unmapped or otherwise closed by the pipeline tool.
- The source task should leave `fanout_active`, enter `awaiting_promotion`, and carry selected implementation metadata.
- The source task is not Review-ready yet. Do not call normal `pipeline_complete_task`, `pipeline_review`, or `pipeline_patch_state` on it.
- Dependent middleware candidates can start only after their dependencies are judged and promoted when they need the dependency's canonical code path.

---

## Step 6.5: Promote Winners to Canonical Source Tasks [GATE]

After each judge result, promote the selected implementation into the source task's canonical path before allowing normal Review.

Use `pipeline_do_next_task`; judged source tasks in `awaiting_promotion` should return action `middleware_promote` to the selected implementation agent or conductor. If operating directly, call:

```text
mcp__fizzy__pipeline_promote_middleware_winner(
  board_id=<explicit board id>,
  session_id=<session id>,
  source_task_card_id=<typed source task card>,
  agent=<selected implementation agent or conductor>,
  promotion_commit_hash=<commit that copies/renames winner to canonical path>,
  canonical_impl_path=<canonical path required by the source task>,
  notes=<optional promotion notes>
)
```

Promotion rules:

- Treat the judge result as authoritative. Read the judge card comment and `middleware-results.jsonl` before editing.
- Use `selected_impl_path` and `selected_commit_hash` as the source of truth. Do not replace the winner with a losing canonical implementation or current `HEAD`.
- If the selected implementation lives at a variant path, copy or rename it into the canonical source task path before retiring variants.
- Commit the promotion, then call `pipeline_promote_middleware_winner`.
- Only the selected implementation agent or conductor may promote.
- `pipeline_patch_state` must not be used to rewrite `impl_path`, `commit_hash`, `implementer_agent`, or `extensions` while the source task is locked.
- After promotion, the source task moves to `Review`; then normal review and testing gates apply.

---

## Step 7: Record Results

Write or append a session-local result artifact:

```text
.adversarial-spec/specs/<slug>/middleware-results.jsonl
```

Each JSONL record should include:

- `middleware_id`
- `middleware_name`
- `source_task_card_id`
- `fanout_card_ids`
- `judge_card_id`
- `selected_impl_card_id`
- `selected_model`
- `selected_commit_hash`
- `selected_impl_path`
- `promotion_commit_hash`
- `canonical_impl_path`
- `tests_passed`
- `tests_failed`
- `time_seconds`
- `lines`
- `chars`
- `test_suite_path`
- `decision_notes`

Update session state:

```json
{
  "current_phase": "execution",
  "current_step": "Middleware creator complete; selected winners promoted and execution ready for implementation pickup",
  "middleware_creator_status": "complete",
  "middleware_results_path": ".adversarial-spec/specs/<slug>/middleware-results.jsonl"
}
```

If the middleware pass was skipped:

```json
{
  "current_phase": "execution",
  "current_step": "Middleware creator skipped; continue execution planning",
  "middleware_creator_status": "skipped"
}
```

---

## Failure Handling

Use pipeline tools, not direct card moves, for all middleware state transitions.

Hard stops:

- Candidate artifact invalid.
- Final spec path missing.
- Execution plan missing and user does not approve generating/loading it.
- Source task card missing or not typed as a pipeline task.
- Source task not in `New Todo` or `Failed Review`.
- Test suite path missing or outside allowed root.
- Fanout creation partially fails.
- Judge cannot identify a valid completed implementation.

Recovery paths:

- Missing source task: return to Phase 7, amend/load the execution plan, then resume this phase.
- Missing tests: create the test suite or route to execution planning to produce it.
- Failed implementation: let remaining implementation cards complete; judge only viable cards.
- All implementations failed: mark the source task `Failed Review` through the pipeline review/test path and record the failure summary.
- Incorrect fanout: conductor may use `pipeline_cancel_middleware_fanout` with a reason before implementations are judged.

---

## Exit Criteria

This phase is complete when one of these is true:

- Every materialized candidate has a judged selected implementation and the session has `middleware_creator_status: "complete"`.
- The user explicitly skipped materialization and the session has `middleware_creator_status: "skipped"`.
- No candidates exist and the session has `middleware_creator_status: "not_applicable"`.

After exit, route to Phase 7 if execution planning still needs approval/loading. Route to Phase 8 only when the execution plan is loaded, middleware fanouts are complete or skipped, and the user has approved implementation pickup.
