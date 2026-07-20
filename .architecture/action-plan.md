# Architecture Action Plan

> Derived from hazards, patterns, and findings at Git `ef18c66`.
> This is a planning artifact; mapcodebase does not implement these changes.

## Wave 1 — protect correctness gates

1. **Make final-review failure non-success.**
   - Owner surface: `gauntlet/phase_7_final_boss.py`, `gauntlet/core_types.py`,
     orchestrator result/exit mapping.
   - Source concern: `CON-001` / `duplicated-gauntlet-model-error-fallbacks`.
   - Acceptance: injected model failure produces an explicit failed/blocked
     result, non-success exit behavior, and no `FinalBossVerdict.PASS`.
   - Dependency: define the result vocabulary before changing callers.

2. **Guard shared gauntlet telemetry.**
   - Owner surface: `gauntlet/phase_3_filtering.py` and
     `gauntlet/persistence.py`.
   - Source concern: `HAZ-001` / `CON-002`.
   - Acceptance: two concurrent runs cannot lose dedup history; telemetry
     writes use the same lock/atomic policy as checkpoints, with a concurrency
     regression test.

3. **Guard session and provider state writes.**
   - Owner surface: `session.py`, `providers.py`, shared persistence utility.
   - Source concerns: `HAZ-002`, `HAZ-003`, `CON-007`.
   - Acceptance: interrupted writes leave valid prior state; same-target
     concurrent writes are serialized or explicitly rejected; malformed state
     is reported rather than silently disappearing.

## Wave 2 — remove semantic drift

4. **Unify gauntlet timeout defaults.**
   - Owner surface: `debate.py`, `gauntlet/cli.py`, shared CLI/config helper.
   - Source concern: `FIND-002` / `CON-004`.
   - Acceptance: both entry points expose the same documented default, or the
     difference is explicit in `GauntletConfig` and covered by tests.

5. **Centralize worker-role resolution.**
   - Owner surface: `.claude/hooks/dispatch_check.py`,
     `pipeline_continue.py`, `pipeline_idle_retry.py`, new shared hook helper.
   - Source concern: `duplicated-worker-role-resolution` / `CON-003`.
   - Acceptance: one precedence table drives all three hooks; environment,
     registration, and fallback cases have shared contract tests.

6. **Correct stale runtime comments and transitional labels.**
   - Owner surface: `gauntlet/phase_3_filtering.py`,
     `gauntlet/core_types.py`, `validation_emission.py`.
   - Source concerns: `FIND-003`, `FIND-004`, `CON-006`.
   - Acceptance: comments identify the live clustering/telemetry path and the
     validation handlers; a future agent cannot infer that active commands are
     skeleton-only.

## Wave 3 — reduce structural coupling

7. **Define one transport adapter contract.**
   - Owner surface: `models.py`, `gauntlet/model_dispatch.py`, token tracking.
   - Source concern: `FIND-006` / `CON-009`.
   - Acceptance: CLI/LiteLLM routing and usage accounting have one transport
     implementation with policy-specific callers.

8. **Normalize package layout and imports.**
   - Owner surface: `pyproject.toml`, root symlink, `scripts/__init__.py`,
     path-mutating modules, duplicate prompt module names.
   - Source concern: `FIND-001` / `CON-005`.
   - Acceptance: installed and source checkouts resolve the same package; direct
     module execution does not depend on mutable `sys.path` ordering.

9. **Split `run_gauntlet()` coordination from phase policy.**
   - Owner surface: `gauntlet/orchestrator.py` and persistence/metrics helpers.
   - Source concern: `FIND-007` / `CON-010`.
   - Acceptance: phase order, resume/checkpoint behavior, and result assembly
     retain tests while each responsibility has a bounded entry point.

## Sequencing rule

Wave 1 precedes any refactor that changes result or persistence shapes. Wave 2
can proceed independently after the gate contracts are explicit. Wave 3 should
follow only after the existing CLI, gauntlet, and hook contract tests pass.
