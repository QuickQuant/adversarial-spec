# Architecture Action Plan

> Derived from verified hazards, patterns, and findings at Git `2433efa`.
> This is a planning artifact; mapcodebase does not implement these changes.

## Wave 1 — protect correctness gates

1. **Make final-review failure non-success.**
   - Owner surface: `gauntlet/phase_7_final_boss.py`, `gauntlet/core_types.py`,
     orchestrator result/exit mapping.
   - Source concern: `CON-001` / `FIND-001`.
   - Acceptance: injected model failure produces an explicit failed/blocked
     result, non-success exit behavior, and no `FinalBossVerdict.PASS`.
   - Dependency: define the result vocabulary before changing callers.

2. **Make the lifecycle contract include verification.**
   - Owner surface: `SKILL.md`, Phase 8/9 lifecycle documentation, journey-order tests.
   - Source concern: `CON-002` / `FIND-002`.
   - Acceptance: an `implementation → verification → complete` journey passes the resume-time order checker; no alternative canonical ordering exists.

3. **Guard shared gauntlet sidecars.**
   - Owner surface: `gauntlet/orchestrator.py`, `phase_3_filtering.py`, persistence utility.
   - Source concern: `CON-003`.
   - Acceptance: two same-spec runs cannot overwrite raw response, cluster report, or dedup telemetry; a concurrency regression test proves isolation or merge semantics.

4. **Guard session state writes and make corruption visible.**
   - Owner surface: `session.py`, `models.py`, shared persistence utility.
   - Source concerns: `CON-004`, `CON-007`.
   - Acceptance: same-target writers are serialized or rejected; interrupted writes preserve valid state; session listing reports skipped/corrupt paths.

## Wave 2 — remove semantic drift

5. **Unify gauntlet timeout defaults.**
   - Owner surface: `debate.py`, `gauntlet/cli.py`, shared CLI/config helper.
   - Source concern: `FIND-003` / `CON-006`.
   - Acceptance: both entry points expose the same documented default, or the
     difference is explicit in `GauntletConfig` and covered by tests.

6. **Centralize worker-role resolution.**
   - Owner surface: `.claude/hooks/dispatch_check.py`,
     `pipeline_continue.py`, `pipeline_idle_retry.py`, new shared hook helper.
   - Source concern: `duplicated-worker-role-resolution` / `CON-005`.
   - Acceptance: one precedence table drives all three hooks; environment,
     registration, and fallback cases have shared contract tests.

7. **Correct stale runtime comments and transitional labels.**
   - Owner surface: `gauntlet/phase_3_filtering.py`,
     `gauntlet/core_types.py`, `validation_emission.py`.
   - Source concerns: `FIND-004`, `FIND-005`, `CON-008`.
   - Acceptance: comments identify the live clustering/telemetry path and the
     validation handlers; a future agent cannot infer that active commands are
     skeleton-only.

## Wave 3 — reduce structural coupling

8. **Define one transport adapter contract.**
   - Owner surface: `models.py`, `gauntlet/model_dispatch.py`, token tracking.
   - Source concern: `FIND-007` / `CON-009`.
   - Acceptance: CLI/LiteLLM routing and usage accounting have one transport
     implementation with policy-specific callers.

9. **Reduce direct source-layout bootstraps.**
   - Owner surface: `scripts/__init__.py`, path-mutating modules, package import tests.
   - Source concern: `CON-010`.
   - Acceptance: installed and source checkout imports have one explicit package contract; retain the verified root symlink until callers migrate.

10. **Make Python 3.10 TOML behavior explicit.**
   - Owner surface: `pyproject.toml`, `pre_gauntlet/orchestrator.py`.
   - Source concern: `FIND-008` / `CON-011`.
   - Acceptance: Python 3.10 loads compatibility configuration or fails with an actionable error, never silently defaults because a parser is absent.

## Sequencing rule

Wave 1 precedes refactors that change result or persistence shapes. Wave 2 can proceed after lifecycle and gate contracts are explicit. Wave 3 follows only after affected CLI, gauntlet, and hook contract tests pass.
