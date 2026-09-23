# CLAUDE.md
<!-- Base: Brainquarters v2.3 | Project: v1.8 | Last synced: 2026-07-12 -->
<!-- Last reviewed: 2026-06-09 | Next review: 2026-06-30 -->
<!-- Target: 60-100 lines | If >100 lines, prune or move to .active_context.md -->

## Domain Vocabulary
Project glossary (auto-loaded): @CONTEXT.md
Shared ecosystem terms load globally from Brainquarters/shared-context/GLOSSARY.md.

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
/conductor          # Briefing: git, session, pipeline state
/adversarial-spec   # Start or resume spec workflow
```

### Phase Awareness
Eight phases; select the route from the active session's `pipeline_version`:

- Pre-v6: requirements → roadmap → debate → target-architecture → gauntlet → finalize → execution → implementation.
- v6+: requirements → roadmap → decomposition → debate → gauntlet → finalize → execution → implementation.

See `skills/adversarial-spec/SKILL.md` § Phase Router. v6 carries the Phase 4 artifact in D0; verification is a Phase 8 subflow.

You must always know what phase you are in when operating on the codebase. It is rare to make changes outside of a pipeline task card. If you find yourself doing this, you must at least be operating from a plan the user just approved via plan mode.

### Commands
```bash
uv run pytest                            # Test
uvx ruff check --fix --unsafe-fixes      # Lint
```

### Deployment
`~/.claude/skills/adversarial-spec` is a symlink to `skills/adversarial-spec/` —
source edits are live immediately; there is no copy step.

### Documentation Lookup (docmaster)
There are no external APIs this project interfaces against. If this ever changes, use docmaster. You may request a new API for coverage (and update this line in CLAUDE.md).

### Context Loading (On-Demand)
Don't pre-load domain context. Load when needed:
- **Process lessons**: Read `adversarial-spec-process-failure-report.md`
- **Skill phases**: Read `skills/adversarial-spec/phases/`
- **Implementation**: Read execution plan from `.adversarial-spec/`

### Resuming Work
```
/conductor                # Briefing incl. parked sessions and lane state
/context-switch           # Switch between contexts within the project
```
(Tasks MCP retired June 2026 — `/tasks` is gone; Fizzy pipeline is the task system.)

## Guardrails

**Hooks enforce safety** — see `.claude/hooks/`.

- **NO GLOBAL KILLS**: Never use `killall`, `pkill`, or broad `kill` patterns. Target specific PIDs from the current project only.
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
- Delegate or restart when debugging loops, repeated large reads, or metadata chatter are inflating primary context. The conductor still owns final validation of diffs, tests, and evidence.

## Pipeline Work (Phase-Owned)

`/adversarial-spec`, the active session state, and the current phase document own
pipeline behavior. This file deliberately does not define a second pickup, wakeup,
or waiting protocol.

- **Route first**: Resolve the active adversarial-spec phase before touching a card.
- **Board status**: Use `pipeline_lane_state` for status. Never call
  `pipeline_do_next_task` merely to poll, wait, or inspect.
- **Pickup**: Call `pipeline_do_next_task` only when ready to perform whatever it
  returns. Always pass the explicit Fizzy `board_id`.
- **Idle**: Read the returned `attention`/blocker, report the named next actor, then
  stop. Never sleep-and-retry or launch/relaunch a local watcher to simulate progress.
- **Dispatch**: A dispatch is a notice or audit record, not proof of a claim,
  acknowledgement, or successful wakeup. Verify live board state before acting.
- **Unavailable review**: Surface an unreachable independent reviewer as unavailable;
  do not simulate liveness with a local loop.

Board routing: `adversarial-spec` — Fizzy (`03fw5alxw15iqwh6hq15vfdsb`).

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
