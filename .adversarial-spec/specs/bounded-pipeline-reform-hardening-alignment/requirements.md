# Requirements — Bounded Pipeline Reform & Hardening Alignment

**Session:** `adv-spec-202609150549-bounded-reform-hardening-align` · **Phase:** 1 (requirements) · **Draft:** v0.2, 2026-09-15 (v0.1 confirmed by the Master Conductor with OQ-1..6; v0.2 folds roadmap debate R1)
**Doc type:** spec · **Depth:** full · **Root altitude:** system (declared at triage; see plan doc)
**Status:** CONFIRMED v0.1 (2026-09-15); v0.2 additions (US-13..16, INV-10, RB-1, OQ-7/8) await the roadmap gate.

The interview corpus for this draft is the hardening packet, the two cross-vendor reviews, the bounded-pipeline ruleset and open decisions, and the four fixes already landed. No live interview was possible; every open question that an interview would have answered is listed in §8 for the operator.

## 1. Problem

Across the March–September 2026 incidents, tests proved input reality but not proof-target identity: the wrong caller, route, process, or contract passed. adversarial-spec's REAL-DATA policy was never the gap. The missing control is a second, orthogonal axis — did the evidence hit the intended authority, caller, path, contract, and runtime — plus the bookkeeping that makes authority migration and temporary custody close itemized instead of inferred. Three concrete contradictions were reproduced (Defects A, B, C); A and B are patched, C is specified but not built.

## 2. Users

| id | user | needs |
| --- | --- | --- |
| UT-1 | Conductor (claude) running a session | authoring templates that make target binding cheap when triggered and invisible when not |
| UT-2 | Worker seats (codex, gemini) implementing and reviewing cards | typed reject codes, not prose, at every gate they can hit |
| UT-3 | Operator (Jason) | destructive actions never inferred; itemized previews; grandfathered in-flight work |
| UT-4 | fizzy-pipeline-mcp (consumer of emitted plans and TMRs) | one versioned cross-repo contract, validate/load parity |
| UT-5 | Downstream maintainer (prediction-prime first) | adoption guide, v5→v6 migration path, ordinary single-path work pays no new tax |
| UT-6 | Integration maintainer (keystone, skill, Fizzy consumer) | one named owner per shared contract; consumers validate their declared scope only |

## 3. Goals

- G-1 Add proof-target identity as an orthogonal axis to REAL-DATA without weakening it (packet decision 1, 2).
- G-2 Surface authority divergence structurally, not lexically, and close cutovers as chains (decisions 3, 4, 6).
- G-3 Make temporary custody itemized and never destructive by inference (decisions 5, 9).
- G-4 Land every change through the bounded pipeline itself, post-finalize, with grandfathering (ruleset §0, packet §6–7).

## 4. User stories

Each story names its intended happy-path spine in plain language (spine designation is Phase 2 work).

