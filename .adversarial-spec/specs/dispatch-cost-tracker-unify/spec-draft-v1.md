# Technical Spec Draft v1: Dispatch & Cost-Tracker Unification

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

## 4. Roadmap User Story Mapping

| ID | Story | Spec Coverage |
|----|-------|---------------|
| US-0 | Audit tracker references before edits | Sections 6, 12, 14 |
| US-1 | Add `fresh_tracker` fixture | Sections 9, 11 |
| US-2 | Rename to `TokenTracker.record_call()` | Sections 7, 8 |
| US-3 | Move gauntlet tracking to `model_dispatch.call_model()` | Sections 8, 10 |
| US-4 | Capture concern status durably | Sections 13, 15 |

## 5. Current State

### 5.1 Tracker implementation

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

### 5.2 Debate-side write sites

`models.py` records usage inside `call_single_model()` for:

- Codex CLI responses
- Gemini CLI responses
- Claude CLI responses
- LiteLLM responses

These write sites stay in `models.py` for this spec. They will call the renamed method, but their placement does not move.

### 5.3 Gauntlet write sites

The following gauntlet phase files import `cost_tracker` from `models.py` and call `cost_tracker.add(...)` after `call_model(...)`:

- `gauntlet/phase_1_attacks.py`
- `gauntlet/phase_2_synthesis.py`
- `gauntlet/phase_4_evaluation.py`
- `gauntlet/phase_5_rebuttals.py`
- `gauntlet/phase_6_adjudication.py`
- `gauntlet/phase_7_final_boss.py`

`gauntlet/orchestrator.py` reads tracker totals for run statistics. That read-side dependency is legitimate, but it must import the public tracker from the new module.

### 5.4 Out-of-scope CON-001

The generated architecture concern for CON-001 drifted from source. It claimed three independent LiteLLM paths with divergent `max_tokens` values, but current source verification found two direct `litellm.completion(...)` paths and no matching `max_tokens` values. This spec records the drift and does not unify LiteLLM dispatch.

## 6. Getting Started: Implementation Workflow

<!-- Addresses US-0 -->

1. Run a full-tree audit for tracker references:
   - `cost_tracker`
   - `CostTracker`
   - `.add(`
   - `token_tracking`
   - `TokenTracker`
   - `record_call`
2. Save or summarize the audit in the implementation card evidence.
3. Add the test fixture first, while production code still uses `CostTracker`.
4. Migrate tests away from direct phase-local tracker monkeypatches.
5. Run targeted tests for migrated test files.
6. Add `token_tracking.py` and move the tracker implementation.
7. Rename write API from `add()` to `record_call()`.
8. Update all implementation and test imports atomically.
9. Move gauntlet tracking writes into `gauntlet/model_dispatch.call_model()`.
10. Run deterministic mocked parity tests.
11. Run the full test suite.
12. Verify `skills/adversarial-spec/` is the deployed skill path via the existing symlink to `~/.claude/skills/adversarial-spec/`.

Expected time to first verification: under 10 minutes for the audit and fixture test boundary.

If prerequisites fail:

- If `uv run pytest` cannot run because of cache permissions, use the project-approved environment fix or report the blocker explicitly.
- If the symlink is missing in a future environment, either deploy by copying to `~/.claude/skills/adversarial-spec/` or record user-approved deployment deferral.

## 7. Token Tracking Module

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

## 8. Import and API Migration

<!-- Addresses US-2, US-3 -->

- Update debate/model code:

- `models.py` imports the `token_tracking` module, not the mutable singleton.
- Existing write sites call `token_tracking.tracker.record_call(...)`.
- Existing `ModelResponse.cost` behavior is unchanged.
- `debate.py` imports the `token_tracking` module and uses the same read-side fields for summaries and checkpoint metadata.

Update gauntlet code:

- `gauntlet/model_dispatch.py` imports the `token_tracking` module.
- Phase files do not import tracker.
- `gauntlet/orchestrator.py` imports the `token_tracking` module for read-side totals.

Required access pattern:

```python
import token_tracking

token_tracking.tracker.record_call(model, input_tokens, output_tokens)
```

Avoid direct singleton imports and aliases:

```python
from token_tracking import tracker  # not allowed in production modules
from token_tracking import tracker as cost_tracker  # not allowed
```

This is required for `fresh_tracker` to remain a single patch point. If modules bind the singleton at import time, patching `token_tracking.tracker` will not affect those modules.

## 9. Test Fixture Migration

<!-- Addresses US-1 -->

Add an opt-in pytest fixture in `skills/adversarial-spec/scripts/tests/conftest.py`:

```python
@pytest.fixture
def fresh_tracker(monkeypatch):
    from token_tracking import TokenTracker
    import token_tracking

    fresh = TokenTracker()
    monkeypatch.setattr(token_tracking, "tracker", fresh)
    yield fresh
```

During the first commit boundary, if production still imports `models.cost_tracker`, the fixture may temporarily patch the current singleton. After the production rename, the fixture must patch `token_tracking.tracker`.

Tests should assert tracker state through `fresh_tracker`, not by monkeypatching `record_call` directly.

