# Architecture Findings

> Generated: 2026-03-21 | Git: 12c5d3f | Target: /home/jason/PycharmProjects/adversarial-spec
> Skill version: 2.6 | Model: claude-opus-4-6
>
> Opinionated suggestions based on full codebase analysis.
> Validate these with `/gemini-bundle` or `/adversarial-spec`.

## Findings

### FIND-001: scope.py is dead code (606 lines, imported by nothing)
- **Category:** dead-code
- **Severity:** warning
- **Confidence:** high
- **Component:** debate-engine
- **Files:**
  - `skills/adversarial-spec/scripts/scope.py`
- **Observation:** scope.py defines ScopeDiscovery, DiscoveryType, DiscoveryPriority, and related functions for scope management. It is 606 lines but not imported by any other module in the codebase.
- **Suggestion:** Either integrate into the debate workflow or delete it. Dead code creates confusion about what's active.
- **Evidence:** `grep -r "import.*scope\|from.*scope" scripts/` returns zero results (excluding tests).

### FIND-002: (RESOLVED) gauntlet.py monolith successfully extracted into package
- **Category:** complexity
- **Severity:** info
- **Confidence:** high
- **Component:** gauntlet
- **Files:**
  - `skills/adversarial-spec/scripts/gauntlet/` (16 modules)
- **Observation:** The 4087-line gauntlet.py monolith has been successfully extracted into a 16-module `gauntlet/` package. `gauntlet_monolith.py` remains as a 12-line shim. The extraction was driven by the gauntlet-refactor-quota-burn spec.
- **Suggestion:** None — this finding is resolved. Consider deleting `gauntlet_monolith.py` once all external references are updated.
- **Evidence:** 16 modules in gauntlet/, shim at gauntlet_monolith.py, 377+ tests passing.

### FIND-003: cost_tracker now has threading.Lock (GIL concern addressed)
- **Category:** performance
- **Severity:** info
- **Confidence:** high
- **Component:** models
- **Files:**
  - `skills/adversarial-spec/scripts/models.py:204`
- **Observation:** The CostTracker singleton now uses a threading.Lock for thread-safe accumulation. This addresses the previous concern about GIL removal in Python 3.14+.
- **Suggestion:** None — resolved.
- **Evidence:** CostTracker.add() uses self._lock (threading.Lock).

### FIND-004: No file locking on .claude/tasks.json (MCP server + TaskManager concurrent access)
- **Category:** error-handling
- **Severity:** warning
- **Confidence:** medium
- **Component:** mcp-tasks
- **Files:**
  - `mcp_tasks/server.py`
  - `skills/adversarial-spec/scripts/task_manager.py`
- **Observation:** Both MCP server and Python TaskManager read/write `.claude/tasks.json` without file locking. If a Claude Code agent calls MCP TaskUpdate while debate.py's TaskManager is writing, data loss is possible.
- **Suggestion:** Add file locking (e.g., `filelock` which is already a dependency) to load_tasks/save_tasks in both files.
- **Evidence:** load_tasks()/save_tasks() use plain path.read_text()/path.write_text() with no locking.

### FIND-005: Execution planner deprecation incomplete — exports still pending cleanup
- **Category:** dead-code
- **Severity:** info
- **Confidence:** high
- **Component:** execution-planner
- **Files:**
  - `execution_planner/__init__.py`
- **Observation:** The execution planner deprecation (Feb 2026) deleted dead modules but `__init__.py` still exports 5 symbols. Some (GauntletReport, LinkedConcern) may no longer be needed externally.
- **Suggestion:** Audit which exports are still imported elsewhere. Remove unused re-exports.
- **Evidence:** Deprecation spec mentions Phase 3 (clean up exports) as PENDING.

### FIND-006: knowledge_service.py exists but is not wired into any flow
- **Category:** dead-code
- **Severity:** info
- **Confidence:** high
- **Component:** pre-gauntlet
- **Files:**
  - `skills/adversarial-spec/scripts/integrations/knowledge_service.py`
- **Observation:** knowledge_service.py implements a caching utility but is not called from any active code path.
- **Suggestion:** Either wire into the pre-gauntlet flow or remove.
- **Evidence:** Only references are definition file and `__init__.py` re-export.

### FIND-007: (RESOLVED) Model name validation now implemented
- **Category:** security
- **Severity:** info
- **Confidence:** high
- **Component:** gauntlet
- **Files:**
  - `skills/adversarial-spec/scripts/gauntlet/model_dispatch.py:39-53`
- **Observation:** `_validate_model_name()` validates model names against a blocklist regex that rejects shell metacharacters (;|&$`), whitespace, control characters, and flag-like patterns (--). This addresses the previous defense-in-depth concern.
- **Suggestion:** None — resolved.
- **Evidence:** `_MODEL_NAME_BLOCKLIST = re.compile(r'[;|&$`\s]|[\x00-\x1f]|--|^-')` at model_dispatch.py:39.

### FIND-008: Two gauntlet CLI entry points with divergent flag names
- **Category:** idiomatic
- **Severity:** warning
- **Confidence:** high
- **Component:** gauntlet
- **Files:**
  - `skills/adversarial-spec/scripts/debate.py`
  - `skills/adversarial-spec/scripts/gauntlet/cli.py`
- **Observation:** debate.py uses `--codex-reasoning` for attack reasoning effort and `--gauntlet-resume` for resume. gauntlet/cli.py uses `--attack-codex-reasoning` and `--resume`. This is by design (spec R2-12), but creates confusion for users.
- **Suggestion:** Document the flag mapping clearly in --help text. Consider adding `--codex-reasoning` as an alias in cli.py.
- **Evidence:** debate.py add_gauntlet_arguments() vs gauntlet/cli.py parser.

---

## Summary
- **Total findings:** 8
- **By severity:** info: 5 | warning: 3 | error: 0
- **Top concern:** FIND-004 (tasks.json no locking) — latent concurrent access issue. FIND-008 (flag divergence) is a usability concern.
- **Confidence breakdown:** high: 7 | medium: 1 | low: 0
