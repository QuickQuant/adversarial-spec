# Component: Validation Emission and Evidence Ledger

> Derived from: `skills/adversarial-spec/scripts/validation_emission.py`, `tmr_schema.py`, `telegram_bot.py` | Verified at: `ef18c66`
> If any derived-from file changed since `ef18c66`, trust source over this doc.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Normalize validation rows, manage evidence batches, parse replies, and emit stable CLI envelopes |
| Entry | `main()` at `validation_emission.py:3423` |
| Key files | `validation_emission.py`, TMR schema, Telegram helper |
| Depends on | FileLock, subprocess, JSON/hashlib, Telegram API |
| Used by | validation workflow, Phase 8/promotion, tests |
| Runtime status | implemented |
| Architecture status | active_primary |

## What This Component Does

Validation emission is a standalone, bounded CLI around a file-backed ledger. It derives canonical row/story/conops hashes, applies state transitions under a lock, assembles bounded Telegram digests, parses replies idempotently, records system-validation evidence, and emits one JSON envelope for every handled invocation.

## Contracts

### Boundary Field Contracts

Chain: command handler → `_emit` → caller.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `status` | always | yes | `ok`/`issues`/`reprompt`/`error` | no | malformed/no envelope; no success inference | handler | `validation_emission.py:51-67,200-220,3418-3428` | verified |
| `code` | conditional/nullable | yes | issue/error code or null | no | no detailed reason; inspect `issues` | handler | `validation_emission.py:194-220,3423-3460` | verified |
| `issues` | always structurally | yes | list of issue mappings | ledger-specific issue may be persisted separately | empty issue list; status still controls result | handler | `validation_emission.py:194-220` | verified |
| `data` | always structurally, command-dependent | yes | mapping | command-specific | no data payload; caller follows status/code | handler | `validation_emission.py:200-220,2888-2908` | verified |

### File/state contracts

| Surface | Kind | Key fields/operations | Access boundary |
|---|---|---|---|
| validation ledger | JSON file | rows, batches, hashes, evidence | FileLock at `validation_emission.py:959-1048` |
| evidence artifact | JSON/Markdown | row/story refs, result, environment | bounded path under spec root |
| reply batch | JSON state | assembled/sent/processed/reset states | ledger writer |

## Invariants

- All normal command exits use `_emit` so stdout remains one JSON object (`validation_emission.py:3418-3460`).
- Input paths resolve under a spec root (`validation_emission.py:312`); oversized or secret-bearing payloads are rejected before mutation.
- Ledger mutation uses a lock and atomic replacement (`validation_emission.py:959-1065,1337`).
- Hash fields bind rows, stories, conops, and artifacts; stale replies cannot silently update a changed row (`validation_emission.py:397-457,2145-2348`).

## Data Flow

```text
IN: argv + ledger/reply/artifact paths
PROCESS: bounds -> normalize/hash -> lock/mutate -> digest/reply/system validation
OUT: ledger/evidence files + Envelope stdout
```

## Key Functions

| Function | Purpose | Location |
|---|---|---|
| `handle_normalize_rows()` | canonicalize/lint rows | `validation_emission.py:1093` |
| `mutate_ledger()` | locked ledger transition | `validation_emission.py:1337` |
| `handle_assemble_digest()` | bounded digest creation | `validation_emission.py:1528` |
| `handle_record_send()` | batch send state | `validation_emission.py:1757` |
| `handle_parse_reply()` | idempotent reply parsing | `validation_emission.py:2348` |
| `emit_system_validation()` | record validation evidence | `validation_emission.py:2606` |
| `handle_self_check()`/`handle_status()` | integrity/closure checks | `validation_emission.py:2888,3102` |

## Error Handling

- `ValidationIssuesError` emits `issues`; `LedgerBusyError` and corruption emit `error` with stable codes (`validation_emission.py:3423-3460`).
- Unexpected exceptions are written to stderr while stdout remains an error Envelope.
- Missing/invalid paths, hashes, duplicate rows, stale batches, and secret patterns have explicit issue codes.

## Concurrency Concerns

| Resource | Callers | Synchronization | Risk |
|---|---|---|---|
| ledger/batch state | normalize, send, reply, status commands | FileLock with owner diagnostics | guarded; lock timeout is a surfaced error |

## Configuration

| Config | Source | Default | Precedence |
|---|---|---|---|
| size/lock bounds | module constants `validation_emission.py:264-286,959` | fixed limits | code constants |
| spec root | manifest/path arguments | current spec context | explicit path is validated under root |
| Telegram sender allowlist | registry path/env-derived configuration | none | explicit registry controls accepted senders |

## Integration Points

**Calls out to:** Telegram API/reply artifacts, subprocess validation commands, TMR/provenance records.

**Called by:** direct CLI users, Phase 8 evidence flow, tests.

## Active vs Target

- **Active consumers:** validation-leg workflow and dogfood/test fixtures.
- **Target architecture:** keep the Envelope and ledger as the canonical machine boundary instead of ad hoc JSON outputs.

## LLM Notes

- A `status=ok` envelope with empty `data` is valid for commands that only mutate/check state; callers must use command semantics and issue codes, not truthiness of `data`.
