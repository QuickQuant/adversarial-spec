> **FIRST ACTION upon entering this phase:** Create this TodoWrite immediately.
> Do NOT read further until the TodoWrite is active.
> Every `[GATE]` item must be marked completed before proceeding past it.

```
TodoWrite([
  {content: "Load finalized spec and gauntlet concerns", status: "in_progress", activeForm: "Loading finalized spec and gauntlet concerns"},
  {content: "Scope assessment — present to user", status: "pending", activeForm: "Assessing execution scope"},
  {content: "Load codebase architecture docs [GATE] — read primer.md + matched components before any exploration", status: "pending", activeForm: "Loading codebase architecture docs"},
  {content: "Load target architecture and build Architecture Spine (if exists)", status: "pending", activeForm: "Building architecture spine"},
  {content: "Decompose into tasks with gauntlet concern linkage", status: "pending", activeForm: "Decomposing spec into tasks"},
  {content: "Assign test strategies (test-first/test-after)", status: "pending", activeForm: "Assigning test strategies"},
  {content: "Over-decomposition guard check", status: "pending", activeForm: "Checking for over-decomposition"},
  {content: "Present plan to user for approval [GATE]", status: "pending", activeForm: "Presenting execution plan for approval"},
  {content: "Write execution plan to disk [GATE]", status: "pending", activeForm: "Writing execution plan to disk"},
  {content: "Verify plan file exists and update session state", status: "pending", activeForm: "Verifying plan persistence"},
  {content: "Generate fizzy-plan.json and load into pipeline [GATE]", status: "pending", activeForm: "Loading execution plan into Fizzy pipeline"},
  {content: "Add concern context comments to all cards [GATE]", status: "pending", activeForm: "Adding concern context comments to Fizzy cards"},
])
```

Mark each step `completed` as you finish it. Mark the current step `in_progress`.

---

## Execution Planning (Phase 7)

After the spec is finalized and the gauntlet has been run, offer to generate an execution plan.

**Skipping the gauntlet is highly discouraged.** Anything that needs an execution plan should also need the thoroughness of a gauntlet review — the gauntlet generates the concrete failure-mode concerns that become acceptance criteria in the execution plan. Without it, acceptance criteria are vague and implementation bugs slip through to code review (or worse, production). At minimum, run a limited gauntlet if context is running short.

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

### Step 2.5: Load Codebase Architecture (REQUIRED before decomposition)

**Do NOT decompose into tasks, launch Explore agents, or glob/grep the codebase until you have read the architecture docs.** The architecture docs tell you what components exist, what contracts matter, and what gotchas to avoid. Without them, you will invent file structures that conflict with the existing codebase.

**Load project architecture docs:**
```bash
# Check for architecture docs
[ -f .architecture/manifest.json ] && echo "exists" || echo "missing"
```

If `.architecture/manifest.json` exists:
1. Read `.architecture/INDEX.md` — for YOUR navigation only (component table, key files)
2. Read `.architecture/primer.md` — system summary, components, contracts, gotchas
3. Match the spec's scope against the INDEX component table:
   - Which components does the spec touch?
   - Which key files will need modification?
4. Read 2-4 matched component docs from `.architecture/structured/components/`
5. If the spec crosses component boundaries: read `.architecture/structured/flows.md`
6. If the spec touches known debt: read `.architecture/concerns.md`

If `.architecture/` does NOT exist:
- Warn the user: "No architecture docs found. Consider running `/mapcodebase` first."
- If proceeding without: use targeted file reads (not broad Explore agents) to understand the blast zone

**Then load target architecture (from Phase 4, if it exists):**
```bash
# Check for target architecture from Phase 4
ls .adversarial-spec/specs/*/target-architecture.md 2>/dev/null | head -1
```

If found, extract cross-cutting patterns and add an Architecture Spine section to the execution plan:

```markdown
## Architecture Spine
Cross-cutting patterns from the Target Architecture. All tasks must follow.

### [Pattern Name]
- **Pattern:** [one-line description]
- **Rule:** [what implementers must / must not do]
- **Reference:** Target Architecture §[N], Task W0-[N]
```

**Wave 0: Architecture Foundation**

Create tasks establishing shared infrastructure BEFORE feature tasks:
- One task per pattern in the Target Architecture
- Wave 0 tasks block all feature tasks depending on the pattern
- Typical: 4-8 tasks, S-M effort

Example:
```
Wave 0 Tasks
───────────────────────────────────────
W0-1  Establish data fetching pattern     S   Blocks: Tasks 3, 5, 8
W0-2  Implement auth middleware           M   Blocks: Tasks 4, 6, 7
W0-3  Set up shared error handling        S   Blocks: All feature tasks
W0-4  Create component boundary template  S   Blocks: Tasks 3, 4, 5
```

**If no target architecture exists:** Skip Architecture Spine and Wave 0. Proceed directly to Task Decomposition.

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

Wait for user approval before proceeding to Step 8.

**[GATE] TodoWrite: Mark "Present plan to user for approval" completed before proceeding to Step 8.**

---

### Step 8: Persist Execution Plan

