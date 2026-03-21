# System Overview: adversarial-spec

> Generated: 2026-03-21 | Git: 12c5d3f | Target: /home/jason/PycharmProjects/adversarial-spec
> Skill version: 2.6 | Model: claude-opus-4-6

## What This System Does

adversarial-spec is a Claude Code skill that refines software specifications through multi-model debate and adversarial stress-testing. It sends specs to multiple LLMs (OpenAI, Anthropic, Google, xAI, Mistral, Groq, and CLI tools like Codex, Gemini CLI, Claude CLI) simultaneously for iterative critique until all models agree, then runs a gauntlet of 9 named adversary personas that attack the spec from different angles (security, scalability, UX, etc.). The result is a battle-tested specification with surviving concerns prioritized by severity.

## Architecture at a Glance

The system is built around two complementary flows sharing a common model abstraction layer. The **debate engine** (`debate.py`) orchestrates multi-round critiques where each round sends the current spec to selected models in parallel, collects their responses, checks for agreement, and saves checkpoints. The **gauntlet pipeline** (`gauntlet/` package, 16 modules) is a 7-phase pipeline that generates adversarial attacks, synthesizes a big-picture view, clusters and deduplicates concerns, evaluates them with frontier models, runs rebuttals for dismissed concerns, performs final adjudication, and optionally runs a "Final Boss" UX review.

Both flows rely on a unified model layer (`models.py`) that dispatches calls through LiteLLM for API providers or via subprocess for CLI tools (Codex, Gemini CLI, Claude CLI). A thread-safe `CostTracker` singleton accumulates token usage and cost across all calls. Provider configuration, API key validation, Bedrock support, and cost tables live in `providers.py`.

Adversary personas are defined as frozen dataclasses in `adversaries.py`, each with a name, prefix (for concern IDs), persona prompt, and explicit dismissal/acceptance rules. The gauntlet package was extracted from a 4,087-line monolith into 16 focused modules, with a shim `__init__.py` re-exporting 5 public symbols for backwards compatibility.

## Primary Data Flows

### Spec Critique Loop

A spec arrives via stdin or session resume. `debate.py` formats it with system prompts (selected by doc type and depth), optional focus areas, and context files. `call_models_parallel()` at models.py:901 dispatches to N models simultaneously via `ThreadPoolExecutor`. Each model's response is parsed for `[AGREE]`/`[SPEC]` markers. Results are saved as round checkpoints and optionally sent via Telegram. The user iterates manually — each invocation is one round.

### Gauntlet Pipeline

A spec enters `run_gauntlet()` at `gauntlet/orchestrator.py:116` and flows through 7 phases: (1) adversary personas generate concerns in parallel (`phase_1_attacks.py`), (2) an LLM synthesizes patterns across all concerns (`phase_2_synthesis.py`), (3) historical filtering removes resolved issues and semantic clustering deduplicates (`phase_3_filtering.py`), (3.5) checkpoint after clustering, (4) multiple evaluation models produce accept/dismiss/acknowledge/defer verdicts (`phase_4_evaluation.py`), (5) dismissed concerns get adversary rebuttals (`phase_5_rebuttals.py`), (6) sustained rebuttals get final adjudication (`phase_6_adjudication.py`), (7) optional Final Boss UX review (`phase_7_final_boss.py`). Results persist to `~/.adversarial-spec/runs/` via `persistence.py`. A `GauntletConfig` dataclass centralizes all timeout/reasoning/mode settings, and `PhaseMetrics` captures per-phase telemetry for the run manifest.

### Cost Tracking

Every model call reports token counts (from API responses, CLI JSON output, or character-based estimation). A global `CostTracker` singleton at models.py:204 accumulates per-model and total costs using rates from `MODEL_COSTS` in `providers.py`. The tracker uses a `threading.Lock` for thread-safe accumulation across parallel calls.

### Pre-Gauntlet Context Collection

