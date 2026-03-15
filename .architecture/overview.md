# System Overview: adversarial-spec

> Generated: 2026-02-06T20:35:00Z | Git: e94ebfe | Target: /home/jason/PycharmProjects/adversarial-spec
> Skill version: 2.1 | Model: Claude Opus 4.6

## What This System Does

adversarial-spec is a Claude Code skill that generates and refines software specifications through multi-model adversarial debate. It sends a draft spec to multiple LLM providers (OpenAI Codex, Google Gemini, Anthropic Claude, etc.) for critique, iterates until all models agree, then stress-tests the consensus through an adversarial gauntlet with named attacker personas. The final output is a battle-tested specification ready for implementation.

## Architecture at a Glance

The system is built around a CLI-driven debate loop orchestrated by `debate.py`, the main entry point. A user feeds in a draft specification (via stdin or file), and the debate engine sends it to multiple LLM models in parallel using `models.py`, which abstracts over three calling strategies: LiteLLM for standard API models, subprocess for Codex CLI (agentic), and subprocess for Gemini CLI. Each model returns a critique with an agree/disagree signal. If all models agree, the spec has converged; otherwise, the latest revised spec is fed back for another round.

Once the spec reaches consensus, it can optionally enter the adversarial gauntlet (`gauntlet.py`), where five named adversary personas (ParanoidSecurity, BurnedOncall, DistributedSystemsNerd, etc.) attack the spec from different angles. A "Final Boss" reviewer then synthesizes findings and issues a PASS/REFINE/RECONSIDER verdict. Adversary performance is tracked with a medal system (gold/silver/bronze) based on the uniqueness and severity of their catches.

The execution planner (`execution_planner/`) converts finalized specs into implementation task DAGs, though this subsystem is being deprecated in favor of Claude creating plans directly using embedded guidelines (Option B+ decision, Feb 2026). The `gauntlet_concerns.py` module survives deprecation because it parses structured gauntlet JSON to link concerns to tasks.

Supporting infrastructure includes session management for multi-round persistence, Telegram notifications for async feedback, an MCP Tasks server for cross-agent task coordination, and a pre-gauntlet context pipeline that collects git state and system health before running the gauntlet.

## Primary Data Flows

### Spec Critique Loop

A spec enters via stdin or file, gets wrapped in a system prompt (with persona, focus area, and doc type settings from `prompts.py`), and is sent to N models in parallel via `ThreadPoolExecutor`. Each model returns a `ModelResponse` with an agree/disagree flag and optionally a revised spec extracted from `[SPEC]...[/SPEC]` tags. If all models agree, convergence is reached. Otherwise, the latest revised spec becomes input for the next round. Session state persists across rounds via JSON files in `~/.config/adversarial-spec/sessions/`.

### Adversarial Gauntlet

The finalized spec enters a 6-phase pipeline: (1) adversary concern generation in parallel, (2) duplicate filtering, (3) frontier model evaluation with accept/dismiss verdicts, (4) optional rebuttal where dismissed adversaries can argue back, (5) big-picture synthesis identifying hidden connections and gaps, (6) medal awards ranking adversary performance. Output is a structured JSON report stored in `~/.adversarial-spec-gauntlet/`.

### Execution Planning

A spec plus optional gauntlet concerns flow through: spec intake (parsing to structured types), scope assessment, task decomposition, test strategy assignment, over-decomposition guard, and parallelization analysis. This produces a `TaskPlan` DAG. This pipeline is being simplified to guidelines-based LLM generation.

### Cost Tracking

Every model call reports input/output token counts. The `CostTracker` singleton looks up per-token rates from `MODEL_COSTS` in `providers.py` and accumulates totals. Cost summaries appear in CLI output and Telegram notifications.

## Key Architectural Decisions

- **LiteLLM as universal adapter**: Provides a single `completion()` API across OpenAI, Anthropic, Google, Groq, Mistral, xAI, and Bedrock, avoiding provider-specific client code.
- **Subprocess for agentic CLIs**: Codex and Gemini CLI tools are invoked via subprocess rather than API because they run as agentic processes with file access, requiring `--json` output parsing.
- **Lazy optional imports**: `execution_planner`, `telegram_bot`, and `task_manager` are imported only when needed, keeping startup fast and allowing the debate engine to work without them.
- **Hub-and-spoke config**: `prompts.py`, `providers.py`, and `adversaries.py` are pure data/config modules imported by everything else, forming a stable foundation layer.
- **No circular dependencies**: The import graph is strictly acyclic. Leaves (prompts, adversaries) feed hubs (models, providers), which feed entry points (debate, gauntlet).

## Non-Obvious Things

- **Duplicate scripts directory**: `skills/adversarial-spec/scripts/scripts/` is a stale copy from a previous deployment. The canonical source is `skills/adversarial-spec/scripts/`. The source and deployed skill dirs (`~/.claude/skills/adversarial-spec/`) are now symlinked, so manual deployment is no longer needed.
- **execution_planner is mid-deprecation**: The `execution_planner/` package at project root contains modules being phased out. Only `gauntlet_concerns.py` and its data models survive. Dead code includes `spec_intake.py`, `agent_dispatch.py`, `execution_control.py`, `progress.py`, `llm_extractor.py`, and `__main__.py`.
- **Pre-gauntlet uses Pydantic, rest uses dataclasses**: The pre-gauntlet subsystem (`scripts/pre_gauntlet/`) uses Pydantic `BaseModel` for data validation, while the rest of the codebase uses stdlib `dataclasses`. This is intentional — pre-gauntlet validates external inputs (git state, build output) where schema enforcement matters.
- **Codex/Gemini CLI costs are $0**: These tools are subscription-based, so `MODEL_COSTS` entries for them have zero per-token rates. Cost tracking still counts their tokens for budgeting awareness.
- **Hook-based safety**: `.claude/hooks/` contains Python scripts that run as pre/post tool-use hooks enforcing rules like "never use deprecated model names" and "minimum timeouts for Codex reasoning levels".

## Component Map

| Component | Purpose | Key Entry |
|-----------|---------|-----------|
| Debate Engine | Multi-model spec critique loop | `main()` at debate.py:1933 |
| Gauntlet | Adversarial stress-testing with personas | `run_gauntlet()` at gauntlet.py |
| Models | LLM call abstraction (LiteLLM + CLI) | `call_models_parallel()` at models.py |
| Providers | API key management, profiles, costs | `validate_model_credentials()` at providers.py |
| Prompts | Templates, personas, focus areas | `get_system_prompt()` at prompts.py |
| Session | Round persistence, checkpoints | `SessionState` at session.py |
| Execution Planner | Spec-to-task decomposition (deprecating) | `TaskPlanner` at execution_planner/task_planner.py |
| Pre-Gauntlet | Context collection before gauntlet | `PreGauntletOrchestrator.run()` at pre_gauntlet/orchestrator.py |
| MCP Tasks | Cross-agent task coordination server | `mcp.run()` at mcp_tasks/server.py |
| Telegram | Async notification and polling | `main()` at telegram_bot.py |
| Task Manager | Python API for task lifecycle | `TaskManager` at task_manager.py |

For detailed component docs, see `structured/components/`.
