# Plan: Architecture Concern Remediation

## Context

mapcodebase 3.1 identified 8 actionable concerns (CON-001 through CON-008). Exploration revealed **CON-002 (dead code) is invalid** — all three files (`scope.py`, `knowledge_service.py`, `gauntlet_monolith.py`) are actively used. The underlying findings (FIND-001, FIND-002, FIND-007) were wrong. This plan addresses the 7 valid concerns and corrects the false positive.

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

## Step 0: Correct CON-002 False Positive

**Files:**
- `.architecture/concerns.md` — remove CON-002 section, update summary counts
- `.architecture/manifest.json` — remove CON-002 from `concerns[]`, update `concerns_identified` metric, remove FIND-001/FIND-002/FIND-007 from `findings[]` (or add corrective note to `warnings[]`)
- `.architecture/findings.md` — mark FIND-001/FIND-002/FIND-007 as invalid
- `.architecture/primer.md` — update "Top Actionable Concerns" section

**Why:** `scope.py` has active tests in `test_adversaries.py` (scope_guidelines validation). `knowledge_service.py` is imported by `pre_gauntlet/discovery.py` and exported from `integrations/__init__.py`. `gauntlet_monolith.py` is an intentional backward-compatibility shim.

---

## Step 1: CON-006 — Declare Pydantic Dependency

**File:** `pyproject.toml`
- Add `"pydantic>=2.0"` to `dependencies` list

`pre_gauntlet/models.py` has 20+ Pydantic models with Field validation constraints. Converting to dataclasses would lose validation and be high-effort. pydantic likely comes transitively from `mcp>=1.0.0` but should be declared explicitly.

**Verify:** `uv run python -c "import pydantic; print(pydantic.VERSION)"`

---

## Step 2: CON-005 — Fix Test Import Infrastructure

**File 1:** `pyproject.toml`
- Add `pythonpath = ["skills/adversarial-spec/scripts"]` to `[tool.pytest.ini_options]`

**Files 2-18:** All 17 test files in `skills/adversarial-spec/scripts/tests/`
- Remove `sys.path.insert(0, str(Path(__file__).parent.parent))` from each
- Remove `import sys` only if not used elsewhere in the file
- Remove `from pathlib import Path` only if not used elsewhere in the file

Integration tests are deferred — out of scope for this plan.

**Verify:** `uv run pytest` — all existing tests pass

---

## Step 3: CON-001 — FileLock on tasks.json

**File 1:** `mcp_tasks/server.py`
- Add `from filelock import FileLock`
- Add helper: `_tasks_lock = lambda path: FileLock(f"{path}.lock")`
- Wrap `load_tasks()` body with `with _tasks_lock(tasks_file):`
- Wrap `save_tasks()` body with `with _tasks_lock(tasks_file):`

**File 2:** `skills/adversarial-spec/scripts/task_manager.py`
- Same pattern: add FileLock import, wrap `_load()` and `_save()` bodies

**Reference pattern:** `gauntlet/persistence.py:74-76` (`_lock_for()`)

**Verify:** `uv run pytest`, confirm `.claude/tasks.json.lock` sidecar appears after use

---

## Step 4: CON-004 — Fix Silent Error Swallowing in Gauntlet Phases

**Strategy: inverse re-raise pattern** (catch Exception, re-raise programming bugs).

A `_RECOVERABLE` tuple would miss LiteLLM's custom exception hierarchy (`litellm.APIError`, `litellm.RateLimitError`, etc.) which does NOT inherit from `RuntimeError` or `OSError`. The codebase imports no litellm exception types. The inverse pattern is safer:

```python
# Re-raise programming bugs that should crash loudly
_PROGRAMMING_BUGS = (TypeError, NameError, KeyError, AttributeError, IndexError, ValueError, ImportError, SyntaxError)

except Exception as e:
    if isinstance(e, _PROGRAMMING_BUGS):
        raise
    # ... existing fallback behavior (log + safe default)
```

This catches all third-party exceptions (LiteLLM, subprocess, network) while surfacing actual bugs.

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

