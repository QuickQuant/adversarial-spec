# Filesystem Map: adversarial-spec

> Generated: 2026-04-16 | Git: 9ca3ccd
> Skill version: 3.6 | Model: claude-opus-4-6

## Root Structure

| Directory/File | Purpose |
|----------------|---------|
| `skills/adversarial-spec/` | Skill definition (phases, scripts, reference docs) |
| `execution_planner/` | Gauntlet concern parsing (mostly deprecated) |
| `mcp_tasks/` | MCP task server for cross-agent coordination |
| `onboarding/` | Core practices and project practices docs |
| `.architecture/` | Architecture documentation (this directory) |
| `.adversarial-spec/` | Spec artifacts, session manifests, resolved concerns |
| `.adversarial-spec-checkpoints/` | Debate round checkpoints (per-session) |
| `.adversarial-spec-gauntlet/` | Gauntlet phase checkpoints (hash-keyed JSON + lock files) |
| `.claude/` | Claude Code hooks, settings, task coordination |
| `.coordination/` | Multi-agent coordination protocol |
| `pyproject.toml` | Dependencies, build config, entry points |

## Key Areas

### skills/adversarial-spec/scripts/

The main source code directory. All Python scripts live here.

| Path | Purpose |
|------|---------|
| `debate.py` | Master CLI entrypoint (1562 lines, 18+ actions) |
| `models.py` | LLM call abstraction, cost tracking, parallel dispatch (1000 lines) |
| `providers.py` | Model config, cost rates, Bedrock, CLI detection |
| `adversaries.py` | Named attacker persona definitions (frozen dataclasses) |
| `prompts.py` | System prompts, focus areas, personas templates |
| `session.py` | Session state persistence for debate rounds |
| `scope.py` | Scope discovery definitions (606 lines, no importers — status unclear) |
| `telegram_bot.py` | Telegram notification bot (send, poll, notify) |
| `task_manager.py` | Task state management + demo harness |
| `gauntlet_monolith.py` | 12-line shim → delegates to gauntlet/cli.py |

### skills/adversarial-spec/scripts/gauntlet/

The 18-module gauntlet package (extracted from original monolith).

| Path | Purpose |
|------|---------|
| `__init__.py` | Public API exports (run_gauntlet, format_gauntlet_report, etc.) |
| `__main__.py` | Enables `python -m gauntlet` invocation |
| `cli.py` | Standalone gauntlet CLI (separate flag names from debate.py) |
| `orchestrator.py` | 7-phase pipeline sequencing, state management, resume (865 lines) |
| `core_types.py` | Data models: Concern, Evaluation, Rebuttal, GauntletConfig, Medal, etc. |
| `model_dispatch.py` | Model selection, rate limiting, name validation |
| `persistence.py` | FileLock-guarded checkpoint save/load, atomic writes |
| `prompts.py` | Centralized phase system prompts (NEW — extracted from inline) |
| `phase_1_attacks.py` | Attack generation (parallel adversary dispatch) |
| `phase_2_synthesis.py` | Big-picture synthesis across all concerns |
| `phase_3_filtering.py` | Concern filtering, explanation matching (clustering removed) |
| `phase_4_evaluation.py` | Frontier model evaluation (verdict assignment, multi-model consensus) |
| `phase_5_rebuttals.py` | Adversary rebuttal for dismissed concerns |
| `phase_6_adjudication.py` | Final adjudication and verdict aggregation |
| `phase_7_final_boss.py` | Final boss review (pass/refine/reconsider) |
| `medals.py` | Adversary accuracy scoring and medal awards |
| `reporting.py` | Markdown report generation, leaderboard formatting |
| `synthesis_extract.py` | Standalone concern parsing/clustering utility |

### skills/adversarial-spec/scripts/pre_gauntlet/

Pre-gauntlet context collection pipeline.

| Path | Purpose |
|------|---------|
| `orchestrator.py` | Coordinate git/system/file collectors |
| `models.py` | Pydantic models: GitPosition, SystemState, Concern |
| `context_builder.py` | Assemble collected context into markdown |
| `alignment_mode.py` | Interactive user validation of collected context |
| `discovery.py` | Discovery result types |

