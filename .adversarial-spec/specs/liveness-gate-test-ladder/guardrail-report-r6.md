# Guardrail Report — R6 convergence re-review (spec-draft-v8)

> Round 6 (codex/gpt-5.5 + gemini-3.1-pro). gemini `[AGREE]` (stub — bare marker, 0-char
> justification → NOT a quality agreement). codex `agreed:false`, **1 valid concern (R6-C7)** applied to v8.
> No convergence (codex blocked; gemini agreement is stub-quality). Guardrails run **inline** by Claude.

## The R6-C7 fix (codex, CRITICAL→applied)
R5-C3 made `live_or_induced` a tagged `{kind, detail?}` but left `null` listed as a member of the
`kind` enum, while §4.3/§0.2 also use field-level JSON `null` for a justified MOCK. Two valid-looking
encodings for "no technique" (JSON `null` vs `{kind: null}`) → cross-repo parser drift / false rejects
under `extra:forbid`. Fix: `live_or_induced` is now a strict **union** — JSON `null` XOR a tagged object
whose `kind` is never null. Dropped `null` from the `kind` enum; `TmrParser` rejects `{kind: null}` and
`{"kind": "null"}`. §3.1 enum row + null-note + v8 changelog updated; TC-1.4 added as the falsifying oracle.

## CONS (consistency) — PASS
R6-C7 *removes* the dual-encoding contradiction. Verified no remaining `kind`+null co-occurrence except
the corrected union statements (§3.1 row, null note). §4.3 `live_or_induced: null` is now the single
canonical "no technique" encoding — consistent. No new contradiction introduced.

## SCOPE — PASS
Narrows an existing field's validation (the R5-C3 tagged form); no new feature or scope. Realizes the
already-accepted strict-union intent.

## TRACE — PASS
All 15 user stories retain coverage. TC-1.4 added under US-1 (TMR validation). No journey lost a spine.

## CANON — 1 FOLLOW-UP (non-blocking, tracked)
The `kind`-enum-without-`null` delta must mirror into the keystone JSON Schema
(`test-maturity-record-schema.md` → `VALID_LIVENESS_TECHNIQUES`) and `architecture-invariants.json`.
Folds into the existing **CANON-r4-1** post-convergence arch-sync (same mirror pass that carries the
v7-field delta). Not blocking R7.

## TCOV — PASS
TC-1.4 is the falsifying oracle for the new rule: valid forms (JSON null / tagged non-null kind) accepted;
invalid forms (`{kind: null}`, `{"kind": "null"}`, `other` w/o detail) rejected with named errors. A parser
that treats `{kind: null}` as equivalent to JSON null is explicitly called smoke-only.

## Verdict
v8 is internally consistent; the only open guardrail item is the tracked CANON arch-mirror (folds into
CANON-r4-1). No convergence — codex's R6-C7 applied, gemini agreement is stub-quality. Proceed to R7:
re-dispatch both critics on v8; **press gemini for a substantive justification** (its R6 [AGREE] was an
8-byte stub) before any convergence is declared.
