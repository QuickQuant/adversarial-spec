# System Overview: adversarial-spec

> Generated: 2026-04-16 | Git: 9ca3ccd | Target: /home/jason/PycharmProjects/adversarial-spec
> Skill version: 3.6 | Model: claude-opus-4-6
> Freshness: fresh | Trust: Current HEAD with no relevant drift

## What This System Does

adversarial-spec is a Claude Code skill that refines product specifications through multi-model adversarial debate. Users pipe a spec into the CLI, which dispatches it to multiple LLMs for critique, collects responses, and drives iterative refinement until models reach consensus. For thorough stress-testing, a 7-phase gauntlet pipeline runs the spec through named adversary personas (security paranoid, scalability hawk, UX advocate, etc.), evaluates their concerns with frontier models, and produces a final pass/refine/reconsider verdict.

## Architecture at a Glance

The system is built around two primary workflows sharing a common model-calling layer. The **debate engine** (`debate.py`) is the master CLI, routing 18 different actions through argparse dispatch. For standard critique rounds, it loads a spec (from stdin or a resumed session), calls `call_models_parallel()` to dispatch to all configured LLMs simultaneously via ThreadPoolExecutor, collects `ModelResponse` objects, checks for consensus, and prompts the user to continue or stop.

The **gauntlet pipeline** (`gauntlet/orchestrator.py` + 18 submodules) is the heavy-duty path. It runs 7 sequential phases: attack generation (Phase 1, parallel across adversaries and models), big-picture synthesis (Phase 2), concern filtering (Phase 3 — note: Phase 3.5 clustering was removed after finding it lost 48% of concerns), frontier-model evaluation (Phase 4), adversary rebuttals (Phase 5), adjudication with medals (Phase 6), and final boss review (Phase 7). Each phase checkpoints its output to `.adversarial-spec-gauntlet/` using FileLock-guarded atomic writes, enabling resume after crashes or quota exhaustion. Phase prompts are centralized in `gauntlet/prompts.py`.

Both workflows share the **models layer** (`models.py`), which abstracts 7+ LLM providers through LiteLLM for API-based models and subprocess calls for CLI models (Codex, Gemini CLI, Claude CLI). A global thread-safe `CostTracker` accumulates token usage and costs across all parallel calls. The **providers layer** (`providers.py`) manages model configuration, cost rates, Bedrock routing, and CLI availability detection.

The **adversaries module** (`adversaries.py`) defines 9+ named attacker personas as frozen dataclasses with structured evaluation protocols (valid/invalid dismissal rules, scope guidelines). These drive the gauntlet's attack generation and evaluation phases. Adversaries have version tracking via `content_hash()` for detecting persona changes.

Supporting this are a **pre-gauntlet** context collector (git position, system state, spec-affected files), a **session** persistence layer for multi-round debate state, an **MCP task server** (FileLock-guarded) for cross-agent coordination, and an **execution planner** module (mostly deprecated, only gauntlet concern parsing remains). The skill workflow is managed via a **Fizzy pipeline board** with 9 phases (init-and-requirements through verification).

## Primary Data Flows

### Debate Critique Flow

A spec arrives via stdin, gets loaded into a `SessionState`, and is dispatched to N models in parallel via `call_models_parallel()`. Each model receives a system prompt (persona + focus area) and the spec as user message. Responses come back as `ModelResponse` objects with critique text, token counts, and agreement flags. If all models agree, the round ends. Otherwise, the user reviews the critiques and optionally continues to the next round. Session state and checkpoints persist to disk after each round at `debate.py:1206`.

### Gauntlet Stress-Test Flow

The spec enters `run_gauntlet()` at `gauntlet/orchestrator.py:194` with a `GauntletConfig`. Phase 1 dispatches the spec to all adversary-model pairs in parallel via ThreadPoolExecutor (up to 32 workers), collecting raw `Concern` objects with stable hash-based IDs. Phase 2 synthesizes a big-picture view. Phase 3 filters concerns against a resolved-concerns database and deduplicates (clustering was removed after a process failure). Phase 4 sends filtered concerns to a frontier model for verdict assignment (dismiss/accept/acknowledge/defer), with optional multi-model consensus. Phase 5 gives dismissed adversaries a rebuttal chance. Phase 6 aggregates verdicts and awards medals. Phase 7's final boss reviews everything and issues a pass/refine/reconsider verdict. Each phase checkpoints via `persistence.py` with FileLock coordination.

