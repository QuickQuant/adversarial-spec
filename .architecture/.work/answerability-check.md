# Phase 6f Answerability Check

> Generated: 2026-07-19T08:43:13-05:00 | Git: `ef18c66`
>
> Each answer was written from the generated architecture docs first, then
> spot-checked against the cited source. All seven questions passed.

1. **What does absence of `status` mean at the validation CLI boundary?**
   - **Docs answer:** `status` is structurally required in the validation
     `Envelope`; absence means malformed output and must not be treated as
     success. Read `structured/components/validation-emission.md` and the
     `validation-cli-stdout` table in `structured/cross-references.md`.
   - **Spot-check:** `skills/adversarial-spec/scripts/validation_emission.py:200-220,3418-3460`.
   - **Result:** pass.

2. **Which file implements the gauntlet entry point?**
   - **Docs answer:** `skills/adversarial-spec/scripts/gauntlet/orchestrator.py`,
     `run_gauntlet()` at line 205; debate and standalone CLI are callers.
   - **Spot-check:** `orchestrator.py:205` and the two call paths in the
     structured entry-point map.
   - **Result:** pass.

3. **What breaks if a TMR `tmr_uid` is changed?**
   - **Docs answer:** The registry identity and compiler diff key change;
     prose derivation, provenance, coverage, and promotion joins can no longer
     match the prior record as the same stable TMR.
   - **Spot-check:** `tmr_compile_step.py:139-249`, `tmr_schema.py:175-377`,
     `phase8_promotion.py:162-243`.
   - **Result:** pass.

4. **How does a gauntlet resume avoid accepting stale state?**
   - **Docs answer:** Persistence stores checkpoint metadata and hashes under
     a per-path lock; resume validates schema/spec/config/data hashes before the
     next phase consumes the artifact.
   - **Spot-check:** `gauntlet/persistence.py:74-137,281-333`.
   - **Result:** pass.

5. **Which mechanism owns a hook allow/deny decision?**
   - **Docs answer:** The configured hook/sub-hook process owns the transient
     stdin/stdout decision; notification and activity logs are side effects,
     not proof of a pipeline transition.
   - **Spot-check:** `.claude/hooks/codex_pretool_combined.py:18-72` and
     `.claude/settings.json` hook registrations.
   - **Result:** pass.

6. **Where is a critical or happy-path-spine record prevented from closing on
   mock-only evidence?**
   - **Docs answer:** Phase 8 promotion evaluates liveness, criticality,
     negative-oracle, and boundary-mock requirements before close.
   - **Spot-check:** `phase8_promotion.py:162-271`, `tmr_schema.py:124-174`.
   - **Result:** pass.

7. **Why can the same gauntlet request have different timeout behavior?**
   - **Docs answer:** The top-level debate CLI defaults to 1200 seconds while
     the standalone gauntlet CLI defaults to 1800 seconds; both pass timeout
     policy into the gauntlet workflow.
   - **Spot-check:** `debate.py:401-404`, `gauntlet/cli.py:64-69`,
     `gauntlet/orchestrator.py:205-224`.
   - **Result:** pass.

## Result

`7 / 7` answerability tests passed. No documentation coverage gap was opened.