An optional pre-gauntlet phase (`pre_gauntlet/` package) runs before the gauntlet to collect codebase context — git position, build status, discovered services, and alignment checks. It enriches the spec with `context_markdown` before adversarial testing begins.

## Key Architectural Decisions

- **Single-invocation model**: No daemon. Each CLI invocation is one debate round or one gauntlet run. Session persistence enables manual multi-round iteration.
- **Thread-per-model parallelism**: `ThreadPoolExecutor` dispatches to all models simultaneously. Cost tracking is lock-guarded.
- **CLI subprocess routing**: Codex, Gemini, and Claude CLI called via subprocess for file access capability at zero token cost.
- **LiteLLM abstraction**: 7+ API providers unified behind `litellm.completion()`.
- **Checkpoint persistence with FileLock**: JSON files after each gauntlet phase; `filelock` ensures atomic writes for multi-process safety.
- **Layered dependencies**: CLI → Orchestration → LLM → Config. No circular imports.
- **Monolith extraction with shim**: `gauntlet/__init__.py` re-exports 5 public symbols for backwards compatibility.
- **GauntletConfig centralization**: All timeout/reasoning/mode parameters flow through a single config dataclass, eliminating the scattered hardcoded defaults that caused a quota-burn bug.

## Non-Obvious Things

- **`debate.py` is both CLI and library**: It's the primary entry point for both debate and gauntlet subcommands, not just debates. The gauntlet has its own standalone CLI (`python -m gauntlet`) but debate.py adds `--show-manifest`, `--gauntlet-resume`, and `--codex-reasoning` flags.
- **`--codex-reasoning` controls attack reasoning**: In debate.py, `--codex-reasoning` maps to `attack_codex_reasoning` in `run_gauntlet()`. There is no `--attack-codex-reasoning` in debate.py — that flag only exists in the standalone `gauntlet/cli.py`.
- **`gauntlet_monolith.py` is a shim**: The original monolith was replaced by a 12-line file that raises `ImportError` directing callers to the package.
- **`execution_planner/` is mostly deprecated**: Only `gauntlet_concerns.py` survives long-term. Generation logic moved to LLM guidelines in `phases/06-execution.md`.
- **Skills are symlinked**: `~/.claude/skills/adversarial-spec/` is symlinked to `skills/adversarial-spec/` in the repo, so changes are deployed instantly.
- **Adversary stats are cumulative**: `~/.adversarial-spec/adversary_stats.json` accumulates across all gauntlet runs, building a leaderboard over time.
- **`scope.py` is unused**: Exists in scripts but not imported by any active module.
- **Model name validation**: `gauntlet/model_dispatch.py` validates model names against a blocklist regex to prevent injection via `--models` flag.

## Component Map

| Component | Purpose | Key Entry |
|-----------|---------|-----------|
| Debate Engine | Multi-model spec critique loop with CLI orchestration | `main()` at debate.py:1493 |
| Gauntlet Pipeline | 7-phase adversarial stress-testing (16-module package) | `run_gauntlet()` at gauntlet/orchestrator.py:116 |
| Model Layer | LLM call abstraction (LiteLLM + 3 CLI tools) | `call_models_parallel()` at models.py:901 |
| Adversaries | 9 named adversary personas with dismissal rules | `ADVERSARIES` dict at adversaries.py |
| Providers | API key validation, costs, profiles, Bedrock support | `validate_model_credentials()` at providers.py |
| Prompts | System prompts, focus areas, doc-type templates | `get_system_prompt()` at prompts.py |
| Pre-Gauntlet | Codebase context collection before gauntlet | `run_pre_gauntlet()` at pre_gauntlet/orchestrator.py |
| MCP Tasks | Cross-agent task coordination server | `mcp` at mcp_tasks/server.py |
| Execution Planner | Gauntlet concern parsing (deprecated) | `load_concerns_for_spec()` at execution_planner/ |
| Session | Debate session state and checkpointing | `SessionState` at session.py:17 |

For detailed component docs, see `structured/components/`.
