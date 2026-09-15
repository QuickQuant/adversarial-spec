# Filesystem Map: adversarial-spec

> Generated: 2026-07-20T14:44:38-05:00 | Git: `2433efa` | Skill: 4.0

## Root Structure

| Directory/File | Purpose |
|---|---|
| `skills/adversarial-spec/` | canonical deployed skill, phase instructions, runtime scripts and tests |
| `skills/adversarial-spec/scripts/` | Python runtime: debate, providers, gauntlet, validation, TMR and integrations |
| `skills/adversarial-spec/scripts/gauntlet/` | seven phases, types, model dispatch, persistence, reports |
| `skills/adversarial-spec/scripts/pre_gauntlet/` | repository grounding, context building and alignment state |
| `skills/adversarial-spec/scripts/tests/` | primary pytest suite (configured in root `pyproject.toml`) |
| `execution_planner/` | concern parsing and dependency semantics package |
| `.claude/hooks/` | separate Python hook plane and hook configuration helpers |
| `.adversarial-spec/` | session/spec/checkpoint artifacts; excluded from architecture source mapping |
| `.architecture/` | generated architecture corpus |
| `docs/` | ADRs, plans and historical reports |
| `onboarding/`, `wisdom/` | process/domain guidance, not runtime |
| `orchestration/`, `.reports/` | operational handoffs and generated briefing reports |

## Key Areas

| Path | Purpose |
|---|---|
| `scripts/debate.py` | top-level debate/gauntlet CLI and pipeline gates |
| `scripts/models.py`, `providers.py` | concurrent model calls, profiles and credential/config lookup |
| `scripts/session.py` | session/checkpoint JSON storage |
| `scripts/gauntlet/core_types.py` | central gauntlet contract dataclasses |
| `scripts/gauntlet/orchestrator.py` | phase sequence and final persistence |
| `scripts/gauntlet/persistence.py` | atomic locks, checkpoint/resume, run/stat artifacts |
| `scripts/validation_emission.py` | validation ledger and closeout CLI |
| `scripts/tmr_*.py`, `provenance_journal.py`, `phase8_promotion.py` | test-maturity evidence pipeline |
| `scripts/integrations/` | Git, process and knowledge-service boundaries |

## Entry Points

| File | How It Starts | What It Does |
|---|---|---|
| `scripts/debate.py` | direct Python invocation | critique, gauntlet and utility CLI |
| `scripts/gauntlet/__main__.py` | `python -m gauntlet` with scripts on path | standalone gauntlet CLI |
| `scripts/validation_emission.py` | direct Python invocation | ledger/evidence/digest/system-validation subcommands |
| `scripts/gauntlet_check_cli.py` | direct Python invocation | TMR spine/F-prime gate |
| `scripts/telegram_bot.py` | direct Python invocation | setup/send/poll/notify |
| `.claude/settings.json` | Claude Code loads project config | registers local hooks |

## Configuration Files

| File | Configures |
|---|---|
| `pyproject.toml` | root metadata, dependencies, console declarations, pytest/ruff/mypy |
| `skills/adversarial-spec/pyproject.toml` | skill-local dependency metadata |
| `.claude/settings.json` | project Claude hook registrations |
| `.mcp.json` | local Fizzy MCP server/board binding; do not expose its credential value |
| provider env/config paths in `providers.py:15-23` | named provider credentials and profiles |
| consumer `pyproject.toml` compatibility section | pre-gauntlet runtime policy |

## Notable Conventions

- The root `adversarial_spec` symlink maps the installed package name to the checked-in runtime source at `skills/adversarial-spec/scripts`; preserve this bridge during packaging changes.
- Tests live under the skill runtime tree and root pytest injects that scripts directory into `pythonpath` (`pyproject.toml:78-88`).
- `.adversarial-spec/` contains work artifacts, not architecture source; do not infer runtime contracts from it.
