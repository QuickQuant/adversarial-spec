# Plan: Architecture Concern Remediation (FINAL)

## Context

mapcodebase 3.1 identified 8 actionable concerns (CON-001 through CON-008). Exploration revealed **CON-002 (dead code) is invalid** — all three files (`scope.py`, `knowledge_service.py`, `gauntlet_monolith.py`) are actively used. The underlying findings (FIND-001, FIND-002, FIND-007) were wrong. This plan addresses the 7 valid concerns and corrects the false positive.

## Debate History

- **Round 1** (Codex 5.4 + Gemini 3 Pro): 3 corrections accepted — transaction-scoped lock for CON-001, audit trail for CON-002, kept inverse re-raise for CON-004
- **Round 2**: 7 corrections accepted — canonical `_mutate_tasks()` helper, lock timeout + error contract, additive metrics, narrowed `_PROGRAMMING_BUGS` tuple, added `SYNTHESIS_SYSTEM_PROMPT`, rollback path, Getting Started section
- **Round 3**: 1 correction accepted — `rsync --delete` for deployment. `filelock` dependency concern was moot (already declared). Shared task_io module rejected (separate packages, no shared import path).

## Getting Started

**Prerequisites:** Python 3.14+, `uv`, git checkout of the repo.

**Bootstrap:**
```bash
uv sync
uv run pytest                  # capture baseline — all tests must pass
uv run python -c "import pydantic, filelock; print('deps-ok')"  # verify deps
```

**Workflow per step:** implement one concern → targeted test verification → full `uv run pytest` → commit.

**Time to first task:** Under 10 minutes from clean checkout to baseline verified.

## Execution Order

| Step | Concern | Effort | Why this order |
|------|---------|--------|----------------|
| 0 | CON-002 correction | 5 min | Fix false positive in concerns.md + manifest before other work |
| 1 | CON-006 (pydantic dep) | 2 min | One-line fix, unblocks clean dependency resolution |
| 2 | CON-005 (test infra) | 15 min | Fix test imports before making code changes that need testing |
| 3 | CON-001 (tasks.json locking) | 15 min | Highest real-world risk |
| 4 | CON-004 (error swallowing) | 20 min | Bug fixes, no API changes |
| 5 | CON-003 (phase 2 inline dispatch) | 15 min | Refactor scoped to one file |
| 6 | CON-007 (gauntlet prompts) | 20 min | Readability, no behavioral change |
| 7 | CON-008 (CLI flag aliases) | 10 min | Additive only, lowest risk |

Each step = one commit.

---

## Step 0: Correct CON-002 False Positive (audit trail approach)

**Files:**
- `.architecture/concerns.md` — mark CON-002 as `INVALIDATED` with rationale (do NOT delete the section)
- `.architecture/manifest.json`:
  - Set `"status": "invalidated"` on CON-002 in `concerns[]` with `"invalidation_reason"` field
  - Add `"status": "invalidated"` to FIND-001/FIND-002/FIND-007 in `findings[]`
  - Keep `concerns_identified` as total count (8), add `concerns_identified_valid: 7`
  - Add a `warnings[]` entry: `{"code": "ARCH_INVALIDATION", "message": "CON-002 invalidated — scope.py, knowledge_service.py, gauntlet_monolith.py confirmed active", "created_at": "ISO-8601", "related_ids": ["CON-002", "FIND-001", "FIND-002", "FIND-007"]}`
- `.architecture/findings.md` — mark FIND-001/FIND-002/FIND-007 as `INVALIDATED` with rationale (preserve original text, add status header)
- `.architecture/primer.md` — update "Top Actionable Concerns" section, remove CON-002 from actionable list, note it was invalidated

**Why:** `scope.py` has active tests in `test_adversaries.py` (scope_guidelines validation). `knowledge_service.py` is imported by `pre_gauntlet/discovery.py` and exported from `integrations/__init__.py`. `gauntlet_monolith.py` is an intentional backward-compatibility shim.

**Audit trail rationale:** Preserving invalidated findings prevents future mapcodebase runs from re-reporting the same false positives and documents the investigation for future contributors.