### Cost Tracking Flow

Every model call (API or CLI) reports token usage to the global `cost_tracker` at `models.py:211`. API models look up `MODEL_COSTS` for per-token pricing. CLI models report zero cost (subscription-based). The tracker uses `threading.Lock` for thread-safe accumulation across ThreadPoolExecutor workers. Cost summaries appear in output and are included in run manifests.

## Key Architectural Decisions

- **Single-invocation CLI, no daemon**: Each run is self-contained. Multi-round continuity comes from session files and checkpoints, not a running process.
- **ThreadPoolExecutor for model parallelism**: Simple, effective for I/O-bound LLM calls. Up to 32 workers for gauntlet Phase 1.
- **FileLock-guarded atomic checkpoints**: Prevents corrupted JSON on crash. Temp file + fsync + os.replace ensures durability.
- **Hash-based checkpoint keys**: `spec_hash + config_hash` ensures stale checkpoints are detected and invalidated on resume.
- **LiteLLM as provider abstraction**: Unifies OpenAI, Anthropic, Google, xAI, Mistral, Groq, and more behind a single `completion()` call.
- **CLI subprocess routing for subscription models**: Codex, Gemini CLI, and Claude CLI run as subprocess calls, bypassing LiteLLM entirely.
- **Frozen adversary dataclasses with version tracking**: `content_hash()` enables detecting when personas change, invalidating old evaluation data.

## Non-Obvious Things

- **Two gauntlet CLIs exist**: `debate.py gauntlet` and `gauntlet/cli.py` accept different flag names for the same features. They share `run_gauntlet()` as the backend.
- **gauntlet_monolith.py is a 12-line shim**: Legacy compatibility. Delegates to `gauntlet/cli.py:main()`.
- **scope.py (606 lines) has no importers**: The `scope_guidelines` field on `Adversary` is active and tested, but scope.py itself is not imported by any module. Status unclear.
- **Pydantic is an implicit dependency**: Used in `pre_gauntlet/models.py` but not declared in `pyproject.toml`.
- **No "Spec" dataclass**: Specs flow as plain strings. Identity is tracked via SHA-256 hash, not a structured type.
- **Unattended mode is a builtins.input monkey-patch**: Replaced globally during gauntlet runs, restored in a finally block.
- **PROGRAMMING_BUGS tuple** (`core_types.py`): Excludes TypeError, NameError, AttributeError from broad exception handling — they propagate for visibility.
- **Phase 3.5 clustering was removed**: After analysis showed Haiku subagent lost 48% of concerns. Adversary scope design handles overlap upstream.

## Component Map

| Component | Purpose | Key Entry |
|-----------|---------|-----------|
| Debate Engine | CLI routing + multi-round debate | `main()` at debate.py:1520 |
| Gauntlet Pipeline | 7-phase adversarial stress-test | `run_gauntlet()` at gauntlet/orchestrator.py:194 |
| Models | LLM call abstraction (LiteLLM + CLI) | `call_models_parallel()` at models.py:914 |
| Providers | Model config, costs, Bedrock | `providers.py` |
| Adversaries | Named attacker personas | `adversaries.py` |
| Prompts | Centralized prompt templates | `prompts.py` |
| Pre-Gauntlet | Git/system context collection | `run_pre_gauntlet()` at pre_gauntlet/orchestrator.py:207 |
| Session | Debate state persistence | `SessionState` at session.py:17 |
| MCP Tasks | Cross-agent task coordination | `mcp.run()` at mcp_tasks/server.py:365 |
| Execution Planner | Gauntlet concern parsing (mostly deprecated) | `execution_planner/gauntlet_concerns.py` |

For detailed component docs, see `structured/components/`.
