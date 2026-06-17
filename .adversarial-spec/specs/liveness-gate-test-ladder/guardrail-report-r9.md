# Guardrail report — R9 incorporation (spec-draft-v11) — 2026-06-16

Spec: spec-draft-v11.md (1167L) | Tests: tests-pseudo.md (460L)
R9 critics: gemini-3-flash (6, completed) + codex/gpt-5.5 (6, from prior identical-content run;
final-instance dispatch hit usage limit ~6:04 PM). Both families CONVERGED on the same 6 residual
findings — neither found anything new. v11 = v10 + 8 surgical fixes (the 6 + 2 sub-parts). All
corrections; none reopen the trust model or the security-strip.

## Results
| Guardrail | Verdict | Notes |
|---|---|---|
| CONS | PASS | GateResult `outcome` vs receipt `run_evidence.result` cleanly separated (envelope uses outcome only; receipt result untouched, 8 legit spots); `supersedes` array-default-`[]` consistent across §3/§3.1-partition/§4.2; identity=tmr_uid consistent §3/TC-1.0/TC-INV-004 |
| SCOPE | PASS | all 8 fixes are corrections to existing sections; no new capability |
| TRACE | PASS | 15/15 US intact; §13 coverage map unchanged (TC IDs unchanged) |
| CANON | PASS (tracked) | finalize-tracked: mirror to architecture-invariants.json — status/lifecycle enum (from R8) + `supersedes` array shape + GateResult `outcome` canonical field; regen §3.1 schema_sha256. Non-blocking. |
| TCOV | PASS (improved) | TC-1.0/TC-INV-004 now key identity on tmr_uid (assert coordinate preservation, not tuple-identity); TC-3.0 now requires non-empty technical_constraint; TC-8.4 = registry fixture (2 active spine:true); TC-8.0 emits {outcome} only |

## Tracked-to-finalize (non-blocking)
- CANON: architecture-invariants.json mirror (status enum + supersedes array + GateResult outcome) + §3.1 schema_sha256 regen.
- §12 open item 11: 14 spine tests still need tmr-registry.json records (R4-4 compile) — pre-existing.

## Verdict
v11 incorporation clean. Record R9 (convergence=false). R10 = the clean 2-family convergence check
on v11 once codex usage resets (~6:04 PM) + gemini-3-flash. Strong convergence trend: R8 14 → R9 6
(both families agree on the same 6, now fixed).
