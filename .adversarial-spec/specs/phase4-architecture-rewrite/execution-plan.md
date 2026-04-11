# Execution Plan: Phase 4 Architecture Rewrite

**Session:** `adv-spec-202604021743-phase4-architecture-rewrite`
**Spec:** `.adversarial-spec/specs/phase4-architecture-rewrite/spec-output.md` (v17, 1481 lines)
**Tests:** `.adversarial-spec/specs/phase4-architecture-rewrite/tests-spec.md` (448 lines)
**Gauntlet concerns:** `.adversarial-spec/gauntlet-concerns-2026-04-03.json` (19 accepted, 4 acknowledged — all incorporated in v17)
**Plan commit target:** `main`

## Summary

- **Tasks:** 8 (S: 5, M: 3, L: 0)
- **Workstreams:** 1 (single-agent, sequential with bounded parallelism within waves)
- **Gauntlet concerns addressed:** 19 of 19 accepted (already baked into v17 during rounds 1-13)
- **Estimated effort:** Medium
- **Scope:** Documentation rewrite + cross-reference updates + deployment. **No code changes.**

## Scope Assessment

This is a **meta-spec**: v17 describes the new Phase 4 (target-architecture) phase doc of the adversarial-spec skill itself. The deliverable is a rewrite of `skills/adversarial-spec/phases/04-target-architecture.md` (currently 225 lines) to match the full v17 specification (1481 lines), plus cross-reference updates in adjacent phase docs and deployment to `~/.claude/skills/adversarial-spec/`.

**Blast zone:**
- `skills/adversarial-spec/phases/04-target-architecture.md` — complete rewrite
- `skills/adversarial-spec/phases/02-roadmap.md` — cross-reference to invariant tests
- `skills/adversarial-spec/phases/05-gauntlet.md` — adversary briefing inputs (concern x surface matrix, triggered concerns)
- `skills/adversarial-spec/phases/07-execution.md` — consume `middleware-candidates.json`, verify `phase_artifacts.spec_fingerprint`
- `skills/adversarial-spec/SKILL.md` — register `middleware-creator` as optional phase between `finalize` and `execution`
- `~/.claude/skills/adversarial-spec/phases/` — deployment target

**Components impacted:** NONE. This rewrite only touches phase doc markdown and `SKILL.md`. No Python modules (debate.py, gauntlet/, models.py, providers.py, etc.) are modified.

**Middleware identification:** NONE. Documentation rewrites produce no typed interfaces. The `middleware-candidates.json` artifact is empty for this session.

## Architecture Spine

**N/A.** This execution does not require cross-cutting architecture patterns — it is a documentation rewrite with no runtime components. Wave 0 skipped.

## Tasks

### Wave 1: Core Phase-Doc Rewrite

#### T1: Rewrite 04-target-architecture.md from v17 spec

- **Effort:** M (large markdown copy + phase-doc restructuring)
- **Strategy:** test-after — content is deterministic from spec; tests-spec.md validates structure
- **Spec refs:** v17 spec §§0–22 (entire document)
- **Concerns addressed:** CB-1..CB-6, RC-1, FM-1..FM-5, SEC-1, SEC-2, OP-1, OP-2, DD-1, DD-2, US-1 (all 19 accepted gauntlet concerns — already in v17, must survive rewrite)
- **Acceptance criteria:**
  - [ ] Target file: `skills/adversarial-spec/phases/04-target-architecture.md`
  - [ ] Contains phase-doc entry TodoWrite block (§1) including `draft_review` and `final_approval` [GATE] items
  - [ ] Contains all three context modes: greenfield, brownfield_feature, brownfield_debug (§§3, 7, 12, 13)
  - [ ] Canonical enums section present with cli_command, public_api, data_stream, plus cli_parsing/idempotency/api_compatibility/data_integrity (§§0.25, 0.41)
  - [ ] Bootstrap Contract with fingerprint lifecycle (§0.5) — freeze-state computation
  - [ ] Human Gate Protocol (§0) defining scale_check, context_mode, draft_review, final_approval
  - [ ] Required headers for target-architecture.md yaml include `architecture_fingerprint` (§7)
  - [ ] §7.5 Middleware Interface Identification with `linked_goals` in candidate schema
  - [ ] §10.5 Required Check Derivation mandates observability for CLI and data_stream surfaces
  - [ ] §15 Session Mutation Contract references `fizzy_card_id` (not `trello_card_id`)
  - [ ] §6.3 category-native matrix column constraint present
  - [ ] All sections §0 through §22 + Open Questions present
  - [ ] YAML frontmatter / heading style matches sibling phase docs (02-roadmap, 03-debate, 05-gauntlet, 06-finalize, 07-execution)
