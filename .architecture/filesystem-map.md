# Filesystem Map: adversarial-spec

> Generated: 2026-03-21 | Git: 12c5d3f
> Skill version: 2.6 | Model: claude-opus-4-6

## Root Structure

| Directory/File | Purpose |
|----------------|---------|
| `skills/adversarial-spec/` | Skill source — phases, scripts, reference docs |
| `execution_planner/` | Gauntlet concern parsing (mostly deprecated) |
| `mcp_tasks/` | MCP server for cross-agent task coordination |
| `tests/` | Root-level pytest tests |
| `onboarding/` | Project practices and core practices docs |
| `wisdom/` | Accumulated learnings and CEO wisdom |
| `docs/` | Documentation bundles (Gemini bundle) |
| `.architecture/` | Architecture documentation (this directory) |
| `.adversarial-spec/` | Spec artifacts, session data, issue tracking |
| `.claude/` | Claude Code hooks and settings |

## Key Areas

### skills/adversarial-spec/

| Path | Purpose |
|------|---------|
| `scripts/debate.py` | Main CLI entry point — debate + gauntlet commands (1535 lines) |
| `scripts/gauntlet/` | 7-phase adversarial review package (16 modules, ~5200 lines total) |
| `scripts/gauntlet/__init__.py` | Shim re-exporting 5 public symbols |
| `scripts/gauntlet/__main__.py` | Module entry for `python -m gauntlet` |
| `scripts/gauntlet/cli.py` | Standalone gauntlet CLI |
| `scripts/gauntlet/core_types.py` | All dataclasses: Concern, Evaluation, GauntletConfig, PhaseMetrics, etc. |
| `scripts/gauntlet/orchestrator.py` | `run_gauntlet()` — phase sequencing, resume, manifest telemetry |
| `scripts/gauntlet/persistence.py` | File I/O, checkpoints, stats, run manifests (FileLock-based) |
| `scripts/gauntlet/model_dispatch.py` | Model selection, validation, rate limiting |
| `scripts/gauntlet/reporting.py` | Leaderboard, synergy analysis, gauntlet report |
| `scripts/gauntlet/medals.py` | Medal calculation and persistence |
| `scripts/gauntlet/phase_1_attacks.py` | Phase 1: Generate adversary attacks (196 lines) |
| `scripts/gauntlet/phase_2_synthesis.py` | Phase 2: Big-picture synthesis (208 lines) |
| `scripts/gauntlet/phase_3_filtering.py` | Phase 3: Filtering + clustering (456 lines) |
| `scripts/gauntlet/phase_4_evaluation.py` | Phase 4: Multi-model evaluation (283 lines) |
| `scripts/gauntlet/phase_5_rebuttals.py` | Phase 5: Adversary rebuttals (128 lines) |
| `scripts/gauntlet/phase_6_adjudication.py` | Phase 6: Final adjudication (97 lines) |
| `scripts/gauntlet/phase_7_final_boss.py` | Phase 7: Optional Final Boss review (330 lines) |
| `scripts/gauntlet_monolith.py` | Compatibility shim (12 lines, raises ImportError) |
| `scripts/models.py` | LLM abstraction: LiteLLM + CLI tool routing (944 lines) |
| `scripts/providers.py` | Model config, costs, credentials, Bedrock (683 lines) |
| `scripts/prompts.py` | Prompt templates, focus areas, personas (505 lines) |
| `scripts/adversaries.py` | Named attacker persona definitions (914 lines) |
| `scripts/session.py` | Session state and checkpoint management (109 lines) |
| `scripts/scope.py` | Scope discovery (standalone, not currently imported) |
| `scripts/task_manager.py` | Python API for task management (687 lines) |
| `scripts/telegram_bot.py` | Telegram notification utilities (443 lines) |
| `scripts/mutmut_config.py` | Mutation testing configuration |
| `scripts/pre_gauntlet/` | Pre-gauntlet context collection subsystem |
| `scripts/collectors/` | Git position and system state collectors |
| `scripts/extractors/` | Spec-affected file extraction |
| `scripts/integrations/` | Subprocess wrappers (git, process runner, knowledge service) |
| `scripts/tests/` | Test suite (16 test files, 377+ tests) |
| `phases/` | Phase documentation (01-init through 08-implementation) |
| `reference/` | Reference docs for the skill |
| `SKILL.md` | Skill definition with metadata and phase routing |

