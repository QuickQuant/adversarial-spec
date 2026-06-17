# R8 re-convergence synthesis (spec-draft-v9) — 2026-06-16

**Verdict: NOT converged.** Both critics `agreed=false`, strongly convergent. None reopen the
locked trust model or the deliberate security-strip — all are *corrections* to the v9 fold.

**Critics:** codex/gpt-5.5 (10 findings) + claude-opus-4.7 (4 findings).
**Substitution (infra-forced):** gemini-3.1-pro quota-exhausted ~21h; pipeline `gemini-3-flash`
alias 404s (passes CLI id `gemini-3-flash`, real id is `gemini-3-flash-preview`). claude-opus-4.7
used as a distinct 2nd family. round_instance fac11564b03e42a5.
Raw artifacts: `debate-workspaces/.../round-fac11564b03e42a5/results/{codex-gpt-5.5,claude-opus-4.7}/`.

**Root cause:** `tests-pseudo.md` was never diffed against the v9 schema redesign. The v9
"consistency check passed" only checked the *spec* for dead refs; it never re-synced *tests*.

## v10 fix list (both critics gave concrete, compatible [SPEC] patches)

1. **US-8 MORPH (keystone, both critics independently).** TC-8.0 + TC-INV-001 still call the
   skill-side pre-check **PRIMARY**; v4 SEC-1 (carried to v9) made skill-side **advisory** and
   Fizzy `pipeline_advance` the **mechanical** gate. Re-center both spine tests on the Fizzy
   gauntlet-entry gate (contract = `uv run gauntlet-check --action gauntlet --output json`, R4-2),
   skill-side as fail-fast advisory. NEGATIVE oracle: Fizzy refuses advance when no F′ evidence is
   attached, even if the advisory pre-check passed. → run `reference/morph-reconciliation.md` for US-8.
2. TC-1.3 / TC-8.0 still parse a markdown `TMR:` block → violates DR-11/DD-1 (registry is SoR;
   F′ never parses markdown). Fixtures must use `tmr-registry.json`; tests-pseudo carries
   `<!-- tmr_uid: <ULID> -->` anchors + generated prose only.
3. TMR identity inconsistent: §3 keys by `session·user_story·test_id` but DR-4 makes `tmr_uid`
   the immutable identity. Renames keep the same `tmr_uid`; replace/split/merge mint new uid +
   tombstone old + set `supersedes`. Fix §3 identity text + §7 rename semantics.
4. `run_evidence` discriminated union: tests still use flat `{result, env}`; only the `code`
   variant has `env`. Fix tests + §2.1 step-4 receipt shape (`tier: code` variant).
5. DR-8 generalization untested: §4.3 null rule names only `MOCK`; add TC-3.2 negative —
   critical-seam + `data_strategy ∈ {SYNTHETIC, STATIC, MOCK-EXTERNAL, FRONTEND}` + empty
   `why_impossible_to_reproduce_live` is REJECTED (closes relabel-to-bypass).
6. §3.1 shared-enums table missing `status: active|tombstoned` → DD-5 prose/schema hash mismatch.
   Add the row; regenerate `schema_sha256`.
7. §4.2 required-vs-optional partition unspecified under `extra: forbid`. Add the partition
   (always-required / optional-with-default / conditionally-required) — claude supplied a full draft.
8. DR-9 claims env→real-pass "tabulated" but §8.1 is prose-only. Insert the actual matrix
   (criticality_source × critical_seam × env × live_or_induced → real-pass?) — claude supplied it.
9. §8.2 ContractVersionResolver prose retains anti-attacker framing (inconsistent with DR-7);
   tests say marker-alone flips outcome but resolver anchors on immutable Fizzy `created_at`.
   Reframe as honest-mistake protection; fix TC-12.0/12.1/INV-016.
10. §7 vs §12.10 override-provenance conflict (journal vs no-journal-scope). Per DR-10:
    plain-text `decisions.log` with `decision_id`; journal scoped to `{test,node}` field changes,
    cites `decision_id`. SEC-3 ≥50-char floor: state explicitly it is DROPPED post-DR-7.
11. TC-11.0 producer split: owner repo authors/binds the test, skill-runner executes + captures
    receipt. TC-11.0 wrongly says the promotion pass writes the real test.
12. §11 guardrails: "file pointers" → content payloads (DR-6 reads-once-passes-identical-bytes);
    TMR-changing findings keyed by `{user_story,test_id}`, spec/contract findings by
    `spec_section`/`contract` and not journaled unless they drive a field change.
13. ULID exemplar `01J0EXEMPLARULID0000000000` is 25 chars; ULID is 26 (Crockford base32). Pad.

**Pipeline state:** round 8 begun (round_instance fac11564b03e42a5); advance BLOCKED on checklist
steps "Synthesize findings" + "Update spec" — must author v10 + attest before recording the round.
**Next:** author spec-draft-v10 → re-sync tests-pseudo → guardrails → attest steps → advance R8
(convergence=false, current_spec_draft=v10) → R9.
