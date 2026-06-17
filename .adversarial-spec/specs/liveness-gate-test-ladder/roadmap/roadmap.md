# Roadmap: Liveness Gate + Test Ladder (adversarial-spec slice)

> Session: adv-spec-202606151042-liveness-gate-test-ladder | Card 5715 | Altitude: system
> Complexity: complex | Plan: docs/plans/liveness-gate-and-test-ladder.md
> Keystone schema: docs/plans/test-maturity-record-schema.md

## Goals
- Make it **impossible to reach the gauntlet** without a phase-appropriate happy-path spine test for every user story.
- Force every MOCK to **name the live/induced technique** or be promoted to REAL-DATA.
- Give the five guardrails **structured, persisted, test/US-keyed** output (enabling provenance + meta-analysis).
- Provide a durable **decision provenance journal** (test-maturity + altitude-triage) for meta-analysis.
- Define a **shared TMR schema contract** with fizzy, schema-first (field-for-field).
- Classify every deliverable by **verification tier** and apply the this-project liveness interpretation.
- **Version-fence** the new gates so in-flight sessions are unaffected.

## Non-Goals
- The fizzy-side persistence/enforcement (M-4b-style sweep gate, run_evidence storage) — separate coordinated fizzy spec.
- The concept-accessor façade / bindings / fail-closed lint — target-repo (prediction-prime) + its CI.
- Dogfooding these changes on this very session — run on the current skill version; version the changes.
- The sessions stats dashboard — deferred, forward-only, separate trigger (after this card hits debate R2).
- Backfilling provenance for past sessions.
- prediction-prime live-fill work (Track A) and fault-injection infra (B6).

## Getting Started (bootstrap) — added R2 (roadmap debate)
**User Stories:**
- **US-15:** As an operator, I want a documented first-run path so I can bootstrap the liveness gate + test ladder and verify a gate locally in minutes.

**Success Criteria (nl):**
- [ ] First-run path is documented: start a **post-fence** `/adversarial-spec` session → author one `[spine]` test per user story in `tests-pseudo.md` → run the authoring lint → enter debate → attempt gauntlet entry and observe the spine gate pass-or-`exit 2`.
- [ ] A new operator can run the F′ gate against a fixture (full-coverage → pass; missing-spine → exit 2) without reading the implementation.
- [ ] Deploy reality is stated correctly: `~/.claude/skills/adversarial-spec` is a **symlink** to source — edits are live, **no copy step** (correcting the stale CLAUDE.md "manual copy" line; do NOT prescribe `cp -r`).

---

### Milestone 1 — Shared TMR schema contract (keystone, schema-first)
**User Stories:**
- **US-1:** As a spec author *and* fizzy, I want one agreed TMR field set + enums (`data_strategy`, `live_or_induced`, `maturity`, spine fields, `run_evidence.env`) so the skill's emission and fizzy's validation never drift.

**Success Criteria (nl):**
- [ ] The schema doc enumerates every field + enum member and marks each skill-owned / fizzy-owned / new.
- [ ] Both repos reference the same source of truth; a field or enum-member mismatch is detectable, not silent.
- [ ] The handshake (which repo lands the constants first) is decided.

---

### Milestone 2 — Happy-path-spine authoring + strict MOCK (A, B)
**User Stories:**
- **US-2:** As a spec author, I want to declare exactly one happy-path spine (TC-0) per user story with named steps, and anchor every failure test to a spine step, so no journey lacks a primary-success test.
- **US-3:** As a spec author, I want every MOCK test to name the live/induced technique (or be promoted to REAL-DATA) so convenience can't masquerade as impossibility.
- **US-4:** As a spec author, I want tests tracked through `nl → acceptance → concrete` at phase-appropriate rigor so I'm never forced to over-build a test early.

**Success Criteria (nl):**
- [ ] Authoring docs require one happy-path spine per US; failure tests carry `spine_step_ref`; an unanchored failure test is rejected at authoring.
- [ ] A MOCK without a named technique (and without genuine impossibility) is flagged; valid techniques enumerated; promotion path clear.
- [ ] Each test carries a `maturity`; promotion rules defined; debate-time accepts `nl`/`acceptance`.

---

### Milestone 3 — Guardrail rearchitecture: structured output + parallel subagents (C, D, K)
**User Stories:**
- **US-5:** As the orchestrator, I want each guardrail to run as a parallel subagent emitting structured, test/US-keyed findings so findings are persisted and feed the provenance journal.
- **US-6:** As a spec author, I want TRACE to flag a user story with no happy-path spine as ORPHANED so missing spines surface at round 1.
- **US-7:** As a spec author, I want TCOV to promote `nl→acceptance`, ingest ALL owner test files (not just the ledger), apply strict `data_strategy_mismatch`, and flag `missing_liveness_test` so absent/weak critical-seam tests are caught.

