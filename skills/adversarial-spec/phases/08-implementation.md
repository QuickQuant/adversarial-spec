## Implementation (Phase 8)

After the execution plan is generated, offer to proceed with implementation:

> "Execution plan generated with N tasks. Would you like to proceed with implementation?"

---

### Agent Identity (REQUIRED)

You must identify yourself with a stable agent name for cross-agent review enforcement.
The pipeline skips Review cards where `last_agent == requesting agent` — without a
stable name, cross-agent review breaks.

| Agent | Name to pass |
|-------|-------------|
| Claude Code | `claude` |
| Codex | `codex` |
| Gemini CLI | `gemini` |

Pass your agent name in every `pipeline_*` call.

---

### Setup Checklist (REQUIRED before the self-pickup loop)

**Do NOT enter the self-pickup loop until ALL of these are done:**

```
Implementation Setup
───────────────────────────────────────
[ ] Session ID and Board ID identified
[ ] Fizzy cards loaded (pipeline_load or manual creation)
    — verify with pipeline_lane_state(pipeline="task")
[ ] Context loaded (see Context Loading below)
```

**Session ID discovery:**
1. If provided at invocation, use it
2. Otherwise: read `.adversarial-spec/session-state.json` → `active_session_id`
3. If no active session: stop and report — cannot self-pick without a session

**Board ID discovery:**
Board is **not** pinned implicitly at server startup for implementation work. Identify the target board from the session, card state, or project config, then pass `board_id` explicitly on every board-scoped `pipeline_*` call.

If you do not know the board ID yet, stop and discover it before entering the self-pickup loop. Do **not** rely on `FIZZY_BOARD_ID` as a hidden default.

**If cards are not yet loaded:** The execution plan must be converted to Fizzy cards first.
Use `pipeline_load(plan_path, session_id)` with the `fizzy-plan.json` from the execution phase.

---

### Context Loading (REQUIRED before implementing any card)

Before entering the loop, load these in order. Without this context, you will make
implementation decisions that contradict the spec or the codebase's existing patterns.

#### 1. Project conventions
- Read `CLAUDE.md` (or `AGENTS.md` for Codex) — project rules, test/lint commands, key paths

#### 2. Architecture docs
- Read `.architecture/INDEX.md` for navigation (your reference, not context to carry)
- Read `.architecture/primer.md` — system summary, components, contracts, gotchas
- If the session touches known debt areas: read `.architecture/concerns.md`
- Read 2-4 matched component docs from `.architecture/structured/components/` based on
  which modules the execution plan modifies

**How to match components:**
- Read the execution plan's file list (or the session file's `requirements_summary`)
- Compare file paths against the INDEX component table's "Key Files" column
- Read the matching component docs

#### 3. The spec
- Read the spec output: path is in the session file's `spec_path` field,
  or at `.adversarial-spec/specs/<slug>/spec-output.md`
- This is the debated and gauntleted specification. Implementation must conform to it.
- Pay attention to: Goals/Non-Goals, acceptance criteria, gauntlet concerns that were accepted

#### 4. The execution plan
- Read the execution plan: path is in the session file's `execution_plan_path` field,
  or at `.adversarial-spec/specs/<slug>/execution-plan.md`
- This defines: task breakdown, wave ordering, file structure (Architecture Spine),
  validation strategies, dependency graph, and parallelization guidance

**Context budget note:** For large specs/plans, read the sections relevant to your
current wave rather than loading the entire document. The card description has the
specific task requirements; the spec and plan provide the "why" and "how it fits."

---

### The Self-Pickup Loop

This is the core implementation protocol. All agents (Claude, Codex, Gemini) follow the same loop.

#### Step 1: Get Next Task

```
pipeline_do_next_task(
  session_id = SESSION_ID,
  pipeline   = "task",
  agent      = AGENT_NAME,
  board_id   = BOARD_ID
)
```

The pipeline walks lanes in priority order and returns the next qualifying card:

| Priority | Lane | Selection Rule |
|----------|------|----------------|
| 1 | Failed Review | First unclaimed card (claim-wait-verify) |
| 2 | Review | First card where `implementer_agent != requesting agent` |
| 3 | Untested | First card |
| 4 | New Todo | First unclaimed card where all `depends_on` are satisfied (claim-wait-verify) |
| 5 | Passed Test | Only when lanes 1-4 are all empty |

**Card Claiming Protocol (built into MCP):**
For Failed Review and New Todo lanes, the pipeline uses a claim-wait-verify protocol
to prevent two agents from working on the same card simultaneously:

1. **Write claim:** Set `claimed_by` + `claimed_at` in the card's state/metadata
2. **Wait 3 seconds:** Race-condition window — if another agent also claimed, their
   write may overwrite ours
3. **Re-read and verify:** Fetch the card again. If `claimed_by` still matches our
   agent name, the claim succeeded. If not, skip the card and try the next one.

Claims expire after 10 minutes (stale claims are ignored). This is fully automatic —
agents don't need to do anything special beyond calling `pipeline_do_next_task`.

Returns: `{card_id, task_id, action_string, lane, effort, strategy}` or idle.

#### Step 2: Execute Based on Action

**action = "implement" (from New Todo)**

1. Read the card description: `get_card_description(card_id)`
2. Read checklists for acceptance criteria: `get_card_checklists(card_id)`
3. If `.conductor/config.json` exists and conductor is enabled:
   - Claim files before editing: `bq conductor claim create PATH --workflow SLUG --agent AGENT`
4. Implement the changes:
   - Follow structural conformance rules (see below)
   - Follow validation strategy from `strategy` field (test-first or test-after)
   - Address all acceptance criteria
