# Entry Points

> All system entrances: where execution begins or external input arrives.
> Generated: 2026-02-06T20:35:00Z

## Summary

12 distinct entry points found: 6 CLI-invoked, 1 MCP server, 5 library/orchestrator APIs. The system is CLI-driven with the debate engine (`debate.py`) as the primary entry, routing to 18 different action handlers.

## Entry Point Table

```
ENTRY_POINT                      FILE:LINE                                TYPE     TRIGGER                          CALLS
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
main()                           scripts/debate.py:1933                   cli      `adversarial-spec` command       create_parser(), handle_*, run_critique()
main()                           scripts/gauntlet.py:3269                 cli      Direct script / __name__:3478    run_gauntlet(), format_gauntlet_report()
main()                           scripts/telegram_bot.py:404              cli      Direct script / __name__:442     cmd_setup(), cmd_send(), cmd_poll(), cmd_notify()
main()                           execution_planner/__main__.py:22         cli      `python -m execution_planner`    SpecIntake, TaskPlanner, format_plan_*()
module code                      scripts/task_manager.py:665              main     __name__ == "__main__"           TaskManager(), create_adversarial_spec_session()
mcp.run()                        mcp_tasks/server.py:365                  export   MCP protocol launch              FastMCP.run()
PreGauntletOrchestrator.run()    scripts/pre_gauntlet/orchestrator.py:51  export   Called from debate/gauntlet       collectors, extractors, context_builder
run_gauntlet()                   scripts/gauntlet.py                      export   Called from debate.py             adversary calls, evaluations, medals
call_models_parallel()           scripts/models.py                        export   Called from run_critique()        ThreadPoolExecutor, call_single_model()
TaskManager                      scripts/task_manager.py:114              export   Lazy-loaded by debate.py         create_task(), update_task(), list_tasks()
SessionState                     scripts/session.py                       export   Called for persistence            load(), save(), save_checkpoint()
handle_*() (6 variants)          scripts/debate.py:607+                   cli      Router dispatch from main()      Various per-action
```

Types: `main` | `cli` | `export` (MCP/library)

## By Type

### Main / CLI Entry Points

```
ENTRY: main()
FILE: skills/adversarial-spec/scripts/debate.py:1933
TRIGGER: `uv run python ~/.claude/skills/adversarial-spec/scripts/debate.py <action>`
CALLS: create_parser(), handle_info_command(), handle_utility_command(), handle_execution_plan(),
       handle_gauntlet(), apply_profile(), parse_models(), setup_bedrock(),
       validate_models_before_run(), load_or_resume_session(), run_critique()
NOTES: Main orchestrator. Routes to 18 action handlers based on argparse subcommands.
       Actions: critique, gauntlet, providers, focus-areas, personas, profiles, sessions,
       gauntlet-adversaries, adversary-stats, medal-leaderboard, adversary-versions,
       bedrock, save-profile, diff, send-final, export-tasks, execution-plan
```

```
ENTRY: main()
FILE: skills/adversarial-spec/scripts/gauntlet.py:3269
TRIGGER: `uv run python gauntlet.py` or called from debate.py:handle_gauntlet()
CALLS: argparse, run_gauntlet(), format_gauntlet_report()
NOTES: Standalone gauntlet runner. Can be invoked directly or via debate.py.
       Returns JSON or formatted text report.
```

```
ENTRY: main()
FILE: skills/adversarial-spec/scripts/telegram_bot.py:404
TRIGGER: `uv run python telegram_bot.py <subcommand>`
CALLS: cmd_setup(), cmd_send(), cmd_poll(), cmd_notify()
NOTES: 4 subcommands: setup (discover chat_id), send (pipe message), poll (wait for reply), notify (one-shot)
       Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars.
```

```
ENTRY: main()
FILE: execution_planner/__main__.py:22
TRIGGER: `python -m execution_planner`
CALLS: SpecIntake.parse_file(), GauntletConcernParser.parse_file(), TaskPlanner.auto_generate(),
       format_plan_as_markdown(), format_plan_as_summary()
NOTES: DEPRECATED. Full 6-phase execution pipeline. Being replaced by LLM guidelines approach.
```

### MCP / Server Entry Points

```
ENTRY: mcp.run()
FILE: mcp_tasks/server.py:365
TRIGGER: MCP protocol (registered in pyproject.toml as `mcp-tasks`)
CALLS: FastMCP.run() — exposes 4 tools via decorators:
       TaskCreate (line 98), TaskGet (line 140), TaskList (line 160), TaskUpdate (line 261)
NOTES: Shares storage with task_manager.py via .claude/tasks.json.
       Supports session_id and status filtering.
```

### Library / Orchestrator Entry Points

```
ENTRY: PreGauntletOrchestrator.run()
FILE: skills/adversarial-spec/scripts/pre_gauntlet/orchestrator.py:51
TRIGGER: Called from debate.py or gauntlet.py before main gauntlet
CALLS: GitPositionCollector.collect(), SystemStateCollector.collect(),
       extract_spec_affected_files(), build_context(), run_alignment_mode()
NOTES: Returns PreGauntletResult. Can be disabled per doc_type via CompatibilityConfig.
```

```
ENTRY: run_gauntlet()
FILE: skills/adversarial-spec/scripts/gauntlet.py
TRIGGER: Called from debate.py:handle_gauntlet() or gauntlet.py:main()
CALLS: Adversary concern generation, evaluation, rebuttal, big-picture synthesis, medal awards
NOTES: Core gauntlet engine. 6-phase pipeline with ThreadPoolExecutor parallelism.
```

```
ENTRY: call_models_parallel()
FILE: skills/adversarial-spec/scripts/models.py
TRIGGER: Called from debate.py:run_critique()
CALLS: ThreadPoolExecutor → call_single_model() per model
       call_single_model() routes to: litellm.completion(), call_codex_model(), or call_gemini_cli_model()
NOTES: Returns list[ModelResponse]. Retries with exponential backoff (3 attempts).
```

### Demo / Test Entry Points

```
ENTRY: module-level code
FILE: skills/adversarial-spec/scripts/task_manager.py:665
TRIGGER: `if __name__ == "__main__"` — demo/test execution
CALLS: TaskManager(), create_adversarial_spec_session(), get_session_summary()
NOTES: Creates a full 5-phase adversarial-spec session and prints summary stats. Demo only.
```
