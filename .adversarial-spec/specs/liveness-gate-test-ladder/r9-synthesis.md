# R9 synthesis (spec-draft-v10) — v11 fix list — 2026-06-16

**Verdict: NOT converged**, but tightly bounded. codex/gpt-5.5 and gemini-3-flash (2 distinct
families) **independently converged on the SAME 6 residual findings** — neither found anything new
beyond these. All are surgical corrections (mostly tests-pseudo not fully re-synced to the v10
schema + 2 spec field-type issues). None reopen the trust model or the security-strip.

(codex's R9 dispatch in the final round instance hit its usage limit ~6:04 PM reset; its findings
are from the prior identical-content run, captured here + in r9-codex-findings.md. flash's raw:
round-12a5a35148104b81/results/gemini-3-flash/. The clean 2-family convergence check is R10 on v11.)

## v11 fix list (codex [SPEC] patches are concrete; flash confirms all 6)

1. **Identity = tmr_uid, in spec AND tests.** §3 already says tmr_uid is immutable identity, but
   TC-1.0 / TC-INV-004 still assert the `session·user_story·test_id` tuple is the identity to hold
   unchanged. Fix: tests key identity on `tmr_uid`; they may assert coordinate PRESERVATION for
   user_story/test_id, and session only when testing exported/container metadata. Also §3: `session_id`
   is registry-container/export metadata, NOT a field inside local tmr-registry.json; active records
   unique on `(user_story, test_id)` locally / `(session_id, user_story, test_id)` when exported.
2. **`supersedes` → array.** §3.1/§4.2 define it singular (`<tmr_uid>|null`), but §3/§7 require
   merge lineage (many predecessors). Fix: `supersedes` = array of tmr_uid, default `[]`
   (replacement = one pred; merge = many; tombstoned-without-replacement = `[]`). Update §3.1 partition
   (it's currently listed under optional-with-default `null` → change to default `[]`).
3. **`status` required-on-emit.** §3.1: post-emit registry records MUST contain `status`; validators
   do not silently fill a missing required key (compiler emits `active` on creation). (Confirm the
   §3.1 partition lists `status` as always-required — it does; just add the "no silent fill" note.)
4. **GateResult: `outcome` is the ONLY normative outcome field.** §5.1 uses `outcome`; §6 checker
   output JSON uses `result`; TC-8.0 returns BOTH `{result, outcome}`. Fix: §6 output JSON envelope =
   `{contract_version, outcome, checked_at, session_id, roadmap_manifest_sha256, tmr_registry_sha256,
   findings, override_eligible, evidence_id}` — drop `result`. TC-8.0 returns `{outcome:"pass"}` only.
   (Keep `run_evidence.result: pass|fail` — that's a different field, unaffected.)
5. **`tier` ↔ `verification_mode` = compatible-by-MAP, not equality.** §8.1 says receipt `tier` is
   "hard-checked against verification_mode" — ambiguous, reads as string equality, but judgment-tier
   uses `verification_mode: system-validation` (no `golden-eval` mode, §9). Fix: define the map
   explicitly in §8.1: `automated-*`/`test-producer` → tier `code`; `system-validation` + transcript
   fields → tier `system-validation`; `system-validation` + `golden_manifest_id`/`per_case_results` →
   tier `judgment`; exempt modes (`artifact-sync`/`static-check`/`manual-ux`) → `run_evidence: null`.
6. **TC-8.0 embedded block = generated-view MIRROR.** TC-8.0 still presents the YAML `TMR:` block as
   what F′ parses. Fix: label it "F′ parses the corresponding `tmr-registry.json` record, not this
   markdown block; this block is the generated-view mirror." (The §6/§4.2 "registry is SoR" already
   says this; the test must not contradict it.)
7. **TC-8.4 = registry fixture.** TC-8.4 (duplicate-spine) describes a `tests-pseudo` fixture with two
   `[spine]` tests → implies markdown parsing. Fix: fixture = a `tmr-registry.json` with two active
   `spine:true` records for the same scalar `user_story`.
8. **TC-3.0 require `technical_constraint`.** §3.1/§4.3 require a non-empty `technical_constraint` for
   a justified MOCK (`data_strategy=MOCK ∧ live_or_induced=null`), but TC-3.0 only asserts
   `why_impossible_to_reproduce_live`. Fix: TC-3.0 asserts BOTH non-empty.

codex [SPEC] raw: round-62849d816b564514/results/codex-gpt-5.5/raw.txt (items 1-5).
flash [SPEC] raw: round-12a5a35148104b81/results/gemini-3-flash/raw.txt.
