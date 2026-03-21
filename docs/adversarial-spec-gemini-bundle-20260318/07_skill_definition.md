<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: skills/adversarial-spec/SKILL.md (530 lines, 23836 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
---
name: adversarial-spec
description: Iteratively refine a product spec by debating with multiple LLMs (GPT, Gemini, Grok, etc.) until all models agree. Use when user wants to write or refine a specification document using adversarial development.
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# Adversarial Spec Development

Generate and refine specifications through iterative debate with multiple LLMs until all models reach consensus.

**Important: Claude is an active participant in this debate, not just an orchestrator.** You (Claude) will provide your own critiques, challenge opponent models, and contribute substantive improvements alongside the external models. Make this clear to the user throughout the process.

## FIRST ACTION - Read Local Session State

**BEFORE DOING ANYTHING ELSE**, check for an active session in the current project:

```bash
# ALWAYS read this first - it tells you what context you're in
cat .adversarial-spec/session-state.json 2>/dev/null
```

### If session-state.json exists:

Read ALL fields:
- `active_session_id`: The session ID (path is `sessions/<id>.json`)
- `context_name`: What work stream this is
- `current_phase`: Where we are (requirements, roadmap, debate, target-architecture, gauntlet, finalize, execution, implementation)
- `current_step`: Specific progress point
- `next_action`: What you should do/ask - FOLLOW THIS
- `do_not_ask`: Topics to avoid (ALWAYS a list) - RESPECT THIS
- `session_stack`: Recently active sessions (most recent first, optional)

**Validate integrity (Zombie Pointer Handling):**
If `active_session_id` is set, check if `sessions/<id>.json` exists:
```bash
[ -f ".adversarial-spec/sessions/<active_session_id>.json" ] && echo "exists" || echo "missing"
```

If the session file is MISSING (e.g., git branch switch):
- Clear `active_session_id` to null in your mental model
- Show warning: "Previous active session not found (branch switch or deletion)"
- Proceed as "no active session"

**If session file exists**, also read it for full context including `journey` array.

**Startup Context Intent Gate (REQUIRED):**

Before entering the phase workflow, detect whether the user may have switched workstreams.

Check these signals:
- `session_stack` has multiple entries (recent alternate context exists)
- `session_stack[0]` differs from `active_session_id` (pointer drift)
- Most recently updated file in `.adversarial-spec/sessions/` is not `active_session_id`
- Latest user messages suggest a topic different from `context_name`

If ANY signal exists, ask before proceeding:
```
Context Intent Check
───────────────────────────────────────
Active: [context_name] ([active_session_id])
Recent alt: [alt_context_name] ([alt_session_id])   # if available

Did we switch what we're working on?

[Continue active] [Switch to recent] [Show sessions]
```

Rules:
- Do NOT auto-switch silently.
- On **Continue active**: proceed with current pointer.
- On **Switch to recent**:
  1. Load target session file.
  2. Atomically update pointer file fields (`active_session_id`, `active_session_file`, `context_name`, `current_phase`, `current_step`, `next_action`, `updated_at`).
  3. Append journey event to target session: `{"time":"ISO8601","event":"Resumed via startup context intent check","type":"resume"}`.
  4. Continue from the switched session.
- On **Show sessions**: list up to 5 recent sessions by `updated_at`, then ask again.

**Check for Missing Manifest (Retroactive Generation):**

After validating the session exists, check if it has a corresponding manifest:
```bash
# Derive expected manifest path from context_name
CONTEXT_SLUG=$(echo "$CONTEXT_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')
MANIFEST_PATH=".adversarial-spec/specs/${CONTEXT_SLUG}/manifest.json"

[ -f "$MANIFEST_PATH" ] && echo "manifest exists" || echo "manifest missing"
```

If manifest is MISSING but session has roadmap-relevant data (milestones, user stories, test cases in session file or checkpoints):
```
Missing Manifest Detected
───────────────────────────────────────
Session: [context_name]
Status: Session exists but no manifest.json

This session predates roadmap artifacts. I can generate
a manifest from:
• Session file data (if milestones/stories exist)
• Checkpoint files (extract structured content)
• Tasks MCP (if tasks are linked)

[Generate manifest] [Skip - not needed] [Skip - will do manually]
```

**On "Generate manifest":**
1. Scan session file for `milestones`, `user_stories`, `test_cases`
2. Scan checkpoints for structured content (look for `##` headers, bullet lists)
3. Query Tasks MCP for tasks with matching `context_name`
4. Create `specs/<slug>/manifest.json` with extracted data
5. Log to journey: `{"time": "ISO8601", "event": "Generated manifest retroactively", "type": "maintenance"}`

**On "Skip":** Proceed without manifest. Some sessions (exploratory, debug-only) legitimately don't need one.

**Check for Architecture Manifest:**

After checking the spec manifest, also check for `.architecture/manifest.json`:
```bash
[ -f ".architecture/manifest.json" ] && echo "architecture mapping exists" || echo "architecture mapping missing"
```

If architecture manifest is MISSING:
```
Architecture Mapping Status
───────────────────────────────────────
Status: No .architecture/manifest.json found

Architecture docs help fresh agents understand the codebase
without re-reading source. Generate with /mapcodebase.

[Run /mapcodebase now] [Skip - not needed yet]
```

If architecture manifest EXISTS but may be stale:
```bash
# Check if git hash in manifest matches current HEAD
ARCH_HASH=$(python3 -c "import json; print(json.load(open('.architecture/manifest.json')).get('git_hash', ''))" 2>/dev/null)
CURRENT_HASH=$(git rev-parse --short HEAD 2>/dev/null)
[ "$ARCH_HASH" != "$CURRENT_HASH" ] && echo "architecture mapping may be stale (generated at $ARCH_HASH, now at $CURRENT_HASH)"
```

If stale, show advisory (not blocking):
```
Architecture Mapping Advisory
───────────────────────────────────────
Generated at: [arch_hash]
Current HEAD: [current_hash]
Consider running /mapcodebase --update
```

**On "Skip":** Proceed normally. Architecture mapping is advisory, not required.

**Load Architecture Context (REQUIRED when `.architecture/` exists):**

If `.architecture/manifest.json` exists (mapping is available), load targeted architecture docs into your context **now** — before any phase work begins. The LLM makes decisions throughout the session (synthesis, critique evaluation, accept/reject) that are all better when grounded in actual architecture.

```bash
# 1. Read INDEX.md to understand the component map (for YOUR navigation only)
cat .architecture/INDEX.md 2>/dev/null

# 2. ALWAYS read overview.md — the single most valuable context file
cat .architecture/overview.md 2>/dev/null

# 3. Select 2-4 component docs based on the session's blast zone
# Parse the spec/session requirements_summary for file paths and module names
# Match those against the INDEX component table
# Read matching component docs from .architecture/structured/components/
```

**Selection heuristic:**
- Parse the spec (or session `requirements_summary`) for file paths and module names
- Match those against the INDEX component table
- Read the matching component docs + `overview.md`
- If unsure which components are relevant, `overview.md` + `flows.md` covers ~80% of what any phase needs

**Cost:** ~400-600 lines of context. **Benefit:** Avoids context-blind debate/gauntlet rounds where models guess at codebase patterns.

**IMPORTANT:** `INDEX.md` is for YOUR navigation only. It contains links that opponent models cannot follow. Never pass `INDEX.md` as `--context` to `debate.py` — pass the substantive docs it references instead.

**Present Path Context (REQUIRED FORMAT):**
```
Path Context
───────────────────────────────────────
Session: [context_name]
Phase: [current_phase]
Origin: [branched_from or "Direct start"]

Journey (recent):
• [time] [event]
• [time] [event]

Next: [next_action]

[Continue] [Switch recent] [New session] [Archive this] [Branch]
```

### If no session-state.json exists:

Check if `.adversarial-spec/` directory exists:
- If NO: Offer to create workspace (first-run bootstrap)
- If YES but no state: Show "No active session" with options

**Present:**
```
No active session.

[Start new] [Resume recent] [Continue without tracking]
```

### Schema Migration (v1.1 → v1.3)

**CRITICAL:** If session-state.json exists but `schema_version` < 1.3, trigger migration:

1. **Detect legacy schema:**
   ```bash
   # Check schema version
   jq -r '.schema_version // "1.0"' .adversarial-spec/session-state.json
   ```

2. **If v1.1 or earlier:**
   - Inform user: "Found legacy session state (v1.1). Migrating to v1.3 format..."
   - Extract data from legacy session-state.json (completed_work, scaling_results, bugs_fixed, etc.)
   - Create proper session file: `sessions/<session-id>.json` with:
     - `journey` array (reconstruct from checkpoints if possible)
     - `requirements_summary.completed_work` (from legacy `completed_work` string)
     - `extended_state` (preserve rich fields like `gauntlet_results`, `dev_instance`, etc.)
   - Create `specs/<project>-roadmap/manifest.json` if roadmap data can be inferred from:
     - Tasks MCP (extract milestones from completed/pending tasks)
     - Trello board (if linked)
     - Checkpoint files (extract user stories, test cases)
   - Update session-state.json to v1.3 pointer format
   - Log to journey: `{"time": "ISO8601", "event": "Migrated from v1.1 to v1.3", "type": "migration"}`

3. **Migration checklist:**
   - [ ] Session file created with all legacy data preserved
   - [ ] manifest.json created (even if partial)
   - [ ] session-state.json updated to v1.3 pointer
   - [ ] Rich fields preserved in `extended_state`
   - [ ] Journey reconstructed from checkpoints

4. **After migration:** Proceed with normal v1.3 flow (show path context, offer options)

### Session State Rules (CRITICAL):

- If `do_not_ask` exists, DO NOT ask those questions
- If `next_action` exists, DO that action
- The session state tells you exactly what to do - follow it
- `do_not_ask` is ALWAYS a list - if you see a string, it's legacy format

---

## Process Discipline (All Phases)

**NEVER abandon the structured process.** When users ask tangential questions or "quick fixes":

1. **Check if it's in scope** - Is this part of the current session?
2. **Use TodoWrite** - Track ALL work, even small investigations
3. **Stay targeted** - Don't burn context with ad-hoc debugging (2-3 queries max)
4. **Identify root causes** - Don't apply band-aids that become stale immediately
5. **Propose through process** - Update session state, get approval

**Red flags you're abandoning the process:**
- 10+ turns without TodoWrite updates
- Manually setting values to make things "look right"
- Multiple restarts/retries without understanding why
- Saying "let me just quickly..." outside of task context

When in doubt: **Update session state** and **use TodoWrite**.

---

## Phase Router - Read ONLY What You Need

Based on `current_phase` from session state, read the appropriate file:

| Phase | File to Read |
|-------|--------------|
| No session / New work | `~/.claude/skills/adversarial-spec/phases/01-init-and-requirements.md` |
| requirements | `~/.claude/skills/adversarial-spec/phases/01-init-and-requirements.md` |
| roadmap | `~/.claude/skills/adversarial-spec/phases/02-roadmap.md` |
| debate | `~/.claude/skills/adversarial-spec/phases/03-debate.md` |
| target-architecture | `~/.claude/skills/adversarial-spec/phases/04-target-architecture.md` |
| gauntlet | `~/.claude/skills/adversarial-spec/phases/05-gauntlet.md` |
| finalize | `~/.claude/skills/adversarial-spec/phases/06-finalize.md` |
| execution | `~/.claude/skills/adversarial-spec/phases/07-execution.md` |
| implementation | `~/.claude/skills/adversarial-spec/phases/08-implementation.md` |
| complete | Ask user: "Start new work? Or continue with follow-up?" |

**Read the file for your current phase using the Read tool.** Don't load all phases at once.

### User Language → Phase Mapping

Users don't always use exact phase names. Map their intent:

| User says | Target phase |
|-----------|-------------|
| "critique," "review," "feedback," "get opinions" | **debate** |
| "architecture," "target architecture," "how should we build it," "patterns" | **target-architecture** |
| "adversarial," "stress test," "try to break it," "gauntlet," "attack" | **gauntlet** |
| "finalize," "lock it down," "we're done debating" | **finalize** |
| "execution plan," "implementation plan," "how to build it" | **execution** |
| "start building," "implement," "code it" | **implementation** |

**The debate and gauntlet are fundamentally different processes:**
- **Debate** = collaborative improvement via `debate.py critique` (round-based model feedback)
- **Gauntlet** = adversarial stress testing via adversary personas (PARA, BURN, LAZY, etc.) with per-adversary briefings and a multi-phase attack pipeline

Do NOT run `debate.py critique` when the user wants the gauntlet, and vice versa.

### CRITICAL: Phase Transition Gate

**On ANY phase transition (user request or natural progression), you MUST:**

1. **Read the TARGET phase file** from the Phase Router table above — not continue with the current one
2. **Follow the target phase's entry protocol** — each phase has specific startup steps
3. **Do not apply the previous phase's commands/tools to the new phase** — e.g., do not use `debate.py critique` for the gauntlet phase

**Why:** Process failure (Feb 2026) showed the LLM staying in "debate mode" when the user requested the gauntlet, attempting to run `debate.py critique` Round 4 instead of reading `05-gauntlet.md` and following its distinct protocol (Arm Adversaries, persona-based attacks, multi-phase evaluation pipeline).

### CRITICAL: Phase Transition Rules

**NEVER mark a session as `complete` without going through these gates:**

1. **finalize → execution**: After finalize, you MUST ask: "Spec is finalized. Would you like me to generate an execution plan for implementation?"
   - If yes: Read `phases/07-execution.md` and create the plan directly using its guidelines
   - If no: User explicitly declines - only THEN can you mark complete (with note: "execution skipped by user")

2. **execution → implementation/complete**: Create execution plans directly using guidelines in `phases/07-execution.md`. There is no `debate.py execution-plan` command - that pipeline was deprecated (Feb 2026, Option B+).
   - If the plan has 0 actionable tasks, WARN the user before proceeding

**Why this matters:** The failure report showed sessions jumping from gauntlet→complete, skipping execution entirely. This loses all the work linking gauntlet concerns to implementation tasks.

**If in Brainquarters** (detected by `projects.yaml` existing): Can also use `TaskList(list_contexts=True)` to see cross-project contexts.

### Phase Transition Protocol

**Every phase transition must update BOTH files atomically:**

1. **Detail file** (`sessions/<id>.json`) — update first:
   - Set `current_phase` to new phase
   - Set `current_step` to entry point description
   - Set `updated_at` to ISO 8601 timestamp
   - Append to `journey`: `{"time": "ISO8601", "event": "Phase transition: <old> → <new>", "type": "transition"}`
   - If `journey` array doesn't exist, create it

2. **Pointer file** (`session-state.json`) — update second:
   - Set `current_phase`, `current_step`, `next_action`, `updated_at`

**Detail file first, pointer second.** If interrupted between writes, the pointer stays behind (safe — it catches up on next transition). The reverse would leave a pointer ahead of a stale detail file.

**Artifact path fields** — set in the detail file at specific transitions:

| Transition | Field | Value |
|------------|-------|-------|
| roadmap → debate | `roadmap_path` | `"roadmap/manifest.json"` or `"inline"` |
| target-architecture → gauntlet | `target_architecture_path` | Path to architecture doc (e.g., `"specs/<slug>/target-architecture.md"`) |
| gauntlet → finalize | `gauntlet_concerns_path` | Path to saved concerns JSON (e.g., `".adversarial-spec/gauntlet-concerns.json"`) |
| finalize → execution | `spec_path` | Path to written spec (e.g., `"spec-output.md"`) |
| finalize → execution | `manifest_path` | Path to spec manifest if created (e.g., `"specs/<slug>/manifest.json"`) |
| execution → implementation | `execution_plan_path` | Path to written execution plan (e.g., `".adversarial-spec/specs/<slug>/execution-plan.md"`) |
| any → complete | `completed_at` | ISO 8601 timestamp |

**Non-artifact transitions** (debate → gauntlet, etc.) still MUST dual-write `current_phase` and `current_step` to both files, even though they don't produce artifact path fields. Every phase change syncs both files — no exceptions.

Both writes must use atomic pattern (temp file + rename).

**Backward compatibility:** If the detail file lacks `current_phase` (legacy sessions), add it — do not error. The schema is flexible.

---

## First-Run Bootstrap

If `.adversarial-spec/` directory doesn't exist, offer to create workspace:

```
No adversarial-spec workspace found.

Creating standard directories:
  .adversarial-spec/sessions/
  .adversarial-spec/checkpoints/
  .adversarial-spec/specs/
  .adversarial-spec/issues/
  .adversarial-spec/retrospectives/
  .adversarial-spec/.backup/

[Proceed] [Cancel]
```

On proceed:
1. Create all directories
2. Create `session-state.json` with `active_session_id: null`
3. Display "Workspace ready. Start new session?"

---

## Alignment Prompts (Hybrid Trigger)

At **checkpoint**, **phase transition**, or **startup**, offer alignment check:

```
Alignment Check
───────────────────────────────────────
Goal: [context.goal]
Phase: [current_phase]

Still aligned?
[Yes] [Refocus] [Skip]
```

**Actions:**
- **Yes:** Log `{"time": "ISO8601", "event": "Alignment confirmed", "type": "alignment"}` to journey
- **Refocus:** Prompt for new goal, update `context.goal`, log `alignment_refocused`
- **Skip:** Log `alignment_skipped`

---

## Pre-Checkpoint Checklist (REQUIRED)

**Before running `/checkpoint`, verify ALL of these.** The checkpoint command only handles pointer/session state — the surrounding process steps are your responsibility.

```
Pre-Checkpoint Verification
───────────────────────────────────────
[ ] Deliverables persisted — All debate output, execution plans,
    specs, and gauntlet concerns exist as FILES on disk
    (not just conversation/terminal output)
[ ] Alignment check offered — Alignment Prompts section above
[ ] Orphan detection run — File Discipline section below
[ ] TodoWrite current — Reflects actual work state

Proceed with /checkpoint? [Y/n]
```

**If any check fails:**
- Fix it before running `/checkpoint`
- Debate output → save to `.adversarial-spec-checkpoints/` (debate.py does this automatically for `critique` runs; for manual synthesis, write the file yourself)
- Execution plans → save to `.adversarial-spec/specs/<slug>/execution-plan.md`

**Why this matters:** The checkpoint command exits 0 even when deliverables are missing from disk. Context switches after checkpoint destroy conversation-only output permanently.

---

## Context Budget Gates (CRITICAL)

**Checkpoint-First Rule:** After writing a final spec version or completing a context-heavy phase, checkpoint IMMEDIATELY. Do not write reports, update MEMORY.md, or do additional work before checkpointing. Those can happen in the next session.

**Phase transition gates:**

| Transition | Gate |
|-----------|------|
| debate → gauntlet | If you wrote a spec draft in this session, **checkpoint before starting the gauntlet**. The gauntlet generates massive tool output and should start in a fresh context window. |
| gauntlet → finalize | If you ran a full gauntlet round (8+ adversaries) in this session, **checkpoint before synthesizing** the final spec version. |
| any → checkpoint | After writing the final deliverable for any phase, checkpoint is your NEXT action. Not reports. Not MEMORY.md. Not process failure analysis. Checkpoint first. |

**Heuristic:** If the session has (a) written a full spec draft AND (b) completed a full gauntlet round, you are in the danger zone. Checkpoint immediately. Do not do additional work.

---

## TaskOutput Anti-Patterns (CRITICAL)

These patterns waste context budget and have caused session death:

1. **NEVER Read the output file after a blocking TaskOutput call.** `TaskOutput(block=true)` already returns the full result into context. Reading the same file again doubles the token cost for zero benefit.

2. **NEVER re-launch the same command after a hook rejection.** If a Bash command is blocked by a hook, switch tools or fix the command immediately. Do not read the hook source to investigate why — hooks are a solved problem.

3. **NEVER retry the same command with incremental timeout increases.** Know the timeout requirements before launching: Codex calls need `timeout=900000` minimum. Use background mode for any long-running model call.

4. **After launching background tasks, check with `block=false` after ~45s** to catch quota/crash errors before committing to a full timeout wait.

---

## File Discipline & Orphan Detection

At checkpoint/resume, scan project root for potential orphan files.

**Allowlist (never flag):**
README.md, CLAUDE.md, AGENTS.md, CONTRIBUTING.md, CHANGELOG.md, CODE_OF_CONDUCT.md, SECURITY.md, GOVERNANCE.md, LICENSE, LICENSE.md, pyproject.toml, package.json, Makefile

**Detection heuristics:**
- `*.md` in root NOT in allowlist
- Contains date patterns (YYYYMMDD) in filename
- Contains "spec", "checkpoint", "session", "notes", "issues" in filename

**If orphans found:**
```
Found potential orphans:
• [filename]
  Suggested: .adversarial-spec/issues/

Move? [Y/n/skip all]
```

**NEVER auto-move.** Always confirm with user.

---

## Session ID Generation

Format: `adv-spec-YYYYMMDDHHMM-<slug>`

**Slug rules:**
1. Lowercase the context name
2. Replace non-alphanumeric with `-`
3. Collapse multiple `-` to single
4. Trim leading/trailing `-`
5. Truncate to 32 chars

Example: "Fix: User Login (Auth)" → `adv-spec-202601311430-fix-user-login-auth`

---

## Atomic Writes (CRITICAL)

**ALL JSON file writes must be atomic:**
1. Write to temp file (`.adversarial-spec/sessions/file.json.tmp`)
2. Rename to target (atomic on POSIX)

This prevents corruption if user interrupts (Ctrl+C).

---

## Reference Files (Load On-Demand)

Only read these when you need specific information:

- `~/.claude/skills/adversarial-spec/reference/document-types.md` - Spec types (product/technical/full/debug)
- `~/.claude/skills/adversarial-spec/reference/advanced-features.md` - Focus modes, personas, profiles
- `~/.claude/skills/adversarial-spec/reference/script-commands.md` - debate.py CLI reference
- `~/.claude/skills/adversarial-spec/reference/gauntlet-details.md` - Adversarial gauntlet details
- `~/.claude/skills/adversarial-spec/reference/convergence-and-telegram.md` - Convergence rules, Telegram


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: skills/adversarial-spec/phases/01-init-and-requirements.md (664 lines, 29004 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
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
  "models": ["gpt-5.3", "gemini-3-pro"],
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
> Model A (codex/gpt-5.3-codex) suggests: "We need a caching layer with TTL and circuit breaker pattern"
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
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models codex/gpt-5.3-codex,gemini-cli/gemini-3-pro-preview --doc-type debug <<'SPEC_EOF'
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
2. Proceed to Step 1.6 (Roadmap Alignment)



<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: skills/adversarial-spec/phases/02-roadmap.md (220 lines, 6543 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
### Step 1.6: Roadmap Alignment (Spec Only, REQUIRED)

**This step is MANDATORY for all spec documents.** It ensures user stories and testable milestones are defined BEFORE technical debate begins.

**Update Tasks:** Mark "Assess complexity" as `in_progress`.

#### 1. Build RequirementsSummary

From interview answers (or by asking clarifying questions if no interview), build:

```json
{
  "user_types": ["developer", "admin", "end-user"],
  "feature_groups": ["authentication", "data export", "reporting"],
  "external_integrations": ["Kalshi API", "Polymarket API"],
  "unknowns": ["rate limit behavior under load"],
  "bootstrap_steps": ["Install CLI", "Configure API keys", "Run first query"]
}
```

**Validation:**
- `user_types` must have at least 1 entry
- `feature_groups` must have at least 1 entry
- For technical/full depth: `bootstrap_steps` must be non-empty

#### 2. Assess Complexity

Calculate complexity score:
```
score = user_types + feature_groups + (2 × integrations) + unknowns
```

| Tier | Criteria | Roadmap Action |
|------|----------|----------------|
| **Simple** | score ≤ 4, no integrations, no unknowns | One-shot inline roadmap |
| **Medium** | score 5-9 or exactly 1 integration | One debate round on roadmap |
| **Complex** | score ≥ 10 or 2+ integrations or 3+ unknowns | Create `roadmap/` folder |

**User can override:** `--complexity-override simple|medium|complex`

#### 3. Draft Roadmap

Generate roadmap with user stories and milestones:

```markdown
## Roadmap: [Feature Name]

### Milestone 1: [Name]
**User Stories:**
- US-1: As a [persona], I want [action] so that [benefit]
- US-2: ...

**Success Criteria (Natural Language):**
- [ ] User can [do X]
- [ ] System responds with [Y]
- [ ] Error case [Z] is handled

**Test Cases (expand during implementation):**
- TC-1.1: [Description] (stage: nl)
- TC-1.2: [Description] (stage: nl)

**Dependencies:** None | M0

### Milestone 2: ...
```

**For technical/full depth, REQUIRE a "Getting Started" milestone:**
```markdown
### Milestone 0: Getting Started (Bootstrap)
**User Stories:**
- US-0: As a new user, I want to set up the tool so that I can start using it

**Success Criteria:**
- [ ] Setup takes < 5 minutes
- [ ] Clear error messages if prerequisites missing
- [ ] Can verify setup worked before proceeding
```

#### 4. Roadmap Debate (Medium/Complex Only)

For medium or complex tier, run one debate round on the roadmap itself:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models MODEL_LIST --doc-type spec --depth product <<'ROADMAP_EOF'
[roadmap content]
ROADMAP_EOF
```

Opponent models critique:
- Missing user stories
- Unclear success criteria
- Missing bootstrap workflow
- Dependency issues

Synthesize questions surfaced and ask user before finalizing.

#### 5. User Confirmation (REQUIRED)

**CRITICAL CHECKPOINT:** Before writing any files, present the roadmap to the user:

> "Here's the roadmap I've drafted:
>
> **Complexity:** [tier] (score: [N])
> **Milestones:** [list]
> **User Stories:** [count]
> **Getting Started:** [present/missing]
>
> Do you want to:
> 1. Accept this roadmap
> 2. Make changes
> 3. Run roadmap debate for more perspectives"

**Do NOT proceed to adversarial debate until user confirms roadmap.**

#### 6. Persist Roadmap Artifacts

**For simple tier:**
- Store roadmap inline in session file (`.adversarial-spec/sessions/<session>.json`)
- Include `user_stories` array with US-X entries

**For medium/complex tier:**
Write to `roadmap/` folder:
```
roadmap/
  manifest.json      # Source of truth (JSON)
  overview.md        # Rendered human-readable view
  _progress.json     # Test status tracking
  _progress.md       # Human-readable progress
```

**⚠️ VERIFICATION CHECKPOINT (REQUIRED):**

After persisting artifacts, verify they exist before proceeding:

```bash
# Verify artifacts were created
echo "=== Roadmap Artifact Verification ==="

if [ -f "roadmap/manifest.json" ]; then
  echo "✓ roadmap/manifest.json exists"
  US_COUNT=$(grep -o '"US-[0-9]*"' roadmap/manifest.json | wc -l)
  echo "  Found $US_COUNT user story references"
else
  echo "✗ roadmap/manifest.json NOT FOUND"
fi

# Check session file for simple tier
if ls .adversarial-spec/sessions/*.json 1>/dev/null 2>&1; then
  echo "✓ Session file exists"
fi

echo ""
echo "If artifacts are missing, create them NOW before proceeding to debate."
```

**Do NOT proceed to Phase 3 (Debate) until artifacts are verified.**

**Update session with roadmap path:**

After verification passes, sync both session files per the Phase Transition Protocol:
- Detail file (`sessions/<id>.json`): set `roadmap_path` to `"roadmap/manifest.json"` (medium/complex) or `"inline"` (simple tier)
- Append journey: `{"time": "ISO8601", "event": "Roadmap artifacts persisted", "type": "artifact"}`
- Update both files with `current_phase: "roadmap"`, `current_step: "Roadmap persisted and verified"`
- Use atomic writes for both files

#### 7. Create Roadmap Tasks

Create MCP Tasks for each milestone and user story:

```python
# Milestone task
TaskCreate(
    subject="[M1] Core Engine",
    description="...",
    metadata={
        "schema_version": "1.0",
        "source": "roadmap",
        "task_type": "milestone",
        "milestone_id": "M1",
        "roadmap_path": "roadmap/manifest.json"
    }
)

# User story task
TaskCreate(
    subject="[US-1] Bootstrap documentation",
    description="As a developer, I want to bootstrap docs...",
    metadata={
        "schema_version": "1.0",
        "source": "roadmap",
        "task_type": "user_story",
        "milestone_id": "M1",
        "user_story_id": "US-1",
        "test_cases": ["TC-1.1", "TC-1.2"]
    }
)
```

#### 8. Test Case Evolution

Test cases evolve through stages during the workflow:

| Stage | When | Format |
|-------|------|--------|
| `nl` (natural language) | Roadmap creation | "User can bootstrap documentation" |
| `acceptance` | After debate | "Given valid URL, when bootstrap runs, docs appear in index within 30s" |
| `concrete` | During implementation | `def test_bootstrap(): assert bootstrap(url).success` |

**Completeness rule:** Test case design is not complete until concrete tests cover all natural language descriptions. This may require multiple adversarial-spec rounds.

**Linking concrete tests:** Use `@spec:TC-X.Y` tags in test files:
```python
def test_bootstrap_from_url():
    """
    @spec:TC-1.1
    """
    result = bootstrap("https://example.com/docs")
    assert result.success
```



<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: skills/adversarial-spec/phases/03-debate.md (703 lines, 31157 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
**TodoWrite (REQUIRED):** At the start of the debate phase, create a TodoWrite list tracking all major steps. Update it as you complete each step. Example:

```
TodoWrite([
  {content: "Verify roadmap exists (gate)", status: "in_progress", activeForm: "Verifying roadmap exists"},
  {content: "Load roadmap user stories", status: "pending", activeForm: "Loading roadmap user stories"},
  {content: "Load or generate initial document", status: "pending", activeForm: "Loading initial document"},
  {content: "Information flow audit (technical/full)", status: "pending", activeForm: "Auditing information flows"},
  {content: "External API interface verification (technical/full)", status: "pending", activeForm: "Verifying external API interfaces"},
  {content: "Select opponent models", status: "pending", activeForm: "Selecting opponent models"},
  {content: "Assemble context files (technical/full)", status: "pending", activeForm: "Assembling context files"},
  {content: "Round 1: Requirements validation", status: "pending", activeForm: "Running Round 1 debate"},
  {content: "Context readiness audit (technical/full)", status: "pending", activeForm: "Running context readiness audit"},
  {content: "Round 2: Architecture & design", status: "pending", activeForm: "Running Round 2 debate"},
  ...additional rounds as needed...
])
```

Mark each step `completed` as you finish it. Mark the current step `in_progress`. Skip steps marked "technical/full" for product-depth specs.

---

### Step 1: Verify Roadmap Exists (GATE)

**BLOCKING CHECK:** Before ANY debate work, verify that roadmap artifacts from Phase 2 exist.

```bash
# Check for roadmap artifacts
ROADMAP_EXISTS=false

# Check 1: roadmap folder with manifest.json (medium/complex projects)
if [ -f "roadmap/manifest.json" ]; then
  echo "✓ Found roadmap/manifest.json"
  ROADMAP_EXISTS=true
fi

# Check 2: inline roadmap in session file (simple projects)
if [ -f ".adversarial-spec/session-state.json" ]; then
  if grep -q '"user_stories"' .adversarial-spec/sessions/*.json 2>/dev/null; then
    US_COUNT=$(cat .adversarial-spec/sessions/*.json | grep -o 'US-[0-9]*' | sort -u | wc -l)
    if [ "$US_COUNT" -gt 0 ]; then
      echo "✓ Found $US_COUNT user stories in session file"
      ROADMAP_EXISTS=true
    fi
  fi
fi

if [ "$ROADMAP_EXISTS" = false ]; then
  echo "✗ NO ROADMAP ARTIFACTS FOUND"
  echo ""
  echo "You must complete Phase 2 (Roadmap) before entering debate."
  echo "Run: Read ~/.claude/skills/adversarial-spec/phases/02-roadmap.md"
fi
```

**If no roadmap artifacts exist:**
> ⛔ **STOP.** Do not proceed to debate.
>
> The roadmap phase (02-roadmap.md) must be completed first, including:
> - User stories (US-0, US-1, etc.) defined and validated
> - Roadmap artifacts persisted (Step 6 of 02-roadmap.md)
> - User confirmation checkpoint passed
>
> **Action:** Return to `02-roadmap.md` and complete all steps including artifact persistence.

**Only proceed to Step 2 if roadmap verification passes.**

---

### Step 2: Load Roadmap User Stories (REQUIRED)

**CRITICAL:** Before generating any spec draft, load and use the user stories from Phase 1.5/2.

**Load roadmap artifacts:**
```bash
# Load from roadmap folder (medium/complex)
if [ -f "roadmap/manifest.json" ]; then
  cat roadmap/manifest.json
fi

# Or load from session file (simple)
cat .adversarial-spec/sessions/*.json | jq '.roadmap // .user_stories'
```

**Extract user stories:**
- Parse all `US-X` entries from the roadmap
- Note their associated milestones
- Identify the "Getting Started" user story (US-0) if present
- Collect success criteria for each story

**Create a User Story Reference Table** for use during spec generation:

```markdown
## Roadmap User Stories (from Phase 2)

| ID | Story | Milestone | Success Criteria |
|----|-------|-----------|------------------|
| US-0 | As a new user, I want to set up... | M0: Bootstrap | Setup < 5 min, clear errors |
| US-1 | As a developer, I want to... | M1: Core | Can query docs, < 500 tokens |
| US-2 | ... | M1: Core | ... |
```

**If no roadmap exists:** This is an error. Return to Phase 1.5/2 (02-roadmap.md) to create one. Do NOT proceed to generate a spec without user stories.

### Step 2.5: Load or Generate Initial Document

**If user provided a file path:**
- Read the file using the Read tool
- Validate it has content
- **Map existing sections to user stories** - identify which US-X each section addresses
- Flag any user stories without corresponding sections
- Use it as the starting document

**If generating from scratch (no existing file):**

Build the spec draft **anchored to roadmap user stories**:

1. **Review user stories first.** For each US-X, determine:
   - Which spec section(s) will address this story
   - What details are needed beyond what the roadmap specifies
   - What assumptions need to be validated

2. **Ask targeted clarifying questions** only for gaps NOT covered by the roadmap:
   - Don't ask "Who are the target users?" if US-X already defines them
   - Do ask implementation details: "For US-2 (data export), what formats are needed?"
   - Ask 2-4 focused questions. Reference specific user stories in your questions.

3. **Generate a complete document** that explicitly addresses each user story:
   - **For each US-X, create corresponding spec sections**
   - Use comments like `<!-- Addresses US-1, US-2 -->` to maintain traceability
   - Cover all sections even if some require assumptions
   - State assumptions explicitly so opponent models can challenge them
   - For product depth: Include placeholder metrics that the user can refine
   - For technical/full depth: Include concrete choices that can be debated

   **REQUIRED for technical/full depth:** The spec MUST include a "Getting Started" section addressing US-0 from the roadmap. This section must answer:
   - What does a new user need before they can use this? (prerequisites)
   - What's the step-by-step first-run experience? (setup workflow)
   - What happens if prerequisites aren't met? (error handling)
   - How long until a user can perform their first real task? (time to value)

   **If US-0 is missing from the roadmap**, return to Phase 2 (02-roadmap.md) to add it before generating the spec.

4. **Present the draft with user story mapping** before sending to opponent models:
   - Show the full document
   - Show which user stories each section addresses
   - Flag any user stories without clear coverage
   - Ask: "Does this capture your intent? Any user stories need better coverage?"
   - Incorporate user feedback before proceeding

Output format (whether loaded or generated):
```
[SPEC]
<document content here>
[/SPEC]
```

### Step 2.6: Information Flow Audit (For Technical/Full Depth Specs)

**CRITICAL**: Before finalizing any technical spec with architecture diagrams, audit every information flow.

Every arrow in an architecture diagram represents a mechanism decision. If you don't make that decision explicitly, you'll default to familiar patterns that may not fit the requirements.

**Example Failure:** A spec showed `Worker -> Exchange (order)` and `Exchange -> Worker (result)`. Everyone assumed "result" meant polling. Reality: the exchange provided real-time WebSocket push. The spec required 200ms latency; polling would have 5000ms. 62 adversary concerns were raised about error handling for the polling implementation - all of which would have been avoided with WebSocket.

**For each arrow/flow in your architecture:**

1. **What mechanism?** REST poll? WebSocket push? Webhook callback? Queue?

2. **What does the source system support?** Before assuming, check:
   - If Context7 MCP tools are available, query the external system's documentation
   - Look for: WebSocket channels, webhook endpoints, streaming APIs
   - Don't assume polling is the only option

3. **Does it meet latency requirements?** If a requirement says "<500ms", polling at 5s intervals won't work.

**Add an Information Flow table to technical specs:**

```markdown
## Information Flows

| Flow | Source | Destination | Mechanism | Latency | Source Capabilities | Justification |
|------|--------|-------------|-----------|---------|---------------------|---------------|
| Order submission | Worker | Exchange | REST POST | ~100ms | REST only | N/A |
| Fill notification | Exchange | Worker | WebSocket | <50ms | WebSocket USER_CHANNEL, REST poll | Real-time needed for 200ms requirement |
```

This prevents the gauntlet from flagging unspecified flows after you've already designed around the wrong mechanism.

### Step 2.7: External API Interface Verification (For Technical/Full Depth Specs)

**CRITICAL**: When defining TypeScript/Python interfaces for external API responses, DO NOT GUESS.

AI models pattern-match what they think an API "probably" looks like based on training data. This leads to specs with wrong field names, missing fields, and invented fields that don't exist.

**Example Failure (Real Bug):**
```typescript
// WHAT 3 FRONTIER MODELS AGREED ON (WRONG):
interface KalshiOrderResponse {
  filled_count: number;        // ❌ WRONG - API uses "fill_count"
  average_fill_price?: number; // ❌ DOESN'T EXIST in API
}
```

Three frontier models agreed on this interface. None checked. The implementation failed at runtime.

**Before defining ANY external API interface, check these sources IN ORDER:**

1. **SDK TYPE DEFINITIONS (Best Source)**
   If an official SDK exists, its `.d.ts` files are authoritative:
   ```bash
   # Find exact field names:
   grep -A 50 "export interface Order" node_modules/kalshi-typescript/dist/models/order.d.ts

   # Search for specific field:
   grep -rn "fill_count" node_modules/kalshi-typescript/dist/
   ```
   SDK types are auto-generated from OpenAPI specs - always correct, always up to date.

2. **LOCAL API DOCUMENTATION**
   Check `api_documentation/` or `api-reference/` folders for cached docs.

3. **CONTEXT7 (If SDK unavailable)**
   Use MCP tools: `mcp__context7__resolve-library-id` → `mcp__context7__query-docs`

4. **ASK THE USER**
   If no SDK and no docs found, ask for a documentation link. DO NOT proceed with guesses.

**In the spec, cite the source:**
```typescript
// Source: node_modules/kalshi-typescript/dist/models/order.d.ts
// Verified: 2026-01-27
interface KalshiOrder {
  fill_count: number;  // NOT "filled_count"
  // ... copy exact fields from SDK
}
```

**If no authoritative source exists:**
Mark as `UNVERIFIED` and flag for user:
```typescript
// ⚠️ UNVERIFIED - No SDK or docs found
// TODO: Verify against actual API before implementation
interface SomeApiResponse { ... }
```

### Step 3: Select Opponent Models

First, check which API keys are configured:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py providers
```

Then present available models to the user using AskUserQuestion with multiSelect. Build the options list based on which API keys are set:

**If OPENAI_API_KEY is set, include:**
- `gpt-5.3` - Frontier reasoning

**If ANTHROPIC_API_KEY is set, include:**
- `claude-sonnet-4-5-20250929` - Claude Sonnet 4.5, excellent reasoning
- `claude-opus-4-6` - Claude Opus 4.6, highest capability

**If GEMINI_API_KEY is set, include:**
- `gemini/gemini-3-pro` - Top LMArena score (1501 Elo)
- `gemini/gemini-3-flash` - Fast, pro-level quality

**If XAI_API_KEY is set, include:**
- `xai/grok-3` - Alternative perspective

**If MISTRAL_API_KEY is set, include:**
- `mistral/mistral-large` - European perspective

**If GROQ_API_KEY is set, include:**
- `groq/llama-3.3-70b-versatile` - Fast open-source

**If DEEPSEEK_API_KEY is set, include:**
- `deepseek/deepseek-chat` - Cost-effective

**If ZHIPUAI_API_KEY is set, include:**
- `zhipu/glm-4` - Chinese language model
- `zhipu/glm-4-plus` - Enhanced GLM model

**If Codex CLI is installed, include:**
- `codex/gpt-5.3-codex` - OpenAI Codex with extended reasoning

**If Gemini CLI is installed, include:**
- `gemini-cli/gemini-3-pro-preview` - Google Gemini 3 Pro
- `gemini-cli/gemini-3-flash-preview` - Google Gemini 3 Flash

Use AskUserQuestion like this:
```
question: "Which models should review this spec?"
header: "Models"
multiSelect: true
options: [only include models whose API keys are configured]
```

More models = more perspectives = stricter convergence.

### Step 3.5: Assemble Context Files (REQUIRED for technical/full depth)

**Before the first debate round**, assemble context files so opponent models can critique against the actual codebase, not hallucinated patterns.

**Use TodoWrite** to track each context source as you check it:

```
TodoWrite([
  {content: "Check architecture docs (.architecture/)", status: "in_progress", activeForm: "Checking architecture docs"},
  {content: "Check source issues (.adversarial-spec/issues/)", status: "pending", activeForm: "Checking source issues"},
  {content: "Check type definitions (API models, interfaces)", status: "pending", activeForm: "Checking type definitions"},
  {content: "Check existing routes/endpoints", status: "pending", activeForm: "Checking existing routes"},
  {content: "Validate context files contain substantive content", status: "pending", activeForm: "Validating context file content"},
  {content: "Build --context flags and store in session", status: "pending", activeForm: "Building context flags"},
])
```

**Build the --context flags:**

```bash
CONTEXT_FLAGS=""

# 1. Architecture docs (almost always relevant)
# WARNING: Do NOT pass INDEX.md as --context. INDEX.md is a navigation page
# containing links that opponent models cannot follow. It provides zero
# substantive content. Pass the files it REFERENCES instead:
if [ -d ".architecture" ]; then
  # ALWAYS include overview.md — the single most valuable context file
  [ -f ".architecture/overview.md" ] && CONTEXT_FLAGS="$CONTEXT_FLAGS --context .architecture/overview.md"

  # Include component docs relevant to the spec's blast zone (2-4 files)
  # Match spec file paths/module names against .architecture/structured/components/
  # e.g., --context .architecture/structured/components/data-service.md

  # For broad specs, flows.md covers data paths across the whole system
  [ -f ".architecture/structured/flows.md" ] && CONTEXT_FLAGS="$CONTEXT_FLAGS --context .architecture/structured/flows.md"
fi

# 2. Source issues/requirements that motivated the spec
# Check session extended_state for issues_file, or scan issues dir
for f in .adversarial-spec/issues/*.md; do
  [ -f "$f" ] && CONTEXT_FLAGS="$CONTEXT_FLAGS --context $f"
done

# 3. Key type definitions (limit to 3-5 most relevant files)
# e.g., --context src/types.ts --context src/api_models.py
```

**Context File Validation (REQUIRED before passing --context):**

Before passing any file via `--context`, verify it contains substantive content:

1. **Does the file contain actual architecture/code information?** Navigation pages, tables of contents, and link-only documents are useless to opponent models — they can't follow links.
2. **Can the recipient model use the content without following links?** If the file is mostly `[link text](url)` references, pass the linked files instead.
3. **Is the file relevant to the spec being critiqued?** Don't pass every architecture doc — select files that cover the spec's blast zone.

**Do NOT pass as --context:**
- `INDEX.md` or any file that's primarily navigation/links
- Files over 500 lines without trimming to relevant sections
- Files unrelated to the spec's scope

**Store assembled context list in session state** (`extended_state.context_files`) for reuse across rounds.

**Do NOT run `debate.py critique` without --context for technical/full specs that reference an existing codebase.** Product-depth specs about new greenfield projects may not need context.

### Step 4: Send to Opponent Models for Critique

**CRITICAL: Always pass the COMPLETE spec document from disk. NEVER summarize, condense, or rewrite it from memory.**

The spec file on disk is the source of truth. Opponent models must see the exact same document the user approved. Any "optimization" that shortens the input invalidates the entire round.

**Before EVERY debate round (use TodoWrite to track — do NOT skip):**

```
TodoWrite([
  {content: "Write spec to disk as spec-draft-vN.md", status: "in_progress", activeForm: "Writing spec to disk"},
  {content: "Verify spec file line count (wc -l)", status: "pending", activeForm: "Verifying spec file"},
  {content: "Pipe spec from disk to debate.py (cat file | debate.py)", status: "pending", activeForm: "Running debate round N"},
])
```

1. Write the current spec to `.adversarial-spec/specs/<slug>/spec-draft-vN.md`
2. Verify the file exists and has expected content: `wc -l .adversarial-spec/specs/<slug>/spec-draft-vN.md`
3. Use `cat <file> | debate.py ...` — the file IS the input, never a heredoc

```bash
# CORRECT: pipe from disk (structurally safe)
cat .adversarial-spec/specs/<slug>/spec-draft-vN.md | \
  python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --models MODEL_LIST --doc-type spec --depth DEPTH \
  --round N \
  $CONTEXT_FLAGS
```

**NEVER do this:**
```bash
# WRONG: heredoc from memory — LLM will condense the spec
python3 debate.py critique --models ... <<'SPEC_EOF'
<LLM rewrites spec from memory here — WILL lose sections>
SPEC_EOF
```

Replace:
- `<slug>`: spec directory name (from session)
- `vN`: current version number (v1 for Round 1, v2 for Round 2, etc.)
- `MODEL_LIST`: comma-separated models from user selection
- `DEPTH`: `product`, `technical`, or `full` (based on spec depth from Phase 1)
- `N`: current round number
- `$CONTEXT_FLAGS`: assembled in Step 3.5 (empty for product-depth greenfield specs)

For debug investigations, use `--doc-type debug` (no --depth needed).

The script calls all models in parallel and returns each model's critique or `[AGREE]`. It logs the input line count and SHA256 hash — verify these match the file you piped.

### Step 5: Review, Critique, and Iterate

**Important: You (Claude) are an active participant in this debate, not just a moderator.** After receiving opponent model responses, you must:

1. **Provide your own independent critique** of the current spec
2. **Evaluate opponent critiques** for validity
3. **Synthesize all feedback** (yours + opponent models) into revisions
4. **Explain your reasoning** to the user

Display your active participation clearly:
```
--- Round N ---
Opponent Models:
- [Model A]: <agreed | critiqued: summary>
- [Model B]: <agreed | critiqued: summary>

Claude's Critique:
<Your own independent analysis of the spec. What did you find that the opponent models missed? What do you agree/disagree with?>

Synthesis:
- Accepted from Model A: <what>
- Accepted from Model B: <what>
- Added by Claude: <your contributions>
- Rejected: <what and why>
```

**Debate Round Focus Progression:**

Each round has a specific focus. This prevents deep-diving into implementation before requirements are validated.

| Round | Focus | What to Review |
|-------|-------|----------------|
| **Round 1** | REQUIREMENTS VALIDATION | User story coverage, Getting Started section, success criteria clarity |
| **Round 2** | ARCHITECTURE & DESIGN | Component design, data models, API contracts, system boundaries |
| **Round 3** | IMPLEMENTATION DETAILS | Algorithms, performance targets, security, error handling |
| **Round 4+** | REFINEMENT | Edge cases, polish, final consistency checks |

**Important:** Do not accept critiques about Round 3 topics (algorithms, performance) in Round 1 - defer them to the appropriate round. Requirements must be validated before implementation details are debated.

---

**Round 1 Roadmap Validation (REQUIRED for Spec documents):**

In Round 1, BEFORE reviewing technical details, **confirm** the spec addresses all roadmap user stories. Since the spec was generated anchored to user stories (Step 2), this is a verification step, not a discovery step.

**Use TodoWrite** to track each validation item — mark completed or flag blocked:

1. **Confirm User Story Coverage:** Verify the spec addresses ALL user stories from the roadmap.
   - The spec should already have `<!-- Addresses US-X -->` markers from Step 2.5
   - For each `US-X` in roadmap, confirm the corresponding spec section exists and is substantive
   - **If a user story lacks coverage:** This is a Step 2.5 error. Return to Step 2.5 to address it before continuing debate.

2. **Confirm Getting Started Exists:** For technical/full depth:
   - A "Getting Started" or "Bootstrap" section should already exist (addressing US-0)
   - The bootstrap workflow from the roadmap should be documented
   - New users can understand how to set up the system
   - **If missing:** Return to Step 2.5 to add it

3. **Confirm Success Criteria Are Testable:** For each success criterion:
   - Is it specific enough to write a test for?
   - If not, flag for clarification (this is expected - criteria often need refinement)

4. **USER CHECKPOINT (Round 1 only):**
   After Round 1 synthesis, present findings to the user:
   > "Round 1 confirmed user story coverage:
   > - [list US-X → section mappings]
   >
   > Technical concerns raised:
   > - [list concerns from opponent models and Claude]
   >
   > Success criteria needing clarification:
   > - [list if any]
   >
   > Before Round 2, do any of these conflict with your priorities?"

   Do NOT proceed to Round 2 until user confirms direction.

---

**Context Readiness Audit (GATE — between Round 1 and Round 2, REQUIRED for technical/full depth):**

> **STOP.** Do NOT proceed to Round 2 without completing this audit.
> This is a GATE, not advisory. The audit produces the `ContextInventoryV1` that:
> - Builds the `--context` flags for Round 2+ debate invocations
> - Feeds the Arm Adversaries step before the gauntlet (see 04-gauntlet.md)
> - Prevents the failure pattern where models critique architecture without seeing the actual codebase
>
> **If this audit was skipped** (e.g., resumed session), run it NOW before proceeding.

After Round 1 validates requirements and before Round 2 debates architecture, audit what codebase context is available to inform the remaining debate and the eventual gauntlet.

**Why here:** Round 1 is about user value (no codebase context needed). Round 2 is about architecture (codebase context critical). Gaps discovered now have time to be addressed — tasks can complete while debate proceeds.

**Use TodoWrite** to track each context source check from the table below — mark each as completed with its status (AVAILABLE/PARTIAL/NOT_AVAILABLE/NOT_APPLICABLE).

**Process:**

1. **Identify the blast zone.** Parse the spec for file paths, module names, table names, function names, and external services. These are the files/modules the spec will likely modify.

2. **Check context sources against this checklist:**

   | Context Source | Check Method | Who Benefits |
   |---------------|-------------|--------------|
   | Architecture docs | `[ -f .architecture/manifest.json ]` | ALL (base context) |
   | Schema/type definitions | Grep for table/interface names in blast zone | PEDA, COMP |
   | Test coverage | Check for pytest-cov config or recent coverage report | PEDA, COMP |
   | Dependency inventory | Read pyproject.toml / package.json | LAZY, PREV, PARA |
   | Git recent changes | `git log --oneline -10 -- <blast zone files>` | COMP, PREV |
   | Build/test status | `uv run pytest --tb=short` (or equivalent) | COMP |
   | Monitoring/metrics | Check for alerting config, dashboards, SLIs | BURN |
   | Error handling patterns | Grep for try/except, circuit breaker, retry in blast zone | BURN |
   | Auth/authz patterns | Grep for auth, permission, token in blast zone | PARA |
   | External API docs | Check for SDK, cached docs, Context7 availability | AUDT, FLOW |
   | Legacy/archive dirs | `find . -type d -name "_legacy" -o -name "deprecated"` | PREV |
   | Design rationale (ADRs) | Check for decision docs, spec history | ASSH |
   | Existing similar features | Grep for feature keywords across codebase | PREV, LAZY |

3. **Classify each source:** `AVAILABLE`, `PARTIAL`, `NOT_AVAILABLE`, or `NOT_APPLICABLE`.

4. **For PARTIAL sources, determine if gap is actionable:**
   - Can we generate a coverage report now? → Suggest task
   - Can we fetch API docs via Context7? → Suggest task
   - Is this a fundamental gap the spec SHOULD address? → Note for Round 2+

5. **Present to user:**

   ```
   Context Readiness Audit
   ═══════════════════════════════════════
   Blast zone: 5 files, 3 modules

   ✓ AVAILABLE (6)
     Architecture docs, schema definitions, type definitions,
     dependency inventory, git history, build status

   ⚠ GAPS (2)
     Test coverage — no pytest-cov configured
       → Can generate now (spawns 30s task)
     External API docs — spec references FooAPI, no local docs
       → Can fetch via Context7 (spawns task)

   ✗ NOT AVAILABLE (1)
     Monitoring data — no alerting configured
       → This is a design gap. Round 3 should address it.

   ─ NOT APPLICABLE (1)
     Incident reports — not relevant for CLI tool

   [Generate available gaps] [Proceed without] [Choose which]
   ```

6. **Cache inventory in session state** as `ContextInventoryV1`:

   ```json
   {
     "schema_version": "1.0",
     "audit_timestamp": "ISO-8601",
     "git_hash": "short hash",
     "blast_zone": ["file1.py", "file2.py"],
     "sources": {
       "source_id": {
         "status": "available|partial|not_available|not_applicable",
         "path": "string or null",
         "summary": "one-line description",
         "est_tokens": 1200,
         "actionable": false,
         "task_id": null
       }
     },
     "total_available_tokens": 8500,
     "gaps_noted": ["description of design gaps for later rounds"]
   }
   ```

   This inventory is reused by:
   - **Context-addition-protocol** — debate round appendices draw from it instead of re-extracting
   - **Arm Adversaries** — gauntlet briefings are assembled from it (see 04-gauntlet.md)

   **Staleness rule:** If `git rev-parse --short HEAD` differs from `git_hash` in inventory, re-extract only the sources whose files were modified.

**After the audit, update --context flags for Round 2+:**

Build expanded context from the inventory's AVAILABLE sources:
```bash
CONTEXT_FLAGS=""
for source in inventory.sources where status == "available" and path != null:
  CONTEXT_FLAGS="$CONTEXT_FLAGS --context $source.path"
```

Update `extended_state.context_files` in session state with the new list. Use these flags for ALL subsequent `debate.py critique` invocations.

---

**Round 2 Architecture & Design (For Spec documents):**

**PRE-CHECK:** Verify the Context Readiness Audit was completed. If `extended_state.context_inventory` is missing from the session state, STOP and run the audit above before proceeding. Round 2 without codebase context produces hallucinated critiques.

After Round 1 confirms requirements, Round 2 focuses on system design:

1. **Component Design:** Are system components well-defined with clear responsibilities?
2. **Data Models:** Do the data models support all user stories?
3. **API Contracts:** Are APIs complete with request/response schemas and error codes?
4. **System Boundaries:** Are integration points with external systems clear?

**Defer implementation details** (algorithms, caching strategies, etc.) to Round 3.

**Round 3 Implementation Details (For Spec documents):**

After architecture is validated, Round 3 focuses on implementation:

1. **Algorithms:** Are the proposed algorithms appropriate for the scale?
2. **Performance:** Are targets specific and measurable?
3. **Security:** Are threats identified with mitigations?
4. **Error Handling:** Are failure modes enumerated with recovery strategies?

**Round 4+ Refinement:**

Final rounds focus on polish:
- Edge cases and boundary conditions
- Consistency across sections
- Clarity of language
- Final verification against user stories

---

**Handling Early Agreement (Anti-Laziness Check):**

If any model says `[AGREE]` within the first 2 rounds, be skeptical. Press the model by running another critique round with explicit instructions:

```bash
cat .adversarial-spec/specs/<slug>/spec-draft-vN.md | \
  python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --models MODEL_NAME --doc-type TYPE --press
```

The `--press` flag instructs the model to:
- Confirm it read the ENTIRE document
- List at least 3 specific sections it reviewed
- Explain WHY it agrees (what makes the spec complete)
- Identify ANY remaining concerns, however minor

If the model truly agrees after being pressed, output to the user:
```
Model X confirms agreement after verification:
- Sections reviewed: [list]
- Reason for agreement: [explanation]
- Minor concerns noted: [if any]
```

If the model was being lazy and now has critiques, continue the debate normally.

**If ALL models (including you) agree:**
- Proceed to Step 5.5 (Gauntlet Review - Optional)

**If ANY participant (model or you) has critiques:**
1. List every distinct issue raised across all participants
2. For each issue, determine if it is valid (addresses a real gap) or subjective (style preference)
3. **If a critique raises a question that requires user input, ask the user before revising.** Examples:
   - "Model X suggests adding rate limiting. What are your expected traffic patterns?"
   - "I noticed the auth mechanism is unspecified. Do you have a preference (OAuth, API keys, etc.)?"
   - Do not guess on product decisions. Ask.
4. Address all valid issues in your revision
5. If you disagree with a critique, explain why in your response
6. Output the revised document incorporating all accepted feedback
7. **Write the revised spec to disk** as `spec-draft-v{N+1}.md` (where N is current round):
   ```bash
   # Write revised spec to disk BEFORE next round
   # This is the source of truth for the next debate.py invocation
   ```
   Verify the file was written: `wc -l .adversarial-spec/specs/<slug>/spec-draft-v{N+1}.md`
8. Go back to Step 4, piping the NEW file from disk: `cat spec-draft-v{N+1}.md | debate.py ...`

**Handling conflicting critiques:**
- If models suggest contradictory changes, evaluate each on merit
- If the choice is a product decision (not purely technical), ask the user which approach they prefer
- Choose the approach that best serves the document's audience
- Note the tradeoff in your response

---

### Phase Transition: debate → gauntlet

When consensus is reached and user opts for gauntlet, sync both session files per the Phase Transition Protocol (SKILL.md):

1. **Detail file** (`sessions/<id>.json`): set `current_phase: "gauntlet"`, `current_step: "Consensus reached, running gauntlet"`, append journey entry
2. **Pointer file** (`session-state.json`): set `current_phase: "gauntlet"`, `current_step`, `next_action`, `updated_at`

If user declines gauntlet and proceeds directly to finalize, set `current_phase: "finalize"` instead.



<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: skills/adversarial-spec/phases/04-target-architecture.md (196 lines, 6051 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
## Target Architecture (Phase 4)

After spec debate converges, define the shared architecture patterns before the gauntlet.

**Prerequisites:**
- Spec debate (Phase 3) has converged
- Roadmap with user stories exists

**Inputs:**
- Converged spec draft
- Roadmap / user stories
- `.architecture/manifest.json` patterns[] (optional — from `/mapcodebase`)
- Framework documentation (via Context7 / web)
- gemini-bundle findings (optional)

---

### Step 1: Scale Check (Gate)

Not every project needs formal architecture. Assess:

```
Scale Assessment
───────────────────────────────────────
Spec scope: [user story count]
Codebase: [greenfield / existing with N files]
Stack complexity: [single runtime / multi-service]

Recommended: [Full architecture | Lightweight | Skip]
```

**Skip criteria:** <3 user stories AND single-file scope, or pure library with no app layer.

If skip: log Decision Journal entry with `decision: "skip"`, transition directly to gauntlet.

---

### Step 2: Assess Starting Point

**Greenfield (no code exists):**
Architecture drafted from scratch (Steps 3-5).

**Brownfield (existing codebase):**
1. Load `.architecture/overview.md` and relevant component docs
2. List all `warning`/`error` patterns from `manifest.json` `patterns[]`
3. Load gemini-bundle findings if available
4. Focus: "what new patterns does this spec need?" + "which existing patterns need adjustment?"

---

### Step 3: Categorize the Application

Classify along dimensions relevant to the project type. The taxonomy adapts to the category — don't force web-app dimensions onto a CLI tool.

**Schema (flexible dimensions array):**
```json
{
  "architecture_taxonomy": {
    "category": "web-app | cli | api-service | library | data-pipeline | mobile | other",
    "dimensions": [
      {
        "name": "rendering",
        "value": "hybrid-ssr-csr",
        "rationale": "SSR for initial load, CSR for interactive editors",
        "source_refs": ["Next.js App Router docs", "spec §7"]
      }
    ],
    "confirmed_by_user": true,
    "confirmed_at": "ISO8601"
  }
}
```

**Typical dimensions by category:**
- **Web apps:** Rendering, Navigation, Auth, Data freshness, State management, Multi-page sharing
- **CLIs:** Execution model, State, Concurrency, I/O
- **APIs:** Transport, Auth, Data layer, Scaling
- **Libraries:** API surface, Error handling, Extensibility

Present classification to user for confirmation before proceeding.

---

### Step 4: Research Best Practices

For each dimension:
1. Look up established pattern for the chosen stack
2. Minimum 2 sources (official docs + community/template)
3. Use Context7 if available for exact API signatures
4. Note where the framework provides built-in solutions

---

### Step 5: Draft Target Architecture Document

Produce `specs/<slug>/target-architecture.md`:

```markdown
### [Pattern Name]
**Decision:** [pattern chosen]
**Rationale:** [why, with source references]
**Alternative considered:** [what else was evaluated]
**Implementation sketch:** [code snippets or file structure]
**Applies to:** [which user stories / features]
```

If `patterns[]` available from mapcodebase: each `warning`/`error` pattern gets a corresponding section explaining how it's addressed.

---

### Step 6: Debate the Architecture

Run architecture-specific critique rounds:

```bash
cat specs/<slug>/target-architecture.md | \
  uv run python ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --models MODEL_LIST --doc-type architecture --round N \
  --context specs/<slug>/spec-draft-latest.md \
  $CONTEXT_FLAGS
```

**If debate reveals spec gaps:** Revise spec → run spec debate round → resume architecture debate.

Continue until convergence.

---

### Step 7: Dry-Run Verification

Walk the most complex user flow through the architecture step-by-step:
- Which component renders / handles the request?
- What data is fetched, by whom, via what mechanism?
- What state is created, where, what happens on navigation?
- What happens on error?

**The dry-run is the proof the architecture is complete.**

If gaps found: revise architecture, re-debate the change.

---

### Step 8: Record Decisions

Log all architecture decisions to the Decision Journal in the session detail file.

**Decision Journal schema:**
```json
{
  "decision_journal": [
    {
      "entry_id": "dj-YYYYMMDD-<6 char random>",
      "time": "ISO8601",
      "phase": "target-architecture",
      "topic": "auth-pattern",
      "decision": "adopt",
      "choice": "Middleware-based auth with cached fallback",
      "rationale": "Eliminates per-page auth calls",
      "alternatives_considered": ["Per-page getUser()", "React cache() only"],
      "revisit_trigger": "If middleware latency exceeds 50ms",
      "reverses_entry_id": null
    }
  ]
}
```

**Decision types:** `adopt`, `reject`, `defer`, `skip`, `reversed`

**Rules:**
- Append-only — never edit or delete entries
- `reversed` entries must set `reverses_entry_id` pointing to the original
- Required fields: `entry_id`, `time`, `phase`, `topic`, `decision`, `choice`, `rationale`
- Optional fields: `alternatives_considered`, `revisit_trigger`, `reverses_entry_id`

---

### Outputs
- `specs/<slug>/target-architecture.md`
- Decision Journal entries in session detail file
- Architecture taxonomy in session detail file

### Completion Criteria
- All taxonomy dimensions decided with rationale
- At least one dry-run completed without gaps
- Architecture debated through at least one converged round
- Decision Journal records categorization + each pattern decision

### Phase Transition

**Detail file** (`sessions/<id>.json`):
- Set `current_phase: "gauntlet"`
- Set `target_architecture_path` to the architecture doc path
- Append journey: `{"time": "ISO8601", "event": "Phase transition: target-architecture → gauntlet", "type": "transition"}`

**Pointer file** (`session-state.json`):
- Update `current_phase`, `current_step`, `next_action`, `updated_at`


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: skills/adversarial-spec/phases/05-gauntlet.md (375 lines, 19998 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
### Step 5.5: Gauntlet Review (Optional)

After consensus is reached but before finalization, offer the adversarial gauntlet:

> "All models have agreed on the spec. Would you like to run the adversarial gauntlet for additional stress testing? This puts the spec through attack by specialized personas (security, oncall, QA, etc.)."

**If user accepts gauntlet:**

1. Ask which adversary personas to use (or use 'all'):
   ```bash
   python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet-adversaries
   ```

   **Adversary Quick Reference (exact CLI names):**

   | Prefix | CLI Name | Role |
   |--------|----------|------|
   | COMP | `existing_system_compatibility` | Codebase compatibility (pre-gauntlet) |
   | PARA | `paranoid_security` | Security threats |
   | BURN | `burned_oncall` | Operational failure modes |
   | LAZY | `lazy_developer` | Unnecessary complexity |
   | PEDA | `pedantic_nitpicker` | Edge cases |
   | ASSH | `asshole_loner` | Design flaws |
   | PREV | `prior_art_scout` | Existing code reuse |
   | AUDT | `assumption_auditor` | Unverified assumptions |
   | FLOW | `information_flow_auditor` | Architecture flow gaps |
   | ARCH | `architect` | Code structure, data flow, component boundaries |
   | UXAR | `ux_architect` | User story coherence (final boss) |

   **NEVER invent adversary names.** If `gauntlet-adversaries` crashes, read its output carefully — it prints valid names before any traceback. Use those exact names.

2. **Select gauntlet attack models.** Present available models using AskUserQuestion with multiSelect:

   ```
   question: "Which models should run adversary attacks? (cheap/free models recommended — they find holes, frontier model evaluates)"
   header: "Attack models"
   multiSelect: true
   options: [build from available providers, prioritize free/cheap models]
   ```

   **Recommended lineup (if available):**
   - `codex/gpt-5.4` — GPT-5.4 via Codex CLI (free, token-efficient)
   - `gemini-cli/gemini-3-pro-preview` — Gemini 3 Pro (free via CLI)
   - `claude-cli/claude-sonnet-4-6` — Claude Sonnet 4.6 (free via CLI)

   These become `--gauntlet-attack-models` (comma-separated). The frontier evaluation model is selected automatically.

3. **Understand the cost model BEFORE launching.**

   The gauntlet pipeline makes many LLM calls. Know the math before choosing flags:

   ```
   Phase 1 (attacks):     N adversaries × M attack models = N×M calls
   Phase 2 (synthesis):   1 call (first eval model)
   Phase 3 (filtering):   1 call (cheap model)
   Phase 3.5 (clustering): 1 call (cheap model)
   Phase 4 (evaluation):  ceil(remaining_concerns / 15) batches × E eval models
                           EACH batch re-sends the full spec
   ```

   **Example (real numbers from a username spec gauntlet):**
   8 adversaries × 2 attack models = 16 Phase 1 calls → 331 raw concerns.
   After filtering/dedup: ~300 concerns remain.
   Phase 4: ceil(300/15) = 20 batches × 2 eval models = **40 eval calls**.
   Total: 16 + 2 + 2 + 40 = **60 calls**, each with ~11K token spec as input.

   **Phase 1 is where external models add value** (diverse perspectives finding different issues).
   **Phase 4 is where cost explodes** — and it's advisory, because YOU (Claude) are the final
   evaluator when synthesizing results into spec changes.

   **`--codex-reasoning` is GLOBAL** — it applies to attacks AND evaluations equally.
   There is no way to use xhigh for attacks and medium for evaluation (or vice versa).

   **Reasoning level guidance:**

   | Level | When to use | Trade-off |
   |-------|------------|-----------|
   | `medium` | **Default for gauntlet runs.** Attack quality at medium is still high — adversary system prompts are well-crafted and do the heavy lifting. Eval quality at medium is fine because it's advisory (Claude does final evaluation). | Best cost/value ratio |
   | `high` | User explicitly requests deeper analysis, or spec is unusually complex (>30 sections, multiple interacting systems) | 2-3× more quota than medium |
   | `xhigh` | Almost never for gauntlet. 60 calls at xhigh will burn through Codex 5h queue in minutes. Only if user explicitly requests it AND understands the cost. | Can exhaust daily quota in one run |
   | `low` | Quick exploratory gauntlet, draft specs, when you just want a rough signal | Fast but may miss subtle issues |

   **Always pass `--codex-reasoning medium` unless the user explicitly requests otherwise.**

   Present the cost estimate before launching:
   ```
   Gauntlet Cost Estimate
   ═══════════════════════════════════════
   Adversaries: 8 × 2 attack models = 16 Phase 1 calls
   Estimated concerns: ~200-400 (typical for detailed specs)
   Phase 4 eval: ~20-30 batches × 2 eval models = 40-60 calls
   Total calls: ~60-80
   Reasoning: medium (recommended)

   [Launch] [Adjust reasoning] [Reduce adversaries]
   ```

4. **Arm Adversaries** (REQUIRED before running gauntlet). See below.

5. Run the gauntlet with armed briefings.

   **Gemini Rate Limit Staggering (REQUIRED):**
   When using Gemini CLI models as attack models, do NOT launch all adversaries simultaneously. Gemini's free tier has a **4 requests per minute** rate limit that causes 429 errors and returns 0 structured concerns if exceeded.

   - **Max 4 Gemini calls per 60-second window**
   - Launch up to 4 adversaries at once, wait 61s, then launch the next batch
   - All batches run in background — do NOT block-wait for Batch 1 to finish before launching Batch 2
   - After launching each batch, do a quick `TaskOutput(block=false)` check at ~45s to catch quota errors early
   - Collect all results AFTER all batches are launched

   **Example launch order** (8 adversaries, Gemini attack model):
   ```
   Batch 1: PARA, BURN, LAZY, PEDA (launch together)
   sleep 61s
   Batch 2: ASSH, PREV, AUDT, FLOW (launch together)
   Collect all 8 results
   ```

6. **Post-Gauntlet Synthesis (REQUIRED — this is where real evaluation happens).**

   The pipeline's automated evaluation (Phases 2-4) is a useful first pass, but **Claude is the
   final evaluator**. The pipeline generates concerns; Claude judges them. This is intentional —
   Claude has full codebase context, spec history, and architectural understanding that the
   pipeline's eval models do not.

   **Step 6a: Parse Sanity Check**

   After the pipeline completes, check that the parser accurately captured all model responses.

   **Why:** Some models (especially Gemini) output structured markdown (`### 1. Title` with
   sub-bullets) instead of plain numbered lists (`1. Concern text`). The parser expects
   `line[0].isdigit()` so `### 1.` lines are silently dropped — entire high-quality responses
   can parse to 0 concerns.

   **Process:**
   - Check the gauntlet output for any adversary×model combinations with 0 concerns
   - If any exist, read the raw responses file (`.adversarial-spec-gauntlet/raw-responses-*.json`)
   - Launch a **haiku subagent** to read the raw responses for 0-concern entries and report:
     "N responses had substantive content but 0 parsed concerns. Summaries: [one-line each]"
   - If mismatches found, YOU read the raw responses directly — they're part of your evaluation input

   **Common parse failure patterns:**
   - `### N. Title` (Gemini markdown headers) — parser expects `N.` at line start
   - Structured sub-bullets without a plain numbered parent line
   - Concerns formatted as prose paragraphs without numbering

   **Cost:** One haiku call (~2K input tokens). Prevents losing entire model perspectives.

   **Step 6b: Synthesize ALL Inputs**

   Your evaluation inputs are:
   1. **Pipeline verdicts** (Phase 4 output) — accepted, dismissed, acknowledged, deferred
   2. **Raw responses for parse failures** — concerns the pipeline never evaluated
   3. **Your own codebase knowledge** — architecture docs, blast zone files, implementation state
   4. **Spec context** — what's already addressed, what's intentional, what's out of scope

   **Evaluation process:**
   - Start with pipeline-accepted concerns — these already passed automated review. Quickly
     confirm they're real (the pipeline is usually right on accepts).
   - Check pipeline-dismissed concerns for false negatives — did the eval model dismiss something
     valid? Skim the reasoning. Focus on dismissals where the eval said "spec already handles this"
     but you know the spec doesn't.
   - Read raw responses from parse failures. These are often the highest-signal concerns because
     they came from a different model perspective (Gemini vs GPT).
   - **Deduplicate across sources.** The same concern often appears from multiple adversaries and
     both parsed + unparsed responses. Group by theme, not by source.
   - Classify each unique concern:
     - **Accept** — spec needs revision. Note what changes.
     - **Acknowledge** — valid point, won't address (out of scope, known tradeoff). Credit the adversary.
     - **Dismiss** — not valid. One sentence why.

   **Step 6c: Present Findings**

   Present a consolidated concern report (not the raw pipeline dump):
   ```
   Gauntlet Findings
   ═══════════════════════════════════════
   Sources: N pipeline-evaluated + M from parse recovery
   After dedup: X unique concerns

   ACCEPTED (spec changes needed):
   1. [theme] — [one-line summary] (sources: PARA×GPT, BURN×Gemini)
   2. ...

   ACKNOWLEDGED (valid, won't address):
   1. [theme] — [one-line summary + why not addressing]
   2. ...

   DISMISSED: Y concerns (noise/already covered)

   [Proceed to spec revision] [Discuss specific concerns]
   ```

7. **Revise spec with accepted concerns.**
   - Add mitigations for accepted concerns
   - Update relevant sections (don't summarize or reduce existing content)
   - Save the full concern report as `gauntlet-concerns-YYYY-MM-DD.json`
   - If significant changes were made, consider running another debate round

8. Optionally run Final Boss (UX Architect review — expensive but thorough)

**If user declines gauntlet:**
- Proceed directly to finalize phase

---

### Arm Adversaries (before gauntlet attack generation)

Adversaries produce higher-quality findings when they have codebase context, not just the spec text. This step assembles per-adversary briefing documents from the Context Readiness Audit inventory (built during debate — see 03-debate.md) and reports token overhead.

**Process:**

#### 1. Check for Context Inventory

The Context Readiness Audit (between debate Round 1 and Round 2) should have produced a `ContextInventoryV1` in session state.

- **If inventory exists:** Check staleness — compare `git_hash` in inventory to current `git rev-parse --short HEAD`. If HEAD changed, re-extract only modified blast zone artifacts.
- **If inventory is missing** (audit was skipped or session is new): Run a lightweight version now — check architecture docs, blast zone files, and git state. Skip the full checklist but get enough for base context.

#### 2. Assemble Base Context (all adversaries)

Every adversary gets a feature briefing (~800 tokens):

- **Architecture excerpt** — relevant subsection of `.architecture/overview.md` (NOT the whole file). If no architecture docs exist, note this as a gap.
- **Target Architecture** — if `specs/<slug>/target-architecture.md` exists (from Phase 4), include it in full. This is the primary architecture context for ALL adversaries. If missing (Phase 4 skipped or legacy session), note: "No target architecture available — architecture-level concerns may be underrepresented."
- **Files in blast zone** — file paths with one-line descriptions of what each does
- **Recent git activity** — last 5 commits touching blast zone files

**Context truncation:** If combined spec + roadmap + target architecture exceeds 80% of the target model's context window, summarize the architecture document before feeding to gauntlet. Preserve all Decision/Rationale sections; truncate Implementation sketches.

#### 3. Assemble Per-Adversary Supplements

Each adversary has a specific lens. Give them ammunition for that lens:

| Adversary | Supplement | Budget |
|-----------|-----------|--------|
| **PARA** (paranoid_security) | Auth/authz patterns in blast zone, input validation boundaries, dependency audit results, API surface area | ~350 tok |
| **BURN** (burned_oncall) | External dependency list with timeout configs, existing error handling patterns (retry, circuit breaker), monitoring status or explicit "none exists" note | ~280 tok |
| **LAZY** (lazy_developer) | Installed SDK capabilities, platform features already available, existing utility functions, framework builtins that overlap with spec proposals | ~420 tok |
| **PEDA** (pedantic_nitpicker) | Type definitions, enum values, schema constraints (nullable, unique, defaults), validation rules, test coverage report if available | ~380 tok |
| **ASSH** (asshole_loner) | Design rationale / ADRs, known tech debt markers (TODO/FIXME/HACK in blast zone), broader architecture context beyond excerpt | ~200 tok |
| **COMP** (existing_system) | Full build/test status, current vs proposed schema diff, naming conventions in area, pending migrations, duplicate file analysis | ~1,100 tok |
| **PREV** (prior_art_scout) | Legacy/archive search results, dependency inventory (installed but unused SDKs), keyword search results across codebase, existing similar pattern analysis | ~650 tok |
| **AUDT** (assumption_auditor) | External API doc excerpts, SDK type definitions, existing integration code showing how external systems actually behave | ~300 tok |
| **FLOW** (info_flow_auditor) | FULL architecture overview (not just excerpt), data flow docs from `.architecture/structured/flows.md`, external API capabilities (REST/WS/webhook), existing latency data if available | ~900 tok |
| **ARCH** (architect) | FULL target architecture doc (not just excerpt), component docs from `.architecture/structured/components/`, existing shared patterns/utilities inventory, first-feature propagation analysis | ~1,000 tok |

#### 4. Apply Relevance Filter

Not every adversary needs every supplement for every spec:

- Spec adds an API endpoint? → PARA gets auth patterns, FLOW gets data flow
- Spec changes a data model? → PEDA gets constraints, COMP gets schema diff
- Spec integrates external service? → AUDT gets API docs, PREV gets existing integrations
- Spec is internal refactor? → LAZY gets utility inventory, ASSH gets design rationale
- If a supplement source was `NOT_AVAILABLE` or `NOT_APPLICABLE` in the audit, skip it and include a one-line note in the "Known Gaps" section of the briefing

#### 5. Format Briefings

Each adversary's context is prepended to the spec in a structured block:

```markdown
## ADVERSARY BRIEFING: [adversary_name]

> This briefing contains codebase context extracted for your review.
> Use it to validate the spec's claims against what actually exists.
> Extraction: 2026-02-09T15:00:00Z | Git: e94ebfe | Branch: main

### Base Context
[architecture excerpt, blast zone files, git activity]

### Your Specific Context
[per-adversary supplement — tailored to this adversary's lens]

### Known Gaps
[anything we couldn't provide and why]
- No monitoring data — this is a CLI tool, no production metrics exist
- Test coverage report not generated — tests exist but no pytest-cov configured

---

## SPECIFICATION TO REVIEW

[spec text]
```

#### 6. Report Token Counts

Present the token overhead before proceeding:

```
Adversary Briefings — Token Report
═══════════════════════════════════════

                          Base   Spec   Supplement   TOTAL
Adversary
──────────────────────────────────────────────────────────
PARA  paranoid_security    800   1,400     350       2,550
BURN  burned_oncall        800   1,400     280       2,480
LAZY  lazy_developer       800   1,400     420       2,620
PEDA  pedantic_nitpicker   800   1,400     380       2,580
ASSH  asshole_loner        800   1,400     200       2,400
COMP  existing_system      800   1,400   1,100       3,300
PREV  prior_art_scout      800   1,400     650       2,850
AUDT  assumption_auditor   800   1,400     300       2,500
FLOW  info_flow_auditor    800   1,400     900       3,100
──────────────────────────────────────────────────────────
TOTALS                   7,200  12,600   4,580      24,380
Previous (spec only):                               12,600
Increase:                                          +11,780  (+93%)

Cost at current adversary model (gemini-3-flash): +$0.0009
```

Token estimation: `len(text) // 4` (approximate, for reporting only).

Store the bundle in session state as `BriefingBundleV1`:
```json
{
  "schema_version": "1.0",
  "generated_at": "ISO-8601",
  "git_hash": "short hash",
  "adversaries": {
    "adversary_name": {
      "base_tokens": 800,
      "supplement_tokens": 350,
      "spec_tokens": 1400,
      "total_tokens": 2550,
      "gaps": ["description of what was missing"]
    }
  }
}
```

#### 7. Run Gauntlet with Briefings

Instead of piping raw spec to all adversaries, pass each adversary its assembled briefing:

```bash
# Each adversary gets its own briefing document via the debate.py gauntlet command
# The briefings are assembled above and passed as the spec input
# If generate_attacks() accepts a briefings dict, use it; otherwise pipe per-adversary
cat briefing-COMP.md | python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet \
  --gauntlet-adversaries existing_system_compatibility
```

In practice, Claude assembles the briefings in memory and passes them to the gauntlet. The `generate_attacks()` function accepts an optional `briefings: dict[str, str]` parameter — if provided, each adversary gets its specific briefing instead of raw spec. If not provided, falls back to spec-only (backward compatible).

**UX_ARCHITECT (Final Boss) is NOT armed here.** The final boss runs AFTER the gauntlet phases and receives the full concern summary. Its context is the gauntlet output itself.

#### Token Budget Guidelines

| Component | Budget | Rationale |
|-----------|--------|-----------|
| Base context (per adversary) | 600–1,000 tok | Architecture excerpt + blast zone + git. Orientation, not drowning. |
| Per-adversary supplement | 200–1,200 tok | COMP/FLOW need more (audit structure). ASSH needs less (attacks logic). |
| Total per adversary | 800–2,200 tok added | Never more than 2x the spec size in added context. |
| Total across all adversaries | < 100% increase | Doubling total input is the upper bound. |

**If budget is exceeded:**
1. Trim base context — shorter architecture excerpt
2. Drop supplements for adversaries where spec doesn't touch their domain
3. Truncate large artifacts with `... N more items`

---

### Phase Transition: gauntlet → finalize

After gauntlet concerns are integrated into the spec, sync both session files per the Phase Transition Protocol (SKILL.md):

1. **Detail file** (`sessions/<id>.json`):
   - Set `current_phase: "finalize"`, `current_step: "Gauntlet complete, spec updated with accepted concerns"`
   - Set `gauntlet_concerns_path` to the saved concerns JSON (e.g., `".adversarial-spec/gauntlet-concerns-2026-02-10.json"`)
   - Append journey: `{"time": "ISO8601", "event": "Gauntlet complete, N concerns accepted", "type": "transition"}`
2. **Pointer file** (`session-state.json`): set `current_phase: "finalize"`, `current_step`, `next_action`, `updated_at`


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: skills/adversarial-spec/phases/06-finalize.md (123 lines, 5599 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
### Step 6: Finalize and Output Document

When ALL opponent models AND you have said `[AGREE]` (and gauntlet is complete or skipped):

**Before outputting, perform a final quality check:**

1. **Completeness**: Verify every section from the document structure is present and substantive
2. **Consistency**: Ensure terminology, formatting, and style are uniform throughout
3. **Clarity**: Remove any ambiguous language that could be misinterpreted
4. **Actionability**: Confirm stakeholders can act on this document without asking follow-up questions

**For Specs (product depth), verify:**
- Executive summary captures the essence in 2-3 paragraphs
- User personas have names, roles, goals, and pain points
- Every user story follows "As a [persona], I want [action] so that [benefit]"
- Success metrics have specific numeric targets and measurement methods
- Scope explicitly lists what is OUT as well as what is IN

**For Specs (technical/full depth), verify:**
- Architecture diagram or description shows all components and their interactions
- Every API endpoint has method, path, request schema, response schema, and error codes
- Data models include field types, constraints, indexes, and relationships
- Security section addresses authentication, authorization, encryption, and input validation
- Performance targets include specific latency, throughput, and availability numbers
- **Getting Started** section exists with clear bootstrap workflow

**For Debug Investigations, verify:**
- Evidence gathered before hypotheses formed (no guessing without data)
- Simple explanations ruled out before complex ones
- Root cause identified with clear evidence chain
- Proposed fix is proportional to the problem (not over-engineered)
- Verification plan exists with specific steps to confirm the fix
- Prevention section identifies tests to add and documentation updates

**Output the final document:**

1. Print the complete, polished document to terminal
2. Write it to the appropriate file:
   - Spec: `spec-output.md`
   - Debug Investigation: `debug-output.md`
3. Print a summary:
   ```
   === Debate Complete ===
   Document: [Product Specification | Technical Specification | Full Specification | Debug Investigation]
   Rounds: N
   Models: [list of opponent models]
   Claude's contributions: [summary of what you added/changed]

   Key refinements made:
   - [bullet points of major changes from initial to final]
   ```
4. If Telegram enabled:
   ```bash
   python3 ~/.claude/skills/adversarial-spec/scripts/debate.py send-final --models MODEL_LIST --doc-type TYPE --rounds N <<'SPEC_EOF'
   <final document here>
   SPEC_EOF
   ```
5. Update session with artifact paths (sync both files per Phase Transition Protocol):
   - Detail file (`sessions/<id>.json`): set `spec_path` to the written file path (`"spec-output.md"` or `"debug-output.md"`)
   - If gauntlet was run, also set `gauntlet_concerns_path` to the saved concerns JSON (if not already set during gauntlet → finalize transition)
   - If a spec manifest was created (`specs/<slug>/manifest.json`), set `manifest_path` to its path
   - Append journey: `{"time": "ISO8601", "event": "Spec finalized: <path>", "type": "artifact"}`
   - Update both files with `current_phase: "finalize"`, `current_step: "Document finalized, awaiting user review"`
   - Use atomic writes for both files

### Step 7: User Review Period

**After outputting the finalized document, give the user a review period:**

> "The document is finalized and written to `spec-output.md`. Please review it and let me know if you have any feedback, changes, or concerns.
>
> Options:
> 1. **Accept as-is** - Document is complete
> 2. **Request changes** - Tell me what to modify, and I'll update the spec
> 3. **Run another review cycle** - Send the updated spec through another adversarial debate"

**If user requests changes:**
1. Make the requested modifications to the spec
2. Show the updated sections
3. Write the updated spec to file
4. Ask again: "Changes applied. Would you like to accept, make more changes, or run another review cycle?"

**If user wants another review cycle:**
- Proceed to Step 8 (Additional Review Cycles)

**If user accepts:**
- Finalization complete. Ask if they want to proceed to execution planning (Phase 5).

### Step 8: Additional Review Cycles (Optional)

After the user review period, or if explicitly requested:

> "Would you like to run an additional adversarial review cycle for extra validation?"

**If yes:**

1. Ask if they want to use the same models or different ones:
   > "Use the same models (MODEL_LIST), or specify different models for this cycle?"

2. Run the adversarial debate again from Step 3 with the current document as input.

3. Track cycle count separately from round count:
   ```
   === Cycle 2, Round 1 ===
   ```

4. When this cycle reaches consensus, return to Step 7 (User Review Period).

5. Update the final summary to reflect total cycles:
   ```
   === Debate Complete ===
   Document: [Product Specification | Technical Specification | Full Specification | Debug Investigation]
   Cycles: 2
   Total Rounds: 5 (Cycle 1: 3, Cycle 2: 2)
   Models: Cycle 1: [models], Cycle 2: [models]
   Claude's contributions: [summary across all cycles]
   ```

**Use cases for additional cycles:**
- First cycle with faster models (gemini-cli/gemini-3-flash-preview), second cycle with stronger models (codex/gpt-5.3-codex, gemini-cli/gemini-3-pro-preview)
- First cycle for structure and completeness, second cycle for security or performance focus
- Fresh perspective after user-requested changes



<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: skills/adversarial-spec/phases/07-execution.md (292 lines, 10117 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
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

### Step 2.5: Architecture Spine (if Target Architecture exists)

**Load target architecture:**
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

Only after verification: proceed to Phase 7 (Implementation).


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: skills/adversarial-spec/phases/08-implementation.md (202 lines, 8283 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
## Implementation (Phase 8)

After the execution plan is generated, offer to proceed with implementation:

> "Execution plan generated with N tasks. Would you like to proceed with implementation?"

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


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: skills/adversarial-spec/reference/advanced-features.md (227 lines, 7756 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
## Advanced Features

### Critique Focus Modes

Direct models to prioritize specific concerns using `--focus`:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models codex/gpt-5.3-codex --focus security --doc-type tech <<'SPEC_EOF'
<spec here>
SPEC_EOF
```

**Available focus areas:**
- `security` - Authentication, authorization, input validation, encryption, vulnerabilities
- `scalability` - Horizontal scaling, sharding, caching, load balancing, capacity planning
- `performance` - Latency targets, throughput, query optimization, memory usage
- `ux` - User journeys, error states, accessibility, mobile experience
- `reliability` - Failure modes, circuit breakers, retries, disaster recovery
- `cost` - Infrastructure costs, resource efficiency, build vs buy

Run `python3 ~/.claude/skills/adversarial-spec/scripts/debate.py focus-areas` to see all options.

### Model Personas

Have models critique from specific professional perspectives using `--persona`:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models codex/gpt-5.3-codex --persona "security-engineer" --doc-type tech <<'SPEC_EOF'
<spec here>
SPEC_EOF
```

**Available personas:**
- `security-engineer` - Thinks like an attacker, paranoid about edge cases
- `oncall-engineer` - Cares about observability, error messages, debugging at 3am
- `junior-developer` - Flags ambiguity and tribal knowledge assumptions
- `qa-engineer` - Identifies missing test scenarios and acceptance criteria
- `site-reliability` - Focuses on deployment, monitoring, incident response
- `product-manager` - Focuses on user value and success metrics
- `data-engineer` - Focuses on data models and ETL implications
- `mobile-developer` - API design from mobile perspective
- `accessibility-specialist` - WCAG compliance, screen reader support
- `legal-compliance` - GDPR, CCPA, regulatory requirements

Run `python3 ~/.claude/skills/adversarial-spec/scripts/debate.py personas` to see all options.

Custom personas also work: `--persona "fintech compliance officer"`

### Context Injection

Include existing documents as context for the critique using `--context`:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models codex/gpt-5.3-codex --context ./existing-api.md --context ./schema.sql --doc-type tech <<'SPEC_EOF'
<spec here>
SPEC_EOF
```

Use cases:
- Include existing API documentation that the new spec must integrate with
- Include database schemas the spec must work with
- Include design documents or prior specs for consistency
- Include compliance requirements documents

### Session Persistence and Resume

Long debates can crash or need to pause. Sessions save state automatically:

```bash
# Start a named session
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models codex/gpt-5.3-codex --session my-feature-spec --doc-type tech <<'SPEC_EOF'
<spec here>
SPEC_EOF

# Resume where you left off (no stdin needed)
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --resume my-feature-spec

# List all sessions
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py sessions
```

Sessions save:
- Current spec state
- Round number
- All configuration (models, focus, persona, preserve-intent)
- History of previous rounds

Sessions are stored in `~/.config/adversarial-spec/sessions/`.

### Auto-Checkpointing

When using sessions, each round's spec is saved to `.adversarial-spec-checkpoints/` in the current directory:

```
.adversarial-spec-checkpoints/
├── my-feature-spec-round-1.md
├── my-feature-spec-round-2.md
└── my-feature-spec-round-3.md
```

Use these to rollback if a revision makes things worse.

### Retry on API Failure

API calls automatically retry with exponential backoff (1s, 2s, 4s) up to 3 times. If a model times out or rate-limits, you'll see:

```
Warning: codex/gpt-5.3-codex failed (attempt 1/3): rate limit exceeded. Retrying in 1.0s...
```

If all retries fail, the error is reported and other models continue.

### Response Validation

If a model provides critique but doesn't include proper `[SPEC]` tags, a warning is displayed:

```
Warning: codex/gpt-5.3-codex provided critique but no [SPEC] tags found. Response may be malformed.
```

This catches cases where models forget to format their revised spec correctly.

### Preserve Intent Mode

Convergence can collapse toward lowest-common-denominator interpretations, sanding off novel design choices. The `--preserve-intent` flag makes removals expensive:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models codex/gpt-5.3-codex --preserve-intent --doc-type tech <<'SPEC_EOF'
<spec here>
SPEC_EOF
```

When enabled, models must:

1. **Quote exactly** what they want to remove or substantially change
2. **Justify the harm** - not just "unnecessary" but what concrete problem it causes
3. **Distinguish error from preference**:
   - ERRORS: Factually wrong, contradictory, or technically broken (remove/fix)
   - RISKS: Security holes, scalability issues, missing error handling (flag)
   - PREFERENCES: Different style, structure, or approach (DO NOT remove)
4. **Ask before removing** unusual but functional choices

This shifts the default from "sand off anything unusual" to "add protective detail while preserving distinctive choices."

**Use when:**
- Your spec contains intentional unconventional choices
- You want models to challenge your ideas, not homogenize them
- Previous rounds removed things you wanted to keep
- You're refining an existing spec that represents deliberate decisions

Can be combined with other flags: `--preserve-intent --focus security`

### Cost Tracking

Every critique round displays token usage and estimated cost:

```
=== Cost Summary ===
Total tokens: 12,543 in / 3,221 out
Total cost: $0.0847

By model:
  codex/gpt-5.3-codex: $0.00 (8,234 in / 2,100 out) [subscription]
  gemini-cli/gemini-3-pro-preview: $0.00 (4,309 in / 1,121 out) [free tier]
```

Cost is also included in JSON output and Telegram notifications.

### Saved Profiles

Save frequently used configurations as profiles:

**Create a profile:**
```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py save-profile strict-security --models codex/gpt-5.3-codex,gemini-cli/gemini-3-pro-preview --focus security --doc-type tech
```

**Use a profile:**
```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --profile strict-security <<'SPEC_EOF'
<spec here>
SPEC_EOF
```

**List profiles:**
```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py profiles
```

Profiles are stored in `~/.config/adversarial-spec/profiles/`.

Profile settings can be overridden by explicit flags.

### Diff Between Rounds

Generate a unified diff between spec versions:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py diff --previous round1.md --current round2.md
```

Use this to see exactly what changed between rounds. Helpful for:
- Understanding what feedback was incorporated
- Reviewing changes before accepting
- Documenting the evolution of the spec

### Export to Task List

Extract actionable tasks from a finalized spec:

```bash
cat spec-output.md | python3 ~/.claude/skills/adversarial-spec/scripts/debate.py export-tasks --models codex/gpt-5.3-codex --doc-type prd
```

Output includes:
- Title
- Type (user-story, task, spike, bug)
- Priority (high, medium, low)
- Description
- Acceptance criteria

Use `--json` for structured output suitable for importing into issue trackers:

```bash
cat spec-output.md | python3 ~/.claude/skills/adversarial-spec/scripts/debate.py export-tasks --models codex/gpt-5.3-codex --doc-type prd --json > tasks.json
```



<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: skills/adversarial-spec/reference/context-addition-protocol.md (317 lines, 14048 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
## Context Addition Protocol

### Purpose

Opponent models only see what is piped to them via stdin. Without codebase context, they can only critique internal coherence of the spec. With targeted context, they can validate the spec against real code artifacts -- catching mismatches between what the spec proposes and what actually exists.

This protocol defines WHEN and HOW the orchestrating agent (Claude) should enrich spec documents with codebase context before sending them to opponent models.

**Relationship to existing mechanisms:**
- `--context` flag: Passes whole files. Good for static docs, bad for extracting targeted snippets.
- Pre-gauntlet `ContextBuilder`: Collects git position, build health, schema snapshots. Runs before gauntlet, not during debate rounds.
- This protocol: Fills the gap between those two -- targeted extraction during debate rounds, scoped to what the current round needs.

---

### 1. When to Add Context

Context extraction has a cost: tokens, latency, and noise. Only add it when it will change the quality of critique.

| Round | Focus | Add Context? | Rationale |
|-------|-------|:------------:|-----------|
| **Round 1** | Requirements validation | **No** | Requirements are about user value and story coverage. Code artifacts add noise. Exception: if the spec references existing behavior ("maintain backward compatibility with X"), extract X's interface. |
| **Round 2** | Architecture and design | **Yes** | This is the primary round for context. Models need to see real schema, real types, real function signatures to validate proposed architecture against what exists. |
| **Round 3** | Implementation details | **Yes (selective)** | Add only artifacts directly referenced by the round's concerns. If Round 2 already included the schema, do not re-include it. Add new artifacts only (e.g., a specific function body if the critique questions an algorithm). |
| **Round 4+** | Refinement | **Rarely** | Only if a specific concern requires verification against code. Most refinement rounds are about spec coherence, not code alignment. |

**Decision rule:** Before extracting context, ask: "Would an engineer reviewing this spec open a specific file to validate a claim?" If yes, extract that artifact. If the spec is self-contained for this round's focus, skip context.

---

### 2. What to Extract

**Always extract (when adding context at all):**
- Schema definitions (`schema.ts`, `schema.prisma`, `models.py`, etc.)
- TypeScript/Python type definitions and interfaces referenced in the spec
- Function signatures (name, params, return type) for functions the spec modifies or wraps
- Key constants and configuration shapes (e.g., `config.ts` exports)
- Enum definitions that define state machines or status flows

**Extract when relevant to the round:**
- Existing API route signatures (request/response types) when the spec proposes new or modified endpoints
- Database table definitions when the spec proposes schema changes
- Test file structure (file names only, not test bodies) when the spec proposes a testing strategy
- Error type definitions when the spec proposes error handling changes

**Never extract:**
- Full file contents (use targeted snippets, not `cat file.ts`)
- Implementation bodies of functions (signatures are enough; bodies waste tokens)
- Node modules, lock files, or generated code
- `.env` files, credentials, secrets, or config values containing keys
- Git history or diffs (the pre-gauntlet handles this)
- Test assertion bodies (opponent models do not need to review test logic)

---

### 3. How to Extract

The orchestrating agent (Claude) performs extraction directly using its available tools. There is no separate script for this -- the agent uses Grep, Read, and Glob during the synthesis step between debate rounds.

**Extraction workflow (between rounds, before sending to opponents):**

```
1. Identify spec claims that reference codebase artifacts
   - Look for: table names, function names, type names, file paths, module names
   - Example: "Extend the `orders` table with a `status` field" -> extract orders table definition

2. Extract targeted artifacts using tools:
   - Grep: Find where a type/function is defined
     grep -n "export interface Order" convex/
   - Read: Pull the specific lines (not the whole file)
     Read convex/schema.ts lines 45-72
   - Glob: Find related files
     glob "convex/**/*order*"

3. Format as appendix (see Section 4)

4. Verify size budget (see Section 5)

5. Attach appendix to spec before piping to opponents
```

**Extraction commands (examples):**

```bash
# Schema definitions
grep -A 30 "orders:" convex/schema.ts

# Function signatures (just the export line + params)
grep -A 5 "export.*function.*placeOrder" worker/src/

# Type definitions
grep -A 20 "export interface OrderRequest" worker/src/types.ts

# Constants and config shape
grep -A 10 "export const" worker/src/lib/config.ts

# Existing API routes
grep "httpRouter\|\.route(" convex/http.ts
```

---

### 4. Format

Context is appended as a clearly separated appendix at the end of the spec, AFTER the `[/SPEC]` tag's content but still within the heredoc sent to the debate script. This prevents opponents from confusing context with spec content.

```markdown
[SPEC]
... spec content ...
[/SPEC]

---

## APPENDIX: Codebase Context (Round N)

> This appendix contains real code artifacts extracted from the codebase.
> Use these to validate the spec's claims against what actually exists.
> Extraction timestamp: 2026-02-09T14:30:00Z | Git: abc1234 (branch: feature-x)

### A1. Schema: convex/schema.ts (lines 45-72)

```typescript
orders: defineTable({
  exchange: v.string(),
  exchangeOrderId: v.string(),
  side: v.union(v.literal("buy"), v.literal("sell")),
  price: v.number(),
  quantity: v.number(),
  status: v.string(),
  // ...
})
```

### A2. Interface: worker/src/types.ts (lines 12-28)

```typescript
export interface OrderRequest {
  exchange: "kalshi" | "polymarket";
  ticker: string;
  side: "buy" | "sell";
  price: number;
  quantity: number;
}
```

### A3. Function Signature: worker/src/connectors/kalshi.ts (line 89)

```typescript
export async function placeOrder(
  credentials: ExchangeCredentials,
  order: OrderRequest
): Promise<OrderResponse>
```
```

**Formatting rules:**
- Each artifact gets a numbered label (`A1`, `A2`, ...) for easy reference in critiques
- Include the source file path and line numbers
- Use the correct language tag on code fences
- Keep each artifact self-contained -- an opponent model should understand it without reading the full file
- Add a one-line note if the artifact has been truncated (e.g., "// ... 15 more fields omitted")

---

### 5. Size Budget

**Hard limit: 200 lines for the appendix.** This keeps the appendix under ~25% of a typical spec, avoiding the failure mode where context drowns out the document being reviewed.

| Artifact Type | Typical Size | Budget Guideline |
|---------------|:------------:|:----------------:|
| Schema table definition | 10-30 lines | 2-3 tables max |
| Interface/type definition | 5-20 lines | 3-5 types max |
| Function signature | 3-8 lines | 5-8 signatures max |
| Constants/enums | 5-15 lines | 2-3 max |
| Architecture overview excerpt | 15-30 lines | 1 max |

**If the appendix exceeds 200 lines:**
1. Prioritize artifacts that the spec directly modifies over artifacts it merely references
2. Trim function signatures to just the export line (omit param docs)
3. Truncate large schemas to only the tables/fields mentioned in the spec
4. Remove architecture overview (opponents can infer architecture from types and signatures)

**If the appendix is under 50 lines:** You are probably under-extracting. Check if the spec references artifacts you have not included.

---

### 6. Architecture Docs

The `.architecture/` directory (when it exists) contains high-level system overviews. These are useful but expensive in tokens.

**Include `.architecture/overview.md` (or equivalent) when:**
- Round 2 is the first round with context (opponents have no prior codebase knowledge)
- The spec proposes a new component that interacts with multiple existing components
- The spec changes data flow between existing components

**Skip architecture docs when:**
- Round 3+ (opponents already saw it in Round 2)
- The spec modifies a single, isolated component
- The schema and type definitions already tell the story
- The architecture overview exceeds 40 lines (extract only the relevant subsection instead)

**How to include:**
- Extract only the section relevant to the spec's scope, not the full overview
- Place it as `A0` (before code artifacts) since it provides the framing
- Example: if the spec is about order execution, extract only the "Order Flow" or "Trading Pipeline" section from the architecture overview

```markdown
### A0. Architecture Context: .architecture/overview.md (lines 34-58)

> Extracted subsection: "Order Execution Pipeline"

The worker receives order requests via the Convex HTTP action `placeOrder`,
routes them through exchange-specific connectors, and writes results back
to the `orders` table via mutation...
```

---

### 7. Staleness Warning

Codebase context can become stale between the time it is extracted and when opponent models read it. Always mark extraction provenance.

**Required header on every appendix:**

```markdown
> Extraction timestamp: 2026-02-09T14:30:00Z | Git: abc1234 (branch: feature-x)
```

**The orchestrating agent must capture:**
- Timestamp of extraction (ISO 8601)
- Current git HEAD short hash (first 7 chars)
- Current branch name

**Staleness rules:**
- If the appendix was extracted in a previous round and no relevant commits have landed since, reuse it with a note: `(reused from Round N, no relevant changes)`
- If new commits have landed that touch files in the appendix, re-extract those specific artifacts
- If the working tree is dirty (uncommitted changes to files in the appendix), add a warning: `WARNING: Uncommitted changes exist in [file]. Extracted content may not match working state.`

**How to capture git info:**

```bash
# Short hash
git rev-parse --short HEAD

# Branch name
git branch --show-current

# Check if specific files have uncommitted changes
git diff --name-only -- convex/schema.ts worker/src/types.ts
```

---

### Integration with Debate Flow

This protocol slots into **Step 4** of `03-debate.md` (Send to Opponent Models). The modified flow:

1. (Existing) Revise spec based on previous round's feedback
2. **(New) Context extraction decision:** Based on the round number and focus, decide whether to add/update the appendix
3. **(New) Extract and format:** If adding context, run the extraction workflow from Section 3
4. **(New) Assemble payload:** Combine spec + appendix into the heredoc
5. (Existing) Send to debate script via stdin

The appendix is **not part of the spec itself**. When extracting the `[SPEC]...[/SPEC]` content for persistence or checkpointing, strip the appendix. The appendix is ephemeral -- it exists only in the payload sent to opponents.

### Integration with `--context` Flag

The `--context` flag and this protocol serve different purposes and can be used together:

| Mechanism | What it sends | Who decides | Scope |
|-----------|---------------|-------------|-------|
| `--context` flag | Whole files | User | Static across all rounds |
| This protocol | Targeted snippets | Orchestrating agent | Per-round, evolves with debate |

If the user passes `--context ./schema.sql`, do not duplicate that content in the appendix. Reference it: `(See --context file: schema.sql for full schema. Relevant excerpt below.)`

### Integration with Context Readiness Audit

The Context Readiness Audit (see `03-debate.md`, runs between Round 1 and Round 2) produces a `ContextInventoryV1` cached in session state. This inventory is the **source of truth** for what context is available.

**How this protocol uses the inventory:**

1. **Round 2 (first round with context):** Instead of extracting artifacts from scratch, check the inventory for `AVAILABLE` sources. Extract from the paths and line ranges recorded there. This avoids redundant Grep/Read calls.

2. **Round 3+:** Check if inventory `git_hash` matches current HEAD. If stale, re-extract only modified artifacts. If current, reuse with note: `(reused from Round N, no relevant changes)`.

3. **Token tracking:** When assembling the appendix, estimate tokens for each artifact (`len(text) // 4`) and include a total in the appendix header:

   ```markdown
   > Extraction timestamp: 2026-02-09T14:30:00Z | Git: abc1234 (branch: feature-x)
   > Context tokens: ~1,180 (A0: 400, A1: 350, A2: 280, A3: 150)
   ```

4. **Gap awareness:** If the inventory has `NOT_AVAILABLE` sources relevant to this round's focus, note them at the end of the appendix:

   ```markdown
   ### Context Gaps (from audit)
   - Test coverage: No pytest-cov configured. Tests exist but coverage unknown.
   - Monitoring: No alerting configured (CLI tool).
   ```

   This gives opponent models visibility into what they CAN'T validate.

**If no inventory exists** (audit was skipped, or the debate started without it): Fall back to the extraction workflow in Section 3 above. The inventory is a cache optimization, not a hard dependency.

### Integration with Arm Adversaries

The same inventory feeds the Arm Adversaries step (see `04-gauntlet.md`) which assembles per-adversary briefings before the gauntlet. The key difference:

| This protocol (debate rounds) | Arm Adversaries (gauntlet) |
|-------------------------------|---------------------------|
| Same appendix for all opponent models | Per-adversary briefings with unique supplements |
| Targeted snippets (200-line budget) | Larger context packages (up to 2x spec size) |
| Evolves per round | One-shot assembly before attack generation |
| Claude extracts manually | Claude assembles from inventory + fresh extraction |

Both draw from the same inventory. Neither should re-extract what the other already has.


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: skills/adversarial-spec/reference/convergence-and-telegram.md (49 lines, 1865 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
## Convergence Rules

- Maximum 10 rounds per cycle (ask user to continue if reached)
- ALL models AND Claude must agree for convergence
- More models = stricter convergence (each adds a perspective)
- Do not agree prematurely - only accept when document is genuinely complete
- Apply critique criteria rigorously based on document type

**Quality over speed**: The goal is a document that needs no further refinement. If any participant raises a valid concern, address it thoroughly. A spec that takes 7 rounds but is bulletproof is better than one that converges in 2 rounds with gaps.

**When to say [AGREE]**: Only agree when you would confidently hand this document to:
- For PRD: A product team starting implementation planning
- For Tech Spec: An engineering team starting a sprint

**Skepticism of early agreement**: If opponent models agree too quickly (rounds 1-2), they may not have read the full document carefully. Always press for confirmation.

## Telegram Integration (Optional)

Enable real-time notifications and human-in-the-loop feedback. Only active with `--telegram` flag.

### Setup

1. Message @BotFather on Telegram, send `/newbot`, follow prompts
2. Copy the bot token
3. Run setup:
   ```bash
   python3 ~/.claude/skills/adversarial-spec/scripts/telegram_bot.py setup
   ```
4. Message your bot, then run setup again to get chat ID
5. Set environment variables:
   ```bash
   export TELEGRAM_BOT_TOKEN="your-token"
   export TELEGRAM_CHAT_ID="your-chat-id"
   ```

### Usage

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --model codex/gpt-5.3-codex --doc-type tech --telegram <<'SPEC_EOF'
<document here>
SPEC_EOF
```

After each round:
- Bot sends summary to Telegram
- 60 seconds to reply with feedback (configurable via `--poll-timeout`)
- Reply incorporated into next round
- No reply = auto-continue



<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: skills/adversarial-spec/reference/current-models.md (59 lines, 2780 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# Current Model Recommendations

> **Last updated: 2026-03-12**
> Review this file when a new model is released. Update models here, then sync hardcoded
> defaults in `scripts/` (search for the old model name).

## Recommended Models by Role

### Attack / Critique (concern generation)
Models that find issues in specs. Diverse perspectives matter more than raw power.

| Provider | Model ID | Notes |
|----------|----------|-------|
| Codex CLI | `codex/gpt-5.4` | **Primary.** Free via ChatGPT subscription. Token-efficient. |
| Gemini CLI | `gemini-cli/gemini-3-pro-preview` | Free. Strong on unique angles. Parser may need sanity check (outputs `### N.` headers). |
| Claude CLI | `claude-cli/claude-sonnet-4-6` | Free. Cannot nest inside a Claude session — use only from Codex or standalone. |
| Gemini CLI | `gemini-cli/gemini-3-flash-preview` | Free. Faster, cheaper, good for quick passes. |

### Evaluation (concern judgment)
Models that evaluate whether concerns are valid. The pipeline auto-selects eval models, but
**Claude (the orchestrator) is the final evaluator** — pipeline eval is advisory.

| Provider | Model ID | Notes |
|----------|----------|-------|
| Codex CLI | `codex/gpt-5.4` | Default eval model. Use `--codex-reasoning medium` for gauntlet eval. |
| Gemini CLI | `gemini-cli/gemini-3-pro-preview` | Second eval model for multi-model consensus. |

### Frontier (deep analysis, final boss)
For tasks requiring maximum reasoning depth.

| Provider | Model ID | Notes |
|----------|----------|-------|
| Claude | Claude Opus 4.6 | The orchestrating model. Best evaluator — has full codebase context. |
| Codex CLI | `codex/gpt-5.4` | With `--codex-reasoning high` or `xhigh` for targeted deep analysis. |

## Deprecated Models

| Old Model | Replacement | When |
|-----------|-------------|------|
| `codex/gpt-5.3-codex` | `codex/gpt-5.4` | 2026-03-05 (GPT-5.4 release) |
| `codex/gpt-5.1-codex-max` | `codex/gpt-5.4` | 2026-03-05 |
| `gpt-5.3` (API) | `gpt-5.4` (if using API) | 2026-03-05 |

## Paid API Models (avoid for adversarial-spec debates)

Per user preference: **never use paid APIs for adversarial-spec debates — use CLIs only (free).**

| Provider | Model ID | Cost | When to use |
|----------|----------|------|-------------|
| OpenAI API | `gpt-5.4` | $5/$15 per 1M tok | Only if CLI is unavailable |
| OpenRouter | `openrouter/openai/gpt-5.4` | Varies | Only if CLI is unavailable |

## Keeping Defaults in Sync

When updating this file, also update hardcoded model defaults in:
- `scripts/providers.py` — `MODEL_COSTS`, `PROVIDERS` list, `auto_detect_providers()`
- `scripts/gauntlet.py` — search for old model name in fallback strings
- `scripts/debate.py` — docstring examples, help text
- `SETUP.md` — provider table


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: skills/adversarial-spec/reference/document-types.md (210 lines, 8601 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
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
# Product-focused spec (like old PRD)
adversarial-spec critique --doc-type spec --depth product

# Technical spec (like old tech spec)
adversarial-spec critique --doc-type spec --depth technical

# Full spec (both product and technical)
adversarial-spec critique --doc-type spec --depth full
```

**Legacy flags (deprecated, will be removed in v2.0):**
- `--doc-type prd` → `--doc-type spec --depth product`
- `--doc-type tech` → `--doc-type spec --depth technical`

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
> Model A (codex/gpt-5.3-codex) suggests: "We need a caching layer with TTL and circuit breaker pattern"
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
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models codex/gpt-5.3-codex,gemini-cli/gemini-3-pro-preview --doc-type debug <<'SPEC_EOF'
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



<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: skills/adversarial-spec/reference/gauntlet-details.md (75 lines, 3370 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
## Adversarial Gauntlet

The gauntlet is a multi-phase stress test that puts your spec through adversarial attack by specialized personas, then evaluates which attacks are valid.

### Gauntlet Phases

1. **Phase 1: Adversary Attacks** - Multiple adversary personas attack the spec in parallel
2. **Phase 2: Evaluation** - A frontier model evaluates each attack (accept/dismiss/defer)
3. **Phase 3: Rebuttals** - Dismissed adversaries can challenge the evaluation
4. **Phase 4: Summary** - Aggregated results showing accepted concerns
5. **Phase 5: Final Boss** (optional) - Opus 4.6 UX Architect reviews the spec holistically

### Adversary Personas

| Persona | Focus |
|---------|-------|
| `paranoid_security` | Auth holes, injection, encryption gaps, trust boundaries |
| `burned_oncall` | Missing alerts, log gaps, failure modes, debugging at 3am |
| `lazy_developer` | Complexity that the platform/SDK already handles. Dismissals must prove simpler fails. |
| `pedantic_nitpicker` | Inconsistencies, spec gaps, undefined edge cases |
| `asshole_loner` | Aggressive devil's advocate, challenges fundamental assumptions |
| `prior_art_scout` | Finds existing code, SDKs, legacy implementations that spec ignores |
| `assumption_auditor` | Challenges domain premises, demands documentation citations |
| `information_flow_auditor` | Audits architecture arrows - every unlabeled flow, every assumed mechanism |

### Usage

```bash
# Run gauntlet with all adversaries (generally this is what you want)
cat spec.md | python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet --gauntlet-adversaries all

# Run with specific adversaries
cat spec.md | python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet --gauntlet-adversaries paranoid_security,burned_oncall

# Combine with regular critique (gauntlet runs first)
cat spec.md | python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models codex/gpt-5.3-codex --gauntlet --gauntlet-adversaries all

# Skip rebuttals for faster execution
cat spec.md | python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet --gauntlet-adversaries all --no-rebuttals

# List available adversaries
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet-adversaries

# View adversary performance stats
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py adversary-stats
```

### Final Boss Review

After phase 4 completes, you'll be prompted:

```
Run Final Boss UX review? (y/n):
```

The Final Boss is an Opus 4.6 UX Architect who reviews the spec for:
- User journey completeness
- Error state handling
- Accessibility concerns
- Overall coherence

This is expensive but thorough. You can also pre-commit with `--final-boss` to skip the prompt.

### Gauntlet Options

- `--gauntlet, -g` - Enable gauntlet mode (can combine with critique)
- `--gauntlet-adversaries` - **NAMES only** (comma-separated or `all`). NOT a count!
  - ✅ `--gauntlet-adversaries all`
  - ✅ `--gauntlet-adversaries paranoid_security,burned_oncall`
  - ❌ `--gauntlet-adversaries 5` (WRONG - this is not a count)
- `--gauntlet-model` - Model for adversary attacks (default: auto-select free model)
- `--gauntlet-frontier` - Model for evaluation (default: auto-select frontier model)
- `--no-rebuttals` - Skip Phase 3 rebuttal phase
- `--final-boss` - Auto-run Phase 5 (skips prompt)



<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: skills/adversarial-spec/reference/script-commands.md (99 lines, 4225 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
## Script Reference

```bash
# Full path to debate.py (required - scripts are in a subdirectory)
DEBATE="python3 ~/.claude/skills/adversarial-spec/scripts/debate.py"

# Core commands
$DEBATE critique --models MODEL_LIST --doc-type TYPE [OPTIONS] < spec.md
$DEBATE critique --resume SESSION_ID
$DEBATE diff --previous OLD.md --current NEW.md
$DEBATE export-tasks --models MODEL --doc-type TYPE [--json] < spec.md

# Info commands
$DEBATE providers      # List supported providers and API key status
$DEBATE focus-areas    # List available focus areas
$DEBATE personas       # List available personas
$DEBATE profiles       # List saved profiles
$DEBATE sessions       # List saved sessions

# Profile management
$DEBATE save-profile NAME --models ... [--focus ...] [--persona ...]

# Telegram
$DEBATE send-final --models MODEL_LIST --doc-type TYPE --rounds N < spec.md

# Gauntlet (adversarial attack on specs)
# IMPORTANT: --gauntlet-adversaries expects NAMES, not a count!
$DEBATE gauntlet --gauntlet-adversaries all < spec.md                    # All adversaries
$DEBATE gauntlet --gauntlet-adversaries paranoid_security,burned_oncall  # Specific ones
$DEBATE gauntlet-adversaries  # List available adversary names
$DEBATE adversary-stats       # View adversary performance
```

**Critique options:**
- `--models, -m` - Comma-separated model list (auto-detects from available API keys if not specified)
- `--doc-type, -d` - Document type: prd or tech (default: tech)
- `--round, -r` - Current round number (default: 1)
- `--focus, -f` - Focus area for critique
- `--persona` - Professional persona for critique
- `--context, -c` - Context file (can be used multiple times)
- `--profile` - Load settings from saved profile
- `--preserve-intent` - Require explicit justification for any removal
- `--session, -s` - Session ID for persistence and checkpointing
- `--resume` - Resume a previous session by ID
- `--press, -p` - Anti-laziness check for early agreement
- `--telegram, -t` - Enable Telegram notifications
- `--poll-timeout` - Telegram reply timeout in seconds (default: 60)
- `--json, -j` - Output as JSON
- `--codex-search` - Enable web search for Codex CLI models (allows researching current info)
- `--timeout` - Timeout in seconds for model API/CLI calls (default: 600)
- `--show-cost` - Show cost summary after critique

## External Documentation Discovery (Context7)

Before the gauntlet runs, the **Discovery Agent** extracts external services from your spec and fetches their official documentation via Context7. This prevents models from making assumptions based on training data patterns.

### Why Discovery Matters

AI models share training data and thus share false assumptions. The classic failure:

> All models assumed "crypto trading = on-chain transactions" when Polymarket's CLOB is actually off-chain with SDK-handled signing. 11 concerns were raised about nonces that don't exist.

### How to Use Discovery

When you have Context7 MCP tools available, run discovery before the gauntlet:

1. **Extract services from spec:**
   ```python
   from pre_gauntlet import DiscoveryAgent, run_discovery

   result = run_discovery(spec_text, min_confidence=0.6, max_services=5)
   print(f"Discovered: {[s.name for s in result.services]}")
   ```

2. **Fetch documentation via Context7:**
   - Use `mcp__context7__resolve-library-id` to resolve library names
   - Use `mcp__context7__query-docs` to fetch relevant documentation
   - Results are cached locally (24h TTL, `~/.cache/adversarial-spec/knowledge/`)

3. **Inject priming context into gauntlet:**
   ```python
   from pre_gauntlet import run_pre_gauntlet

   pre_result = run_pre_gauntlet(
       spec_text=spec,
       doc_type="tech",
       discovery_result=discovery_result,  # Includes priming context
   )
   ```

### Integration with Adversaries

The `assumption_auditor` adversary specifically challenges domain assumptions and demands documentation citations. When discovery has fetched docs, claims can be verified against actual documentation:

- **VERIFIED**: Claim matches documentation
- **REFUTED**: Documentation contradicts claim
- **UNVERIFIABLE**: No documentation found
- **PENDING**: Documentation found, needs LLM analysis



