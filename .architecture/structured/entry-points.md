# Entry Points

> All runtime entrances and external-input surfaces. Generated at `ef18c66`; if a cited source file changes, trust source over this document.

## Summary

The project has CLI entry points for debate, gauntlet, gate checks, validation emission, dependency analysis, Telegram, usage routing, and migration, plus Claude Code hook event entrances. There are no HTTP server routes owned by this repository; outbound HTTP is used for Telegram and optional headroom/model services.

## Entry Point Table

| Entry point | File:line | Type | Trigger | Direct calls |
|---|---|---|---|---|
| `debate.main()` | `skills/adversarial-spec/scripts/debate.py:1623` | cli | `adversarial-spec` console script | parser, profile/model resolution, gates, critique/gauntlet handlers |
| `gauntlet_check_cli.main()` | `skills/adversarial-spec/scripts/gauntlet_check_cli.py:27` | cli | `gauntlet-check` console script | gate checks, result envelope, exit mapping |
| `gauntlet.cli.main()` | `skills/adversarial-spec/scripts/gauntlet/cli.py:13` | cli | `python -m gauntlet` | `run_gauntlet`, persistence, reporting |
| `validation_emission.main()` | `skills/adversarial-spec/scripts/validation_emission.py:3423` | cli | validation subcommand invocation | parser, command handler, envelope emitter |
| `dependency_semantics.main()` | `skills/adversarial-spec/scripts/dependency_semantics.py:525` | cli | plan-report invocation | `analyze_plan`, JSON output |
| `telegram_bot.main()` | `skills/adversarial-spec/scripts/telegram_bot.py:404` | cli | Telegram helper invocation | setup/send/poll/notify handlers |
| `usage_router.main()` | `skills/adversarial-spec/scripts/usage_router.py:145` | cli | usage-router invocation | headroom fetch, route selection, CLI dispatch |
| `migrate-journey-to-log.main()` | `skills/adversarial-spec/scripts/migrate-journey-to-log.py:81` | cli | migration script invocation | session migration, atomic write |
| `PreGauntletOrchestrator.run_pre_gauntlet()` | `skills/adversarial-spec/scripts/pre_gauntlet/orchestrator.py:207` | export | gauntlet compatibility check | config, collectors, discovery, context, validation commands |
| `run_gauntlet()` | `skills/adversarial-spec/scripts/gauntlet/orchestrator.py:205` | export | debate/standalone gauntlet caller | internal phases, persistence, final result |
| `codex_pretool_combined.main()` | `.claude/hooks/codex_pretool_combined.py:57` | event | Claude Code pre-tool hook | configured safety sub-hooks |
| `fizzy_payload_guard.main()` | `.claude/hooks/fizzy_payload_guard.py:86` | event | Fizzy MCP pre-tool hook | deny/warn/override logic |
| `pipeline_continue.main()` | `.claude/hooks/pipeline_continue.py:70` | event | successful pipeline tool result | role/result parsing, system message |
| `pipeline_idle_retry.main()` | `.claude/hooks/pipeline_idle_retry.py:73` | event | pipeline idle result | backoff, system message, status note |
| `dispatch_check.main()` | `.claude/hooks/dispatch_check.py:86` | event | agent dispatch/tool event | role/dispatch validation |
| `pipeline_notifications.main()` | `.claude/hooks/pipeline_notifications.py:392` | event | card completion/review event | event extraction, local/Telegram notification |

## CLI metadata

- `pyproject.toml:48` maps `adversarial-spec` to `adversarial_spec.debate:main`.
- `pyproject.toml:49` maps `gauntlet-check` to `adversarial_spec.gauntlet_check_cli:main`.
- `skills/adversarial-spec/scripts/gauntlet/__main__.py:3` delegates module execution to `gauntlet.cli.main`.

## Main / Startup

ENTRY: `debate.main`
FILE: `skills/adversarial-spec/scripts/debate.py:1623`
TRIGGER: installed console script or direct execution
CALLS: `create_parser`, utility handlers, `handle_gauntlet`, `run_critique`, output/session helpers
NOTES: gate enforcement occurs before expensive model calls; no daemon startup.

ENTRY: `validation_emission.main`
FILE: `skills/adversarial-spec/scripts/validation_emission.py:3423`
TRIGGER: direct script/module execution
CALLS: `build_parser`, `HANDLERS[args.subcommand]`, `_emit`
NOTES: stdout remains a single JSON envelope even on handled exceptions.

## Event / Hook Handlers

ENTRY: `codex_pretool_combined.main`
FILE: `.claude/hooks/codex_pretool_combined.py:57`
EVENT: Claude Code pre-tool JSON event
SOURCE: Claude Code hook runner
CALLS: `load_and_run` for each configured safety hook

ENTRY: `pipeline_continue.main`
FILE: `.claude/hooks/pipeline_continue.py:70`
EVENT: post-tool pipeline result
SOURCE: Claude Code hook runner
CALLS: `_detect_role`, tool-result parsing, stdout system message

ENTRY: `pipeline_notifications.main`
FILE: `.claude/hooks/pipeline_notifications.py:392`
EVENT: pipeline completion/review tool result
SOURCE: Claude Code hook runner
CALLS: `_extract_event`, `_handle_complete_task`, `_handle_review`, Telegram/local dispatch helpers
