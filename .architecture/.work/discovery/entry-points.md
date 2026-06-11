# Discovery: Entry Points (incremental 9ca3ccd→f198887, 2026-06-11)

ENTRY: main (debate CLI) | FILE: skills/adversarial-spec/scripts/debate.py:1499 | TYPE: cli
TRIGGER: python3 debate.py <action> (stdin spec input)
CALLS: create_parser, enforce_pipeline_card_gate, handle_info_command, handle_utility_command, handle_gauntlet, apply_profile, parse_models, load_context_files, setup_bedrock, validate_models_before_run, preflight_models, load_or_resume_session, run_critique, handle_send_final
NOTES: actions critique/gauntlet/diff/providers/profiles/sessions/adversary-stats/medal-leaderboard/adversary-versions/send-final/bedrock; session resume; Telegram optional; --timeout default 1200.

ENTRY: main (gauntlet CLI) | FILE: skills/adversarial-spec/scripts/gauntlet/cli.py:13 | TYPE: cli
TRIGGER: python -m gauntlet | NOTES: divergent flags (--attack-codex-reasoning, --resume); --eval-tier-strategy; --list-adversaries; --stats; --list-runs; --show-run.
ENTRY: __main__ (gauntlet pkg) | FILE: gauntlet/__main__.py:1 | TYPE: cli — wrapper to cli.main.

ENTRY: run_gauntlet | FILE: gauntlet/orchestrator.py:205 | TYPE: export
TRIGGER: debate.py/cli.py programmatic | CALLS: get_spec_hash, GauntletConfig, select_adversary_model/select_eval_model, generate_attacks, generate_big_picture_synthesis, filter_concerns_with_explanations, cluster_concerns, evaluate_concerns(_multi_model), run_rebuttals, final_adjudication, run_final_boss_review, save_checkpoint, update_run_manifest, save_gauntlet_run
NOTES: 7-phase pipeline; checkpoint/resume; unattended monkey-patches input(); medals + stats.

ENTRY: call_models_parallel | FILE: models.py (~948) | TYPE: export — ThreadPool dispatch, MAX_RETRIES=3, per-model partial checkpoints, CLI-vs-litellm routing.
ENTRY: preflight_models | FILE: models.py:922 | TYPE: export (NEW) — parallel credential/model ping pre-dispatch; PREFLIGHT_TIMEOUT=120; skippable --skip-preflight.
ENTRY: save_checkpoint | FILE: session.py:88 | TYPE: export — round checkpoints to .adversarial-spec-checkpoints/.
ENTRY: send_telegram_notification | FILE: debate.py:134 | TYPE: event — post-round, poll_for_reply; errors suppressed.
ENTRY: send_final_spec_to_telegram | FILE: debate.py:210 | TYPE: event — one-way final notify.
ENTRY: main (telegram_bot) | FILE: scripts/telegram_bot.py:404 | TYPE: cli — setup/send/poll/notify; env TELEGRAM_BOT_TOKEN/CHAT_ID.
ENTRY: main (migrate-journey-to-log) | FILE: scripts/migrate-journey-to-log.py:81 | TYPE: cli — one-shot journey→JSONL migration, idempotent, --dry-run.

## Hooks (harness)
ENTRY: codex_pretool_combined.py:57 | PreToolUse(Bash, codex) — composes banned_git/banned_fs/force_flag/pip_install via importlib; first failure wins.
ENTRY: dispatch_check.py:86 | PreToolUse(pipeline_do_next_task) — new dispatch-log lines → systemMessage; baseline /tmp/dispatch-baseline-{project}-{role}.txt; KNOWN_ROLES claude/codex/gemini/glm.
ENTRY: pipeline_continue.py:70 | PostToolUse(complete_task|review|test) — forces pipeline_do_next_task via systemMessage when ok=true.
ENTRY: pipeline_idle_retry.py:73 | PostToolUse(do_next_task) — idle backoff ACTIVE [30,60,120,240]s / OVERNIGHT [..,480,960]s; synchronous time.sleep; status post after 6 idles; counter /tmp/pipeline-idle-count-*.
ENTRY: pipeline_notifications.py:~55 | PostToolUse(pipeline_*) — async Telegram + auto-dispatch; config .conductor/notifications.json; exit 0 always.
ENTRY: session_activity_logger.py:55 | SessionStart/UserPromptSubmit/SessionEnd — JSONL append + 1MB rotation.
ENTRY: _resolve_config.py:39 | export — lru_cached project hook_config.json resolver (mode flexible default).

## Module exports
ADVERSARIES dict + FINAL_BOSS + PRE_GAUNTLET (adversaries.py); altitude_spec_shape/self_check_plan/emit_fizzy_plan (mini_spec_emission.py); GauntletConcernParser/load_concerns_for_spec (execution_planner/gauntlet_concerns.py); token_tracking.tracker singleton (token_tracking.py:66).

## Deletions verified — NO dangling imports: mcp_tasks/, task_manager.py, scope.py, gauntlet_monolith.py.
