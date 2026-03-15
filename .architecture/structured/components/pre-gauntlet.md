# Component: Pre-Gauntlet

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Collect git state, system health, and build context before gauntlet |
| Entry | `PreGauntletOrchestrator.run()` at scripts/pre_gauntlet/orchestrator.py:51 |
| Key files | pre_gauntlet/orchestrator.py, collectors/, extractors/, integrations/ |
| Depends on | Git CLI, Process Runner, Pydantic |
| Used by | Debate Engine, Gauntlet |

## What This Component Does

The pre-gauntlet pipeline collects environmental context before running the adversarial gauntlet. It gathers git position (branch, commits, diff stats), system state (build status, schema files, directory trees), extracts which files are affected by the spec, and builds a markdown context document. This context helps adversaries make more targeted critiques.

## Data Flow

```
IN:  spec text + repo root + config
     └─> PreGauntletOrchestrator.run() (orchestrator.py:51)

PROCESS:
     ├─> extract_spec_affected_files() → list of relevant files
     ├─> GitPositionCollector.collect() → git branch, diff stats, concerns
     ├─> SystemStateCollector.collect() → build status, schemas, trees
     ├─> build_context() → markdown document combining all data
     └─> [interactive] run_alignment_mode() → user confirmation

OUT: PreGauntletResult
     ├── status: COMPLETE | INFRA_ERROR
     ├── context_markdown: str (enriched context for gauntlet)
     └── concerns: list (infrastructure-level concerns)
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `PreGauntletOrchestrator.run()` | Main orchestrator | orchestrator.py:51 |
| `GitPositionCollector.collect()` | Git state collection | collectors/git_position.py |
| `SystemStateCollector.collect()` | System state collection | collectors/system_state.py |
| `extract_spec_affected_files()` | File relevance analysis | extractors/spec_affected_files.py |
| `build_context()` | Markdown context assembly | pre_gauntlet/context_builder.py |
| `run_alignment_mode()` | Interactive alignment check | pre_gauntlet/alignment_mode.py |

## Common Patterns

### Config-Driven Collection

Each collection step is gated by `CompatibilityConfig` settings. Doc type rules control which collectors run (e.g., `require_git`, `require_build`, `require_schema`).

### Pydantic Models

Unlike the rest of the codebase (which uses dataclasses), pre-gauntlet uses Pydantic `BaseModel` for input validation. This is intentional — pre-gauntlet validates external data (git output, build results) where schema enforcement matters.

## Error Handling

- **Git errors**: `GitCliError` → returns `INFRA_ERROR` status (non-fatal to caller)
- **System state errors**: Caught broadly → returns `INFRA_ERROR`
- **File extraction errors**: Warning to stderr, continues with empty list
- **All errors are non-fatal**: Callers can proceed without pre-gauntlet context

## Integration Points

**Calls out to:**
- `GitCli` (integrations/git_cli.py) — read-only git commands via subprocess
- `ProcessRunner` (integrations/process_runner.py) — build command execution
- File system reads for schemas and directory trees

**Called by:**
- `debate.py` — before gauntlet runs
- `gauntlet.py` — standalone gauntlet mode

## LLM Notes

- The pre-gauntlet pipeline is completely optional. The debate engine works without it.
- `CompatibilityConfig` is the control surface — modify it to change what gets collected.
- `integrations/knowledge_service.py` exists but is not wired into the main flow yet.
- The `scripts/scripts/` stale copy also has pre_gauntlet files — always use `scripts/pre_gauntlet/`.
