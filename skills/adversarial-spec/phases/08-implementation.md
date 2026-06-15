## Implementation (Phase 8)

> **FIRST ACTION on entering this phase:** create this TodoWrite. Do NOT read further until it's active.

```
TaskCreate([
  {subject: "Identify agent name, session ID, board ID", status:"pending", activeForm:"Identifying agent and session"},
  {subject: "Load Fizzy cards (pipeline_load or verify existing)", status:"pending", activeForm:"Loading Fizzy cards"},
  {subject: "Read CLAUDE.md / AGENTS.md", status:"pending", activeForm:"Reading project conventions"},
  {subject: "Read .architecture/INDEX.md + primer.md", status:"pending", activeForm:"Reading architecture docs"},
  {subject: "Read matched component docs", status:"pending", activeForm:"Reading component architecture"},
  {subject: "Read the converged spec", status:"pending", activeForm:"Reading spec"},
  {subject: "Read the execution plan", status:"pending", activeForm:"Reading execution plan"},
  {subject: "Enter self-pickup loop", status:"pending", activeForm:"Running self-pickup loop"},
])
```

**[GATE]** Items 3-7 must be `completed` before item 8 starts. Skipping arch docs → decisions that contradict existing patterns. Confirmed failure mode.

Multi-agent reminder: once in the loop, keep TodoWrite items phase-scoped (e.g., "Process next review card"). Never hardcode card IDs or commit hashes — the pipeline is authoritative.

After execution plan is generated, ask: *"Execution plan generated with N tasks. Proceed with implementation?"*

---

### Agent Identity (REQUIRED)

Cross-agent review enforcement depends on a stable agent name. Pipeline skips Review cards where `last_agent == requester`.

| Agent | Name to pass |
|-------|--------------|
| Claude Code | `claude` |
| Codex | `codex` |
| Gemini CLI | `gemini` |

Pass your name on every `pipeline_*` call.

---

### Setup Checklist (before the self-pickup loop)

```
[ ] Session ID and Board ID identified
[ ] Fizzy cards loaded — verify with pipeline_lane_state(pipeline="task")
[ ] Context loaded (see below)
```

**Session ID:** if provided at invocation, use it. Else read `.adversarial-spec/session-state.json` → `active_session_id`. No session → stop and report.

**Board ID:** not pinned implicitly. Identify from session / card state / project config, and pass `board_id` explicitly on every board-scoped call. Never rely on `FIZZY_BOARD_ID` as a hidden default.

**Cards not loaded:** convert the execution plan to Fizzy cards via `pipeline_load(plan_path, session_id)` using the `fizzy-plan.json` from Phase 7.

---

### Context Loading (before implementing any card)

Load in order. Skipping this → decisions that contradict the spec or codebase patterns.