Define `_PROGRAMMING_BUGS` in each file locally, or in a shared `gauntlet/exceptions.py` if preferred.

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
    system_prompt="You are an expert at pattern recognition and synthesis.",
    user_message=prompt,
    timeout=config.timeout,
    codex_reasoning=config.attack_codex_reasoning,
)
cost_tracker.add(model, in_tokens, out_tokens)
```

Remove unused imports: `call_codex_model`, `call_gemini_cli_model`, `call_claude_cli_model`, and the `try: from litellm import completion` block.

Keep import: `from gauntlet.model_dispatch import call_model` and `from models import cost_tracker`.

**Note:** Path 1 (`call_model()`) and Path 2 (`call_models_parallel()`) serve different needs (gauntlet single-model vs debate multi-model parallel) and should coexist. Only Path 3 (inline duplication) is being eliminated.

**Verify:** `uv run pytest` — specifically `test_gauntlet_synthesis_extract.py`

---

## Step 6: CON-007 — Extract Gauntlet Prompts

**New file:** `skills/adversarial-spec/scripts/gauntlet/prompts.py`

Extract 8 prompt constants:

| Constant | Source | Template vars |
|----------|--------|---------------|
| `ATTACK_SYSTEM_PROMPT` | phase_1_attacks.py:73-79 | `{persona}` |
| `ATTACK_USER_PROMPT` | phase_1_attacks.py:81-85 | `{spec}` |
| `BIG_PICTURE_PROMPT` | phase_2_synthesis.py:33-81 | `{concerns_by_adversary}` |
| `EXPLANATION_MATCHING_PROMPT` | phase_3_filtering.py:87-99 | none |
| `CLUSTERING_PROMPT` | phase_3_filtering.py:250-280 | none |
| `EVALUATION_SYSTEM_PROMPT` | phase_4_evaluation.py:62-87 | `{protocols_text}` |
| `REBUTTAL_PROMPT` | phase_5_rebuttals.py:22-42 | `{dismissal_reasoning}` |
| `ADJUDICATION_SYSTEM_PROMPT` | phase_6_adjudication.py:46-60 | none |

Each phase file replaces inline prompt with `from gauntlet.prompts import <CONSTANT>`.

Convert f-strings to `.format()` templates where needed.

**Verify:** `uv run pytest`, diff rendered prompts before/after

---

## Step 7: CON-008 — CLI Flag Aliases in debate.py

**File:** `skills/adversarial-spec/scripts/debate.py` — `add_gauntlet_arguments()` and `add_codex_arguments()`

Add argparse aliases (additive only, no breaking changes):

| Current flag | Alias to add |
|-------------|-------------|
| `--gauntlet-adversaries` | `--adversaries` |
| `--gauntlet-model` | `--adversary-model` |
| `--gauntlet-attack-models` | `--attack-models` |
| `--gauntlet-frontier` | `--eval-model` |
| `--codex-reasoning` | `--attack-codex-reasoning` |

Also add `"minimal"` to `--codex-reasoning` choices (cli.py supports it, debate.py doesn't).

**Skip** `--resume` aliasing: debate.py `--resume` takes a session ID string, cli.py `--resume` is a boolean flag. Different semantics, can't alias.

**Verify:** `uv run pytest`, `uv run python debate.py gauntlet --help` shows aliases

---

## Post-Implementation

1. `uv run pytest` — all tests pass
2. `uvx ruff check --fix --unsafe-fixes` — clean
3. `cp -r skills/adversarial-spec/* ~/.claude/skills/adversarial-spec/` — deploy
4. `/mapcodebase --update` — refresh architecture docs with resolved concerns

---

## Evaluate-Plan Results

### Architecture Status: `fresh`

Manifest schema 2.0, git hash matches HEAD (c3b5f8c), all accessor artifacts present.

### Risks Found During Evaluation

1. **CON-004 `_RECOVERABLE` tuple would miss LiteLLM errors (FIXED ABOVE)** — LiteLLM exceptions don't inherit from RuntimeError/OSError. Switched to inverse re-raise pattern.
2. **CON-003 + CON-007 both modify phase_2_synthesis.py** — sequential execution with fresh reads required.
3. **CON-008 argparse `dest`** — aliases don't change dest name; downstream reads `args.gauntlet_adversaries` which is correct.

### Exploration Still Needed During Implementation

- Exact system_prompt in phase_2 inline dispatch (verify the plan's hardcoded string)
- Which test files use `sys`/`Path` beyond sys.path hack (check each before removing imports)
- Whether `_PROGRAMMING_BUGS` should be shared or per-file (decide during Step 4)
