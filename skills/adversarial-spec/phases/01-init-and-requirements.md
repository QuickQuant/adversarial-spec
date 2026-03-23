> **FIRST ACTION upon entering this phase:** Create this TodoWrite immediately.
> Do NOT read further until the TodoWrite is active.
> Every `[GATE]` item must be marked completed before proceeding past it.

```
TodoWrite([
  {content: "Determine document type and depth", status: "in_progress", activeForm: "Determining document type"},
  {content: "Identify starting point (file or concept)", status: "pending", activeForm: "Identifying starting point"},
  {content: "Offer interview mode (spec only)", status: "pending", activeForm: "Offering interview mode"},
  {content: "Conduct interview — cover all 8 topics", status: "pending", activeForm: "Conducting requirements interview"},
  {content: "Build RequirementsSummary (user_types, features, integrations, unknowns)", status: "pending", activeForm: "Building requirements summary"},
  {content: "User confirms requirements before roadmap [GATE]", status: "pending", activeForm: "Awaiting user requirements confirmation"},
])
```

Mark each step `completed` as you finish it. Mark the current step `in_progress`. For debug investigations, mark "Offer interview mode" and "Conduct interview" as `completed` immediately (not applicable).

---

## Task-Driven Workflow

**CRITICAL: At the start of every adversarial-spec session, immediately set up Tasks to track the entire workflow.** This ensures you never lose track of where you are in the process.

### Using MCP Tasks

Use these tools throughout the workflow:

| Tool | Purpose | Example |
|------|---------|---------|
| `TaskCreate` | Create a new task | `TaskCreate(subject="Run debate round 1", description="...")` |
| `TaskUpdate` | Update status, add blockers | `TaskUpdate(taskId="3", status="completed", owner="adv-spec:debate")` |
| `TaskList` | See tasks or list contexts | `TaskList(context_name="OMS Implementation")` |
| `TaskGet` | Get full task details | `TaskGet(taskId="3")` |

**TaskList parameters:**
- `session_id`: Filter by session_id in metadata
- `context_name`: Filter by context_name in metadata (preferred - human-readable)
- `status`: Filter by status (pending, in_progress, completed)
- `list_contexts`: If true, returns summary of all active contexts instead of task list

**IMPORTANT:** Use `TaskList(list_contexts=True)` at session start to detect active work streams. Then use `TaskList(context_name="...")` to see tasks for the selected context.

**Key fields (via TaskUpdate):**
- **`owner`** - Who's responsible: `adv-spec:orchestrator`, `adv-spec:debate`, `adv-spec:planner`, `adv-spec:impl:backend`
- **`addBlockedBy`** - Dependencies: task IDs that must complete first
- **`metadata`** - Context: `{"phase": "debate", "round": 1, "session_id": "...", "concern_ids": [...]}`

Tasks are stored globally but filtered by `session_id` in metadata.

### Initial Task Structure

When `/adversarial-spec` is invoked, create the following task structure using TaskCreate:

