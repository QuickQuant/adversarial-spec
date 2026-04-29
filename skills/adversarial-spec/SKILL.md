---
name: adversarial-spec
description: Iteratively refine a product spec by debating with multiple LLMs (GPT, Gemini, Grok, etc.) until all models agree. Use when user wants to write or refine a specification document using adversarial development.
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# Adversarial Spec Development

Refine specs through iterative debate with multiple LLMs until all agree.

**Claude is a participant, not just an orchestrator** — critique, challenge, contribute alongside the external models. Say so to the user.

## ZEROTH ACTION — Conductor Registration (before session state)

Every invocation registers with the project conductor and launches a wake listener. Tiny cost; a worker that can't be signaled is pointless.

### 0a: Role
Env-var detection: `$CLAUDE_PROJECT_DIR` → **claude** (conductor); `$GEMINI_PROJECT_DIR` → **gemini**; Codex-style env → **codex**. Workers otherwise.

### 0b: Invocation Mode
If `$ADVSPEC_INVOKED_BY_CONDUCTOR=1`: read `$ADVSPEC_DISPATCH_FILE` (JSON task payload), handle, then 0d. Otherwise self-invoked → 0c.

### 0c: Self-Registration
Write `.conductor/agents/<role>.json` with `{role, pid, started_at, is_conductor, dispatch_log, session_state}` via atomic tmp+rename.

- `is_conductor`: `true` for the CLI that ran `/conductor`, else `false`. Hooks gate behavior on this field; it survives compaction (re-read your own file to recover role).
- PID: host PID, or `"sandboxed"` if `os.getpid()` < 100 (bubblewrap). PID is advisory.
- Passive — no handshake. Stale markers OK. Don't keep a shell alive just to own an EXIT trap.

### 0d: Wake Listener
Reuse if PID file exists and PID alive; only launch if none.

- **Conductor (claude):** `/tmp/claude-telegram-wake-<project>.pid`, launch `~/.claude/bin/telegram-wake-listener` with `run_in_background=true`. Enforced by `require-listener.sh` stop hook.
- **Workers (gemini/codex):** `/tmp/claude-dispatch-wake-<project>-<role>.pid`, script `~/.claude/bin/dispatch-wake-listener <role>`. Claude's `run_in_background` is Claude-only; Gemini/Codex use native backgrounding (`nohup … &` etc.), accounting for bubblewrap `/tmp` constraints.
- Listener tails `.conductor/dispatch/<role>/updates.jsonl` and exits on first new line.
- Can't background at all? Inline-check the dispatch log at the top of each pickup iteration (compare `wc -l` to baseline).
- Missing binary → report the path and stop.

### Chicken-and-Egg (design note)
Workers don't search for the conductor; conductor doesn't handshake. Workers drop a marker and self-pickup. Conductor reads `.conductor/agents/` when it has work. No discovery, no race.

### Bootstrap Boundary
Registration and startup checks are metadata-only. Do NOT start fizzy-mcp, app servers, Docker stacks, or probe by launching services. Inspect existing processes/PIDs/sockets/logs first. Only start a service when the current phase requires it and it isn't already running.

### 0e: Continue to FIRST ACTION.

---

## FIRST ACTION - Read Local Session State

**BEFORE ANYTHING ELSE**, read the pointer:

```bash
cat .adversarial-spec/session-state.json 2>/dev/null
```

### If session-state.json exists:

Pointer fields used on resume: `active_session_id`, `context_name`, `current_phase`, `current_step`, `next_action`, `do_not_ask` (list — RESPECT), `session_stack` (optional).

**Zombie pointer check:** if `sessions/<active_session_id>.json` is missing (branch switch, deletion), warn the user and treat as "no active session."

**Don't read the whole detail file.** It's 400+ lines and holds phase-scoped artifacts (`context_inventory`, `requirements_summary`) that resume doesn't need. The journey now lives in a sibling JSONL (`sessions/<id>.journey.log`) — read on demand only. Pull resume fields from the detail file via `jq`:

```bash
jq -r '{checkpointed_cleanly,current_phase,current_step,fizzy_card_id,spec_path,execution_plan_path,roadmap_path,last_checkpoint,todowrite_snapshot}' \
  .adversarial-spec/sessions/<id>.json
```

