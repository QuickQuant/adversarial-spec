# Actionable Concerns: adversarial-spec

> Refreshed by mapcodebase on 2026-07-19 at `ef18c66`.
> Fix-first rollup over hazards, patterns, and findings. No source changes are
> implied by this document.

## Top priorities

### CON-001: A failed final-boss review can be emitted as PASS

- **Severity:** error | **Component:** gauntlet
- **Why:** The repeated phase fallback pattern ends in
  `FinalBossVerdict.PASS` after an exception, making review unavailability
  success-shaped.
- **Do:** Introduce a typed failed-review outcome and make the final gate
  refuse promotion on that outcome.
- **Sources:** `duplicated-gauntlet-model-error-fallbacks`,
  `phase_7_final_boss.py:239-249`

### CON-002: Dedup history is a read-modify-write race

- **Severity:** medium | **Component:** gauntlet-persistence
- **Why:** Independent gauntlet invocations can read the same
  `.adversarial-spec-gauntlet/dedup-stats.json`, append in memory, and overwrite
  one another; this path does not use the locked atomic writer used by the
  checkpoint layer.
- **Do:** Route dedup telemetry through the persistence writer or use a locked
  append/merge protocol and test concurrent invocations.
- **Sources:** `HAZ-001`, `phase_3_filtering.py:197-233`,
  `orchestrator.py:566`

### CON-003: Role detection has three independently drifting policies

- **Severity:** warning | **Component:** harness-hooks
- **Why:** Three pipeline hooks duplicate role constants, registration scans,
  environment precedence, and fallbacks; dispatch has extra Codex logic.
- **Do:** Centralize role resolution in a shared hook helper and add precedence
  contract tests.
- **Sources:** `duplicated-worker-role-resolution`,
  `dispatch_check.py:18-83`, `pipeline_continue.py:21-67`,
  `pipeline_idle_retry.py:24-70`

### CON-004: Two gauntlet CLIs silently choose different deadlines

- **Severity:** warning | **Component:** debate-engine / gauntlet
- **Why:** `debate.py` defaults to 1200 seconds while `gauntlet/cli.py`
  defaults to 1800 seconds for the same broad workflow.
- **Do:** Share one timeout argument/default contract or document an explicit
  policy difference and test both entry points.
- **Sources:** `FIND-002`, `debate.py:401-404`, `gauntlet/cli.py:64-69`

### CON-005: Source imports depend on a symlink and mutable import order

- **Severity:** warning | **Component:** infrastructure / models
- **Why:** Package discovery, root symlink exposure, `sys.path.insert`, and two
  same-named prompt modules make direct script/module execution sensitive to
  import order.
- **Do:** Normalize package layout and use package-qualified imports before
  removing the bootstrap paths.
- **Sources:** `FIND-001`, `pyproject.toml:42-50`,
  `scripts/__init__.py:8-10`, `scripts/prompts.py`, `gauntlet/prompts.py`

### CON-006: Runtime comments disagree with the active telemetry and validation paths

- **Severity:** warning | **Component:** gauntlet / validation-emission
- **Why:** Phase 3 comments say clustering was removed while the orchestrator
  calls it; validation-emission comments still describe concrete handlers as
  skeleton replacements.
- **Do:** Update comments and add source-level checks for the authoritative
  telemetry/handler paths so future agents do not infer the wrong architecture.
- **Sources:** `FIND-003`, `FIND-004`, `phase_3_filtering.py:1-5`,
  `orchestrator.py:520-566`, `validation_emission.py:3236-3252`

## Priority: later

### CON-007: Session and provider files bypass shared persistence guarantees

- **Severity:** medium | **Component:** session / providers
- **Why:** Session snapshots/checkpoints and global/profile config writes use
  direct `Path.write_text()` without the lock/atomic protocol used by gauntlet
  persistence and validation ledgers.
- **Do:** Decide whether concurrent writers are supported; if yes, adopt a
  shared locked atomic writer, otherwise enforce single-writer ownership and
  surface conflicts.
- **Sources:** `HAZ-002`, `HAZ-003`, `session.py:45-133`,
  `providers.py:136-139,242-247`

### CON-008: Session discovery silently hides corrupt records

- **Severity:** warning | **Component:** session
- **Why:** `list_sessions()` catches every exception and returns an incomplete
  list without diagnostics.
- **Do:** Distinguish expected corrupt-file handling from programming errors and
  report/quarantine skipped records.
- **Sources:** `FIND-005`, `session.py:72-85`

### CON-009: Model transport plumbing is duplicated across layers

- **Severity:** warning | **Component:** models / gauntlet
- **Why:** General and gauntlet model adapters independently branch between CLI
  and LiteLLM paths, allowing defaults and failure behavior to diverge.
- **Do:** Share transport adapters while keeping orchestration policy at the
  caller.
- **Sources:** `FIND-006`, `models.py:298-1077`,
  `gauntlet/model_dispatch.py:64-143`

### CON-010: `run_gauntlet()` is the coupling hub for phase and persistence policy

- **Severity:** warning | **Component:** gauntlet
- **Why:** One function owns phase sequencing, resume, checkpoints, metrics,
  stats, medals, process-global input behavior, and result assembly.
- **Do:** Extract a phase coordinator and isolate persistence/metrics policy.
- **Sources:** `FIND-007`, `orchestrator.py:205-980`

## Verification Debt

No open boundary verification items remain from this run. Boundary tables were
checked against the active adapters and consumers at `ef18c66`; the five
delegated discovery explorers timing out is recorded as run provenance and
freshness caution, not as a claim about a runtime boundary.
