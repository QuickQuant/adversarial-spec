# Discovery: Data Flow (incremental 9ca3ccd→f198887, 2026-06-11)

PATH: CLI Spec Input → Critique Debate Cycle
SOURCE: stdin + CLI args (debate.py main ~:1499)
TRANSFORMS: log_input_stats (debate.py:116, sha256+line count) → load_context_files (models.py) → load_profile (providers.py:198, ~/.config/adversarial-spec/profiles/) → preflight_models (models.py:922, parallel credential ping, NEW) → call_models_parallel (models.py:948, LiteLLM or CLI subprocess) → token_tracking.tracker.record_call (token_tracking.py:21) → save_critique_responses (session.py:105) → save_checkpoint (session.py:88) → detect_active_session (session.py:17) → SessionState.save (session.py:46)
SINK: stdout report/JSON; .adversarial-spec-checkpoints/ (round-{N}.md, round-{N}-critiques.json, round-{N}-{model}.json per-model partial saves at models.py:1020); ~/.config/adversarial-spec/sessions/{id}.json; .adversarial-spec/session-state.json
DATA_SHAPE: spec str + args → ModelResponse(model, response, agreed, spec, error, tokens, cost) → spec str + checkpoints
NOTES: per-model partial checkpoints survive kills; TokenTracker threadsafe (token_tracking.py:32); preflight failures exit before dispatch; CLI models via subprocess.run, API via litellm.completion.

PATH: Gauntlet Concern Generation → Phase 4 Batch Tiering
SOURCE: spec + GauntletConfig (orchestrator.py run_gauntlet ~:205)
TRANSFORMS: get_spec_hash (persistence.py) → _load_approved_prompts (orchestrator.py:125; FM-1 spec-hash gate raises ValueError at ~:145) → Phase1 generate_attacks (phase_1_attacks.py): call_model (model_dispatch.py:62) → _parse_json_concerns (phase_1_attacks.py:30) / parse_numbered_list fallback (:140) / _extract_severity_from_text (:106); Concern.id via generate_concern_id (adversaries.py) → save_checkpoint (concerns-{hash}.json + raw-responses-{hash}.json) → Phase3.5 cluster_concerns (clustering.py:83; _tokenize :56, _jaccard :64 thresh 0.65, _pick_representative :74; clustered-concerns-{hash}.json; auto when ≥200 concerns) → Phase4 tier_concerns_by_length (batch_tiering.py:73; _percentile_threshold :55 p60/p90; easy=75/med=30/hard=12; pick_eval_batch_arg :172; summarize_tiers :142) → evaluate_concerns_multi_model (phase_4_evaluation.py; evaluations-{hash}.json) → save_gauntlet_run (~/.adversarial-spec/runs/{hash}.json) → update_adversary_stats (~/.adversarial-spec/adversary_stats.json, FileLock persistence.py:74)
DATA_SHAPE: Concern(adversary,text,severity,id,source_model) → BatchTier list → Evaluation(concern_id, verdict accepted|dismissed|deferred, explanation, model); run manifest PhaseMetrics(phase_index,status,duration_s,tokens,models_used,spec_hash)
NOTES: concern IDs hash-stable (dedup deterministic); clustering deterministic; batch tiering pure function with flat fallback < tier_min_concerns (batch_tiering.py:200-210).

PATH: Execution Planner → Concern Linking; Pre-Gauntlet context
SOURCE: gauntlet concern JSON + spec (execution_planner/gauntlet_concerns.py:137)
TRANSFORMS: GauntletConcernParser.parse_file (:172) → _parse_concern (:192) → _extract_section_refs/_extract_title → GauntletConcern dataclass → indexes by_section/by_adversary/by_severity (:154-168). Pre-gauntlet (pre_gauntlet/orchestrator.py:56): extract_spec_affected_files, GitPositionCollector, SystemStateCollector, build_context, run_alignment_mode.
SINK: GauntletReport.to_json (:97); PreGauntletResult.context_markdown
NOTES: pre-gauntlet optional per doc_type (CompatibilityConfig, orchestrator.py:74).

