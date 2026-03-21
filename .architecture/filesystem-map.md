# Filesystem Map: adversarial-spec

> Generated: 2026-03-18 | Git: 0eb7ad9
> Skill version: 2.6 | Model: claude-opus-4-6

## Root Structure

| Directory/File | Purpose |
|----------------|---------|
| `skills/adversarial-spec/` | Skill source — phases, scripts, reference docs |
| `execution_planner/` | Gauntlet concern parsing (mostly deprecated) |
| `mcp_tasks/` | MCP server for cross-agent task coordination |
| `tests/` | pytest test suite |
| `onboarding/` | Project practices and core practices docs |
| `wisdom/` | Accumulated learnings and CEO wisdom |
| `.architecture/` | Architecture documentation (this directory) |
| `.adversarial-spec/` | Spec artifacts, session data, issue tracking |
| `.claude/` | Claude Code hooks and settings |

## Key Areas

### skills/adversarial-spec/

| Path | Purpose |
|------|---------|
| `scripts/debate.py` | Main CLI entry point (1485 lines) |
| `scripts/gauntlet.py` | 7-phase adversarial review (4087 lines, largest file) |
| `scripts/models.py` | LLM abstraction: LiteLLM + CLI tool routing (937 lines) |
| `scripts/providers.py` | Model config, costs, credentials, Bedrock (683 lines) |
| `scripts/prompts.py` | Prompt templates, focus areas, personas (505 lines) |
| `scripts/adversaries.py` | Named attacker persona definitions (914 lines) |
| `scripts/session.py` | Session state and checkpoint management |
| `scripts/scope.py` | Scope discovery (standalone, not currently imported) |
| `scripts/task_manager.py` | Python API for task management (687 lines) |
| `scripts/telegram_bot.py` | Telegram notification utilities (443 lines) |
| `scripts/mutmut_config.py` | Mutation testing configuration |
| `scripts/pre_gauntlet/` | Pre-gauntlet context collection subsystem |
| `scripts/collectors/` | Git position and system state collectors |
| `scripts/extractors/` | Spec-affected file extraction |
| `scripts/integrations/` | Subprocess wrappers (git, process runner, knowledge service) |
| `phases/` | Phase documentation (01-philosophy through 08-implementation) |
| `reference/` | Reference docs for the skill |

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
| `specs/` | Generated spec artifacts with manifests |
| `issues/` | Issue tracking docs |

## Entry Points

| File | How It Starts | What It Does |
|------|---------------|--------------|
| `scripts/debate.py` | `adversarial-spec <action>` (pyproject.toml entry) | Main CLI: critique, gauntlet, info commands |
| `scripts/gauntlet.py` | `python gauntlet.py` or called from debate.py | Standalone gauntlet CLI |
| `scripts/telegram_bot.py` | `python telegram_bot.py <cmd>` | Telegram setup, send, poll, notify |
| `mcp_tasks/server.py` | `mcp-tasks` (pyproject.toml entry) | MCP task server for Claude Code |

## Configuration Files

| File | Configures |
|------|------------|
| `pyproject.toml` | Dependencies, entry points, ruff/pytest config |
| `uv.lock` | Locked dependency versions |
| `CLAUDE.md` | Project instructions for Claude Code |
| `.claude/hooks/` | Safety hooks (deprecated models, codex timeout, secret leaks) |
| `.claude/settings.local.json` | Hook registration |
| `~/.config/adversarial-spec/profiles/` | Saved user profiles (focus + persona combos) |
| `~/.config/adversarial-spec/sessions/` | Session state files |
| `~/.claude/adversarial-spec/config.json` | Global config (Bedrock settings) |

## Notable Conventions

- **Deployed vs source**: `skills/adversarial-spec/` is the source. `~/.claude/skills/adversarial-spec/` is the deployed copy. Manual `cp -r` required after changes.
- **No separate test directory per module**: Tests are in a top-level `tests/` dir, not alongside source.
- **Pre-gauntlet is isolated**: The `pre_gauntlet/`, `collectors/`, `extractors/`, and `integrations/` directories form a self-contained subsystem with no imports from the main debate/gauntlet modules.
- **Checkpoint directories are local**: `.adversarial-spec-checkpoints/` and `.adversarial-spec-gauntlet/` are created in the working directory, not in a global config path.
