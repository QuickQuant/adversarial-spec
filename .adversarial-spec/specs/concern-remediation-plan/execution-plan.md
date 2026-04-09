# Execution Plan: Architecture Concern Remediation

## Summary
- Tasks: 8 (S: 3, M: 4, L: 1)
- Workstreams: 1 (sequential — each step builds on the previous)
- Gauntlet concerns addressed: N/A (gauntlet skipped — spec is a remediation plan, not a feature spec)
- Estimated effort: ~2 hours

## Execution Sequence

```
T0 (CON-002) → T1 (CON-006) → T2 (CON-005) → T3 (CON-001) → T4 (CON-004) → T5 (CON-003) → T6 (CON-007) → T7 (CON-008) → Post
                                                                                    ↑
                                                                               T5 and T6 both
                                                                               touch phase_2_synthesis.py
                                                                               (fresh read between)
```

## Tasks

### Task 0: Correct CON-002 False Positive
- **Effort:** S
- **Strategy:** no tests (documentation-only)
- **Spec refs:** Step 0
- **Dependencies:** None (do first — establishes correct baseline)
- **Acceptance criteria:**
  - [ ] CON-002 section in `concerns.md` marked `INVALIDATED` with rationale — original text preserved
  - [ ] FIND-001, FIND-002, FIND-007 marked `INVALIDATED` in `findings.md` — original text preserved
  - [ ] `manifest.json` has `"status": "invalidated"` on CON-002 and related findings
  - [ ] `manifest.json` has `concerns_identified: 8` (total) AND `concerns_identified_valid: 7`
  - [ ] `manifest.json` has `warnings[]` entry with code `ARCH_INVALIDATION`
  - [ ] `primer.md` "Top Actionable Concerns" no longer lists CON-002

---

### Task 1: Declare Pydantic Dependency (CON-006)
- **Effort:** S
- **Strategy:** no tests (config-only)
- **Spec refs:** Step 1
- **Dependencies:** T0
- **Acceptance criteria:**
  - [ ] `pyproject.toml` has `"pydantic>=2.0"` in `dependencies`
  - [ ] `uv sync` succeeds
  - [ ] `uv run python -c "import pydantic; print(pydantic.VERSION)"` prints version

---

### Task 2: Fix Test Import Infrastructure (CON-005)
- **Effort:** M
- **Strategy:** test-after (run full suite to verify)
- **Spec refs:** Step 2
- **Dependencies:** T1 (pyproject.toml must be stable)
- **Acceptance criteria:**
  - [ ] `pyproject.toml` has `pythonpath = ["skills/adversarial-spec/scripts"]` in `[tool.pytest.ini_options]`
  - [ ] Zero test files contain `sys.path.insert(0, str(Path(__file__).parent.parent))`
  - [ ] `import sys` removed from files where it was ONLY used for sys.path hack
  - [ ] `from pathlib import Path` removed from files where it was ONLY used for sys.path hack
  - [ ] Each file checked individually (not bulk-removed)
  - [ ] `uv run pytest` — all tests pass
- **Implementation checklist:**
  - Before removing imports from each file, grep for other uses of `sys` and `Path` in that file

---

### Task 3: Canonical Mutation Path with FileLock (CON-001)
- **Effort:** M
- **Strategy:** test-first — highest real-world risk (data loss in multi-agent workflows)
- **Spec refs:** Step 3
- **Dependencies:** T2 (test infra must work before writing new tests)
- **Acceptance criteria:**
  - [ ] `mcp_tasks/server.py` has `_mutate_tasks()` helper with 10s lock timeout
  - [ ] `mcp_tasks/server.py` has `_load_tasks_unlocked()` and `_save_tasks_unlocked()` (private)
  - [ ] `_save_tasks_unlocked()` uses atomic write: temp file + `os.replace`
  - [ ] All mutating operations in `server.py` route through `_mutate_tasks()`
  - [ ] No public `load_tasks()`/`save_tasks()` pair remains (prevents TOCTOU bypass)
  - [ ] Lock timeout raises `RuntimeError` with `TASK_STORE_BUSY` message
  - [ ] Corrupt JSON raises error with `TASK_STORE_CORRUPT` message
  - [ ] Cross-reference comment points to `task_manager.py` parallel implementation
  - [ ] `task_manager.py` has identical pattern with cross-reference comment to `server.py`
  - [ ] `uv run pytest` passes
  - [ ] `.claude/tasks.json.lock` sidecar appears after a mutation
- **Test cases (write first):**
  - Test that `_mutate_tasks` holds lock across full read-modify-write
  - Test that corrupt JSON raises `TASK_STORE_CORRUPT`
  - Test that atomic write doesn't leave partial files on crash (write to temp, replace)

---

### Task 4: Fix Silent Error Swallowing (CON-004)
- **Effort:** M
- **Strategy:** test-first — bug fixes that change error behavior
- **Spec refs:** Step 4
- **Dependencies:** T3
- **Acceptance criteria:**
  - [ ] `_PROGRAMMING_BUGS = (TypeError, NameError, AttributeError, ImportError, SyntaxError, AssertionError)` — NO ValueError, NO KeyError
  - [ ] `phase_3_filtering.py:139-140` no longer silently catches all exceptions
  - [ ] All 6 phase files have `_PROGRAMMING_BUGS` re-raise guard in their `except Exception` blocks
  - [ ] Existing fallback behavior (log + safe default) preserved for non-programming-bug exceptions
  - [ ] Warning messages written to `sys.stderr` (not stdout)
  - [ ] `uv run pytest` passes
