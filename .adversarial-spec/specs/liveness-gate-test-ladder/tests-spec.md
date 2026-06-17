# tests-spec.md — Liveness Gate + Architecture-Linked Test Ladder (formalized acceptance tests)

> Promoted from `tests-pseudo.md` at finalize (spec v12, R12 convergence + gauntlet/reconciliation complete).
> `tests-pseudo.md` stays as the prose audit trail; this file is the formalized acceptance-test contract.
> System of record for TMR records is `tmr-registry.json` (DR-11/DD-1); these tests parse the registry,
> never embedded markdown.

## Reference-validation status (finalize)

| Reference | Status |
|---|---|
| `debate.py: enforce_pipeline_card_gate` | **verified** — `skills/adversarial-spec/scripts/debate.py:1351`; `round_actions = {"critique","gauntlet"}` at `:1370` (F′ must branch on `args.action`). |
| `adversaries.py` guardrail personas | **verified** — `REQUIREMENTS_TRACER:1174`, `TEST_COVERAGE_AUDITOR:1284`, `GUARDRAILS` dict `:1348`. |
| fizzy `VALID_VERIFICATION_MODES` / `EXEMPT_MODES` / `VALID_ALTITUDES` | **verified existing** (code-confirmed 2026-06-15 in spec §1/§9); referenced, not redefined. |
| Keystone `test-maturity-record-schema.md` + `VALID_TMR_STATUS` / `VALID_DATA_STRATEGIES` / `VALID_LIVENESS_TECHNIQUES` | **forward (P0 to-create)** — fizzy P0 adds; handshake is part of the activation rule (§3.2/§12.7). Tests against these run once the keystone + fizzy P0 land (activation rule, §1). |

## Verification tiers (US-14)
- **code** → REAL-DATA `pytest` against real artifact fixtures (roadmap-manifest + `tmr-registry.json` fixtures).
- **prompt/doc** → STATIC doc-lint + `system-validation` scoped skill run + fault-induced fixtures.
- **LLM-judgment** → golden-case eval against a planted-defect corpus (`golden_cases/manifest.json`, US-5).

Every oracle below is classified **semantic** (would fail under the wrong behavior) or **smoke** (existence
/200/non-null/range only). A test passing only a smoke oracle does NOT satisfy its user story.

## Coverage completeness matrix

Every user story owns exactly one happy-path spine (TC-x.0) + ≥0 branch tests; Phase-4 invariant tests
cross-cut. No orphan tests (every TC maps to a US or a named invariant); no uncovered US.

| US | Spine | Branches | Invariant tests | Tier(s) |
|----|-------|----------|-----------------|---------|
| US-1 Shared TMR schema | TC-1.0 | TC-1.1, TC-1.2, TC-1.3, TC-1.4 | TC-INV-004, TC-INV-008 | code |
| US-2 Happy-path-spine authoring | TC-2.0 | TC-2.1, TC-2.2 | — | prompt/doc |
| US-3 Strict MOCK falsification | TC-3.0 | TC-3.1, TC-3.2 | — | prompt/doc, code, judgment |
| US-4 Maturity ladder | TC-4.0 | TC-4.1 | — | code |
| US-5 Parallel structured guardrails | TC-5.0 | TC-5.1, TC-5.2, TC-5.3 | TC-INV-010 | code |
| US-6 TRACE spine-inversion | TC-6.0 | TC-6.1 | — | judgment |
| US-7 TCOV liveness guardrail | TC-7.0 | TC-7.1, TC-7.2 | — | code, judgment |
| US-8 Deterministic F′ gate | TC-8.0 | TC-8.1, TC-8.2, TC-8.3, TC-8.4 | TC-INV-001 | code |
| US-9 Test provenance journal | TC-9.0 | TC-9.1 | TC-INV-013 | code |
| US-10 Altitude-triage provenance | TC-10.0 | TC-10.1 | TC-INV-015 | code |
| US-11 Phase-8 pseudo→real promotion | TC-11.0 | TC-11.1 | TC-INV-017 | code |
| US-12 Version fence | TC-12.0 | TC-12.1 | TC-INV-016 | code |
| US-13 Glossary / ADR / doc-types | TC-13.0 | — | — | prompt/doc |
| US-14 Verification tiers | TC-14.0 | TC-14.1 | TC-INV-018 | prompt/doc, code |
| US-15 Getting Started | TC-15.0 | TC-15.1 | — | prompt/doc |
| (cross-cut) INV-009 no critical_seam re-derivation | — | — | TC-INV-009 | code |