Direct monkeypatches of tracker write methods are only allowed when a test names the consumer under test and asserts call semantics. They must not be used as a general accounting reset. The default pattern is state verification through `fresh_tracker`.

## 10. Gauntlet Dispatch Boundary

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

5. Return the same tuple shape as today:

```python
return content, input_tokens, output_tokens
```

The returned tuple must not add cost. Existing phase callers should not need a shape change.

Phase-level `cost_tracker.add(...)` calls are deleted. This prevents double-recording.

### Phase 3 filtering note

`gauntlet/phase_3_filtering.py` already calls `call_model(...)` and discards token counts. After this refactor, it will be tracked automatically by `call_model(...)`. This is an intentional correction of a historical undercount, not a behavior regression. Exact aggregate token totals are not expected to match old runs when phase 3 filtering executes.

## 11. Deterministic Parity Test

<!-- Addresses US-1, US-3 -->

Add a deterministic mocked dispatch test. It must not call real models.

Minimum coverage:

- Mock `completion(...)` for the LiteLLM path with fixed usage metadata.
- Mock CLI dispatch helpers with fixed `(content, input_tokens, output_tokens)` tuples.
- Exercise representative gauntlet call sites through `call_model(...)`.
- Assert exact equality for:
  - `by_model`
  - `total_input_tokens`
  - `total_output_tokens`
  - `total_cost`

The parity test has two parts:

1. Previously tracked phase call sites remain single-counted after the boundary move.
2. `phase_3_filtering.py` is recorded once when it calls `call_model(...)`.

Do not require exact aggregate parity with old runs that executed phase 3 filtering, because old runs undercounted that model usage.

## 12. Audit Gates

<!-- Addresses US-0 -->

Before production rename:

- Full-tree audit references old tracker names and write API.
- Identify any dynamic string references in tests.
- Identify documentation references that should remain historical.

After production rename:

- `rg -n "from models import cost_tracker|cost_tracker|CostTracker|\\.add\\(" skills/adversarial-spec/scripts skills/adversarial-spec/scripts/tests`
- Investigate every match.
- Matches in unrelated collection `.add(...)` calls or historical markdown may remain only if documented.
- Tracker write failures are determined by object context, not by every textual `.add(` match.
- No gauntlet phase file may match tracker singleton names.

## 13. Concern Status Handling

<!-- Addresses US-4 -->

This session treats generated architecture docs as refreshable mapcodebase output.

Required durable records:

- Session `requirements_summary` says CON-002 is the active remediation.
- Session `requirements_summary` says CON-001 is out of scope because source verification showed drift.
- Roadmap manifest and final spec repeat that status.

Do not manually edit `.architecture/concerns.md` or `.architecture/findings.md` solely for this session. The next `/mapcodebase` run should regenerate those files from current source and mark the old concern state obsolete.

## 14. Verification Plan

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
3. Deterministic mocked parity test.
4. Full suite:

```bash
uv run pytest
```

5. Static boundary checks:

```bash
rg -n "cost_tracker|token_tracker|from token_tracking import tracker" skills/adversarial-spec/scripts/gauntlet/phase_*.py
rg -n "from token_tracking import tracker|CostTracker|cost_tracker" skills/adversarial-spec/scripts skills/adversarial-spec/scripts/tests
rg -n "\\.add\\(" skills/adversarial-spec/scripts skills/adversarial-spec/scripts/tests
```

The first command must return no tracker singleton matches in phase files. The second command must have no production references to old tracker names or direct singleton imports. The third command is an inventory; unrelated collection `.add(...)` calls are allowed after review.

## 15. Deployment and Resume Notes

<!-- Addresses US-4 -->

`~/.claude/skills/adversarial-spec` is currently a symlink to `skills/adversarial-spec`, and Codex loaded this skill from the repo path. Manual copy is not required in this environment.

Final verification must still record one of:

- Deployed path is symlinked and therefore already current.
- Files were copied to deployed skill path.
- User explicitly deferred deployment.

## 16. Open Questions for Debate

These questions are allowed in debate, but they must not expand this session without user approval:

1. Should direct monkeypatches of `record_call` be banned entirely, or permitted for narrow failure-injection tests?
2. Is removing every `cost_tracker` string reference from tests worth the churn, or should historical assertion text be allowed?
3. Does `debate.py` need a local variable rename from `cost_tracker` to `tracker`, or should summary text continue saying "Cost Summary" because dollar cost remains a read-side field?

## 17. Acceptance Criteria

- `TokenTracker` and `tracker` live in `token_tracking.py`.
- Production code has no `CostTracker` or `cost_tracker` symbol.
- Tracker write API is `record_call(...)`.
- Existing read-side fields remain stable.
- Production modules access the mutable singleton through `import token_tracking`, not `from token_tracking import tracker`.
- Gauntlet phase files do not import a tracker singleton.
- Gauntlet model usage is recorded once at `gauntlet/model_dispatch.call_model()`.
- Phase 3 filtering usage is intentionally recorded once through `call_model(...)`.
- Debate/CLI handler placement in `models.py` remains otherwise unchanged.
- Deterministic mocked parity test passes.
- Full suite passes or any blocker is documented with the exact failure.
- CON-002 and CON-001 status are recorded in session/spec artifacts.
