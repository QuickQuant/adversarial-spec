# Round 1 Synthesis and Guardrails

Session: `adv-spec-202604291604-dispatch-cost-tracker-unify`
Round instance: `1475ef58aad24263`
Input spec: `spec-draft-v2.md`
Output spec: `spec-draft-v3.md`

## Critic Returns

- `claude-cli/claude-opus-4-7`: completed, did not agree, 7 findings.
- `gemini-cli/gemini-3.1-pro-preview`: completed, did not agree, 3 findings.
- Prior local Codex critique: already applied to `spec-draft-v2.md`.

## Accepted Findings

- Add explicit two-phase `fresh_tracker` fixture migration so the fixture is implementable before `token_tracking.py` exists.
- Require pre-rename audit of `call_model(...)` tuple unpack shapes before relying on the 3-tuple invariant.
- Ban module-level local rebinds of `token_tracking.tracker`, not only `from token_tracking import tracker`.
- Expand deterministic parity coverage to include each gauntlet phase call pattern plus LiteLLM and all three CLI prefixes.
- Refine audit commands so `.add(...)` inventory is not swamped by unrelated collection methods.
- Resolve the `debate.py` local variable naming question inside the spec.
- Add exact symlink verification command.
- List `phase_3_filtering.py` in current state as currently untracked but intentionally tracked after the boundary move.
- Add a developer user journey section.
- Add explicit error-handling/concurrency requirements for `TokenTracker.record_call(...)`.
- Update `tests-pseudo.md` to cover the new fixture-order, singleton-rebind, invalid-token, CLI-prefix, and symlink checks.

## Rejected or Constrained Findings

- Gemini suggested choosing between coercing invalid token counts to zero or raising `ValueError`. The synthesized spec does not choose a behavior blindly; it requires preserving audited current behavior unless a deliberate `ValueError` change is added with tests and spec update.
- No finding expands scope to CON-001, CON-003, retry behavior, timeout behavior, or generated architecture-doc editing.

## Guardrail Results

- CONS: pass. Section references resolve after inserting User Journey; unresolved open questions moved to Resolved Decisions.
- SCOPE: pass. New material is implementation-order, test, and doc-quality detail for CON-002. CON-001 remains explicitly out of scope.
- TRACE: pass. US-0 through US-4 still map to spec sections and tests-pseudo coverage.
- CANON: pass. No new repeated domain literal unions or canonical domain enum references were introduced.

## Verification

- `python3 -m json.tool` passed for `manifest.json`, `trello-plan.json`, and `.adversarial-spec/session-state.json`.
