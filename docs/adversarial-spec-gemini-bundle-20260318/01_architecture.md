<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: .architecture/overview.md (67 lines, 7260 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# System Overview: adversarial-spec

> Generated: 2026-03-18 | Git: 0eb7ad9 | Target: /home/jason/PycharmProjects/adversarial-spec
> Skill version: 2.6 | Model: claude-opus-4-6

## What This System Does

adversarial-spec is a Claude Code skill that iteratively refines product specifications through multi-model debate. It sends a spec to multiple LLMs (GPT, Claude, Gemini, Grok, etc.) simultaneously, collects critiques, and continues rounds until all models agree. A separate gauntlet mode stress-tests specs with named adversary personas that attack from specific angles (security paranoia, oncall burnout, UX skepticism, etc.).

## Architecture at a Glance

The system is built around a CLI tool (`debate.py`) that orchestrates parallel LLM calls through a provider-agnostic abstraction layer. When a user submits a spec for critique, `debate.py` parses CLI arguments, loads any saved profiles/sessions, formats prompts from centralized templates, and dispatches the spec to multiple models simultaneously via `ThreadPoolExecutor`. Each model is called through one of four routes: LiteLLM (for API-based providers), or subprocess shells for Codex CLI, Gemini CLI, and Claude CLI. Responses are collected, checked for agreement markers (`[AGREE]`), and persisted as session checkpoints for resumability.

The gauntlet subsystem (`gauntlet.py`, the largest file at ~4000 lines) provides a 7-phase adversarial review pipeline. Named adversary personas generate attacks, a big-picture synthesis identifies patterns across concerns, filtering and clustering reduce volume, multi-model evaluation produces verdicts, rebuttals challenge dismissals, final adjudication resolves sustained rebuttals, and an optional Final Boss (Opus) reviews everything holistically. Each phase persists intermediate results to disk for crash recovery.

Supporting this are: a prompt template system (`prompts.py`) with focus areas and personas, a provider configuration layer (`providers.py`) handling credentials/costs/Bedrock, session state persistence (`session.py`), a pre-gauntlet context collector that gathers git and system state, and an MCP task server that enables Claude Code integration.

## Primary Data Flows

### Spec Critique Loop

A spec arrives via stdin or session resume. `debate.py` formats it with system prompts (selected by doc type and depth), optional focus areas, and context files. `call_models_parallel()` at models.py:894 dispatches to N models simultaneously via `ThreadPoolExecutor`. Each model's response is parsed for `[AGREE]`/`[SPEC]` markers. Results are saved as round checkpoints and optionally sent via Telegram. The user iterates manually — each invocation is one round.

### Gauntlet Attack Pipeline

A spec enters `run_gauntlet()` at gauntlet.py:3290 and flows through 7 phases: (1) adversary personas generate concerns in parallel, (2) an LLM synthesizes patterns across all concerns, (3) historical filtering removes already-resolved issues, (3.5) semantic clustering deduplicates, (4) multiple evaluation models produce accept/dismiss/acknowledge/defer verdicts in batched waves, (5) dismissed concerns get adversary rebuttals, (6) sustained rebuttals get final adjudication, (7) optional Final Boss UX review. All intermediate data persists to `.adversarial-spec-gauntlet/` JSON files.

### Cost Tracking

Every model call reports token counts (from API responses, CLI JSON output, or character-based estimation). A global `CostTracker` singleton at models.py:204 accumulates per-model and total costs using rates from `MODEL_COSTS`. Output includes cost breakdowns in both text and JSON formats.

## Key Architectural Decisions

- **Single-invocation model**: No daemon or long-running process. Each CLI invocation is one debate round or one gauntlet run. Session persistence enables manual multi-round iteration.
- **Thread-per-model parallelism**: `ThreadPoolExecutor` with one worker per model. Relies on Python GIL for synchronization (informational cost tracker only).
- **CLI tool subprocess isolation**: Codex, Gemini, and Claude are called via `subprocess.run()`, not API, to leverage their built-in file access and agentic capabilities at no token cost.
- **Provider-agnostic routing**: LiteLLM wraps 7+ API providers. CLI tools have dedicated handlers. Model prefix determines routing.
- **Checkpoint-based resilience**: Gauntlet saves JSON after each phase. Session checkpoints save spec and raw critique responses per round. Recovery is manual (resume session or re-run gauntlet).
- **Layered architecture**: CLI → Orchestration → LLM Abstraction → Config/Data. No circular dependencies. Pre-gauntlet subsystem is fully isolated.

## Non-Obvious Things

- **gauntlet.py is ~4000 lines**: The largest file by far. Contains the full 7-phase pipeline, concern data classes, evaluation logic, medal/leaderboard tracking, and report formatting. Not currently split because phases share internal data structures heavily.
- **Execution planner is mostly deprecated**: Only `gauntlet_concerns.py` survives long-term. Phase 6 (execution planning) was rewritten to use Claude's native planning with embedded guidelines instead of a code pipeline. Dead modules have been deleted.
- **CLI tools are "free"**: Codex/Gemini/Claude CLI use the user's subscription, so `MODEL_COSTS` assigns them $0. This means cost tracking underreports when CLI tools are used.
- **`scope.py` is standalone**: A 600-line scope discovery module that isn't imported by anything currently.
- **Pre-gauntlet uses Pydantic**: The only part of the system using Pydantic for data validation. The rest uses dataclasses or plain dicts.
- **Session IDs have path traversal protection**: `is_relative_to()` checks prevent malicious session IDs from writing outside `~/.config/adversarial-spec/sessions/`.
- **`LITELLM_LOG` is force-set to ERROR**: Both `debate.py` and `models.py` set this at import time to suppress noisy LiteLLM output.

## Component Map

| Component | Purpose | Key Entry |
|-----------|---------|-----------|
| Debate Engine | Multi-model spec critique loop with CLI orchestration | `main()` at debate.py:1443 |
| Gauntlet | 7-phase adversarial stress-testing with named personas | `run_gauntlet()` at gauntlet.py:3290 |
| Models | LLM call abstraction (LiteLLM + 3 CLI tools) | `call_models_parallel()` at models.py:894 |
| Providers | Model config, credentials, cost rates, Bedrock support | `validate_model_credentials()` at providers.py:436 |
| Prompts | Centralized templates, focus areas, personas | `get_system_prompt()` at prompts.py:125 |
| Session | State persistence and checkpoint management | `SessionState` at session.py:17 |
| Pre-Gauntlet | Git/system context collection before gauntlet | `PreGauntletOrchestrator.run()` at orchestrator.py:51 |
| Adversaries | Named attacker persona definitions | `ADVERSARIES` dict at adversaries.py |
| MCP Tasks | Cross-agent task coordination via MCP protocol | `mcp.run()` at server.py:365 |
| Task Manager | Python API for task management | `TaskManager` at task_manager.py:114 |
| Execution Planner | Gauntlet concern parsing (deprecated except gauntlet_concerns) | `GauntletConcernParser` at gauntlet_concerns.py |

For detailed component docs, see `structured/components/`.


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: .architecture/patterns.md (95 lines, 5699 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# Cross-Cutting Pattern Analysis

> Generated by mapcodebase Phase 5 — compares repeated code patterns against
> framework best practices.
> Generated: 2026-03-18 | Git: 0eb7ad9 | Skill version: 2.6

## Patterns Detected

### subprocess-cli-model-calling-repeated-structure
- **Files:** [3 functions in 1 file]
  - `skills/adversarial-spec/scripts/models.py` (call_codex_model:351, call_gemini_cli_model:451, call_claude_cli_model:536)
- **Description:** Three separate functions implement nearly identical subprocess calling patterns: validate CLI available, build command array, run subprocess with capture_output/timeout, check returncode, parse output, handle TimeoutExpired/FileNotFoundError. Each duplicates 80+ lines of boilerplate.
- **Severity:** warning
- **Category:** loading
- **Concern:** High duplication of error handling and CLI invocation logic. If subprocess behavior changes, 3 locations must be updated. New CLI models require duplicating all this code.
- **Recommended:** Create a generic `_call_cli_model(cmd_array, system_prompt, user_message, timeout, output_parser_func)` that handles subprocess boilerplate. Each model handler becomes 20-30 lines.

### repeated-json-load-with-fallback-error-handling
- **Files:** [8+ locations across 2 files]
  - `skills/adversarial-spec/scripts/gauntlet.py` (lines 395, 563, 596, 629, 1032, 1252+)
  - `skills/adversarial-spec/scripts/session.py`
- **Description:** JSON loading with identical error handling repeated 8+ times: `try json.loads(path.read_text()) except (json.JSONDecodeError, OSError): return fallback`. Pattern is identical across load_adversary_stats, load_gauntlet_run, list_gauntlet_runs, load_resolved_concerns, etc.
- **Severity:** warning
- **Category:** data-fetching
- **Concern:** Scattered identical error handling makes it hard to update strategy uniformly. If error handling needs change (e.g., add logging), 8+ locations must be updated.
- **Recommended:** Create `load_json_safe(path, default_value=None)` utility function.

### environment-variable-reading-scattered
- **Files:** [4 files]
  - `skills/adversarial-spec/scripts/telegram_bot.py`
  - `skills/adversarial-spec/scripts/providers.py`
  - `skills/adversarial-spec/scripts/task_manager.py`
  - `skills/adversarial-spec/scripts/gauntlet.py`
- **Description:** Environment variables read directly via `os.environ.get()` scattered across 4+ files. No centralized authority for env var list or validation. Gauntlet alone reads API keys in 5+ separate locations.
- **Severity:** warning
- **Category:** configuration
- **Concern:** Difficult to audit which env vars are required. No centralized validation. If config source changes, all files need updating.
- **Recommended:** Create config.py with centralized `get_api_keys()`, `get_telegram_config()`, `get_aws_config()` functions.

### duplicate-path-safety-validation
- **Files:** [4 locations in 1 file]
  - `skills/adversarial-spec/scripts/session.py` (lines 37, 45, 79, 96)
- **Description:** Path safety validation using `is_relative_to()` repeated 4 times. Identical security check: `path.resolve().is_relative_to(DIR.resolve())`.
- **Severity:** warning
- **Category:** state-management
- **Concern:** Security-critical logic duplicated. If validation needs to change, all 4 locations must be updated independently.
- **Recommended:** Extract to `_validate_path(path, base_dir)` utility in session.py.

### test-file-sys-path-injection
- **Files:** [3 files]
  - `skills/adversarial-spec/scripts/tests/test_models.py`
  - `skills/adversarial-spec/scripts/tests/test_providers.py`
  - `skills/adversarial-spec/scripts/tests/test_session.py`
- **Description:** All test files begin with identical preamble: `sys.path.insert(0, str(Path(__file__).parent.parent))` for relative imports.
- **Severity:** info
- **Category:** configuration
- **Concern:** None — pattern is appropriate for current project structure.
- **Recommended:** Could be extracted to conftest.py for single-point-of-change, but not required.

### litellm-configuration-duplication
- **Files:** [2 files]
  - `skills/adversarial-spec/scripts/debate.py`
  - `skills/adversarial-spec/scripts/models.py`
- **Description:** Both files independently suppress litellm logging at module load time.
- **Severity:** info
- **Category:** configuration
- **Concern:** None — minimal duplication between 2 files.
- **Recommended:** Current approach is acceptable.

### cli-exit-code-convention
- **Files:** [2 files]
  - `skills/adversarial-spec/scripts/debate.py`
  - `skills/adversarial-spec/scripts/telegram_bot.py`
- **Description:** Both use sys.exit(1) for runtime errors and sys.exit(2) for config errors, but convention is implicit.
- **Severity:** info
- **Category:** error-handling
- **Concern:** None — pattern is consistent across both files.
- **Recommended:** Current approach is correct. Document if adding more CLIs.

### cli-argparse-structure
- **Files:** [2 files]
  - `skills/adversarial-spec/scripts/debate.py`
  - `skills/adversarial-spec/scripts/telegram_bot.py`
- **Description:** Both implement argparse with subparsers and command routing. Framework-mandated boilerplate.
- **Severity:** info
- **Category:** configuration
- **Concern:** None — pattern is appropriate for 2 CLIs.
- **Recommended:** Current approach is correct.

---

## Summary
- **Total patterns detected:** 8
- **Info:** 4 | **Warning:** 4 | **Error:** 0
- **Top concern:** `subprocess-cli-model-calling-repeated-structure` — 3 functions duplicating 80+ lines each of subprocess boilerplate in models.py. Highest impact because it blocks clean addition of new CLI models and creates maintenance risk for error handling changes.


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: .architecture/findings.md (93 lines, 6823 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# Architecture Findings

> Generated by mapcodebase Phase 6 — opinionated suggestions based on full
> codebase analysis. Validate these with `/gemini-bundle` or `/adversarial-spec`.
> Generated: 2026-03-18 | Git: 0eb7ad9 | Skill version: 2.6

## Findings

### FIND-001: scope.py is dead code (606 lines, imported by nothing)
- **Category:** dead-code
- **Severity:** warning
- **Confidence:** high
- **Component:** debate-engine
- **Files:**
  - `skills/adversarial-spec/scripts/scope.py`
- **Observation:** scope.py defines ScopeDiscovery, DiscoveryType, DiscoveryPriority, and related functions for scope management. It is 606 lines but not imported by any other module in the codebase. No `from scope import` or `import scope` found anywhere.
- **Suggestion:** Either integrate into the debate workflow (it appears designed for discovery management during spec iteration) or delete it. Dead code creates confusion about what's active.
- **Evidence:** `grep -r "import.*scope\|from.*scope" scripts/` returns zero results (excluding tests).

### FIND-002: gauntlet.py exceeds maintainable single-file size (4087 lines)
- **Category:** complexity
- **Severity:** warning
- **Confidence:** medium
- **Component:** gauntlet
- **Files:**
  - `skills/adversarial-spec/scripts/gauntlet.py:1-4087`
- **Observation:** gauntlet.py is 4087 lines containing: 7-phase pipeline orchestration, concern/evaluation/rebuttal data classes, filtering and clustering logic, multi-model evaluation with wave-based concurrency, medal/leaderboard tracking, report formatting, adversary stats persistence, and standalone CLI. This is 2-3x larger than typical maintainable module size.
- **Suggestion:** Consider splitting into: `gauntlet/pipeline.py` (phase orchestration), `gauntlet/evaluation.py` (concern evaluation + rebuttals), `gauntlet/stats.py` (medals, leaderboards, stats persistence), `gauntlet/report.py` (report formatting). Data classes could go in `gauntlet/types.py`.
- **Evidence:** 4087 lines. For comparison, debate.py is 1485 lines, models.py is 937 lines.

### FIND-003: cost_tracker relies on GIL for thread safety (Python 3.14+ risk)
- **Category:** performance
- **Severity:** warning
- **Confidence:** medium
- **Component:** models
- **Files:**
  - `skills/adversarial-spec/scripts/models.py:163-204`
- **Observation:** The global `cost_tracker` singleton is written to from multiple threads (one per model call via ThreadPoolExecutor) without synchronization. Dict updates to `by_model` are not atomic. Currently safe under GIL, but Python 3.14+ (PEP 703) may remove the GIL, making this a real race condition.
- **Suggestion:** Add a `threading.Lock` to `CostTracker.add()`. Minimal performance impact (lock is fast, contention rare), but future-proofs against GIL removal.
- **Evidence:** `cost_tracker.add()` called from `call_single_model()` which runs in ThreadPoolExecutor threads. No lock, no threading.Lock usage anywhere in models.py.

### FIND-004: No file locking on .claude/tasks.json (MCP server + TaskManager concurrent access)
- **Category:** error-handling
- **Severity:** warning
- **Confidence:** medium
- **Component:** mcp-tasks
- **Files:**
  - `mcp_tasks/server.py`
  - `skills/adversarial-spec/scripts/task_manager.py`
- **Observation:** Both MCP server and Python TaskManager read/write `.claude/tasks.json` without file locking. If a Claude Code agent calls MCP TaskUpdate while debate.py's TaskManager is writing, data loss is possible.
- **Suggestion:** Add file locking (e.g., `fcntl.flock` on Linux) to load_tasks/save_tasks in both files. Or use a single writer pattern where TaskManager goes through MCP.
- **Evidence:** `load_tasks()` and `save_tasks()` in both server.py and task_manager.py use plain `path.read_text()` / `path.write_text()` with no locking.

### FIND-005: Execution planner deprecation incomplete — __init__.py still exports 5+ dead types
- **Category:** dead-code
- **Severity:** info
- **Confidence:** high
- **Component:** execution-planner
- **Files:**
  - `execution_planner/__init__.py`
- **Observation:** The execution planner deprecation (Feb 2026) deleted dead modules but `__init__.py` still exports GauntletConcern, GauntletConcernParser, GauntletReport, LinkedConcern, load_concerns_for_spec. Some of these types (GauntletReport, LinkedConcern) may no longer be needed externally.
- **Suggestion:** Audit which exports are still imported elsewhere. Remove unused re-exports to complete the deprecation.
- **Evidence:** Deprecation spec at `.adversarial-spec/specs/execution-planner-deprecation.md` mentions Phase 3 (clean up exports) as PENDING.

### FIND-006: knowledge_service.py exists but is not wired into any flow
- **Category:** dead-code
- **Severity:** info
- **Confidence:** high
- **Component:** pre-gauntlet
- **Files:**
  - `skills/adversarial-spec/scripts/integrations/knowledge_service.py`
- **Observation:** knowledge_service.py implements a caching utility with Pydantic models for `~/.cache/adversarial-spec/knowledge/`. It's exported from `integrations/__init__.py` but not imported or called from the pre-gauntlet orchestrator or any other active code path.
- **Suggestion:** Either wire into the pre-gauntlet flow (it appears designed for this) or remove. Its presence with full implementation but no integration is confusing.
- **Evidence:** `grep -r "knowledge_service\|KnowledgeService" scripts/` returns only the definition file and `__init__.py` re-export.

### FIND-007: Subprocess commands built from user-controlled model names without sanitization
- **Category:** security
- **Severity:** info
- **Confidence:** low
- **Component:** models
- **Files:**
  - `skills/adversarial-spec/scripts/models.py:351-616`
- **Observation:** CLI model names (e.g., `codex/gpt-5.3-codex`) are passed through to subprocess command arrays. While subprocess.run with list arguments (not shell=True) prevents shell injection, the model name becomes a CLI argument. If a user provides a malicious model name via `--models`, it could potentially be interpreted as a CLI flag by the subprocess tool.
- **Suggestion:** Validate model names against an allowed character set (alphanumeric, hyphens, slashes, dots) before passing to subprocess. This is defense-in-depth — the current list-based subprocess.run is already safe against shell injection.
- **Evidence:** models.py:399 `cmd = ["codex", "exec", "--json", "--full-auto", "-m", model_name, ...]` — model_name comes from CLI args without character validation.

---

## Summary
- **Total findings:** 7
- **By severity:** info: 3 | warning: 4 | error: 0
- **Top concern:** FIND-003 (cost_tracker GIL reliance) and FIND-004 (tasks.json no locking) — both are latent concurrency issues that will surface under specific conditions.
- **Confidence breakdown:** high: 3 | medium: 3 | low: 1


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: .architecture/INDEX.md (80 lines, 4688 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# Architecture: adversarial-spec

> Generated: 2026-03-18 | Git: 0eb7ad9 | Target: /home/jason/PycharmProjects/adversarial-spec
> Skill version: 2.6 | Model: claude-opus-4-6

## System Summary

adversarial-spec is a Claude Code skill that refines product specifications through multi-model debate and adversarial stress-testing. A CLI tool sends specs to multiple LLMs in parallel, collects critiques, and iterates until consensus. A gauntlet mode runs specs through named adversary personas (security paranoid, burned oncall, UX skeptic, etc.) in a 7-phase attack-evaluate-rebuttal pipeline. The system is stateless per invocation, with session persistence enabling manual multi-round iteration.

## Components

| Component | Purpose | Entry Point | Key Files |
|-----------|---------|-------------|-----------|
| Debate Engine | Multi-model spec critique CLI | `main()` at debate.py:1443 | debate.py, session.py |
| Gauntlet | 7-phase adversarial stress-testing | `run_gauntlet()` at gauntlet.py:3290 | gauntlet.py, adversaries.py |
| Models | LLM call abstraction (LiteLLM + CLI) | `call_models_parallel()` at models.py:894 | models.py |
| Providers | Config, credentials, costs, Bedrock | `validate_model_credentials()` at providers.py:436 | providers.py |
| Prompts | Templates, focus areas, personas | `get_system_prompt()` at prompts.py:125 | prompts.py |
| Adversaries | Named attacker persona definitions | `ADVERSARIES` dict | adversaries.py |
| Session | State persistence and checkpoints | `SessionState` at session.py:17 | session.py |
| Pre-Gauntlet | Git/system context collection | `PreGauntletOrchestrator.run()` at orchestrator.py:51 | pre_gauntlet/, collectors/, integrations/ |
| MCP Tasks | Cross-agent task coordination | `mcp.run()` at server.py:365 | mcp_tasks/server.py |
| Task Manager | Python task management API | `TaskManager` at task_manager.py:114 | task_manager.py |
| Execution Planner | Gauntlet concern parsing (deprecated) | `GauntletConcernParser` | execution_planner/gauntlet_concerns.py |

## Navigation

**Understand the system:**

| Question | Read |
|----------|------|
| What does this system do? | [overview.md](overview.md) |
| Where is code located? | [filesystem-map.md](filesystem-map.md) |
| What patterns does the code use? | [patterns.md](patterns.md) |
| What architectural issues exist? | [findings.md](findings.md) |

**Work on specific tasks:**

| Task | Read |
|------|------|
| Add a new model provider | [components/models.md](structured/components/models.md), [components/providers.md](structured/components/providers.md) |
| Add a new adversary persona | [components/adversaries.md](structured/components/adversaries.md), [components/gauntlet.md](structured/components/gauntlet.md) |
| Modify the critique flow | [components/debate-engine.md](structured/components/debate-engine.md) |
| Change prompt templates | [components/prompts.md](structured/components/prompts.md) |
| Work on pre-gauntlet context | [components/pre-gauntlet.md](structured/components/pre-gauntlet.md) |
| Modify MCP task tools | [components/mcp-tasks.md](structured/components/mcp-tasks.md) |

**Deep reference:**

| Need | Read |
|------|------|
| All entry points | [entry-points.md](structured/entry-points.md) |
| Flow-by-flow breakdown | [flows.md](structured/flows.md) |
| Call graphs and data paths | [cross-references.md](structured/cross-references.md) |
| Visual diagrams (humans) | [HUMAN_READ_ONLY_visuals/](HUMAN_READ_ONLY_visuals/) |

## Architecture Decisions

Key patterns in this codebase:
- **Single-invocation CLI**: No daemon. Each command is one round or one gauntlet run. Sessions enable resumability.
- **Thread-per-model parallelism**: ThreadPoolExecutor dispatches to all models simultaneously.
- **CLI subprocess routing**: Codex/Gemini/Claude called via subprocess for file access capability at zero token cost.
- **LiteLLM abstraction**: 7+ API providers unified behind `litellm.completion()`.
- **Checkpoint persistence**: JSON files after each gauntlet phase and each debate round for crash recovery.
- **Layered dependencies**: CLI → Orchestration → LLM → Config. No circular imports.
- **Isolated pre-gauntlet**: Context collection subsystem has zero imports from debate/gauntlet modules.

## Generation Info

| Field | Value |
|-------|-------|
| Generated by | `/mapcodebase` |
| Skill version | 2.6 |
| Model | claude-opus-4-6 |
| Generated | 2026-03-18 |
| Git hash | 0eb7ad9 |
| Update | `/mapcodebase --update` |
| Full regen | `/mapcodebase` |

To check if this mapping is stale, compare the skill version above against `~/.claude/skills/mapcodebase/VERSION.md`. Major version mismatch = full re-scan needed.


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: .architecture/filesystem-map.md (92 lines, 4433 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
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


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: .architecture/structured/entry-points.md (117 lines, 7743 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# Entry Points

> All system entrances: where execution begins or external input arrives.
> Generated: 2026-03-18 | Git: 0eb7ad9

## Summary

25 entry points found: 11 CLI commands, 4 MCP tools, 1 polling loop, 2 pre-gauntlet APIs, 4 library exports, 3 info/utility handlers. The system is CLI-driven with `debate.py` as the primary entry, routing to action handlers.

## Entry Point Table

```
ENTRY_POINT                      FILE:LINE                                TYPE     TRIGGER                          CALLS
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
main()                           scripts/debate.py:1443                   cli      `adversarial-spec` command       create_parser(), handle_*, run_critique()
main()                           scripts/gauntlet.py:3836                 cli      Direct script / __name__:4086    run_gauntlet(), format_gauntlet_report()
main()                           scripts/telegram_bot.py:404              cli      Direct script / __name__:442     cmd_setup(), cmd_send(), cmd_poll(), cmd_notify()
handle_info_command()            scripts/debate.py:610                    cli      Info-type actions                list_providers(), list_personas(), etc.
handle_utility_command()         scripts/debate.py:682                    cli      Utility actions                  handle_bedrock_command(), save_profile()
handle_execution_plan()          scripts/debate.py:731                    cli      action == "execution-plan"       Execution plan handlers
handle_gauntlet()                scripts/debate.py:989                    cli      action == "gauntlet"             run_gauntlet(), format_gauntlet_report()
handle_send_final()              scripts/debate.py:920                    cli      action == "send-final"           Model calls for final output
handle_export_tasks()            scripts/debate.py:938                    cli      action == "export-tasks"         extract_tasks(), models
run_critique()                   scripts/debate.py:1156                   cli      Critique workflow                call_models_parallel(), generate_diff()
task_manager demo                scripts/task_manager.py:665              main     __name__ == "__main__"           TaskManager(), create_adversarial_spec_session()
mcp.run()                        mcp_tasks/server.py:365                  export   MCP protocol launch              FastMCP.run()
TaskCreate                       mcp_tasks/server.py:98                   export   MCP tool call                    load_tasks(), save_tasks()
TaskGet                          mcp_tasks/server.py:140                  export   MCP tool call                    load_tasks()
TaskList                         mcp_tasks/server.py:160                  export   MCP tool call                    load_tasks()
TaskUpdate                       mcp_tasks/server.py:261                  export   MCP tool call                    load_tasks(), save_tasks()
discover_chat_id()               scripts/telegram_bot.py:223              event    cmd_setup() → infinite poll      api_call() in while True loop
PreGauntletOrchestrator.run()    scripts/pre_gauntlet/orchestrator.py:51  export   Called from gauntlet/debate      collectors, extractors, context_builder
run_pre_gauntlet()               scripts/pre_gauntlet/orchestrator.py:207 export   Public API function              PreGauntletOrchestrator.run()
run_gauntlet()                   scripts/gauntlet.py:3290                 export   Called from debate.py            adversary calls, evaluations, medals
call_models_parallel()           scripts/models.py:894                    export   Called from run_critique()        ThreadPoolExecutor, call_single_model()
TaskManager                      scripts/task_manager.py:114              export   Lazy-loaded by debate.py         create_task(), update_task(), list_tasks()
SessionState                     scripts/session.py:17                    export   Called for persistence            load(), save(), save_checkpoint()
execution_planner exports        execution_planner/__init__.py:9          export   from execution_planner import    GauntletConcernParser, load_concerns_for_spec()
mcp_tasks exports                mcp_tasks/__init__.py:3                  export   from mcp_tasks import mcp        FastMCP server instance
```

Types: `main` | `cli` | `export` | `event`

## By Type

### Main / CLI Entry Points

```
ENTRY: main()
FILE: skills/adversarial-spec/scripts/debate.py:1443
TRIGGER: `adversarial-spec <action>` (pyproject.toml entry point) or __name__ at :1484
CALLS: create_parser(), handle_info_command(), handle_utility_command(), handle_execution_plan(),
       handle_gauntlet(), apply_profile(), parse_models(), setup_bedrock(),
       validate_models_before_run(), load_or_resume_session(), run_critique()
NOTES: Main orchestrator. Routes to action handlers based on argparse subcommands.
       Actions: critique, gauntlet, providers, focus-areas, personas, profiles, sessions,
       gauntlet-adversaries, adversary-stats, medal-leaderboard, adversary-versions,
       bedrock, save-profile, diff, send-final, export-tasks, execution-plan
```

```
ENTRY: main()
FILE: skills/adversarial-spec/scripts/gauntlet.py:3836
TRIGGER: Direct script execution (__name__:4086) or called from debate.py
CALLS: run_gauntlet(), format_gauntlet_report(), list_gauntlet_runs(), load_gauntlet_run(), get_adversary_leaderboard()
NOTES: Standalone gauntlet CLI with argparse. Returns JSON or formatted report.
```

```
ENTRY: main()
FILE: skills/adversarial-spec/scripts/telegram_bot.py:404
TRIGGER: Direct script execution (__name__:442)
CALLS: create_parser with subparsers → cmd_setup(), cmd_send(), cmd_poll(), cmd_notify()
NOTES: 4 subcommands. Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars.
```

### MCP / Server Entry Points

```
ENTRY: mcp.run()
FILE: mcp_tasks/server.py:365
TRIGGER: MCP protocol (registered in pyproject.toml as `mcp-tasks`)
CALLS: FastMCP.run() — exposes 4 tools via decorators:
       TaskCreate (line 98), TaskGet (line 140), TaskList (line 160), TaskUpdate (line 261)
NOTES: Shares storage with task_manager.py via .claude/tasks.json.
       Supports session_id, context_name, and status filtering. Supports list_contexts mode.
```

### Event / Polling Entry Points

```
ENTRY: discover_chat_id()
FILE: skills/adversarial-spec/scripts/telegram_bot.py:223
TRIGGER: Called from cmd_setup()
CALLS: api_call() in infinite while True loop (line 238)
NOTES: Polls Telegram API until user sends message. Runs until Ctrl+C.
```

### Library / Orchestrator Entry Points

```
ENTRY: PreGauntletOrchestrator.run()
FILE: skills/adversarial-spec/scripts/pre_gauntlet/orchestrator.py:51
TRIGGER: Called from debate.py or gauntlet.py before main gauntlet
CALLS: GitPositionCollector.collect(), SystemStateCollector.collect(),
       extract_spec_affected_files(), build_context(), run_alignment_mode()
NOTES: Returns PreGauntletResult. Can be disabled per doc_type via CompatibilityConfig.
```

```
ENTRY: call_models_parallel()
FILE: skills/adversarial-spec/scripts/models.py:894
TRIGGER: Called from debate.py:run_critique()
CALLS: ThreadPoolExecutor → call_single_model() per model
       Routes to: litellm.completion(), call_codex_model(), call_gemini_cli_model(), call_claude_cli_model()
NOTES: Returns list[ModelResponse]. Retries with exponential backoff (3 attempts, 1s/2s/4s).
```


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: .architecture/structured/flows.md (350 lines, 11177 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# Structured Flows

> Every significant flow in structured notation. Optimized for LLM consumption.
> Generated: 2026-03-18 | Git: 0eb7ad9

## Notation

```
FLOW: name
TRIGGER: what initiates this flow
ENTRY: function(file:line)
STATUS: implemented | partial | disabled
STEPS:
  1. action -> next_action
  2. action [condition] -> branch_a | branch_b
DATA_IN:
  - param_name: type (description)
DATA_OUT:
  - return_value: type (description)
EXITS_TO: destination_flow(s)
```

All 7 fields are required for every flow. If a field doesn't apply, write `none`.

---

## Lifecycle Flows

### FLOW: debate_startup

```
TRIGGER: User runs `debate.py critique` with spec input
ENTRY: main() (scripts/debate.py:1443)
STATUS: implemented

STEPS:
  1. create_parser() -> parse CLI arguments
  2. [action == info_command] -> handle_info_command() | continue
  3. [action == utility_command] -> handle_utility_command() | continue
  4. [action == execution-plan] -> handle_execution_plan() | continue
  5. [action == gauntlet] -> handle_gauntlet() | continue
  6. apply_profile(args) -> merge profile settings into args
  7. parse_models(args) -> resolve model list
  8. [bedrock enabled] -> setup_bedrock() | continue
  9. validate_models_before_run() -> check API keys
  10. load_or_resume_session() -> get/create session state
  11. run_critique() -> enter debate loop

DATA_IN:
  - spec: str (markdown spec via stdin or --spec-file)
  - models: list[str] (from --models or profile)
  - doc_type: str (spec|prd|tech|debug)
  - focus: Optional[str] (focus area name)
  - persona: Optional[str] (persona name)

DATA_OUT:
  - none (outputs to stdout, session file, optional telegram)

EXITS_TO: debate_round_loop
```

### FLOW: session_resume

```
TRIGGER: User runs debate.py with --resume <session_id>
ENTRY: load_or_resume_session() (scripts/debate.py)
STATUS: implemented

STEPS:
  1. SessionState.load(session_id) -> read JSON from sessions dir
  2. Validate path is within SESSIONS_DIR (security check)
  3. Restore spec, round number, models, focus, persona
  4. [session has history] -> display last round summary | skip
  5. Return restored session state

DATA_IN:
  - session_id: str (session identifier)

DATA_OUT:
  - session: SessionState (restored state with spec, round, history)

EXITS_TO: debate_round_loop
```

---

## Data Processing Flows

### FLOW: debate_round_loop

```
TRIGGER: Called from debate_startup after session is loaded
ENTRY: run_critique() (scripts/debate.py:1156)
STATUS: implemented

STEPS:
  1. log_input_stats() -> calculate line count and SHA256 hash
  2. Build system prompt via get_system_prompt(doc_type, persona, focus)
  3. Build user message via REVIEW_PROMPT_TEMPLATE with spec + context
  4. call_models_parallel(models, system_prompt, user_message) -> list[ModelResponse]
  5. Filter successful responses (no errors)
  6. Extract agreement: all_agreed = all(r.agreed for r in successful)
  7. [any response has revised spec] -> update session.spec | keep current
  8. SessionState.save() -> persist round results
  9. save_checkpoint(round_num, spec) -> write .adversarial-spec-checkpoints/
  10. save_critique_responses(results, round_num) -> write critiques JSON
  11. [telegram enabled] -> send_telegram_notification() | skip
  12. output_results() -> JSON or formatted text to stdout

DATA_IN:
  - session: SessionState (current spec, round number, models)
  - args: argparse.Namespace (CLI options)

DATA_OUT:
  - output: dict (JSON with responses, agreement status, cost)
  - side_effects: session file updated, checkpoint written, critiques JSON saved

EXITS_TO: none (terminal — one round per invocation, user decides next round)
```

### FLOW: model_call

```
TRIGGER: Called from call_models_parallel() for each model
ENTRY: call_single_model() (scripts/models.py:619)
STATUS: implemented

STEPS:
  1. [model starts with "codex/"] -> call_codex_model() | continue
  2. [model starts with "gemini-cli/"] -> call_gemini_cli_model() | continue
  3. [model starts with "claude-cli/"] -> call_claude_cli_model() | continue
  4. litellm.completion(model, messages) -> raw response
  5. Extract response text from completion
  6. Detect agreement: search for "[AGREE]" marker
  7. [has [SPEC]...[/SPEC] tags] -> extract revised spec | spec=None
  8. cost_tracker.add(model, input_tokens, output_tokens)
  9. Return ModelResponse

DATA_IN:
  - model: str (model identifier)
  - system_prompt: str (instructions)
  - user_message: str (spec + prompt)

DATA_OUT:
  - response: ModelResponse (model, response, agreed, spec, tokens, cost)

EXITS_TO: debate_round_loop (collected by ThreadPoolExecutor)
```

### FLOW: gauntlet_pipeline

```
TRIGGER: User runs `debate.py gauntlet` or `gauntlet.py`
ENTRY: run_gauntlet() (scripts/gauntlet.py:3290)
STATUS: implemented

STEPS:
  1. Parse adversary list and model selection
  2. Phase 1: Generate concerns (parallel per adversary, ThreadPoolExecutor max_workers=5)
     - For each adversary: build persona prompt, call LLM, extract Concern objects
     - Persist to .adversarial-spec-gauntlet/concerns-{hash}.json
     - Persist raw responses to raw-responses-{hash}.json
  3. Phase 2: Big Picture Synthesis
     - LLM synthesizes patterns across all concerns
     - Returns real_issues, hidden_connections, meta_concern, high_signal
  4. Phase 3: Filter concerns against resolved historical concerns
     - Returns filtered, dropped, noted lists
  5. Phase 3.5: Cluster near-duplicate concerns via LLM
     - Reduces volume, preserves cluster_members mapping
  6. Phase 4: Multi-model evaluation (batched, 15 concerns per batch, wave-based concurrency)
     - For each concern: multiple eval models produce verdict (accepted/dismissed/acknowledged/deferred)
     - Persist evaluations to evaluations-{hash}.json
  7. Phase 5: Rebuttals for dismissed concerns (parallel per batch)
     - Adversary rebuts using REBUTTAL_PROMPT
     - Returns sustained: bool per rebuttal
  8. Phase 6: Final adjudication for sustained rebuttals
     - Final model reviews challenge vs dismissal
  9. Phase 7: [--final-boss or interactive prompt] -> Final Boss UX review (Opus 4.6) | skip
     - Returns PASS/REFINE/RECONSIDER verdict with UX concerns
  10. format_gauntlet_report() -> formatted output
  11. Track dedup stats and medal awards

DATA_IN:
  - spec: str (specification markdown)
  - adversaries: list[str] (adversary names, or "all")
  - models: list[str] (attack, eval, clustering models)

DATA_OUT:
  - report: GauntletResult (concerns, evaluations, rebuttals, medals, big_picture, final_boss)

EXITS_TO: terminal (report output)
```

### FLOW: cost_tracking

```
TRIGGER: Every model call completion
ENTRY: CostTracker.add() (scripts/models.py:163)
STATUS: implemented

STEPS:
  1. Look up model in MODEL_COSTS dict (providers.py:18-47)
  2. Calculate: cost = (input_tokens/1M * input_rate) + (output_tokens/1M * output_rate)
  3. [CLI model (codex/, gemini-cli/, claude-cli/)] -> cost = 0 | standard rate
  4. Accumulate in global totals and per-model breakdown (by_model dict)
  5. [output requested] -> CostTracker.summary() formats human-readable string

DATA_IN:
  - model: str (model identifier)
  - input_tokens: int
  - output_tokens: int

DATA_OUT:
  - cost: float (accumulated in singleton)

EXITS_TO: included in debate output, gauntlet report, telegram notifications
```

### FLOW: pre_gauntlet_context

```
TRIGGER: Called before gauntlet run when pre-gauntlet is enabled
ENTRY: PreGauntletOrchestrator.run() (scripts/pre_gauntlet/orchestrator.py:51)
STATUS: implemented

STEPS:
  1. Check if pre-gauntlet enabled for doc type (config.get_doc_type_rule)
  2. Extract spec-affected files (regex analysis of spec)
  3. [require_git] -> GitPositionCollector.collect() | skip
     - Current branch, commits, staleness check
  4. [require_build] -> SystemStateCollector.collect() | skip
     - Run build command with timeout, extract schemas, walk dirs
  5. build_context() -> assemble markdown document
  6. [alignment_mode] -> run_alignment_mode() (LLM confirms context matches spec) | skip

DATA_IN:
  - spec_text: str (specification)
  - doc_type: DocType
  - config: CompatibilityConfig

DATA_OUT:
  - result: PreGauntletResult (status, context_markdown, concerns, timings)

EXITS_TO: gauntlet_pipeline (context passed as additional input)
```

---

## Background Flows

### FLOW: telegram_notification

```
TRIGGER: Round completion when --telegram flag is set
ENTRY: send_telegram_notification() (scripts/debate.py:185)
STATUS: implemented

STEPS:
  1. Format round results into message text
  2. telegram_bot.send_long_message() -> split at 4096 char boundaries
  3. For each chunk: api_call("sendMessage", {chat_id, text}) -> HTTP POST
  4. [poll_timeout > 0] -> poll_for_reply() with getUpdates | skip
  5. [reply received] -> return user feedback text | return None

DATA_IN:
  - results: list[ModelResponse]
  - round_num: int
  - poll_timeout: int (seconds)

DATA_OUT:
  - feedback: Optional[str] (user's Telegram reply)

EXITS_TO: debate_round_loop (feedback available for next round)
```

---

## Error Recovery Flows

### FLOW: model_call_retry

```
TRIGGER: Model call failure (timeout, API error, subprocess error)
ENTRY: call_single_model() retry loop (scripts/models.py:619)
STATUS: implemented

STEPS:
  1. Attempt model call
  2. [success] -> return ModelResponse | continue
  3. [attempt < MAX_RETRIES (3)] -> sleep(RETRY_BASE_DELAY * 2^attempt) -> retry | fail
  4. [all retries exhausted] -> return ModelResponse with error field set

DATA_IN:
  - model: str
  - system_prompt: str
  - user_message: str

DATA_OUT:
  - response: ModelResponse (may have error field populated)

EXITS_TO: call_models_parallel (error responses filtered by debate loop)
```

### FLOW: session_state_persistence

```
TRIGGER: Round completion, session save, or checkpoint
ENTRY: SessionState.save() (scripts/session.py:32)
STATUS: implemented

STEPS:
  1. Serialize session state to JSON
  2. Validate path is within SESSIONS_DIR (prevent directory traversal via is_relative_to)
  3. Write JSON to sessions/{session_id}.json
  4. [checkpoint] -> write spec to .adversarial-spec-checkpoints/round-{N}.md
  5. [critique responses] -> write JSON to checkpoints/round-{N}-critiques.json

DATA_IN:
  - session: SessionState

DATA_OUT:
  - none (file system side effects)

EXITS_TO: none
```

### FLOW: provider_validation

```
TRIGGER: Before model calls in debate startup
ENTRY: validate_model_credentials() (scripts/providers.py:436)
STATUS: implemented

STEPS:
  1. For each model: determine provider from prefix (gpt-, claude-, gemini/, etc.)
  2. Check required env var (OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, etc.)
  3. [CLI tool model] -> check shutil.which() for binary availability | check env var
  4. [bedrock mode] -> resolve friendly name to Bedrock model ID, check AWS config
  5. Return (valid_models, invalid_models)
  6. [any invalid] -> print error, sys.exit(2) | continue

DATA_IN:
  - models: list[str] (model identifiers)

DATA_OUT:
  - valid_models: list[str]
  - invalid_models: list[str]

EXITS_TO: debate_round_loop (if all valid) or sys.exit(2)
```


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: .architecture/structured/cross-references.md (204 lines, 11883 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# Cross References

> Call graphs, data paths, and dependency lookups.
> Generated: 2026-03-18 | Git: 0eb7ad9

## Function Call Graph

### Debate Engine

```
main() (scripts/debate.py:1443)
  ├── calls: create_parser(), handle_info_command(), handle_utility_command(),
  │          handle_execution_plan(), handle_gauntlet(), apply_profile(),
  │          parse_models(), setup_bedrock(), validate_models_before_run(),
  │          load_or_resume_session(), run_critique()
  ├── called_by: CLI invocation (__name__:1484)
  └── async: no

handle_info_command() (scripts/debate.py:610)
  ├── calls: list_providers(), list_focus_areas(), list_personas(), list_profiles(),
  │          SessionState.list_sessions(), get_adversary_leaderboard(), get_medal_leaderboard(),
  │          print_version_manifest()
  ├── called_by: main()
  └── async: no

handle_utility_command() (scripts/debate.py:682)
  ├── calls: handle_bedrock_command(), save_profile()
  ├── called_by: main()
  └── async: no

handle_gauntlet() (scripts/debate.py:989)
  ├── calls: run_gauntlet(), format_gauntlet_report()
  ├── called_by: main()
  └── async: no

run_critique() (scripts/debate.py:1156)
  ├── calls: log_input_stats(), get_task_manager(), call_models_parallel(),
  │          generate_diff(), get_critique_summary(), send_telegram_notification(),
  │          save_checkpoint(), save_critique_responses(), SessionState.save(),
  │          output_results()
  ├── called_by: main()
  └── async: no
```

### Models

```
call_models_parallel() (scripts/models.py:894)
  ├── calls: ThreadPoolExecutor, call_single_model() (per model, max_workers=len(models))
  ├── called_by: run_critique(), gauntlet phases
  └── async: no (thread-parallel)

call_single_model() (scripts/models.py:619)
  ├── calls: call_codex_model(), call_gemini_cli_model(), call_claude_cli_model(),
  │          litellm.completion(), cost_tracker.add(), detect_agreement(), extract_spec()
  ├── called_by: call_models_parallel()
  └── async: no

call_codex_model() (scripts/models.py:351)
  ├── calls: subprocess.run("codex exec --json --full-auto"), parse JSONL events
  ├── called_by: call_single_model()
  └── async: no (subprocess blocks)

call_gemini_cli_model() (scripts/models.py:451)
  ├── calls: subprocess.run("gemini -m <model> -y"), filter noise prefixes
  ├── called_by: call_single_model()
  └── async: no (subprocess blocks)

call_claude_cli_model() (scripts/models.py:536)
  ├── calls: subprocess.run("claude -p --json-out"), parse JSON formats
  ├── called_by: call_single_model()
  └── async: no (subprocess blocks)
```

### Gauntlet

```
run_gauntlet() (scripts/gauntlet.py:3290)
  ├── calls: generate_attacks() (ThreadPoolExecutor, max_workers=5),
  │          generate_big_picture_synthesis(), filter_concerns_with_explanations(),
  │          cluster_concerns_with_provenance(), evaluate_concerns_multi_model(),
  │          format_gauntlet_report(), _track_dedup_stats()
  ├── called_by: handle_gauntlet() (debate.py), gauntlet.py:main()
  └── async: no (thread-parallel per phase)

evaluate_concerns_multi_model() (scripts/gauntlet.py:2172)
  ├── calls: ThreadPoolExecutor per model, litellm.completion(), normalize_verdict()
  ├── called_by: run_gauntlet()
  └── async: no (thread-parallel, batched 15 concerns, wave-based concurrency)
```

### Pre-Gauntlet

```
PreGauntletOrchestrator.run() (scripts/pre_gauntlet/orchestrator.py:51)
  ├── calls: extract_spec_affected_files(), GitPositionCollector.collect(),
  │          SystemStateCollector.collect(), build_context(), run_alignment_mode()
  ├── called_by: debate.py, gauntlet.py
  └── async: no

GitPositionCollector.collect() (scripts/collectors/git_position.py)
  ├── calls: GitCli.current_branch(), GitCli.diff_stat(), GitCli.log()
  ├── called_by: PreGauntletOrchestrator.run()
  └── async: no

SystemStateCollector.collect() (scripts/collectors/system_state.py)
  ├── calls: ProcessRunner.run(), file reads
  ├── called_by: PreGauntletOrchestrator.run()
  └── async: no
```

## Data Path Summary

```
DATA_PATH               SOURCE                    TRANSFORMS                              SINK
──────────────────────────────────────────────────────────────────────────────────────────────────────────
spec_critique           stdin/file                prompt_build → model_call → agree_check  stdout JSON + session file
gauntlet_review         stdin spec                adversary_gen → filter → cluster → eval  gauntlet JSON files + stdout
cost_tracking           model responses           token_count → rate_lookup → accumulate   stdout summary
telegram_notify         round results             format → split_chunks → api_call         Telegram HTTP API
session_persist         round completion          serialize → validate_path → write         sessions/*.json
checkpoint_save         round completion          spec → markdown + critiques → JSON       checkpoints/round-N.*
config_load             env vars + files          env_read → profile_merge → validate      in-memory config
pre_gauntlet_ctx        git + system state        collect → build_context → align          context markdown
```

## Hub Files

Files imported by many others (high-impact change targets):

```
FILE                              IMPORTED_BY_COUNT   EXPORTS
──────────────────────────────────────────────────────────────────────────────────
scripts/prompts.py                5+                  FOCUS_AREAS, PERSONAS, get_system_prompt(), REVIEW_PROMPT_TEMPLATE,
                                                      PRESS_PROMPT_TEMPLATE, EXPORT_TASKS_PROMPT, get_doc_type_name(),
                                                      PRESERVE_INTENT_PROMPT
scripts/providers.py              3+                  MODEL_COSTS, validate_model_credentials(), load_profile(),
                                                      save_profile(), list_providers(), list_focus_areas(), list_personas(),
                                                      list_profiles(), handle_bedrock_command(), DEFAULT_CODEX_REASONING
scripts/models.py                 3+                  ModelResponse, call_models_parallel(), cost_tracker, extract_tasks(),
                                                      generate_diff(), get_critique_summary(), is_o_series_model(),
                                                      load_context_files(), detect_agreement(), extract_spec()
scripts/adversaries.py            3+                  Adversary, ADVERSARIES, FINAL_BOSS, PRE_GAUNTLET, PARANOID_SECURITY,
                                                      BURNED_ONCALL, generate_concern_id(), ADVERSARY_PREFIXES
pre_gauntlet/models.py            5+                  CompatibilityConfig, PreGauntletResult, PreGauntletStatus,
                                                      DocType, ContextSummary
```

## Shared Utilities

```
UTILITY                           FILE:LINE                              USED_BY (count)
──────────────────────────────────────────────────────────────────────────────────────────
get_system_prompt()               scripts/prompts.py:125                 2+ (models, debate)
validate_model_credentials()      scripts/providers.py:436               2+ (debate, providers)
cost_tracker.add()                scripts/models.py:163                  3+ (call_single_model routes, gauntlet)
generate_concern_id()             scripts/adversaries.py                 2+ (gauntlet, gauntlet_concerns)
build_context()                   scripts/pre_gauntlet/context_builder   2+ (orchestrator, tests)
get_tasks_file()                  scripts/task_manager.py                2+ (TaskManager, MCP server)
load_context_files()              scripts/models.py:207                  2+ (debate, models)
```

## External Dependencies

```
PACKAGE                 USED_FOR                                    KEY_USAGE_SITES
──────────────────────────────────────────────────────────────────────────────────────────
litellm                 Universal LLM API wrapper                   models.py (completion()), gauntlet.py
mcp (fastmcp)           MCP server framework                        mcp_tasks/server.py (FastMCP)
pydantic                Data validation (pre-gauntlet models)       pre_gauntlet/models.py (BaseModel)
concurrent.futures      Parallel model calls                        models.py (ThreadPoolExecutor), gauntlet.py
subprocess              CLI tool invocation (Codex, Gemini, Claude) models.py, integrations/git_cli.py, process_runner.py
argparse                CLI argument parsing                        debate.py, gauntlet.py, telegram_bot.py
urllib                  Telegram Bot API HTTP calls                 telegram_bot.py (urlopen, Request)
hashlib                 Spec hashing, concern IDs                   debate.py, adversaries.py, gauntlet.py
pytest                  Test framework                              tests/*.py
ruff                    Linting                                     pyproject.toml
```

## Config Sources

```
CONFIG                          SOURCE              ACCESSED_BY
──────────────────────────────────────────────────────────────────────────────────
OPENAI_API_KEY                  env var             providers.py, gauntlet.py
ANTHROPIC_API_KEY               env var             providers.py, gauntlet.py
GEMINI_API_KEY                  env var             providers.py, gauntlet.py
XAI_API_KEY                     env var             providers.py
GROQ_API_KEY                    env var             providers.py, gauntlet.py
DEEPSEEK_API_KEY                env var             gauntlet.py
MISTRAL_API_KEY                 env var             providers.py
TELEGRAM_BOT_TOKEN              env var             telegram_bot.py
TELEGRAM_CHAT_ID                env var             telegram_bot.py
MCP_WORKING_DIR                 env var             task_manager.py, mcp_tasks/server.py
LITELLM_LOG                     env var (set)       debate.py:65, models.py:16 (hardcoded to "ERROR")
AWS_REGION/PROFILE/ROLE_ARN     env vars            providers.py (Bedrock config)
CLAUDE_CODE, CC_WORKSPACE       env var             gauntlet.py (environment detection)
GEMINI_PAID_TIER, CLAUDE_PAID_TIER env var          gauntlet.py (pricing detection)
~/.claude/adv-spec/config.json  file                providers.py (global Bedrock config)
~/.config/adv-spec/profiles/    directory           providers.py (saved profiles)
~/.config/adv-spec/sessions/    directory           session.py (session persistence)
~/.cache/adv-spec/knowledge/    directory           integrations/knowledge_service.py (cache)
.claude/tasks.json              file                task_manager.py, mcp_tasks/server.py
```


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: .architecture/structured/components/debate-engine.md (103 lines, 4686 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# Component: Debate Engine

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Orchestrates multi-model spec critique rounds until consensus |
| Entry | `main()` at scripts/debate.py:1443 |
| Key files | debate.py (1485 lines), session.py |
| Depends on | Models, Providers, Prompts, Gauntlet, Session, TaskManager (optional), Telegram (optional) |
| Used by | CLI invocation, Claude Code skill |

## What This Component Does

The debate engine is the primary user-facing entry point. It takes a draft specification, sends it to multiple LLM models for critique, collects their responses, checks for consensus (all models agree via `[AGREE]` marker), and outputs the result. It manages CLI actions through a single `main()` function that routes to specialized handlers. Each invocation is one round — the user decides whether to iterate.

## Data Flow

```
IN:  spec text (stdin or --spec-file)
     + CLI arguments (models, focus, persona, doc_type)
     └─> main() (debate.py:1443)

PROCESS:
     ├─> parse arguments and apply profile
     ├─> validate model credentials
     ├─> load or resume session
     ├─> call_models_parallel() for the round
     ├─> check agreement, update session
     ├─> save checkpoint + critique responses
     └─> output results (JSON/text/telegram)

OUT: JSON output to stdout
     + session file (sessions/{id}.json)
     + checkpoint (checkpoints/round-N.md)
     + critiques (checkpoints/round-N-critiques.json)
     └─> debate.py:output_results()
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `main()` | CLI entry, argument parsing, action routing | debate.py:1443 |
| `run_critique()` | Core debate round — calls models, checks agreement | debate.py:1156 |
| `handle_info_command()` | Lists providers, focus areas, personas, sessions, adversaries | debate.py:610 |
| `handle_utility_command()` | Bedrock setup, profile save | debate.py:682 |
| `handle_gauntlet()` | Invokes adversarial gauntlet | debate.py:989 |
| `handle_send_final()` | Sends final spec to models | debate.py:920 |
| `handle_export_tasks()` | Extracts tasks via LLM | debate.py:938 |
| `output_results()` | Formats and prints round results | debate.py |
| `send_telegram_notification()` | Sends results to Telegram, polls for reply | debate.py:185 |

## Common Patterns

### Action Routing

`main()` uses a series of conditional checks on `args.action` to dispatch to handlers. Info commands and utility commands are checked first (early return), then gauntlet and execution plan, with critique as the default.

### Optional Feature Loading

Telegram, task tracking, and execution planner are all lazy-loaded with try/except ImportError guards. This keeps the core debate loop functional without optional dependencies.

### Input Stats Logging

`log_input_stats()` at debate.py:114 computes line count and SHA256 hash of input spec to detect if compression/summarization has altered the spec between rounds.

## Error Handling

- **Model call failures**: Handled in models.py with retries. Debate engine filters out error responses and continues with successful ones.
- **Missing API keys**: `validate_models_before_run()` checks credentials before starting. Exits with code 2 if keys missing.
- **Missing stdin**: Exits with code 1 if no spec provided.
- **Session corruption**: Session load validates JSON structure. Corrupt sessions logged and skipped.

## Configuration

| Config | Source | Default |
|--------|--------|---------|
| Models | `--models` CLI or profile | First available provider |
| Doc type | `--doc-type` CLI | `spec` |
| Focus | `--focus` CLI or profile | None (general critique) |
| Persona | `--persona` CLI or profile | None (default reviewer) |
| Telegram | `--telegram --poll-timeout` | Disabled |

## Integration Points

**Calls out to:**
- `Models.call_models_parallel()` — for LLM critique calls
- `Gauntlet.run_gauntlet()` — for adversarial review
- `Session.save()/load()` — for state persistence
- `Telegram.send_telegram_notification()` — for async feedback (optional)
- `TaskManager` — for MCP task tracking (optional, lazy-loaded)

**Called by:**
- CLI invocation by user or Claude Code skill

## LLM Notes

- debate.py is ~1485 lines. Read specific sections rather than the whole file.
- The action handlers are NOT separate subcommands — they're dispatched by `if/elif` chains in `main()`.
- `run_critique()` at line 1156 is the heart of the debate loop. Everything else is setup or utility.
- No signal handlers for SIGTERM/SIGINT — relies on subprocess handling.
- `LITELLM_LOG` is force-set to ERROR at line 65.


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: .architecture/structured/components/gauntlet.md (95 lines, 4853 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# Component: Gauntlet

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | 7-phase adversarial stress-testing of specs with named attacker personas |
| Entry | `run_gauntlet()` at scripts/gauntlet.py:3290 |
| Key files | gauntlet.py (~4087 lines), adversaries.py |
| Depends on | Models (litellm), Adversaries, Providers |
| Used by | Debate Engine (handle_gauntlet), standalone CLI |

## What This Component Does

The gauntlet subjects a spec to attack from multiple adversary personas, each probing from a different angle (security, operations, distributed systems, UX, business logic). A 7-phase pipeline generates concerns, synthesizes patterns, filters/clusters duplicates, evaluates with multi-model consensus, processes rebuttals for dismissed concerns, adjudicates sustained rebuttals, and optionally runs a Final Boss holistic review. Adversary performance is tracked with a medal system.

## Data Flow

```
IN:  spec text + adversary selection + model config
     └─> run_gauntlet() (gauntlet.py:3290)

PROCESS:
     ├─> Phase 1: Generate concerns (parallel, ThreadPoolExecutor max_workers=5)
     ├─> Phase 2: Big Picture Synthesis (LLM holistic analysis)
     ├─> Phase 3: Filter against resolved concerns
     ├─> Phase 3.5: Cluster near-duplicates via LLM
     ├─> Phase 4: Multi-model evaluation (batched, wave-based concurrency)
     ├─> Phase 5: Rebuttals (dismissed adversaries argue back)
     ├─> Phase 6: Final adjudication (sustained rebuttals reviewed)
     └─> Phase 7: Optional Final Boss UX review (Opus 4.6)

OUT: GauntletResult
     + .adversarial-spec-gauntlet/concerns-{hash}.json
     + .adversarial-spec-gauntlet/raw-responses-{hash}.json
     + .adversarial-spec-gauntlet/evaluations-{hash}.json
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `run_gauntlet()` | Main 7-phase pipeline orchestrator | gauntlet.py:3290 |
| `generate_attacks()` | Phase 1: parallel adversary concern generation | gauntlet.py |
| `generate_big_picture_synthesis()` | Phase 2: holistic cross-concern analysis | gauntlet.py |
| `filter_concerns_with_explanations()` | Phase 3: filter against resolved concerns | gauntlet.py |
| `cluster_concerns_with_provenance()` | Phase 3.5: semantic deduplication | gauntlet.py |
| `evaluate_concerns_multi_model()` | Phase 4: batched multi-model verdict generation | gauntlet.py:2172 |
| `format_gauntlet_report()` | Human-readable report formatting | gauntlet.py:3710 |
| `get_adversary_leaderboard()` | Running stats across gauntlet runs | gauntlet.py |
| `get_medal_leaderboard()` | Medal rankings across runs | gauntlet.py |

## Common Patterns

### Phase Checkpoint Persistence

Each phase writes intermediate results to `.adversarial-spec-gauntlet/` JSON files immediately after completion. This enables crash recovery — if a later phase fails, earlier results survive.

### Wave-Based Concurrency (Phase 4)

Multi-model evaluation uses batched processing (15 concerns per batch) with per-provider rate limit awareness. Multiple waves are dispatched if needed.

### Verdict Normalization

`normalize_verdict()` at gauntlet.py:148 maps various model response formats to canonical verdicts: accepted, dismissed, acknowledged, deferred.

### Medal System

Medals (gold/silver/bronze) awarded based on: uniqueness of catches (concerns no other adversary found), severity of catches, and signal-to-noise ratio. Stats persist in `~/.adversarial-spec/adversary_stats.json`.

## Error Handling

- **Per-adversary failures**: Each adversary call is independent. If one fails, others continue.
- **Evaluation failures**: If eval model can't evaluate a concern, it's marked as deferred.
- **Phase errors**: try/except at phase level — logs warning, continues with partial results.

## Integration Points

**Calls out to:**
- `litellm.completion()` — LLM calls for all phases
- `ADVERSARIES` dict (adversaries.py) — persona definitions
- `cost_tracker` (models.py) — cost accumulation
- File system — JSON persistence for crash recovery

**Called by:**
- `debate.py:handle_gauntlet()` — via debate CLI
- `gauntlet.py:main()` — standalone CLI at line 3836

## LLM Notes

- gauntlet.py is ~4087 lines — the largest file. The core `run_gauntlet()` starts at line 3290.
- Adversary personas are defined in adversaries.py, not gauntlet.py. Each has name, prefix, persona fields.
- The Final Boss (FINAL_BOSS in adversaries.py) issues PASS/REFINE/RECONSIDER verdicts and is run after all other phases.
- Phase 2 (Big Picture Synthesis) was added after original design — it identifies hidden connections and meta-concerns that individual adversaries miss.
- Data classes: Concern (line 121), Evaluation (line 153), Rebuttal (line 165), BigPictureSynthesis (line 175), GauntletResult (line 192).


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: .architecture/structured/components/models.md (112 lines, 5375 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# Component: Models

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | LLM call abstraction across providers (API + 3 CLI tools) |
| Entry | `call_models_parallel()` at scripts/models.py:894 |
| Key files | models.py (937 lines), providers.py (683 lines) |
| Depends on | litellm, subprocess (Codex/Gemini/Claude CLI), Prompts, Providers |
| Used by | Debate Engine, Gauntlet |

## What This Component Does

Models provides a unified interface for calling multiple LLM providers. It handles four calling strategies: LiteLLM for standard API models (OpenAI, Anthropic, Google, Groq, Mistral, xAI, Bedrock), and subprocess for Codex CLI, Gemini CLI, and Claude CLI. It manages parallel execution via ThreadPoolExecutor, retries with exponential backoff, response parsing (agreement markers, spec extraction), and cost tracking via a global singleton.

## Data Flow

```
IN:  model list + system prompt + user message
     └─> call_models_parallel() (models.py:894)

PROCESS:
     ├─> ThreadPoolExecutor spawns one call_single_model() per model
     ├─> Each routes by prefix: codex/ | gemini-cli/ | claude-cli/ | litellm
     ├─> Parse response: extract text, [AGREE] marker, [SPEC]...[/SPEC] tags
     ├─> cost_tracker.add() per successful call
     └─> Collect results as list[ModelResponse]

OUT: list[ModelResponse]
     └─> returned to caller (debate loop or gauntlet)
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `call_models_parallel()` | ThreadPoolExecutor orchestration | models.py:894 |
| `call_single_model()` | Router: litellm vs codex vs gemini vs claude | models.py:619 |
| `call_codex_model()` | Subprocess call to `codex exec --json --full-auto` | models.py:351 |
| `call_gemini_cli_model()` | Subprocess call to `gemini -m <model> -y` | models.py:451 |
| `call_claude_cli_model()` | Subprocess call to `claude -p --json-out` | models.py:536 |
| `CostTracker.add()` | Token cost accumulation | models.py:163 |
| `CostTracker.summary()` | Human-readable cost report | models.py:186 |
| `detect_agreement()` | Check for [AGREE] marker | models.py:226 |
| `extract_spec()` | Extract [SPEC]...[/SPEC] content | models.py:231 |
| `extract_tasks()` | Parse [TASK]...[/TASK] structured task data | models.py:240 |
| `generate_diff()` | Diff between original and revised spec | models.py:340 |
| `load_context_files()` | Load --context files as markdown sections | models.py:207 |

## Common Patterns

### Model Routing by Prefix

`call_single_model()` checks model prefix to route:
- `codex/` prefix → subprocess to Codex CLI with JSON event stream parsing
- `gemini-cli/` prefix → subprocess to Gemini CLI with noise filtering
- `claude-cli/` prefix → subprocess to Claude CLI with JSON output parsing
- Everything else → `litellm.completion()`

### Retry with Exponential Backoff

Failed calls retry up to MAX_RETRIES=3 with backoff: RETRY_BASE_DELAY=1.0 * 2^attempt → 1s, 2s, 4s. On final failure, ModelResponse.error is populated.

### CLI File Safety Preamble

CLI tools get `CLI_FILE_SAFETY_PREAMBLE` (models.py:112-120) prepended to prevent them from modifying files.

## Error Handling

- **API timeouts**: Caught and retried with backoff
- **Subprocess failures**: TimeoutExpired and CalledProcessError caught, converted to error responses
- **Missing CLI tools**: `shutil.which()` check at import time (CODEX_AVAILABLE, GEMINI_CLI_AVAILABLE, CLAUDE_CLI_AVAILABLE)
- **JSON parse errors**: Malformed CLI responses logged but don't crash (graceful degradation)
- **Rate limits**: Handled by litellm's built-in retry logic

## Concurrency Concerns

| Resource | Callers | Synchronization | Risk |
|----------|---------|-----------------|------|
| `cost_tracker` (global singleton) | Multiple threads via `call_single_model()`, gauntlet phases | None (relies on GIL) | Dict updates to `by_model` not atomic — if two threads update same model key, one update may be lost. Cost is informational only. |

## Configuration

| Config | Source | Default |
|--------|--------|---------|
| MODEL_COSTS | providers.py dict | Per-model input/output rates |
| MAX_RETRIES | models.py constant | 3 |
| RETRY_BASE_DELAY | models.py constant | 1.0 seconds |
| Codex reasoning | `--codex-reasoning` CLI | DEFAULT_CODEX_REASONING from providers |

## Integration Points

**Calls out to:**
- `litellm.completion()` — standard API calls
- `subprocess.run("codex exec --json")` — Codex CLI
- `subprocess.run("gemini -m")` — Gemini CLI
- `subprocess.run("claude -p --json-out")` — Claude CLI
- `providers.MODEL_COSTS` — cost lookup

**Called by:**
- `debate.py:run_critique()` — debate rounds
- `gauntlet.py` — adversary calls (some phases use litellm directly)

## LLM Notes

- CLI tool models (codex/, gemini-cli/, claude-cli/) have $0 cost (subscription-based) but tokens are still tracked.
- Token estimation for Gemini CLI: `len(text) // 4` (rough approximation).
- `is_o_series_model()` detects O-series models that need special handling (no custom temperature).
- `cost_tracker` is a module-level singleton (models.py:204). All calls in a process share it.
- When adding new models, update `MODEL_COSTS` in providers.py.
- ModelResponse dataclass at models.py:141 — fields: model, response, agreed, spec, input_tokens, output_tokens, cost, error.


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: .architecture/structured/components/providers.md (86 lines, 3952 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# Component: Providers

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Model configuration, credentials, cost rates, Bedrock support |
| Entry | `validate_model_credentials()` at scripts/providers.py:436 |
| Key files | providers.py (683 lines) |
| Depends on | Prompts (FOCUS_AREAS, PERSONAS), standard library |
| Used by | Models, Debate Engine, Gauntlet |

## What This Component Does

Providers is the configuration hub for model management. It defines MODEL_COSTS (per-token rates for all supported models), handles credential validation against environment variables, manages saved profiles (model + focus + persona combos), implements Bedrock support (enable/disable, model resolution, region config), and exposes listing functions for providers, focus areas, and personas.

## Data Flow

```
IN:  model names, profile names, bedrock settings
     └─> validate_model_credentials(), load_profile(), etc.

PROCESS:
     ├─> Check env vars for API keys per provider
     ├─> Check shutil.which() for CLI tool availability
     ├─> Load/save profiles from ~/.config/adversarial-spec/profiles/
     ├─> Load/save global config from ~/.claude/adversarial-spec/config.json
     └─> Resolve Bedrock model IDs from friendly names

OUT: Validation results, profile data, config data
     └─> consumed by debate.py and models.py
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `validate_model_credentials()` | Check API keys/CLI tools for model list | providers.py:436 |
| `load_profile()` | Load saved profile | providers.py |
| `save_profile()` | Save profile to disk | providers.py |
| `list_providers()` | List available providers | providers.py |
| `list_focus_areas()` | List available focus areas (from prompts) | providers.py |
| `list_personas()` | List available personas (from prompts) | providers.py |
| `load_global_config()` | Read global JSON config | providers.py:95 |
| `save_global_config()` | Write global JSON config | providers.py:106 |
| `is_bedrock_enabled()` | Check Bedrock toggle | providers.py:112 |
| `resolve_bedrock_model()` | Map friendly name to Bedrock ID | providers.py:124 |
| `handle_bedrock_command()` | CLI bedrock subcommand handler | providers.py |

## Key Data

| Constant | Purpose |
|----------|---------|
| `MODEL_COSTS` | Dict mapping model names to {input, output} per-million-token rates | providers.py:18-47 |
| `PROFILES_DIR` | `~/.config/adversarial-spec/profiles/` |
| `GLOBAL_CONFIG_PATH` | `~/.claude/adversarial-spec/config.json` |
| `DEFAULT_CODEX_REASONING` | Default reasoning level for Codex CLI |
| `CODEX_AVAILABLE` | Boolean: is `codex` binary on PATH |
| `GEMINI_CLI_AVAILABLE` | Boolean: is `gemini` binary on PATH |
| `CLAUDE_CLI_AVAILABLE` | Boolean: is `claude` binary on PATH |

## Error Handling

- **Missing config file**: `load_global_config()` returns empty dict if file doesn't exist or JSON is invalid
- **Missing profiles dir**: Created on first save
- **Invalid Bedrock model**: Returns None from resolve, caller handles

## Integration Points

**Calls out to:**
- `prompts.FOCUS_AREAS` — for listing focus areas
- `prompts.PERSONAS` — for listing personas
- File system — config and profile JSON files
- Environment variables — API keys

**Called by:**
- `debate.py` — credential validation, profile loading, bedrock setup
- `models.py` — MODEL_COSTS for cost calculation
- `gauntlet.py` — credential checks, model selection

## LLM Notes

- When adding a new model, add its cost entry to `MODEL_COSTS` dict. CLI models (codex/, gemini-cli/, claude-cli/) use {input: 0, output: 0}.
- Provider detection is prefix-based: gpt- → OpenAI, claude- → Anthropic, gemini/ → Google, etc.
- CLI tool availability is checked once at import time via `shutil.which()`, not per-call.
- Bedrock support remaps model names with "bedrock/" prefix and sets AWS_REGION env var.


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: .architecture/structured/components/prompts.md (67 lines, 2775 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# Component: Prompts

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Centralized prompt templates, focus areas, and personas |
| Entry | `get_system_prompt()` at scripts/prompts.py:125 |
| Key files | prompts.py (505 lines) |
| Depends on | Standard library only |
| Used by | Models, Providers, Debate Engine, Gauntlet |

## What This Component Does

Prompts is a pure data/function module that provides all prompt templates used across the system. It defines system prompts by doc type and depth, review/press prompt templates, focus areas (specialized critique angles), personas (reviewer personalities), and utility prompts for task extraction and diff generation. It's the most-imported module in the codebase.

## Data Flow

```
IN:  doc_type, depth, persona, focus parameters
     └─> get_system_prompt() (prompts.py:125)

PROCESS:
     ├─> Select system prompt by doc_type (spec, debug, etc.)
     ├─> Apply depth modifier (product, technical, full)
     └─> Combine with focus area and persona if specified

OUT: Formatted prompt strings
     └─> consumed by models.py for LLM calls
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `get_system_prompt()` | Select and format system prompt by doc_type/depth | prompts.py:125 |
| `get_doc_type_name()` | Human-readable doc type name | prompts.py |

## Key Data

| Constant | Purpose |
|----------|---------|
| `FOCUS_AREAS` | Dict of specialized critique angles (security, performance, etc.) | prompts.py:31-110 |
| `PERSONAS` | Dict of reviewer personalities | prompts.py:112-123 |
| `REVIEW_PROMPT_TEMPLATE` | Standard review round template |
| `PRESS_PROMPT_TEMPLATE` | Press (adversarial pressure) template |
| `PRESERVE_INTENT_PROMPT` | Instruction to preserve original intent |
| `EXPORT_TASKS_PROMPT` | Task extraction template |
| `SYSTEM_PROMPT_*` | System prompts by doc type |

## Integration Points

**Calls out to:**
- Nothing (leaf module, no internal imports)

**Called by:**
- `models.py` — prompt construction for LLM calls
- `providers.py` — FOCUS_AREAS and PERSONAS for listing
- `debate.py` — doc type names and prompt formatting
- `gauntlet.py` — system prompt selection

## LLM Notes

- This is a leaf module with no internal dependencies — highest import count in the codebase (5+).
- Focus areas are specialized critique angles like "security", "performance", "api-design" — they modify the system prompt to bias the reviewer.
- Personas are reviewer personalities like "senior-engineer", "product-manager" — they change the tone and perspective.
- Template substitution uses Python `.format()` with named placeholders: {round}, {doc_type_name}, {spec}, {focus_section}, {context_section}.


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: .architecture/structured/components/adversaries.md (64 lines, 2728 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# Component: Adversaries

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Named attacker persona definitions for gauntlet stress-testing |
| Entry | `ADVERSARIES` dict at scripts/adversaries.py |
| Key files | adversaries.py (914 lines) |
| Depends on | Standard library only (hashlib, dataclasses, datetime) |
| Used by | Gauntlet, Debate Engine, Execution Planner (gauntlet_concerns) |

## What This Component Does

Adversaries is a pure data module that defines named attacker personas used in the gauntlet pipeline. Each adversary has a name, attack focus area, prompt prefix, and detailed persona description. The module also provides the concern ID generation function and adversary prefix mappings used by the gauntlet concern parser. Key personas include PARANOID_SECURITY, BURNED_ONCALL, FINAL_BOSS, and PRE_GAUNTLET.

## Data Flow

```
IN:  none (pure data module)

PROCESS:
     ├─> Define Adversary dataclass with name, prefix, persona
     ├─> Build ADVERSARIES dict mapping names to Adversary instances
     └─> Provide generate_concern_id() for unique concern identification

OUT: Adversary definitions + utility functions
     └─> imported by gauntlet.py, debate.py, execution_planner/
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `generate_concern_id()` | Generate unique concern ID from adversary + text hash | adversaries.py |
| `Adversary` dataclass | Data structure: name, prefix, persona fields | adversaries.py |

## Key Data

| Constant | Purpose |
|----------|---------|
| `ADVERSARIES` | Dict mapping adversary names to Adversary instances |
| `PARANOID_SECURITY` | Security-focused adversary |
| `BURNED_ONCALL` | Operations/reliability adversary |
| `FINAL_BOSS` | Holistic UX reviewer (issues PASS/REFINE/RECONSIDER) |
| `PRE_GAUNTLET` | Pre-debate context-focused adversary |
| `ADVERSARY_PREFIXES` | Maps concern ID prefixes to adversary names |

## Integration Points

**Calls out to:**
- Nothing (leaf module, no internal imports)

**Called by:**
- `gauntlet.py` — persona definitions for attack generation
- `debate.py` — adversary listing and stats
- `execution_planner/gauntlet_concerns.py` — ADVERSARY_PREFIXES for concern linking

## LLM Notes

- This is a leaf module with no internal dependencies — safe to modify without cascading effects.
- Adding a new adversary: create an Adversary instance, add to ADVERSARIES dict, optionally add prefix to ADVERSARY_PREFIXES.
- The FINAL_BOSS adversary is special — it runs after all other phases and issues system-level verdicts (PASS/REFINE/RECONSIDER).
- Concern IDs use a hash of adversary prefix + concern text for deduplication across runs.


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: .architecture/structured/components/pre-gauntlet.md (96 lines, 4477 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# Component: Pre-Gauntlet

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Collect git state, system health, and build context before gauntlet |
| Entry | `PreGauntletOrchestrator.run()` at scripts/pre_gauntlet/orchestrator.py:51 |
| Key files | pre_gauntlet/orchestrator.py, collectors/, extractors/, integrations/ |
| Depends on | Git CLI, Process Runner, Pydantic |
| Used by | Debate Engine, Gauntlet |

## What This Component Does

The pre-gauntlet pipeline collects environmental context before running the adversarial gauntlet. It gathers git position (branch, commits, diff stats), system state (build status, schema files, directory trees), extracts which files are affected by the spec, and builds a markdown context document. An optional alignment mode uses an LLM to confirm the context matches the spec's intent.

## Data Flow

```
IN:  spec text + repo root + config
     └─> PreGauntletOrchestrator.run() (orchestrator.py:51)

PROCESS:
     ├─> extract_spec_affected_files() → list of relevant files
     ├─> GitPositionCollector.collect() → git branch, diff stats, concerns
     ├─> SystemStateCollector.collect() → build status, schemas, trees
     ├─> build_context() → markdown document combining all data
     └─> [alignment_mode] run_alignment_mode() → LLM confirmation

OUT: PreGauntletResult
     ├── status: COMPLETE | INFRA_ERROR
     ├── context_markdown: str (enriched context for gauntlet)
     ├── concerns: list (infrastructure-level concerns)
     └── timings: dict (performance data)
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `PreGauntletOrchestrator.run()` | Main orchestrator | orchestrator.py:51 |
| `run_pre_gauntlet()` | Public API wrapper | orchestrator.py:207 |
| `GitPositionCollector.collect()` | Git state collection | collectors/git_position.py |
| `SystemStateCollector.collect()` | System state collection | collectors/system_state.py |
| `extract_spec_affected_files()` | File relevance analysis | extractors/spec_affected_files.py |
| `build_context()` | Markdown context assembly | pre_gauntlet/context_builder.py |
| `run_alignment_mode()` | Interactive alignment check | pre_gauntlet/alignment_mode.py |

## Common Patterns

### Config-Driven Collection

Each collection step is gated by `CompatibilityConfig` settings. Doc type rules control which collectors run (e.g., `require_git`, `require_build`, `require_schema`).

### Pydantic Models

Unlike the rest of the codebase (which uses dataclasses), pre-gauntlet uses Pydantic `BaseModel` for input validation. This is intentional — pre-gauntlet validates external data (git output, build results) where schema enforcement matters.

### Complete Isolation

The pre-gauntlet subsystem has zero imports from the main debate/gauntlet modules. It only uses its own subpackages (collectors, extractors, integrations) and standard library.

## Error Handling

- **Git errors**: `GitCliError` → returns `INFRA_ERROR` status (non-fatal to caller)
- **System state errors**: Caught broadly → returns `INFRA_ERROR`
- **File extraction errors**: Warning to stderr, continues with empty list
- **All errors are non-fatal**: Callers can proceed without pre-gauntlet context

## Configuration

| Config | Source | Default |
|--------|--------|---------|
| `config.enabled` | CompatibilityConfig | True |
| `require_git` | Per doc_type rule | True |
| `require_build` | Per doc_type rule | False |
| `require_schema` | Per doc_type rule | False |

## Integration Points

**Calls out to:**
- `GitCli` (integrations/git_cli.py) — read-only git commands via subprocess
- `ProcessRunner` (integrations/process_runner.py) — build command execution
- `KnowledgeService` (integrations/knowledge_service.py) — caching utility (exists but not wired into main flow)
- File system reads for schemas and directory trees

**Called by:**
- `debate.py` — before gauntlet runs
- `gauntlet.py` — standalone gauntlet mode

## LLM Notes

- The pre-gauntlet pipeline is completely optional. The debate engine works without it.
- `CompatibilityConfig` is the control surface — modify it to change what gets collected.
- `integrations/knowledge_service.py` exists with caching at `~/.cache/adversarial-spec/knowledge/` but is not wired into the main flow yet.
- All collectors run independently (no interdependencies between git and system state collection).


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: .architecture/structured/components/mcp-tasks.md (79 lines, 3392 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# Component: MCP Tasks

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Cross-agent task coordination via MCP protocol |
| Entry | `mcp.run()` at mcp_tasks/server.py:365 |
| Key files | mcp_tasks/server.py, scripts/task_manager.py |
| Depends on | mcp (FastMCP), shared .claude/tasks.json storage |
| Used by | Claude Code agents, debate.py (optional task tracking) |

## What This Component Does

The MCP Tasks server provides a task management API accessible to Claude Code agents via the MCP protocol. It exposes four tools (TaskCreate, TaskGet, TaskList, TaskUpdate) that operate on a shared `.claude/tasks.json` file. The companion `task_manager.py` provides a Python API to the same storage, enabling debate.py to track round progress alongside MCP-based task management.

## Data Flow

```
IN:  MCP protocol messages (tool calls from Claude Code)
     └─> FastMCP server (server.py:365)

PROCESS:
     ├─> TaskCreate: generate ID, write to tasks.json
     ├─> TaskGet: read by ID from tasks.json
     ├─> TaskList: filter by session_id, context_name, status; or list_contexts mode
     └─> TaskUpdate: modify status, metadata, blockedBy, addBlocks

OUT: MCP protocol responses (JSON)
     + .claude/tasks.json (shared file)
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `TaskCreate` (decorator) | Create new task | server.py:98 |
| `TaskGet` (decorator) | Get task by ID | server.py:140 |
| `TaskList` (decorator) | List tasks with filters or list contexts | server.py:160 |
| `TaskUpdate` (decorator) | Update task status/metadata/dependencies | server.py:261 |
| `TaskManager.__init__()` | Python API initialization | task_manager.py:114 |
| `TaskManager.create_task()` | Python task creation | task_manager.py |
| `create_adversarial_spec_session()` | Creates full phase-based task set | task_manager.py:301 |

## Common Patterns

### Shared Storage

Both the MCP server and Python TaskManager read/write the same `.claude/tasks.json`. This enables Claude Code's MCP tools and Python scripts to see each other's tasks without a separate coordination layer.

### Working Directory Detection

`get_working_dir()` checks `MCP_WORKING_DIR` → `PWD` → `os.getcwd()` to find the project root. This ensures tasks are stored per-project.

### Context-Based Filtering

TaskList supports `context_name` filtering and a `list_contexts` mode that returns a summary of all contexts with task counts and last activity, enabling work stream management.

## Error Handling

- **File locking**: No explicit locking — assumes single writer at a time
- **Missing file**: Created on first write with `{tasks: [], next_id: 1}` structure
- **Invalid JSON**: Caught and returns empty task list

## Integration Points

**Calls out to:**
- File system (`.claude/tasks.json`) — read/write

**Called by:**
- Claude Code agents via MCP protocol
- `debate.py:get_task_manager()` — lazy-loaded Python API
- `task_manager.py:create_adversarial_spec_session()` — batch task creation

## LLM Notes

- The MCP server uses FastMCP decorators, not explicit tool registration. Tools are defined as decorated functions.
- `task_manager.py` is the Python equivalent of the MCP server — same storage, different interface.
- Session-based filtering uses `metadata.session_id` field, not a top-level session property.


<!-- ══════════════════════════════════════════════════════════════ -->
<!-- FILE: .architecture/structured/components/execution-planner.md (43 lines, 1911 bytes) -->
<!-- ══════════════════════════════════════════════════════════════ -->
# Component: Execution Planner

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Gauntlet concern parsing (mostly deprecated) |
| Entry | `GauntletConcernParser` at execution_planner/gauntlet_concerns.py |
| Key files | execution_planner/__init__.py, gauntlet_concerns.py |
| Depends on | Adversaries (for ADVERSARY_PREFIXES, generate_concern_id) |
| Used by | Debate Engine (optional, lazy-loaded) |

## What This Component Does

The execution planner was originally a full spec-to-task decomposition pipeline. **It is mostly deprecated** (Option B+ decision, Feb 2026). The pipeline approach was replaced by Claude creating plans directly using embedded guidelines in `phases/06-execution.md`. Dead modules have been deleted. Only `gauntlet_concerns.py` survives long-term — it parses structured gauntlet JSON to link concerns to spec sections.

## Data Flow

```
IN:  gauntlet concern JSON files
     └─> GauntletConcernParser.parse_file()

PROCESS:
     ├─> Parse concern JSON structure
     ├─> Match concern IDs to adversary prefixes
     └─> Link concerns to spec sections

OUT: list[GauntletConcern] with linked spec references
     └─> returned to caller
```

## Key Functions

| Function | Purpose | Location | Status |
|----------|---------|----------|--------|
| `GauntletConcernParser.parse_file()` | Parse gauntlet JSON | gauntlet_concerns.py | **KEEP** |
| `load_concerns_for_spec()` | Load all concerns for a spec hash | gauntlet_concerns.py | **KEEP** |

## LLM Notes

- Only `gauntlet_concerns.py` and `__init__.py` exist in this directory now. Dead modules were deleted in the execution planner deprecation (Feb 2026).
- `from execution_planner import ...` in debate.py is wrapped in try/except for graceful degradation.
- The `__init__.py` exports: GauntletConcern, GauntletConcernParser, GauntletReport, LinkedConcern, load_concerns_for_spec.


