# Component: Provenance, Criticality, and Phase 8 Promotion

> Derived from: `skills/adversarial-spec/scripts/provenance_journal.py`, `phase8_promotion.py`, `criticality_classifier.py`, `tcov_liveness.py`, `spine_coverage_checker.py` | Verified at: `ef18c66`
> If any derived-from file changed since `ef18c66`, trust source over this doc.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Record lineage transitions and decide whether evidence is sufficient to close implementation |
| Entry | `ProvenanceJournalWriter` at `provenance_journal.py:112`; `evaluate_phase8_close()` at `phase8_promotion.py:162` |
| Key files | provenance journal, promotion, criticality/liveness/spine checks |
| Depends on | TMR schema/registry, FileLock, run evidence |
| Used by | Phase 8 implementation flow, validation workflow, tests |
| Runtime status | implemented |
| Architecture status | active_primary |

## What This Component Does

The component records TMR/node transitions with optimistic expected coordinates and durable append-only lineage. Phase 8 promotion consumes TMR records and evidence, enforcing liveness, criticality, negative-oracle, and boundary-mock rules before permitting close.

## Contracts

### Boundary Field Contracts

Chain: `JournalTransition` → ordered locks → registry/journal/index.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| `subject_type`/`subject_id` | required | yes | supported test/node subject | journal/index | invalid transition | journal writer | `provenance_journal.py:19-40,54-105` | verified |
| `event_type` | required enum | yes | transition reducer | append-only | invalid/no-op not accepted | journal writer | `provenance_journal.py:19-40,460-479` | verified |
| `expected_from` | optional optimistic fence | yes | writer checks when supplied | preserve transition metadata | no optimistic fence; caller accepts weaker stale-writer protection | caller/writer | `provenance_journal.py:54-105,112-400` | verified |

### Type Contracts

| Contract | Purpose | Owner | Consumed By |
|---|---|---|---|
| `JournalTransition` | typed lineage event | `provenance_journal.py:54` | writer/index/journal |
| `AppendReceipt` | result of successful append | `provenance_journal.py:105` | caller/evidence flow |
| `PromotionRequest` | requested evidence action | `phase8_promotion.py:23` | implementation workflow |
| `Phase8PromotionReport` | close decision/issues | `phase8_promotion.py:62` | Phase 8 gate |

## Invariants

- Registry, journal, and index writes acquire locks in a stable order (`provenance_journal.py:581-596`) to avoid lock-order deadlocks.
- Writes are atomic and previous bytes are restored on failure (`provenance_journal.py:522-573`).
- `expected_from` rejects stale coordinates rather than merging unknown changes (`provenance_journal.py:112-400`).
- Critical or happy-path-spine records require real/induced evidence and negative-oracle/boundary-mock checks (`phase8_promotion.py:243-271`).

## Data Flow

```text
IN: typed transition + current registry/index + TMR evidence
PROCESS: validate -> lock -> append -> atomic registry/index update -> promotion evaluation
OUT: AppendReceipt, lineage files, Phase8PromotionReport
```

## Key Functions

| Function | Purpose | Location |
|---|---|---|
| `append_decision_log()` | append decision event | `provenance_journal.py:416` |
| `active_spine_records()` | select spine records | `provenance_journal.py:401` |
| `evaluate_phase8_close()` | evaluate promotion/close | `phase8_promotion.py:162` |
| `capture_run_evidence()` | attach execution evidence | `phase8_promotion.py:128` |
| `CriticalityClassifier` | classify critical seam/source | `criticality_classifier.py:11` |
| `TcovLivenessAuditor` | liveness audit | `tcov_liveness.py:14` |

## Error Handling

- Stale expected coordinates raise a typed provenance error; no silent overwrite.
- Promotion issues remain in the report and block closure when required proof is absent.
- Atomic write failure restores previous state before re-raising (`provenance_journal.py:545-573`).

## Concurrency Concerns

| Resource | Callers | Synchronization | Risk |
|---|---|---|---|
| registry/journal/index | transitions, promotion, dispositions | ordered multi-file locks | guarded; lock acquisition order is part of invariant |

## Configuration

| Config | Source | Default | Precedence |
|---|---|---|---|
| contract/schema version | TMR schema/constants | `tmr.v1` | schema authority |
| criticality | explicit field, architecture link, unknown | `unknown` if absent | explicit > architecture link > unknown |
| evidence rules | Phase 8 code constants | strict | critical/spine rules override generic verification mode |

## Integration Points

**Calls out to:** TMR compiler/schema, validation-emission artifacts, local filesystem.

**Called by:** Phase 8 workflow, disposition/promotion callers.

## Active vs Target

- **Active consumers:** current validation-leg implementation and tests.
- **Target architecture:** all evidence-affecting transitions should pass through the journal/registry contract.

## LLM Notes

- A green unit test can satisfy code verification without satisfying liveness; promotion evaluates both the record’s strategy and its evidence.
