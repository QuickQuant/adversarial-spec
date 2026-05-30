# Technical Spec Draft v3: Dispatch & Cost-Tracker Unification

> Session: `adv-spec-202604291604-dispatch-cost-tracker-unify`
> Scope: CON-002 only
> Roadmap: `.adversarial-spec/specs/dispatch-cost-tracker-unify/manifest.json`
> Tests: `.adversarial-spec/specs/dispatch-cost-tracker-unify/tests-pseudo.md`

## 1. Overview

The gauntlet pipeline currently imports the global `cost_tracker` singleton from `models.py` in phase modules. That makes phase logic responsible for model accounting, couples gauntlet internals to debate-engine state, and forces tests to monkeypatch phase-local `cost_tracker.add(...)` sites.

This refactor creates a dedicated token tracking module, renames the tracker API to match what it really records, and moves gauntlet write-side accounting to `gauntlet/model_dispatch.call_model()`.

## 2. Goals

<!-- Addresses US-0, US-1, US-2, US-3, US-4 -->

- Remove gauntlet phase dependency on `models.cost_tracker`.
- Rename cost tracking to token tracking with clear API names.
- Keep model-call behavior unchanged except for the tracking boundary.
- Reduce test monkeypatch surface to one fixture pattern.
- Capture CON-002 remediation and CON-001 drift in durable session/spec artifacts.

## 3. Non-Goals

- Do not implement CON-001 litellm pathway unification.
- Do not implement CON-003 orchestrator extraction.
- Do not manually edit generated `.architecture` docs solely for hygiene.
- Do not require real model-call parity smoke tests.
- Do not change retry behavior, timeout behavior, JSON mode behavior, temperature defaults, or max-token defaults.

## 4. User Journey

This is an internal refactor. CLI users and gauntlet consumers should see unchanged command behavior and unchanged model-call results.

The developer workflow changes:

- Adding or editing a gauntlet phase no longer requires importing `cost_tracker` or manually recording token usage. A phase calls `gauntlet/model_dispatch.call_model()`, and tracking is handled at the dispatch boundary.
- Tests that need isolated accounting state use `fresh_tracker` instead of monkeypatching phase-local `cost_tracker.add(...)` references.
- The implementation card records one audit of tracker references and `call_model(...)` return shapes before production code moves, so reviewers can verify the refactor mechanically.

## 5. Roadmap User Story Mapping

| ID | Story | Spec Coverage |
|----|-------|---------------|
| US-0 | Audit tracker references before edits | Sections 7, 13, 15 |
| US-1 | Add `fresh_tracker` fixture | Sections 10, 12 |
| US-2 | Rename to `TokenTracker.record_call()` | Sections 8, 9 |
| US-3 | Move gauntlet tracking to `model_dispatch.call_model()` | Sections 9, 11 |
| US-4 | Capture concern status durably | Sections 14, 16 |

## 6. Current State

### 6.1 Tracker implementation

`skills/adversarial-spec/scripts/models.py` defines:

- `CostTracker`
- `cost_tracker = CostTracker()`
- `CostTracker.add(model, input_tokens, output_tokens) -> float`

The tracker stores:

- `total_input_tokens`
- `total_output_tokens`
- `total_cost`
- `by_model`
- `summary()`

`add()` is thread-safe via a `threading.Lock`.

### 6.2 Debate-side write sites and current import shape

`models.py` records usage inside `call_single_model()` for:

- Codex CLI responses
- Gemini CLI responses
- Claude CLI responses
- LiteLLM responses

These write sites stay in `models.py` for this spec. They will call the renamed method, but their placement does not move.

Audit step 1 in Section 7 must enumerate every existing `from models import cost_tracker` and `cost_tracker.add(` site in `models.py`, `debate.py`, gauntlet phase files, and tests. Record the list in the implementation card before any production rename. That list is the source of truth for the import-shape conversion required by Section 9.

The current `call_model(...)` return tuple is `(content, input_tokens, output_tokens)`. Audit step 1 must verify this shape across all callers before Section 11 takes effect. If any 4-tuple caller is found, enumerate and rewrite it in the same commit that introduces tracker writes inside `call_model(...)`.

### 6.3 Gauntlet write sites

The following gauntlet phase files import `cost_tracker` from `models.py` and call `cost_tracker.add(...)` after `call_model(...)`:

- `gauntlet/phase_1_attacks.py`
- `gauntlet/phase_2_synthesis.py`
- `gauntlet/phase_4_evaluation.py`
- `gauntlet/phase_5_rebuttals.py`
- `gauntlet/phase_6_adjudication.py`
- `gauntlet/phase_7_final_boss.py`