```
Phase 1: Requirements Gathering
- [ ] Determine document type (spec or debug)
- [ ] If spec: determine depth (product, technical, or full)
- [ ] Identify starting point (existing file or new concept)
- [ ] Offer interview mode (spec only; debug skips interview)
- [ ] Conduct interview (if selected, spec only)
  - [ ] Problem & Context (what problem, prior attempts, why now)
  - [ ] Users & Stakeholders (all user types, technical levels, concerns)
  - [ ] Functional Requirements (core journey, decision points, edge cases)
  - [ ] Technical Constraints (integrations, performance, scale, compliance)
  - [ ] UI/UX Considerations (experience, flows, density, platforms)
  - [ ] Tradeoffs & Priorities (what gets cut, speed/quality/cost)
  - [ ] Risks & Concerns (what could fail, assumptions, dependencies)
  - [ ] Success Criteria (metrics, minimum viable, exceeding expectations)
- [ ] For debug: Gather symptoms, evidence, initial hypotheses
- [ ] Build RequirementsSummary (user types, features, integrations, unknowns)
- [ ] User confirms requirements before roadmap

Phase 1.5: Roadmap Alignment (spec only, REQUIRED)
- [ ] Assess complexity (simple/medium/complex)
  - simple: score ≤4, no integrations, no unknowns → one-shot roadmap
  - medium: score 5-9 or 1 integration → one debate round on roadmap
  - complex: score ≥10 or 2+ integrations → roadmap folder, iterative discovery
- [ ] Draft initial roadmap
  - [ ] Define user stories (AS A... I WANT... SO THAT...)
  - [ ] Define natural language success criteria
  - [ ] Identify "Getting Started" workflow (for technical/full depth)
  - [ ] Define milestones with dependencies
- [ ] Validate roadmap schema
- [ ] Roadmap debate (if medium/complex)
  - [ ] Send roadmap to opponent models
  - [ ] Synthesize questions surfaced
  - [ ] Ask user clarifying questions
  - [ ] Revise roadmap based on answers
- [ ] User confirms roadmap (REQUIRED checkpoint)
- [ ] Persist roadmap artifacts (manifest.json + rendered views)
- [ ] Create milestone Tasks
- [ ] Create user story Tasks
- [ ] Note: Test cases expand from natural language → concrete during implementation

Phase 2: Adversarial Debate
- [ ] Check available API providers
- [ ] User selects opponent models
- [ ] Configure critique options (focus area, persona, context files - optional)
- [ ] Run debate rounds until consensus
  - [ ] Round N: Send spec to opponent models
  - [ ] Round N: Receive and display critiques
  - [ ] Round N: Claude provides independent critique
  - [ ] Round N: Check for lazy agreement (press if rounds 1-2)
  - [ ] Round N: Synthesize all feedback
  - [ ] Round N: Ask user for input on product decisions (if any critique requires it)
  - [ ] Round N: Revise spec with accepted changes
  - [ ] Round N: Check for consensus (all agree?)
  - (add round tasks dynamically as debate continues)
- [ ] Consensus reached - all participants agree

Phase 3: Gauntlet (if running adversarial stress test)
- [ ] Offer gauntlet review
- [ ] Select adversary personas (paranoid_security, burned_oncall, etc.)
- [ ] Gauntlet Phase 1: Run adversary attacks in parallel
- [ ] Gauntlet Phase 2: Frontier model evaluates each concern
- [ ] Gauntlet Phase 3: Process rebuttals from dismissed adversaries
- [ ] Gauntlet Phase 4: Generate summary report with accepted concerns
- [ ] Gauntlet Phase 5: Final Boss UX review (if selected)
- [ ] Integrate accepted concerns into spec
- [ ] Save gauntlet concerns JSON for execution planning

Phase 4: Finalization
- [ ] Quality check: Completeness (all sections substantive?)
- [ ] Quality check: Consistency (terminology, formatting uniform?)
- [ ] Quality check: Clarity (no ambiguous language?)
- [ ] Quality check: Actionability (stakeholders can act without questions?)
- [ ] Verify spec addresses ALL roadmap user stories
- [ ] Document-specific verification:
  - Spec (product depth): user stories, success metrics, scope boundaries
  - Spec (technical/full depth): APIs with schemas, data models, performance targets, Getting Started
  - Debug: evidence supports diagnosis, fix is proportional, verification plan exists
- [ ] Output final document to terminal
- [ ] Write to spec-output.md (or debug-output.md for debug type)
- [ ] Print debate summary (rounds, models, key refinements)
- [ ] Send to Telegram (if enabled)
- [ ] User review period: Accept / Request changes / Run another cycle
- [ ] Apply user-requested changes (if any)
- [ ] Run additional review cycle (if requested, loop to Phase 2)

Phase 5: Execution Planning
- [ ] Offer execution plan generation
- [ ] FR-1: Spec Intake (parse, detect type, extract elements)
- [ ] FR-2: Scope Assessment (single-agent vs multi-agent recommendation)
- [ ] FR-3: Task Plan Generation (create tasks, link gauntlet concerns)
- [ ] FR-4: Test Strategy Configuration (assign test-first/test-after)
- [ ] FR-5: Over-Decomposition Guard (check threshold, suggest consolidation)
  - If warning triggered: Confirm with user whether to proceed or consolidate
- [ ] FR-6: Parallelization Analysis (identify workstreams, merge points)
- [ ] Output execution plan (JSON/markdown/summary)
- [ ] Review plan with user

Phase 6: Implementation (if proceeding with code execution)
- [ ] Review execution plan and task dependencies
- [ ] Confirm workstream assignment (if parallel execution)
- [ ] Add implementation tasks from plan:
  - (each task from execution plan appears here with effort/risk)
  - Example: [S] Implement schema: orders (medium risk, 2 concerns)
  - Example: [M] Implement endpoint: orders:placeDma (high risk, 5 concerns)
- [ ] Execute tasks in dependency order
- [ ] For high-risk tasks: Write tests BEFORE implementation
- [ ] For all tasks: Verify acceptance criteria including concern-derived criteria
- [ ] Coordinate at merge points (if parallel workstreams)
- [ ] Final integration verification
```

