# Entry Points

> Full system entrances. Generated: 2026-07-20T14:44:38-05:00 | Verified at `2433efa` against the dirty worktree.

## Summary

The runtime is CLI and hook dominated: the debate/gauntlet, validation, and TMR gate CLIs are primary entrances; `.claude/settings.json` registers a separate stdin/stdout hook plane. The root `adversarial_spec` symlink deliberately bridges console metadata to the traced source layout.

## Entry Point Table

| Entry point | File:line | Type | Trigger | Direct role |
|---|---|---|---|---|
| `debate.main()` | `scripts/debate.py:1623` | cli | direct debate script | gate, session, critique/gauntlet dispatch |
| `handle_gauntlet()` | `scripts/debate.py:898` | cli | `debate.py gauntlet` | invokes gauntlet/reporting |
| `gauntlet.cli.main()` | `scripts/gauntlet/cli.py:13` | cli | `python -m gauntlet` | optional pre-gauntlet then gauntlet |
| `run_gauntlet()` | `scripts/gauntlet/orchestrator.py:205` | export | gauntlet import/CLI | phase 1–7 pipeline |
| `validation_emission.main()` | `scripts/validation_emission.py:3423` | cli | validation subcommand | calls handler, emits Envelope |
| `gauntlet_check_cli.main()` | `scripts/gauntlet_check_cli.py:27` | cli | gate invocation | TMR/spine result |
| `dependency_semantics.main()` | `scripts/dependency_semantics.py:525` | cli | `--plan` invocation | JSON dependency analysis |
| `usage_router.main()` | `scripts/usage_router.py:145` | cli | optional prompt | headroom route/optional Codex |
| `telegram_bot.main()` | `scripts/telegram_bot.py:404` | cli | setup/send/poll/notify | Telegram protocol |
| `synthesis_extract.main()` | `scripts/gauntlet/synthesis_extract.py:119` | cli | direct script | run-log to synthesis input |
| `migrate-journey-to-log.main()` | `scripts/migrate-journey-to-log.py:81` | cli | direct script | legacy migration |
| `verification_tier_lint` block | `scripts/verification_tier_lint.py:220` | cli | direct module | fixed-path lint |
| `fizzy_payload_guard.main()` | `.claude/hooks/fizzy_payload_guard.py:86` | event | PreToolUse | block/allow Fizzy call |
| `pipeline_notifications.main()` | `.claude/hooks/pipeline_notifications.py:392` | event | PostToolUse | optional notification/dispatch |
| `session_activity_logger.main()` | `.claude/hooks/session_activity_logger.py:55` | event | hook lifecycle | append session JSONL |
| skill manifest | `skills/adversarial-spec/SKILL.md:2` | export | skill discovery | routes into session workflow |

## Important exported facades

- `gauntlet.run_gauntlet`, `format_gauntlet_report`, leaderboard functions — `scripts/gauntlet/__init__.py:8-13`.
- `pre_gauntlet.run_pre_gauntlet`, `run_discovery`, `load_config_from_pyproject`, `save_report` — `scripts/pre_gauntlet/__init__.py:12-48`.
- `execution_planner.load_concerns_for_spec` — `execution_planner/__init__.py:14`.
- `extractors.extract_spec_affected_files` — `scripts/extractors/__init__.py:7`.

## Packaging note

`pyproject.toml:45-46` declares `adversarial_spec.debate:main` and `adversarial_spec.gauntlet_check_cli:main`; the root `adversarial_spec` symlink maps that package to `skills/adversarial-spec/scripts`. `uv run adversarial-spec --help` succeeds, so this is a verified packaging bridge rather than a path-drift finding.