`gauntlet/phase_3_filtering.py` already calls `call_model(...)` but currently discards token counts. It is presently untracked. After this refactor it becomes tracked automatically through `call_model(...)`. This is an intentional correction; see Section 11.

`gauntlet/orchestrator.py` reads tracker totals for run statistics. That read-side dependency is legitimate, but it must import the public tracker from the new module.

### 6.4 Out-of-scope CON-001

The generated architecture concern for CON-001 drifted from source. It claimed three independent LiteLLM paths with divergent `max_tokens` values, but current source verification found two direct `litellm.completion(...)` paths and no matching `max_tokens` values. This spec records the drift and does not unify LiteLLM dispatch.

## 7. Getting Started: Implementation Workflow

<!-- Addresses US-0 -->

1. Run a full-tree audit for tracker references and `call_model(...)` return shape:
   - `cost_tracker`
   - `CostTracker`
   - `(cost_tracker|tracker)\.add\(`
   - `token_tracking`
   - `TokenTracker`
   - `record_call`
   - `call_model\(` callers and tuple unpack shapes
2. Save the raw audit output and an interpreted enumeration of import sites and `call_model(...)` unpack shapes in the implementation card evidence.
3. Add the phase-1 test fixture first, while production code still uses `CostTracker`. The phase-1 fixture patches `models.cost_tracker`; see Section 10.
4. Migrate tests away from direct phase-local tracker monkeypatches, using the phase-1 fixture.
5. Run targeted tests for migrated test files.
6. Add `token_tracking.py` and move the tracker implementation. In the same commit, switch `models.py` and `debate.py` to `import token_tracking`, and rewrite the fixture to its phase-2 form in Section 10.
7. Rename write API from `add()` to `record_call()`.
8. Update all implementation and test imports atomically.
9. Move gauntlet tracking writes into `gauntlet/model_dispatch.call_model()` and delete phase-level `cost_tracker.add(...)` calls.
10. Run deterministic mocked parity tests.
11. Run the full test suite.
12. Verify deployed skill path:

```bash
readlink ~/.claude/skills/adversarial-spec
```

The output must equal the absolute path of `skills/adversarial-spec/` in this repo, or deployment must be performed by copy, or user-approved deferral must be recorded.

Expected time to first verification: under 10 minutes for the audit and fixture test boundary.

If prerequisites fail:

- If `uv run pytest` cannot run because of cache permissions, use the project-approved environment fix or report the blocker explicitly.
- If the symlink is missing in a future environment, deploy by copying to `~/.claude/skills/adversarial-spec/` or record user-approved deployment deferral.

## 8. Token Tracking Module

<!-- Addresses US-2 -->

Create:

`skills/adversarial-spec/scripts/token_tracking.py`

It owns:

```python
@dataclass
class TokenTracker:
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    by_model: dict = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def record_call(self, model: str, input_tokens: int, output_tokens: int) -> float:
        ...

    def summary(self) -> str:
        ...


tracker = TokenTracker()
```

The cost calculation behavior must be copied from `CostTracker.add()` exactly:

- CLI prefixes `codex/`, `gemini-cli/`, and `claude-cli/` use zero cost.
- Non-CLI models use `MODEL_COSTS.get(model, DEFAULT_COST)`.
- Cost is `(input_tokens / 1_000_000 * input_rate) + (output_tokens / 1_000_000 * output_rate)`.
- All aggregate mutations happen under the lock.

Read-side names remain stable:

- `total_cost`
- `total_input_tokens`
- `total_output_tokens`
- `by_model`
- `summary()`

No `CostTracker` compatibility class and no `cost_tracker` alias should remain in production code.

### 8.1 Error Handling and Concurrency

`record_call(...)` must preserve the current `CostTracker.add(...)` behavior for token values unless the pre-rename audit proves a different behavior already exists. If current behavior accepts zero token counts, the new method must also accept zero. If negative or non-integer token counts are possible at any call site, the implementation must handle them deliberately rather than silently corrupting totals: either preserve the exact current behavior with a regression test, or raise `ValueError` with a targeted test and update the spec before implementation.

All aggregate mutations must happen under `_lock`: `total_input_tokens`, `total_output_tokens`, `total_cost`, and `by_model`. `summary()` must read a consistent snapshot under the same lock if the current implementation already does so; otherwise the audit must record that read behavior is intentionally unchanged.

## 9. Import and API Migration

<!-- Addresses US-2, US-3 -->

Update debate/model code:

