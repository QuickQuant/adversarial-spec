# Entry Points

> All system entrances: where execution begins or external input arrives.
> Generated: 2026-03-21 | Git: 12c5d3f

## Summary

27 entry points found: 12 CLI commands, 4 MCP tools, 1 polling loop, 2 pre-gauntlet APIs, 5 library exports, 3 info/utility handlers. The system is CLI-driven with `debate.py` as the primary entry, routing to action handlers. The gauntlet now has a standalone CLI via the extracted `gauntlet/` package.

## Entry Point Table

```
ENTRY_POINT                      FILE:LINE                                TYPE     TRIGGER                          CALLS
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
main()                           scripts/debate.py:1493                   cli      `adversarial-spec` command       create_parser(), handle_*, run_critique()
main()                           scripts/gauntlet/cli.py:13               cli      `python -m gauntlet` / __main__  run_gauntlet(), format_gauntlet_report()
main()                           scripts/telegram_bot.py:404              cli      Direct script / __name__:442     cmd_setup(), cmd_send(), cmd_poll(), cmd_notify()
handle_info_command()            scripts/debate.py:610                    cli      Info-type actions                list_providers(), list_personas(), etc.
handle_utility_command()         scripts/debate.py:682                    cli      Utility actions                  handle_bedrock_command(), save_profile()
handle_execution_plan()          scripts/debate.py:731                    cli      action == "execution-plan"       Execution plan handlers
handle_gauntlet()                scripts/debate.py:989                    cli      action == "gauntlet"             run_gauntlet(), format_gauntlet_report(), format_run_manifest()
handle_send_final()              scripts/debate.py:920                    cli      action == "send-final"           Model calls for final output
handle_export_tasks()            scripts/debate.py:938                    cli      action == "export-tasks"         extract_tasks(), models
run_critique()                   scripts/debate.py:1206                   cli      Critique workflow                call_models_parallel(), generate_diff()
task_manager demo                scripts/task_manager.py:665              main     __name__ == "__main__"           TaskManager(), create_adversarial_spec_session()
mcp.run()                        mcp_tasks/server.py:365                  export   MCP protocol launch              FastMCP.run()
TaskCreate                       mcp_tasks/server.py:98                   export   MCP tool call                    load_tasks(), save_tasks()
TaskGet                          mcp_tasks/server.py:140                  export   MCP tool call                    load_tasks()
TaskList                         mcp_tasks/server.py:160                  export   MCP tool call                    load_tasks()
TaskUpdate                       mcp_tasks/server.py:261                  export   MCP tool call                    load_tasks(), save_tasks()
discover_chat_id()               scripts/telegram_bot.py:223              event    cmd_setup() -> infinite poll     api_call() in while True loop
PreGauntletOrchestrator.run()    scripts/pre_gauntlet/orchestrator.py:51  export   Called from gauntlet/debate      collectors, extractors, context_builder
run_pre_gauntlet()               scripts/pre_gauntlet/orchestrator.py:207 export   Public API function              PreGauntletOrchestrator.run()
run_gauntlet()                   scripts/gauntlet/orchestrator.py:116     export   Called from debate.py, cli.py    phases 1-7, persistence, medals
call_models_parallel()           scripts/models.py:901                    export   Called from run_critique()        ThreadPoolExecutor, call_single_model()
TaskManager                      scripts/task_manager.py:114              export   Lazy-loaded by debate.py         create_task(), update_task(), list_tasks()
SessionState                     scripts/session.py:17                    export   Called for persistence            load(), save(), save_checkpoint()
execution_planner exports        execution_planner/__init__.py:9          export   from execution_planner import    GauntletConcernParser, load_concerns_for_spec()
mcp_tasks exports                mcp_tasks/__init__.py:3                  export   from mcp_tasks import mcp        FastMCP server instance
gauntlet package exports         scripts/gauntlet/__init__.py:8           export   from gauntlet import             ADVERSARIES, run_gauntlet, format_gauntlet_report, leaderboards
format_run_manifest()            scripts/gauntlet/reporting.py            export   --show-manifest handler          Formats PhaseMetrics telemetry for display
```

Types: `main` | `cli` | `export` | `event`

## By Type

### Main / CLI Entry Points

