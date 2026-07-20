# Filesystem Map: adversarial-spec

> Generated: 2026-07-19T08:43:13-05:00 | Git: ef18c66
> Skill version: 4.0 | Model: Codex | Architecture verified at `ef18c66`

## Root Structure

| Directory/File | Purpose |
|----------------|---------|
| `skills/` | Installed/deployed Claude Code skill definitions, phases, references, and canonical Python source |
| `adversarial_spec` | Symlink to `skills/adversarial-spec/scripts`; packaging/import alias |
| `execution_planner/` | Plan-side gauntlet concern parsing; currently secondary/partial |
| `scripts/` | Root-level test/support scripts; not the main runtime package |
| `tests/` | Root test area; currently sparse/legacy compared with `skills/.../scripts/tests` |
| `golden_cases/` | Test-maturity golden fixtures and manifest inputs |
| `docs/` | Historical generated bundles plus design/proposal documentation |
| `orchestration/` | Session/process handoffs and external review artifacts |
| `onboarding/` | Project practices and alignment notes |
| `wisdom/` | Project learning/process notes |
| `.claude/` | Claude Code settings, hooks, hook tests, and conductor dispatch state |
| `.claude-plugin/` | Plugin and personal marketplace manifests |
| `.architecture/` | Generated architecture corpus, manifest, discovery workspace, and human visuals |
| `.adversarial-spec/` | Session/spec/checkpoint state; excluded from source exploration |
| `.adversarial-spec-checkpoints/` | Historical checkpoint artifacts; excluded from runtime mapping |
| `.adversarial-spec-gauntlet/` | Generated gauntlet responses/reports; runtime persistence target, not source |
| `.reports/` | Generated HTML/operator reports and report state |
| `.conductor/` | Local conductor notifications/coordination state |
| `.agents/` | Agent metadata/configuration |
| `.github/` | Repository automation and workflow configuration |
| `.idea/`, `.vscode/` | IDE/editor metadata |
| `.venv/`, `venv/`, `skills/adversarial-spec/.venv/` | Python virtual environments; excluded |
| `adversarial_spec.egg-info/`, `skills/adversarial-spec/adversarial_spec_skill.egg-info/` | Build/install metadata |
| `.pytest_cache/`, `.ruff_cache/` | Tool caches; excluded |

## Key Areas

### `skills/adversarial-spec/`

| Path | Purpose |
|------|---------|
| `SKILL.md` | Claude Code skill entry and workflow contract |
| `phases/` | Eight adversarial-spec pipeline phase documents |
| `reference/` | Model, prompt, document-type, migration, and TMR references |
| `agents/` | Skill-specific agent prompts/roles |
| `scripts/` | Canonical Python runtime package and tests |
| `scripts/gauntlet/` | Gauntlet orchestration, phase modules, persistence, reporting, model dispatch |
| `scripts/pre_gauntlet/` | Compatibility/discovery/context checks |
| `scripts/tests/` | Main pytest suite, configured by `pyproject.toml:testpaths` |

### `skills/adversarial-spec/scripts/`

| Path | Purpose |
|------|---------|
| `debate.py` | Top-level CLI, critique loop, gates, session/output routing |
| `models.py`, `providers.py`, `prompts.py`, `adversaries.py` | model/config/prompt/persona shared layer |
| `session.py`, `gauntlet/persistence.py` | resumability and file-backed state |
| `tmr_schema.py`, `tmr_parser.py`, `tmr_compile_step.py` | strict TMR schema and compilation |
| `validation_emission.py` | validation ledger/evidence/digest CLI |
| `provenance_journal.py`, `phase8_promotion.py`, `tcov_liveness.py` | lineage, evidence, and close gates |
| `authoring_lint.py`, `verification_tier_lint.py`, `guardrail_orchestration.py` | document/test/guardrail checks |
| `dependency_semantics.py`, `execution_planner/` | plan graph and gauntlet concern tooling |

### `.claude/hooks/`

| Path | Purpose |
|------|---------|
| `codex_pretool_combined.py` | Runs configured hook sub-processors |
| `banned_*`, `bash_command_check.py`, `prod_deployment_guard.py`, `secret_exposure.py`, `force_flag_defense.py`, `pip_install_block.py`, `uv_run_check.py`, `deprecated_models.py` | command/safety checks |
| `dispatch_check.py`, `pipeline_continue.py`, `pipeline_idle_retry.py`, `pipeline_notifications.py`, `session_activity_logger.py`, `telegram_postcompact.py` | pipeline/session coordination and notification |
| `fizzy_payload_guard.py` | payload size/shape/override guard |
| `tests/` | hook unit tests |

## Entry Points

| File | How It Starts | What It Does |
|------|---------------|--------------|
| `pyproject.toml:48` → `debate.py:1623` | `adversarial-spec ...` | main debate/gauntlet CLI |
| `pyproject.toml:49` → `gauntlet_check_cli.py:27` | `gauntlet-check ...` | gate result/check CLI |
| `gauntlet/__main__.py:3` | `python -m gauntlet` | standalone gauntlet CLI |
| `validation_emission.py:3423` | direct script/module | validation/evidence subcommands |
| `dependency_semantics.py:525` | direct script/module | plan dependency report |
| `telegram_bot.py:404` | direct script/module | Telegram setup/send/poll/notify |
| `.claude/hooks/codex_pretool_combined.py:57` | Claude Code hook runner | combined safety/coordination decision |

## Configuration Files

| File | Configures |
|------|------------|
| `pyproject.toml` | package metadata, console scripts, dependencies, pytest/ruff/mypy, compatibility config |
| `uv.lock`, `requirements*.txt` | dependency resolution/legacy install surfaces |
| `.mcp.json` | local Fizzy MCP server and project board metadata; secret values are not architecture payload |
| `.claude/hooks/hook_config.json` | hook pattern/config behavior |
| `.claude/settings.json`, `.claude/settings.local.json` | Claude Code hook/tool settings |
| `~/.claude/adversarial-spec/config.json` | user-level provider/global config, loaded by `providers.py` |
| `~/.config/adversarial-spec/profiles/` | named model/provider profiles |
| `golden_cases/manifest.json` and spec-local `tmr-registry.json` | TMR/golden-case contract inputs |

## Notable Conventions

- Canonical Python source is nested under the skill directory but exposed through a root symlink; do not assume `adversarial_spec/` is a real directory.
- Runtime tests live under `skills/adversarial-spec/scripts/tests/`, while root `scripts/tests/` holds a separate validation-emission test surface.
- Generated state is intentionally file-backed and distributed across home config, project `.adversarial-spec-gauntlet`, spec-local ledgers, and Claude hook logs.
- `.architecture/HUMAN_READ_ONLY_visuals/` is for humans; structured docs are the LLM-facing payload.
- Historical docs/checkpoints and reports coexist with active code. Check import/entry-point reachability before treating a file as runtime.
