# CLAUDE.md
<!-- Base: Brainquarters v1.9 | Project: v1.7 | Last synced: 2026-04-05 -->
<!-- Last reviewed: 2026-04-04 | Next review: 2026-04-25 -->
<!-- Target: 60-100 lines | If >100 lines, prune or move to .active_context.md -->

## WHAT: Project & Stack

**adversarial-spec** — Claude Code skill for iterative spec development through multi-model debate.

Runtime: Python 3.14+ | Deps: uv, pyproject.toml | Tests: pytest | Lint: ruff

**Key paths:**
- `skills/adversarial-spec/` — Skill definition (phases, scripts, reference)
- `~/.claude/skills/adversarial-spec/` — Deployed skill (what Claude Code uses)
- `adversarial-spec-process-failure-report.md` — Process lessons learned

## HOW: Working in This Codebase

### Session Start
```
/tasks              # Check for existing work
/adversarial-spec   # Start or resume spec workflow
```

### Phase Awareness
Phases: requirements → roadmap → debate → target-architecture → gauntlet → finalize → execution → implementation

You must always know what phase you are in when operating on the codebase. It is rare to make changes outside of a pipeline task card. If you find yourself doing this, you must at least be operating from a plan the user just approved via plan mode.

### Commands
```bash
uv run pytest                            # Test
uvx ruff check --fix --unsafe-fixes      # Lint
```

### Deployment
Changes to `skills/adversarial-spec/` need manual copy to `~/.claude/skills/`:
```bash
cp -r skills/adversarial-spec/* ~/.claude/skills/adversarial-spec/
```

### Documentation Lookup (docmaster)
There are no external APIs this project interfaces against. If this ever changes, use docmaster. You may request a new API for coverage (and update this line in CLAUDE.md).

### Context Loading (On-Demand)
Don't pre-load domain context. Load when needed:
- **Process lessons**: Read `adversarial-spec-process-failure-report.md`
- **Skill phases**: Read `skills/adversarial-spec/phases/`
- **Implementation**: Read execution plan from `.adversarial-spec/`

### Resuming Work
```
/tasks                    # See work streams and pending tasks
/tasks <context>          # See tasks for specific work stream
```

## Guardrails

**Hooks enforce safety** — see `.claude/hooks/`.

- Read `.architecture/INDEX.md` first for navigation, then `primer.md` for context. Don't glob/grep when architecture docs exist.
- Validate required fields before writes (fail-fast, no silent fallbacks)
- Read official docs with Docmaster before integrating external APIs
- Integration-specific logic stays in integration modules. Core services use standardized interfaces only.
- Fizzy MCP tool calls must pass explicit `board_id` from `projects.yaml`; no default board lock.

## Token Discipline
- Hook blocks a command → switch tools immediately. Do NOT read hook source to diagnose.
- Codex calls → always `timeout=900000`+ and `run_in_background`. Hook enforces minimums.
- `TaskOutput(block=true)` returns full result — never re-read the same output file.
- Background tasks → check `block=false` at ~45s before committing to a blocking wait.
- Failure patterns (rate limits, wrong defaults) → record in MEMORY.md same session.
- Background notification for already-consumed task → reply "Already processed." (one line).

## Multi-Agent Coordination (Claude + Codex)

Two agents work **in parallel on the same branch**. Coordination via `.handoff.md` + pipeline board.

- **Before picking up a card**: Read `.handoff.md`, update your row, check for file conflicts
- **State gates, not commit gates**: Advance pipeline state only when exit criteria are satisfied
- **When work is review-ready**: Update `.handoff.md` review queue, move card → "Review" with evidence (commit hash + checks)
- **Reviews before new work**: Check review queue first — reviewing the other agent's review-ready change set takes priority over picking up a new card
- **Don't stall**: If there are pending todos or cards, just do the work — don't ask "Shall I proceed?"
- **Full protocol**: Read `.coordination/PROTOCOL.md`

Board: Fizzy `03fvw8ld1ibx7m42gi14p4pkl` (ASPEC Pipeline) | Trello `69be407deef7267a2cea1feb` (legacy, migration in progress)

## Debugging Rules
- If you suspect failure, write a failing test saved to disk. Judge your solution by running the test. The test stays to prove no future changes resurface the bug.
- Read the ENTIRE error message and stack trace before forming a hypothesis.
- No speculative fixes. If root cause isn't proven, produce a diagnostic plan, not a patch.
- Apply the minimal fix — fewest files possible. If you want to rewrite large sections, you don't understand the root cause yet.
- Stop at first anomaly: if any key metric drops >25% from baseline, stop and investigate.

## Communication Style
Default: terse. Full sentences only for root causes, confirmed fixes, dead ends.
Drop articles, linking verbs, filler. Imperatives for actions, fragments for observations.

Terse: "Refactoring for edge case." not "I'll go ahead and refactor that function to handle the edge case."
Full: "authenticate_or_request_with_http_token expects `Token token=value`. Request sends Bearer — won't match. Cause of 401."

## Progressive Disclosure

**This file is minimal by design.** Load context on-demand:
- **Project patterns**: Read `onboarding/project-practices.md`
- **Codebase orientation**: Read `.architecture/INDEX.md`
- **Telegram bridge** (human-gated review from mobile): Read `~/.claude/skills/adversarial-spec/reference/telegram-bridge.md`

## Review Trigger
**`/checkpoint`**: If `Next review` date passed → verify file matches workflows, check line count (target 60-100), update dates (+21 days), sync AGENTS.md.
