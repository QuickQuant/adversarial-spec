# Entry Points

> All system entrances: where execution begins or external input arrives.
> Generated: 2026-06-11 (incremental) | Git: f198887

## Summary

27 entry points across 4 files. Dominated by CLI actions (18 via debate.py), with MCP tools (4), library APIs (5+), and one Telegram bot.

## Entry Point Table

```
ENTRY_POINT                      FILE:LINE                            TYPE      TRIGGER                           CALLS
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
main()                           debate.py:1520                       cli       adversarial-spec <action>          create_parser, handle_*, run_critique
main()                           gauntlet/cli.py:13                   cli       python -m gauntlet                 run_gauntlet, format_gauntlet_report
main()                           telegram_bot.py:404                  cli       direct script execution            cmd_setup, cmd_send, cmd_poll, cmd_notify
main()                           gauntlet/synthesis_extract.py:119    cli       python -m gauntlet.synthesis_ext   extract_and_cluster_concerns
run_gauntlet()                   gauntlet/orchestrator.py:194         export    Called from debate.py or cli.py     all 7 phase functions
run_pre_gauntlet()               pre_gauntlet/orchestrator.py:51      export    Called from gauntlet cli            PreGauntletOrchestrator.run
call_models_parallel()           models.py:914                        export    Called from critique/gauntlet       call_single_model via ThreadPool
```

Types: `main` | `http` | `websocket` | `event` | `scheduled` | `cli` | `export`

## By Type

### Main / Startup

```
ENTRY: main()
FILE: skills/adversarial-spec/scripts/debate.py:1493
TRIGGER: `adversarial-spec <action>` CLI command (registered in pyproject.toml)
CALLS: create_parser(), handle_info_command(), handle_utility_command(), handle_execution_plan(),
       handle_gauntlet(), apply_profile(), parse_models(), setup_bedrock(), validate_models_before_run(),
       handle_send_final(), handle_export_tasks(), load_or_resume_session(), run_critique()
NOTES: Routes 18 actions via argparse. Master CLI entry for the entire system.
```

```
ENTRY: main()
FILE: skills/adversarial-spec/scripts/gauntlet/cli.py:13
TRIGGER: `python -m gauntlet` via __main__.py:3 or direct script invocation
CALLS: run_gauntlet(), format_gauntlet_report(), list_gauntlet_runs(), load_gauntlet_run(), get_adversary_leaderboard()
NOTES: Standalone gauntlet CLI with different flag names than debate.py (--resume vs --gauntlet-resume, --attack-codex-reasoning vs --codex-reasoning)
```

```
ENTRY: main()
FILE: skills/adversarial-spec/scripts/telegram_bot.py:404
TRIGGER: Direct script execution (__name__ == "__main__" at line 442)
CALLS: cmd_setup(), cmd_send(), cmd_poll(), cmd_notify()
NOTES: 4 subcommands. Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.
```

### CLI Action Handlers (debate.py)

```
ENTRY: handle_info_command()
FILE: skills/adversarial-spec/scripts/debate.py:639
TRIGGER: args.action in {providers, focus-areas, personas, profiles, sessions, gauntlet-adversaries, adversary-stats, medal-leaderboard, adversary-versions}
CALLS: list_providers(), list_focus_areas(), list_personas(), list_profiles(), etc.
NOTES: Query-only commands. No model calls.
```

```
ENTRY: handle_utility_command()
FILE: skills/adversarial-spec/scripts/debate.py:711
TRIGGER: args.action in {bedrock, save-profile, diff}
CALLS: handle_bedrock_command(), save_profile()
NOTES: Configuration management commands.
```

```
ENTRY: handle_gauntlet()
FILE: skills/adversarial-spec/scripts/debate.py:1018
TRIGGER: args.action == "gauntlet"
CALLS: run_gauntlet(), format_gauntlet_report(), load_run_manifest(), format_run_manifest()
NOTES: Reads spec from stdin. Parses comma-separated adversaries and models.
```

```
ENTRY: run_critique()
FILE: skills/adversarial-spec/scripts/debate.py:1206
TRIGGER: Called from main() for critique action
CALLS: call_models_parallel(), generate_diff(), save_checkpoint(), preflight_models()
NOTES: Main multi-round debate loop. Supports session resumption.
```

