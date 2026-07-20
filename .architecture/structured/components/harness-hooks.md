# Component: Harness Hooks

> Derived from: `.claude/hooks/*.py`, `.claude/hooks/hook_config.json`, `.claude/settings.json` | Verified at: `ef18c66`
> If any derived-from file changed since `ef18c66`, trust source over this doc.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Enforce command/Fizzy safety and coordinate Claude Code pipeline workers |
| Entry | `codex_pretool_combined.main()` at `.claude/hooks/codex_pretool_combined.py:57` |
| Key files | combined safety hook, `fizzy_payload_guard.py`, pipeline hooks, command guards |
| Depends on | Claude Code hook protocol, local config, optional Telegram/Fizzy metadata |
| Used by | Claude Code tool lifecycle and pipeline workers |
| Runtime status | implemented |
| Architecture status | active_primary |

## Contracts

### Boundary Field Contracts

Chain: Claude Code event stdin → hook classifier(s) → stdout/exit protocol.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `decision` | only block-capable hook emits JSON | yes; allow is exit 0/no output | Claude Code hook protocol | no | allow/no-op for combined safety path; not a card transition | hook protocol | `codex_pretool_combined.py:26-72`, `fizzy_payload_guard.py:51-86` | verified |
| `reason` | with block decision | yes | hook protocol | no | no diagnostic reason | sub-hook | `fizzy_payload_guard.py:51-60,105-149` | verified |
| `systemMessage` | conditional after pipeline result/idle | direct | Claude Code operator/worker message | transient | no message; hook may still log/act | pipeline hook | `pipeline_continue.py:70-121`, `pipeline_idle_retry.py:130-159` | verified |

## Invariants

- Combined safety hooks run in order and stop on first non-zero exit (`codex_pretool_combined.py:18-72`).
- Hook input is consumed once; combined adapter replays serialized input into each sub-hook (`codex_pretool_combined.py:26-47`).
- Hook safety modules do not import runtime skill code; they communicate via JSON/stdout and local side effects.
- Fizzy payload overrides require a long intent plus a fresh process-failure file (`fizzy_payload_guard.py:60-84`).

## Data Flow

```text
IN: Claude Code tool event JSON
PROCESS: safety classifier -> role/event classifier -> optional notification/logging
OUT: block/warn/allow exit or systemMessage JSON
```

## Key Functions

| Function | Purpose | Location |
|---|---|---|
| `load_and_run()` | replay event into sub-hook | `codex_pretool_combined.py:26` |
| `fizzy_payload_guard.main()` | bounded MCP/payload gate | `fizzy_payload_guard.py:86` |
| `dispatch_check.main()` | role/dispatch check | `dispatch_check.py:86` |
| `pipeline_continue.main()` | continuation injection | `pipeline_continue.py:70` |
| `pipeline_idle_retry.main()` | backoff/status instruction | `pipeline_idle_retry.py:73` |
| `pipeline_notifications.main()` | completion/review notification | `pipeline_notifications.py:392` |

## Error Handling

- Malformed hook JSON fails open for some safety sub-hooks and emits `{}` for coordination hooks; each hook must be evaluated according to its registration contract.
- Safety guard violations are printed as structured decisions and exit without raising into the caller.
- Notification failures are side-effect failures, not proof of card-state failure.

## Concurrency Concerns

| Resource | Callers | Synchronization | Risk |
|---|---|---|---|
| dispatch/activity JSONL | multiple hook invocations | append-only file writes; no global lock visible | interleaved records or duplicate notifications under concurrent events |
| Telegram notification | completion/review hook events | no shared lock | duplicate or out-of-order operator messages |

## Configuration

| Config | Source | Default | Precedence |
|---|---|---|---|
| hook registration | Claude settings/hook config | registered hooks | settings determine whether module runs |
| role | registration/input/env | `codex` fallback | registration → project env → fallback (`pipeline_continue.py:25-68`) |
| Fizzy override | metadata or env + fresh process-failure path | denied | valid override conditions required |

## Integration Points

**Calls out to:** Claude Code protocol, local `.conductor`/`.adversarial-spec` files, optional Telegram/Fizzy metadata.

**Called by:** Claude Code hook runner.

## Active vs Target

- **Active consumers:** current Claude Code sessions and pipeline workers.
- **Target architecture:** hooks remain a thin protocol/safety layer; authoritative state remains on the board/filesystem.

## LLM Notes

- A `systemMessage` tells a worker what to do next but does not establish that the requested pipeline operation succeeded; verify live board state separately.