**Success Criteria (nl):**
- [ ] Five guardrails run as separate subagents (never one combined prompt); each returns structured findings keyed to test/US; results aggregated + persisted per round.
- [ ] TRACE reports US-without-spine as ORPHANED and judges whether the labeled spine is the real primary path; keeps the no-test-suggestions rule elsewhere.
- [ ] TCOV emits PROMOTE/BLOCK, reads standalone test files, flags MOCK-without-technique, and marks a critical-seam happy-path with no REAL/induced test as blocking `missing_liveness_test`.

---

### Milestone 4 — Deterministic spine-coverage gate (F′)
**User Stories:**
- **US-8:** As the operator, I want a deterministic gate at the gauntlet-entry chokepoint that blocks reaching the gauntlet unless every user story has a phase-appropriate-maturity happy-path spine test, with a logged override, so coverage is forced not advisory.

**Success Criteria (nl):**
- [ ] Gate runs in `enforce_pipeline_card_gate`; it **blocks gauntlet entry only** (uncovered US → `exit 2`), and is **advisory (warn, non-blocking) during `critique`** so early debate isn't blocked while tests are still maturing. (R1, roadmap debate)
- [ ] Maturity-aware: `nl`/`acceptance` spine passes at debate→gauntlet; live-run/`concrete` deferred to G.
- [ ] Override requires a logged ≥50-char reason (mirrors the staleness-gate pattern).

---

### Milestone 5 — Decision provenance journal (J)
**User Stories:**
- **US-9:** As the operator, I want an append-only journal of test-maturity transitions (with drivers) so I can replay each user story's test journey.
- **US-10:** As the operator, I want altitude-triage transitions journaled (`created` → reclassifications → close `altitude_fit`) so I can measure triage accuracy and the altitude distribution.

**Success Criteria (nl):**
- [ ] Every TMR-field change appends a record (`from`/`to`/`driver`/`phase`), keyed `subject_type=test`; queryable as a per-US journey.
- [ ] Node-altitude changes appended with driver; close `altitude_fit` ∈ {right, too_high, too_low}; supports "of subsystem-tagged, % right by the end" and "distribution of altitudes identified".

---

### Milestone 6 — Phase-8 pseudo→real promotion + version-fence (G)
**User Stories:**
- **US-11:** As the operator, I want critical-seam/spine tests promoted to real and RUN green (at the right verification tier) before implementation closes, so a declared-but-never-run REAL-DATA test counts as failing.
- **US-12:** As the operator, I want the new gates fenced to new specs so in-flight sessions aren't retroactively failed.

**Success Criteria (nl):**
- [ ] A promotion pass writes+runs each critical-seam/spine test; code seam → pytest, prompt/doc → system-validation, judgment → golden eval; an un-run REAL-DATA test = failing; spine/critical-seam can't be `spike`/exempt.
- [ ] A version marker (`liveness_contract_version`, e.g. `tmr.v1`) gates the new requirements; sessions started before it keep their original rules. (R3, roadmap debate)

---

### Milestone 7 — Glossary / ADR / document-types (H)
**User Stories:**
- **US-13:** As a future author, I want the new vocabulary (happy-path spine, TMR, maturity ladder, liveness) and the cross-repo scope decision recorded so terms don't collide (esp. with "Architecture Spine") and decisions are durable.

**Success Criteria (nl):**
- [ ] CONTEXT.md entries added; `document-types.md` row format updated; an ADR records the test-ladder/TMR/liveness decision + the two-spec scope split.

---

### Cross-cutting — Verification tiers
**User Stories:**
- **US-14:** As the operator, I want every deliverable classified by verification tier (code→REAL-DATA pytest / prompt→system-validation / judgment→golden eval) so this skill's own work is verified appropriately given it's part code, part prompts.

**Success Criteria (nl):**
- [ ] Each task declares its verification tier; the tier determines the `verification_mode`; the system-validation close exercises the prompt/doc tier.

---

## Dependencies
- **M1 (TMR schema) is the keystone** — M2 (authoring fields), M4 (F′ parse), M5 (journal keys), and the fizzy spec all depend on it. Land first.
- M3 (structured guardrails, K) is the prerequisite for M5's test-journey records (J).
- M4 (F′) depends on M2 (the `spine:`/`maturity` fields it keys on).
- M6 (G/version-fence) depends on M1 + M2.
- M7 (glossary/ADR) runs alongside throughout.

## Next (roadmap phase)
1. Generate `tests-pseudo.md` — happy-path spine (TC-0) + error-case per US, with Data Strategy + maturity annotations (current skill rules; this is dogfood-adjacent).
2. Architecture-impact assessment [GATE] + goal-alignment [GATE].
3. Roadmap debate round (complex tier) → user confirms roadmap [GATE] → persist manifest.json → Phase 2 debate.