---

## Step 1: CON-006 — Declare Pydantic Dependency

**File:** `pyproject.toml`
- Add `"pydantic>=2.0"` to `dependencies` list

`pre_gauntlet/models.py` has 20+ Pydantic models with Field validation constraints. Converting to dataclasses would lose validation and be high-effort. pydantic likely comes transitively from `mcp>=1.0.0` but should be declared explicitly.

Note: `filelock==3.16.1` is already declared (added during gauntlet refactor).

**Verify:** `uv run python -c "import pydantic; print(pydantic.VERSION)"`

---

## Step 2: CON-005 — Fix Test Import Infrastructure

**File 1:** `pyproject.toml`
- Add `pythonpath = ["skills/adversarial-spec/scripts"]` to `[tool.pytest.ini_options]`

**Target files:** All test files in `skills/adversarial-spec/scripts/tests/` containing the `sys.path.insert` hack.
- Remove `sys.path.insert(0, str(Path(__file__).parent.parent))` from each
- Remove `import sys` only if not used elsewhere in the file
- Remove `from pathlib import Path` only if not used elsewhere in the file
- Check each file individually — do not assume uniform import usage

Integration tests are deferred — out of scope for this plan.

**Verify:** `uv run pytest` — all existing tests pass

---

## Step 3: CON-001 — Canonical Mutation Path with FileLock

**Strategy: one canonical mutation helper** — all task mutations route through a single function that holds the lock across the full read→mutate→write cycle. This prevents TOCTOU races AND prevents regression when new mutation call sites are added.

**Design note:** `mcp_tasks/server.py` (repo root) and `task_manager.py` (skill scripts package) live in separate packages with no shared import path. Extracting to a shared module would create cross-package coupling. Instead, each file gets its own `_mutate_tasks()` with a comment referencing the other implementation for parity.

**File 1:** `mcp_tasks/server.py`

Add a canonical mutation helper:
```python
from filelock import FileLock, Timeout

_LOCK_TIMEOUT = 10  # seconds

def _mutate_tasks(tasks_file: str, fn):
    """Atomic read-modify-write under lock. fn(tasks) -> modified tasks.

    NOTE: Parallel implementation exists in task_manager.py (skill scripts).
    Keep both in sync when modifying the locking/write protocol.
    """
    lock = FileLock(f"{tasks_file}.lock", timeout=_LOCK_TIMEOUT)
    try:
        with lock:
            tasks = _load_tasks_unlocked(tasks_file)
            tasks = fn(tasks)
            _save_tasks_unlocked(tasks_file, tasks)
            return tasks
    except Timeout:
        raise RuntimeError(f"TASK_STORE_BUSY: Could not acquire {tasks_file}.lock within {_LOCK_TIMEOUT}s")
```

- Rename existing `load_tasks()` → `_load_tasks_unlocked()` (private, no lock)
- Rename existing `save_tasks()` → `_save_tasks_unlocked()` (private, no lock)
- Use atomic write in `_save_tasks_unlocked`: write to temp file + `os.replace`
- Refactor all mutating operations to call `_mutate_tasks(path, lambda tasks: ...)`
- Read-only callers can call `_load_tasks_unlocked()` directly (tolerate stale reads)

**Error contract:**
- Lock timeout → `TASK_STORE_BUSY` error with deterministic message
- Corrupt JSON → `TASK_STORE_CORRUPT` error (catch `json.JSONDecodeError` in `_load_tasks_unlocked`)

**File 2:** `skills/adversarial-spec/scripts/task_manager.py`
- Same pattern: add `_mutate_tasks()` helper with cross-reference comment, route all mutations through it

**Reference pattern:** `gauntlet/persistence.py:74-76` (`_lock_for()`)

**Verify:** `uv run pytest`, confirm `.claude/tasks.json.lock` sidecar appears after use

---

## Step 4: CON-004 — Fix Silent Error Swallowing in Gauntlet Phases

**Strategy: inverse re-raise pattern** (catch Exception, re-raise programming bugs).