**Task Management Rules:**
1. Mark each task `in_progress` when you start it (use `TaskUpdate` with `status: "in_progress"`)
2. Mark each task `completed` immediately when done - don't batch completions
3. Add sub-tasks dynamically as they emerge (e.g., each debate round gets its own tasks)
4. Remove tasks that don't apply (e.g., if user skips interview, mark as completed with note)
5. When execution planning generates implementation tasks, add them to Phase 7 with effort/risk
6. Only one task should be `in_progress` at a time per owner
7. Never skip phases without explicitly marking skipped tasks
8. If user makes a choice that eliminates a phase, mark those tasks as completed with "skipped" note

**Ownership Conventions:**
- `adv-spec:orchestrator` - Main agent running the skill (Phases 1-4)
- `adv-spec:debate` - Debate round coordination
- `adv-spec:gauntlet` - Gauntlet execution
- `adv-spec:planner` - Execution planning (Phase 5)
- `adv-spec:impl:{workstream}` - Implementation workstreams (e.g., `adv-spec:impl:backend`)

**Dependency Patterns:**
- **Phase-level:** Each phase's first task is `blockedBy` the previous phase's last task
- **Round-level:** Debate round N+1 is `blockedBy` round N
- **Parallel tasks:** Gauntlet adversary attacks can run in parallel (same `blockedBy`)
- **Implementation:** Use execution plan's dependency graph for `blockedBy`

**Metadata Fields:**

Use structured metadata to track tasks throughout the workflow. Different task types use different fields:

```json
// Milestone task (from roadmap)
{
  "schema_version": "1.0",
  "source": "roadmap",
  "task_type": "milestone",
  "session_id": "adv-spec-20260124-150000",
  "context_name": "OMS Implementation",
  "phase": "roadmap",
  "milestone_id": "M1",
  "roadmap_path": "roadmap/manifest.json",
  "test_summary": {"total": 5, "passing": 2, "failing": 1, "not_started": 2}
}

// User story task (from roadmap)
{
  "schema_version": "1.0",
  "source": "roadmap",
  "task_type": "user_story",
  "session_id": "adv-spec-20260124-150000",
  "context_name": "OMS Implementation",
  "phase": "roadmap",
  "milestone_id": "M1",
  "user_story_id": "US-1",
  "test_cases": ["TC-1.1", "TC-1.2"]
}

// Debate round task
{
  "schema_version": "1.0",
  "task_type": "debate",
  "session_id": "adv-spec-20260124-150000",
  "context_name": "OMS Implementation",
  "phase": "debate",
  "doc_type": "spec",
  "depth": "technical",
  "round": 3,
  "models": ["gpt-5.4", "gemini-3-pro"],
  "roadmap_milestone": "M1"
}

// Implementation task (from execution plan)
{
  "schema_version": "1.0",
  "task_type": "implementation",
  "session_id": "adv-spec-20260124-150000",
  "context_name": "OMS Implementation",
  "phase": "implementation",
  "milestone_id": "M1",
  "user_story_ids": ["US-1", "US-2"],
  "concern_ids": ["PARA-abc123"],
  "spec_refs": ["Section 3.2"],
  "workstream": "backend",
  "risk_level": "high",
  "effort": "M",
  "test_strategy": "test-first"
}
```

**Required fields for all tasks:**
- `schema_version`: Always "1.0"
- `task_type`: One of `milestone`, `user_story`, `test_case`, `debate`, `implementation`
- `session_id`: Format `adv-spec-YYYYMMDD-HHMMSS`
- `context_name`: Human-readable name for the work stream (e.g., "OMS Implementation")
- `phase`: One of `roadmap`, `debate`, `gauntlet`, `implementation`

