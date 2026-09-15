# Component: Gauntlet Persistence

> Derived from: `skills/adversarial-spec/scripts/gauntlet/persistence.py`, `gauntlet/orchestrator.py` | Verified at: `2433efa`
> If a derived-from file changed since `2433efa`, trust source over this document.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Persist gauntlet checkpoints, run records, stats and resolved-concern state safely. |
| Entry | `save_checkpoint()` at `gauntlet/persistence.py:560` |
| Depends on | FileLock, core types, filesystem |
| Used by | orchestrator and gauntlet phases |
| Runtime / architecture | implemented / active_primary |

## Contracts

### Boundary Field Contracts

Checkpoint chain: orchestrator -> `save_checkpoint()` -> `_write_json_atomic()` -> `_load_checkpoint_envelope()`.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `_meta` | always | yes | metadata dict required | required | checkpoint ignored | producer | `persistence.py:571,579,296` | verified |
| schema/spec/config hashes | always | yes | exact expected values | required | no unsafe resume | producer | `persistence.py:572-574,308-318` | verified |
| `data_hash` | always | yes | recomputed when truthy | required | legacy-like skip of integrity check | adapter | `persistence.py:106,577,320` | verified |
| `data` | always | yes | phase-specific payload | required | checkpoint ignored | producer | `persistence.py:581,325,712` | verified |

## Invariants

- Writes use a sidecar lock, same-directory temp file, fsync and replace (`persistence.py:74-152`).
- Resume rejects wrong schema/spec/config and hash-mismatched data (`persistence.py:281-325`).
- Path keys resolve to known checkpoint destinations, not arbitrary traversal paths (`persistence.py:171-184`).

## Data Flow

`phase data -> dataclass serialization -> metadata/hash envelope -> atomic locked JSON -> compatibility loader -> phase data`.

## Key Functions

| Function | Purpose | Location |
|---|---|---|
| `_write_json_atomic()` | file-level atomic writer | `persistence.py:124` |
| `save_checkpoint()` | construct envelope | `persistence.py:560` |
| `_load_checkpoint_envelope()` | validate/recover payload | `persistence.py:281` |
| `update_run_manifest()` | phase status/metrics | `persistence.py:629` |

## Concurrency Concerns

| Resource | Callers | Synchronization | Risk |
|---|---|---|---|
| run manifest | phase/terminal updates | lock only per read/write, not transaction | lost phase/metric update |
| resolved concern count | parallel filtering calls | lock not across read-modify-write | undercount |

## LLM Notes

- File atomicity does not create a transaction across multiple sidecars or across a read-modify-write sequence.
