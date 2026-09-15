# Discovery: Entry Points

> Full nuke run; normalized from a delegated explorer. Verified at `2433efa` against the dirty worktree.

## Primary CLI and module entries

ENTRY: `debate.main`
FILE: `skills/adversarial-spec/scripts/debate.py:1623`
TYPE: cli
TRIGGER: direct `debate.py` invocation
CALLS: parser, pipeline-card gate, model preflight, session/resume, critique or gauntlet dispatch
NOTES: critique and gauntlet enforce a Fizzy pipeline-card gate.

ENTRY: `gauntlet.cli.main`
FILE: `skills/adversarial-spec/scripts/gauntlet/cli.py:13`
TYPE: cli
TRIGGER: `PYTHONPATH=skills/adversarial-spec/scripts python -m gauntlet`
CALLS: optional pre-gauntlet, `run_gauntlet`, report/leaderboard readers
NOTES: reads spec from file or stdin; alignment mode can be interactive.

ENTRY: `gauntlet.orchestrator.run_gauntlet`
FILE: `skills/adversarial-spec/scripts/gauntlet/orchestrator.py:205`
TYPE: export
TRIGGER: both gauntlet CLI paths/importers
CALLS: attack, filtering, clustering, evaluation, rebuttal, adjudication, Final Boss, persistence
NOTES: public seven-phase gauntlet façade via `gauntlet/__init__.py:10`.

ENTRY: `validation_emission.main`
FILE: `skills/adversarial-spec/scripts/validation_emission.py:3423`
TYPE: cli
TRIGGER: validation-emission subcommand
CALLS: parser, `HANDLERS[subcommand]`, `_emit`
NOTES: stdout is always JSON `Envelope`; errors are caught at this boundary.

ENTRY: `gauntlet_check_cli.main`
FILE: `skills/adversarial-spec/scripts/gauntlet_check_cli.py:27`
TYPE: cli
TRIGGER: direct check CLI invocation
CALLS: TMR parse, spine coverage, gate result writer
NOTES: rejects path arguments outside workspace.

ENTRY: `dependency_semantics.main`
FILE: `skills/adversarial-spec/scripts/dependency_semantics.py:525`
TYPE: cli
TRIGGER: direct invocation with `--plan`
CALLS: `analyze_plan`, JSON serializer
NOTES: read-only JSON report.

ENTRY: `usage_router.main`
FILE: `skills/adversarial-spec/scripts/usage_router.py:145`
TYPE: cli
TRIGGER: direct optional-prompt invocation
CALLS: local usage fetch, route selection, Codex dispatch
NOTES: Gemini can be selected but is not dispatched by this script.

ENTRY: `telegram_bot.main`
FILE: `skills/adversarial-spec/scripts/telegram_bot.py:404`
TYPE: cli
TRIGGER: `setup|send|poll|notify` subcommand
CALLS: selected argparse handler
NOTES: network protocol boundary; configuration comes from named environment variables.

ENTRY: `migrate-journey-to-log.main`
FILE: `skills/adversarial-spec/scripts/migrate-journey-to-log.py:81`
TYPE: cli
TRIGGER: direct migration invocation
CALLS: session glob and migration
NOTES: mutates sessions unless `--dry-run`.

## Validation mutation subcommands

- `handle_derive_conops` — `validation_emission.py:688`
- `handle_check_rows` — `validation_emission.py:715`
- `handle_normalize_rows` — `validation_emission.py:1093`
- `handle_record_evidence` — `validation_emission.py:1183`
- `handle_assemble_digest` — `validation_emission.py:1528`
- `handle_record_send` / `handle_cancel_batch` / `handle_reset_failed` / `handle_supersede_row` — `validation_emission.py:1757-1988`
- `handle_parse_reply` / `emit_system_validation` / `handle_self_check` / `handle_status` — `validation_emission.py:2348-3102`

## Hook entries

` .claude/settings.json:3` declaratively registers Claude hook handlers. The main externally invoked entries include `fizzy_payload_guard.main` (`.claude/hooks/fizzy_payload_guard.py:86`), `pipeline_notifications.main` (`pipeline_notifications.py:392`), `session_activity_logger.main` (`session_activity_logger.py:55`), and the command safety hooks under `.claude/hooks/`.

## Packaging finding

`pyproject.toml:45-46` declares `adversarial_spec.debate:main` and `adversarial_spec.gauntlet_check_cli:main`, but the traced runtime is under `skills/adversarial-spec/scripts`; this package-path drift is a diagnosis candidate.