```
ENTRY: main()
FILE: skills/adversarial-spec/scripts/debate.py:1493
TRIGGER: `adversarial-spec <action>` (pyproject.toml entry point) or __name__
CALLS: create_parser(), handle_info_command(), handle_utility_command(), handle_execution_plan(),
       handle_gauntlet(), apply_profile(), parse_models(), setup_bedrock(),
       validate_models_before_run(), load_or_resume_session(), run_critique()
NOTES: Main orchestrator. Routes to action handlers based on argparse subcommands.
       Actions: critique, gauntlet, providers, focus-areas, personas, profiles, sessions,
       gauntlet-adversaries, adversary-stats, medal-leaderboard, adversary-versions,
       bedrock, save-profile, diff, send-final, export-tasks, execution-plan.
       Gauntlet-specific flags: --show-manifest [HASH], --gauntlet-resume, --codex-reasoning, --eval-codex-reasoning, --unattended
```

```
ENTRY: main()
FILE: skills/adversarial-spec/scripts/gauntlet/cli.py:13
TRIGGER: `python -m gauntlet` via gauntlet/__main__.py or direct module import
CALLS: run_gauntlet(), format_gauntlet_report(), list_gauntlet_runs(), load_gauntlet_run(), get_adversary_leaderboard()
NOTES: Standalone gauntlet CLI with all flags including --attack-codex-reasoning (distinct from debate.py --codex-reasoning).
       Also supports --resume, --unattended, --pre-gauntlet, --spec-file.
```

```
ENTRY: main()
FILE: skills/adversarial-spec/scripts/telegram_bot.py:404
TRIGGER: Direct script execution (__name__:442)
CALLS: create_parser with subparsers -> cmd_setup(), cmd_send(), cmd_poll(), cmd_notify()
NOTES: 4 subcommands. Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars.
```

### MCP / Server Entry Points

```
ENTRY: mcp.run()
FILE: mcp_tasks/server.py:365
TRIGGER: MCP protocol (registered in pyproject.toml as `mcp-tasks`)
CALLS: FastMCP.run() - exposes 4 tools via decorators:
       TaskCreate (line 98), TaskGet (line 140), TaskList (line 160), TaskUpdate (line 261)
NOTES: Shares storage with task_manager.py via .claude/tasks.json.
       Supports session_id, context_name, and status filtering. Supports list_contexts mode.
```

### Event / Polling Entry Points

```
ENTRY: discover_chat_id()
FILE: skills/adversarial-spec/scripts/telegram_bot.py:223
TRIGGER: Called from cmd_setup()
CALLS: api_call() in infinite while True loop (line 238)
NOTES: Polls Telegram API until user sends message. Runs until Ctrl+C.
```

### Library / Orchestrator Entry Points

```
ENTRY: run_gauntlet()
FILE: skills/adversarial-spec/scripts/gauntlet/orchestrator.py:116
TRIGGER: Called from debate.py:handle_gauntlet() or gauntlet/cli.py:main()
CALLS: GauntletConfig(), select_adversary_model(), select_eval_model(), _validate_model_name(),
       generate_attacks(), generate_big_picture_synthesis(), filter_concerns_with_explanations(),
       cluster_concerns_with_provenance(), evaluate_concerns_multi_model(), run_rebuttals(),
       final_adjudication(), run_final_boss_review(), save_gauntlet_run(), update_adversary_stats(),
       calculate_medals(), save_medal_reports(), update_run_manifest()
NOTES: Primary gauntlet API. Builds GauntletConfig from CLI params, sequences 7 phases,
       handles resume from checkpoints, emits PhaseMetrics telemetry per phase.
```

```
ENTRY: call_models_parallel()
FILE: skills/adversarial-spec/scripts/models.py:901
TRIGGER: Called from debate.py:run_critique()
CALLS: ThreadPoolExecutor -> call_single_model() per model
       Routes to: litellm.completion(), call_codex_model(), call_gemini_cli_model(), call_claude_cli_model()
NOTES: Returns list[ModelResponse]. Retries with exponential backoff (3 attempts, 1s/2s/4s).
```

```
ENTRY: PreGauntletOrchestrator.run()
FILE: skills/adversarial-spec/scripts/pre_gauntlet/orchestrator.py:51
TRIGGER: Called from debate.py or gauntlet/cli.py before main gauntlet
CALLS: GitPositionCollector.collect(), SystemStateCollector.collect(),
       extract_spec_affected_files(), build_context(), run_alignment_mode()
NOTES: Returns PreGauntletResult. Can be disabled per doc_type via CompatibilityConfig.
```
