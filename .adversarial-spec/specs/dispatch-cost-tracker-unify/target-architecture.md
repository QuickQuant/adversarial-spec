---
schema_version: "1.0"
spec_slug: "dispatch-cost-tracker-unify"
phase_mode: "lightweight"
context_mode: "brownfield_debug"
framework: "Python CLI package"
framework_version: "Python >=3.10; package adversarial-spec 1.0.0"
surfaces: ["cli_command", "public_api"]
roadmap_path: ".adversarial-spec/specs/dispatch-cost-tracker-unify/manifest.json"
tests_pseudo_path: ".adversarial-spec/specs/dispatch-cost-tracker-unify/tests-pseudo.md"
architecture_fingerprint: null
---

# Target Architecture: Dispatch and Token Tracking Boundary

## Overview

This lightweight target architecture covers the brownfield debug path for CON-002: gauntlet phase modules currently import the debate-engine `models.cost_tracker` singleton and write accounting records directly. The fix is systemic, not local: token accounting writes move to the gauntlet dispatch boundary while read-side summaries remain available to orchestration.

The architecture does not reopen CON-001 LiteLLM dispatch unification or CON-003 orchestrator extraction.

## Goals and Non-Goals

Goals:

- Remove gauntlet phase dependency on `models.cost_tracker`.
- Rename cost tracking to `TokenTracker.record_call()` with stable read-side fields.
- Preserve model dispatch behavior and `call_model(...)` return shape.
- Make tracker test isolation use one mutable module patch point.
- Record CON-002 remediation and CON-001 drift in durable artifacts.

Non-goals:

- No LiteLLM pathway unification.
- No gauntlet orchestrator extraction.
- No generated `.architecture` document edits solely for hygiene.
- No real model-call parity smoke tests.

## Framework Profile

```json
{
  "profile_type": "single",
  "category": "cli",
  "framework": "Python CLI package",
  "framework_version": "Python >=3.10; package adversarial-spec 1.0.0",
  "runtime": "python",
  "deployment_target": "serverful",
  "enabled_features": ["argparse", "ThreadPoolExecutor", "subprocess", "FileLock"],
  "subprofiles": {
    "rendering_model": "N/A",
    "data_access_model": "module-level services and file artifacts",
    "mutation_model": "CLI commands and in-process function calls",
    "cache_model": "N/A",
    "error_model": "Python exceptions plus CLI exit codes"
  },
  "enforcement_model": "CLI model-name validation remains in gauntlet/model_dispatch.py; token accounting writes are enforced by resolving token_tracking.tracker at call time inside dispatch and model-handler boundaries."
}
```

## Applicable Execution Surfaces

| Surface | Scope | Existing entrypoints | Phase 4 focus |
|---------|-------|----------------------|---------------|
| `cli_command` | Debate and gauntlet CLI execution paths | `debate.py`, `gauntlet/cli.py`, `gauntlet/orchestrator.py` | Preserve CLI-visible model-call behavior and cost summary output while moving the write boundary. |
| `public_api` | Internal module APIs consumed across gauntlet phases and tests | `models.ModelResponse`, `gauntlet/model_dispatch.call_model()`, tracker read fields | Keep stable tuple/read contracts and prevent singleton rebinding that would break `fresh_tracker`. |

## Concern Assessments

### CON-002 Layer Boundary and Source of Truth

**Decision:** Centralize gauntlet token accounting writes in `gauntlet/model_dispatch.call_model()` and debate-side handler writes in `models.py`; make `token_tracking.py` the tracker source of truth.

**Surfaces:** `cli_command`, `public_api`

**Goals/NFRs:** Goals 1, 2, 3, 4

**User stories:** US-0, US-1, US-2, US-3

**Framework primitive:** Python module boundary with mutable module attribute patching.

**Default status:** custom

**Why sufficient/insufficient:** The previous Python default of importing a mutable singleton into each phase was insufficient because it created many independent monkeypatch targets. A module-qualified access pattern, `token_tracking.tracker`, keeps one patch point and makes the write owner explicit.

**Rationale:** Local architecture docs identify `models.py` as the LLM abstraction and gauntlet phases as model dispatch consumers. The spec narrows the fix to CON-002 and preserves existing dispatch behavior.

**Alternative considered:** Keep phase-level writes and only rename `CostTracker` to `TokenTracker`. Rejected because it preserves the layer violation and test patch sprawl.

**Failure mode prevented:** A future phase adds or changes a model call and forgets token accounting, double-records it, or requires a new phase-local monkeypatch.

**Implementation sketch:** Create `token_tracking.py`; update production modules to `import token_tracking`; write through `token_tracking.tracker.record_call(...)` at dispatch boundaries; delete phase-level tracker imports and write calls.

**Invariant refs:** INV-001, INV-002, INV-003

**Test hook:** TC-INV-001, TC-INV-002, TC-INV-003

### Model Dispatch Contract Preservation

