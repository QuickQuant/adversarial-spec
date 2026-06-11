# Discovery: Contracts (incremental 9ca3ccd→f198887, 2026-06-11)

TYPE_CONTRACTS:
- Concern (gauntlet/core_types.py:83-95): adversary, text, severity, id (auto via generate_concern_id → PREFIX-hash8, deterministic), source_model. Consumers: phases 1/4, persistence, reporting, execution_planner.
- Evaluation (core_types.py:99-110): concern, verdict normalized dismissed|accepted|acknowledged|deferred (normalize_verdict :72-74), reasoning, severity (falls back to concern.severity).
- Rebuttal (core_types.py:114-119): evaluation, response, sustained bool.
- GauntletResult (core_types.py:232-253): concerns, evaluations, rebuttals, final_concerns, models, total_time/cost, final_boss_result?, spec_hash, adversary_timing. signal_score = acceptance_rate - (1-acceptance_rate)*norm_effort*0.5.
- GauntletConfig (core_types.py:424-453): timeout (default 1800), attack/eval codex reasoning, auto_checkpoint, resume, unattended, eval_tier_strategy power_law_length|flat, eval_flat_batch_size, eval_tier_min_concerns. Replaces 13 scattered defaults (QUOTA BURN FIX 1).
- PhaseMetrics (core_types.py:482-497): phase, index, status completed|failed|skipped_resume, duration, tokens, models_used, config_snapshot, error?, spec_hash.
- FinalBossResult (core_types.py:207-229): verdict enum PASS|REFINE|RECONSIDER, concerns, alternate_approaches, dismissal_review_stats, approved property (compat).
- BigPictureSynthesis (core_types.py:123-137): real_issues, hidden_connections, whats_missing, meta_concern, high_signal.
- Medal (core_types.py:140-168): gold|silver|bronze, adversary(+version), concern, report, run_id, spec_hash.
- Adversary (adversaries.py:17-34): name, prefix, persona, dismissal/acceptance rules, version, content_hash() 12-char.
- AdversaryTemplate (adversaries.py:73-105): v2.0, tone, focus_areas, scope_guidelines frozen mapping keyed "{category}:{value}" vs VALID_SCOPE_KEYS.
- TokenTracker (token_tracking.py:11-47): threadsafe record_call/summary; CLI-prefixed models zero-cost.

API_CONTRACTS:
- debate.py CLI: actions critique|gauntlet|...; flags incl. --timeout default 1200 (CHANGED 2026-06-11 from 900), --codex-reasoning default xhigh (attack default low set per-call), --pipeline-card gate (card id | IntentionalOverride + >=50-char reason), --accept-tests-stale, --show-manifest [HASH].
- gauntlet/cli.py: DIVERGENT flags (--attack-codex-reasoning, --resume, --timeout default 1800).
- preflight_models(models, codex_reasoning, timeout, cwd) → dict[model, error|None]; PREFLIGHT_PROMPT "Reply with exactly: OK"; PREFLIGHT_TIMEOUT=120 (models.py:869-945).
- ModelResponse (models.py:140-150): model, response, agreed, spec?, error?, tokens, cost.

DATA_MODEL_SURFACES:
- Checkpoint envelope (persistence.py): {_meta:{schema_version=2, spec_hash, config_hash, phase, created_at, data_hash}, data:[...]}; data_hash = sha256(canonical_json sort_keys); files concerns-/raw-responses-/clustered-concerns-/evaluations-/final-boss-{hash8}.json under .adversarial-spec-gauntlet/.
- Run manifest (persistence.py:598-626): run-manifest-{hash8}-{ts}.json {spec_hash full, spec_as_gauntleted_path, status running|completed|failed|interrupted, created/updated_at, phases:[PhaseMetrics]}. NEW intensity fields (v4+ altitude sessions, written by skill conductor): session_altitude, adversaries:[{model,family}], foci[] — consumed by fizzy pipeline_mark_gauntlet_complete.
- Resolved concerns registry: {concern_id: {adversary, text, resolution, resolved_at, resolved_by_model}} — cross-run dismissal filter.
- Adversary stats ~/.adversarial-spec/adversary_stats.json (FileLock): per-adversary concerns_raised/accepted/dismissed/deferred/signal_score/dismissal_effort/rebuttals.
- Medals ~/.adversarial-spec/medals/ file-per-award.
- ADVERSARIES dict: frozen MappingProxyType, read-only public.
- MODEL_COSTS (providers.py:21-50) + DEFAULT_COST {input:5, output:15} per-1M.

REUSABLE INTERFACES:
- generate_concern_id(adversary, text) → "{PREFIX}-{hash8}" deterministic (adversaries.py).
- resolve_adversary_name(name_or_prefix) → Adversary|None, case-insensitive.
- mini_spec_emission.py: PLAN_SCHEMA_VERSION=3 (must match fizzy V4_PLAN_SCHEMA_VERSION); ALTITUDE_OBLIGATIONS {component:{component_verification}, subsystem:+subsystem, system:+system}; REQUIREMENT_ID_RE ^[A-Z]+-R?\d+$; emit_fizzy_plan(tree, session_id, slug, with_artifact_manifest, artifact_root) → v3 fizzy-plan.json (+12-char plan_hash artifacts); self_check_plan(plan) → {valid, issues[{code, task_id}]} mirroring live pipeline_validate_plan altitude branch; reject codes WRONG_SCHEMA_VERSION/NO_ROOT/MULTIPLE_ROOTS/ROOT_NOT_SYSTEM/INVALID_ALTITUDE/MISSING_LEVEL_VV/VV_ABOVE_ALTITUDE/VV_KIND_MISMATCH/ORPHAN_REALIZATION/UNDECOMPOSED_REQUIREMENT. VERIFICATION-ONLY in v4 (validation leg arrives with validation_emission.py — spec in flight on card 5604).
- batch_tiering.py: BatchTier(name, concerns, batch_size); tier_concerns_by_length(cuts p60/p90, sizes 75/30/12) pure/deterministic; pick_eval_batch_arg(strategy, ...) → int | list[BatchTier], min_concerns 30 fallback.
- clustering.py: cluster_concerns (Jaccard 0.65 single-link, deterministic), should_auto_cluster (>=200).

HOOK I/O: bash_command_check (stdin none, stderr message, exit 0/1/2 by mode); pipeline_notifications (fire-and-forget, exit 0 always, config .conductor/notifications.json); dispatch_check/pipeline_continue/pipeline_idle_retry emit {decision/systemMessage} JSON on stdout.

RETIRED CONTRACTS: mcp_tasks MCP task protocol (GONE — Fizzy pipeline is the task system); task_manager.py scheduling interface; scope.py (scope guidance lives in AdversaryTemplate.scope_guidelines); gauntlet_monolith.py (modularized).
