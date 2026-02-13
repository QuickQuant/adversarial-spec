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
- `current_phase`: Where we are (requirements, roadmap, debate, gauntlet, finalize, execution, implementation)
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
| gauntlet | `~/.claude/skills/adversarial-spec/phases/04-gauntlet.md` |
| finalize | `~/.claude/skills/adversarial-spec/phases/05-finalize.md` |
| execution | `~/.claude/skills/adversarial-spec/phases/06-execution.md` |
| implementation | `~/.claude/skills/adversarial-spec/phases/07-implementation.md` |
| complete | Ask user: "Start new work? Or continue with follow-up?" |

**Read the file for your current phase using the Read tool.** Don't load all phases at once.

### CRITICAL: Phase Transition Rules

**NEVER mark a session as `complete` without going through these gates:**

1. **finalize → execution**: After finalize, you MUST ask: "Spec is finalized. Would you like me to generate an execution plan for implementation?"
   - If yes: Read `phases/06-execution.md` and create the plan directly using its guidelines
   - If no: User explicitly declines - only THEN can you mark complete (with note: "execution skipped by user")

2. **execution → implementation/complete**: Create execution plans directly using guidelines in `phases/06-execution.md`. There is no `debate.py execution-plan` command - that pipeline was deprecated (Feb 2026, Option B+).
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
| gauntlet → finalize | `gauntlet_concerns_path` | Path to saved concerns JSON (e.g., `".adversarial-spec/gauntlet-concerns.json"`) |
| finalize → execution | `spec_path` | Path to written spec (e.g., `"spec-output.md"`) |
| finalize → execution | `manifest_path` | Path to spec manifest if created (e.g., `"specs/<slug>/manifest.json"`) |
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