### skills/adversarial-spec/scripts/collectors/

| Path | Purpose |
|------|---------|
| `git_position.py` | Git branch, commits, staleness detection |
| `system_state.py` | Build status, schema contents, directory trees |

### skills/adversarial-spec/scripts/integrations/

| Path | Purpose |
|------|---------|
| `git_cli.py` | Git subprocess wrapper (GitCli, GitCliError) |
| `process_runner.py` | Generic subprocess runner with timeout |
| `knowledge_service.py` | Knowledge base caching |

### skills/adversarial-spec/scripts/tests/

20 test files covering all components.

| Path | Purpose |
|------|---------|
| `test_models.py`, `test_model_calls.py` | Model calling, cost tracking, parallel dispatch |
| `test_providers.py` | Provider config, Bedrock, CLI detection |
| `test_session.py` | Session persistence, path traversal protection |
| `test_adversaries.py` | Adversary registry, scope guidelines, content hash |
| `test_prompts.py` | Prompt templates and persona validation |
| `test_cli.py` | debate.py CLI argument parsing |
| `test_gauntlet_*.py` (12 files) | Gauntlet phases, orchestrator, persistence, types, dispatch, medals |
| `test_telegram_bot.py` | Telegram bot command tests |

### skills/adversarial-spec/phases/

Skill phase documentation (9 phases, markdown instructions for Claude Code).

| Path | Purpose |
|------|---------|
| `01-init-and-requirements.md` | Initialization and requirements gathering |
| `02-roadmap.md` | Roadmap and milestone planning |
| `03-debate.md` | Multi-model debate execution |
| `04-target-architecture.md` | Target architecture definition (rewritten Apr 2026) |
| `05-gauntlet.md` | Gauntlet stress-test (cardinal rules for synthesis) |
| `06-finalize.md` | Spec finalization |
| `07-execution.md` | Execution plan generation (with verification gates) |
| `08-implementation.md` | Implementation phase |
| `09-verification.md` | Test mapping and verification |

## Entry Points

| File | How It Starts | What It Does |
|------|---------------|--------------|
| `scripts/debate.py` | `adversarial-spec <action>` (pyproject.toml) | Master CLI — routes 18 actions |
| `scripts/gauntlet/cli.py` | `python -m gauntlet` or direct | Standalone gauntlet CLI |
| `scripts/telegram_bot.py` | Direct script execution | Telegram notification bot |
| `mcp_tasks/server.py` | MCP protocol (registered entry point) | Task CRUD for cross-agent coordination |

## Configuration Files

| File | Configures |
|------|------------|
| `pyproject.toml` | Dependencies (litellm, filelock, mcp), entry points, ruff, pytest |
| `~/.claude/adversarial-spec/config.json` | Global Bedrock config (enabled, region, models) |
| `~/.config/adversarial-spec/sessions/` | Debate session state (per session_id) |
| `~/.config/adversarial-spec/profiles/` | Reusable model/API key profiles |
| `~/.adversarial-spec/` | Adversary stats, medals, resolved concerns, runs |
| `.adversarial-spec-gauntlet/` | Gauntlet phase checkpoints (hash-keyed) |
| `.claude/hooks/` | Pre/post tool use hooks (deprecated model check, timeout guard) |
| `.claude/settings.local.json` | Hook registrations |

## Notable Conventions

- **Scripts live under `skills/adversarial-spec/scripts/`**, not a standard `src/` directory. This matches the Claude Code skill deployment model.
- **Tests live alongside source** in `scripts/tests/`, not a separate `tests/` directory at root.
- **Two copies of the skill exist**: source in `skills/adversarial-spec/` and deployed in `~/.claude/skills/adversarial-spec/`. Changes require manual copy.
- **Checkpoint files use hash-based names**: `{phase}-{spec_hash}.json` prevents overwrite of valid data.
- **Lock files are sidecar files**: `.adversarial-spec-gauntlet/*.json.lock` next to their data files.
