# Component: Gauntlet Persistence and Resume

> Derived from: `skills/adversarial-spec/scripts/gauntlet/persistence.py`, `core_types.py`, `medals.py`, `phase_3_filtering.py` | Verified at: `ef18c66`
> If any derived-from file changed since `ef18c66`, trust source over this doc.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Store/checkpoint/resume gauntlet state, stats, medals, and run reports |
| Entry | `save_checkpoint()` at `persistence.py:560` |
| Key files | `persistence.py`, `medals.py`, `phase_3_filtering.py` |
| Depends on | FileLock, JSON, core types |
| Used by | Gauntlet orchestrator/phases/CLI/reporting |
| Runtime status | implemented |
| Architecture status | active_primary |

## What This Component Does

Persistence turns typed phase state into inspectable JSON/Markdown artifacts and reconstructs it for resume. It protects checkpoint and run writes with FileLock, canonical serialization, and content hashes. Shared usage stats/medal files are longer-lived and have a wider concurrency surface than run-specific files.

## Contracts

### Boundary Field Contracts

Chain: typed phase result → checkpoint envelope → resume loader.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `_meta.schema_version` | always | yes | supported checkpoint version | required | cannot decode safely | persistence | `persistence.py:45,79-137` | verified |
| `_meta.spec_hash` | always | yes | current spec hash match | required | checkpoint is for unknown spec | persistence | `persistence.py:171-212,281-333` | verified |
| `_meta.config_hash` | always | yes | current normalized config match | required | config drift cannot be assessed | persistence | `persistence.py:187-212,281-333` | verified |
| `_meta.data_hash` | always | yes | serialized data integrity | required | data integrity unknown | persistence | `persistence.py:99-137,281-333` | verified |
| `data` | phase-dependent | yes | phase-specific dataclass mapping | required for non-empty checkpoint | no resumable state | phase/orchestrator | `persistence.py:79-137` | verified |

## Invariants

- Writes use atomic temporary replacement and a lock for the target (`persistence.py:74-137`).
- Resume validates all relevant hashes before deserializing a phase state (`persistence.py:281-333`).
- Path resolution prevents arbitrary checkpoint filenames from escaping the configured artifact directory (`persistence.py:155-187`).

## Data Flow

```text
IN: phase dataclasses/spec/config
    └─> serialize/hash/lock
PROCESS: atomic write -> load/validate -> deserialize
OUT: checkpoint/run manifest/stats/medal files
     └─> orchestrator resume/reporting
```

## Key Functions

| Function | Purpose | Location |
|---|---|---|
| `_write_json_atomic()` | atomic locked JSON write | `persistence.py:124` |
| `save_checkpoint()` | phase checkpoint | `persistence.py:560` |
| `load_partial_run()` | resume loader | `persistence.py:688` |
| `save_gauntlet_run()` | final run artifact | `persistence.py:469` |
| `save_run_manifest()`/`update_run_manifest()` | manifest lifecycle | `persistence.py:598-629` |
| `save_adversary_stats()` | shared usage stats | `persistence.py:346` |

## Error Handling

- Corrupt JSON/mismatched hashes are rejected rather than repaired silently (`persistence.py:111-137,281-333`).
- Lock failures are surfaced to the caller; raw phase artifacts remain available for diagnosis.

## Concurrency Concerns

| Resource | Callers | Synchronization | Risk |
|---|---|---|---|
| run/checkpoint files | orchestrator/CLI | FileLock + atomic replacement | guarded per path |
| HAZ-001: shared filtering stats | phase 3 filtering from either live gauntlet CLI | no lock visible at `phase_3_filtering.py:217-233` | concurrent runs may lose updates |
| medals index | medal writers | persistence path conventions; verify lock coverage before multi-run use | duplicate/lost index updates possible |

## Configuration

| Config | Source | Default | Precedence |
|---|---|---|---|
| artifact dirs | module constants at `persistence.py:39-49` | `.adversarial-spec-gauntlet`/home state | explicit path/hash options |
| checkpoint schema | `CHECKPOINT_SCHEMA_VERSION` | 2 | code version is authoritative |

## Integration Points

**Calls out to:** file system/FileLock and core type serializers.

**Called by:** all gauntlet phase/resume/reporting paths.

## Active vs Target

- **Active consumers:** current gauntlet package.
- **Legacy consumers:** old monolith artifacts are not active.
- **Target architecture:** all shared state writes should use one documented locking policy.
- **Drift note:** run-specific lock coverage is stronger than shared stats/medal write coverage.

## LLM Notes

- Hash mismatch is a contract failure, not a prompt/model failure; preserve the original checkpoint while diagnosing.