Phases that need more (gauntlet → `gauntlet_concerns_path`, finalize → `requirements_summary`) read that one field on demand. Never `cat` the whole file.

**Recent decisions:** if `sessions/<id>.decisions.log` exists, tail ~20 lines. Authoritative "what landed and why it matters." Replaces `git log` / `git show` for orientation. See Decisions Log section.

**Clean-exit check:**
- `checkpointed_cleanly: false` → previous session died mid-work. Warn, offer "Continue from last checkpoint" / "Review what changed."
- `true` or absent → normal flow.

**Mark this session in progress** immediately — set `checkpointed_cleanly: false` via atomic tmp+rename on the detail file. If this session crashes, the next resume sees the flag.

**TodoWrite snapshot:** if `todowrite_snapshot` is a non-empty list, restore TodoWrite from it. Otherwise the Phase Router creates a fresh one. Either way, the phase doc's behavioral rules still apply.

**Context Intent Gate:** if `session_stack` has multiple entries, or the pointer drifts from the most-recently-updated session file, or the user's recent messages suggest a different workstream → ask before proceeding:

```
Context Intent Check
Active: [context_name] ([id])
Recent alt: [alt_context_name] ([alt_id])

Did we switch? [Continue active] [Switch to recent] [Show sessions]
```

Never auto-switch. On switch: atomically update pointer (`active_session_id`, `active_session_file`, `context_name`, `current_phase`, `current_step`, `next_action`, `updated_at`) and append a `resume` event to the target session's journey log.

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
5. Append to journey log: `{"time": "ISO8601", "event": "Generated manifest retroactively", "type": "maintenance"}`

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
     - `sessions/<id>.journey.log` (JSONL, reconstruct from checkpoints if possible)
     - `requirements_summary.completed_work` (from legacy `completed_work` string)
     - `extended_state` (preserve rich fields like `gauntlet_results`, `dev_instance`, etc.)
   - Create `specs/<project>-roadmap/manifest.json` if roadmap data can be inferred from:
     - Tasks MCP (extract milestones from completed/pending tasks)
     - Fizzy board (if linked)
     - Checkpoint files (extract user stories, test cases)
   - Update session-state.json to v1.3 pointer format
   - Append to journey log: `{"time": "ISO8601", "event": "Migrated from v1.1 to v1.3", "type": "migration"}`

3. **Migration checklist:**
   - [ ] Session file created with all legacy data preserved
   - [ ] manifest.json created (even if partial)
   - [ ] session-state.json updated to v1.3 pointer
   - [ ] Rich fields preserved in `extended_state`
   - [ ] Journey log reconstructed from checkpoints (JSONL)

4. **After migration:** Proceed with normal v1.3 flow (show path context, offer options)

### Session State Rules (CRITICAL):

- If `do_not_ask` exists, DO NOT ask those questions
- If `next_action` exists, DO that action
- The session state tells you exactly what to do - follow it
- `do_not_ask` is ALWAYS a list - if you see a string, it's legacy format

---

## Process Discipline (All Phases)

**NEVER abandon the structured process** on tangential questions or "quick fixes":

1. Check scope — part of this session?
2. Use TodoWrite for ALL work, even small investigations.
3. Stay targeted — 2-3 queries max for ad-hoc debugging.
4. Root causes, not band-aids.
5. Propose through process — update session state, get approval.

**Red flags:** 10+ turns without TodoWrite updates; manually setting values to make things "look right"; multiple restarts without understanding why; "let me just quickly…" outside task context.

When in doubt: update session state and use TodoWrite.

### Pipeline-card fence (critique + gauntlet)

**If the session has a `fizzy_card_id`, NEVER invoke `debate.py critique` or `debate.py gauntlet` directly.** All round dispatches go through the Fizzy pipeline tools (`pipeline_begin_debate_round` → `pipeline_dispatch_single_agent_debate` → `pipeline_register_debate_agent_return` → `pipeline_advance_debate_round`). Standalone runs bypass the Test-Spec Sync gate — that is exactly how `tests-pseudo.md` drifted from v2 through v7 without a single staleness warning.

