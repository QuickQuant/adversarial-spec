# Guardrail Report — R11 (spec-draft-v12)

**Round:** 11 (press round)
**Spec:** `spec-draft-v11.md` → `spec-draft-v12.md` (1170L)
**Date:** 2026-06-16
**Evaluation:** inline (conductor) — 3 surgical prose-alignment edits closing a CANON-class
stale-tail drift; no body/contract/numeric/scope change. Dispatching guardrail models for
this delta would be wasteful.

## R11 critic outcome (what drove the edits)

Both critics were **pressed** after R10's bare `[AGREE]`s:
- `gemini-3-flash`: quality `[AGREE]`, 2127-char justification, 0 findings (reviewed §3/§6/§8.1;
  confirmed tmr_uid identity, live_or_induced strict union, tier↔mode compat map, GateResult
  outcome-only, supersedes-array). One soft non-blocking note: §12.13 echo-diff could become a
  rubber-stamp.
- `codex/gpt-5.5`: `agreed=false`, 1 finding (2 sub-items) — residual §12 stale-tail drift the
  v11 **body** had already resolved. Confirmed the 6 R9 fixes all landed correctly.

## Edits applied (v11 → v12)

| # | Section | Change | Class |
|---|---------|--------|-------|
| R11-1 | §12 item 3 | "F′ parses each test's structured `TMR:` block" → "F′ parses validated records from `tmr-registry.json` via `TmrParser`; markdown/`TMR:` blocks are display-only mirrors, never gate input" | CANON drift fix |
| R11-2 | §12 item 12 | stale "Open only: adversary leaderboard + final convergence round" → "remaining non-contract process work only; no schema/gate blockers after v12" | CONS (stale process state) |
| R11-3 | §12.13 | round-trip echo guard: echo-diff is an explicit semantic diff for sign-off, never a blind rubber-stamp | hardening (flash note) |

## Guardrail status

| Guardrail | Status | Notes |
|-----------|--------|-------|
| CONS  | **pass** | §12.3 now consistent with §3/§4.2/§6 (F′ input = registry). §12.12/§12.13 are prose/operator-guard text; no new contradiction, no numbering/arithmetic change. |
| SCOPE | **pass** | No new capability. All three edits remove/align stale prose. |
| TRACE | **pass** | No user-story coverage lost (the §13 coverage map is untouched). |
| CANON | **pass (drift CLOSED)** | R11-1 closes the §12.3 F′-input-contract drift — the exact drift class v11 claimed to close. **1 prior CANON item remains tracked-to-finalize**, unchanged by this round: architecture-invariants mirror (status enum / supersedes-array / GateResult-outcome) + `schema_sha256` regen. |
| TCOV  | **pass** | tests-pseudo.md was ALREADY in sync — line 35 ("the registry is the SoR; F′ never parses markdown") and line 207 ("F′ parses the corresponding `tmr-registry.json` record, not this markdown block") already assert registry-parsing. The drift was purely in the §12 prose; no test change required. |

## Convergence assessment

R11 did **not** converge (codex `agreed=false`, 1 finding — now fixed in v12). The press was the
right call: R10's bare codex `[AGREE]` had concealed a genuine `CANON`-class finding. flash's
pressed `[AGREE]` is now a quality, counting agreement.

**Next: R12** — clean 2-family convergence re-check on v12 (codex/gpt-5.5 + gemini-3-flash,
press framing retained). If both quality-`[AGREE]` → 2-critic/2-family system-altitude quorum →
reconcile card 5715 gauntlet state + finalize. Trend: R8 14 → R9 6 → R10 0 (unsubstantiated) →
R11 1 (real, fixed).
