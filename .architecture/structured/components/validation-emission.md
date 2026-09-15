# Component: Validation Emission

> Derived from: `skills/adversarial-spec/scripts/validation_emission.py`, `skills/adversarial-spec/phases/07-execution.md` | Verified at: `2433efa`
> If a derived-from file changed since `2433efa`, trust source over this document.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Manage ConOps, validation rows, evidence, digest judgments and close artifacts. |
| Entry | `main()` at `validation_emission.py:3423` |
| Depends on | FileLock, JSON/artifact paths, Git metadata |
| Used by | execution/conductor close workflow |
| Runtime / architecture | implemented / active_primary |

## Contracts

### Boundary Field Contracts

`main()` -> `Envelope.as_dict()` -> `_emit()` -> execution conductor/stdout.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `status` | always | yes | advance only `ok` + zero issues | ignored | invalid discriminator | producer | `validation_emission.py:203,209,217`, `07-execution.md:937` | verified |
| `code` | always | yes | remediation code | ignored | null means no stable code | producer | `validation_emission.py:204,211`, `07-execution.md:899` | verified |
| `issues[]` | always | yes | success requires empty | ignored | no reported issue | producer | `validation_emission.py:194,205,212` | verified |
| `data` | always | yes | subcommand result shape | ignored | no extra payload | producer | `validation_emission.py:206,213`, `07-execution.md:918` | verified |

### Data Model Surface

| Surface | Kind | Key Operations | Access Boundary |
|---|---|---|---|
| validation ledger | JSON artifact | normalize, evidence, digest, judge, supersede, status | workspace-root containment |
| ConOps | Markdown/hash artifact | derive and bind story hashes | overwrite guard |
| system validation | JSON artifact | emit/self-check | reject symlinked inputs |

## Invariants

- `mutate_ledger()` is the only ledger mutation path and locks + atomically replaces output (`validation_emission.py:1337-1372`).
- Corrupt ledger bytes are quarantined rather than silently repaired (`validation_emission.py:1019-1037`).
- Reply judgment validates sender from raw update and applies the batch all-or-nothing (`validation_emission.py:2348-2552`).
- Close requires active-story coverage and valid evidence/provenance (`validation_emission.py:2606-3036`).

## Data Flow

`roadmap manifest -> ConOps/hash -> rows/evidence ledger -> bounded digest -> human reply -> system-validation artifact -> Envelope`.

## Key Functions

| Function | Purpose | Location |
|---|---|---|
| `handle_derive_conops()` | derive bounded/hash-bound ConOps | `validation_emission.py:688` |
| `handle_normalize_rows()` | validate/stamp canonical rows | `validation_emission.py:1093` |
| `handle_parse_reply()` | authenticate and apply judgments | `validation_emission.py:2348` |
| `emit_system_validation()` | construct close artifact | `validation_emission.py:2606` |
| `handle_self_check()` | verify output integrity | `validation_emission.py:2888` |

## Concurrency Concerns

| Resource | Callers | Synchronization | Risk |
|---|---|---|---|
| validation ledger | mutating subcommands | FileLock / atomic replace | busy failures are explicit, not torn JSON |

## LLM Notes

- `status` alone does not mean success: consumers must interpret `issues` and the process exit mapping too.