**Roadmap-linked fields:**
- `milestone_id`: Links task to roadmap milestone (e.g., "M1")
- `user_story_id`: Links task to user story (e.g., "US-1")
- `roadmap_path`: Path to manifest.json
- `test_summary`: Progress tracking for milestones

**Handling Optional Phases:**
- **Interview**: If user declines, remove all 8 interview sub-tasks
- **Debug investigations**: Remove interview sub-tasks (debug doesn't use interview); Phase 5/6 may still apply if debug leads to implementation tasks
- **Gauntlet**: If user declines, remove entire Phase 3
- **Execution Planning**: If user declines, remove Phase 5
- **Implementation**: If user just wanted the plan, remove Phase 6

**Why this matters:** Long adversarial sessions can span many rounds and phases. Without explicit task tracking, it's easy to lose context about what phase you're in, what's been completed, and what comes next. MCP Tasks provide a persistent roadmap visible to both you and the user, with dependencies ensuring work happens in the right order. The task list persists across sessions - if the user returns later, they can see exactly where they left off. When the skill is used from another project, tasks are stored in that project's `.claude/tasks.json` and visible via `TaskList`.

## Setup

If you encounter provider issues or need to configure new API keys, see [SETUP.md](SETUP.md).

## Document Types

Ask the user which type of document they want to produce:

### Spec (Unified Specification)

**Two pathways:** `spec` (for creating new things) and `debug` (for fixing existing things).

The `spec` pathway has three depth levels that control required sections:

| Depth | Focus | When to Use |
|-------|-------|-------------|
| `product` | User value, stakeholders, success metrics | Product planning, stakeholder alignment |
| `technical` | Architecture, APIs, data models | Engineering implementation |
| `full` | All of the above | Complete journey from requirements to implementation |

**CLI usage:**
```bash
# Product-focused spec (stakeholders, user stories, metrics)
adversarial-spec critique --doc-type spec --depth product

# Technical spec (architecture, APIs, data models)
adversarial-spec critique --doc-type spec --depth technical

# Full spec (both product and technical)
adversarial-spec critique --doc-type spec --depth full
```

#### Spec Structure by Depth

**Product depth** (stakeholder-focused):
- Executive Summary
- Problem Statement / Opportunity
- Target Users / Personas
- User Stories / Use Cases
- Functional Requirements
- Non-Functional Requirements
- Success Metrics / KPIs
- Scope (In/Out)
- Dependencies
- Risks and Mitigations

**Technical depth** (engineering-focused):
- Overview / Context
- Goals and Non-Goals
- **Getting Started** (REQUIRED - bootstrap workflow)
- System Architecture
- Component Design
- API Design (endpoints, request/response schemas)
- Data Models / Database Schema
- Infrastructure Requirements
- Security Considerations
- Error Handling Strategy
- Performance Requirements / SLAs
- Observability (logging, metrics, alerting)
- Testing Strategy
- Deployment Strategy
- Migration Plan (if applicable)
- Open Questions / Future Considerations

**Full depth**: All sections from both product and technical.

#### Critique Criteria by Depth

**Product depth:**
1. Clear problem definition with evidence
2. Well-defined user personas with real pain points
3. User stories follow proper format (As a... I want... So that...)
4. Measurable success criteria
5. Explicit scope boundaries
6. Realistic risk assessment

**Technical depth:**
1. **Getting Started section exists** - Clear bootstrap workflow
2. Clear architectural decisions with rationale
3. Complete API contracts (not just endpoints, but full schemas)
4. Data model handles all identified use cases
5. Security threats identified and mitigated
6. Error scenarios enumerated with handling strategy
7. Performance targets are specific and measurable
8. Deployment is repeatable and reversible
9. No ambiguity an engineer would need to resolve

**Full depth:** All criteria from both.

**CRITICAL for Round 1:** Before technical critique, verify:
- All roadmap user stories have corresponding spec sections
- "Getting Started" section exists (technical/full depth)
- Success criteria are testable

### Debug Investigation

Structured investigation document for diagnosing and fixing bugs in existing systems. Uses adversarial debate to ensure evidence-based diagnosis and proportional fixes.

**When to use:**
- Bug reports with unclear root cause
- Performance issues requiring investigation
- Intermittent failures needing systematic diagnosis
- Any situation where you need to understand and fix existing code

**Philosophy: Evidence → Hypothesis → Fix**

The fix might be 1 line or 100 lines—what matters is that it's proportional to the actual problem and justified by evidence. A 1-line bug deserves a 1-line fix. A systemic issue may genuinely need architectural changes. The debate ensures we don't skip steps.

**Structure (Formal Schema):**
- **Symptoms**: User-visible behavior, timing (always/intermittent/under load), when it started, blast radius
- **Expected vs Actual Behavior**: Table comparing expected vs actual for each scenario
- **Evidence Gathered**: Logs with timestamps and interpretation, timings, error messages, reproduction steps
- **Hypotheses**: Ranked by (likelihood × ease of verification), with evidence for/against each
- **Diagnostic Plan**: Immediate checks (<5 min), targeted logging to add, tests to run
- **Root Cause**: File, line, issue description, why it happened, why initial hypotheses were wrong (if applicable)
- **Proposed Fix**: Changes required (table with file, change, lines), before/after code, justification for approach
- **Verification**: Steps to confirm fix, regression checks, log confirmation
- **Prevention**: Test case to add, documentation updates, similar bugs to check

**Critique Criteria:**
1. Evidence before hypothesis - no guessing without data
2. Simple explanations ruled out first - check basics before redesigning
3. Targeted diagnostics - each log answers a specific question
4. Proportional fix - justified by evidence, not by habit
5. Root cause identified - not just symptom masking
6. Verification plan - specific steps to confirm fix

**Anti-patterns flagged:**
- Premature Architecture - proposing abstractions before ruling out simple bugs
- Shotgun Debugging - logging everywhere without hypotheses
- Untested Assumptions - claiming cause without measurement
- Disproportionate Fix - complexity doesn't match evidence
- Scope Creep - "while we're here" improvements

**Security Warning:**
Debug investigations often contain sensitive data. Before submission:
- Scrub logs of PII, API keys, passwords, and credentials
- Remove internal hostnames, IP addresses, and network topology
- Redact customer data
- Follow your organization's data handling policies

Content is sent to LLM providers (OpenAI, Google, etc.). Do not include data that violates corporate policies or regulatory requirements.

**Context Window Guidance:**
Large log files may exceed model context limits. Best practices:
- Include targeted log snippets, not full files
- Focus on logs around the time of the error
- Summarize repetitive patterns rather than including all instances
- Use `grep` or similar to extract relevant lines before inclusion

**Example Debate Flow:**

Round 1 - Initial Investigation:
> User submits: "Orders page takes 60+ seconds to load, sometimes blank"
>
> Model A (codex/gpt-5.4) suggests: "We need a caching layer with TTL and circuit breaker pattern"
>
> Model B (claude) challenges: "Before designing infrastructure, what do the logs show? Have we measured where the 60 seconds is spent?"
>
> Model C (gemini) adds: "The blank page suggests a different issue than slowness. Are these the same bug or two bugs?"

Round 2 - Evidence Gathering:
> Investigation adds: Log shows ORDERS_CB_COMPLETE took 67234ms, breakdown shows AADriver call: 64 seconds
>
> Model A revises: "The 64 seconds is retry overhead. We should add a circuit breaker for AADriver."
>
> Model B challenges: "A full circuit breaker registry is overkill. A simple timestamp check would work. What's the minimal fix?"
>
> Model C adds: "Why is AADriver failing? Is it actually down, or is there a configuration issue?"

Round 3 - Proportional Fix:
> Investigation finds: urllib3 default retry policy causes 3 retries × 10+ seconds = 30+ seconds
>
> Consensus: Proportional fix - disable retries for AADriver (fail fast), add simple timestamp-based skip. ~10 lines total.

**Example invocation:**
```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models codex/gpt-5.4,gemini-cli/gemini-3-pro-preview --doc-type debug <<'SPEC_EOF'
# Debug Investigation: Orders Page 60s Load Time

## Symptoms
- Orders page takes 60+ seconds to load
- Sometimes blank entirely
- Started after recent deploy
- Affects all users

## Expected vs Actual Behavior
| Scenario | Expected | Actual |
|----------|----------|--------|
| Load orders page | <2s load time | 60+ seconds |
| Display orders list | Shows all orders | Sometimes blank |

## Evidence Gathered
### Logs
- [10:23:45] ORDERS_CB_COMPLETE took 67234ms
- [10:23:45] "Max retries exceeded connecting to AADriver"

### Timings
- Exchange API calls: 3 seconds total
- AADriver call: 64 seconds (timeout + retries)

## Hypotheses
| # | Hypothesis | Evidence For | Evidence Against | Verification | Effort |
|---|------------|--------------|------------------|--------------|--------|
| 1 | AADriver retry storm | Log shows 64s, retry message | None | Check retry config | 5 min |
| 2 | Database slow | General slowness | Logs show DB queries fast | Query timing | 15 min |
...
SPEC_EOF
```

## Process

### Step 0: Context Detection (Work Stream Selection)

**Before doing anything else**, detect if there's an active session in the current project. This prevents showing irrelevant contexts from other projects.

**PRIORITY ORDER:**
1. **Local session-state.json** (current project's session - ALWAYS check first)
2. **MCP Tasks** (cross-project view - ONLY in Brainquarters, detected by `projects.yaml`)

#### Step 0a: Check Local Session State (ALWAYS DO THIS FIRST)

```bash
# Check for local session in current project
if [ -f ".adversarial-spec/session-state.json" ]; then
  cat .adversarial-spec/session-state.json
fi
```

**If `.adversarial-spec/session-state.json` exists:**
1. Read the `context_name` and `current_phase` from it
2. If `active_session_id` field exists (v1.3) or `active_session` (legacy v1.1), load session file:
   - v1.3: `sessions/<active_session_id>.json`
   - v1.1 legacy: Check `active_session_file` or derive from `active_session`
3. **Validate integrity:** If session file is MISSING, clear the reference and show "no active session"
4. Present path context with journey (see SKILL.md for format):
   ```
   Found active session in this project:

     Context: Brainquarters Definition
     Phase: implementation
     Last checkpoint: checkpoint-20260128-migration.md

   Resume this session? Or describe something new.
   ```

4. **If user wants to resume:** Load session state and proceed to where they left off
5. **If user describes new work:** Ask for new context name, create new session

#### Step 0b: Check MCP Tasks (ONLY IN BRAINQUARTERS)

**IMPORTANT:** MCP Tasks is global and shows contexts from ALL projects. This is only useful when you're IN Brainquarters (the meta-project that manages other projects).

**Detect if in Brainquarters:**
```bash
# Brainquarters has projects.yaml at root - other projects don't
if [ -f "projects.yaml" ]; then
  echo "In Brainquarters - can show cross-project contexts"
fi
```

**If IN Brainquarters AND no local session:** Use `TaskList(list_contexts=True)` to see all project contexts:
```
Cross-project work streams (Brainquarters view):

  1. OMS Implementation (prediction-prime)
     - 3 tasks in progress

  2. Pricing Bug Fix (quicktrade)
     - 1 task in progress

Switch to one of these? Or start new work.
```

**If NOT in Brainquarters:** Do NOT show MCP Tasks contexts from other projects. Only use local session-state.json. If no local session exists, proceed directly to creating a new one.

#### Why This Scoping Matters

- MCP Tasks is **global** - shows contexts from ALL projects
- Local session-state.json is **project-specific** - always relevant
- Completed contexts disappear from MCP Tasks `list_contexts` (only shows active)
- Local session-state.json persists regardless of task status
- **Only Brainquarters** (detected by `projects.yaml`) should see cross-project contexts

**Session state file** (`.adversarial-spec/session-state.json`) structure (v1.3):

```json
{
  "schema_version": "1.3",
  "active_session_id": "adv-spec-202601281430-brainquarters-definition",
  "context_name": "Brainquarters Definition",
  "current_phase": "implementation",
  "current_step": "Migration protocol",
  "next_action": "Continue with next migration task",
  "do_not_ask": ["hierarchy approach", "verbosity level"],
  "updated_at": "ISO8601 UTC timestamp"
}
```

**Note:** Session file path is derived from ID: `sessions/<active_session_id>.json`
Legacy files with `active_session_file` field will still work (migration happens on read).

### Step 0.5: Initialize Task Tracking

Set up MCP Tasks for the workflow:

1. **Read current project's session state:** Check `.adversarial-spec/session-state.json` to get the `session_id` and `context_name`
2. **Check for existing session:** Use `TaskList(session_id="...")` to see only this context's tasks
3. **Create session tasks:** Use `TaskCreate` to create tasks for each phase (see "Task-Driven Workflow" above)
4. **Set metadata:** Include `session_id`, `context_name`, `phase`, and `doc_type` in each task's metadata
5. **Set dependencies:** Use `addBlockedBy` to establish the dependency chain
6. **Start first task:** Mark "Determine document type" as `in_progress` with owner `adv-spec:orchestrator`

**IMPORTANT:** Always include `context_name` in task metadata. This enables the context detection in Step 0.

### Step 1: Gather Input and Offer Interview Mode

**Update Tasks:** Use `TaskUpdate` to mark "Determine document type" as `completed`, then mark "Identify starting point" as `in_progress`.

Ask the user:

1. **Document type**: "spec" or "debug"
   - spec: Unified specification (replaces PRD/tech, use depth to control focus)
   - debug: Debug Investigation (evidence-based diagnosis)

2. **If spec, ask depth**: "product", "technical", or "full"
   - product: Business/stakeholder focus (user stories, metrics, scope)
   - technical: Engineering focus (architecture, APIs, data models)
   - full: Both product and technical sections

3. **Starting point**:
   - Path to existing file (e.g., `./docs/spec.md`, `~/projects/auth-spec.md`)
   - Or describe what to build (user provides concept, you draft the document)
   - For debug: describe symptoms, provide logs, or reference an existing investigation

4. **Interview mode** (optional, spec only):
   > "Would you like to start with an in-depth interview session? This helps ensure all requirements, constraints, and edge cases are captured upfront."

   Note: Debug investigations skip interview mode and go directly to evidence gathering.

### Step 1.5: Interview Mode (If Selected)

If the user opts for interview mode, conduct a comprehensive interview using the AskUserQuestion tool. This is NOT a quick Q&A; it's a thorough requirements gathering session.

**If an existing spec file was provided:**
- Read the file first
- Use it as the basis for probing questions
- Identify gaps, ambiguities, and unstated assumptions

**Interview Topics (cover ALL of these in depth):**

1. **Problem & Context**
   - What specific problem are we solving? What happens if we don't solve it?
   - Who experiences this pain most acutely? How do they currently cope?
   - What prior attempts have been made? Why did they fail or fall short?

2. **Users & Stakeholders**
   - Who are all the user types (not just primary)?
   - What are their technical sophistication levels?
   - What are their privacy/security concerns?
   - What devices/environments do they use?

3. **Functional Requirements**
   - Walk through the core user journey step by step
   - What happens at each decision point?
   - What are the error cases and edge cases?
   - What data needs to flow where?

4. **Technical Constraints**
   - What systems must this integrate with?
   - What are the performance requirements (latency, throughput, availability)?
   - What scale are we designing for (now and in 2 years)?
   - Are there regulatory or compliance requirements?

5. **UI/UX Considerations**
   - What is the desired user experience?
   - What are the critical user flows?
   - What information density is appropriate?
   - Mobile vs desktop priorities?

6. **Tradeoffs & Priorities**
   - If we can't have everything, what gets cut first?
   - Speed vs quality vs cost priorities?
   - Build vs buy decisions?
   - What are the non-negotiables?

7. **Risks & Concerns**
   - What keeps you up at night about this project?
   - What could cause this to fail?
   - What assumptions are we making that might be wrong?
   - What external dependencies are risky?

8. **Success Criteria**
   - How will we know this succeeded?
   - What metrics matter?
   - What's the minimum viable outcome?
   - What would "exceeding expectations" look like?

**Interview Guidelines:**
- Ask probing follow-up questions. Don't accept surface-level answers.
- Challenge assumptions: "You mentioned X. What if Y instead?"
- Look for contradictions between stated requirements
- Ask about things the user hasn't mentioned but should have
- Continue until you have enough detail to write a comprehensive spec
- Use multiple AskUserQuestion calls to cover all topics

**After interview completion:**
1. Synthesize all answers into a RequirementsSummary
2. Present RequirementsSummary to user for confirmation
3. Proceed to Step 1.6 (Roadmap Alignment)

**[GATE] TodoWrite: Mark "User confirms requirements before roadmap" completed before proceeding to Step 1.6 (Roadmap).**