- **Dependencies:** None
- **Test refs:** TC-3.1, TC-4.1–TC-4.4, TC-5.1–TC-5.3, TC-6.1–TC-6.4, TC-7.1–TC-7.2, TC-8.1–TC-8.4, TC-9.1–TC-9.5, TC-10.1, TC-11.1–TC-11.2, TC-12.1–TC-12.2, TC-13.1–TC-13.4
- **Dispatch:** Claude (doc-heavy, stakes are high — do not dispatch to CLI worker for a 1400+ line rewrite in this execution)

#### T2: Update 02-roadmap.md cross-references for invariant-tests integration

- **Effort:** S
- **Strategy:** test-after
- **Spec refs:** v17 §20 Migration Plan → Cross-Reference Updates
- **Concerns addressed:** None (downstream consumer doc)
- **Acceptance criteria:**
  - [ ] Target file: `skills/adversarial-spec/phases/02-roadmap.md`
  - [ ] References `<!-- P4_INVARIANT_TESTS_START -->` / `<!-- P4_INVARIANT_TESTS_END -->` marker protocol for tests-pseudo.md upsert
  - [ ] Notes that Phase 4 upserts invariant tests and this is NOT appended repeatedly on reruns
  - [ ] Points to `04-target-architecture.md §8.3` as the normative source for the upsert contract
- **Dependencies:** T1 (reference §8.3 must exist)
- **Test refs:** TC-3.2
- **Dispatch:** Gemini CLI or Codex CLI (simple cross-ref update, appropriate for worker)

#### T3: Update 05-gauntlet.md cross-references for adversary briefing inputs

- **Effort:** S
- **Strategy:** test-after
- **Spec refs:** v17 §22 Phase Interactions → Phase 5
- **Concerns addressed:** None
- **Acceptance criteria:**
  - [ ] Target file: `skills/adversarial-spec/phases/05-gauntlet.md`
  - [ ] Adversary briefing inputs reference framework profile, surface map, concern x surface matrix, invariant set, and triggered concerns
  - [ ] Adversary-to-concern mapping documented: BURN→observability+realtime, PARA→enforcement/auth/security/trust, LAZY→enforcement bypass, COMP→SoT/brownfield compatibility
  - [ ] Points to `04-target-architecture.md §§6, 8` as the normative source for concern + invariant definitions
- **Dependencies:** T1
- **Test refs:** TC-3.2
- **Dispatch:** Gemini CLI or Codex CLI

#### T4: Update 07-execution.md cross-references for invariant/middleware consumption

- **Effort:** S
- **Strategy:** test-after
- **Spec refs:** v17 §22 Phase Interactions → Phase 7, §15 Session Mutation Contract (spec_fingerprint staleness check)
- **Concerns addressed:** OP-1 (Phase 7 stale architecture consumption)
- **Acceptance criteria:**
  - [ ] Target file: `skills/adversarial-spec/phases/07-execution.md`
  - [ ] Documents consumption of `middleware-candidates.json` when present (advisory in lightweight, normative in full)
  - [ ] Documents staleness check: Phase 7 must verify `phase_artifacts.spec_fingerprint` against current spec before consuming architecture artifacts
  - [ ] Task generation references invariant IDs and surface scope
  - [ ] High-risk tasks (3+ invariants) marked test-first