`debate.py` now enforces this itself: `critique` and `gauntlet` require `--pipeline-card <card_id>`, or `--pipeline-card IntentionalOverride --override-reason '<≥50 chars>'`. The script also runs a staleness check comparing `spec_path` mtime vs `tests_pseudo_path` mtime from the session detail file; stale → exit 2 unless `--accept-tests-stale` is passed. Overrides and stale-accepts are logged to `sessions/<id>.decisions.log`.

When the pipeline rejects a round (sequence mismatch, checklist missing, active-round conflict), see `phases/03-debate.md` Step 4 "No fallback" — reconcile via pipeline tools or `pipeline_patch_state` with a `process_failure_path` note. Do not reach for `debate.py` as the escape hatch.

---

## Phase Router — Read ONLY What You Need

Based on `current_phase`, read the matching phase file:

| Phase | File to Read |
|-------|--------------|
| No session / New work | `~/.claude/skills/adversarial-spec/phases/01-init-and-requirements.md` |
| requirements | `~/.claude/skills/adversarial-spec/phases/01-init-and-requirements.md` |
| roadmap | `~/.claude/skills/adversarial-spec/phases/02-roadmap.md` |
| debate | `~/.claude/skills/adversarial-spec/phases/03-debate.md` |
| target-architecture | `~/.claude/skills/adversarial-spec/phases/04-target-architecture.md` |
| gauntlet | `~/.claude/skills/adversarial-spec/phases/05-gauntlet.md` |
| finalize | `~/.claude/skills/adversarial-spec/phases/06-finalize.md` |
| middleware-creator (optional) | `~/.claude/skills/adversarial-spec/phases/middleware-creator.md` — runs after `finalize` when `middleware-candidates.json` exists and the user chooses to materialize shared middleware before normal implementation pickup. See note below. |
| execution | `~/.claude/skills/adversarial-spec/phases/07-execution.md` |
| implementation | `~/.claude/skills/adversarial-spec/phases/08-implementation.md` |
| complete | Ask user: "Start new work? Or continue with follow-up?" |

**Use the Read tool.** Don't load all phases at once.

**Re-read discipline.** Read the phase doc only when:
1. First activation of the phase (just transitioned in).
2. A phase transition is happening this turn (load the TARGET doc).
3. Session compacted, or the phase doc was edited since last read.

If `current_phase` is unchanged since the prior checkpoint and you've seen the doc in a recent session, skip the re-read. Canonical rules live in the active TodoWrite + the pointer's `next_action`. Re-reading a 200–400-line phase doc every resume is a silent tax.

**TodoWrite source priority:**
1. If `todowrite_snapshot` exists → restore TodoWrite from it (already done during the Clean-Exit step).
2. Else → create fresh TodoWrite from the phase doc's `TaskCreate([...])` template.

Either way, the phase doc's instructions and gate rules still apply — the snapshot only replaces TodoWrite init.

**Multi-agent TodoWrite rule (CRITICAL):** in phases where multiple LLMs work the same board (Phase 8 implementation), TodoWrite items MUST be phase-scoped activities, never specific card IDs or commit hashes. The Fizzy pipeline is the only authoritative "what's next" — `pipeline_do_next_task` returns live state. Snapshotted card-specific todos go stale the moment another agent touches the board.

- Bad: `Review W1-7 card #1403 (codex impl 6c4bb3d)`.
- Good: `Process next review card from pipeline`, `Handle failed-review cards first`, `Pick up next New Todo when review lane empty`.

Card IDs and commit hashes belong in the live transcript, not the persisted snapshot.

**Router order:**
```
requirements → roadmap → debate → target-architecture → gauntlet → finalize → middleware-creator? → execution → implementation → complete
```

`middleware-creator?` is optional, slotted between `finalize` and `execution`. It runs iff Phase 4 produced `middleware-candidates.json` AND the user chose to materialize shared middleware before normal pickup. Empty list or user skip → `finalize → execution` directly.

**Operational:** middleware fanouts require typed Fizzy source task cards and existing test-suite paths. If `fizzy-plan.json` isn't yet loaded, pass through Phase 7 far enough to create/load the execution cards, then return to `middleware-creator`. Don't bypass with raw `add_card` or direct card moves — use the Fizzy middleware pipeline tools.

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

