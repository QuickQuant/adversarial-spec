# Guardrail Report — R5 incorporation (spec-draft-v7)

> Round 5 convergence round (codex/gpt-5.5 + gemini-3.1-pro, both `agreed:false`, 9 concerns).
> All 9 applied to v7. Guardrails run **inline** by Claude (spec fits in context; no subagent dispatch).

## CONS (consistency) — PASS (no new contradictions)
The 9 fixes were themselves contradiction-repairs; verified they don't introduce new ones:
- `live_or_induced` is now a tagged `{kind, detail?}` (§3.1); §4.3 MOCK rule (C6) and §8.1 receipt reference it consistently — naming a technique ⇒ promote (matches §0.2).
- `also_covers[]` declared NON-COVERING in BOTH §4.1 and §6 — F′ counts scalar `user_story` only.
- exit `5` (`setup_error`) now in §6 fail-closed list AND the §6 GateResult exit map — aligned.
- `tmr_uid` in §4.2 canonical field list + §7 DD-8 + §4.2 prose-anchor — coherent.
- §8.1 DD-4/SEC-4 split is now single-voiced: owner repo authors/binds, skill-runner executes + captures the receipt.
- §5.1 headless floor exemption is consistent with §6 (the ≥50-char floor still governs interactive human overrides).

## SCOPE — PASS
All 9 fixes are refinements of already-accepted v6 folds (DD-3/DD-6/DD-8/DD-4/US-2/US-6). New identifiers (`spine_of`, `also_covers`, `tmr_uid`, `technical_constraint`, `other:<detail>`) realize accepted concerns; no new scope introduced.

## TRACE — PASS
All 15 user stories retain coverage (§13 map unchanged). No journey lost a spine designation.

## CANON — 1 FOLLOW-UP (non-blocking, tracked)
The new v7 fields (`tmr_uid`, `spine_of`, `also_covers`, `technical_constraint`) and the `live_or_induced` `{kind, detail}` tagged form must be mirrored into the **keystone JSON Schema** (`test-maturity-record-schema.md`) and `architecture-invariants.json` (INV-004/INV-029 surfaces). CANON-r4-1 mirrored the v6 set; this is a small v7 delta. Tracked for the post-convergence arch-sync (folds into finalize / TCOV-r4-1). Not blocking R6.

## TCOV — DEFERRED (TCOV-r4-1, known)
G3 added negative-oracle requirements for the new infra components (§9). Materializing those oracles + the tmr-registry migration is the deferred TCOV-r4-1 task (§12 item 11). No new test artifact written this round by design.

## Verdict
v7 is internally consistent; the only open guardrail item (CANON v7-field delta) is a tracked non-blocking follow-up. Proceed to R6 re-review for convergence.