A `_RECOVERABLE` tuple would miss LiteLLM's custom exception hierarchy (`litellm.APIError`, `litellm.RateLimitError`, etc.) which does NOT inherit from `RuntimeError` or `OSError`. The codebase imports no litellm exception types. The inverse pattern is safer:

```python
# Re-raise programming bugs that should crash loudly
# NOTE: ValueError and KeyError are NOT included — malformed model JSON
# raises these during parsing, and they are recoverable operational errors.
_PROGRAMMING_BUGS = (TypeError, NameError, AttributeError, ImportError, SyntaxError, AssertionError)

except Exception as e:
    if isinstance(e, _PROGRAMMING_BUGS):
        raise
    # ... existing fallback behavior (log + safe default)
```

This catches all third-party exceptions (LiteLLM, subprocess, network) and malformed model output while surfacing actual programming bugs.

**Critical fix — phase_3_filtering.py:139-140:**
```python
# BEFORE: except Exception: pass  (completely silent!)
# AFTER:
except Exception as e:
    if isinstance(e, _PROGRAMMING_BUGS):
        raise
    print(f"Warning: Explanation matching failed: {e}", file=sys.stderr)
```

**Other files** (add re-raise guard, keep existing log+fallback behavior):
- `phase_1_attacks.py:158` — add `_PROGRAMMING_BUGS` re-raise before existing warning
- `phase_4_evaluation.py:128,209,226` — add re-raise guard (keep existing JSONDecodeError-specific catch at 126)
- `phase_5_rebuttals.py:108` — add re-raise guard
- `phase_6_adjudication.py:93` — add re-raise guard

Define `_PROGRAMMING_BUGS` in each file locally (6 files, same tuple). If duplication feels excessive during implementation, extract to `gauntlet/error_policy.py`.

**Verify:** `uv run pytest`

---

## Step 5: CON-003 — Replace Phase 2 Inline Dispatch

**File:** `skills/adversarial-spec/scripts/gauntlet/phase_2_synthesis.py`

Replace the inline CLI routing block (lines 113-146) that duplicates `call_model()` logic without model validation:

```python
# BEFORE: 35 lines of if/elif/else routing to codex/gemini/claude/litellm
# AFTER:
response, in_tokens, out_tokens = call_model(
    model=model,
    system_prompt=SYNTHESIS_SYSTEM_PROMPT,  # extracted in Step 6, use literal until then
    user_message=prompt,
    timeout=config.timeout,
    codex_reasoning=config.attack_codex_reasoning,
)
cost_tracker.add(model, in_tokens, out_tokens)
```

**IMPORTANT:** Use the exact existing Phase 2 system_prompt text — do NOT invent a new literal. Read it from the source file during implementation.

Remove unused imports: `call_codex_model`, `call_gemini_cli_model`, `call_claude_cli_model`, and the `try: from litellm import completion` block.

Keep import: `from gauntlet.model_dispatch import call_model` and `from models import cost_tracker`.

**Note:** Path 1 (`call_model()`) and Path 2 (`call_models_parallel()`) serve different needs (gauntlet single-model vs debate multi-model parallel) and should coexist. Only Path 3 (inline duplication) is being eliminated.

**Verify:** `uv run pytest` — specifically `test_gauntlet_synthesis_extract.py`

---

## Step 6: CON-007 — Extract Gauntlet Prompts

**New file:** `skills/adversarial-spec/scripts/gauntlet/prompts.py`

Extract 9 prompt constants:

| Constant | Source | Template vars |
|----------|--------|---------------|
| `ATTACK_SYSTEM_PROMPT` | phase_1_attacks.py:73-79 | `{persona}` |
| `ATTACK_USER_PROMPT` | phase_1_attacks.py:81-85 | `{spec}` |
| `SYNTHESIS_SYSTEM_PROMPT` | phase_2_synthesis.py (inline dispatch) | none |
| `BIG_PICTURE_PROMPT` | phase_2_synthesis.py:33-81 | `{concerns_by_adversary}` |
| `EXPLANATION_MATCHING_PROMPT` | phase_3_filtering.py:87-99 | none |
| `CLUSTERING_PROMPT` | phase_3_filtering.py:250-280 | none |
| `EVALUATION_SYSTEM_PROMPT` | phase_4_evaluation.py:62-87 | `{protocols_text}` |
| `REBUTTAL_PROMPT` | phase_5_rebuttals.py:22-42 | `{dismissal_reasoning}` |
| `ADJUDICATION_SYSTEM_PROMPT` | phase_6_adjudication.py:46-60 | none |