1. Read the TARGET phase file from the router — do not continue with the current one.
2. Follow the target phase's entry protocol (each has specific startup steps).
3. Do not apply the previous phase's commands/tools. E.g., no `debate.py critique` during the gauntlet.

**Why:** Feb 2026 failure — LLM stayed in "debate mode" on a gauntlet request, ran `debate.py critique` R4 instead of `05-gauntlet.md`'s distinct Arm-Adversaries / persona-attack pipeline.

### CRITICAL: Phase Transition Rules

**NEVER mark `complete` without these gates:**

1. **finalize → execution**: ask "Spec is finalized. Generate an execution plan now?"
   - Yes → read `phases/07-execution.md`, create plan.
   - No → mark complete with note `"execution skipped by user"`.

2. **execution → implementation/complete**: create the plan directly using `phases/07-execution.md`. `debate.py execution-plan` is deprecated (Feb 2026, Option B+). If the plan has 0 actionable tasks, WARN before proceeding.

**Why:** sessions were jumping gauntlet → complete, skipping execution and losing the concern-to-task linkage.

**Brainquarters** (detected by `projects.yaml`): `TaskList(list_contexts=True)` shows cross-project contexts.

### Phase Transition Protocol (REQUIRED)

**Every phase transition must update BOTH files atomically, in order:**

1. **Detail file** (`sessions/<id>.json`) — first:
   - Set `current_phase`, `current_step`, `updated_at` (ISO 8601).
   - Append to journey log (`sessions/<id>.journey.log`, JSONL): `{"time":"ISO8601","event":"Phase transition: <old> → <new>","type":"transition"}`. See "Journey Log" below.

2. **Pointer file** (`session-state.json`) — second:
   - Set `current_phase`, `current_step`, `next_action`, `updated_at`.

3. **Fizzy card** (if `fizzy_card_id` present) — third:
   - Add comment: `"Phase: <old> → <new>. <1-line accomplishment>."`
   - Call `pipeline_patch_state(card_id, session_id, patch)` with relevant state updates (`debate_round`, `last_agent`, etc.).
   - Use a **haiku subagent** to keep MCP payload out of main context.

4. **Telegram** (if project has telegram config) — fourth:
   - `~/.claude/bin/telegram-send <project> "Phase: <old> → <new>. <1-2 sentence summary of what/next>."`
   - **Wait 120 seconds** (`time.sleep(120)`) — deliberate pause so the human can Ctrl+C to redirect. Not a bug.

**Order matters.** Interrupted mid-sequence: pointer catches up on next transition (safe); Fizzy isn't load-bearing for local resume; Telegram is notification, not state.

**Artifact path fields** — set in detail file at these transitions:

| Transition | Field | Value |
|------------|-------|-------|
| roadmap → debate | `roadmap_path` | `"roadmap/manifest.json"` or `"inline"` |
| target-architecture → gauntlet | `target_architecture_path` | Path to architecture doc (e.g., `"specs/<slug>/target-architecture.md"`) |
| gauntlet → finalize | `gauntlet_concerns_path` | Path to saved concerns JSON (e.g., `".adversarial-spec/gauntlet-concerns.json"`) |
| finalize → execution | `spec_path` | Path to written spec (e.g., `"spec-output.md"`) |
| finalize → execution | `manifest_path` | Path to spec manifest if created (e.g., `"specs/<slug>/manifest.json"`) |
| execution → implementation | `execution_plan_path` | Path to written execution plan (e.g., `".adversarial-spec/specs/<slug>/execution-plan.md"`) |
| any → complete | `completed_at` | ISO 8601 timestamp |

**Non-artifact transitions** (debate → gauntlet, etc.) still MUST dual-write `current_phase` and `current_step` to both files. Every phase change syncs both — no exceptions. Both writes use atomic tmp+rename.

**Backward compatibility:** legacy detail files missing `current_phase` → add it, don't error.

### Major Milestone Notifications (Telegram)

Send Telegram + 120s pause at these intra-phase milestones — they're the moments where an interruption saves hours:

