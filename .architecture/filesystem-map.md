# Filesystem Map: adversarial-spec

> Generated: 2026-02-06T20:35:00Z | Git: e94ebfe
> Skill version: 2.1 | Model: Claude Opus 4.6

## Root Structure

| Directory/File | Purpose |
|----------------|---------|
| `skills/adversarial-spec/` | Skill source: phases, scripts, reference docs. Symlinked to `~/.claude/skills/adversarial-spec/` |
| `execution_planner/` | Spec-to-task pipeline (mid-deprecation; only `gauntlet_concerns.py` survives) |
| `mcp_tasks/` | MCP server for cross-agent task management |
| `onboarding/` | Onboarding docs: core practices, project practices |
| `wisdom/` | Collected project wisdom and lessons |
| `.adversarial-spec/` | Session state, checkpoints, specs, issues, retrospectives |
| `.claude/` | Claude Code config: hooks, settings, tasks.json |
| `.architecture/` | Architecture documentation (this directory) |

## Key Areas

### skills/adversarial-spec/

| Path | Purpose |
|------|---------|
| `scripts/debate.py` | Main CLI entry point (~2000 lines). Routes 18 action commands |
| `scripts/gauntlet.py` | Adversarial gauntlet engine (~3500 lines). 6-phase pipeline |
| `scripts/models.py` | LLM call abstraction. ThreadPoolExecutor parallel calls |
| `scripts/providers.py` | Provider config, MODEL_COSTS, API key validation |
| `scripts/prompts.py` | Prompt templates, personas, focus areas |
| `scripts/adversaries.py` | Adversary persona definitions and medal system |
| `scripts/session.py` | Session state persistence, checkpoints |
| `scripts/telegram_bot.py` | Telegram Bot API integration (send, poll, notify) |
| `scripts/task_manager.py` | Python API wrapping MCP Tasks storage |
| `scripts/mutmut_config.py` | Mutation testing configuration |
| `scripts/collectors/` | Git position and system state collectors |
| `scripts/extractors/` | Spec-affected file extraction |
| `scripts/integrations/` | Git CLI, process runner, knowledge service |
| `scripts/pre_gauntlet/` | Pre-gauntlet pipeline: orchestrator, context builder, alignment |
| `scripts/tests/` | pytest tests for all script modules |
| `scripts/scripts/` | **Stale copy** — ignore, canonical source is `scripts/` |
| `phases/` | Skill phase docs (01-init through 07-implementation) |
| `reference/` | Reference docs: script commands, gauntlet details, convergence rules |
| `SKILL.md` | Skill definition loaded by Claude Code |
| `SETUP.md` | Skill setup instructions |

### execution_planner/

| Path | Purpose |
|------|---------|
| `__init__.py` | Re-exports 30+ types from submodules |
| `gauntlet_concerns.py` | **KEEP**: Parses gauntlet JSON, links concerns to spec sections |
| `task_planner.py` | **KEEP**: Task DAG generation from spec |
| `spec_intake.py` | DEPRECATED: Document parsing (being replaced by LLM guidelines) |
| `agent_dispatch.py` | DEPRECATED: Multi-agent task dispatch |
| `execution_control.py` | DEPRECATED: Execution flow control |
| `progress.py` | DEPRECATED: Progress tracking |
| `llm_extractor.py` | DEPRECATED: LLM-based data extraction |
| `__main__.py` | DEPRECATED: CLI entry point |

### mcp_tasks/

| Path | Purpose |
|------|---------|
| `server.py` | FastMCP server with 4 tools: TaskCreate, TaskGet, TaskList, TaskUpdate |

### .claude/hooks/

| Path | Purpose |
|------|---------|
| `deprecated_models.py` | PreToolUse: catches stale model names in Bash commands |
| `codex-timeout-guard.py` | PreToolUse: enforces min timeouts for Codex reasoning levels |
| `bash_command_check.py` | PreToolUse: general bash safety checks |
| `banned_git_commands.py` | PreToolUse: blocks destructive git commands |
| `force_flag_defense.py` | PreToolUse: blocks --force flags |
| `secret_exposure.py` | PostToolUse: detects secrets in written files |
| `uv_run_check.py` | PreToolUse: enforces `uv run` for Python |
| `_template.py` | Template for creating new hooks |

## Entry Points

| File | How It Starts | What It Does |
|------|---------------|--------------|
| `scripts/debate.py` | `uv run python debate.py <action>` | Main adversarial spec CLI (18 actions) |
| `scripts/gauntlet.py` | `uv run python gauntlet.py` | Standalone gauntlet runner |
| `scripts/telegram_bot.py` | `uv run python telegram_bot.py <cmd>` | Telegram bot (setup, send, poll, notify) |
| `execution_planner/__main__.py` | `python -m execution_planner` | Execution plan generation (deprecating) |
| `mcp_tasks/server.py` | MCP protocol | Task management server |

## Configuration Files

| File | Configures |
|------|------------|
| `pyproject.toml` | Dependencies (litellm, mcp, pydantic, pytest, ruff), build config |
| `.claude/settings.local.json` | Hook registrations (PreToolUse, PostToolUse, Stop) |
| `.claude/settings.json` | Claude Code project settings |
| `.adversarial-spec/session-state.json` | Active session pointer and phase tracking |
| `~/.claude/adversarial-spec/config.json` | Global config (Bedrock settings) |
| `~/.config/adversarial-spec/profiles/` | Saved debate profiles (models, focus, persona) |
| `~/.config/adversarial-spec/sessions/` | Session state JSON files |

## Notable Conventions

- **Tests live alongside source**: `scripts/tests/` mirrors `scripts/` structure, not a separate top-level `tests/` dir.
- **Symlinked deployment**: `skills/adversarial-spec/` is symlinked to `~/.claude/skills/adversarial-spec/`, so changes take effect immediately without manual copy.
- **Phase-driven skill**: The skill reads one phase file at a time from `phases/` based on `current_phase` in session state. This keeps context windows small.
- **Dual package roots**: Both `skills/adversarial-spec/` and root `execution_planner/` have their own `pyproject.toml`. The skill scripts use relative imports and `sys.path` manipulation rather than installed packages.
