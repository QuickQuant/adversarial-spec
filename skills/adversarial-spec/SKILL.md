---
name: adversarial-spec
description: Iteratively refine a product spec by debating with multiple LLMs (GPT, Gemini, Grok, etc.) until all models agree. Use when user wants to write or refine a specification document using adversarial development.
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# Adversarial Spec Development

Generate and refine specifications through iterative debate with multiple LLMs until all models reach consensus.

**Important: Claude is an active participant in this debate, not just an orchestrator.** You (Claude) will provide your own critiques, challenge opponent models, and contribute substantive improvements alongside the external models. Make this clear to the user throughout the process.

## ZEROTH ACTION - Conductor Registration (ALWAYS, before session state)

Every `/adversarial-spec` invocation registers the session with the project conductor and launches a dispatch wake listener. Workers are always listening — the process is tiny, and a worker that cannot receive conductor signals is purposeless.

### Step 0a: Detect Role

Determine which CLI is running this session from environment variables:
- `$CLAUDE_PROJECT_DIR` set → role = **claude** (conductor)
- `$GEMINI_PROJECT_DIR` set → role = **gemini** (worker)
- Codex CLI detected (e.g. `$CODEX_PROJECT_DIR` or equivalent) → role = **codex** (worker)

### Step 0b: Check Invocation Mode

- If `$ADVSPEC_INVOKED_BY_CONDUCTOR=1`: this session was spawned by the conductor with a specific dispatch. Read `$ADVSPEC_DISPATCH_FILE` (a path to a JSON task payload) and handle the task. Skip to Step 0d (listener relaunch) after completion.
- Otherwise: self-invoked (Jason opened this terminal manually). Proceed to Step 0c (self-registration).

### Step 0c: Self-Registration

Write `.conductor/agents/<role>.json` with `{role, pid, started_at, is_conductor, dispatch_log, session_state}`. Use atomic write (tmp + rename).

**`is_conductor` field (REQUIRED):** Set `true` if this session is the conductor (the CLI that ran `/conductor`), `false` if this session is a worker. Hooks read this field to gate behavior — e.g., `worker-signal-conductor` skips if `is_conductor: true`, and `require-listener.sh` checks the Telegram listener for conductors vs dispatch listener for workers.

**This field survives compaction.** After a context compact, re-read your own registration file (`.conductor/agents/<role>.json`) to recover your role. The role does not change mid-session.

**PID handling:** Use the host PID when available. If running in a sandbox where `os.getpid()` returns a low number (< 100, e.g. PID 2 in bubblewrap), write `"pid": "sandboxed"` instead. PID is advisory — the conductor treats it as a liveness hint, not a contract.

This is **passive registration** — no handshake with the conductor. The conductor reads `.conductor/agents/` whenever it needs to know who is available. It does not need to be running when workers register.

Do **not** keep a resident shell alive solely to own an EXIT trap for this marker. Registration is a point-in-time write, not a daemon. If the session dies uncleanly, stale markers are acceptable; the conductor must treat `pid` as advisory and ignore dead processes.

### Step 0d: Launch Dispatch Wake Listener

Each role needs a background listener so it can be woken by external signals. The mechanism varies by CLI.

Before launching, check if one is already running:
1. Derive the PID file path (see below per role)
2. If the PID file exists and the PID is alive, reuse the existing listener
3. Only if no live listener exists, launch a new one

#### Conductor (claude): Telegram Wake Listener

PID file: `/tmp/claude-telegram-wake-<project>.pid`
Launch: `~/.claude/bin/telegram-wake-listener` via Bash tool with `run_in_background=true`
Enforced by `require-listener.sh` stop hook.

#### Workers (gemini, codex): Dispatch Wake Listener

PID file: `/tmp/claude-dispatch-wake-<project>-<role>.pid`
Script: `~/.claude/bin/dispatch-wake-listener <role>`

