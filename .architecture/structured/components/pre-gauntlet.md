# Component: Pre-Gauntlet

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Git/system context collection before gauntlet runs |
| Entry | `run_pre_gauntlet()` at pre_gauntlet/orchestrator.py:207 |
| Key files | pre_gauntlet/orchestrator.py, pre_gauntlet/models.py, collectors/git_position.py, collectors/system_state.py, pre_gauntlet/context_builder.py |
| Depends on | integrations/git_cli.py, integrations/process_runner.py |
| Used by | Gauntlet Pipeline (via gauntlet/cli.py) |
| Runtime status | implemented |
| Architecture status | active_primary |

## What This Component Does

Collects environmental context before gauntlet runs: git position (branch, commits, staleness), system state (build status, schemas, directory trees), and spec-affected files. Assembles this into a markdown context document that enhances the spec for adversary evaluation. Includes an interactive alignment mode where users can validate/reject collected context.

## Data Flow

```
IN:  Spec text + repo root + config
     └─> PreGauntletOrchestrator.run() (pre_gauntlet/orchestrator.py:51)

PROCESS:
     ├─> extract_spec_affected_files() -> file list
     ├─> GitPositionCollector.collect() -> git position + concerns
     ├─> SystemStateCollector.collect() -> system state + concerns
     ├─> build_context() -> assembled markdown (max 200k chars)
     └─> [optional] run_alignment_mode() -> user validation

OUT: PreGauntletResult (context_markdown, concerns, timings)
     └─> consumed by gauntlet pipeline
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `run_pre_gauntlet()` | Public API entry point | pre_gauntlet/orchestrator.py:207 |
| `PreGauntletOrchestrator.run()` | Class-based orchestrator | pre_gauntlet/orchestrator.py:51 |
| `GitPositionCollector.collect()` | Git branch/commit info | collectors/git_position.py |
| `SystemStateCollector.collect()` | Build status, schemas | collectors/system_state.py |
| `build_context()` | Assemble markdown context | pre_gauntlet/context_builder.py |
| `run_alignment_mode()` | Interactive user validation | pre_gauntlet/alignment_mode.py |

## Contracts

### Type Contracts

| Contract | Purpose | Owner | Consumed By |
|----------|---------|-------|-------------|
| `PreGauntletResult` | Collection result container | pre_gauntlet/__init__.py | gauntlet/cli.py |
| `GitPosition` | Git repo state (Pydantic BaseModel) | pre_gauntlet/models.py:178 | context_builder |
| `SystemState` | System environment state (Pydantic) | pre_gauntlet/models.py:230 | context_builder |
| `Concern` (pre-gauntlet) | System/build concern | pre_gauntlet/models.py:257 | alignment_mode |

## Error Handling

- **GitCliError**: Caught, returns INFRA_ERROR status. Pipeline continues with empty git context.
- **SystemState collection failure**: Caught, returns INFRA_ERROR. Pipeline continues with empty system context.
- **All collectors are read-only**: No modifications to repo or system state.

## LLM Notes

- Pre-gauntlet Concern is a different type from gauntlet/core_types.Concern. Don't confuse them.
- Pydantic is used here but not in pyproject.toml (implicit dependency).
- knowledge_service.py in integrations/ is implemented but not wired into any flow.
