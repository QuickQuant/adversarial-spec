# Process Failure #12 — ADDENDUM to the take/take handoff

> **RESOLVED 2026-06-08 (commit `6be8c9a`).** Skill halves (a) generator + (b) process
> are implemented and the row + thread entry are folded into the main handoff
> (`adversarial-spec-process-failure-report-pipeline-seams-20260530.md`, row #12 / General
> principle). Only the fizzy contract half (c) remains, and it is fizzy's. This file is
> kept as the original forensic record; the main report is now authoritative.

**Standalone because the main handoff (`adversarial-spec-process-failure-report-pipeline-seams-20260530.md`) is being edited concurrently.** This is *only* #12 — append this one row to the table in that file (after #11) and add `#12` to the "General principle" thread list when convenient. Nothing else here changes.

Discovered after #11 was fixed: merging `acceptance_criteria` into the 34 tasks cleared #11, and re-running the real `pipeline_validate_plan` then surfaced #12 (the validator raises on the first failing task, so #12 was masked until #11 was resolved). Plan is now `valid:true` (hash `76d86dd0`, 35 tasks, 0 issues).

**Your half (adversarial-spec):** the generator — Phase 7's fizzy-plan emitter writes `strategy:"skip"` for deferred/manual-only tasks. It should emit a valid strategy (`spike`) instead, and Phase 7 should run the real `pipeline_validate_plan` as its authoritative pre-load gate (this would have caught both #11 and #12 in one pass, instead of the local revalidation that knew neither contract). (The enum/contract half — whether `"skip"` should become first-class — is fizzy's.)

| # | Hole | Owner | Evidence | Fix | Effort |
|---|------|-------|----------|-----|--------|
| 12 | **`strategy` enum drift — Phase 7 generator emits `strategy:"skip"` for deferred / non-automated-test tasks, but fizzy rejects it.** Same hidden-until-load class as #11, and only surfaced *after* #11 was fixed because `_validate_plan` raises on the first failing task. fizzy's `VALID_STRATEGIES = {test-first, test-after, spike, refactor}` (`pipeline.py:134`, enforced `:3800-3801`) has no `skip`. The Phase 7 generator used `"skip"` to mean "deferred / manual-only, no automated-test commitment" (G14 deferred wire-integrity per A3/SDK-5; L3 manual-ux operator tooltips). | adversarial-spec **skill** (generator) + **fizzy** (contract/enum) | This session: 2 of 35 tasks used `strategy:"skip"`; real `pipeline_validate_plan` returned `valid:false, PLAN_INVALID "Task G14: invalid strategy"`. Note `strategy` is **decoupled** from the v2 verification gate (`_validate_v2_task` never reads it) — both tasks already pass verification independently via EXEMPT modes (`static-check`/`manual-ux`) + `exemption_reason`, so the enum value is the *only* thing that was wrong. Mapped both `skip→spike` (the honest valid value — `spike` commits no automated tests, unlike test-first/test-after); plan then reached `valid:true` (hash `76d86dd0`). | (a) **generator:** map deferred / manual-only tasks to a valid strategy (`spike`) instead of `"skip"`; (b) **process:** run the real `pipeline_validate_plan` (would have caught #11 *and* #12 in one pass); and/or (c) **contract:** add a first-class `"skip"`/`"deferred"` strategy to `VALID_STRATEGIES` if deferred tasks are a real lifecycle state, or document `spike` as the canonical deferred mapping. | EASY |
