# Component: Debate Session Persistence

> Derived from: `skills/adversarial-spec/scripts/session.py`, `debate.py` | Verified at: `ef18c66`
> If any derived-from file changed since `ef18c66`, trust source over this doc.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Save/load resumable debate state and checkpoint metadata |
| Entry | `SessionState` at `session.py:17` |
| Key files | `session.py`, `debate.py` |
| Depends on | JSON/pathlib, project/session state paths |
| Used by | Debate Engine |
| Runtime status | implemented |
| Architecture status | active_secondary |

## What This Component Does

Session persistence captures debate document, round context, model outputs, and continuation metadata so later invocations can resume without reconstructing state from transcript text.

## Contracts

| Contract | Purpose | Owner | Consumed By |
|---|---|---|---|
| `SessionState` | in-memory serialized state | `session.py:17` | debate load/save |
| session JSON | durable checkpoint | `session.py:42-133` | resume paths |

## Invariants

- Save/load use the same JSON shape; partial state remains distinguishable from a completed round (`session.py:42-133`).
- Session IDs are path-validated before file access (`session.py` path checks).

## Data Flow

```text
IN: debate round state
PROCESS: dataclass/asdict -> JSON write -> JSON load
OUT: SessionState for next invocation
```

## Key Functions

| Function | Purpose | Location |
|---|---|---|
| `SessionState.save()` | persist state | `session.py:42` |
| `SessionState.load()` | load state | `session.py` |
| `save_checkpoint()` | write round checkpoint | `session.py:74` |
| `save_critique_responses()` | preserve raw responses | `session.py:85` |

## Error Handling

- Missing/corrupt JSON is a resume error; caller decides whether to start fresh.
- Path traversal is rejected before read/write.

## Concurrency Concerns

| Resource | Callers | Synchronization | Risk |
|---|---|---|---|
| HAZ-002: session JSON/checkpoints | concurrent debate invocations and resume writes | no FileLock or atomic replacement visible | last writer can replace another round's state or expose partial JSON |

## Configuration

| Config | Source | Default | Precedence |
|---|---|---|---|
| session root | module/path conventions | project/user state | explicit session path |

## Integration Points

**Calls out to:** filesystem JSON.

**Called by:** Debate Engine load/resume/output paths.

## Active vs Target

- **Active consumers:** debate CLI.
- **Target architecture:** converge session and gauntlet persistence on shared atomic/lock policy where concurrent use is supported.

## LLM Notes

- Do not infer consensus from a checkpoint’s existence; inspect round/status fields.