- **Dependencies:** T1
- **Test refs:** TC-3.2
- **Dispatch:** Gemini CLI or Codex CLI

#### T5: Register middleware-creator as optional phase in SKILL.md

- **Effort:** S
- **Strategy:** test-after
- **Spec refs:** v17 §22 Phase Interactions → Middleware-Creator (proposed, not yet registered)
- **Concerns addressed:** None (documentation-only registration; no phase logic changes)
- **Acceptance criteria:**
  - [ ] Target file: `skills/adversarial-spec/SKILL.md`
  - [ ] Phase router documents `requirements | roadmap | debate | target-architecture | gauntlet | finalize | middleware-creator? | execution | implementation`
  - [ ] `middleware-creator` explicitly marked optional and preceded by finalize
  - [ ] Prerequisite note: phase is passive until a phases/middleware-creator.md doc is written — v17 does not author that doc (per non-goals)
  - [ ] No phase dispatch logic changes — only documentation of the intended router shape
- **Dependencies:** T1 (cross-references §22 content)
- **Test refs:** TC-3.2
- **Dispatch:** Claude (touches SKILL.md which is sensitive; keep in Claude's lane)

### Wave 2: Deploy and Smoke-Verify

#### T6: Deploy phase docs to ~/.claude/skills/adversarial-spec/ with backup

- **Effort:** S
- **Strategy:** test-after (deployment is file copy; verification via T7/T8)
- **Spec refs:** v17 §19 Deployment Strategy
- **Concerns addressed:** None
- **Acceptance criteria:**
  - [ ] Generate `release_id`: `p4-YYYYMMDD-<short-hash>`
  - [ ] Backup current deployed files to `~/.claude/skills/adversarial-spec/.backup/<release_id>/`
  - [ ] Copy updated phase docs: 02-roadmap.md, 04-target-architecture.md, 05-gauntlet.md, 07-execution.md, SKILL.md
  - [ ] Use atomic rename (write to temp path, then mv)
  - [ ] Checksum verification: `sha256sum` source vs deployed match for each file
  - [ ] Record deployment to `.adversarial-spec/release-log.jsonl` with `release_id` and file list
- **Dependencies:** T1, T2, T3, T4, T5
- **Test refs:** None (Section 19 of v17 defines but no explicit TC — rolled into T7/T8 verification)
- **Dispatch:** Claude (deployment touches user home dir; do not delegate to CLI worker)

#### T7: Smoke-run greenfield scenario against deployed Phase 4 doc

- **Effort:** M
- **Strategy:** test-after
- **Spec refs:** v17 §§1–11 (greenfield flow)
- **Concerns addressed:** None (integration verification)
- **Acceptance criteria:**
  - [ ] Fresh agent reads `~/.claude/skills/adversarial-spec/phases/04-target-architecture.md`
  - [ ] Agent can identify the required TodoWrite block including `draft_review` and `final_approval` gates
  - [ ] Agent can list all 12 surface_id enum values (including cli_command, public_api, data_stream)
  - [ ] Agent can list all 15 dry_run_check_id enum values
  - [ ] Agent can describe fingerprint lifecycle (scaffold → draft → frozen → published)
  - [ ] Given a synthetic 3-story / 2-surface / 2-concern roadmap, agent produces valid phase4_bootstrap record, phase_mode selection, and context_mode selection without halt
  - [ ] No dangling references to removed Phase 4 concepts (verify via grep)
- **Dependencies:** T6
- **Test refs:** TC-3.1, TC-5.1, TC-9.1, TC-9.2, TC-10.1
- **Dispatch:** Can dispatch to Gemini CLI as a pure "read + describe" worker task; Claude runs the verification pass

#### T8: Smoke-run brownfield scenario against deployed Phase 4 doc

- **Effort:** M
- **Strategy:** test-after
- **Spec refs:** v17 §§12, 13 (brownfield feature + brownfield debug flows)
- **Concerns addressed:** None
- **Acceptance criteria:**
  - [ ] Fresh agent can select brownfield_feature given "adding feature to existing codebase" scenario
  - [ ] Agent produces blast zone + touched surfaces + touched concerns
  - [ ] Agent runs concern fitness assessment: adequate | needs_extension | missing | conflicts
  - [ ] Agent flags `now`-severity existing debt when concern is adequate but reinforces anti-pattern
  - [ ] Brownfield_debug variant: agent identifies failed concern + failed surface, runs local-vs-systemic decision, classifies invariant gap
  - [ ] Agent references §22 to confirm Phase 7 staleness check applies
- **Dependencies:** T6
- **Test refs:** TC-2.2, TC-3.1, TC-3.2
- **Dispatch:** Can dispatch to Gemini CLI; Claude verifies

## Dependency Graph

```
T1 ──┬── T2
     ├── T3
     ├── T4
     └── T5 ──┐
              ├── T6 ──┬── T7
              │        └── T8
T2 ──────────┤
T3 ──────────┤
T4 ──────────┘
```

Wave 1 tasks T2/T3/T4 are independent after T1 completes and can run in parallel. T5 depends on T1 only but is kept in Wave 1 for organization. T6 (deploy) requires all Wave 1 tasks. T7 and T8 run in parallel after T6.

## Workstream / Dispatch Plan

- **Claude (main):** T1 (large rewrite), T5 (SKILL.md), T6 (deployment), final verification of T7/T8
- **Gemini CLI worker:** T2 or T3 or T4 (any of the 3 cross-ref updates)
- **Codex CLI worker:** T2 or T3 or T4 (the other cross-ref updates)
- **Gemini/Codex as verifier:** T7/T8 read-only smoke checks

Per user's overnight mode: "the codex and gemini CLIs are ready to help execute once it gets there, so dont hesitate to dispatch when its time". T2/T3/T4 are good candidates because they are self-contained, small, and have clear acceptance criteria.

## Uncovered Concerns

**None.** All 19 accepted gauntlet concerns were incorporated into v17 during rounds 1–13 and gauntlet synthesis (v10→v11). The 4 acknowledged concerns (RC-2, SEC-2-ack, DD-3, US-2) were deferred by intent, not by oversight. Middleware-creator registration is covered by T5 but is explicitly marked as documentation-only per roadmap non-goal "Implementing downstream tool integrations (future work)".

## Risk Register

| Risk | Mitigation |
|------|-----------|
| T1 rewrite drops a v17 section during copy | Grep-based section checklist in acceptance criteria; verify via diff against spec-output.md sections |
| Cross-ref tasks point to wrong section numbers after T1 restructures | T2/T3/T4 run AFTER T1 confirms final section numbering |
| T6 deployment overwrites user's uncommitted changes in ~/.claude/skills/ | Mandatory backup step before copy; release_id recorded |
| Codex CLI is flaky (history: timeout at 1800s, exit code 1 in rounds 13/14) | Keep T1 and T6 on Claude; dispatch only T2/T3/T4 to CLI workers |
| fizzy-plan.json schema mismatch | Validated against pipeline_load expected schema during T6 setup |

## Notes for Implementation Phase

- v17 is committed at `2d87dc1`. All changes land on `main`.
- The current `skills/adversarial-spec/phases/04-target-architecture.md` at 225 lines is the old version — T1 replaces it fully, not incrementally.
- Cross-ref updates in T2/T3/T4 must preserve existing sibling content and only insert/update the specific sections mentioned in acceptance criteria.
- T6 deployment copies from `skills/adversarial-spec/phases/*` to `~/.claude/skills/adversarial-spec/phases/*` — one level up from SKILL.md. Make sure paths are correct.
- After T8 completes, transition session to `implementation` phase (per SKILL.md router).
