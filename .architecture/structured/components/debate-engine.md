# Component: Debate Engine

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Master CLI entrypoint + multi-round debate orchestration |
| Entry | `main()` at debate.py:1493 |
| Key files | debate.py |
| Depends on | Models, Providers, Adversaries, Prompts, Session, Gauntlet Pipeline |
| Used by | CLI users, downstream skills |
| Runtime status | implemented |
| Architecture status | active_primary |

## What This Component Does

The debate engine is the master CLI for adversarial-spec. It routes 18 different actions through argparse dispatch, orchestrates multi-round debate sessions where multiple LLMs critique a spec simultaneously, and delegates to the gauntlet pipeline for stress-testing. It manages session persistence, checkpoint saving, and user interaction for the debate loop.

## Data Flow

```
IN:  Spec text (stdin or resumed session)
     └─> main() (debate.py:1493)

PROCESS:
     ├─> create_parser() -> argparse routing
     ├─> [critique] call_models_parallel() -> aggregate -> consensus check
     ├─> [gauntlet] run_gauntlet() -> format report
     └─> save_checkpoint() + session.save()

OUT: Critique responses (stdout), checkpoints (disk)
     └─> .adversarial-spec-checkpoints/ + ~/.config/adversarial-spec/sessions/
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `main()` | CLI entry, argparse routing | debate.py:1493 |
| `run_critique()` | Multi-round debate loop | debate.py:1206 |
| `handle_gauntlet()` | Gauntlet delegation | debate.py:1018 |
| `handle_info_command()` | Query commands (providers, sessions, etc.) | debate.py:639 |
| `handle_utility_command()` | Config commands (bedrock, profiles) | debate.py:711 |
| `load_or_resume_session()` | Session load/create | debate.py:1146 |
| `handle_send_final()` | Send final spec to models | debate.py:949 |
| `handle_export_tasks()` | Export tasks from spec | debate.py:967 |

## Contracts

### Type Contracts

| Contract | Purpose | Owner | Consumed By |
|----------|---------|-------|-------------|
| `SessionState` | Debate round persistence | session.py:17 | debate.py (load/resume) |
| `ModelResponse` | Per-model critique result | models.py:142 | debate.py (aggregation) |

## Common Patterns

### Action Routing
Each action has an early-return handler. Actions are mutually exclusive — no fall-through. Info commands return before model validation, avoiding unnecessary credential checks.

### Session Lifecycle
Sessions are created on first critique, saved after each round, and resumed via `--resume {session_id}`. History accumulates per round. Path traversal protection on session_id.

## Error Handling

- **sys.exit(1)**: Generic API error, validation failure
- **sys.exit(2)**: Missing credentials or config
- **sys.exit(130)**: KeyboardInterrupt (standard UNIX signal)

## Integration Points

**Calls out to:**
- `Models.call_models_parallel()` — for parallel LLM dispatch
- `Gauntlet.run_gauntlet()` — for stress-test pipeline
- `Session.SessionState.save/load()` — for state persistence

**Called by:**
- CLI entry point (pyproject.toml `adversarial-spec` command)

## LLM Notes

- debate.py is 1500+ lines. The action routing in main() is the roadmap — read it first.
- The gauntlet flag names differ from gauntlet/cli.py (`--gauntlet-resume` vs `--resume`, `--codex-reasoning` vs `--attack-codex-reasoning`).
- `run_critique()` is the core debate loop — it's where consensus checking and user prompting happen.