- **US-1 Target-bound test obligations.** As a conductor, I want a triggered TMR (spine, critical seam, cross-runtime, separately deployed, money effect, authority migration, replacement) to carry a `target_binding`, so that a passing test cannot discharge an obligation via a sibling route, harness caller, or predecessor authority. Spine: author a triggered test in `tests-pseudo.md` → compile into a TMR with binding → validate → promote against an observation that matches.
- **US-2 Progressive binding population.** As a conductor, I want binding fields to populate across the maturity ladder (list fields default empty; full set required only at `concrete`), so that Phase 2 authoring is not blocked by 15 mandatory fields (review F-03 amendment, decision 2 modification).
- **US-3 Triggered authority census.** As a conductor in Phase 4, I want the structural trigger (equivalent-effect paths, separate runtime, authority role change) to demand `authority-paths.json` and every outcome-equivalent path, so that a review of "the failing path plus one sibling" cannot leave live routes unverified. Spine: trigger evaluates true → census authored → validator passes → hash enters the architecture fingerprint. Un-triggered: `triggered:false` with rationale, nothing else.
- **US-4 Cutover chains in execution planning.** As a conductor in Phase 7, I want every path whose role changes to expand into producer, consumer, artifact, activation, running-identity, acceptance, predecessor-probe, and retirement nodes with `not_applicable(reason)` allowed, so that source commits and process launches cannot close independently. Spine: census delta → obligations → plan tasks → strict-int schema-3 emission → Fizzy validate and load classify identically.
- **US-5 Observed target at promotion.** As the Phase 8 skill-runner, I want run evidence to carry a `target_observation` produced by the runner (never authored by the owner), compared against the binding with typed rejects (`PROOF_CALLER_MISMATCH`, `PROOF_PATH_MISMATCH`, `PROOF_AUTHORITY_ROLE_MISMATCH`, `RUNTIME_IDENTITY_INCOMPLETE`), so that a real run of the wrong thing is a reject, not a pass.
- **US-6 Typed fixture provenance.** As a conductor, I want boundary substitutions declared by type at each replaced boundary and the lexical "mock" scan demoted to advisory, so that `makeEnvelope` cannot pass and prose saying "no mocks" cannot halt (`FIXTURE_PROVENANCE_CEILING`).
- **US-7 Custody ledger.** As an operator, I want every pipeline-owned temporary authority (branch, worktree, clone, release dir, activation pointer, unit override) to have one ledger row with a terminal disposition, a budget that blocks new creation (`CUSTODY_BUDGET_BREACH`) but never authorizes cleanup, and an itemized preview with explicit authorization before any removal, so that a 307→72 worktree contraction can never be closed by count.
- **US-8 Critic and adversary prompts.** As a conductor, I want debate guardrails and gauntlet seats asked whether a REAL-DATA test can hit a retired, emergency, or non-product path, whether producer and consumer share a contract, which identity field wins under contradiction, and which predecessor stays callable, so that existing seats attack route identity with no new model launch.
- **US-9 Finalize binding.** As a conductor in Phase 6, I want TCOV (or its ORACLE successor per D-2) to fail a triggered test without binding and concern closure to require a named enforcing test plus proof target, so that a concern cannot close on an implementation task alone.
- **US-10 Golden replay and mutation proof.** As a worker, I want the 18 golden cases to replay against the pure validators with their expected codes, the three controls to stay accepted, and every binding field to have a mutation test that produces its specific code, so that fields are load-bearing rather than decorative. The four §5 codes with no golden case today (`CUSTODY_ENTRY_MISSING`, `PROOF_OUTCOME_MISMATCH`, `TMR_TARGET_BINDING_REQUIRED`, `VALIDATE_LOAD_CLASSIFICATION_DIVERGENCE`) get cases.
- **US-11 Rollout and grandfathering.** As an operator, I want schemas and validators to land under warning mode first, hard rejects only for sessions created after the enforcement version, old TMRs visibly `legacy-unbound`, and skill edits shipped as Phase 7 W-tasks post-finalize, so that in-flight sessions are never retroactively failed and the deployed-symlink hazard (ruleset §0) is respected.
- **US-12 Dogfood.** As the conductor of this session, I want the session to run the v6 bounded pipeline (D0 decomposition, per-leaf A→S, fan-in gauntlet) using only the gates that exist today, deliver the new gates as Phase 7/8 W-tasks, and record every process failure it hits, so that delivery and adoption are demonstrated honestly (the new gates are exercised end-to-end by the next v6 session, US-16).
- **US-13 Recovery after a rejected proof.** As a blocked worker, I want every rejection to name the failed expectation, expected vs observed, whether evidence is missing or mismatched, the next actor, and the permitted recovery, so that I recover without discarding unrelated completed work.
- **US-14 Reconciliation after interruption.** As an operator returning after an interrupted run or custody operation, I want incomplete runs and surviving temporary resources reconciled before dependent work proceeds, so that interruption never implies completion or exemption.
- **US-15 Integration ownership.** As an integration maintainer, I want explicit compatibility and validation ownership per shared contract (keystone → Brainquarters; plan/metadata validation → Fizzy; TMR execution logic → skill/runner), so that producers and consumers agree without duplicating each other's checks.
- **US-16 Downstream adoption.** As a downstream maintainer, I want an adoption guide, a v5→v6 migration path, and an ordinary-work control example, so that I introduce the reform with no new requirements on unaffected work.

## 5. Invariants

