# Component: Harness Hooks

> Derived from: `.claude/settings.json`, `.claude/hooks/` | Verified at: `2433efa`
> If a derived-from file changed since `2433efa`, trust source over this document.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Enforce tool policy and emit non-authoritative activity/notification side effects. |
| Entry | registered commands in `.claude/settings.json:3` |
| Key files | `fizzy_payload_guard.py`, `pipeline_notifications.py`, `session_activity_logger.py`, command guards |
| Depends on | hook stdin JSON and local filesystem/config |
| Used by | Claude/Codex tool lifecycle |
| Runtime / architecture | implemented / active_primary |

## Contracts

### Boundary Field Contracts

Hook host -> Fizzy guard -> hook decision.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `tool_name` | host-dependent | yes | selects applicable rule | ignored | no named rule; allow | producer | `fizzy_payload_guard.py:88,92,109,120` | verified |
| `tool_input` | host-dependent | yes | guard args default `{}` | ignored | no scope/caller/metadata | producer | `fizzy_payload_guard.py:93,110,127` | verified |
| override metadata | conditional | yes | intent + fresh note required | derived | override unavailable | producer | `fizzy_payload_guard.py:60-70,102` | verified |
| `decision`, `reason` | denial-only | n/a | hook host consumes block object | ignored | no decision permits action | adapter | `fizzy_payload_guard.py:51-53,147` | verified |

### Activity-log Boundary

`session_activity_logger.py:55-96` appends `{ts,session_id,event,project}` for every accepted entry. Empty session/event/root prevents a line; `source`/`model` are SessionStart-only and `reason` SessionEnd-only.

## Invariants

- Invalid hook JSON exits without side effect rather than throwing into the host (`fizzy_payload_guard.py:86-91`).
- A notification/dispatch is not proof of a successful workflow transition; it is a post-tool side effect (`pipeline_notifications.py:392-437`).
- Activity logger failures are deliberately non-blocking (`session_activity_logger.py:92-97`).

## Data Flow

`hook stdin JSON -> guard or event normalization -> block JSON / JSONL dispatch/activity / optional notification`.

## Key Functions

| Function | Purpose | Location |
|---|---|---|
| `fizzy_payload_guard.main()` | scoped pre-tool block/allow | `fizzy_payload_guard.py:86` |
| `pipeline_notifications.main()` | extract tool event/notify | `pipeline_notifications.py:392` |
| `session_activity_logger.main()` | append bounded activity JSONL | `session_activity_logger.py:55` |
| `_resolve_config.resolve_config()` | hook config precedence | `_resolve_config.py:39` |

## Concurrency Concerns

| Resource | Callers | Synchronization | Risk |
|---|---|---|---|
| idle counter keyed only project/role | same-role worker hooks | none | cross-session backoff interference |
| dispatch JSONL | completion/review hooks | append only/no event dedupe | replay/duplicate messages |

## LLM Notes

- The external hook host’s interpretation of a block decision is outside this repository; this corpus maps emitted protocol fields, not host implementation.
