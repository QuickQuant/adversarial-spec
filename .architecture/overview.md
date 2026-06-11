# System Overview: adversarial-spec

> Generated: 2026-06-11 (incremental update from 9ca3ccd) | Git: f198887 | Target: /home/jason/PycharmProjects/adversarial-spec
> Skill version: 3.8 | Model: claude-fable-5
> Freshness: fresh | Trust: verified at f198887 (worktree carried in-flight skill/doc edits at scan time)

## What This System Does

adversarial-spec is a Claude Code skill that refines product specifications through multi-model adversarial debate. Users pipe a spec into the CLI, which dispatches it to multiple LLMs for critique, collects responses, and drives iterative refinement until models reach consensus. For thorough stress-testing, a 7-phase gauntlet pipeline runs the spec through named adversary personas, evaluates their concerns with frontier models, and produces a final pass/refine/reconsider verdict. Since June 2026 the surrounding multi-agent workflow (conductor + workers on a Fizzy pipeline board) is coordinated by a suite of harness hooks rather than the retired MCP Tasks server.

## Architecture at a Glance

The system is built around two primary workflows sharing a common model-calling layer. The **debate engine** (`debate.py`) is the master CLI, routing actions through argparse dispatch. Critique and gauntlet actions pass a **pipeline-card gate** (`--pipeline-card` required when a session has a Fizzy card; `IntentionalOverride` needs a ≥50-char logged reason) and a **tests-pseudo staleness gate** before any dispatch. A **preflight** step (`preflight_models()`, new) pings every configured model in parallel with a trivial prompt, catching bad model names and dead auth in seconds instead of after the longest critique.

The **gauntlet pipeline** (`gauntlet/orchestrator.py` + submodules) runs 7 sequential phases: attack generation (Phase 1, parallel across adversary×model pairs with per-provider rate-limited batching), big-picture synthesis (Phase 2), concern filtering against the resolved-concerns DB (Phase 3), **deterministic Jaccard clustering** (Phase 3.5 — reinstated as pure code after the earlier Haiku-subagent version was removed for losing 48% of concerns; auto-activates at ≥200 concerns), frontier-model evaluation (Phase 4) with **power-law batch tiering** (`batch_tiering.py`: p60/p90 length cuts → batch sizes 75/30/12, flat fallback under 30 concerns), adversary rebuttals (Phase 5), adjudication with medals (Phase 6), and final boss review (Phase 7). Each phase checkpoints to `.adversarial-spec-gauntlet/` in an integrity-hashed envelope (`{_meta, data}` with `data_hash`) using FileLock-guarded atomic writes; resume validates schema, spec hash, config hash, and data hash before reuse. A Phase 1 **quality gate** hard-fails the run if any adversary×model pair returned text but parsed to zero concerns (raw responses are preserved for manual recovery + `--resume`).

Both workflows share the **models layer** (`models.py`) — LiteLLM for API models, subprocess for CLI models (Codex, Gemini CLI, Claude CLI) — and the extracted **token_tracking** module, whose thread-safe global `tracker` singleton accumulates tokens/cost across all parallel calls (CLI models are zero-cost by design). The **providers layer** (`providers.py`) holds model config, `MODEL_COSTS`, Bedrock routing, and CLI availability flags. The **adversaries module** defines personas as frozen dataclasses plus v2.0 `AdversaryTemplate`s with scope-keyed guideline maps.

**Mini-spec emission** (`mini_spec_emission.py`, new) is the doc-driven/code-checked emission pattern: it shapes Phase-7 execution plans into the fizzy v3 plan contract (`PLAN_SCHEMA_VERSION=3`, `ALTITUDE_OBLIGATIONS` per component/subsystem/system) and offline-mirrors the live `pipeline_validate_plan` altitude checks via `self_check_plan()`. It is the stated pattern for the upcoming `validation_emission.py` (validation-leg spec, card 5604). The **harness hooks** (`.claude/hooks/`, new suite) coordinate multi-agent pipeline work: dispatch-message injection before card pickup, forced continue after card completion, idle backoff with overnight schedules, async Telegram notifications, session activity logging, and a composed Codex pretool safety hook.

Supporting these are the **pre-gauntlet** context collector, the **session** persistence layer for multi-round debate state, and the mostly-deprecated **execution planner** (concern parsing only). The retired **MCP Tasks** server, `task_manager.py`, `scope.py`, and the `gauntlet_monolith.py` shim are deleted with no dangling imports.

## Primary Data Flows

### Debate Critique Flow

Spec arrives via stdin → input stats logged (sha256 + line count) → pipeline-card + staleness gates → preflight ping → `call_models_parallel()` fans out via ThreadPoolExecutor → `ModelResponse` objects collected (per-model partial results checkpointed as they land, surviving process kills) → consensus check → session checkpoints + optional Telegram round notification.

### Gauntlet Stress-Test Flow

