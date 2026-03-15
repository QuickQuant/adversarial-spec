# Brainquarters Handover: Context Exhaustion Fixes (Remaining)

**Date:** 2026-02-23
**Source:** `/home/jason/PycharmProjects/wavelets/.adversarial-spec/issues/2026-02-23-binance-backfill-session-context-exhaustion.md`
**What adversarial-spec already fixed:** See below. This document covers what Brainquarters needs to handle via CLAUDE.md changes across projects.

---

## What adversarial-spec Already Fixed

1. **`debate.py gauntlet-adversaries` bug** — `desc.strip()` crashed with AttributeError because `desc` is an `Adversary` object, not a string. Fixed to `desc.persona.strip()`. Also improved output to show all adversary categories (pre-gauntlet, regular, final boss) with prefixes.

2. **Context Budget Gates** — Added to `SKILL.md`: mandatory checkpoint before starting gauntlet if a spec draft was written in the same session. Phase transition gates table.

3. **Checkpoint-First Rule** — Added to `SKILL.md`: after writing final deliverable, checkpoint is the NEXT action. No reports, no MEMORY.md updates first.

4. **TaskOutput Anti-Patterns** — Added to `SKILL.md`: never re-read output files after blocking TaskOutput, never investigate hook source on rejection, never retry with incremental timeouts.

5. **Gemini Rate Limit Staggering** — Added to `04-gauntlet.md`: max 2 concurrent Gemini calls, 60s gaps between batches, early failure detection with `block=false` checks.

6. **Adversary Name Mapping** — Added to `04-gauntlet.md`: full quick-reference table with exact CLI names, prefixes, and roles. Explicit instruction to never invent names.

---

## What Brainquarters Needs to Fix

These are cross-project behavioral issues that should be addressed in CLAUDE.md files (or core-practices.md / project-practices.md) across all projects that use adversarial-spec sessions.

### 1. Fix `force_flag_defense.py` False Positive on `test -f` / `[ -f`

**File:** `.claude/hooks/force_flag_defense.py` (Brainquarters owns hooks)
**Issue:** The `-f` regex in `FORCE_PATTERNS` matches `test -f` and `[ -f` bash commands, which use `-f` for "file exists" checks, not as a force flag.
**Fix:** Add to `FALSE_POSITIVE_COMMANDS`:
```python
r"test\s+-f\b",                    # test -f (file exists check)
r"\[\s+-f\b",                      # [ -f (file exists check)
r"\[\[\s+-f\b",                    # [[ -f (file exists check)
```

### 2. Hook Rejection Behavior (CLAUDE.md guidance)

**Problem:** When a hook blocks a command, the LLM investigates why — reading hook source code, analyzing regex patterns — wasting ~2,200 tokens. This happened with `force_flag_defense.py` and will happen with any hook.
**Fix:** Add to CLAUDE.md (all projects with hooks):
```
When a hook blocks a Bash command, switch tools immediately (e.g., use
Glob/Read instead of shell test commands). Do NOT read hook source files
to diagnose why — hooks are a solved problem. The error message tells you
what to change. If error messages are not verbose enough, solve that by
making the error message sufficiently descriptive.
```

### 3. Codex Timeout Requirements (CLAUDE.md guidance)

**Problem:** Codex calls were launched 3 times with incrementally higher timeouts (300k, 600k) before the hook allowed 900k. Each rejected attempt wastes tokens.
**Fix:** Add to CLAUDE.md (all projects using Codex):
```
Codex CLI timeout requirements (enforced by codex-timeout-guard hook):
- --codex-reasoning low:    timeout=900000 (15 min)
- --codex-reasoning medium: timeout=900000 (15 min)
- --codex-reasoning high:   timeout=900000 (15 min)
Always use background mode for Codex calls.

OR

when the hook blocks, print this.
```

### 4. TaskOutput Anti-Pattern (CLAUDE.md guidance)

**Problem:** After `TaskOutput(block=true)` returned full debate output (~8,326 tokens), the LLM then Read the same output file, adding ~4,750 redundant tokens.
**Fix:** Add to CLAUDE.md (all projects):
```
TaskOutput(block=true) returns the full result into context.
NEVER follow a blocking TaskOutput with Read calls on the same
output file — the data is already in your context.
```

### 5. Background Task Early Failure Detection (CLAUDE.md guidance)

**Problem:** Background tasks were launched and then immediately blocked on via `TaskOutput(block=true)`, waiting the full timeout before discovering Gemini rate limit errors.
**Fix:** Add to CLAUDE.md (all projects):
```
After launching background tasks, check with TaskOutput(block=false)
after ~45 seconds to catch immediate failures (quota errors, crashes)
before committing to a 10-minute blocking wait.
```

### 6. MEMORY.md Lessons Discipline (CLAUDE.md guidance)

**Problem:** The Gemini rate-limit lesson was a known issue from prior sessions but wasn't recorded in MEMORY.md until it failed again. Root Cause 4 in the failure report.
**Fix:** Add to CLAUDE.md or core-practices.md:
```
When you discover a repeatable failure pattern (rate limits, tool
misuse, wrong defaults), record it in MEMORY.md IMMEDIATELY in the
same session — not "next time." If the session dies before checkpoint,
the lesson is lost and will be repeated.
```

### 7. Background Task Notification Spam Awareness (CLAUDE.md guidance)

**Problem:** 11 background task completion notifications arrived after results were already consumed, forcing 9 redundant response turns (~2,100 tokens wasted).
**Fix:** Add to CLAUDE.md (all projects):
```
Background task notifications arrive asynchronously and may duplicate
results you already consumed via TaskOutput. When a notification
arrives for a task you already processed, respond with a single
short line: "Already processed." Do not re-summarize results.

Prefer staggered sequential launches over mass parallel launches
to reduce notification spam.
```

The fixes may increase the CLAUDE.md size over the permittable size. discuss this with the user. is this ok? 

---

## Priority Order

1. **Hook fix** (#1) — Blocks `test -f` in all projects, causes cascading waste
2. **Hook rejection behavior** (#2) — Prevents token waste on every hook trigger
3. **Codex timeouts** (#3) — Prevents triple-launch pattern
4. **TaskOutput anti-pattern** (#4) — Prevents double-read pattern
5. **Early failure detection** (#5) — Prevents blocking on dead tasks
6. **MEMORY.md discipline** (#6) — Prevents repeated failures across sessions
7. **Notification spam** (#7) — Mitigation for architectural limitation
