# Checkpoint: handed-off-to-codex-spec-draft-v1

- **Timestamp (UTC):** 2026-04-29T19:04:44Z
- **Session:** `adv-spec-202604291604-dispatch-cost-tracker-unify`
- **Context:** Dispatch & Cost-Tracker Unification (CON-001 + CON-002)
- **Phase:** debate
- **Step:** Phase 03 entry. Codex produced spec-draft-v1.md after Phase 01/02. Card 1851 G1 gate manually patched (cross-project leak workaround).

## Current Spec Content
- Spec file: `/home/jason/PycharmProjects/adversarial-spec/.adversarial-spec/specs/dispatch-cost-tracker-unify/spec-draft-v1.md`

```markdown
# Technical Spec Draft v1: Dispatch & Cost-Tracker Unification

> Session: `adv-spec-202604291604-dispatch-cost-tracker-unify`
> Scope: CON-002 only
> Roadmap: `.adversarial-spec/specs/dispatch-cost-tracker-unify/manifest.json`
> Tests: `.adversarial-spec/specs/dispatch-cost-tracker-unify/tests-pseudo.md`

## 1. Overview
```

## Completed Work
Phase 01 requirements complete: scope=CON-002 only; CON-001 marked drifted (concerns.md numbers don't match source — only 2 litellm sites, both temp=0.7, neither sets max_tokens). Decisions locked: new token_tracking.py with TokenTracker; .add() -> .record_call(); hard rename, no shim; phase files stop importing singleton; gauntlet/model_dispatch.call_model() owns .record_call(); debate-side asymmetric (per-handler .record_call() stays in models.py:708/759/810/874); fresh_tracker opt-in pytest fixture replaces ~30 monkeypatches; phased commits (tests first, production follows). RequirementsSummary written and user-edited (R5 reframed: don't manually edit .architecture/ docs; let next /mapcodebase regen). Codex advanced through Phase 02 (roadmap manifest, overview, tests-pseudo, fizzy-plan) into Phase 03 producing spec-draft-v1.md (366 lines). Spec adds: Phase 3 filtering side-effect (newly tracked after refactor), cost-formula port spec, deterministic mocked parity test, deployment-via-symlink note. Card 1851 G1 gate unblocked via pipeline_patch_state escape hatch; incident note filed at .adversarial-spec/issues/2026-04-29-human-gate-cross-project-leak.md (root cause: fizzy-pipeline-mcp config.py:137 hardcodes ENABLE_HUMAN_GATES=1, gate tuple in pipeline.py:100 applies to all boards, no relay wired for adversarial-spec, listener service is a stub).

## Next Action
Codex resumes Phase 03 debate. pipeline_advance now passes G1 gate; card 1851 moves Pre-Roadmap -> Debate. Begin Round 1 critique on spec-draft-v1.md.

## Manifest Status
- Roadmap/spec manifest: exists (`/home/jason/PycharmProjects/adversarial-spec/.adversarial-spec/specs/dispatch-cost-tracker-unify/manifest.json`)
- Architecture manifest: exists (status: success, classification: caution)
  - schema version: `2.0`
  - accessor layer: primer.md=yes, access-guide.md=yes
  - freshness: `fresh`
  - generated hash: `9ca3ccd`
  - current hash: `952c19c`
  - dirty worktree at scan: `True`
  - trust note: Fresh = current HEAD with no relevant drift
  - trust note: Incremental update from c3b5f8c (52 commits, 39 source files changed)
  - advisory: architecture docs are usable with caution; review drift before relying on them

## Roadmap Sync
- Result: `skipped_not_installed`

## CLAUDE.md Review
- Next review: `2026-04-25`
- Advisory: review date has passed

## Open Questions
1. Phase 3 filtering token tracking — opt in to new auto-tracking via call_model() or explicitly opt out to preserve historical undercounting? (spec-draft-v1.md §16 Q1)
2. Allow narrow record_call monkeypatches for failure-injection tests, or ban entirely? (§16 Q2)
3. Remove every cost_tracker string reference from tests, or allow historical assertion text? (§16 Q3)
4. Rename cost_tracker local var in debate.py to tracker, or keep 'Cost Summary' text since dollar cost is still a read-side field? (§16 Q4)
5. Permanent fix for fizzy-pipeline-mcp human-gate cross-project leak — separate session, not bundled here.
