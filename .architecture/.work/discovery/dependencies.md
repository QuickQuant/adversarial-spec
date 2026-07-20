# Phase 1 Discovery: Dependencies

> Architecture verified at `ef18c66`. This report is a local fallback because
> the five delegated explorers were shut down after timeout.

## Source/package topology

- Canonical runtime source is `skills/adversarial-spec/scripts/`; the tracked root entry `adversarial_spec` is a symlink to that directory (`ls -ld` at scan time). `pyproject.toml:39-44` packages `adversarial_spec*` and `execution_planner*`.
- Console scripts are declared at `pyproject.toml:48-49`.
- The skill definition and phase/reference documents live under `skills/adversarial-spec/`; they are consumed by Claude Code rather than imported by the Python runtime.
- `execution_planner/` currently contains the gauntlet-concern parser; cached deleted/legacy modules are excluded from the map.
- `docs/adversarial-spec-gemini-bundle-20260318/` is a historical snapshot, not an active import target.

## Internal dependency graph

adversarial_spec.debate
  imports: models, providers, prompts, session, adversaries, gauntlet, pre_gauntlet, execution_planner, Telegram/helpers
  imported_by: console script, tests, direct module users

adversarial_spec.models
  imports: litellm, subprocess, concurrent.futures, providers, token_tracking
  imported_by: debate, gauntlet.model_dispatch, tests

adversarial_spec.providers
  imports: pathlib/json/os/shutil, model-cost/config definitions
  imported_by: models, debate, token_tracking, gauntlet.model_dispatch

adversarial_spec.gauntlet.orchestrator
  imports: core_types, persistence, model dispatch, phase modules, prompts, adversaries
  imported_by: debate and `gauntlet.__init__`/CLI

adversarial_spec.gauntlet.core_types
  imports: dataclasses/enum and adversaries concern-ID helper
  imported_by: every gauntlet phase, persistence, reporting, tests

adversarial_spec.gauntlet.persistence
  imports: FileLock, JSON/pathlib, core_types
  imported_by: orchestrator, phase modules, medals, CLI/reporting

validation_emission
  imports: FileLock, subprocess, hashlib, JSON/pathlib, Telegram reply helpers
  imported_by: CLI/tests and adjacent validation tooling

tmr_schema / tmr_parser / tmr_compile_step
  imports: Pydantic, JSON/hashlib/pathlib; parser/compiler chain is schema-first
  imported_by: phase8 promotion, classifiers, journal, tests, validation tools

guardrail_orchestration
  imports: dataclasses, JSON/pathlib, model/dispatch integration as configured
  imported_by: test ladder/guardrail callers and tests

.claude/hooks
  imports: standard library plus `_resolve_config`; hooks communicate by stdin/stdout and do not import skill runtime modules
  entry adapter: `codex_pretool_combined.py:18-65`

## External packages and system boundaries

- `litellm==1.80.13`: model API dispatch (`models.py` and `gauntlet/model_dispatch.py`).
- `filelock==3.16.1`: checkpoint, ledger, and provenance synchronization.
- `pydantic>=2.0`: TMR and gate-result validation.
- `mcp>=1.0.0`: external pipeline/MCP integrations in the broader skill surface.
- `python-dotenv>=1.0.0`: dependency declared; current provider code primarily reads environment variables and JSON profiles.
- Python subprocesses: Codex/Gemini/Claude/Antigravity CLIs (`models.py:298-688`, `usage_router.py:116`).
- HTTPS: LiteLLM providers, Telegram API (`telegram_bot.py:47-75`), and optional headroom routing.
- Filesystem: config/profiles under `~/.config/adversarial-spec` and `~/.claude/adversarial-spec`, run/checkpoint artifacts under `.adversarial-spec-gauntlet`, validation ledgers and spec artifacts.

## Configuration sources

- Provider credentials and availability: environment variable names accessed by `providers.py:16`, `providers.py:299-340`, `gauntlet/model_dispatch.py:160-301`; values are never part of this map.
- Model profiles: `~/.config/adversarial-spec/profiles/` and global config `~/.claude/adversarial-spec/config.json` (`providers.py:22-25`, `125-250`).
- Project compatibility: `pyproject.toml` `[tool.adversarial-spec.compatibility]` (`pre_gauntlet/orchestrator.py:254`).
- Hook behavior: `.claude/hooks/hook_config.json` and project/user config resolved by `_resolve_config.py:39`.

## Layer notes

- CLI/orchestration (`debate`, `gauntlet`, pre-gauntlet) depends on model/provider and persistence layers.
- TMR/validation modules form a schema and evidence layer used by Phase 8/pipeline guardrails.
- Hooks are an external coordination plane: they inspect tool events and emit decisions; direct imports into runtime skill code would violate the current separation.
- `adversarial_spec` symlink + `skills/.../scripts` canonical path creates a packaging/source-layout coupling and must remain explicit in downstream docs.
