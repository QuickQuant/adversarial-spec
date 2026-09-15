# Actionable Concerns: adversarial-spec

> Refreshed by mapcodebase on 2026-07-20 at `2433efa`.
> Fix-first rollup over verified hazards, patterns, and findings. No source changes are implied.

## Top priorities

### CON-001: A failed Final Boss review can be emitted as PASS

- **Severity:** error | **Component:** gauntlet
- **Why:** The catch-all exception path returns `FinalBossVerdict.PASS`, making review unavailability success-shaped.
- **Do:** Introduce a typed failed-review outcome and make the final gate refuse promotion on that outcome.
- **Sources:** `FIND-001`, `duplicated-gauntlet-model-error-fallbacks`, `phase_7_final_boss.py:239-252`

### CON-002: The canonical phase order rejects its own verification transition

- **Severity:** error | **Component:** skill lifecycle
- **Why:** Resume validation lists eight phases ending in `implementation → complete`, while the active workflow requires Phase 9 Verification before closure.
- **Do:** Publish and test one canonical order including verification.
- **Sources:** `FIND-002`, `HAZARD: canonical-phase-order-mismatch`, `SKILL.md:75-108`, `phases/08-implementation.md:268-277`, `phases/09-verification.md:184-198`

### CON-003: Same-spec gauntlet runs can overwrite sidecars and lose telemetry

- **Severity:** error | **Component:** gauntlet persistence
- **Why:** Raw responses, cluster reports, and dedup stats use direct writes keyed by spec hash without a run-scoped lock. Concurrent runs can overwrite recovery artifacts or stats.
- **Do:** Isolate by run ID or route all sidecars through a locking/merge protocol; add a two-run concurrency regression test.
- **Sources:** `HAZARD: gauntlet-sidecar-overwrite`, `orchestrator.py:399-403,533-556`, `phase_3_filtering.py:211-233`

### CON-004: Session state and round artifacts have no single-writer guarantee

- **Severity:** medium | **Component:** debate/session
- **Why:** Session JSON, checkpoint Markdown, critique JSON, and partial model outputs are direct writes; concurrent resumes can overwrite the latest state or history.
- **Do:** Declare single-writer ownership or use a lock plus atomic replace and conflict detection.
- **Sources:** `HAZARD: session-state-concurrent-write`, `session.py:46-134`, `models.py:1163-1199`

### CON-005: Role resolution has three independently drifting implementations

- **Severity:** warning | **Component:** harness hooks
- **Why:** Three hooks repeat environment, registration, and host-marker role detection; only dispatch includes extra Codex fallback.
- **Do:** Centralize role resolution and add one precedence contract test suite.
- **Sources:** `duplicated-worker-role-resolution`, `dispatch_check.py:18-83`, `pipeline_continue.py:21-67`, `pipeline_idle_retry.py:24-70`

### CON-006: Two gauntlet entrypoints silently choose different deadlines

- **Severity:** warning | **Component:** debate / gauntlet
- **Why:** Debate defaults to 1200 seconds while standalone gauntlet defaults to 1800 seconds for the same class of model call.
- **Do:** Share the default or make two policies explicit and test both surfaces.
- **Sources:** `FIND-003`, `debate.py:398-410`, `gauntlet/cli.py:60-72`

## Priority: later

### CON-007: Session discovery silently hides corrupt records

- **Severity:** medium | **Component:** session
- **Why:** `list_sessions()` catches every exception and omits the record, hiding corruption or read failures from the operator.
- **Do:** Separate expected parse/OS failure handling from programmer errors and report skipped records.
- **Sources:** `FIND-006`, `session.py:72-85`

### CON-008: Comments and fallback labels contradict active behavior

- **Severity:** warning | **Component:** gauntlet / validation emission
- **Why:** Phase 3 says clustering was removed while the live path clusters; validation emission labels all concrete handlers as skeleton replacements.
- **Do:** Correct comments and add a narrow source-level regression assertion around the active surfaces.
- **Sources:** `FIND-004`, `FIND-005`, `phase_3_filtering.py:1-5`, `orchestrator.py:512-575`, `validation_emission.py:1419-1432,3236-3252`

### CON-009: Model transport plumbing is duplicated across layers

- **Severity:** warning | **Component:** models / gauntlet
- **Why:** General and gauntlet model adapters independently branch between CLI
  and LiteLLM paths, allowing defaults and failure behavior to diverge.
- **Do:** Share transport adapters while keeping orchestration policy at the
  caller.
- **Sources:** `FIND-007`, `models.py:298-1077`,
  `gauntlet/model_dispatch.py:64-143`

### CON-010: Path bootstrap imports remain a source-layout coupling

- **Severity:** warning | **Component:** plan analysis / runtime bootstrap
- **Why:** Several modules mutate `sys.path` to reach skill scripts. The root symlink makes installed entrypoints work, but these direct-source bootstraps still couple imports to repository layout.
- **Do:** Move toward package-qualified imports behind regression tests; retain the verified symlink bridge until every caller is migrated.
- **Sources:** `execution_planner/gauntlet_concerns.py:17-26`, `scripts/__init__.py:8-10`, `FIND-007`

### CON-011: Python 3.10 pre-gauntlet configuration can silently fall back to defaults

- **Severity:** warning | **Component:** pre-gauntlet
- **Why:** `tomli` is not declared although Python 3.10 is supported; its missing fallback returns a default compatibility configuration.
- **Do:** Add the conditional dependency or report a hard, actionable configuration-load error.
- **Sources:** `FIND-008`, `pyproject.toml:9-35`, `pre_gauntlet/orchestrator.py:253-280`

## Verification Debt

`VER-001` — **not modeled:** the external Telegram server-side request validator. The client encoding and client response handling are source-verified; server behavior is outside this repository. See `telegram_bot.py:47-70,89,197-211`.

`VER-002` — **not modeled:** the external hook host's interpretation of a guard decision. Registration, stdin parsing, and emitted decision JSON are source-verified; host enforcement is outside this repository. See `.claude/settings.json:107` and `fizzy_payload_guard.py:51-60,86-147`.

`VER-003` — **documented consumption:** no in-repository program parses validation CLI stdout. The execution workflow's `status == "ok"` and no-issues advance rule is source-verified. See `phases/07-execution.md:897,937` and `validation_emission.py:200-220,3418-3462`.