`run_gauntlet()` (orchestrator.py:205) takes spec + `GauntletConfig` (which centralizes what used to be 13 scattered defaults). Phase 1 groups adversary×model pairs by provider and paces batches per `get_rate_limit_config` (e.g. free Gemini = 1 call/15s) before ThreadPoolExecutor dispatch. Concerns get stable hash IDs (`generate_concern_id`). Phases 2–6 synthesize, filter, cluster, evaluate (tiered batches, optional multi-model consensus), rebut, and adjudicate; Phase 7 optionally runs the final boss. Per-phase `PhaseMetrics` append into a crash-surviving run manifest; for system-altitude pipeline sessions the skill conductor additionally writes intensity fields (`session_altitude`, `adversaries` with families, `foci`) that fizzy's `pipeline_mark_gauntlet_complete` verifies.

### Cost Tracking Flow

Every model call reports to `token_tracking.tracker.record_call()` — `MODEL_COSTS` lookup for API models, zero for CLI models, `DEFAULT_COST` fallback — under a threading.Lock. Summaries surface via `--show-cost`, Telegram payloads, and run-manifest phase metrics.

### Multi-Agent Coordination Flow (hooks)

Workers calling `pipeline_do_next_task` first get pending dispatch messages injected (`dispatch_check.py`, baseline-tracked line counts of `.conductor/dispatch/<role>/updates.jsonl`); after completing/reviewing/testing a card, `pipeline_continue.py` injects a do-not-stop message; idle results trigger `pipeline_idle_retry.py` exponential backoff (30→240s daytime, →960s overnight) with conductor status escalation after 6 idles; `pipeline_notifications.py` fires async Telegram + auto-dispatch.

## Key Architectural Decisions

- **Single-invocation CLI, no daemon**: continuity via session files and checkpoints.
- **ThreadPoolExecutor for model parallelism**: up to 32 workers in gauntlet Phase 1; rate-limit pacing happens synchronously before batch submission, not inside the pool.
- **FileLock-guarded atomic checkpoints with integrity envelopes**: temp+fsync+rename, sha256 `data_hash`, schema/spec/config-hash validation on resume.
- **Deterministic code over LLM subagents for data processing**: clustering (Jaccard) and batch tiering (pure functions) replaced LLM-based steps after measured concern loss.
- **LiteLLM as provider abstraction; CLI subprocess for subscription models.**
- **Preflight before dispatch**: fail on bad model/auth in seconds (skippable with `--skip-preflight`).
- **Gates over conventions**: pipeline-card and tests-staleness gates are enforced in `debate.py`, not just documented.
- **Hooks as the coordination plane**: worker sequencing is enforced by PostToolUse/PreToolUse hooks injecting system messages, replacing the deleted MCP Tasks server.

## Non-Obvious Things

- **Two gauntlet CLIs with divergent flags**: `debate.py` (`--codex-reasoning`, `--gauntlet-resume`, timeout default 1200s) vs `gauntlet/cli.py` (`--attack-codex-reasoning`, `--resume`, timeout default 1800s). Same backend.
- **`prompts.py` shadow collision**: putting `gauntlet/` on `sys.path` shadows top-level `prompts.py` with `gauntlet/prompts.py`. Pytest pythonpath prefers `scripts/`; standalone loaders should use `importlib.util.spec_from_file_location` for `gauntlet/persistence.py`.
- **Phase 1 parse failures are FATAL by design** — raw responses are saved and the run aborts rather than silently dropping an adversary's output; recovery = extract concerns manually, patch the checkpoint (IDs via `generate_concern_id`, integrity via `persistence._data_hash`), re-run with `--resume`.
- **Unattended mode monkey-patches `builtins.input`** (restored in `finally`); final boss falls back to skip on EOF.
- **No "Spec" dataclass**: specs are plain strings tracked by sha256.
- **PROGRAMMING_BUGS tuple** (`core_types.py`): TypeError/NameError/AttributeError propagate out of broad handlers.
- **Run-manifest intensity fields are conductor-written**, not orchestrator-written: the skill appends `session_altitude`/`adversaries`/`foci` after a run for v4+ altitude sessions.
- **Hooks never import skill code** — clean boundary; only `_resolve_config.py` is shared between hooks.

## Component Map

| Component | Purpose | Key Entry |
|-----------|---------|-----------|
| Debate Engine | CLI routing, gates, multi-round debate | `main()` at debate.py:1499 |
| Gauntlet Pipeline | 7-phase adversarial stress-test | `run_gauntlet()` at gauntlet/orchestrator.py:205 |
| Models | LLM call abstraction + preflight | `call_models_parallel()` / `preflight_models()` models.py |
| Token Tracking | Thread-safe cost/token accounting | `tracker` singleton token_tracking.py:66 |
| Providers | Model config, costs, Bedrock, CLI detection | providers.py |
| Adversaries | Personas + templates + concern IDs | adversaries.py |
| Prompts | Debate prompt templates | prompts.py (gauntlet prompts live in gauntlet/prompts.py) |
| Emission Toolchain | Fizzy plan emission + offline self-check | mini_spec_emission.py (validation_emission.py incoming) |
| Pre-Gauntlet | Git/system context collection | `run_pre_gauntlet()` pre_gauntlet/orchestrator.py |
| Session | Debate state persistence | `SessionState` session.py:17 |
| Harness Hooks | Multi-agent pipeline coordination | .claude/hooks/*.py |
| Execution Planner | Gauntlet concern parsing (deprecated remainder) | execution_planner/gauntlet_concerns.py |

Retired: MCP Tasks (deleted June 2026 — Fizzy pipeline board is the task system).

For detailed component docs, see `structured/components/`.