- `models.py` imports the `token_tracking` module, not the mutable singleton.
- Existing write sites call `token_tracking.tracker.record_call(...)`.
- Existing `ModelResponse.cost` behavior is unchanged.
- `debate.py` imports the `token_tracking` module and uses the same read-side fields for summaries and checkpoint metadata.
- Any local variable named `cost_tracker` in `debate.py` is renamed to `tracker` for audit cleanliness. User-facing display strings may continue to say "Cost Summary" because dollar cost remains a read-side field.

Update gauntlet code:

- `gauntlet/model_dispatch.py` imports the `token_tracking` module.
- Phase files do not import tracker.
- `gauntlet/orchestrator.py` imports the `token_tracking` module for read-side totals.

Required access pattern:

```python
import token_tracking

token_tracking.tracker.record_call(model, input_tokens, output_tokens)
```

Forbidden in production modules:

```python
from token_tracking import tracker  # not allowed in production modules
from token_tracking import tracker as cost_tracker  # not allowed
_tracker = token_tracking.tracker  # not allowed at module load
```

This is required for `fresh_tracker` to remain a single patch point. If modules bind the singleton at import time through `from ... import tracker` or a module-level local rebind, patching `token_tracking.tracker` will not affect those modules. Every production read or write must resolve `token_tracking.tracker` at call time.

## 10. Test Fixture Migration

<!-- Addresses US-1 -->

The fixture has two forms across the refactor. Section 7 step 6 is the boundary.

### Phase-1 fixture

Introduce this in Section 7 step 3 while production still defines `models.cost_tracker`:

```python
@pytest.fixture
def fresh_tracker(monkeypatch):
    import models

    fresh = models.CostTracker()
    monkeypatch.setattr(models, "cost_tracker", fresh)
    yield fresh
```

### Phase-2 fixture

Rewrite the fixture in Section 7 step 6, in the same commit that introduces `token_tracking.py`:

```python
@pytest.fixture
def fresh_tracker(monkeypatch):
    import token_tracking

    fresh = token_tracking.TokenTracker()
    monkeypatch.setattr(token_tracking, "tracker", fresh)
    yield fresh
```

Tests should assert tracker state through `fresh_tracker`, not by monkeypatching `record_call` directly.

Direct monkeypatches of tracker write methods are only allowed when a test names the consumer under test and asserts call semantics. They must not be used as a general accounting reset. The default pattern is state verification through `fresh_tracker`.

## 11. Gauntlet Dispatch Boundary

<!-- Addresses US-3 -->

`gauntlet/model_dispatch.call_model()` becomes the single write-side tracking boundary for gauntlet model usage.

Required behavior:

1. Validate the model name exactly as today.
2. Dispatch to the same CLI or LiteLLM path as today.
3. Preserve current arguments:
   - `timeout`
   - `codex_reasoning`
   - `json_mode`
   - LiteLLM `temperature=0.7`
   - no added `max_tokens`
4. After a successful model call returns `(content, input_tokens, output_tokens)`, call:

```python
cost = token_tracking.tracker.record_call(model, input_tokens, output_tokens)
```

5. Return the same 3-tuple shape as today, verified by the Section 6.2 / Section 7 step 1 audit:

```python
return content, input_tokens, output_tokens
```

The returned tuple must not include cost. If the audit finds any 4-tuple caller, convert it to the 3-tuple shape in the same commit; this is part of the Section 11 boundary move.

Phase-level `cost_tracker.add(...)` calls are deleted. This prevents double-recording.

### Phase 3 filtering note

`gauntlet/phase_3_filtering.py` already calls `call_model(...)` and discards token counts. After this refactor, it will be tracked automatically by `call_model(...)`. This is an intentional correction of a historical undercount, not a behavior regression. Exact aggregate token totals are not expected to match old runs when phase 3 filtering executes.

## 12. Deterministic Parity Test

<!-- Addresses US-1, US-3 -->

Add a deterministic mocked dispatch test. It must not call real models.

Required coverage:

- Mock `completion(...)` for the LiteLLM path with fixed usage metadata.
- Mock CLI dispatch helpers with fixed `(content, input_tokens, output_tokens)` tuples for each of `codex/`, `gemini-cli/`, and `claude-cli/` prefixes. This verifies zero-cost behavior.
- Exercise at least one representative `call_model(...)` invocation pattern from each phase file enumerated in Section 6.3, including `phase_3_filtering.py`.
- Assert exact equality for:
  - `by_model`
  - `total_input_tokens`
  - `total_output_tokens`
  - `total_cost`

The parity test has two parts:

1. Previously tracked phase call sites remain single-counted after the boundary move.
2. `phase_3_filtering.py` is recorded once when it calls `call_model(...)`.

Do not require exact aggregate parity with old runs that executed phase 3 filtering, because old runs undercounted that model usage.