**TRACE result:** 0 orphaned spines, 0 uncovered US (all 15 own a scalar `spine:true` designation).

## Canonical GateResult outcome → exit map (US-2, §6) — error cases

| outcome | exit | meaning | override_eligible |
|---|---|---|---|
| `pass` | 0 | coverage satisfied (or advisory `critique` with `warn` findings) | n/a |
| `block` | 2 | uncovered US **or** duplicate happy-path spine | **yes** (logged reason, non-empty/non-ws, no min length) |
| `schema_error` | 3 | `TmrParser` reject (unknown/missing key, bad enum, ambiguous scalar, dup `tmr_uid`) | **no** |
| `orch_error` | 4 | checker invocation / runtime / subagent-death | **no** |
| `setup_error` | 5 | missing manifest/registry | **no** |

`outcome` is the only normative outcome field on the gate envelope (no separate `result`; `run_evidence.result`
is an unrelated receipt field). Fizzy blocks gauntlet entry on any non-`pass` exit (`2|3|4|5`).

---

# Acceptance tests

> Format per test: tier · data_strategy · fixtures · positive oracle (semantic) · negative oracle (semantic).
> Bodies carried from `tests-pseudo.md` (acceptance maturity); fixtures and field names are concrete.

## US-1 — Shared TMR schema contract (keystone)

### TC-1.0 [spine] — round-trip a TMR skill-emit → fizzy-validate
- **tier** code · **data_strategy** REAL-DATA · **fixture** a TMR with every field a valid enum member + a `code`-variant `run_evidence` (`env` exists only on the `code` variant, DR-1).
- **steps** S1 author TMR → S2 skill emits fields → S3 fizzy validates enums → S4 accepted.
- **positive (semantic):** accepted AND semantic round-trip holds — required keys (`tmr_uid`,`user_story`,`test_id`,`maturity`,`data_strategy`,`spine`,`run_evidence`) preserved; immutable `tmr_uid` is identity and unchanged; coordinates `user_story`/`test_id` PRESERVED (not identity); `session_id` asserted only for exported/container metadata (not a local `tmr-registry.json` field); no field silently dropped.
- **negative (semantic):** any silently-dropped key or coerced enum fails the test (enum/field-presence alone is insufficient — identity must key on `tmr_uid`).

### TC-1.1 — enum-member mismatch detected, not silent (branch @ S3)
- code · REAL-DATA · TMR with `data_strategy: "FAKE-DATA"` (∉ `VALID_DATA_STRATEGIES`).
- **semantic:** fizzy rejects with a named error citing the field; a pass on silent drop/accept is smoke-only.

### TC-1.2 — missing required field rejected with a named error (branch @ S3)
- code · REAL-DATA · TMR omitting `maturity` (or `data_strategy`).
- **semantic:** named missing-field error, not a silent default.

### TC-1.3 — `tmr-registry.json` record converts field-for-field (branch @ S2, DR-11/DD-1)
- code · REAL-DATA · a real `tmr-registry.json` record with every required keystone key (incl. `tmr_uid`,`title`,`source_spec`,`critical_seam`,`criticality_source`,`status`). NOT a markdown `TMR:` block.
- **positive (semantic):** every keystone field round-trips (no key dropped, no enum coerced).
- **negative (semantic):** a record with an unknown key / missing required key / bad enum → named `schema_error`.

### TC-1.4 — `live_or_induced` strict union, single "no technique" encoding (branch @ S3, R6-C7)
- code · REAL-DATA · records exercising each form.
- **valid:** `null`; `{kind:"tc-netem:partition"}`; `{kind:"other", detail:"cgroups"}`.
- **invalid (semantic):** `{kind:null}`, `{"kind":"null"}` (kind never null — JSON `null` is the single "no technique" encoding); `{kind:"other"}` (detail required). A parser accepting `{kind:null}` ≡ JSON `null` is smoke-only (reopens the R6-C7 dual-encoding).

