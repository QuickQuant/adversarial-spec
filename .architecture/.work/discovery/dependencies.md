# Discovery: Dependencies

> Full nuke run; normalized from a delegated explorer.

DEPENDENCY_GRAPH:

`debate.py:73` imports token tracking, adversaries, gauntlet, models, prompts, providers, session and Telegram; it is the top-level debate runtime.

`gauntlet/orchestrator.py:16` imports domain types, all seven phases, model dispatch, clustering, medals and persistence; `gauntlet/__init__.py:10` and `gauntlet/cli.py:18` consume it.

`pre_gauntlet/orchestrator.py:15` coordinates collectors, extractors, git/process integrations and compatibility models; `pre_gauntlet/__init__.py:39` exposes it to gauntlet CLI.

`gauntlet_check_cli.py:12` imports gate result, spine coverage, TMR parser/schema; root console metadata points here.

HUBS:
- `gauntlet/core_types.py` — 24 importers (14 production, 10 tests)
- `tmr_schema.py` — 16 importers
- `adversaries.py` — 15 importers
- `gauntlet/model_dispatch.py` — 8 production importers
- `token_tracking.py` — 8 importers
- `gauntlet/persistence.py`, `gauntlet/prompts.py` — 7 each
- `gate_result.py`, `gauntlet/reporting.py`, `models.py`, `providers.py`, `.claude/hooks/_resolve_config.py` — 5 each

SHARED_UTILITIES:
- `generate_concern_id` — `adversaries.py:1535`
- `call_model` — `gauntlet/model_dispatch.py:64`, shared by phases 1-7
- `TokenTracker.record_call` — `token_tracking.py:21`; shared tracker at line 66
- `resolve_config` — `.claude/hooks/_resolve_config.py:39`
- `ProcessRunner.run` plus redaction — `integrations/process_runner.py:56-179`

EXTERNAL_PACKAGES:
- `litellm` — model backend (`gauntlet/model_dispatch.py:28`, `models.py:19-20`)
- `filelock` — persistence/provenance/validation writes
- `pydantic` — TMR, gate and pre-gauntlet models
- `python-dotenv` — provider env loader (`providers.py:12-20`)
- `tomli` fallback — `pre_gauntlet/orchestrator.py:269-275`; not declared in root dependency lists

CONFIG_SOURCES:
- Provider env file/name registry — `providers.py:15-23,297-566`
- Rate/model runtime flags — `gauntlet/model_dispatch.py:155-306`
- Telegram env names — `telegram_bot.py:36-44`
- Hook role/config precedence — `.claude/hooks/_resolve_config.py:9-71`, `dispatch_check.py:65-70`
- Consumer compatibility config — `pre_gauntlet/orchestrator.py:237-290`

ARCHITECTURAL_LAYERS:
- Entrypoints: debate, gauntlet, gate-check CLIs
- Orchestration: gauntlet/pre-gauntlet orchestrators
- Contracts: core types, adversaries, TMR, gate results
- Infrastructure: providers/models, artifacts, integrations
- Hooks: separate stdlib-oriented process plane

DRIFT: root console scripts/package discovery name `adversarial_spec` (`pyproject.toml:44-55`), while runtime source is `skills/adversarial-spec/scripts`; several modules mutate `sys.path` and tests use root `pythonpath` injection (`scripts/__init__.py:8-10`, `pre_gauntlet/orchestrator.py:15-16`, `execution_planner/gauntlet_concerns.py:17-26`, `pyproject.toml:80`).