| Milestone | Message template |
|-----------|-----------------|
| Debate round complete | `"R{N} complete: {count} findings ({critical} critical, {major} major, {minor} minor) applied to spec. Guardrails next."` |
| Guardrail results | `"R{N} guardrails: SCOPE {pass/fail}, TRACE {pass/fail}, CONS {pass/fail}. {fix_count} fixes applied."` |
| Convergence declared | `"Convergence after {N} rounds. Severity trend: {R1 summary} → {RN summary}. Proceeding to finalize."` |
| Spec finalized | `"Spec finalized: {filename} ({lines} lines, {tc_count} TCs, {us_count} US). Proceeding to execution planning."` |
| Execution plan loaded | `"Execution plan: {task_count} tasks across {stream_count} workstreams loaded into pipeline. Cards {first}-{last} in New Todo."` |
| Gauntlet batch complete | `"Gauntlet batch {N}: {adversary_count} adversaries, {raw} raw → {unique} unique → {accepted} accepted concerns."` |

**How:**
```bash
~/.claude/bin/telegram-send <project> "<message>"
sleep 120
```

**Rules:**
- Check `has_telegram_config`; fail open if missing.
- 120s pause is mandatory.
- If `telegram-send` fails, log to stderr and continue — never block on notification infra.
- These are additive to Fizzy card comments. Fizzy = board state; Telegram = human attention.

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

## Alignment Prompts

Offer at **checkpoint**, **phase transition**, and **startup**:

```
Alignment Check
Goal: [context.goal]   Phase: [current_phase]
Still aligned? [Yes] [Refocus] [Skip]
```

- **Yes / Skip:** do nothing. These are UX-only; don't write journey noise ("confirmed"/"skipped" are identical across runs and nobody reads them).
- **Refocus:** the real state change. Mutate `context.goal` on the detail file and append to `goal_history: [{at, from, to, why?}]`. That trail is the artifact — not a generic journey event.

---

## Decisions Log (`sessions/<id>.decisions.log`)

A plain-text append-only ledger of "what landed and why it matters," written one entry per pipeline task completion (and at major phase milestones). Replaces `git log` / `git show` for session resume — gives fresh agents context without re-reading diffs.

**When to append:**
- Immediately after a successful `pipeline_complete_task` (card moves to Review).
- At phase transitions that carry material consequences (spec v4 → v5, accepted gauntlet concern batch, architecture spine locked).
- When a user decision forecloses an option (e.g., "GLM deferred").

**Line format (plain text, one per line):**
```
<ISO8601> [<card_id|phase|decision>] <what landed> — <why it matters>
```

**Append pattern:**
```bash
printf '%s [%s] %s — %s\n' \
  "$(date -u +%FT%TZ)" "<card_id|phase|decision>" "<what>" "<why>" \
  >> .adversarial-spec/sessions/<id>.decisions.log
```

**Phase 8 integration:** after `pipeline_complete_task(...)` returns success, write one line. Keep it scannable — ≤120 chars preferred. Commit hash goes in the "what" field; card ID in the bracket.

**Read pattern (resume):**
```bash
tail -20 .adversarial-spec/sessions/<id>.decisions.log
```

**Rules:**
- Plain text (NOT JSONL) — humans read it, grep scans it.
- Append only. Never rewrite.
- One line per decision. Multi-line reasoning goes in retrospectives.
- Omit if the commit message already says everything.

---

## Journey Log (`sessions/<id>.journey.log`)

Journey is a **JSONL file**, not a JSON-array field inside the session detail. One event per line, appended — never rewritten.

**Append pattern:**
```bash
printf '%s\n' "$(jq -nc --arg time "$(date -u +%FT%TZ)" \
  '{time:$time, event:"<event>", type:"<transition|artifact|create|maintenance|decision|resume>"}')" \
  >> .adversarial-spec/sessions/<id>.journey.log
```

**Why separate file:** the array grew to 80+ entries (~10KB) on long sessions and bloated every targeted `jq` read of the detail file. JSONL means append is O(1) and resume skips the log entirely unless asked.

**Read pattern (recent events):**
```bash
tail -5 .adversarial-spec/sessions/<id>.journey.log | jq .
```

Read only when the user asks "what happened?" or orphan/context detection needs event history. Never load on normal resume.

**Phase 4 extended schema** (`idempotency_key`, `event_id`, `release_id`) writes to the same log; dedup by `idempotency_key` still applies — check the log before appending.

