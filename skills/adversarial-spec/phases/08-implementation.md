## Implementation (Phase 8)

After the execution plan is generated, offer to proceed with implementation:

> "Execution plan generated with N tasks. Would you like to proceed with implementation?"

---

### CRITICAL: Process Discipline During Implementation

**DO NOT abandon the structured process when users ask about specific issues.**

When a user asks "can you check X" or "I want to see Y working":

1. **Check scope first** - Is this part of the current session's tasks?
2. **Use TodoWrite** - Add the investigation as a tracked task
3. **Targeted queries only** - Don't burn context with ad-hoc debugging
4. **Identify root cause** - Don't just poke values to make things "look right"
5. **Propose fix through process** - Update session state with the fix needed

**Anti-patterns to avoid:**
- ❌ Spending 50+ turns on ad-hoc debugging without TodoWrite
- ❌ Manually setting values to make the UI "look right"
- ❌ Multiple restarts and retries without identifying root cause
- ❌ Switching into "fix it now" mode, abandoning the process

**Correct pattern:**
```
User: "I want to see X working"

1. Is X in our current task list?
   - If yes: Continue with that task
   - If no: "This appears to be new work. Should I add it to our tasks?"

2. Add to TodoWrite:
   - [ ] Investigate X issue
   - [ ] Identify root cause
   - [ ] Propose fix

3. Targeted investigation (2-3 queries max)

4. Report findings:
   "Root cause: [clear explanation]
   Fix needed: [specific change]
   Shall I proceed with this fix?"
```

**Why this matters:** The prediction-prime session burned 50+ turns and significant context on ad-hoc debugging that should have been 3 targeted queries. The agent manually poked prices (which became stale immediately) instead of identifying the systemic issue (worker prioritization config). Follow the process.

---

**Update Tasks:** Use `TaskCreate` to add each implementation task from the execution plan. Include metadata for linking:

### Adding Implementation Tasks

For each task in the execution plan, use `TaskCreate` with:
- **subject:** Task title
- **description:** Full task description with acceptance criteria
- **activeForm:** "Implementing: {title}"
- **owner:** `adv-spec:impl:{workstream}` (e.g., `adv-spec:impl:backend`)
- **metadata:** Include `concern_ids`, `spec_refs`, `effort`, `risk_level`, `validation`
- **blockedBy:** Task IDs from execution plan's dependency graph

Example task creation:
```json
{
  "subject": "Implement schema: orders",
  "description": "Create database schema for orders table with fields...",
  "activeForm": "Implementing: orders schema",
  "owner": "adv-spec:impl:backend",
  "metadata": {
    "phase": "implementation",
    "concern_ids": ["PARA-abc123", "BURN-def456"],
    "spec_refs": ["Section 3.2"],
    "effort": "S",
    "risk_level": "medium",
    "validation": "test-after"
  }
}
```

Visual format (for display):
```
Phase 7: Implementation
- [S] Implement schema: orders (medium risk, 2 concerns)
- [S] Implement schema: order_queue (low risk)
- [M] Implement endpoint: orders:placeDma (high risk, 5 concerns)
- [ ] [M] Implement endpoint: orders:placeArbitrage (high risk, 3 concerns)
- [ ] [S] Implement scheduled function: syncOrderStatus (low risk)
```

### Task Execution

Work through implementation tasks in dependency order:

1. Mark task as `in_progress`
2. Read the full task description from the execution plan
3. Follow the validation strategy (test-first or test-after)
4. Address all acceptance criteria, including those from concerns
5. Run the test cases
6. Mark task as `completed`
7. Move to next task

**High-risk tasks** (3+ concerns) use test-first validation:
- Write tests based on test cases before implementation
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
3. Coordinate at merge points
4. Follow the recommended branch pattern

The execution plan's `parallelization` section provides:
- `streams` - Independent workstreams with task IDs
- `merge_sequence` - Order and risk of merging streams
- `branch_pattern` - Recommended git branching strategy
