# Entry Points

> All system entrances: where execution begins or external input arrives.
> Generated: 2026-03-22 | Git: c3b5f8c

## Summary

27 entry points across 4 files. Dominated by CLI actions (18 via debate.py), with MCP tools (4), library APIs (5+), and one Telegram bot.

## Entry Point Table

```
ENTRY_POINT                      FILE:LINE                            TYPE      TRIGGER                           CALLS
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
main()                           debate.py:1493                       cli       adversarial-spec <action>          create_parser, handle_*, run_critique
main()                           gauntlet/cli.py:13                   cli       python -m gauntlet                 run_gauntlet, format_gauntlet_report
main()                           telegram_bot.py:404                  cli       direct script execution            cmd_setup, cmd_send, cmd_poll, cmd_notify
mcp.run()                        mcp_tasks/server.py:365              main      MCP protocol registration          FastMCP server loop
TaskCreate()                     mcp_tasks/server.py:98               export    MCP tool invocation                load_tasks, save_tasks
TaskGet()                        mcp_tasks/server.py:140              export    MCP tool invocation                load_tasks
TaskList()                       mcp_tasks/server.py:160              export    MCP tool invocation                load_tasks
TaskUpdate()                     mcp_tasks/server.py:261              export    MCP tool invocation                load_tasks, save_tasks
run_gauntlet()                   gauntlet/orchestrator.py:196         export    Called from debate.py or cli.py     all 7 phase functions
run_pre_gauntlet()               pre_gauntlet/orchestrator.py:207     export    Called from gauntlet cli            PreGauntletOrchestrator.run
call_models_parallel()           models.py:901                        export    Called from critique/gauntlet       call_single_model via ThreadPool
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

```
ENTRY: mcp.run()
FILE: mcp_tasks/server.py:365
TRIGGER: MCP protocol registration via pyproject.toml entry point
CALLS: FastMCP.run() — starts MCP server loop
NOTES: Exposes 4 tools. Stores tasks in .claude/tasks.json.
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
CALLS: call_models_parallel(), generate_diff(), save_checkpoint(), get_task_manager()
NOTES: Main multi-round debate loop. Supports session resumption.
```

### MCP Tools

```
ENTRY: TaskCreate()
FILE: mcp_tasks/server.py:98
TRIGGER: MCP tool invocation
CALLS: load_tasks(), save_tasks()
NOTES: Creates task with subject, description, metadata. Returns task with assigned ID.
```

```
ENTRY: TaskGet()
FILE: mcp_tasks/server.py:140
TRIGGER: MCP tool invocation
CALLS: load_tasks()
NOTES: Retrieves task by ID.
```

```
ENTRY: TaskList()
FILE: mcp_tasks/server.py:160
TRIGGER: MCP tool invocation
CALLS: load_tasks()
NOTES: Lists tasks with optional filtering by session_id, context_name, status. Supports list_contexts mode.
```

```
ENTRY: TaskUpdate()
FILE: mcp_tasks/server.py:261
TRIGGER: MCP tool invocation
CALLS: load_tasks(), save_tasks()
NOTES: Updates status, subject, description, metadata, dependencies.
```

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
