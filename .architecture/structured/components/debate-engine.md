# Component: Debate Engine

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Orchestrates multi-model spec critique rounds until consensus |
| Entry | `main()` at scripts/debate.py:1933 |
| Key files | debate.py, session.py |
| Depends on | Models, Providers, Prompts, Gauntlet, Session, TaskManager (optional), Telegram (optional), ExecutionPlanner (optional) |
| Used by | CLI invocation, Claude Code skill |

## What This Component Does

The debate engine is the primary user-facing entry point. It takes a draft specification, sends it to multiple LLM models for critique, collects their responses, checks for consensus (all models agree), and either outputs the result or feeds the revised spec back for another round. It manages 18 different CLI actions through a single `main()` function that routes to specialized handlers.

## Data Flow

```
IN:  spec text (stdin or --spec-file)
     + CLI arguments (models, focus, persona, doc_type)
     └─> main() (debate.py:1933)

PROCESS:
     ├─> parse arguments and apply profile
     ├─> validate model credentials
     ├─> load or resume session
     ├─> call_models_parallel() for each round
     ├─> check agreement, update session
     └─> output results (JSON/text/telegram)

OUT: JSON output to stdout
     + session file (sessions/{id}.json)
     + checkpoint (checkpoints/round-N.md)
     └─> debate.py:output_results()
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `main()` | CLI entry, argument parsing, action routing | debate.py:1933 |
| `run_critique()` | Main debate loop — calls models, checks agreement | debate.py:1689 |
| `handle_info_command()` | Lists providers, focus areas, personas, sessions | debate.py:607 |
| `handle_utility_command()` | Bedrock setup, profile save, diff generation | debate.py:675 |
| `handle_execution_plan()` | Runs full execution planning pipeline | debate.py:724 |
| `handle_gauntlet()` | Invokes adversarial gauntlet | debate.py:1553 |
| `handle_send_final()` | Sends final spec to Telegram | debate.py:1484 |
| `handle_export_tasks()` | Extracts tasks via LLM | debate.py:1502 |
| `load_or_resume_session()` | Creates new or resumes existing session | debate.py:1630 |
| `output_results()` | Formats and prints round results | debate.py:1803 |
| `send_telegram_notification()` | Sends round results to Telegram, polls for reply | debate.py:182 |

## Common Patterns

### Action Routing

`main()` uses a series of conditional checks on `args.action` to dispatch to handlers. Info commands and utility commands are checked first (early return), then gauntlet and execution plan, with critique as the default.

### Optional Feature Loading

Telegram, task tracking, and execution planner are all lazy-loaded with try/except ImportError guards. This keeps the core debate loop functional without optional dependencies.

## Error Handling

- **Model call failures**: Handled in models.py with retries. Debate engine filters out error responses and continues with successful ones.
- **Session corruption**: Session load validates JSON structure. Corrupt sessions are logged and skipped.
- **Missing API keys**: `validate_models_before_run()` checks credentials before starting. Exits with clear error message if keys missing.

## Configuration

| Config | Source | Default |
|--------|--------|---------|
| Models | `--models` CLI or profile | First available provider |
| Doc type | `--doc-type` CLI | `spec` |
| Focus | `--focus` CLI or profile | None (general critique) |
| Persona | `--persona` CLI or profile | None (default reviewer) |
| Rounds | `--rounds` CLI | 1 |
| Telegram | `--telegram --poll-timeout` | Disabled |
| Task tracking | `--track-tasks` | Disabled |

## Integration Points

**Calls out to:**
- `Models.call_models_parallel()` — for LLM critique calls
- `Gauntlet.run_gauntlet()` — for adversarial review
- `Session.save()/load()` — for state persistence
- `ExecutionPlanner.*` — for spec-to-task conversion (optional)
- `Telegram.send_telegram_notification()` — for async feedback (optional)
- `TaskManager` — for MCP task tracking (optional)

**Called by:**
- CLI invocation by user or Claude Code skill

## LLM Notes

- debate.py is ~2000 lines. Read specific sections rather than the whole file.
- The 18 action handlers are NOT separate subcommands — they're dispatched by `if/elif` chains in `main()`.
- `run_critique()` is the heart of the debate loop. Everything else is setup or utility.
- The `EXECUTION_PLANNER_AVAILABLE` flag at module level controls whether execution plan features are accessible.