- INV-1 REAL-DATA policy and the liveness obligation are preserved unchanged; the new axis is additive.
- INV-2 No mechanism in this work deletes or authorizes deletion of branches, worktrees, releases, or files.
- INV-3 No new universal pipeline Phase; ownership distributes across Phases 2–9.
- INV-4 Fixtures stay legal for math/BVA/isolation; they never discharge a real boundary obligation.
- INV-5 Keystone changes land keystone-first (canonical file → machine schema → sha re-pin → mirrors, same window); no mirror is edited in place.
- INV-6 Pipeline validation is Fizzy's; the skill emits and self-checks with the same codes but never re-implements the load contract.
- INV-7 Expected target fields belong to obligation identity; observed run data never does (a new observation must not invalidate a waiver; a changed target must).
- INV-8 Nothing reopens a closed phase; new scope goes to the next cycle (ruleset global invariant 1).
- INV-9 An operator exception may exceed the custody budget; it never authorizes cleanup.
- INV-10 A waiver records accepted risk with authority and expiry and leaves the obligation visibly undischarged; a process-failure note attributes and discharges nothing; neither converts unverified evidence into proof. Incident-derived fixtures prove validator behavior, never boundary reality.
- INV-11 Custody budget admission uses the projected total after creation; concurrent requests never share the same remaining capacity.
- INV-12 Absent version metadata is grandfathered legacy; malformed or unreadable metadata is a reject, never legacy.

## 6. Integrations and constraints

- Brainquarters TMR keystone (`test-maturity-record-schema.md`, sha-pinned; `KEYSTONE_PROVENANCE` order test).
- fizzy-pipeline-mcp `_validate_plan` (strict-int discriminator now live, card 21533); no TMR code mirror exists in Fizzy today — the field-for-field claim is prose-only on that side.
- Phase 8 skill-runner (`phase8_promotion.py`, `RunExecution`), `dependency_semantics.py` analyzer v2 (evidence receipts, obligations).
- Gauntlet broker evidence boundary (read-only seats, `GT-REQUEST`, `BLOCKED`).
- Python 3.14, pydantic strict models, rfc8785 hashing.
- Ruleset §0: the deployed skill is a symlink; edits are live everywhere instantly. Defects A and B were landed as operator-sanctioned hotfixes ahead of this session; the spec must record that exception rather than pretend it did not happen.

## 7. Success criteria (packet §9, adopted)

Canonical docs, schema, model, parser, compiler, promoter, and closer agree; invalid discriminator types hard-fail in validate and load; every binding field is observed or mechanically checked; every field has a mutation test; all incident replays fail at their intended gate and all controls pass; existing adversarial-spec and Fizzy suites stay green; operator docs carry one realistic example; no new path relabels fixture or legacy evidence as live proof; no custody path is destructive without exact authorization.

## 7b. Release blocker

- RB-1 OQ-5 (version-only fence) conflicts with US-11 (no retroactive failure) for cards already at pipeline_version 6 when enforcement lands. Before enforcement is exposed the operator approves a rollout schedule or amends the policy. No silent downgrade, hidden selector, or automatic exemption.

## 8. Open questions for the operator (an interview would have settled these)

- OQ-1 Hash inclusion: the packet recommends adding expected target fields to the `tmr_record_hash` projection. That changes keystone §2b (ten fields today). Accept the projection change, or keep the binding outside the hash and version it separately?
- OQ-2 Custody scope: are subagent workspaces created and cleaned within one tool turn exempt (review recommendation), or must every worktree be a row?
- OQ-3 D-2 guardrail repointing (TCOV → ORACLE with executable witness): in scope for this session, or a dependency owned elsewhere?
- OQ-4 Fizzy-side TMR mirror: should Fizzy gain a code mirror of the keystone (so P0 validation is real), or does the field-for-field claim stay prose?
- OQ-5 Enforcement version: what pipeline_version or session marker fences warning mode from hard rejects?
- OQ-6 Codex critique seat for debate: spec-codex per the directive; second family for the system quorum is gemini via the API path (`gemini/gemini-3.5-flash`), never a claude critic from a claude conductor.

- OQ-7 Receipt freshness: validity window for a `target_observation` and the events that invalidate it (process restart, artifact rebuild). Value needed before TC-5.4 can be concrete.
- OQ-8 Critic evaluation criteria and score threshold for the seeded wrong-route test (TC-8.0).

OQ-1..6 were decided 2026-09-15 (see `roadmap/manifest.json` operator_decisions); OQ-7/8 arose from roadmap debate R1.
