# Component: Session

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Debate state persistence for multi-round resume |
| Entry | `SessionState` at session.py:17 |
| Key files | session.py |
| Depends on | None (uses stdlib only) |
| Used by | Debate Engine |
| Runtime status | implemented |
| Architecture status | active_primary |

## What This Component Does

Manages debate session state across rounds. `SessionState` is a dataclass storing the spec, round number, model list, focus/persona settings, and debate history. Sessions persist to `~/.config/adversarial-spec/sessions/{session_id}.json` and can be resumed with `--resume {session_id}`. Includes path traversal protection on session_id validation.

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `SessionState` | Debate state dataclass | session.py:17 |
| `SessionState.save()` | Persist to JSON file | session.py:42 |
| `SessionState.load()` | Load from JSON file | session.py |
| `SessionState.list_sessions()` | Glob all sessions | session.py |
| `save_checkpoint()` | Save round checkpoint markdown | session.py:74 |
| `save_critique_responses()` | Save raw model responses JSON | session.py:85 |

## Contracts

### Type Contracts

| Contract | Purpose | Owner | Consumed By |
|----------|---------|-------|-------------|
| `SessionState` | Debate round state | session.py:17 | debate.py |

## Error Handling

- **FileNotFoundError**: Raised on load() when session doesn't exist. Fatal — caught by debate.py.
- **Path traversal**: is_relative_to() check prevents arbitrary file reads/writes via crafted session_id.

## Concurrency Concerns

| Resource | Callers | Synchronization | Risk |
|----------|---------|-----------------|------|
| Session file | run_critique() saves per round | None | Low — single-user assumption |

## LLM Notes

- No file locking on session files. Single-user assumption. Two concurrent debates on the same session could corrupt state.
- Path safety check (`is_relative_to()`) is repeated 4 times with identical code — known pattern debt.
