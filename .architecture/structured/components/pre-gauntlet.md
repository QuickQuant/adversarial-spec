# Component: Pre-Gauntlet Grounding

> Derived from: `skills/adversarial-spec/scripts/pre_gauntlet/`, `collectors/`, `extractors/`, `integrations/` | Verified at: `2433efa`
> If a derived-from file changed since `2433efa`, trust source over this document.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Ground a spec in repository state and force alignment when blockers exist. |
| Entry | `PreGauntletOrchestrator.run()` at `pre_gauntlet/orchestrator.py:85` |
| Depends on | extractors, Git/system collectors, bounded process runner |
| Used by | standalone gauntlet `--pre-gauntlet` path |
| Runtime / architecture | implemented / active_primary |

## Contracts

### Type Contracts

| Contract | Purpose | Owner | Consumed By |
|---|---|---|
| `PreGauntletResult` | status, concerns, bounded context | `pre_gauntlet/models.py` | CLI/orchestrator |
| compatibility config | target-repo policy | `pre_gauntlet/orchestrator.py:237-290` | collectors/alignment |

## Invariants

- Disabled document types return COMPLETE with the original spec (`orchestrator.py:67-80`).
- Noninteractive blockers return `NEEDS_ALIGNMENT`; they do not silently continue (`alignment_mode.py:60-177`).
- Process execution is array-only, validated, redacted and output-bounded (`integrations/process_runner.py:56-115`).

## Data Flow

`spec + target repo -> affected files/git/system/schema observations -> bounded context -> alignment status -> gauntlet input`.

## Key Functions

| Function | Purpose | Location |
|---|---|---|
| `PreGauntletOrchestrator.run()` | collect/build/align | `orchestrator.py:85` |
| `build_context()` | bounded Markdown renderer | `context_builder.py:213` |
| `run_alignment_mode()` | interactive/noninteractive decision | `alignment_mode.py:60` |

## Error Handling

- Infra errors produce `INFRA_ERROR`; abort/EOF/interrupt produces `ABORTED`; caller maps status to exit behavior (`orchestrator.py:309-325`).

## LLM Notes

- This component reads the *consumer repository’s* compatibility TOML, not this project’s root policy. Changing defaults changes behavior across repositories.
