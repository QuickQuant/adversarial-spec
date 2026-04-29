# Architecture Findings

> Generated: 2026-04-16 | Git: 9ca3ccd | Target: /home/jason/PycharmProjects/adversarial-spec
> Skill version: 3.6 | Model: claude-opus-4-6
>
> Opinionated suggestions based on full codebase analysis.
> Validate these with `/gemini-bundle` or `/adversarial-spec`.

## Findings

### FIND-001: Triple litellm completion() pathway
- **Category:** duplication
- **Severity:** warning
- **Confidence:** high
- **Component:** model-dispatch
- **Files:**
  - `skills/adversarial-spec/scripts/models.py`
  - `skills/adversarial-spec/scripts/gauntlet/model_dispatch.py`
  - `skills/adversarial-spec/scripts/debate.py`
- **Observation:** litellm.completion() is independently imported and called in 3 files with different defaults (temperature 0.3 vs 0.7, max_tokens 4000 vs 4096 vs 8000).
- **Suggestion:** Create a single `_call_litellm()` in model_dispatch.py with explicit parameters.
- **Evidence:** debate.py:66, models.py:21, model_dispatch.py:25 all import completion independently.

---

### FIND-002: Dead clustering code in phase_3_filtering.py
- **Category:** dead-code
- **Severity:** warning
- **Confidence:** high
- **Component:** gauntlet-pipeline
- **Files:**
  - `skills/adversarial-spec/scripts/gauntlet/phase_3_filtering.py`
- **Observation:** ~80 lines of dead clustering code with inline comment "dead code kept for reference." Contradicts the prompts centralization effort.
- **Suggestion:** Delete. It's in git history.
- **Evidence:** phase_3_filtering.py:242 "is dead code kept for reference"

---

### FIND-003: scope.py (606 lines) never imported
- **Category:** dead-code
- **Severity:** info
- **Confidence:** high
- **Component:** scope-module
- **Files:**
  - `skills/adversarial-spec/scripts/scope.py`
- **Observation:** Defines ScopeDiscovery, MiniSpec, ScopeCheckpoint, DiscoveryType. Zero importers. Planned but unintegrated.
- **Suggestion:** Track as planned feature or delete.
- **Evidence:** Grep for scope imports returns 0 matches.

---

### FIND-004: Deprecated CLI commands still wired in debate.py
- **Category:** dead-code
- **Severity:** info
- **Confidence:** medium
- **Component:** debate-engine
- **Files:**
  - `skills/adversarial-spec/scripts/debate.py`
- **Observation:** 'execution-plan' and 'export-tasks' CLI actions print deprecation warnings and exit. ~80 lines of dead scaffolding.
- **Suggestion:** Remove from argparse choices, delete handlers.
- **Evidence:** debate.py:591, 978, 787 contain 'DEPRECATED'.

---

### FIND-005: Inline prompts in phases 5 and 7 bypass gauntlet/prompts.py
- **Category:** missing-abstraction
- **Severity:** warning
- **Confidence:** high
- **Component:** gauntlet-pipeline
- **Files:**
  - `skills/adversarial-spec/scripts/gauntlet/phase_5_rebuttals.py`
  - `skills/adversarial-spec/scripts/gauntlet/phase_7_final_boss.py`
- **Observation:** Phase 5 builds a system_prompt inline (line 46). Phase 7 has a 70-line inline user_prompt (lines 127-179). Both bypass the centralized prompts module.
- **Suggestion:** Extract to gauntlet/prompts.py as named constants with {var} placeholders.
- **Evidence:** phase_5_rebuttals.py:46, phase_7_final_boss.py:127 use inline f-strings.

---

### FIND-006: cost_tracker coupling from all phase files to models.py
- **Category:** layer-violation
- **Severity:** warning
- **Confidence:** high
- **Component:** gauntlet-pipeline
- **Files:**
  - All 7 gauntlet/phase_*.py files
- **Observation:** Every phase file imports the global cost_tracker singleton from models.py. This creates a hard coupling and forces 30+ test monkeypatches.
- **Suggestion:** Move cost_tracker.add() into model_dispatch.call_model() so phases never touch cost tracking directly.
- **Evidence:** 7 phase files each do 'from models import cost_tracker'. Tests monkeypatch per-phase.

---

### FIND-007: sys.path.insert in 6 locations
- **Category:** idiomatic
- **Severity:** warning
- **Confidence:** high
- **Component:** infrastructure
- **Files:**
  - `skills/adversarial-spec/scripts/debate.py` (x2)
  - `skills/adversarial-spec/scripts/pre_gauntlet/orchestrator.py`
  - `skills/adversarial-spec/scripts/collectors/system_state.py`
  - `skills/adversarial-spec/scripts/collectors/git_position.py`
  - `skills/adversarial-spec/scripts/extractors/spec_affected_files.py`
