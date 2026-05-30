# RequirementsSummary: Dispatch & Cost-Tracker Unification

> Session: `adv-spec-202604291604-dispatch-cost-tracker-unify`
> Phase: requirements (Phase 01)
> Fizzy card: 1851
> Origin: Branched from TMV (paused on session_stack). Triaged from `.architecture/concerns.md` CON-001 + CON-002.
> Doc type: spec / depth: technical

## Scope Decision

**In scope:** CON-002 only — eliminate the layer violation where 7 gauntlet phase files import the global `cost_tracker` singleton from `models.py`.

**Out of scope:**
- **CON-001 (triple litellm pathway)** — out of scope for this session. Investigation showed the original numbers in concerns.md (`max_tokens 4000 vs 4096 vs 8000`) do not match source code; both real call sites use `temperature=0.7` and neither sets `max_tokens`. Only two files (not three) call `litellm.completion` directly: `models.py:860` and `gauntlet/model_dispatch.py:119`. The actual divergence (retry loop, Bedrock error mapping, json_mode) is small enough that re-debating the boilerplate is not worth a session.
- **CON-003 (orchestrator extraction)** — separate, larger session.
- **`gauntlet/cli.py`** — verified clean (no `cost_tracker`/`models`/`litellm` imports). Untouched.

## Ground-Truth Findings (from source, not concerns.md)

- `cost_tracker` is **load-bearing** even in CLI-only runs. CLI handlers (Codex/Gemini-CLI/Claude-CLI) call `.add()` at `models.py:708, 759, 810`. CLI cost-per-token is `$0.00` in `MODEL_COSTS`, but `input_tokens`/`output_tokens` are populated and tracked. `orchestrator.py:77` reads `total_input_tokens`/`total_output_tokens` for run stats. The "cost" name is misleading — it is really a token-and-cost tracker.
- The litellm path is **idle but not dead** — supports NVIDIA NIM (added Feb 2026) and any non-subscription provider in `MODEL_COSTS`.
- 7 gauntlet phase files reach across into `models.py`: `phase_1_attacks.py`, `phase_2_synthesis.py`, `phase_4_evaluation.py`, `phase_5_rebuttals.py`, `phase_6_adjudication.py`, `phase_7_final_boss.py`, and `orchestrator.py` (orchestrator reads totals only — that stays).
- ~30 test monkeypatch sites match concerns.md count, spread across `test_gauntlet_phase_1_attacks.py`, `test_gauntlet_phase_config.py`, `test_gauntlet_error_guards.py`, `test_gauntlet_orchestrator.py`, `test_model_calls.py`.

## Requirements

### R1 — Module & class rename (hard rename, no shim)

- New module: `skills/adversarial-spec/scripts/token_tracking.py`.
- Class: `TokenTracker` (renamed from `CostTracker`).
- Method: `.add(model, in_tokens, out_tokens)` → `.record_call(model, in_tokens, out_tokens)`.
- Read-side names preserved for backward compatibility within this codebase: `total_cost`, `total_input_tokens`, `total_output_tokens`, `by_model`, `summary()`.
- Module-level singleton: `tracker` (replaces `cost_tracker`).
- No deprecation shim — internal tool, single user, single repo.

### R2 — Layer rule

- **Phase files do NOT import the singleton.** Any code in `gauntlet/phase_*.py` that previously called `cost_tracker.add(...)` is removed.
- `gauntlet/model_dispatch.call_model()` becomes the **single tracking site** for the gauntlet path. It calls `tracker.record_call(...)` after every successful LLM call.
- `orchestrator.py` keeps reading `tracker.total_input_tokens` / `tracker.total_output_tokens` — that's a legitimate cross-layer read of public API.

### R3 — Debate-side asymmetry (locked)

- The four `.record_call()` sites in `models.py` (lines 708, 759, 810, 874 — Codex CLI, Gemini CLI, Claude CLI, litellm) **stay where they are**. The per-handler functions retain responsibility for tracking their own returned tokens.
- Rationale: smaller blast radius; behavior-equivalent refactor of a hot path is not justified by current evidence. Asymmetry with the gauntlet rule is acceptable and documented.

### R4 — Test redesign

- New pytest fixture `fresh_tracker` in `tests/conftest.py` (opt-in, not autouse). Yields a fresh `TokenTracker` and patches the module singleton for the test's duration.
- All ~30 `monkeypatch.setattr(...cost_tracker.add, ...)` sites are replaced by inclusion of the `fresh_tracker` fixture in the affected test signature.
- `test_cost_tracker_thread_safety` migrates to the new module/class but keeps its concurrency assertions intact.

