# Component: Token Tracking

> Derived from: `skills/adversarial-spec/scripts/token_tracking.py`, `providers.py`, `models.py` | Verified at: `ef18c66`
> If any derived-from file changed since `ef18c66`, trust source over this doc.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Thread-safe token and cost aggregation across model workers |
| Entry | `TokenTracker` at `token_tracking.py:19` |
| Key files | `token_tracking.py`, `providers.py` |
| Depends on | model cost tables, threading |
| Used by | model dispatch/output/reporting |
| Runtime status | implemented |
| Architecture status | active_primary |

## Contracts

| Field | Emitted | Consumer accepts | Persist | Absent means | Evidence | Verified |
|---|---|---|---|---|---|---|
| input/output tokens | provider-dependent | optional numeric usage | run/output conditional | unknown/zero usage; not billing proof | `token_tracking.py:19-70`, `models.py:141-151` | verified |
| cost | derived from usage + provider rates | numeric reporting | output/run conditional | cost cannot be calculated | `providers.py:26-69` | verified |

## Invariants

- All shared counter updates hold the tracker lock (`token_tracking.py:19-70`).
- Provider rates are read from one shared cost table with fallback default (`providers.py:26-69`).

## Data Flow

```text
IN: ModelResponse usage/provider model
PROCESS: lock -> aggregate counts -> cost lookup
OUT: totals for CLI/run report
```

## Integration Points

**Called by:** parallel model workers and output/reporting paths.

## Concurrency Concerns

| Resource | Callers | Synchronization | Risk |
|---|---|---|---|
| process-wide totals | model worker threads | `threading.Lock` | guarded; reset/lifecycle semantics must remain explicit |

## Active vs Target

- **Active consumers:** top-level and gauntlet model paths.
- **Target architecture:** keep cost/token accounting behind one provider-neutral wrapper.

## LLM Notes

- Zero tokens from CLI routes is intentional and does not mean the call did not execute.