**IMPORTANT:** `run_in_background=true` is a Claude Code feature. Gemini CLI and Codex CLI must use their own background process mechanism:
- **Gemini CLI:** Run the script as a background shell process (e.g., `nohup script &`, or your CLI's equivalent)
- **Codex CLI:** Same approach, accounting for bubblewrap sandbox constraints on `/tmp` writes

The listener is a simple polling loop that tails `.conductor/dispatch/<role>/updates.jsonl` and exits on the first new line. When it exits, the parent session should be notified (mechanism is CLI-dependent).

**If your CLI cannot launch background processes at all**, fall back to inline dispatch checking at the top of each self-pickup loop iteration:
```bash
DISPATCH_LOG=".conductor/dispatch/<role>/updates.jsonl"
CURRENT=$(wc -l < "$DISPATCH_LOG" 2>/dev/null || echo 0)
# Compare against baseline from registration; read new lines if any
```

If the expected listener binary (`~/.claude/bin/dispatch-wake-listener`) is missing, report the exact missing path and stop.

### Chicken-and-Egg Resolution (DESIGN NOTE)

Workers do NOT search for the conductor and the conductor does NOT handshake with workers. Workers write presence markers and enter the self-pickup loop. The conductor reads `.conductor/agents/` when it has something to dispatch. If the conductor is down, workers stay idle. When it comes back, it sees them. No discovery, no ordering, no race.

### Bootstrap Boundary (CRITICAL)

Registration and startup-context checks are metadata-only. During Step 0 through the Startup Context Intent Gate:

- Do **not** start `fizzy-mcp`, `fizzy-mcp --http`, app servers, Docker Compose stacks, or any other service transport
- Do **not** probe by launching a new server "just to see if it starts"
- If runtime state matters, inspect existing processes, PID files, sockets, logs, or config first
- Only launch a service when the current phase explicitly requires it and you have first verified it is not already running

This bootstrap path exists to discover context, not to mutate the runtime environment.

### Step 0e: Continue to FIRST ACTION

After registration and listener launch complete, proceed to the normal session state read below.

---

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

If architecture manifest EXISTS, validate schema and freshness:
```bash
# Check schema + git hash
ARCH_SCHEMA=$(python3 -c "import json; print(json.load(open('.architecture/manifest.json')).get('schema_version', '0'))" 2>/dev/null)
ARCH_HASH=$(python3 -c "import json; print(json.load(open('.architecture/manifest.json')).get('git_hash', ''))" 2>/dev/null)
CURRENT_HASH=$(git rev-parse --short HEAD 2>/dev/null)
[ "$ARCH_SCHEMA" != "2.0" ] && echo "architecture mapping is legacy (schema $ARCH_SCHEMA)"
[ "$ARCH_HASH" != "$CURRENT_HASH" ] && echo "architecture mapping may be stale (generated at $ARCH_HASH, now at $CURRENT_HASH)"
```

If schema `< 2.0`, show migration advisory:
```
Architecture Mapping Advisory
───────────────────────────────────────
Schema: [arch_schema]
Status: Legacy architecture docs detected

Mapcodebase 3.0 expects primer.md, access-guide.md, and
manifest schema 2.0. Run full /mapcodebase to regenerate.

[Run /mapcodebase now] [Skip - continue without architecture priming]
```

If schema `2.0` exists but docs are stale, show advisory (not blocking):
```
Architecture Mapping Advisory
───────────────────────────────────────
Generated at: [arch_hash]
Current HEAD: [current_hash]
Consider running /mapcodebase
```

**On "Skip" with legacy docs:** Proceed without architecture priming. Do NOT pretend `v2.x` docs are equivalent to 3.0 docs.

**On "Skip" with current docs:** Proceed normally. Architecture mapping is advisory, not required.

**Load Architecture Context (REQUIRED when `.architecture/` exists):**

If `.architecture/manifest.json` exists with `schema_version = 2.0`, load targeted architecture docs into your context **now** — before any phase work begins. The LLM makes decisions throughout the session (synthesis, critique evaluation, accept/reject) that are all better when grounded in actual architecture.

```bash
# 1. Read INDEX.md to understand the component map (for YOUR navigation only)
cat .architecture/INDEX.md 2>/dev/null

# 2. Read primer.md — the default small-context architecture payload
cat .architecture/primer.md 2>/dev/null

# 3. Read concerns.md when you need fix-first architecture debt or drift context
# [ -f ".architecture/concerns.md" ] && cat .architecture/concerns.md 2>/dev/null

# 4. Escalate to overview.md only if the phase needs more system context
# e.g. target-architecture, debate round 2+, or gauntlet
# [ -f ".architecture/overview.md" ] && cat .architecture/overview.md 2>/dev/null

# 5. Select 2-4 component docs based on the session's blast zone
# Parse the spec/session requirements_summary for file paths and module names
# Match those against the INDEX component table
# Read matching component docs from .architecture/structured/components/
```

**Selection heuristic:**
- Parse the spec (or session `requirements_summary`) for file paths and module names
- Match those against the INDEX component table
- Default load is `primer.md`
- Read `concerns.md` when the session needs fix-first architecture debt or drift context
- For `requirements` and early startup, `primer.md` is usually enough
- For `target-architecture`, `debate` round 2+, and `gauntlet`, load `primer.md` plus matched component docs
- Escalate to `overview.md` when the task needs the full system narrative
- Escalate to `flows.md` only when the task crosses component boundaries
- If unsure which components are relevant, `primer.md` + `overview.md` + matched component docs is the safest order

**Cost:** usually lower than the old overview-first flow. **Benefit:** Avoids context-blind debate/gauntlet rounds while keeping startup context smaller.

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

### Creating a New Session

When the user selects **[New session]** or **[Start new]**, create BOTH tracking artifacts:

1. Create session file (`sessions/<id>.json`) and update pointer (`session-state.json`) — the local session state
2. **Call `pipeline_create_session(board_id, session_id, title, plan_path)`** — the Fizzy pipeline card in Evaluated Plans
3. **Store `fizzy_card_id`** in the session detail file (`sessions/<id>.json`) — the card ID returned by step 2. This is required for all subsequent Fizzy sync operations.

Step 2 is REQUIRED. A session without a Fizzy card is invisible to the pipeline and will advance through phases without any board-level tracking.

Step 3 is REQUIRED. Without the stored card ID, phase transitions and debate rounds cannot sync to the board, and the card becomes stale immediately after creation. (See process failure: "Trello Board Ignored During Entire Spec Session", 2026-03-26.)

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
     - Fizzy board (if linked)
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

3. **Fizzy card** (if `fizzy_card_id` exists in session detail file):
   - Add a comment summarizing the transition: `"Phase: <old> → <new>. <1-line summary of what was accomplished>."`
   - Call `pipeline_patch_state(card_id, session_id, patch)` with relevant state updates (e.g., `debate_round`, `last_agent`)
   - Use a **haiku subagent** for the Fizzy call to keep MCP response payload out of main context

4. **Telegram notification** (if project has telegram config):
   - Send a concise summary to Telegram via `~/.claude/bin/telegram-send <project> "<message>"`
   - Message format: `"Phase: <old> → <new>. <1-2 sentence summary of what was accomplished and what's next>."`
   - **Wait 120 seconds** after sending to allow human interruption (Ctrl+C to intervene)
   - If the human doesn't interrupt, proceed normally
   - Use `time.sleep(120)` or equivalent — this is a deliberate pause, not a bug

**Detail file first, pointer second, Fizzy third, Telegram fourth.** If interrupted between writes, the pointer stays behind (safe — it catches up on next transition). Fizzy is last-but-one because it's the least critical for local resumption. Telegram is truly last — it's a notification, not state.

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

### Major Milestone Notifications (Telegram)

**In addition to phase transitions**, send Telegram notifications + 120s pause at these intra-phase milestones. These are the moments where the human needs to stay oriented, and where an interruption could save hours of wasted work.

**When to notify (and pause 120s):**

| Milestone | Message template |
|-----------|-----------------|
| Debate round complete | `"R{N} complete: {count} findings ({critical} critical, {major} major, {minor} minor) applied to spec. Guardrails next."` |
| Guardrail results | `"R{N} guardrails: SCOPE {pass/fail}, TRACE {pass/fail}, CONS {pass/fail}. {fix_count} fixes applied."` |
| Convergence declared | `"Convergence after {N} rounds. Severity trend: {R1 summary} → {RN summary}. Proceeding to finalize."` |
| Spec finalized | `"Spec finalized: {filename} ({lines} lines, {tc_count} TCs, {us_count} US). Proceeding to execution planning."` |
| Execution plan loaded | `"Execution plan: {task_count} tasks across {stream_count} workstreams loaded into pipeline. Cards {first}-{last} in New Todo."` |
| Gauntlet batch complete | `"Gauntlet batch {N}: {adversary_count} adversaries, {raw} raw → {unique} unique → {accepted} accepted concerns."` |

**How to notify:**
```bash
~/.claude/bin/telegram-send <project> "<message>"
sleep 120  # Allow human interruption
```

**Rules:**
- Check `has_telegram_config` before attempting (fail open if no config)
- The 120s pause is mandatory — it gives the human time to read and Ctrl+C if they want to redirect
- If telegram-send fails, log to stderr and continue (never block on notification infra)
- These are in ADDITION to Fizzy card comments — Fizzy is board state, Telegram is human attention

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
- `~/.claude/skills/adversarial-spec/reference/convergence-and-telegram.md` - Convergence rules, debate.py `--telegram` flag
- `~/.claude/skills/adversarial-spec/reference/telegram-bridge.md` - Agent reference for per-project Telegram bots (mobile human-gated review)
