# R9 codex/gpt-5.5 findings on spec-draft-v10 (agreed=false) — 2026-06-16

Single-critic so far (2nd family blocked — see session next_action). v11 needed regardless.
codex gave concrete [SPEC] patches; these are residual v10 contract drift (mostly tests-pseudo
not fully re-synced to the v10 schema + a few spec gaps).

1. **CRITICAL — identity tuple still live in tests.** §3 says tmr_uid is immutable identity, but
   TC-1.0 / TC-INV-004 still call `session·user_story·test_id` the identity. §3.1 also omits
   `session` from required fields under extra:forbid while §3 uniqueness includes session. Fix:
   tmr_uid = identity; test_id/user_story = coordinates; `session_id` = container/export metadata,
   not a registry field; active records unique on (user_story, test_id) local / (session,us,test_id) exported.
2. **CRITICAL — registry-SoR drift remains in US-8.** TC-8.0 still says F′ parses the embedded
   markdown `TMR:` block; TC-8.4 duplicate-spine fixture is in tests-pseudo not the registry.
   Fix: label the TC-8.0 block a generated-view MIRROR ("F′ parses the tmr-registry.json record,
   not this markdown"); TC-8.4 uses a tmr-registry.json fixture with two active spine:true records.
3. **HIGH — run_evidence.tier can't hard-EQUAL verification_mode.** §8.1 hard-checks tier==mode,
   but judgment-tier uses verification_mode `system-validation` (no `golden-eval` mode exists, §9).
   Fix: "hard-checked" = compatible-by-MAP, not equality: automated-*/test-producer→code;
   system-validation+transcript→system-validation; system-validation+golden_manifest→judgment;
   exempt modes→null.
4. **HIGH — GateResult names two outcome fields.** §5.1 = `outcome`; §6 JSON = `result`; TC-8.0
   expects both `{result, outcome}`. Pick `outcome` as the only normative field everywhere.
5. **MEDIUM — `supersedes` singular can't represent merge.** §3/§7 require split/merge lineage but
   §4.2 defines supersedes as `<tmr_uid>|null`. Fix: array of tmr_uid, default []; merge = many preds.
6. **MEDIUM — TC-3.0 under-specifies justified MOCK.** §3.1/§4.3 require `technical_constraint` for
   MOCK∧null, but TC-3.0 only asserts `why_impossible_to_reproduce_live`. Add technical_constraint.

Raw: debate-workspaces/.../round-62849d816b564514/results/codex-gpt-5.5/raw.txt
(NB: that round instance was replaced; codex findings identical content, captured here.)
