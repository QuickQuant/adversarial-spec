# Discovery: Dependencies (incremental 9ca3ccd→f198887, 2026-06-11)

EXTERNAL_PACKAGES:
- litellm 1.80.13: model API abstraction (models.py try-except import, debate.py guard)
- filelock 3.16.1: checkpoint/stats lock files (gauntlet/persistence.py)
- pydantic >=2.0: imported in persistence.py (legacy compat, not actively used); ALSO used by pre_gauntlet/models.py
- python-dotenv >=1.0: providers.py loads $HOME/.config/secrets/llm-providers (declared)
- mcp >=1.0: declared, not imported in scope (harness-level)

HUBS:
- gauntlet/core_types.py — imported by 12+ (all phases, persistence, model_dispatch, medals, clustering, batch_tiering). Exports Concern, Evaluation, Rebuttal, GauntletConfig, GauntletResult, PhaseMetrics, FinalBossVerdict/Result, ExplanationMatch. No side effects; imports only adversaries.
- adversaries.py — imported by 6 (orchestrator, core_types, debate, execution_planner, gauntlet/__init__, phases). ADVERSARIES (MappingProxyType frozen), Adversary, AdversaryTemplate v2.0 (scope_guidelines frozen mapping), FINAL_BOSS, PRE_GAUNTLET, generate_concern_id, resolve_adversary_name.
- token_tracking.py — orchestrator, models, debate (+phase_4). Mutable global singleton tracker (threadsafe).
- providers.py — models, debate. MODEL_COSTS, DEFAULT_COST, *_AVAILABLE flags, BEDROCK_MODEL_MAP. Side effect: load_dotenv at import.
- prompts.py — models, providers. COLLISION: gauntlet/prompts.py shadows when gauntlet/ on sys.path; pytest pythonpath prefers scripts/ (pyproject.toml:79); documented in gauntlet/__init__ shim. Safe in current config.
- models.py — model_dispatch, debate.

GAUNTLET DAG: orchestrator → phase_1..7 + model_dispatch, persistence, clustering, batch_tiering, medals, reporting, synthesis_extract. No back-edges, no cycles.

PRE_GAUNTLET: orchestrator imports collectors/extractors/integrations/.models/.alignment_mode/.context_builder/.discovery; sys.path insert parent.parent.

EXECUTION_PLANNER: gauntlet_concerns.py sys.path dual-layout insert; only cross-import = adversaries.generate_concern_id.

HOOKS: isolated; only _resolve_config.py shared (lru_cache, env GEMINI_PROJECT_DIR/CLAUDE_PROJECT_DIR → git root → script dir; default mode flexible). Hooks do NOT import skills/scripts (clean boundary).

CONFIG_SOURCES:
- $HOME/.config/secrets/llm-providers ← providers.py:15 (load_dotenv)
- $HOME/.config/adversarial-spec/profiles ← providers.py:17
- $HOME/.claude/adversarial-spec/config.json ← providers.py:18
- .adversarial-spec/session-state.json ← session.py:14
- .adversarial-spec-gauntlet/ ← persistence.py:44 (GAUNTLET_DIR)
- ~/.adversarial-spec/ (runs/, adversary_stats.json, medals/) ← persistence.py, medals.py
- hook_config.json ← _resolve_config.py
- ADVERSARIAL_SPEC_UNAVAILABLE_MODELS env ← model_dispatch.py:154

VIOLATIONS/RISKS:
1. prompts.py shadow collision (mitigated by pytest pythonpath; runtime importlib workaround needed when loading persistence standalone — observed 2026-06-11).
2. providers.py hardcodes secrets path under $HOME.
3. No circular imports detected.
4. DELETED MODULES CONFIRMED ABSENT (no dangling imports): mcp_tasks, task_manager, scope, gauntlet_monolith.

NEW MODULES: mini_spec_emission.py (stdlib-only standalone; consumed by debate.py Phase 7 flows + upcoming validation_emission.py pattern), token_tracking.py (hub), gauntlet/batch_tiering.py + clustering.py (orchestrator support, import core_types only).

LAYERS: external APIs → config/secrets (providers) → core utils (token_tracking, adversaries, prompts) → types (core_types) → model calling (models) → gauntlet pipeline → pre_gauntlet/planner → CLI/session (debate, session) → hooks (isolated).
