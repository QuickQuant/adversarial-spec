# Architecture Findings

> Generated: 2026-03-22 | Git: c3b5f8c | Target: /home/jason/PycharmProjects/adversarial-spec
> Skill version: 3.0 | Model: claude-opus-4-6
>
> Opinionated suggestions based on full codebase analysis.
> Validate these with `/gemini-bundle` or `/adversarial-spec`.

## Findings

### FIND-001: ~~scope.py is dead code (606 lines, imported by nothing)~~ INVALIDATED

> **Status: INVALIDATED** (2026-03-23)
> **Rationale:** scope.py has active tests in `test_adversaries.py` (scope_guidelines validation). The grep evidence was incomplete — it missed test imports.

- **Category:** dead-code
- **Severity:** ~~warning~~ invalidated
- **Confidence:** ~~high~~ invalidated
- **Component:** debate-engine
- **Files:**
  - `skills/adversarial-spec/scripts/scope.py`
- **Observation:** ~~scope.py defines ScopeDiscovery, ScopeReport, and related functions but is not imported anywhere in the codebase~~
- **Suggestion:** ~~Integrate into debate workflow or delete. 606 lines of unmaintained code accumulates drift.~~
- **Evidence:** ~~grep for 'import.*scope' returns zero results across all scripts~~ Evidence was incorrect

---

### FIND-002: ~~knowledge_service.py implemented but not wired~~ INVALIDATED

> **Status: INVALIDATED** (2026-03-23)
> **Rationale:** knowledge_service.py is imported by `pre_gauntlet/discovery.py` and exported from `integrations/__init__.py`. The evidence missed the discovery.py import.

- **Category:** dead-code
- **Severity:** ~~warning~~ invalidated
- **Confidence:** ~~high~~ invalidated
- **Component:** pre-gauntlet
- **Files:**
  - `skills/adversarial-spec/scripts/integrations/knowledge_service.py`
- **Observation:** ~~Full caching implementation (KnowledgeService class) exists in integrations/ but no code path imports or calls it~~
- **Suggestion:** ~~Wire into pre-gauntlet flow or remove~~
- **Evidence:** ~~Only references are definition file and __init__.py re-export. No call sites.~~ Evidence was incorrect

---

### FIND-003: No file locking on .claude/tasks.json
- **Category:** error-handling
- **Severity:** warning
- **Confidence:** medium
- **Component:** mcp-tasks
- **Files:**
  - `mcp_tasks/server.py`
  - `skills/adversarial-spec/scripts/task_manager.py`
- **Observation:** MCP server and TaskManager both read/write tasks.json via plain read_text()/write_text() without locking. filelock is already a dependency.
- **Suggestion:** Add FileLock wrapper to load_tasks/save_tasks, consistent with gauntlet/persistence.py pattern
- **Evidence:** load_tasks()/save_tasks() use plain path.read_text()/write_text() with no locking

---

### FIND-004: Pydantic used but not in pyproject.toml
- **Category:** idiomatic
- **Severity:** warning
- **Confidence:** high
- **Component:** pre-gauntlet
- **Files:**
  - `skills/adversarial-spec/scripts/pre_gauntlet/models.py`
- **Observation:** pre_gauntlet/models.py uses Pydantic BaseModel for GitPosition, SystemState, Concern. Pydantic is not listed in pyproject.toml dependencies.
- **Suggestion:** Add pydantic to pyproject.toml dependencies, or convert to standard dataclasses for consistency with the rest of the codebase
- **Evidence:** `from pydantic import BaseModel` in pre_gauntlet/models.py, absent from pyproject.toml [project.dependencies]

---

### FIND-005: Two gauntlet CLIs with divergent flag names
- **Category:** idiomatic
- **Severity:** warning
- **Confidence:** high
- **Component:** gauntlet
- **Files:**
  - `skills/adversarial-spec/scripts/debate.py`
  - `skills/adversarial-spec/scripts/gauntlet/cli.py`
- **Observation:** debate.py uses --codex-reasoning/--gauntlet-resume, cli.py uses --attack-codex-reasoning/--resume for the same features. No aliases bridge the gap.
- **Suggestion:** Document flag mapping in --help text, or add aliases for consistency
- **Evidence:** debate.py add_gauntlet_arguments() vs gauntlet/cli.py argparse setup

---

### FIND-006: Execution planner deprecation Phase 3 still pending
- **Category:** dead-code
- **Severity:** info
- **Confidence:** high
- **Component:** execution-planner
- **Files:**
  - `execution_planner/__init__.py`
- **Observation:** Deprecation spec lists Phase 3 (cleanup unused exports) as PENDING. __init__.py still exports types that may not be used externally.
- **Suggestion:** Audit which exports are still imported externally, remove unused ones
- **Evidence:** Deprecation spec at .adversarial-spec/specs/execution-planner-deprecation.md lists Phase 3 as PENDING

---

### FIND-007: ~~gauntlet_monolith.py shim still exists~~ INVALIDATED

> **Status: INVALIDATED** (2026-03-23)
> **Rationale:** gauntlet_monolith.py is an intentional backward-compatibility shim. It is referenced by legacy entry points and should be preserved.

- **Category:** dead-code
- **Severity:** ~~info~~ invalidated
- **Confidence:** ~~high~~ invalidated
- **Component:** gauntlet
- **Files:**
  - `skills/adversarial-spec/scripts/gauntlet_monolith.py`
- **Observation:** ~~12-line shim that delegates to gauntlet/cli.py:main(). All references should be cleared by now.~~
- **Suggestion:** ~~Verify no external references, then delete~~
- **Evidence:** ~~gauntlet_monolith.py is 12 lines, just imports and delegates~~ Shim is intentional

---

### FIND-008: FileLock has no timeout on checkpoint files
- **Category:** error-handling
- **Severity:** info
- **Confidence:** medium
- **Component:** gauntlet
- **Files:**
  - `skills/adversarial-spec/scripts/gauntlet/persistence.py`
- **Observation:** FileLock(path) uses default blocking=True with no timeout. If a process crashes holding the lock, the next process blocks indefinitely.
- **Suggestion:** Add a timeout (e.g., 30s) to FileLock acquisition, with clear error message on timeout
- **Evidence:** _lock_for(path) creates FileLock without timeout parameter

---

### FIND-009: Session files have no file locking
- **Category:** error-handling
- **Severity:** info
- **Confidence:** medium
- **Component:** session
- **Files:**
  - `skills/adversarial-spec/scripts/session.py`
- **Observation:** SessionState.save() writes to ~/.config/adversarial-spec/sessions/{id}.json without any file locking. Two concurrent debates on the same session could corrupt state.
- **Suggestion:** Low risk (single-user assumption) but could add FileLock for safety
- **Evidence:** session.py save() uses plain write_text() with no locking mechanism

---

## Summary
- **Total findings:** 9 (6 valid, 3 invalidated)
- **By severity:** info: 2 | warning: 3 | invalidated: 3 | error: 0
- **Top concern:** FIND-003 (tasks.json no locking) — the locking issue is a real bug for concurrent agent access
- **Confidence breakdown:** high: 4 | medium: 3 | invalidated: 3 | low: 0
