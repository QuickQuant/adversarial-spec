# Component: Debate Engine

> Derived from: `skills/adversarial-spec/scripts/debate.py`, `session.py`, `prompts.py` | Verified at: `ef18c66`
> If any derived-from file changed since `ef18c66`, trust source over this doc.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Top-level CLI, model/session gates, critique rounds, output routing |
| Entry | `main()` at `debate.py:1623` |
| Key files | `debate.py`, `session.py`, `prompts.py` |
| Depends on | Models/providers, adversaries, gauntlet, pre-gauntlet, Telegram |
| Used by | `adversarial-spec` console script, direct callers, tests |
| Runtime status | implemented |
| Architecture status | active_primary |

## What This Component Does

The Debate Engine turns CLI/user specification input into a sequence of model critiques and synthesized outputs. It also owns top-level routing into gauntlet, profile/model selection, session loading, pipeline-card/staleness gate enforcement, and final output delivery.

## Contracts

### Type Contracts

| Contract | Purpose | Owner | Consumed By |
|---|---|---|---|
| `argparse.Namespace` options | normalized CLI control plane | `debate.py:525-611` | all handlers |
| `ModelResponse` | model result/usage/error record | `models.py:141-151` | critique/output/session |
| `SessionState` | resumable debate state | `session.py:12-44` | load/save/checkpoint paths |

### Boundary Field Contracts

Chain: CLI input → `debate.main` → model routing → output/session.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| spec text | required from stdin/file/argument | yes | critique/model calls | session/output conditional | no spec; parser/handler must reject or request input | CLI caller | `debate.py:525-611,1026-1086` | verified |
| model list | default or explicit | yes | provider/model dispatcher | session metadata optional | use resolved default/profile selection, not no-model success | debate/provider resolver | `debate.py:757-824`, `providers.py:457-481` | verified |
| session checkpoint | conditional | yes | `SessionState` loader | JSON file | no resume state; start fresh if input permits | session module | `session.py:45-133` | verified |

## Invariants

- Gate checks run before expensive model execution; `enforce_pipeline_card_gate` is called from the top-level flow at `debate.py:1366`.
- Model credentials are validated separately from model dispatch (`debate.py:1312`); a missing credential is not a model response.
- Session persistence is JSON/file-backed and uses explicit load/save helpers (`session.py:45-133`); output text alone is not the resume contract.

## Data Flow

```text
IN: argv/stdin/spec file/profile
    └─> create_parser()/parse_models() (debate.py:525-824)
PROCESS:
    ├─> gate + credential checks
    ├─> load_or_resume_session()
    ├─> run_critique() -> call_models_parallel()
    └─> output_results()/Telegram
OUT: critique/spec/session artifacts
     └─> debate.py:1227; session.py:45-133
```

## Key Functions

| Function | Purpose | Location |
|---|---|---|
| `create_parser()` | builds CLI options and subcommands | `debate.py:525` |
| `handle_gauntlet()` | routes a parsed request to gauntlet | `debate.py:898` |
| `load_or_resume_session()` | obtains existing or new state | `debate.py:1026` |
| `run_critique()` | executes one critique round | `debate.py:1086` |
| `output_results()` | formats/persists/forwards round output | `debate.py:1227` |
| `enforce_pipeline_card_gate()` | blocks invalid pipeline invocation state | `debate.py:1366` |

## Common Patterns

- **Single CLI router:** utility commands and debate/gauntlet actions share one parser, while standalone gauntlet and gate CLIs remain separate (`debate.py:525-611`, `gauntlet/cli.py:13`).
- **Checkpointed rounds:** a completed round can be serialized and resumed rather than depending on live process memory (`session.py:45-133`).

## Error Handling

- Model/credential failures are surfaced before dispatch by `validate_models_before_run` (`debate.py:1312`).
- Pipeline-card/state failures are explicit gate exits at `debate.py:1366`.
- Session read/write errors occur at the file boundary and must not be treated as model disagreement (`session.py:45-133`).

## Concurrency Concerns

| Resource | Callers | Synchronization | Risk |
|---|---|---|---|
| session file | debate rounds/resume paths | no process-wide lock visible in `session.py:45-133` | two concurrent invocations can overwrite a checkpoint; one active CLI is assumed but not enforced here |

## Configuration

| Config | Source | Default | Precedence |
|---|---|---|---|
| model/profile/gauntlet flags | CLI | parser defaults | explicit CLI overrides profile/default |
| provider credentials | environment | unavailable | provider availability controls eligible routes |
| session path | project/user state conventions | module constants | explicit session/spec paths override |

## Integration Points

**Calls out to:**
- `models.call_models_parallel()` for parallel critique (`models.py:1114`).
- `gauntlet.run_gauntlet()` for stress testing (`gauntlet/orchestrator.py:205`).
- `session.save_checkpoint()` and Telegram send helpers for output (`session.py:45-133`, `telegram_bot.py:78`).

**Called by:**
- console entry point declared in `pyproject.toml:48`.

## Active vs Target

- **Active consumers:** CLI users, phase documents, direct tests.
- **Legacy consumers:** older scripts/docs may call `skills/.../scripts/debate.py` directly.
- **Target architecture:** retain one stable top-level CLI while moving evidence/pipeline checks behind typed contracts.
- **Drift note:** separate gauntlet CLI and root symlink/package path remain parallel surfaces.

## LLM Notes

- `debate.py` is both a debate engine and a gauntlet router; changing parser defaults can affect both paths.
- The root `adversarial_spec` import resolves through a symlink to the skill script directory; source edits belong in the canonical nested path.
