# CLAUDE.md
<!-- Base: Brainquarters v1.5 | Project: v1.1 | Last synced: 2026-03-21 -->
<!-- Last reviewed: 2026-03-21 | Next review: 2026-04-11 -->
<!-- Target: 60-100 lines | If >100 lines, prune or move to .active_context.md -->

## WHAT: Project & Stack

**adversarial-spec** - Claude Code skill for iterative spec development through multi-model debate.

| Component | Technology |
|-----------|------------|
| Runtime | Python 3.14+ |
| Dependencies | uv, pyproject.toml |
| Tests | pytest |
| Lint | ruff |

**Key paths:**
- `skills/adversarial-spec/` - Skill definition (phases, scripts, reference)
- `~/.claude/skills/adversarial-spec/` - Deployed skill (what Claude Code uses)
- `adversarial-spec-process-failure-report.md` - Process lessons learned

## WHY: Purpose

1. **Iterative refinement** - Generate specs through adversarial debate with multiple LLMs
2. **User story anchoring** - Ensure specs are grounded in user needs (being improved)
3. **Consensus-driven** - Continue debate until all models agree
4. **Process documentation** - Capture lessons learned for continuous improvement

## HOW: Working in This Codebase

### Session Start
```
/tasks              # Check pending improvements (#94-97)
```

### Commands
```bash
uv run pytest                            # Test
uvx ruff check --fix --unsafe-fixes      # Lint
```

### Resuming Work
```
/tasks                    # See work streams and pending tasks
/tasks <context>          # See tasks for specific work stream
```

### Deployment
Changes to `skills/adversarial-spec/` need manual copy to `~/.claude/skills/`:
```bash
cp -r skills/adversarial-spec/* ~/.claude/skills/adversarial-spec/
```

### Current Focus
Process improvements from failure report:
- Task #94: Fix 03-debate.md to USE user stories (high)
- Task #95: Enhance opponent prompts (high)
- Task #96: Require Bootstrap section (medium)
- Task #97: Structure debate rounds (low)

## Guardrails

**Hooks enforce safety** - see `.claude/hooks/`.

Critical rules (enforced by hooks):
- Never log/print API keys or config objects containing secrets
- Never use `git push --force`, `git reset --hard`, `rm -rf`
- Always use `uv run` for Python commands
- **Before exploring a codebase, read `.architecture/INDEX.md` first.** Do not glob/grep for orientation when architecture docs exist.

Token discipline (see `core-practices.md` §8 for rationale):
- Hook blocks a command → switch tools immediately. Do NOT read hook source to diagnose.
- Codex calls → always `timeout=900000`+ and `run_in_background`. Hook enforces minimums.
- `TaskOutput(block=true)` returns full result — never re-read the same output file.
- Background tasks → check `block=false` at ~45s before committing to a blocking wait.
- Failure patterns (rate limits, wrong defaults) → record in MEMORY.md same session.
- Background notification for already-consumed task → reply "Already processed." (one line).

## Multi-Agent Coordination (Claude + Codex)

Two agents work **in parallel on the same branch**. Coordination via `.handoff.md` + Trello.

- **Before picking up a card**: Read `.handoff.md`, update your row, check for file conflicts with the other agent
- **After picking up a card**: Create a TodoWrite (Claude) / update_plan (Codex) for the card's tasks. Last task must be: "Pick up next card, update handoff, create TodoWrite/update_plan with this task as the last task"
- **After every commit**: Update `.handoff.md` review queue, move Trello card → "Review" list, add comment with commit hash
- **Reviews before new work**: Check review queue first — reviewing the other agent's commit takes priority over picking up a new card
- **Before reviewing a commit**: Check `.handoff.md`, `git log`, and the current branch tip to confirm the referenced commit is still the latest commit for that task. Review the specific commit only if it is still current; if superseded, reconcile Trello/`.handoff.md` to the newer reviewed state instead of re-reviewing stale code
- **Don't stall**: If there are pending todos or cards, do not ask "Shall I proceed?" — just do the work
- **Full protocol**: Read `.coordination/PROTOCOL.md`

### Trello Management

Board: `Adversarial Spec` (`69be407deef7267a2cea1feb`) — **always keep cards in sync with actual work state.**

**Board pinning (enforced by hook):** Always pass `boardId="69be407deef7267a2cea1feb"` to all Trello MCP calls. **Never use `set_active_board`** — it changes global state and causes cross-project drift when multiple projects run simultaneously.

**Trello context discipline:** Never bulk-fetch cards from multiple lists in main context — it causes context bloat. Use a subagent to aggregate Trello data and return a summary. Same principle applies to any large MCP response.

| Action | Trello Update |
|--------|--------------|
| Pick up a card | Move → "In Progress", add comment: `Starting: <agent-name>` |
| Commit | Add comment: `<hash> <summary>`, move → "Review" |
| Review LGTM | Move → "Done" |
| Review needs changes | Move → "In Progress", comment with issues |

Commit messages reference the card: `[AS-1] Short description`

## Progressive Disclosure

**This file is minimal by design.** Load context on-demand:

| Need | Action |
|------|--------|
| Process lessons | Read `adversarial-spec-process-failure-report.md` |
| Skill phases | Read `skills/adversarial-spec/phases/` |
| Project patterns | Read `onboarding/project-practices.md` |
| Universal rules | Read `onboarding/core-practices.md` |

---

## Review Trigger

**`/checkpoint` check:** If `Next review` date has passed:
1. Verify this file still matches actual workflows
2. Check line count (target: 60-100, max: 100)
3. Update `Last reviewed` and `Next review` (+ 21 days)
4. Sync AGENTS.md (identical content)

## Debugging Rules
- REPRODUCE the bug first. Do not jump to fixes.
- Read the ENTIRE error message and stack trace before forming a hypothesis.
- Write a failing test that captures the bug before attempting a fix.
- Do NOT propose speculative fixes. No "maybe", "possibly", "could be".
- If root cause isn't proven, produce a diagnostic plan, not a patch.
- Apply the minimal fix — touch as few files as possible.
- After fixing, run the failing test again to confirm it passes.
- Never rewrite large sections of code to fix a bug. If you feel the urge, you don't understand the root cause yet.

<!-- Line count: ~135 (multi-agent + token discipline + debugging sections) -->
