# Phase 1 Discovery: Entry Points

> Architecture verified at `ef18c66`.
> The five delegated explorers were started in parallel but timed out and were
> shut down after repeated waits. This is the evidence-backed local fallback;
> the limitation is recorded in the manifest warnings.

## Runtime entry points

ENTRY: adversarial_spec.debate:main
FILE: pyproject.toml:48; skills/adversarial-spec/scripts/debate.py:1623
TYPE: cli
TRIGGER: installed `adversarial-spec` console script or direct module/script invocation
CALLS: create_parser, apply_profile, parse_models, validate_models_before_run, handle_gauntlet, run_critique, output_results
NOTES: canonical source is under `skills/adversarial-spec/scripts`; root `adversarial_spec` is a symlink to that directory.

ENTRY: adversarial_spec.gauntlet_check_cli:main
FILE: pyproject.toml:49; skills/adversarial-spec/scripts/gauntlet_check_cli.py:27
TYPE: cli
TRIGGER: installed `gauntlet-check` console script
CALLS: load session/roadmap inputs, run gate checks, write_result_and_exit
NOTES: emits a `GateResult` envelope and maps outcomes to process exit codes.

ENTRY: gauntlet.__main__:main
FILE: skills/adversarial-spec/scripts/gauntlet/__main__.py:3; skills/adversarial-spec/scripts/gauntlet/cli.py:13
TYPE: cli
TRIGGER: `python -m gauntlet`
CALLS: parse gauntlet CLI, run_gauntlet, load/save checkpoint and manifest, render output
NOTES: separate from the top-level debate CLI; flags and defaults are not aliased.

ENTRY: validation_emission.main
FILE: skills/adversarial-spec/scripts/validation_emission.py:3423
TYPE: cli
TRIGGER: direct script/module execution with one of the validation-emission subcommands
CALLS: build_parser, command handler, _emit
NOTES: stdout is a one-line JSON `Envelope`; exit codes are 0/2/3 for ok/issues/environment failures.

ENTRY: dependency_semantics.main
FILE: skills/adversarial-spec/scripts/dependency_semantics.py:525
TYPE: cli
TRIGGER: direct module/script execution against a plan JSON and optional semantics document
CALLS: analyze_plan, JSON input/output helpers
NOTES: returns a machine-readable dependency report; no network boundary.

ENTRY: telegram_bot.main
FILE: skills/adversarial-spec/scripts/telegram_bot.py:404
TYPE: cli
TRIGGER: direct Telegram helper invocation (`setup`, `send`, `poll`, or `notify`)
CALLS: get_config, cmd_setup/cmd_send/cmd_poll/cmd_notify
NOTES: reads `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` by name only; calls Telegram HTTP APIs.

ENTRY: usage_router.main
FILE: skills/adversarial-spec/scripts/usage_router.py:145
TYPE: cli
TRIGGER: direct usage-router invocation
CALLS: fetch_snapshot, extract_usage, pick_route, dispatch, reply_telegram
NOTES: reads a local headroom JSON endpoint, selects a model route, then dispatches to Codex/Gemini CLI.

ENTRY: migrate-journey-to-log.main
FILE: skills/adversarial-spec/scripts/migrate-journey-to-log.py:81
TYPE: cli
TRIGGER: direct migration script invocation
CALLS: migrate_session, atomic_write_json
NOTES: idempotently converts session journey data into a decision log; supports dry-run.

ENTRY: PreGauntletOrchestrator.run_pre_gauntlet
FILE: skills/adversarial-spec/scripts/pre_gauntlet/orchestrator.py:207
TYPE: export
TRIGGER: top-level gauntlet flow requests compatibility checks
CALLS: load_config_from_pyproject, context/discovery/build checks, save_report
NOTES: produces COMPLETE, NEEDS_ALIGNMENT, ABORTED, CONFIG_ERROR, or INFRA_ERROR status.

ENTRY: codex_pretool_combined.main
FILE: .claude/hooks/codex_pretool_combined.py:57
TYPE: event
TRIGGER: Claude Code pre-tool hook invocation with JSON on stdin
CALLS: load_and_run for configured sub-hooks
NOTES: hook subprocess emits the combined decision to stdout; sub-hooks are safety/pipeline classifiers.

ENTRY: pipeline_continue.main / pipeline_idle_retry.main
FILE: .claude/hooks/pipeline_continue.py:70; .claude/hooks/pipeline_idle_retry.py:73
TYPE: event
TRIGGER: Claude Code post-tool or pipeline-idle hook invocation
CALLS: role detection, tool-result parsing, system-message generation
NOTES: lane/role behavior is driven by hook input plus role environment variables.

ENTRY: dispatch_check.main / pipeline_notifications.main
FILE: .claude/hooks/dispatch_check.py:86; .claude/hooks/pipeline_notifications.py:392
TYPE: event
TRIGGER: hook input describing agent dispatch or card completion/review
CALLS: role/event extraction, Fizzy/Telegram notification helpers, local dispatch logging
NOTES: notifications are side effects; they are not proof that a card transition succeeded.

## Exported library surfaces

- `gauntlet.run_gauntlet` is exported by `skills/adversarial-spec/scripts/gauntlet/__init__.py:11`.
- Model/provider helpers are imported by the debate and gauntlet packages; the most important dispatch boundary is `models.call_models_parallel` at `models.py:1114`.
- Validation and TMR modules are imported by tests and by the gate/promotion toolchain rather than registered as separate package entry points.