**This step is REQUIRED before checkpoint or phase transition.** The plan must be on disk, not just in conversation output. A fresh agent (new conversation, Codex, or any other tool) cannot recover inline-only plans.

**Write the execution plan to:**
```
.adversarial-spec/specs/<slug>/execution-plan.md
```

Where `<slug>` is the context name slugified (same as the manifest directory).

**Use atomic write** (temp file + rename) to prevent corruption.

**Update session detail file:**
```json
{
  "execution_plan_path": ".adversarial-spec/specs/<slug>/execution-plan.md"
}
```

**Update pointer file** (`session-state.json`) to include the same `execution_plan_path` for consistency.

**Verify before proceeding:**
- File exists on disk
- File is non-empty
- Path recorded in session detail file

**[GATE] TodoWrite: Mark "Write execution plan to disk" completed before proceeding to Step 9.**

---

### Step 9: Load into Fizzy Pipeline

**This step connects the execution plan to the self-pickup loop.** Without it, cards are just text on disk — no agent can pick them up via `pipeline_do_next_task`.

**Generate `fizzy-plan.json`:**

Write a JSON file alongside the execution plan:
```
.adversarial-spec/specs/<slug>/fizzy-plan.json
```

The JSON must follow the pipeline schema:
```json
{
  "session_id": "<active_session_id from session-state.json>",
  "tasks": [
    {
      "task_id": "T1",
      "title": "Task title from execution plan",
      "description": "Full task description with acceptance criteria",
      "wave": 0,
      "effort": "M",
      "strategy": "test-first",
      "depends_on": [],
      "concern_refs": ["PARA-abc", "BURN-def"],
      "test_refs": ["TC-1.1", "TC-1.2"]
    },
    {
      "task_id": "T2",
      "title": "Second task",
      "description": "Description with acceptance criteria",
      "wave": 1,
      "effort": "S",
      "strategy": "test-after",
      "depends_on": ["T1"],
      "concern_refs": [],
      "test_refs": ["TC-2.1"]
    }
  ]
}
```

**Field mapping from execution plan:**
- `task_id`: Use the task numbering from the plan (T1, T2, ... or W0-1, W1-1, etc.)
- `title`: Task title
- `description`: Full description including acceptance criteria
- `wave`: Wave number from the plan
- `effort`: S / M / L
- `strategy`: test-first / test-after / skip
- `depends_on`: List of task_ids this task depends on (from dependency graph)
- `concern_refs`: List of gauntlet concern IDs linked to this task
- `test_refs`: List of test case IDs from `tests-spec.md` (e.g., `["TC-1.1", "TC-1.2"]`). Every task that touches behavior MUST reference ≥1 test. Tasks without test refs that modify behavior should be flagged for user review.

**Load into pipeline:**
```
pipeline_load(
  plan_path = ".adversarial-spec/specs/<slug>/fizzy-plan.json",
  session_id = "<active_session_id>",
  board_id = BOARD_ID
)
```

This creates cards in the **New Todo** lane with proper state blocks. `pipeline_do_next_task` can now walk these cards, check dependencies, and assign them to agents.

**Verify:**
```
pipeline_lane_state(pipeline="task", board_id=BOARD_ID)
```

Confirm cards appear in New Todo with correct count.

**[GATE] TodoWrite: Mark "Generate fizzy-plan.json and load into pipeline" completed before proceeding to Step 10.**

---

### Step 10: Add Concern Context Comments to Cards

**This step makes each card self-contained for human readers.** Without it, a person opening a single Fizzy card sees acceptance criteria but has no idea WHY the task exists, what production problem it prevents, or which gauntlet findings shaped the approach. They'd have to read the full spec to orient — defeating the purpose of card-level task breakdown.

**For each card created in Step 9, add a comment that includes:**

1. **Which concern(s) it addresses** — e.g., "CON-001: Gateway token refresh has no mutex"
2. **The problem in plain language** — what's broken, what happened (production incidents, data corruption, etc.)
3. **Why the fix takes this shape** — key gauntlet findings that constrained the approach (e.g., "gauntlet FM-2: can't cross-package import because gateway tsconfig restricts rootDir")
4. **How it connects to other cards** — dependencies, fallback relationships (e.g., "if this task's transition fails, T8's stuck detector catches it as the safe fallback")

**Format:**
```
**Context: CON-XXX — [short problem description]**

[1-3 paragraphs: what's broken, what the fix does, which gauntlet findings matter]
```

**Guidelines:**
- Write for a human who will read ONE card, not the full spec
- Include gauntlet concern IDs (e.g., RC-1, FM-2) so they can trace back to the gauntlet findings doc
- For prerequisite/audit tasks (no concern), explain what downstream tasks need from this one
- Keep each comment under 200 words — enough to orient, not a spec restatement

**Efficiency:** All card comments are independent — make all `add_comment` calls in parallel.

**[GATE] TodoWrite: Mark "Add concern context comments to cards" completed before proceeding to Phase 8 (Implementation).**

Only after concern context comments: proceed to Phase 8 (Implementation).