**Legacy sessions** (pre-migration) with `journey` inside the JSON: run `.adversarial-spec/scripts/migrate-journey-to-log.py` once to extract.

---

## Pre-Checkpoint Checklist (REQUIRED)

`/checkpoint` only handles pointer/session state — surrounding process is your responsibility.

```
Pre-Checkpoint Verification
[ ] Deliverables on disk — debate output, execution plans, specs, gauntlet concerns (not conversation-only)
[ ] Alignment check offered
[ ] Orphan detection run
[ ] TodoWrite current and phase-scoped (no stale card IDs)
Proceed? [Y/n]
```

Fix failing checks before running `/checkpoint`.
- Debate output → `.adversarial-spec-checkpoints/` (`debate.py critique` auto-saves; manual synthesis writes the file yourself).
- Execution plans → `.adversarial-spec/specs/<slug>/execution-plan.md`.

**Why:** checkpoint exits 0 even with missing deliverables. Context switches after checkpoint destroy conversation-only output permanently.

---

## Context Budget Gates (CRITICAL)

**Checkpoint-First Rule:** after writing a final spec version or completing a context-heavy phase, checkpoint IMMEDIATELY. Reports, MEMORY.md updates, retros — all in the next session.

| Transition | Gate |
|-----------|------|
| debate → gauntlet | Spec draft written this session → checkpoint before the gauntlet. It generates massive tool output; fresh context is essential. |
| gauntlet → finalize | Full gauntlet round (8+ adversaries) run this session → checkpoint before synthesizing the final spec. |
| any → checkpoint | Final deliverable written → checkpoint is your NEXT action. Not reports, MEMORY, or failure analysis. |

**Danger zone:** spec draft AND full gauntlet round both done this session → checkpoint immediately, no additional work.

---

## TaskOutput Anti-Patterns (CRITICAL)

These have caused session death:

1. **Never Read the output file after a blocking `TaskOutput`.** `TaskOutput(block=true)` already returns the full result — re-reading doubles the token cost.
2. **Never re-launch a hook-rejected command.** Switch tools or fix the command. Do NOT read hook source to diagnose.
3. **Never retry with incrementally larger timeouts.** Know the requirement up front: Codex calls need `timeout=900000` minimum. Use background mode for any long-running model call.
4. **After launching background tasks, probe at ~45s with `block=false`** to catch quota/crash errors before committing to a full-timeout wait.

---

## File Discipline & Orphan Detection

At checkpoint/resume, scan project root for orphans.

**Allowlist (never flag):** README.md, CLAUDE.md, AGENTS.md, CONTRIBUTING.md, CHANGELOG.md, CODE_OF_CONDUCT.md, SECURITY.md, GOVERNANCE.md, LICENSE(.md), pyproject.toml, package.json, Makefile.

**Heuristics:** root `*.md` not in allowlist; filename contains `YYYYMMDD`; filename contains `spec`/`checkpoint`/`session`/`notes`/`issues`.

**On hit, prompt:**
```
Found potential orphans:
• [filename]  →  suggest: .adversarial-spec/issues/
Move? [Y/n/skip all]
```

**Never auto-move.** Always confirm.

---

## Session ID Generation

Format: `adv-spec-YYYYMMDDHHMM-<slug>`.

**Slug:** lowercase context; non-alphanumeric → `-`; collapse runs of `-`; trim; cap 32 chars.
Example: `Fix: User Login (Auth)` → `adv-spec-202601311430-fix-user-login-auth`.

---

## Atomic Writes (CRITICAL)

All JSON writes: write to `<path>.tmp`, then `rename` to target (atomic on POSIX). Prevents corruption on Ctrl+C.

---

## Reference Files (Load On-Demand)

- `reference/document-types.md` — spec types (product/technical/full/debug)
- `reference/advanced-features.md` — focus modes, personas, profiles
- `reference/script-commands.md` — `debate.py` CLI reference
- `reference/gauntlet-details.md` — adversarial gauntlet details
- `reference/convergence-and-telegram.md` — convergence rules, `--telegram` flag
- `reference/telegram-bridge.md` — per-project Telegram bot setup (mobile human-gated review)