### MCP Tools

### Library / Orchestrator APIs

```
ENTRY: run_gauntlet()
FILE: skills/adversarial-spec/scripts/gauntlet/orchestrator.py:196
TRIGGER: Called from debate.py:handle_gauntlet() or gauntlet/cli.py:main()
CALLS: generate_attacks(), generate_big_picture_synthesis(), filter_concerns_with_explanations(),
       evaluate_concerns_multi_model()|evaluate_concerns_single_model(), run_rebuttals(),
       final_adjudication(), run_final_boss_review(), save_checkpoint(), calculate_medals()
NOTES: Core 7-phase gauntlet pipeline. Accepts GauntletConfig with timeout/reasoning/resume flags.
```

```
ENTRY: run_pre_gauntlet()
FILE: skills/adversarial-spec/scripts/pre_gauntlet/orchestrator.py:207
TRIGGER: Called from gauntlet/cli.py with --pre-gauntlet flag
CALLS: PreGauntletOrchestrator.run(), GitPositionCollector.collect(), SystemStateCollector.collect(),
       extract_spec_affected_files(), build_context(), run_alignment_mode()
NOTES: Returns PreGauntletResult. Runs compatibility/discovery checks. Can be disabled per doc_type.
```

```
ENTRY: call_models_parallel()
FILE: skills/adversarial-spec/scripts/models.py:901
TRIGGER: Called from run_critique() and gauntlet phases
CALLS: ThreadPoolExecutor → call_single_model() per thread → litellm.completion() or CLI subprocess
NOTES: Returns list[ModelResponse]. Implements 3-attempt exponential backoff retry.
```

### Event Loop / Polling

```
ENTRY: discover_chat_id()
FILE: skills/adversarial-spec/scripts/telegram_bot.py:223
TRIGGER: Called from cmd_setup()
CALLS: api_call() in infinite while True loop (line 238)
NOTES: Long-running polling loop. Exits on Ctrl+C. Prints chat IDs as they arrive.
```


## Added 2026-06-11 (incremental f198887)

ENTRY: preflight_models()
FILE: skills/adversarial-spec/scripts/models.py:922
TYPE: export
TRIGGER: debate.py main() before dispatch (skippable --skip-preflight)
CALLS: _preflight_single per model (parallel; PREFLIGHT_PROMPT "Reply with exactly: OK"; timeout 120s)
NOTES: returns {model: error|None}; failures abort before expensive dispatch

ENTRY: main (migrate-journey-to-log)
FILE: skills/adversarial-spec/scripts/migrate-journey-to-log.py:81
TYPE: cli
TRIGGER: one-shot migration utility (--dry-run supported)
NOTES: idempotent journey[]→JSONL extraction

ENTRY: hook suite (.claude/hooks/)
TYPE: event (harness PreToolUse/PostToolUse/Session lifecycle)
- codex_pretool_combined.py:57 — composes 4 safety hooks for codex Bash calls
- dispatch_check.py:86 — PreToolUse(pipeline_do_next_task): injects new dispatch-log messages
- pipeline_continue.py:70 — PostToolUse(complete/review/test): do-not-stop systemMessage
- pipeline_idle_retry.py:73 — PostToolUse(do_next_task): idle backoff 30→240s (→960s overnight), escalation at 6 idles
- pipeline_notifications.py — PostToolUse(pipeline_*): async Telegram + auto-dispatch (exit 0 always)
- session_activity_logger.py:55 — session lifecycle → .claude/session-activity.jsonl (1MB rotation)
NOTES: hooks never import skill code; shared helper _resolve_config.py

ENTRY: emit_fizzy_plan() / self_check_plan()
FILE: skills/adversarial-spec/scripts/mini_spec_emission.py:355 / :411
TYPE: export
TRIGGER: Phase-7 execution-plan emission; offline self-check before live pipeline_validate_plan
NOTES: PLAN_SCHEMA_VERSION=3; ALTITUDE_OBLIGATIONS component/subsystem/system

REMOVED (June 2026): all mcp_tasks/server.py entries (MCP Tasks retired), task_manager demo harness, gauntlet_monolith shim.