### execution_planner/

| Path | Purpose |
|------|---------|
| `__init__.py` | Exports GauntletConcernParser, load_concerns_for_spec |
| `gauntlet_concerns.py` | Parses gauntlet concern files (the only surviving module) |

### mcp_tasks/

| Path | Purpose |
|------|---------|
| `__init__.py` | Exports FastMCP server instance |
| `server.py` | MCP tools: TaskCreate, TaskGet, TaskList, TaskUpdate |

### .adversarial-spec/

| Path | Purpose |
|------|---------|
| `session-state.json` | Active session pointer and phase tracking |
| `sessions/` | Session files with journey arrays |
| `specs/` | Generated spec artifacts with manifests |
| `issues/` | Issue tracking docs |

### .claude/

| Path | Purpose |
|------|---------|
| `hooks/` | 12 safety hooks (deprecated models, codex timeout, secret leaks, etc.) |
| `settings.json` | Project settings |
| `settings.local.json` | Hook registration (PreToolUse, PostToolUse, Stop) |
| `tasks.json` | MCP task storage |

## Entry Points

| File | How It Starts | What It Does |
|------|---------------|--------------|
| `scripts/debate.py` | `adversarial-spec <action>` (pyproject.toml entry) | Main CLI: critique, gauntlet, diff, export-tasks, providers, profiles, sessions |
| `scripts/gauntlet/cli.py` | `python -m gauntlet` via `__main__.py` | Standalone gauntlet CLI with all flags |
| `scripts/telegram_bot.py` | `python telegram_bot.py <cmd>` | Telegram setup, send, poll, notify |
| `mcp_tasks/server.py` | `mcp-tasks` (pyproject.toml entry) | MCP task server for Claude Code |

## Configuration Files

| File | Configures |
|------|------------|
| `pyproject.toml` | Dependencies (litellm, filelock, mcp), entry points, ruff/pytest config |
| `uv.lock` | Locked dependency versions |
| `CLAUDE.md` | Project instructions for Claude Code |
| `.claude/hooks/` | Safety hooks (deprecated models, codex timeout, secret leaks, etc.) |
| `.claude/settings.local.json` | Hook registration |
| `~/.config/adversarial-spec/profiles/` | Saved user profiles (focus + persona combos) |
| `~/.config/adversarial-spec/sessions/` | Session state files |
| `~/.claude/adversarial-spec/config.json` | Global config (Bedrock settings) |

## Notable Conventions

- **Deployed vs source**: `skills/adversarial-spec/` is the source. `~/.claude/skills/adversarial-spec/` is the deployed copy (symlinked or manual `cp -r`).
- **Tests alongside scripts**: Tests live in `scripts/tests/`, not a separate root `tests/` dir (root `tests/` exists but is minimal).
- **Pre-gauntlet is isolated**: `pre_gauntlet/`, `collectors/`, `extractors/`, and `integrations/` form a self-contained subsystem with no imports from main debate/gauntlet modules.
- **Checkpoint directories are local**: `.adversarial-spec-checkpoints/` (debate) and `.adversarial-spec-gauntlet/` (gauntlet) are created in the working directory.
- **Two CLI entry points for gauntlet**: `debate.py gauntlet` (primary, adds `--show-manifest`, `--codex-reasoning`, `--gauntlet-resume`) and `python -m gauntlet` (standalone, has `--attack-codex-reasoning`).
