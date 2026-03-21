## Implementation (Phase 8)

After the execution plan is generated, offer to proceed with implementation:

> "Execution plan generated with N tasks. Would you like to proceed with implementation?"

---

### CRITICAL: Setup Checklist (REQUIRED before writing ANY code)

**Do NOT write any code, read source files, or start implementation until ALL of these are done:**

```
Implementation Setup
───────────────────────────────────────
[ ] Trello cards created for all execution plan tasks
[ ] .handoff.md updated with agent assignments and wave plan
[ ] Review queue checked (reviews before new work)
[ ] First card moved to "In Progress" on Trello
[ ] TodoWrite created with setup steps + first wave tasks
```

**Why:** Without this gate, agents read the phase doc, understand the steps, and then skip them to start coding. The Trello cards and handoff file are how multi-agent coordination works — skipping them means Codex has no visibility into the work and can't pick up parallel tasks.

**After completing setup**, add the first wave's code tasks to TodoWrite and begin implementation.

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
2. **Track it** — Add the investigation as a Trello card or comment on the relevant card
3. **Targeted queries only** — Don't burn context with ad-hoc debugging
4. **Identify root cause** — Don't just poke values to make things "look right"
5. **Propose fix through process** — Update Trello card with the fix needed

**Anti-patterns to avoid:**
- Spending 50+ turns on ad-hoc debugging without tracking the work
- Manually setting values to make the UI "look right"
- Multiple restarts and retries without identifying root cause
- Switching into "fix it now" mode, abandoning the process
- Treating passing tests as proof that module boundaries are correct

**Correct pattern:**
```
User: "I want to see X working"

1. Is X in our current task list?
   - If yes: Continue with that task
   - If no: "This appears to be new work. Should I add it to our tasks?"

2. Add Trello comment on relevant card (or create new card):
   - Investigation scope
   - Acceptance criteria for the fix

3. Targeted investigation (2-3 queries max)

4. Report findings:
   "Root cause: [clear explanation]
   Fix needed: [specific change]
   Shall I proceed with this fix?"
```

---

### Trello Integration

**Trello is the task tracker.** Card state must always match actual work state.

#### Adding Implementation Tasks

For each task in the execution plan, create a Trello card on the appropriate wave list with:
- **Name:** Task title (e.g., `[W0-1] Define Pydantic schemas in schemas.py`)
- **Description:** Full task description with acceptance criteria from the execution plan
- **Labels:** Agent label (`claude` or `codex`) if pre-assigned

**Trello subagent rule:** Always use a subagent with a low-reasoning model (haiku for Claude, or equivalent lightweight model for Codex/Gemini) for Trello MCP operations. Trello API responses return large JSON payloads that bloat main context. The subagent performs the operation and returns only the relevant result (card ID, success/failure). This applies to:
- Creating cards
- Moving cards between lists
- Adding comments
- Bulk reads (fetching cards from multiple lists)
- Any MCP call that returns unbounded data

**Board pinning:** Always pass `boardId` explicitly to every Trello MCP call. Never use `set_active_board` — it changes global state and causes cross-project drift.

#### Card Flow During Implementation

```
Wave N list → In Progress → Review → Done
```

| Action | Trello Update |
|--------|---------------|
| Pick up a card | Move → "In Progress", add comment: `Starting: <agent-name>` |
| Commit | Add comment: `<hash> <summary>`, move → "Review" |
| Review LGTM | Move → "Done" |
| Review needs changes | Move → "In Progress", comment with issues |

---

### Multi-Agent Coordination (`.handoff.md`)

When two agents (Claude and Codex) work in parallel on the same branch, `.handoff.md` is the local sync file. Read the full protocol at `.coordination/PROTOCOL.md`.

#### Before Starting Any Work

1. **Read `.handoff.md`** — check what the other agent is working on and which files they own
2. **Check the Review Queue** — reviewing the other agent's commit takes priority over new work
3. **Pick a card with no file overlap** — never edit a file the other agent is actively working on

#### Handoff File Structure

```markdown
## Active Work
| Agent  | State   | Card  | Files        | Started    |
|--------|---------|-------|--------------|------------|
| claude | working | W1-1  | compiler.py  | 2026-03-15 |
| codex  | idle    | —     | —            | 2026-03-15 |

## Review Queue
- [ ] `abc1234` W1-1 (claude) — Implement DatabaseCompiler

## Recent
- [x] `def5678` W0-1 (codex) — Define schemas — LGTM
```

#### Rules

- **Only update your own row** in the Active Work table
- **Both agents** may append to Review Queue and Recent sections
- **Reviews before new work** — always check Review Queue first
- **File conflicts** — the Files column declares ownership; if there's overlap, pick a different card
- **After every commit**: update `.handoff.md` review queue, move Trello card → "Review", add comment with commit hash

#### Codex-Specific Notes

Codex works asynchronously and cannot read Trello directly. It relies on:
- `.handoff.md` for coordination state
- Git log for commit history
- The execution plan for task definitions
- Trello comments left by Claude for review feedback

When handing work to Codex:
- Ensure the card description in `.handoff.md` is self-contained (Codex can't follow Trello links)
- Include the specific acceptance criteria from the execution plan
- List the exact files Codex should touch

When reviewing Codex's work:
- Check `.handoff.md` agent-to-agent messages for Codex's review notes
- Codex posts detailed validation reports — read them before reviewing the diff
- Confirm the referenced commit is still the branch tip before reviewing

---

### Task Execution

Work through implementation tasks in dependency order:

1. Read `.handoff.md` — check for reviews, check file ownership
2. Pick up card: move to "In Progress" on Trello, update `.handoff.md`
3. Read the full task description from the execution plan
4. **Verify target files** — confirm every file you plan to create/modify is in the Architecture Spine
5. Follow the validation strategy (test-first or test-after)
6. Address all acceptance criteria, including those from gauntlet concerns
7. Run tests, lint, type-check
8. Commit with card reference: `[W0-1] Short description`
9. Move card to "Review", update `.handoff.md` review queue
10. Pick up next card (reviews first)

**After completing the last task in a wave:** Run `/checkpoint` before starting the next wave.

**High-risk tasks** (3+ concerns) use test-first validation:
- Write tests based on acceptance criteria before implementation
- Ensure tests cover failure modes from concerns
- Implementation must pass all tests

**Lower-risk tasks** use test-after validation:
- Implement the feature
- Write tests after
- Still address all acceptance criteria

### Parallelization

If the plan recommends multi-agent execution and multiple workstreams:

1. Review the workstream assignments
2. Consider parallel execution for independent streams
3. Coordinate at merge points via `.handoff.md`
4. Follow the recommended branch pattern
5. Use Trello labels to track agent ownership

The execution plan's `parallelization` section provides:
- `streams` — Independent workstreams with task IDs
- `merge_sequence` — Order and risk of merging streams
- `branch_pattern` — Recommended git branching strategy
