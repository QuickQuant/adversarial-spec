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
