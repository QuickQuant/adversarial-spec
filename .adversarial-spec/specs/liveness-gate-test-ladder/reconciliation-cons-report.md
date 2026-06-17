# Reconciliation CONS Report — Liveness Gate + Test Ladder

> Gauntlet→Finalization reconciliation consistency check.
> Gauntlet attacked the converged **v8** snapshot (spec_hash `8695e8c1`).
> Revised/reconciled spec: **spec-draft-v12.md** (R12 system-altitude convergence).
> Date: 2026-06-17.

## What was reconciled

The v8 delta-attack gauntlet surfaced 38 judged concerns (380 raw across codex/gpt-5.5 +
gemini-3-flash families; see `gauntlet-concerns-2026-06-16.json`). Every ACCEPT/ACKNOWLEDGE
concern was folded across the v9→v12 redesign and re-validated through debate rounds R8–R12,
which re-converged at R12 (2 counting critics, 2 distinct families, quality [AGREE] / 0 findings).

Representative high-severity folds (gauntlet → resolution in v12):
- **CB-1** tombstone/status/supersedes missing from schema → §3.1 `status: active|tombstoned` enum
  (fizzy `VALID_TMR_STATUS`) + `tombstoned_at` + `supersedes` as array of tmr_uids (DR-3).
- **CB-2** `run_evidence` incompatible shapes → discriminated union (§3.1/§8.1).
- **CB-3** `live_or_induced` dual-encoding → strict tagged union (R6-C7 line, carried into v12).
- **GateResult** outcome-vs-result fork → `outcome` is the only normative envelope field (R9).
- **CB-7** `tmr_uid` allocation → compiler-allocated ULID, immutable, globally unique (DR-4).

The accompanying CANON-r4-1 architecture mirror (previously "tracked-to-finalize" in the R11/R12
guardrail reports) is now **CLOSED**: `architecture-invariants.json` mirrors the v12 schema deltas
(INV-029 status-enum + array-supersedes; INV-024 outcome-only GateResult; INV-004 identity=tmr_uid),
and the `architecture_fingerprint` was recomputed over the reconciled invariants.

## Consistency verdict

**No contradictions found.**

The R12 guardrail report (`guardrail-report-r12.md`) records CONS / SCOPE / TRACE / CANON / TCOV all
**pass** on v12. The §12.3 F′-input drift (the one real finding the R11 press surfaced) is CLOSED:
F′ parses validated `tmr-registry.json` records, consistent with §3 / §4.2 / §6.

## Non-blocking residual (explicitly NOT a contradiction)

Both R12 critics independently flagged the SAME item and BOTH classified it as
implementation/activation work, not a spec contradiction:

- §12.11 / §13: F′ would not pass against the *current implementation state* because 14 of 15 spine
  tests are not yet compiled into `tmr-registry.json`. This is the **R4-1 activation rule** — the gate
  is advisory until (a) the Fizzy gate lands and (b) the spine tests are compiled into the registry.
  Tracked in §12.11 as implementation/migration work. It does not block reconciliation or finalization.