**Decision:** `gauntlet/model_dispatch.call_model()` remains the public dispatch API for gauntlet phases and keeps returning `(content, input_tokens, output_tokens)`.

**Surfaces:** `public_api`

**Goals/NFRs:** Goals 3, 4

**User stories:** US-0, US-3

**Framework primitive:** Function contract plus deterministic mocked tests.

**Default status:** custom

**Why sufficient/insufficient:** A broad Python refactor could accidentally include cost in the return tuple or change CLI/LiteLLM arguments. The stable tuple contract makes the accounting boundary invisible to phase callers.

**Rationale:** Current source and architecture docs show gauntlet phases already consume `call_model(...)` and manually record token usage afterward. The architecture change should remove only the accounting side effect from phases.

**Alternative considered:** Return `(content, input_tokens, output_tokens, cost)`. Rejected because it expands every phase caller and contradicts the converged spec.

**Failure mode prevented:** Phase caller churn and accidental behavior changes in model dispatch, timeout, JSON mode, temperature, or CLI prefix routing.

**Implementation sketch:** Add recording inside `call_model(...)` after successful model response, then return the same three-tuple. Audit all tuple unpacking before production rename.

**Invariant refs:** INV-001, INV-002

**Test hook:** TC-INV-001, TC-INV-002

### Tracker Isolation for Tests

**Decision:** Tests that need isolated accounting state use `fresh_tracker`, which patches the module attribute owning the singleton.

**Surfaces:** `public_api`

**Goals/NFRs:** Goals 2, 4

**User stories:** US-1, US-2

**Framework primitive:** Pytest fixture plus monkeypatch of a module attribute.

**Default status:** custom

**Why sufficient/insufficient:** Direct monkeypatches of phase-local imported singleton methods were insufficient because every import site became a patch point. A fixture against `token_tracking.tracker` is sufficient only if production modules do not bind the singleton locally at import time.

**Rationale:** This directly supports the two-phase fixture migration in the spec and keeps tests resilient during the hard rename.

**Alternative considered:** Patch `record_call` methods directly in every consumer. Rejected because it repeats the current failure mode with a new method name.

**Failure mode prevented:** Tests that pass by patching one stale local binding while production resolves a different tracker instance.

**Implementation sketch:** Before production move, fixture patches `models.cost_tracker`. After `token_tracking.py` lands, fixture patches `token_tracking.tracker`; production modules access `token_tracking.tracker` at call time.

**Invariant refs:** INV-002, INV-003

**Test hook:** TC-INV-002, TC-INV-003

## Concern x Surface Matrix

| Concern | `cli_command` | `public_api` |
|---------|---------------|--------------|
| Source of truth | CLI cost summaries read totals from `token_tracking.tracker`; owner is `token_tracking.py`; INV-001. | `token_tracking.py` owns `TokenTracker` and `tracker`; consumers must not define `CostTracker` or `cost_tracker`; INV-001. |
| Enforcement | Static audit blocks phase-level tracker imports and module-level singleton rebinds; INV-002. | Production access pattern is `import token_tracking` then call-time resolution of `token_tracking.tracker`; INV-002. |
| Error handling | Existing model-call failure behavior remains unchanged; no tracking write after failed calls; INV-001. | `call_model(...)` tuple shape is unchanged so callers keep existing error flow; INV-001. |
| Validation | Existing model name validation stays in `gauntlet/model_dispatch.py`; token values follow audited current behavior; INV-001. | Audit verifies tuple unpacking before boundary move; INV-001. |
| Source of truth and concurrency | `TokenTracker.record_call(...)` keeps aggregate mutation under `_lock`; INV-003. | `fresh_tracker` can replace the singleton for deterministic tests because production resolves the module attribute at call time; INV-003. |
| Observability | Cost summary display strings may remain "Cost Summary" but read from tracker fields; INV-001. | Static checks provide reviewer-visible evidence of no stale tracker names; INV-002. |

## Architectural Invariants

INV-001: [category:sot] Token accounting writes happen exactly once at the active model dispatch boundary for each successful model call.

INV-002: [category:enforcement] Production modules do not import or bind the tracker singleton directly; they resolve `token_tracking.tracker` at call time.

INV-003: [category:validation] Test isolation uses the public tracker owner module as the single patch point and does not rely on phase-local tracker monkeypatches.

## Middleware Candidates

No middleware fanout is recommended for this lightweight architecture pass. `TokenTracker` is a focused utility class, but this session already specifies it directly and does not require competitive middleware implementation.

## Dry-run Summary

Passed. Lightweight dry-run verified two archetypes:

- `public_api` write path: gauntlet phase caller -> `gauntlet/model_dispatch.call_model()` -> tracker record -> unchanged three-tuple return.
- `cli_command` read path: CLI-visible cost summary reads remain stable through `total_cost`, `total_input_tokens`, `total_output_tokens`, `by_model`, and `summary()`.

Results are recorded in `.adversarial-spec/specs/dispatch-cost-tracker-unify/dry-run-results.json`.

## Open Questions

- None for Phase 4 draft review.
