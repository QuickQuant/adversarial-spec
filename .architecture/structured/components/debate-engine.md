# Component: Debate Engine

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Orchestrates multi-model spec critique rounds until consensus |
| Entry | `main()` at scripts/debate.py:1443 |
| Key files | debate.py (1485 lines), session.py |
| Depends on | Models, Providers, Prompts, Gauntlet, Session, TaskManager (optional), Telegram (optional) |
| Used by | CLI invocation, Claude Code skill |

## What This Component Does

The debate engine is the primary user-facing entry point. It takes a draft specification, sends it to multiple LLM models for critique, collects their responses, checks for consensus (all models agree via `[AGREE]` marker), and outputs the result. It manages CLI actions through a single `main()` function that routes to specialized handlers. Each invocation is one round — the user decides whether to iterate.

## Data Flow

```
IN:  spec text (stdin or --spec-file)
     + CLI arguments (models, focus, persona, doc_type)
     └─> main() (debate.py:1443)

PROCESS:
     ├─> parse arguments and apply profile
     ├─> validate model credentials
     ├─> load or resume session
     ├─> call_models_parallel() for the round
     ├─> check agreement, update session
     ├─> save checkpoint + critique responses
     └─> output results (JSON/text/telegram)

OUT: JSON output to stdout
     + session file (sessions/{id}.json)
     + checkpoint (checkpoints/round-N.md)
     + critiques (checkpoints/round-N-critiques.json)
     └─> debate.py:output_results()
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `main()` | CLI entry, argument parsing, action routing | debate.py:1443 |
| `run_critique()` | Core debate round — calls models, checks agreement | debate.py:1156 |
| `handle_info_command()` | Lists providers, focus areas, personas, sessions, adversaries | debate.py:610 |
| `handle_utility_command()` | Bedrock setup, profile save | debate.py:682 |
| `handle_gauntlet()` | Invokes adversarial gauntlet | debate.py:989 |
| `handle_send_final()` | Sends final spec to models | debate.py:920 |
| `handle_export_tasks()` | Extracts tasks via LLM | debate.py:938 |
| `output_results()` | Formats and prints round results | debate.py |
| `send_telegram_notification()` | Sends results to Telegram, polls for reply | debate.py:185 |

## Common Patterns

### Action Routing

`main()` uses a series of conditional checks on `args.action` to dispatch to handlers. Info commands and utility commands are checked first (early return), then gauntlet and execution plan, with critique as the default.

### Optional Feature Loading

Telegram, task tracking, and execution planner are all lazy-loaded with try/except ImportError guards. This keeps the core debate loop functional without optional dependencies.

### Input Stats Logging

`log_input_stats()` at debate.py:114 computes line count and SHA256 hash of input spec to detect if compression/summarization has altered the spec between rounds.

## Error Handling

- **Model call failures**: Handled in models.py with retries. Debate engine filters out error responses and continues with successful ones.
- **Missing API keys**: `validate_models_before_run()` checks credentials before starting. Exits with code 2 if keys missing.
- **Missing stdin**: Exits with code 1 if no spec provided.
- **Session corruption**: Session load validates JSON structure. Corrupt sessions logged and skipped.

## Configuration

| Config | Source | Default |
|--------|--------|---------|
| Models | `--models` CLI or profile | First available provider |
| Doc type | `--doc-type` CLI | `spec` |
| Focus | `--focus` CLI or profile | None (general critique) |
| Persona | `--persona` CLI or profile | None (default reviewer) |
| Telegram | `--telegram --poll-timeout` | Disabled |

## Integration Points

**Calls out to:**
- `Models.call_models_parallel()` — for LLM critique calls
- `Gauntlet.run_gauntlet()` — for adversarial review
- `Session.save()/load()` — for state persistence
- `Telegram.send_telegram_notification()` — for async feedback (optional)
- `TaskManager` — for MCP task tracking (optional, lazy-loaded)

**Called by:**
- CLI invocation by user or Claude Code skill

## LLM Notes

- debate.py is ~1485 lines. Read specific sections rather than the whole file.
- The action handlers are NOT separate subcommands — they're dispatched by `if/elif` chains in `main()`.
- `run_critique()` at line 1156 is the heart of the debate loop. Everything else is setup or utility.
- No signal handlers for SIGTERM/SIGINT — relies on subprocess handling.
- `LITELLM_LOG` is force-set to ERROR at line 65.