### R5 — Architecture documentation hygiene

- Do not manually edit generated historical `.architecture/concerns.md` or `.architecture/findings.md` solely for this refactor. These files are mapcodebase output and may be overwritten on the next run.
- Record the source-verified status in durable session/spec artifacts instead: CON-002 is the active remediation; CON-001 is out of scope because the generated concern drifted from source.
- Next `/mapcodebase` run should regenerate architecture docs so future agents see CON-002 as resolved and CON-001 as drifted/not actionable.

## Open Questions for Debate Phase

The following are **not** pre-decided. Phase 03 opponent models are expected to weigh in:

- **Q1 — Retry / error semantics divergence.** Today the gauntlet path has no retry loop; the debate path has 3 retries with exponential backoff. Is preserving that divergence the right call, or should `gauntlet/model_dispatch.call_model()` adopt the same retry shape? (Constraint: any change here is behavior-affecting and must be justified by evidence, not preference. CON-001 remains out of scope unless the user explicitly opens a follow-up session.)
- **Q2 — Should the per-handler `.record_call()` sites in `models.py` eventually move into `call_models_parallel()`?** R3 locks "no" for this spec, but the debate may surface a stronger argument. If so, that's a follow-up spec, not a scope expansion here.
- **Q3 — Should `total_cost` also be renamed?** R1 locks read-side names for compat; debate may argue the rename should be total (e.g., `total_dollars` and `total_tokens` as separate properties).

## Sequencing (Phased: tests first, production follows)

- **Commit 1 — Test scaffolding.**
  - Introduce `fresh_tracker` fixture in `tests/conftest.py` against the *current* `cost_tracker` symbol.
  - Migrate the ~30 test monkeypatches to use the fixture.
  - Tests still green; production code unchanged.
  - Proves the fixture pattern works before touching production.
- **Commit 2 — Production rename + dispatcher fix.**
  - Create `token_tracking.py` with `TokenTracker` + `tracker` singleton.
  - Rename `.add` → `.record_call` (call sites updated atomically).
  - Move `.record_call()` out of every `gauntlet/phase_*.py` and into `gauntlet/model_dispatch.call_model()`.
  - Remove `from models import cost_tracker` from all 7 phase files.
  - Update `orchestrator.py` to import totals from `token_tracking`.
  - Update fixture to patch `token_tracking.tracker`.
  - Do not manually edit generated `.architecture/` docs; record resolution/drift in session/spec artifacts and rely on the next mapcodebase run to refresh generated architecture docs.
- Either commit reverts cleanly without breaking the other.

## Risks (all surface in spec)

| # | Risk | Mitigation |
|---|------|------------|
| RK-1 | Hidden silent `.add()` callers (dynamic imports, monkeypatch strings, `getattr` usage that grep misses) | Pre-rename audit: full-tree grep for `cost_tracker`, `cost_tracker.add`, `"cost_tracker"`, `"add"` near tracker context. Document the audit in the spec. |
| RK-2 | Token-count drift in stats — silent undercounting if a handler call is missed | Deterministic mocked dispatch parity test: same fake model responses before/after refactor must produce identical `by_model` totals without real model calls. |
| RK-3 | Thread-safety regression after class rename | `test_cost_tracker_thread_safety` (renamed `test_token_tracker_thread_safety`) must continue to pass; lock semantics migrate intact. |

## Success Criteria (all three combined)

1. **Zero phase imports.** `grep -r "cost_tracker\|token_tracker" skills/adversarial-spec/scripts/gauntlet/phase_*.py` returns 0 hits.
2. **Token totals match before/after.** A deterministic mocked dispatch test produces identical `by_model` token totals pre- and post-refactor for the same input.
3. **Single test patch point.** No `monkeypatch.setattr(...cost_tracker.add, ...)` (or equivalent) survives. All tracking-relevant tests use `fresh_tracker`.

All 457 existing tests must remain green at every commit boundary.

## Constraints Carried Forward

- Preserve per-call-site `temperature` and (absent) `max_tokens` defaults — do not homogenize accidentally during the rename.
- CLI subprocess paths (Codex/Gemini-CLI/Claude-CLI) keep their inline `.record_call()` calls in `models.py` per R3.
- The hard rename is intentional and safe if done test-first: introduce fixture coverage, audit all references, update callers atomically, preserve read-side fields, and require full tests green at each commit boundary.
- The session was branched from TMV (`adv-spec-202604111912-test-mapping-verification-gates`); TMV remains paused on `session_stack` and resumes after this spec lands.