## US-2 — Happy-path-spine authoring

### TC-2.0 [spine] — one spine/US, failures anchored
- prompt/doc (doc-lint) · STATIC · authored tests-pseudo fixture (US-X + one `[spine]` + two failure tests).
- **steps** S1 author US → S2 author spine TC-0 → S3 author failure tests → S4 each cites `spine_step_ref`.
- **semantic:** exactly one spine per US found AND every failure test carries a valid `spine_step_ref`.

### TC-2.1 — unanchored failure test rejected (branch @ S4)
- prompt/doc · STATIC · fault-induced fixture: failure test with no `spine_step_ref`.
- **semantic:** flagged "branch off an unplanted trunk", rejected at authoring.

### TC-2.2 — authoring docs actually produce a spine in a live run (system-validation)
- prompt/doc (`system-validation`) · REAL-DATA · scoped skill run on a 2-US fixture feature.
- **why this tier:** a phase-doc rule's behavior is only provable by an LLM following it.
- **semantic:** the produced tests-pseudo has exactly one happy-path spine per user story.

## US-3 — Strict MOCK falsification

### TC-3.0 [spine] — justified MOCK (no technique + genuine impossibility) accepted
- prompt/doc · STATIC · a test annotated `MOCK`, `live_or_induced: null`, impossibility matrix denying every technique.
- **steps** S1 author MOCK → S2 `live_or_induced: null` → S3 deny every technique → S4 accepted.
- **semantic:** accepted as the ONLY allowed MOCK case AND the check asserts BOTH non-empty `why_impossible_to_reproduce_live` AND non-empty `technical_constraint` (§3.1 conditionally-required for `MOCK ∧ live_or_induced=null`). Asserting only one is smoke-only.

### TC-3.1 — MOCK naming a technique (or dev-forceable condition) is promoted (branch @ S2)
- LLM-judgment (golden case) · REAL-DATA · planted: MOCK with `live_or_induced: tc-netem:partition`; sibling planted on ">100 positions for pagination" (dev-forceable, no technique named).
- **semantic:** REJECTED as justified MOCK; required_action = "promote to REAL-DATA" (naming a technique proves inducibility).

### TC-3.2 — SYNTHETIC critical-seam with empty `why_impossible_to_reproduce_live` rejected (DR-8)
- code · REAL-DATA · TMR `critical_seam:true`, `data_strategy ∈ {SYNTHETIC,STATIC,MOCK-EXTERNAL,FRONTEND}`, empty/absent `why_impossible_to_reproduce_live`.
- **semantic:** REJECTED with named error, required_action "promote to REAL-DATA". A check firing only on literal `MOCK` is smoke-only (reopens the relabel-to-bypass loophole DR-8 closed).

## US-4 — Maturity ladder

### TC-4.0 [spine] — test carries maturity, promotes nl→acceptance when accessors named
- code · REAL-DATA · TMR at `nl` whose elements all map to named accessors.
- **steps** S1 nl authored → S2 accessors named → S3 promote to acceptance.
- **semantic:** emits `PROMOTE nl→acceptance`. (Guard: empty `accessors` does NOT auto-promote — `all([])` is vacuously true; ≥1 named accessor required, CB-5.)

### TC-4.1 — concept never named stays nl + flagged (branch @ S2)
- code · REAL-DATA · TMR whose element maps to no named accessor across N rounds.
- **semantic:** stays `nl`, flagged `BLOCK` (concept undesigned).

## US-5 — Parallel-subagent structured guardrails

### TC-5.0 [spine] — five guardrails as separate subagents, structured test/US-keyed findings
- code/orchestration · REAL-DATA · real spec+tests fixture; assert aggregation shape.
- **steps** S1 revision → S2 dispatch 5 subagents → S3 each returns structured findings → S4 aggregate+persist.
- **semantic:** five separate structured result sets, each finding keyed to a test/US id, aggregated+persisted per round (never one combined prompt).