- **Observation:** Fragile sys.path manipulation instead of proper package structure.
- **Suggestion:** Configure pyproject.toml packages, use relative imports.
- **Evidence:** 6 sys.path.insert calls across source files.

---

### FIND-008: builtins.input monkey-patching not thread-safe
- **Category:** security
- **Severity:** warning
- **Confidence:** medium
- **Component:** gauntlet-pipeline
- **Files:**
  - `skills/adversarial-spec/scripts/gauntlet/orchestrator.py`
- **Observation:** Unattended mode replaces builtins.input globally. ThreadPoolExecutor threads could call it during the window. KeyboardInterrupt handler may bypass finally-block restore.
- **Suggestion:** Use a GauntletConfig flag checked at call sites instead of monkey-patching.
- **Evidence:** orchestrator.py:278-279 monkey-patches, restored at :864.

---

### FIND-009: Hub file importer counts slightly off in docs
- **Category:** doc-accuracy
- **Severity:** info
- **Confidence:** high
- **Component:** architecture-docs
- **Observation:** adversaries.py actual: 13 importers (doc says 11, >20% off). persistence.py actual: 7 importers (doc says 5, >20% off). Others within tolerance.
- **Suggestion:** Update primer importer counts.
- **Evidence:** Grep-based importer counts.

---

### FIND-010: gauntlet_monolith.py shim has no importers
- **Category:** dead-code
- **Severity:** info
- **Confidence:** medium
- **Component:** gauntlet-pipeline
- **Files:**
  - `skills/adversarial-spec/scripts/gauntlet_monolith.py`
- **Observation:** 13-line shim re-exporting main() and run_gauntlet(). Zero importers found.
- **Suggestion:** Verify no external consumers, then delete.
- **Evidence:** Grep returns 0 functional import matches.

---

### FIND-011: orchestrator.py run_gauntlet() is ~695 lines
- **Category:** complexity
- **Severity:** warning
- **Confidence:** high
- **Component:** gauntlet-pipeline
- **Files:**
  - `skills/adversarial-spec/scripts/gauntlet/orchestrator.py`
- **Observation:** Single function spanning ~695 lines with 30+ locals and 3-level try/except nesting. Mixes phase orchestration with checkpoint, manifest, medal, and stats logic.
- **Suggestion:** Extract a phase-table pattern: (name, function, checkpoint_key) tuples with shared checkpoint/resume logic.
- **Evidence:** run_gauntlet starts around line 170, runs to line 865 in an 865-line file.

---

### FIND-012: Bare except in persistence and session I/O boundaries
- **Category:** error-handling
- **Severity:** warning
- **Confidence:** high
- **Component:** gauntlet-pipeline
- **Files:**
  - `skills/adversarial-spec/scripts/gauntlet/persistence.py`
  - `skills/adversarial-spec/scripts/task_manager.py`
  - `skills/adversarial-spec/scripts/session.py`
- **Observation:** PROGRAMMING_BUGS reraise was implemented in phase files, but persistence/task_manager/session modules still silently swallow write failures.
- **Suggestion:** At minimum log to stderr. Failed checkpoint writes are data integrity issues.
- **Evidence:** persistence.py:143, task_manager.py:167, session.py:83 have bare 'except Exception:'.

---

### FIND-013: Numeric claims in docs verified accurate
- **Category:** doc-accuracy
- **Severity:** info
- **Confidence:** high
- **Component:** architecture-docs
- **Observation:** 9 phase files, 18 gauntlet modules, 1562 lines in debate.py, 1000 lines in models.py — all verified within tolerance.
- **Suggestion:** None — claims are accurate.
- **Evidence:** Direct line counts and file counts.

---

### FIND-014: Two parallel call_model abstractions at different layers
- **Category:** duplication
- **Severity:** info
- **Confidence:** medium
- **Component:** debate-engine
- **Files:**
  - `skills/adversarial-spec/scripts/models.py`
  - `skills/adversarial-spec/scripts/gauntlet/model_dispatch.py`
- **Observation:** models.py:call_single_model() and gauntlet/model_dispatch.py:call_model() both route CLI vs API models independently. CLI-routing logic (prefix checks) is duplicated. This is intentional layering but the litellm fallback path is independently implemented.
- **Suggestion:** Have models.py delegate litellm calls through a shared wrapper.
- **Evidence:** models.py:686 and model_dispatch.py:81 both check model.startswith('codex/').

---

## Summary
- **Total findings:** 14
- **By severity:** info: 5 | warning: 9 | error: 0
- **Top finding:** FIND-001 — Triple litellm completion() pathway with silently divergent defaults
- **Confidence breakdown:** high: 11 | medium: 3 | low: 0
