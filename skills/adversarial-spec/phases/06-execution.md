## Execution Planning (Phase 6)

After the spec is finalized (and optionally after gauntlet), offer to generate an execution plan:

> "Spec is finalized. Would you like me to generate an execution plan for implementation?"

**Update Tasks:** Use `TaskUpdate` to mark Phase 6 tasks as `in_progress`/`completed` as you progress. Set owner to `adv-spec:planner`.

---

### Step 1: Load Inputs

You (Claude) create the execution plan directly from the spec and gauntlet output. No external pipeline needed.

**Load the finalized spec:**
- Read the spec file from the session's `spec_path` or the most recent `[SPEC]...[/SPEC]` output

**Load gauntlet concerns (if gauntlet was run):**
```bash
# Find the most recent gauntlet concerns JSON
ls -t .adversarial-spec/specs/*/gauntlet-concerns-*.json 2>/dev/null | head -1
```

If found, read the JSON. Each concern has:
- `adversary`: Which adversary raised it
- `severity`: critical / high / medium / low
- `section_refs`: Which spec sections it targets
- `failure_mode`: What could go wrong
- `detection`: How to detect the failure
- `blast_radius`: Impact scope

---

### Step 2: Scope Assessment

Read through the spec and assess scope before decomposing:

**Guidelines:**
- **Small** (< 5 expected tasks): Single agent, sequential execution. No workstreams needed.
- **Medium** (5-15 tasks): Single agent with logical workstreams. Group by component/layer.
- **Large** (15+ tasks): Consider multi-agent execution. Identify independent workstreams that can run in parallel.

Present the assessment:
```
Scope Assessment
───────────────────────────────────────
Spec sections: N
Gauntlet concerns: M (X critical, Y high)
Estimated tasks: ~Z
Recommendation: [single-agent | single-agent with workstreams | multi-agent]

Proceed with task decomposition? [Y/n]
```

---

### Step 3: Task Decomposition

Create implementation tasks from the spec. For each major spec section or feature:

**Decomposition guidelines:**
- Target **1-4 hours of work per task**
- Each task should be independently testable
- Group related work (e.g., all error codes in one task, not 20 separate tasks)
- Include setup/infrastructure tasks (project scaffold, dependencies, config)

**For each task, specify:**
- **Title**: Short, action-oriented (e.g., "Implement order placement endpoint")
- **Description**: What to build, referencing specific spec sections
- **Spec references**: Which sections this task implements
- **Acceptance criteria**: Derived from spec requirements AND gauntlet concerns
- **Test strategy**: test-first or test-after (see Step 4)
- **Dependencies**: Which tasks must complete before this one
- **Effort estimate**: S (< 1hr), M (1-4hr), L (4-8hr)

**Link gauntlet concerns to tasks:**
For each concern in the gauntlet JSON, match its `section_refs` to your tasks. When a concern maps to a task:
- Add the concern's `failure_mode` as an acceptance criterion
- Add the concern's `detection` strategy as a test case
- Note the concern severity - critical/high concerns make the task higher risk

---

### Step 4: Test Strategy Assignment

Assign test-first or test-after to each task based on risk:

**Use test-first when:**
- Task has 3+ gauntlet concerns linked to it
- Any linked concern is critical or high severity
- Task involves security-sensitive logic
- Task implements complex business rules
- Task has external API integrations
- Task is large effort (L/XL) regardless of concern count — larger tasks have more surface area for bugs
- Acceptance criteria contain vague terms ("good performance", "fast", "better UX") — vagueness needs test anchoring

**Use test-after when:**
- Task is low-risk (0-2 low/medium concerns)
- Task is primarily CRUD or boilerplate
- Task is infrastructure/setup

**Skip tests (no strategy) when:**
- Task is pure documentation (README, docs, comments)
- Task is configuration-only (env vars, deploy config, CI setup)
- Task is a rename/move with no logic changes

Present as a table:
```
Test Strategy
───────────────────────────────────────
Task                          | Strategy    | Reason
Implement auth middleware     | test-first  | 3 concerns (1 critical)
Create DB schema             | test-after  | 0 concerns, standard CRUD
Implement order placement    | test-first  | 5 concerns (2 high)
Add error response codes     | test-after  | 1 low concern
```

---

### Step 5: Over-Decomposition Guard

Before presenting the plan, check for over-decomposition:

**Warning thresholds:**
- If task count > **2x the number of spec sections**, you may be over-decomposing
- If task count > **15 for a simple spec** (< 3 pages), consolidate
- If multiple tasks target the **same spec section** with S effort, merge them

**If threshold exceeded:**
```
⚠️ Over-Decomposition Warning
───────────────────────────────────────
Tasks: 28 (threshold: ~16 based on 8 spec sections)

Suggested consolidations:
• "Create User model" + "Add User validation" + "Add User serialization"
  → "Implement User model with validation"
• "Add GET /users" + "Add POST /users" + "Add DELETE /users"
  → "Implement /users CRUD endpoints"

Apply consolidations? [Y/n/customize]
```

---

### Step 6: Parallelization Analysis

For medium/large plans, identify independent workstreams:

**Guidelines:**
- Tasks with no dependency relationship can run in parallel
- Group into workstreams by component (backend, frontend, infra)
- Identify merge points where workstreams must synchronize
- Order merge sequence by risk (merge highest-risk stream first for early feedback)

**Present workstreams:**
```
Parallelization Plan
───────────────────────────────────────
Stream A (Backend): Tasks 1, 3, 5, 7
Stream B (Frontend): Tasks 2, 4, 6
Stream C (Infra): Tasks 8, 9

Merge points:
• After Task 5 + Task 9: Backend needs infra (medium risk)
• After Task 7 + Task 6: Integration testing (high risk)

Branch pattern: feature/<stream>-<task> → develop → main
```

---

### Step 7: Present Final Plan

Output the execution plan in this format:

```markdown
# Execution Plan: [Project Name]

## Summary
- Tasks: N (S: X, M: Y, L: Z)
- Workstreams: W
- Gauntlet concerns addressed: C of T
- Estimated effort: [range]

## Tasks

### [Workstream A]

#### Task 1: [Title]
- **Effort:** M
- **Strategy:** test-first
- **Spec refs:** Section 3.1, 3.2
- **Concerns:** PARA-abc (critical), BURN-def (high)
- **Acceptance criteria:**
  - [ ] [From spec: requirement]
  - [ ] [From concern PARA-abc: failure mode addressed]
- **Dependencies:** None
- **Test cases:**
  - [From concern detection strategy]

#### Task 2: [Title]
...

## Dependency Graph
Task 1 → Task 3 → Task 5
Task 2 → Task 4
Task 8 → Task 5 (merge point)

## Uncovered Concerns
[List any gauntlet concerns that don't map to tasks - these need attention]
```

**After presenting:**
> "Execution plan ready with N tasks across W workstreams. M gauntlet concerns linked.
> Any concerns not covered? Want to adjust task granularity or workstream assignments?"

Wait for user approval before proceeding to Phase 7 (Implementation).