- **Files to modify:**
  - `phase_1_attacks.py:158`
  - `phase_3_filtering.py:139-140` (critical — currently `except Exception: pass`)
  - `phase_4_evaluation.py:128,209,226` (keep existing JSONDecodeError-specific catch at 126)
  - `phase_5_rebuttals.py:108`
  - `phase_6_adjudication.py:93`
- **Test cases (write first):**
  - Test that `TypeError` in a phase handler raises (not swallowed)
  - Test that `litellm`-style errors (simulated) are caught and produce stderr warning
  - Test that `ValueError` from malformed JSON is caught (not re-raised)

---

### Task 5: Replace Phase 2 Inline Dispatch (CON-003)
- **Effort:** M
- **Strategy:** test-after (refactor, existing tests should catch regressions)
- **Spec refs:** Step 5
- **Dependencies:** T4
- **Acceptance criteria:**
  - [ ] Inline CLI routing block (if/elif/else for codex/gemini/claude/litellm) removed from `phase_2_synthesis.py`
  - [ ] Replaced with single `call_model()` call
  - [ ] System prompt text is EXACTLY the existing Phase 2 literal (verified by reading source first)
  - [ ] Unused imports removed: `call_codex_model`, `call_gemini_cli_model`, `call_claude_cli_model`, `try: from litellm import completion`
  - [ ] `call_model` and `cost_tracker` imports preserved
  - [ ] `uv run pytest` passes — specifically `test_gauntlet_synthesis_extract.py`
- **Implementation note:** Read the current system_prompt from source BEFORE editing. Do NOT use the hardcoded string from the spec.

---

### Task 6: Extract Gauntlet Prompts (CON-007)
- **Effort:** L
- **Strategy:** test-after (behavioral equivalence — diff rendered prompts)
- **Spec refs:** Step 6
- **Dependencies:** T5 (both touch `phase_2_synthesis.py` — fresh read required)
- **Acceptance criteria:**
  - [ ] New file `gauntlet/prompts.py` created with 9 constants
  - [ ] All 9 constants listed in spec table are present
  - [ ] `SYNTHESIS_SYSTEM_PROMPT` included (was missing in v1/v2)
  - [ ] f-strings converted to `.format()` templates where needed
  - [ ] Each phase file imports from `gauntlet.prompts` instead of defining inline
  - [ ] Rendered prompt output is byte-for-byte equivalent for representative inputs
  - [ ] No inline prompt strings remain in phase files (except non-gauntlet prompts)
  - [ ] `uv run pytest` passes
- **Verification:** Diff rendered prompts before/after extraction to confirm equivalence

---

### Task 7: CLI Flag Aliases (CON-008)
- **Effort:** S
- **Strategy:** test-after (additive only, low risk)
- **Spec refs:** Step 7
- **Dependencies:** T6
- **Acceptance criteria:**
  - [ ] `--adversaries` alias for `--gauntlet-adversaries` works
  - [ ] `--adversary-model` alias for `--gauntlet-model` works
  - [ ] `--attack-models` alias for `--gauntlet-attack-models` works
  - [ ] `--eval-model` alias for `--gauntlet-frontier` works
  - [ ] `--attack-codex-reasoning` alias for `--codex-reasoning` works
  - [ ] `"minimal"` added to `--codex-reasoning` choices
  - [ ] All existing flags still work (no breaking changes)
  - [ ] Help text shows canonical flag first, alias second
  - [ ] `--resume` NOT aliased (different semantics between CLIs)
  - [ ] `uv run pytest` passes
  - [ ] `uv run python skills/adversarial-spec/scripts/debate.py gauntlet --help` shows aliases

---

## Post-Implementation Checklist

- [ ] `uv run pytest` — all tests pass
- [ ] `uvx ruff check --fix --unsafe-fixes` — clean
- [ ] Back up deployed skill: `cp -r ~/.claude/skills/adversarial-spec/ /tmp/adversarial-spec-backup-$(date +%Y%m%d%H%M)/`
- [ ] Deploy: `rsync -a --delete skills/adversarial-spec/ ~/.claude/skills/adversarial-spec/`
- [ ] Smoke test (source): `uv run python skills/adversarial-spec/scripts/debate.py gauntlet --help`
- [ ] Smoke test (deployed): `uv run python ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet --help`
- [ ] `/mapcodebase --update` — refresh architecture docs with resolved concerns

## Test Strategy Summary

| Task | Strategy | Reason |
|------|----------|--------|
| T0: CON-002 correction | none | Documentation-only |
| T1: Pydantic dep | none | Config-only |
| T2: Test imports | test-after | Run full suite to verify |
| T3: FileLock | test-first | Highest risk — data loss in multi-agent |
| T4: Error swallowing | test-first | Bug fix changing error behavior |
| T5: Phase 2 dispatch | test-after | Refactor with existing test coverage |
| T6: Prompt extraction | test-after | Behavioral equivalence diff |
| T7: CLI aliases | test-after | Additive, low risk |

## Rollback

Per-task: `git revert <commit>` (each step = one commit).

Full rollback: Revert all commits + restore `/tmp/adversarial-spec-backup-*` + re-run smoke tests.