### TC-5.1 — join keys scoped to TMR-changing findings (branch @ S3, R2)
- code · REAL-DATA · a TMR-changing finding missing `target.{user_story,test_id}` + a CANON finding carrying only `target.spec_section`.
- **semantic:** TMR-changing finding REJECTED (no join key → not journalable); spec/contract finding ACCEPTED as actionable but NOT journaled unless its disposition changes a TMR/node field.

### TC-5.2 — subagent failure is fail-closed via synthetic ORCH (branch)
- code (pytest of orchestrator) · REAL-DATA · one of five subagents times out/dies/returns invalid JSON.
- **semantic:** synthetic `ORCH` finding emitted — blocking on `gauntlet`, warning on `critique`; never proceeds on partial findings as green.

### TC-5.3 — conflicting findings enter a conflict state (branch)
- code · REAL-DATA · two findings with contradictory `required_action` on the same `target.test_id`+field.
- **semantic:** pair enters `conflict` state requiring disposition BEFORE any journaled field transition (no silent last-writer-wins).

## US-6 — TRACE spine-inversion

### TC-6.0 [spine] — US with prose but no spine reported ORPHANED
- LLM-judgment (golden case) · REAL-DATA · planted: US covered in prose, no spine test.
- **semantic:** TRACE reports the US as ORPHANED (traceability break), not a test suggestion.

### TC-6.1 — non-spine missing test NOT flagged (branch, false-positive guard)
- LLM-judgment (golden case) · REAL-DATA · US with a spine but a missing minor edge test.
- **semantic:** TRACE does NOT flag it (no-test-suggestions rule still holds for non-spine).

## US-7 — TCOV liveness guardrail (+ promoter)

> Re-centered by DR-5 morph (2026-06-16): primary deliverable is `missing_liveness_test`; promoter (US-4/§4.4) and `data_strategy_mismatch` (US-3/§4.3) are secondary TCOV findings.

