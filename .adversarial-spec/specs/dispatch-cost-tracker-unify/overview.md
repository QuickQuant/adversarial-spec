# Roadmap: Dispatch & Cost-Tracker Unification

> Session: `adv-spec-202604291604-dispatch-cost-tracker-unify`
> Phase: roadmap
> Scope: CON-002 only

## Goals

- Remove gauntlet phase dependency on `models.cost_tracker`.
- Rename cost tracking to token tracking with clear API names.
- Keep model-call behavior unchanged except for the tracking boundary.
- Reduce test monkeypatch surface to one fixture pattern.
- Capture CON-002 remediation and CON-001 drift in durable session/spec artifacts.

## Non-Goals

- CON-001 litellm pathway unification.
- CON-003 orchestrator extraction.
- Manual edits to generated `.architecture` docs solely for hygiene.
- Real model-call parity smoke tests.

## Complexity

**Tier:** medium
**Score:** 8

Internal refactor with several touched modules and a test migration, but no new external integrations.

## Milestone 0: Getting Started - Bootstrap and Audit

**User Stories:**
- US-0: As a maintainer, I want all tracker references audited before edits so that the hard rename does not miss hidden callers or stale monkeypatches.

**Success Criteria:**
- [ ] Full-tree tracker reference inventory exists.
- [ ] Dynamic and string-based monkeypatch sites are included in the audit.
- [ ] Generated architecture board pointer mismatch is corrected in `AGENTS.md`.

**Dependencies:** None

## Milestone 1: Test Fixture Migration

**User Stories:**
- US-1: As a test author, I want a `fresh_tracker` fixture so that tracking tests patch one stable boundary instead of phase-local globals.

**Success Criteria:**
- [ ] `tests/conftest.py` exposes a `fresh_tracker` fixture.
- [ ] Direct monkeypatches of `cost_tracker.add` are removed.
- [ ] Tests remain green before production rename.

**Dependencies:** M0

## Milestone 2: TokenTracker Rename

**User Stories:**
- US-2: As a maintainer, I want `TokenTracker.record_call()` so that token accounting names match actual behavior while existing read-side summaries stay stable.

**Success Criteria:**
- [ ] `token_tracking.py` owns `TokenTracker` and `tracker`.
- [ ] `record_call` replaces `add` across implementation and tests.
- [ ] Read-side fields `total_cost`, `total_input_tokens`, `total_output_tokens`, `by_model`, and `summary()` remain available.

**Dependencies:** M1

## Milestone 3: Gauntlet Dispatch Boundary

**User Stories:**
- US-3: As a gauntlet maintainer, I want `model_dispatch.call_model()` to own gauntlet tracking so that phase files remain focused on phase logic.

**Success Criteria:**
- [ ] `gauntlet/model_dispatch.call_model()` records gauntlet token usage after successful calls.
- [ ] `gauntlet/phase_*.py` files import no tracker singleton.
- [ ] Deterministic mocked dispatch parity proves token totals are preserved.

**Dependencies:** M2

## Milestone 4: Verification and Status Capture

**User Stories:**
- US-4: As a future agent, I want resolved and drifted concern status captured in durable artifacts so that the next session does not re-open CON-001 or lose the reason for CON-002.

**Success Criteria:**
- [ ] CON-002 is recorded as the remediated target.
- [ ] CON-001 is recorded as out-of-scope drift pending next mapcodebase refresh.
- [ ] Repo skill changes are deployed to `~/.claude/skills/adversarial-spec/` or explicitly deferred by the user.
- [ ] All existing tests pass at the final boundary.

**Dependencies:** M3

## Alignment Check

All user stories serve the stated goals. No story implements CON-001, CON-003, manual generated-doc edits, or real model-call parity tests. Roadmap critique added deployment verification because this project requires repo skill changes to be copied into `~/.claude/skills/adversarial-spec/`.
