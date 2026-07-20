# Component: Pre-Gauntlet Compatibility

> Derived from: `skills/adversarial-spec/scripts/pre_gauntlet/orchestrator.py`, `context_builder.py`, `discovery.py`, collectors | Verified at: `ef18c66`
> If any derived-from file changed since `ef18c66`, trust source over this doc.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Ground a spec in repository/build/schema reality before gauntlet review |
| Entry | `run_pre_gauntlet()` at `pre_gauntlet/orchestrator.py:207` |
| Key files | orchestrator, discovery, context builder, collectors |
| Depends on | pyproject config, git/system commands, optional validation commands |
| Used by | Debate Engine / gauntlet compatibility path |
| Runtime status | implemented |
| Architecture status | active_secondary |

## Contracts

### Boundary Field Contracts

Chain: compatibility config → subprocess checks → `PreGauntletResult`/report.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `command` | conditional per configured check | yes | subprocess runner | report | no check configured; status may remain incomplete | pyproject config | `orchestrator.py:254-293` | verified |
| `environment` | optional per check | yes | report metadata | report | environment unknown; do not infer production/development | config/runner | `orchestrator.py:254-293` | verified |
| status | always on result | yes | typed PreGauntletStatus | report/exit | failed orchestration if no result | orchestrator | `orchestrator.py:310-327` | verified |

## Invariants

- A blocker enters Alignment Mode rather than being silently ignored (`orchestrator.py:207-253`).
- Exit codes are stable and distinct for complete/alignment/abort/config/infra (`orchestrator.py:310-327`).
- Compatibility config is loaded from the project `pyproject.toml` rather than an untracked global default (`orchestrator.py:254`).

## Data Flow

```text
IN: spec + repo root + CompatibilityConfig
PROCESS: git/system collection -> service discovery -> build/schema/validation checks
OUT: PreGauntletResult + JSON report + exit code
```

## Key Functions

| Function | Purpose | Location |
|---|---|---|
| `run_pre_gauntlet()` | orchestration | `orchestrator.py:207` |
| `load_config_from_pyproject()` | typed config loader | `orchestrator.py:254` |
| `run_discovery()` | service/file discovery | `discovery.py:280` |
| `build_context()` | context document | `context_builder.py:213` |
| `save_report()` | report serialization | `orchestrator.py:293` |

## Error Handling

- Config, infrastructure, and alignment failures have separate status/exit codes.
- External command failures are collected into compatibility findings for operator alignment.

## Configuration

| Config | Source | Default | Precedence |
|---|---|---|---|
| compatibility enabled/base branch/build | `pyproject.toml` | configured/default typed values | project config overrides defaults |
| validation environment | per-command config | unknown | explicit environment wins |

## Integration Points

**Calls out to:** git/system/subprocess checks and file discovery.

**Called by:** debate gauntlet route and direct callers.

## Active vs Target

- **Active consumers:** optional pre-gauntlet path.
- **Target architecture:** keep compatibility checks as a clear precondition layer before adversarial model calls.

## LLM Notes

- “No blocker” means configured checks completed; it does not prove external production data is healthy unless the configured environment/command did that check.