### TC-7.0 [spine] — critical seam WITH real/induced test passes TCOV (no missing_liveness_test)
- code · REAL-DATA · fixture TMR for a critical-seam happy-path (`critical_seam:true`) carrying a REAL-DATA or induced test with a recorded `live_or_induced` technique.
- **steps** S1 load critical-seam happy-path TMR → S2 REAL-DATA or recorded technique → S3 TCOV liveness check → S4 NO `missing_liveness_test` (clean/pass).
- **semantic:** emits **no** `missing_liveness_test` (positive counterpart to TC-7.1's `LIV-POS`/`LIV-NEG`).

### TC-7.1 — critical seam with no real/induced test → blocking missing_liveness_test (branch)
- LLM-judgment (golden case) · REAL-DATA · planted corpus: `LIV-POS` (critical-seam happy-path, mock-only), `LIV-NEG` (non-critical happy-path, mock-only).
- **semantic:** on `LIV-POS` emits blocking `missing_liveness_test` with `target.{user_story,test_id}`; on `LIV-NEG` does NOT (false-positive guard).

### TC-7.2 — criticality_unknown on system altitude treated as critical (fail-closed) (branch @ S3)
- code · REAL-DATA · TMR `critical_seam:null`, `criticality_source:unknown`, `altitude:system`, mock-only.
- **semantic:** treated as critical (fail-closed); emits blocking `missing_liveness_test`; never silently non-critical.

## US-8 — Deterministic F′ spine-coverage gate

> Re-centered by SEC-1 reframe (v10): mechanical non-bypassable gate is Fizzy-side (`pipeline_advance` invoking the §6 R4-2 checker contract); skill-side pre-check is advisory. 0 orphaned spines.

### TC-8.0 [spine] — Fizzy gauntlet-entry transition with full coverage admitted by F′ checker
- code · REAL-DATA · real fixture roadmap manifest + `tmr-registry.json` (full coverage), invoked through the §6 normative F′ checker contract. `tmr_uid` exemplar: `01J0EXEMPLARULID00000000XY` (compiler-allocated ULID, length-26).
- **steps** S1 load roadmap US set + registry → S2 Fizzy invokes `uv run gauntlet-check --action gauntlet --output json` at the `pipeline_advance` boundary → S3 checker parses each TMR via `TmrParser`, confirms every US has exactly one `active`, `spine:true` record at acceptable maturity → S4 exit 0 (`pass`), Fizzy admits.
- **positive (semantic):** checker emits `{outcome:"pass"}` (exit 0), Fizzy admits; the advisory skill-side pre-check also returns pass (sanity).
- **negative (semantic):** with the Fizzy checker invocation stubbed/not wired, the advisory pre-check still passes but Fizzy must REFUSE `pipeline_advance` (no F′ evidence attached). Admitting on the advisory pass alone is smoke-only (reopens the SEC-1 honor-system hole). The full exemplar `TMR:` block (generated-view mirror; F′ parses the registry record, not the markdown) lives in `tests-pseudo.md` TC-8.0.

### TC-8.1 — uncovered US → exit 2 (branch @ S3)
- code · REAL-DATA · fixture where US-3 has no spine test.
- **semantic:** exit 2 naming US-3; bypass only via `--accept-missing-spine` + logged reason to `decisions.log`.

### TC-8.2 — maturity-awareness: an nl spine passes at debate→gauntlet (branch @ S3)
- code · REAL-DATA · spine tests only at `nl`.
- **semantic:** passes (does NOT demand `concrete`/live — that's G's Phase-8 gate).

### TC-8.3 — critique action advisory, not blocking (branch)
- code · REAL-DATA · missing spine, gate invoked for `critique`.
- **semantic:** WARNS, does NOT exit 2 for `critique`; same fixture exits 2 for `gauntlet`.

### TC-8.4 — duplicate happy-path spine for one US → exit 2 at gauntlet (branch @ S3)
- code · REAL-DATA · `tmr-registry.json` with two `status:active, spine:true` records for one scalar `user_story: US-2`.
- **semantic:** exit 2 naming the duplicated US (F′ enforces exactly one, ≥1 ∧ ≤1); same fixture WARNS for `critique`.

## US-9 — Test provenance journal

### TC-9.0 [spine] — TMR-field change appends a driver-tagged record; per-US journey replays
- code · REAL-DATA · drive a real maturity + data_strategy change, read back.
- **steps** S1 create test → S2 change a field → S3 append record → S4 read journey for the US.
- **semantic:** journal appends `{subject_type:test, field:data_strategy, from:MOCK, to:REAL-DATA, driver:{type:guardrail, ref:<finding_id>}}`; per-US query replays in order.

### TC-9.1 — append-only: a prior record is never rewritten (branch @ S3)
- code · REAL-DATA · two changes to the same test.
- **semantic:** both records exist (append-only); the first is unmodified.

## US-10 — Altitude-triage provenance

### TC-10.0 [spine] — node altitude journaled created→close with altitude_fit; queries answer
- code · REAL-DATA · node created subsystem, closed with fit attestation.
- **steps** S1 depth_triage created → S2 (optional) reclassify → S3 close `altitude_fit` → S4 query.
- **semantic:** `altitude_fit: right` counts correct; distribution histogram counts it under subsystem.

### TC-10.1 — silently-wrong altitude (stable but too_low) NOT counted correct (branch @ S3)
- code · REAL-DATA · node stable at subsystem, close fit = too_low.
- **semantic:** NOT counted correct (stability alone over-counts; the fit attestation corrects it).

## US-11 — Phase-8 pseudo→real promotion

### TC-11.0 [spine] — critical-seam test promoted (producer-split), RUN, required green
- code (pytest of promotion-pass logic) · REAL-DATA · fixture critical-seam test + owner-repo fixture supplying executable test + bound accessors.
- **steps** S1 select critical-seam/spine pseudo test → S2 Phase-8 emits typed `promotion_request` (skill does NOT write target-repo code) → S3 owner-repo fixture supplies executable test + bound accessors → S4 skill-runner executes declared command + captures typed `run_evidence`, required green.
- **semantic:** emits `promotion_request{tmr_uid, repo, accessors[], command, expected_evidence, negative_oracle}`; skill-runner captures `run_evidence{tier:"code", result:"pass", ...}` (never trusts an owner-written `result:pass`). Does NOT claim the skill writes target-repo code (DD-4/R5-C2 producer split).

### TC-11.1 — declared-but-never-run REAL-DATA test counts as failing (branch @ S3)
- code · REAL-DATA · REAL-DATA test with `run_evidence: null` at close.
- **semantic:** treated as failing (not passing); spine/critical-seam may not be `spike`/exempt.

## US-12 — Version fence

### TC-12.0 [spine] — legacy session (authoritative created_at < fence_cutover_ts) keeps original rules
- code · REAL-DATA · session whose Fizzy card `created_at < fence_cutover_ts`.
- **semantic:** `ContractVersionResolver` classifies legacy; new requirements do not apply (no retroactive failure). Fence decided by immutable `created_at` vs `fence_cutover_ts`, NOT the local `liveness_contract_version` marker.

### TC-12.1 — post-fence session (created_at ≥ cutover) held to new gates even with missing/lower marker (branch)
- code · REAL-DATA · Fizzy card `created_at ≥ fence_cutover_ts`, local marker missing/lowered.
- **semantic:** classified post-fence; new F′ requirement applies (exit 2). A marker-only test (flips outcome by editing the marker alone, ignoring `created_at`) is invalid.

## US-13 — Glossary / ADR / document-types

### TC-13.0 [spine] — vocabulary present + no "spine" collision
- prompt/doc (doc-lint) · STATIC · grep the committed docs.
- **semantic:** "happy-path spine", TMR, maturity ladder, liveness defined; "happy-path spine" always qualified in PROSE (never bare "spine"); machine tokens `spine`/`spine_steps`/`spine_step_ref`/`[spine]` EXEMPT (canonical keystone tokens); ADR records the decision + two-spec scope split.

## US-14 — Verification tiers

### TC-14.0 [spine] — every task declares a verification tier driving its mode
- prompt/doc (doc-lint of execution plan) · STATIC · parse task records.
- **semantic:** every task declares a tier (code/prompt-doc/llm-judgment) + a consistent `verification_mode` (code→`automated-*`/`test-producer`; prompt-doc→`system-validation`/`manual-ux`; judgment→`system-validation` + golden-case corpus oracle). NO `golden-eval` member exists in `VALID_VERIFICATION_MODES`.

### TC-14.1 — code-seam task marked spike/exempt is flagged (branch)
- code (pytest of lint) · REAL-DATA · code-seam task with `verification_mode: static-check`.
- **semantic:** flagged (critical code seams must be REAL-DATA pytest, not exempt).

## US-15 — Getting Started / bootstrap

### TC-15.0 [spine] — documented first-run path bootstraps and verifies a gate
- prompt/doc (`system-validation`) · REAL-DATA · follow the documented bootstrap on a fixture.
- **steps** S1 start post-fence session → S2 author one [spine]/US → S3 run authoring lint → S4 attempt gauntlet → observe pass/exit-2.
- **semantic:** operator reaches a passing spine gate (full coverage) AND a blocking `exit 2` (missing-spine fixture) without reading the implementation.

### TC-15.1 — docs do NOT prescribe a copy-deploy step (branch, anti-regression)
- prompt/doc (doc-lint) · STATIC · grep the Getting Started doc.
- **semantic:** docs state the deployed skill is a symlink (edits live, no copy) and contain no AFFIRMATIVE/prescriptive `cp -r … ~/.claude/skills` instruction; a negative warning ("do NOT run cp -r") is allowed. The lint forbids prescriptive copy steps, not every occurrence of the string.

---

# Phase-4 invariant tests (cross-cutting)

> Derived from `architecture-invariants.json` (lightweight Phase 4). Each carries a positive AND a
> negative/counterfactual assertion; a test that would still pass under the wrong behavior is smoke-only.

### TC-INV-001 — no gauntlet-entry path bypasses Fizzy's invocation of the F′ checker (INV-001/002/003)
- code · REAL-DATA · enumerate every code path transitioning a post-fence session into the gauntlet.
- **positive:** a session with one `status:active, spine:true` TMR per US is admitted by `pipeline_advance` (Fizzy invokes checker → `pass`).
- **negative:** a session missing a spine is BLOCKED by Fizzy at `pipeline_advance` (mechanical) regardless of whether the advisory skill-side pre-check ran. Asserting the skill-side pre-check is the blocker is WRONG (it's a prompt-enforced honor system, §6 SEC-1). Checker timeout / invalid JSON / unrecognized `contract_version` / stale hashes → Fizzy refuses the transition (R4-2 fail-closed).

### TC-INV-004 — schema divergence is always a named rejection, never a silent drop (INV-004)
- code · REAL-DATA · round-trip TMRs through the parser/validator.
- **positive:** canonical TMR round-trips, no key dropped, immutable `tmr_uid` identity unchanged, coordinates `user_story`/`test_id` PRESERVED (`session_id` only for exported/container metadata).
- **negative:** the divergent TMR rejected with a named error citing the offending field; a pass on silent drop is smoke-only.

### TC-INV-008 — canonical TMR schema exists in exactly one location (INV-008)
- code (static/grep) · STATIC · scan both repos for the TMR field table.
- **positive:** canonical `test-maturity-record-schema.md` exists as the single source.
- **negative:** a planted second copy (lacking a `generated-from:<sha256>` allowlist header) makes the check FAIL (lint-not-delete, FM-4); a check that only verifies the canonical file exists is smoke-only.

### TC-INV-009 — no consumer re-derives critical_seam (INV-009)
- code (AST/grep) · STATIC · over consumers of criticality.
- **positive:** every consumer reads the normalized TMR `critical_seam` field.
- **negative:** a planted local derivation from `architecture_link` outside the `CriticalityClassifier` is caught; a check ignoring `architecture_link` usage is smoke-only.

### TC-INV-010 — partial guardrail results never read as green (INV-010)
- code (pytest of orchestrator) · REAL-DATA · a round where one of five subagents fails.
- **positive:** 5/5 returns → aggregation proceeds.
- **negative:** 4/5 → synthetic `ORCH` finding, round does NOT complete green; a pass on 4/5 is the false-confidence hole this spec closes.

### TC-INV-013 — journal is strictly append-only (INV-013)
- code · REAL-DATA · two successive field changes on one subject.
- **positive:** both records exist in order; per-subject replay returns them in sequence.
- **negative:** the byte range of record k is unchanged after k+1, no in-place edit API exists; a test asserting only "a new record exists" is smoke-only.

### TC-INV-015 — silently-wrong-but-stable altitude not counted correct (INV-015)
- code · REAL-DATA · node never reclassified, closed with a fit attestation.
- **positive:** `altitude_fit: right` → counted correct.
- **negative:** `altitude_fit: too_low` → NOT counted correct despite stability; a precision metric keyed on stability alone is smoke-only.

### TC-INV-016 — version fence non-retroactive, anchored on authoritative created_at (INV-016)
- code · REAL-DATA · the SAME missing-spine input under two authoritative timestamps.
- **positive:** post-fence (`created_at ≥ fence_cutover_ts`) → exit 2.
- **negative:** legacy (same input, `created_at < fence_cutover_ts`) → NOT failed; the outcome flips on the immutable `created_at` vs `fence_cutover_ts`, NOT the editable marker. A marker-only test is invalid.

### TC-INV-017 — declared-but-never-run REAL-DATA critical-seam counts as failing (INV-017)
- code (pytest of close evaluation) · REAL-DATA · a critical-seam test at close.
- **positive:** promoted + run-green (`run_evidence{tier:"code", env, result:"pass", ...}`) → close passes.
- **negative:** `run_evidence: null` → close FAILS (counts as failing), and the test may not be `spike`/exempt; a close that passes on null run_evidence is the exact liveness hole this spec exists to kill.

### TC-INV-018 — verification_mode always canonical; no golden-eval member (INV-018)
- code (pytest + static lint) · REAL-DATA · parse execution-plan task records.
- **positive:** every task's `verification_mode ∈ VALID_VERIFICATION_MODES`.
- **negative:** a task with `verification_mode: "golden-eval"` rejected (no such member); a code-seam task with an exempt mode (`artifact-sync`/`static-check`/`manual-ux`) flagged; a lint accepting golden-eval is smoke-only.