PATH: Token & Cost Tracking
SOURCE: every model call (models.py call_*; model_dispatch.py call_model)
TRANSFORMS: tracker.record_call (token_tracking.py:21): MODEL_COSTS lookup (providers.py:21-50); CLI-prefixed models zero-cost; DEFAULT_COST fallback (providers.py:52, $5/$15 per 1M); threadsafe accumulate → tracker.summary (:49)
SINK: global singleton tracker (token_tracking.py:66); stdout --show-cost; Telegram payloads; run-manifest PhaseMetrics
NOTES: cost never persisted by token_tracking itself; gauntlet persistence integrates into manifests.

PATH: Hook session_activity_logger → conductor briefing
SOURCE: hook events SessionStart/UserPromptSubmit/SessionEnd (stdin JSON)
TRANSFORMS: find_project_root (:26 git rev-parse) → rotate_if_needed (:43, 1MB → .jsonl.1) → append JSONL {ts, session_id, event, project, source?, model?, reason?}; Stop/SessionEnd → stdout {"continue": true}
SINK: .claude/session-activity.jsonl (+.1 backup)
NOTES: never fails (exceptions swallowed :97).

PATH: Hook dispatch_check → worker coordination
SOURCE: PreToolUse on pipeline_do_next_task; .conductor/dispatch/{role}/updates.jsonl
TRANSFORMS: _detect_role (:54, env vars or .conductor/agents/*.json) → line-count vs baseline /tmp/dispatch-baseline-{project}-{role}.txt → new lines parsed → systemMessage injection
SINK: baseline file; stdout {decision: allow, systemMessage?}
NOTES: KNOWN_ROLES {claude, codex, gemini, glm} (:19); JSONL append-only.

PATH: Mini-Spec Emission → fizzy plan v3 contract
SOURCE: Phase 7 spec + execution plan (mini_spec_emission.py:99-250)
TRANSFORMS: altitude_spec_shape (:99; ALTITUDE_OBLIGATIONS; _FLOOR_FIELDS + _SUBSYSTEM_EXTRA + _SYSTEM_EXTRA superset chain) → _write_artifact (:123, returns 12-char sha256 plan_hash) → lint_requirement_text (:143, advisory; shall/will/should tiers) → representative_tree (:177) → self_check_plan (offline mirror of fizzy v4 altitude validation)
SINK: artifact_root files + plan_hash values + self-check dict
NOTES: v4 VERIFICATION-ONLY (no validation binding yet — the validation-leg spec adds that); REQUIREMENT_ID_RE ^[A-Z]+-R?\d+$; lint advisory-by-design (:148). THIS is the stated pattern for the upcoming validation_emission.py.

PATH: Model Dispatch → adversary attack selection (free-first)
SOURCE: GauntletConfig + env (model_dispatch.py:182-220)
TRANSFORMS: _get_unavailable_models (:154, ADVERSARIAL_SPEC_UNAVAILABLE_MODELS env) → select_adversary_model (:182, free-first: gemini-cli → groq → deepseek → gemini API) → select_eval_model (codex preferred; _select_codex_eval_model :162) → _validate_model_name (:43, injection prevention) → call_model (:62, CLI subprocess vs litellm, temp 0.7)
NOTES: o-series models reject custom temperature — wrapper adjusts (models.py:122-136).

DELETED MODULES CONFIRMED (no active data paths, grep-verified): mcp_tasks/, scripts/task_manager.py, scripts/scope.py (scope guidance now AdversaryTemplate.scope_guidelines adversaries.py:89), scripts/gauntlet_monolith.py (modularized into gauntlet/).

CRITICAL JUNCTIONS: FileLock sidecars on checkpoints + adversary stats (persistence.py:74); session resume via .adversarial-spec/session-state.json; hash-stable concern IDs; threadsafe TokenTracker; tier auto-fallback; approved-prompts spec-hash gate; hook coordination via session-activity.jsonl + dispatch updates.jsonl.