## 13. Audit Gates

<!-- Addresses US-0 -->

Before production rename:

- Full-tree audit references old tracker names and write API.
- Identify any dynamic string references in tests.
- Identify documentation references that should remain historical.

After production rename:

```bash
rg -n "from models import cost_tracker|cost_tracker|CostTracker" \
  skills/adversarial-spec/scripts skills/adversarial-spec/scripts/tests

rg -n "(cost_tracker|tracker)\.add\(" \
  skills/adversarial-spec/scripts skills/adversarial-spec/scripts/tests

rg -n "from token_tracking import tracker" \
  skills/adversarial-spec/scripts
```

- The first command must return zero matches in production paths. Test files containing intentionally retained historical strings must be enumerated in the implementation card.
- The second command is refined to tracker objects, not arbitrary `.add(...)` calls, and must return zero matches in production paths.
- The third command must return zero matches in production modules. Test fixtures may match only if they are explicitly scoped to the fixture.
- Record a pre-rename baseline of unrelated `.add(...)` matches in the implementation card so post-rename diffs are reviewable.

## 14. Concern Status Handling

<!-- Addresses US-4 -->

This session treats generated architecture docs as refreshable mapcodebase output.

Required durable records:

- Session `requirements_summary` says CON-002 is the active remediation.
- Session `requirements_summary` says CON-001 is out of scope because source verification showed drift.
- Roadmap manifest and final spec repeat that status.

Do not manually edit `.architecture/concerns.md` or `.architecture/findings.md` solely for this session. The next `/mapcodebase` run should regenerate those files from current source and mark the old concern state obsolete.

## 15. Verification Plan

<!-- Addresses US-0, US-1, US-2, US-3, US-4 -->

1. `python3 -m json.tool` for JSON artifacts created in this session.
2. Targeted pytest files after fixture migration:
   - `test_gauntlet_phase_1_attacks.py`
   - `test_gauntlet_phase_config.py`
   - `test_gauntlet_error_guards.py`
   - `test_gauntlet_orchestrator.py`
   - `test_model_calls.py`
   - `test_gauntlet_model_dispatch.py`
   - `test_models.py`
3. Deterministic mocked parity test per Section 12.
4. Full suite: `uv run pytest`.
5. Static boundary checks per Section 13.
6. `readlink ~/.claude/skills/adversarial-spec` per Section 7 step 12.

## 16. Deployment and Resume Notes

<!-- Addresses US-4 -->

`~/.claude/skills/adversarial-spec` is currently a symlink to `skills/adversarial-spec`, and Codex loaded this skill from the repo path. Manual copy is not required in this environment.

Final verification must record one of:

- `readlink` shows the symlink resolves to this repo's `skills/adversarial-spec/` path.
- Files were copied to deployed skill path.
- User explicitly deferred deployment.

## 17. Resolved Decisions

These were debate-time questions and are now resolved:

1. Direct monkeypatches of `record_call` are allowed only for narrow failure-injection tests that name the consumer under test. Default pattern is state verification through `fresh_tracker`.
2. Production paths must be clean of `cost_tracker` strings. Historical assertion text inside tests may remain only if enumerated in the implementation card.
3. `debate.py` local variable `cost_tracker` is renamed to `tracker`; display strings remain unchanged.

Further questions raised in debate must not expand session scope without user approval.

## 18. Acceptance Criteria

- `TokenTracker` and `tracker` live in `token_tracking.py`.
- Production code has no `CostTracker` or `cost_tracker` symbol.
- Tracker write API is `record_call(...)`.
- Existing read-side fields remain stable.
- Production modules access the mutable singleton through `import token_tracking`, not `from token_tracking import tracker`, and never via a module-level local rebind.
- Gauntlet phase files do not import a tracker singleton.
- Gauntlet model usage is recorded once at `gauntlet/model_dispatch.call_model()`.
- Phase 3 filtering usage is intentionally recorded once through `call_model(...)`.
- `call_model(...)` return shape remains the existing 3-tuple `(content, input_tokens, output_tokens)`; any pre-refactor 4-tuple caller found by audit is converted in the same commit.
- Debate/CLI handler placement in `models.py` remains otherwise unchanged.
- `debate.py` local `cost_tracker` variable is renamed to `tracker`; display strings remain unchanged.
- Deterministic mocked parity test passes, covering one call pattern per phase file in Section 6.3 and all three CLI prefixes plus LiteLLM.
- Full suite passes or any blocker is documented with the exact failure.
- CON-002 and CON-001 status are recorded in session/spec artifacts.
- `readlink ~/.claude/skills/adversarial-spec` is recorded in final verification or a copy/deferral is documented.