5. Run project tests and lint (commands from CLAUDE.md / AGENTS.md)
6. Commit with card reference: `[TASK_ID] Short description`
7. Complete: `pipeline_complete_task(session_id, card_id, agent, commit_hash, board_id)`
8. If conductor enabled: release claims
9. **Return to Step 1**

**action = "fix" (from Failed Review)**

Same as "implement" but:
1. Read the card's review notes for what failed (in the state block or card comments)
2. Fix the specific issues raised by the reviewer
3. Do not rewrite the entire implementation — address the review feedback

**action = "review" (from Review lane, cross-agent enforced)**

1. Read the card description and state block
2. Identify the `commit_hash` from the state block
3. Review the change set:
   - `git diff` / `git log` to inspect changes
   - Does it satisfy the card's acceptance criteria?
   - Does it follow project conventions?
   - Do tests pass?
4. Submit verdict:
   ```
   pipeline_review(session_id, card_id, agent, verdict, board_id, notes)
   ```
   - `verdict`: `"approved"` or `"changes_requested"`
   - `notes`: **REQUIRED** for `"changes_requested"` — explain what needs fixing
5. **Return to Step 1**

**action = "test" (from Untested)**

1. Read the card description and `commit_hash`
2. Run the project's test suite
3. Submit result:
   ```
   pipeline_test(session_id, card_id, agent, result, summary, board_id)
   ```
   - `result`: `"passed"` or `"failed"`
   - `summary`: brief test results
4. **Return to Step 1**

**action = "sweep" (from Passed Test, only when all other lanes empty)**

1. **Do NOT call pipeline_sweep yet.** All cards in Passed Test means implementation
   is done, but verification hasn't run.
2. **Transition to Phase 9: Verification.** Follow `09-verification.md`.
3. Verification produces a report and either sweeps (all pass) or fails specific cards.
4. **Stop the self-pickup loop.** Phase 9 takes over from here.

**action = "idle" (no qualifying cards)**

1. Report status to the user:
   - If reason mentions self-review skip: "Cards exist in Review but need a different agent to review them."
   - If all lanes empty: "All cards completed. Implementation done."
2. **Stop the loop.** Do not continue polling.

#### Step 3: Iterate

After each completed action, immediately return to Step 1. The loop continues
until the pipeline returns "idle."

---

### Cross-Agent Review: The Core Value Proposition

The pipeline enforces that the implementer cannot review their own work:

1. `pipeline_do_next_task` skips Review cards where `last_agent == requesting agent`
2. `pipeline_review` rejects the call if `implementer == reviewer`

This means:
- Agent A implements a card → card moves to Review
- Agent B (different agent) reviews it
- If B requests changes → card moves to Failed Review → Agent A or C picks it up
- Cycle continues until a different agent approves

**Every change gets a genuinely independent review.** This eliminates self-confirming bias
without requiring human involvement.

---

### CRITICAL: Structural Conformance

**The execution plan's file structure is a contract, not a suggestion.**

Before creating any file, check it against the Architecture Spine's file structure. If the filename is not listed there, do not create it. This applies to:
- Source modules
- Test helper files
- Utility modules
- "Temporary" files

If you believe a new file is needed that the plan doesn't list, **stop and update the execution plan first** — get user approval, then create the file. The plan must be updated before the code, never after.

**After completing each wave**, run `/checkpoint`. The checkpoint captures structural state and creates a natural review point. This is not optional — it is how structural drift gets caught before it compounds.

**Anti-patterns that cause architectural drift:**
- Creating files not in the plan because a module "feels too big"
- Renaming concepts during implementation ("discovery_engine" instead of "discovery")
- Splitting one planned module into multiple files without plan authority
- Adding code that doesn't exist in the plan's scope (building W2 features during W0)
- Fixing bugs in wrong files instead of catching that the file shouldn't exist

---

### CRITICAL: Process Discipline During Implementation

**DO NOT abandon the structured process when users ask about specific issues.**

When a user asks "can you check X" or "I want to see Y working":

1. **Check scope first** — Is this part of the current session's tasks?
2. **Track it** — Add the investigation as a Fizzy card or comment on the relevant card
3. **Targeted queries only** — Don't burn context with ad-hoc debugging
4. **Identify root cause** — Don't just poke values to make things "look right"
5. **Propose fix through process** — Update Fizzy card with the fix needed

**Anti-patterns to avoid:**
- Spending 50+ turns on ad-hoc debugging without tracking the work
- Manually setting values to make the UI "look right"
- Multiple restarts and retries without identifying root cause
- Switching into "fix it now" mode, abandoning the process
- Treating passing tests as proof that module boundaries are correct

---

### Fizzy Context Discipline

**Board targeting:** Treat `board_id` as an explicit per-call routing parameter for board-scoped operations. Never assume the active board from server startup state or `FIZZY_BOARD_ID`.

**Subagent rule (Claude only):** Use a subagent with a low-reasoning model (haiku) for bulk Fizzy reads. Fizzy API responses are smaller than Trello's (native metadata, no description-embedded state), but bulk operations still bloat main context. This applies to:
- Creating cards in bulk
- Fetching cards from multiple lists
- Any MCP call that returns unbounded data

For single-card operations (get_card_description, pipeline_do_next_task, pipeline_complete_task), direct calls are fine.

---

### Validation Strategy

**High-risk tasks** (3+ concerns, or `strategy: "test-first"`) use test-first validation:
- Write tests based on acceptance criteria before implementation
- Ensure tests cover failure modes from concerns
- Implementation must pass all tests

**Lower-risk tasks** (`strategy: "test-after"`) use test-after validation:
- Implement the feature
- Write tests after
- Still address all acceptance criteria

**Skip tasks** (`strategy: "skip"`):
- No tests needed (documentation, config-only changes)
- Still verify the change works