Each phase file replaces inline prompt with `from gauntlet.prompts import <CONSTANT>`.

Convert f-strings to `.format()` templates where needed. Rendered output must remain byte-for-byte equivalent for representative inputs.

**Verify:** `uv run pytest`, diff rendered prompts before/after

---

## Step 7: CON-008 — CLI Flag Aliases in debate.py

**File:** `skills/adversarial-spec/scripts/debate.py` — `add_gauntlet_arguments()` and `add_codex_arguments()`

Add argparse aliases (additive only, no breaking changes):

| Current flag | Alias to add | Destination (unchanged) |
|-------------|-------------|------------------------|
| `--gauntlet-adversaries` | `--adversaries` | `args.gauntlet_adversaries` |
| `--gauntlet-model` | `--adversary-model` | existing dest |
| `--gauntlet-attack-models` | `--attack-models` | existing dest |
| `--gauntlet-frontier` | `--eval-model` | existing dest |
| `--codex-reasoning` | `--attack-codex-reasoning` | existing dest |

Also add `"minimal"` to `--codex-reasoning` choices (cli.py supports it, debate.py doesn't).

Help text: canonical long flag appears first, alias second.

**Skip** `--resume` aliasing: debate.py `--resume` takes a session ID string, cli.py `--resume` is a boolean flag. Different semantics, can't alias.

**Verify:** `uv run pytest`, `uv run python debate.py gauntlet --help` shows aliases

---

## Post-Implementation

1. `uv run pytest` — all tests pass
2. `uvx ruff check --fix --unsafe-fixes` — clean
3. Back up deployed skill: `cp -r ~/.claude/skills/adversarial-spec/ /tmp/adversarial-spec-backup-$(date +%Y%m%d%H%M)/`
4. Deploy: `rsync -a --delete skills/adversarial-spec/ ~/.claude/skills/adversarial-spec/`
5. Smoke test (source): `uv run python skills/adversarial-spec/scripts/debate.py gauntlet --help`
6. Smoke test (deployed): `uv run python ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet --help`
7. `/mapcodebase --update` — refresh architecture docs with resolved concerns
8. **Rollback:** Revert commit + restore backup from `/tmp/` + re-run smoke tests

---

## Decisions Log

| Decision | Rationale | Round |
|----------|-----------|-------|
| Transaction-scoped lock, not per-function | TOCTOU race with separate load/save locks | R1 |
| Audit trail for invalidated findings | Prevents re-reporting, preserves institutional knowledge | R1 |
| Inverse re-raise, not RecoverableError types | LiteLLM exceptions don't inherit cleanly; wrapping adds complexity | R1 |
| `_mutate_tasks()` canonical helper | Prevents regression when new writers are added | R2 |
| Keep `concerns_identified` total, add `_valid` | Don't reinterpret existing metrics | R2 |
| Remove `ValueError`/`KeyError` from `_PROGRAMMING_BUGS` | Malformed model JSON raises these; they're operational errors | R2 |
| Duplicate `_mutate_tasks()` across packages | No shared import path; cross-package coupling is worse than duplication | R3 |
| `rsync --delete` for deployment | `cp -r` leaves stale files | R3 |
| Plan format, not full spec structure | This is a remediation checklist, not a product spec | R2 (rejected) |

## Exploration Still Needed During Implementation

- Exact system_prompt in phase_2 inline dispatch (verify — do NOT invent a new literal)
- Which test files use `sys`/`Path` beyond sys.path hack (check each before removing imports)
- Whether `_PROGRAMMING_BUGS` duplication across 6 files warrants extraction to `gauntlet/error_policy.py` (decide during Step 4)