1. **Project conventions:** `CLAUDE.md` (or `AGENTS.md` for Codex).
2. **Architecture docs:**
   - `.architecture/INDEX.md` — navigation only (your reference, don't pass to opponent models).
   - `.architecture/primer.md` — system summary, contracts, gotchas.
   - `.architecture/concerns.md` if the session touches known debt.
   - 2-4 component docs from `.architecture/structured/components/`, matched by parsing the execution plan's file list against the INDEX "Key Files" column.
3. **Spec:** path from session detail `spec_path`, else `.adversarial-spec/specs/<slug>/spec-output.md`. Pay attention to Goals/Non-Goals, acceptance criteria, accepted gauntlet concerns.
4. **Execution plan:** path from session detail `execution_plan_path`, else `.adversarial-spec/specs/<slug>/execution-plan.md`. Defines task breakdown, wave ordering, Architecture Spine, validation strategies, dependency graph.

**Context budget:** for large specs/plans, read only the section relevant to your current wave. The card description has the concrete requirements; the spec/plan supply the "why."

**[GATE]** Mark "Read .architecture/INDEX.md + primer.md" and "Read matched component docs" completed before starting the loop. Confirmed failure (2026-04-10): 3 tasks shipped without arch docs, missed pattern conformance during both impl and review.

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
8. **Append to decisions log** (see SKILL.md "Decisions Log"):
   ```bash
   printf '%s [%s] %s — %s\n' "$(date -u +%FT%TZ)" "<card_id>" \
     "<what landed, incl. commit hash>" "<why it matters>" \
     >> .adversarial-spec/sessions/<session_id>.decisions.log
   ```
   One line. Skip if the commit message already says everything material.
9. If conductor enabled: release claims
10. **Return to Step 1**

**action = "fix" (from Failed Review)**

Same as "implement" but:
1. Read the card's review notes for what failed (in the state block or card comments)
2. Fix the specific issues raised by the reviewer
3. Do not rewrite the entire implementation — address the review feedback

**action = "review" (from Review lane, cross-agent enforced)**

1. Read the card description and state block
2. Identify the `commit_hash` from the state block
3. **Measure the diff first:** `git show --stat <commit_hash>` — total lines changed across all files.
4. **Pick review tier by size** (below); don't default to the deepest tier on every card — reading an entire 30-line rename burns context for no gain.
5. Run the tier's checks.
6. Submit verdict:
   ```
   pipeline_review(session_id, card_id, agent, verdict, board_id, notes)
   ```
   - `verdict`: `"approved"` or `"changes_requested"`
   - `notes`: **REQUIRED** for `"changes_requested"` — explain what needs fixing
7. **Return to Step 1**

#### Size-Tiered Review Recipe

| Diff size (lines changed) | Tier | Review recipe |
|---------------------------|------|---------------|
| ≤ 30 | **Spot** | `git show` once, confirm acceptance criteria satisfied, run tests listed on the card. No architecture doc re-read needed. |
| 31–200 | **Small** | Read full diff, verify against card acceptance criteria, run tests, spot-check edge cases (null/empty/failure paths). Confirm no new files outside Architecture Spine. |
| 201–800 | **Medium** | Read full diff, check against spec section (`spec_path`) relevant to this card, verify test coverage of failure modes, confirm no structural drift (file structure matches plan). Run tests + any adjacent integration suites. |
| > 800 | **Large / push back** | Default to `changes_requested` with note: "Diff exceeds 800 lines — decompose into smaller cards before re-review." Only approve if the card explicitly authorizes a large diff (e.g., codegen, vendored dependency) AND a structured walkthrough comment justifies each file. |

**Anti-patterns:**
- Approving "looks fine" without running tests on Small+ cards.
- Reading only the first hunk and generalizing ("rest looks similar").
- Re-reading the full architecture primer for a Spot-tier rename.
- Requesting changes on Spot-tier cards for style nits — leave a comment, approve the functional change.

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

### Validation leg (system altitude)

> **Altitude gate — run this leg ONLY for system-altitude sessions.** Read the
> session's `session_altitude` from the **card metadata via MCP**
> (`get_card_metadata` with the explicit `board_id` from `projects.yaml` and the
> `card_id` from the session detail file), never from local session state alone (US-2).
> - `session_altitude == "system"` → run the close algorithm below before the
>   Finalization advance.
> - `session_altitude` is `component`/`feature`, or the v5 obligation is absent →
>   **SKIP this entire section.** Sub-system altitudes carry no validation obligation
>   (NG2); there is no ConOps, no ledger, and no close call to make.

**What this closes.** Phase 7 drafted the validation rows (see `07-execution.md`
"Validation leg"); this leg *executes the scenarios, gets Jason's judgments, and
closes the gate*. Fizzy pipeline v5 refuses the Finalization→Completed advance for a
system node whose ConOps user stories lack a *passing validation row* — a gate
independent of verification (`system_validation_complete` ≠
`system_verification_complete`; verification asks "built it right?", validation asks
"built the right thing?"). The conductor drives the close; the module
(`~/.claude/skills/adversarial-spec/scripts/validation_emission.py`, prefix every call
with `uv run python`) validates shapes, stamps every hash, and mechanizes the
emission — **it never generates prose and never judges**. Every invocation prints one
JSON envelope on stdout (`{"status","code","issues","data"}`); exit 0 = ok, 2 =
validation issues/reprompt, 3 = environment/lock/corrupt.

**The MCP close call.** The gate is closed CARD-SIDE (never plan-side — a
`system_validation` key in a task's verification binding is rejected by fizzy as
`VV_ABOVE_ALTITUDE`). The single tool is
`pipeline_mark_system_validation_complete`, called with explicit `board_id`:

```
pipeline_mark_system_validation_complete(
  card_id                  = SYSTEM_NODE_CARD_ID,  # the system-altitude TASK node, NOT the session card
  session_id               = SESSION_ID,
  board_id                 = BOARD_ID,            # explicit, from projects.yaml
  validation_artifact_path = "<…>/system_validation.json",   # kind == "system-validation"
  conops_path              = "<…>/roadmap/conops.md",
)
```

> **`card_id` is the system NODE card, not the session card (hard contract, dogfood
> 2026-06-14).** The gate's first precondition is `_task_belongs_to_session`, which
> requires `card_type == "task"` AND `parent_session_id == SESSION_ID`. The session
> card (the `fizzy_card_id` in the session detail file) has `card_type == "session"`,
> so passing it **always** fails with `SESSION_MISMATCH` — it can never satisfy this
> check. The correct target is the single task card with `altitude == "system"`
> (`task_id "SYS"`, the schema-3 root node), discovered from the board, not from the
> session detail file. Confirm via `get_card_metadata` that the chosen card has
> `card_type == "task"`, `altitude == "system"`, and `parent_session_id == SESSION_ID`
> before calling. (`system_validation_complete` lives on this node, and the
> Finalization→Completed coverage gate reads it from the system node too.)

Read-back the true state with `get_card_metadata` (`system_validation_complete: true`).
A lost MCP response is resolved by reading metadata, never by re-emitting blindly (FM-8).

**Close algorithm (single normative ordering — gauntlet DD-2; every step
idempotent, re-entry starts at step 1):**

1. **Preflight** `[conductor]`: read `board_id` (projects.yaml) and `session_id`
   (session detail file). Resolve the **system node card_id** — the task card with
   `card_type == "task"` and `altitude == "system"` (`task_id "SYS"`) whose
   `parent_session_id == session_id` — from the board (NOT the `fizzy_card_id` in the
   session detail file, which is the session card and is the wrong target — see "The
   MCP close call" above). `get_card_metadata` on that node → verify `card_type ==
   task`, `parent_session_id` match, `altitude == system`, pipeline v5+ obligation; if
   `system_validation_complete` already true → skip to step 9. Verify clean
   worktree; verify `conops.md` and ledger exist; re-derive ConOps and
   compare hashes (OQ-3 RESOLVED: always re-derive at close entry) — story
   mismatch → refresh protocol (§8 above) before proceeding; compare ledger
   vs `drafted_baseline_hash` and surface any unexplained drift.
2. All verification obligations discharged; all task cards through review.
3. Evidence: for each active unjudged row, execute scenario → `record-evidence`
   (front matter incl. commit hash, clean worktree).
4. `assemble-digest`. `NOTHING_TO_DIGEST` + no failed rows → step 7.
   `NOTHING_TO_DIGEST` + failed rows present → remediation loop (step 6) —
   never emission (gauntlet CB-5).
5. Send parts (`telegram-send` via stdin, bounded retry) + `record-send` each;
   all sent → await replies; `parse-reply --update-file` per inbound message;
   apply confirmations; loop until batch closed. Bridge down → `cancel-batch`,
   terminal AskUserQuestion fallback for the whole batch (same grammar;
   detection = telegram-send nonzero exit/timeout — gauntlet US-6).
6. Any `fail`: if batch partially judged → `cancel-batch` remainder. Create
   remediation cards (MCP, payload per §4.7); after fixes: verify card
   resolution (MCP) → `reset-failed` per row → step 3.
7. `emit-system-validation` → `self-check` (ALWAYS, on the exact emitted file
   — including on re-entry; record the artifact's sha256).
8. Re-verify the artifact's sha256 unchanged (TOCTOU guard, gauntlet RC-1),
   then `mark_system_validation_complete` (explicit `board_id`). Transient
   MCP error → bounded retry; lost response → `get_card_metadata` to learn
   the true state (gauntlet FM-8).
9. `get_card_metadata` read-back confirms `system_validation_complete: true`
   → commit artifacts → proceed to Finalization advance. Post-close
   discovery of an erroneous validation: process-failure note + fizzy
   handoff item (write-once artifacts, OQ-4c).

**Re-entry routing (read these before re-running the close):**

- **Re-entry always restarts at step 1.** Every step is idempotent, so a crashed
  or interrupted close is recovered by re-running from the top — preflight will
  short-circuit to step 9 if `system_validation_complete` is already true (DD-2).
- **`NOTHING_TO_DIGEST` is a fork, not a finish (CB-5).** No unjudged active rows
  means one of two things: (a) **failed rows present** → go to the step 6
  remediation loop (fix, `reset-failed`, re-execute) — **never emit**; (b) no failed
  rows → all rows are judged-pass, proceed to step 7 emission. The conductor must
  branch on the presence of failed rows, not treat "nothing to digest" as "ready to
  close."
- **`self-check` runs before EVERY `mark_system_validation_complete`, on the exact
  emitted file (INV-5).** This holds on re-entries too — never skip the self-check
  because "it passed last time." The module re-verifies the artifact's sha256 at call
  time (RC-1); a file that changed between emission and the close call is rejected.

**Row state machine (R2 codex — normative; revised per gauntlet CB-1/CB-4):**

| # | From | Event | To | Notes |
|---|------|-------|----|-------|
| S1 | drafted (`result:null`, no evidence) | scenario executed (`record-evidence`) | evidence-attached | front matter binds row/story/conops hashes + commit |
| S2 | evidence-attached | `assemble-digest` | digested (batch d-N) | only `result:null` active rows; batch snapshots hashes |
| S3 | digested | `parse-reply` pass | judged-pass | exits only via S7 |
| S4 | digested | `parse-reply` fail | judged-fail | justification required; remediation cards |
| S5 | digested | `parse-reply` na | judged-na | row-level; sole-row N/A warned at parse, blocks close (TC-3.6) |
| S6 | judged-fail | card resolved + `reset-failed` | needs-reexecution | fail → history (append-only); evidence invalidated (renamed); distinct from drafted — scenario unchanged, evidence required fresh |
| S6b | needs-reexecution | scenario re-executed (`record-evidence`) | evidence-attached | fresh evidence, fresh hashes |
| S7 | ANY state | `supersede-row` (human-approved) | superseded | full snapshot retained; excluded from digests/parsing (INV-10); transactional replacement allowed |
| S8 | digested | `cancel-batch` | evidence-attached | returns to delta pool; audit on batch |

No other transitions exist. `judgment_history` is never rewritten.

#### Error-code playbook

When a close-leg command or the MCP gate rejects, look the code up here and take the
documented response — do not improvise. The first table is the **eight fizzy gate
reject classes** (six raised by `pipeline_mark_system_validation_complete` itself,
two at the Finalization advance); the second is the module's local codes.

**Gate rejects (from the served fizzy contract — six at the close call + two at advance):**

| Gate reject | Conductor response |
|---|---|
| `SESSION_MISMATCH` | **Almost always means the close targeted the session card instead of the system node** (`_task_belongs_to_session` requires `card_type == "task"` + `parent_session_id` match; the session card fails both). Retarget to the `altitude == "system"` task node (`task_id "SYS"`) per "The MCP close call". Only if already on the correct task node: re-run preflight; never re-point at another session's card. |
| `VV_NOT_OBLIGATED_AT_ALTITUDE` | Card isn't system-altitude: investigate triage/altitude drift; do not force. |
| `VALIDATION_KIND_MISMATCH` | Artifact `kind` wrong — regenerate via `emit-system-validation` (a hand-edited artifact is suspected). |
| `VALIDATION_ARTIFACTS_INCOMPLETE` | Run `self-check`; fix reported issues (the gate may group several failures under this code — rely on local self-check granularity, not the gate's message). |
| `VV_LEDGER_HAS_FAILURES` | Should be unreachable (close algorithm blocks on fail rows at step 4/6); if hit, the remediation loop was bypassed — process-failure note + remediate. |
| `VALIDATION_IS_RELABELED_VERIFICATION` | Rows re-point at verification fixtures — redraft scenarios from ConOps intent; check `test_targets` sets (local INV-11 should have caught it first). |
| `SYSTEM_VALIDATION_MISSING` (at advance) | `mark_system_validation_complete` was never called for a system node — run the close algorithm. |
| `UNVALIDATED_USER_STORY` (at advance) | A ConOps US id lacks a passing row — self-check coverage should have caught it; re-run close with the coverage fix. |

**Local module codes (gauntlet FM-5):**

| Local code | Meaning | Response |
|---|---|---|
| `LEDGER_BUSY` (exit 3) | Lock held >10s | Check `status`/live processes; retry once after 30s; stale lock → see filelock stale handling. |
| `LEDGER_CORRUPT` (exit 3) | Unparseable ledger | Corrupt bytes auto-copied aside; restore from git (commit cadence bounds loss); replay from quarantine + Telegram transcript if needed. |
| `NOTHING_TO_DIGEST` (exit 0) | No unjudged active rows | Step 4 routing: failed rows → remediation (step 6); else → emission (step 7). Never treat as "ready to close" without checking for fail rows (CB-5). |
| `SENDER_NOT_ALLOWLISTED` (exit 2) | Telegram reply from unknown sender | Security event logged; if Jason's real reply was discarded, fix the registry allowlist and re-feed the update file. |
| `ALLOWLIST_CONFIG_INVALID` (exit 2) | Registry missing/malformed | Fix the project telegram registry entry; telegram parsing is blocked until valid. |
| `STALE_DIGEST` / `STALE_ROW_HASH` / `STALE_CONOPS` (exit 2) | Reply references non-active batch or changed content | Re-digest; notify Jason which digest is current. |
| `REPROMPT_REQUIRED` (exit 2) | Invalid/partial reply blocks | Send the module's re-prompt text (quoted offending span) to the same channel. |
| `EVIDENCE_MISSING` / `EVIDENCE_MALFORMED` / `EVIDENCE_HASH_MISMATCH` / `EVIDENCE_STALE` (exit 2) | Evidence chain broken | Re-execute the scenario via `record-evidence` for the named row. |
| `REFRESH_DISALLOWED` (exit 2) | Supersession reason not in enum / approval missing | Get the human decision; use the allowed reason enum. |
| `ROW_OVER_BUDGET` (exit 2) | Row exceeds digest byte budget | Redraft the row tighter (drafting error). |
| `SELF_CHECK_FAILED` (exit 2) | Pre-close `self-check` rejected the emitted artifact | Read the issues; fix the row/evidence/coverage problem and re-emit; never call the MCP gate after a failed self-check (INV-5). |
| `ARTIFACT_SHA_MISMATCH` (exit 2) | Artifact changed between emission and close (TOCTOU) | Re-emit and re-run self-check on the fresh file before the MCP call (RC-1). |
| `ANTI_RELABELING_UNCHECKED` (warning) | No verification ledger supplied | Supply `--verification-ledger`; do not close on a warning when verification artifacts exist. |

**[GATE] TodoWrite (system-altitude sessions only): Mark the validation-leg close
complete — all rows judged-pass (or superseded), `emit-system-validation` +
`self-check` clean, `mark_system_validation_complete` called, and
`get_card_metadata` read-back confirms `system_validation_complete: true` — before the
Finalization advance.**

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

**Spike tasks** (`strategy: "spike"`):
- No automated tests committed (documentation, config-only, deferred/manual-only changes)
- Still verify the change works (often via an EXEMPT `verification_mode` + `exemption_reason`)
