# tests-pseudo.md — Liveness Gate + Test Ladder

> Session: adv-spec-202606151042-liveness-gate-test-ladder | maturity stage: nl
> Prose authoring surface + generated VIEW — **NOT canonical** (`tmr-registry.json` is the SoR; DR-11). roadmap/manifest.json links here.
>
> **Verification tiers** (US-14): code → REAL-DATA pytest on real artifact fixtures;
> prompt/doc → STATIC doc-lint + `system-validation` live run + fault-induced fixtures;
> LLM-judgment → golden-case eval (planted-defect fixture spec). Each test names its tier.
> `[spine]` marks the happy-path spine (TC-0) for its user story; failure tests cite the spine step.

---

## US-1 — Shared TMR schema contract (M1, keystone)

### TC-1.0: round-trip a TMR through skill-emit → fizzy-validate  [spine]
**Data Strategy: REAL-DATA** (tier: code) — a real TMR record built from a real test case.
**Spine steps:** S1 author TMR → S2 skill emits fields → S3 fizzy validates enums → S4 accepted.
- given a TMR with every field set to a valid enum member (data_strategy, live_or_induced, maturity, spine; and a `code`-variant `run_evidence` whose `env` is a valid member — `env` exists **only** on the `code` variant, DR-1)
- when the skill emits it and fizzy's validator runs
- then it is accepted AND a **semantic round-trip** holds: all required keys (`tmr_uid`,`user_story`,`test_id`,`maturity`,`data_strategy`,`spine`,`run_evidence`) are preserved, the **immutable `tmr_uid` is the identity** and is unchanged, the **coordinates `user_story` and `test_id` are PRESERVED** (current coordinates, not identity), `session_id` is asserted **only** for exported/container metadata (not a local `tmr-registry.json` field), every enum member is recognized, and **no field is silently dropped**. (R1: codex — enum/field-presence alone is insufficient; identity keys on `tmr_uid`.)

### TC-1.1: enum-member mismatch is detected, not silent  (branch @ S3)
**Data Strategy: REAL-DATA** (tier: code) — a TMR carrying a `data_strategy` value absent from fizzy's set.
- given a TMR with `data_strategy: "FAKE-DATA"` (not in VALID_DATA_STRATEGIES)
- when fizzy validates
- then it rejects with a named error citing the field — never silently drops/accepts.

### TC-1.2: a TMR missing a required field is rejected with a named error  (branch @ S3 — R1)
**Data Strategy: REAL-DATA** (tier: code) — a TMR omitting a required field (`maturity` or `data_strategy`).
- given a TMR with `maturity` (or `data_strategy`) absent
- when fizzy validates
- then it rejects with a named missing-field error (not a silent default). (R1: codex — semantic completeness, not just enum validity.)

### TC-1.3: a `tmr-registry.json` record converts field-for-field to the internal schema  (branch @ S2 — R3, DR-11/DD-1)
**Data Strategy: REAL-DATA** (tier: code — pytest) — load a real `tmr-registry.json` record (NOT a markdown `TMR:` block — the registry is the SoR; F′ never parses markdown) into the internal TMR record.
- given a `tmr-registry.json` record with **every** required keystone key (incl. `tmr_uid`, `title`, `source_spec`, `critical_seam`, `criticality_source`, `status`)
- when `TmrParser` converts it to the internal representation
- then every keystone field round-trips faithfully (no key dropped, no enum coerced); a record with an **unknown key**, a **missing required key**, or a **bad enum** is rejected with a named `schema_error`. (R3: gemini / DR-11/DD-1 — fixtures use `tmr-registry.json` field-for-field, not a markdown-TMR block.)

### TC-1.4: `live_or_induced` is a strict union — the "no technique" case has exactly one encoding  (branch @ S3 — R6-C7)
**Data Strategy: REAL-DATA** (tier: code — pytest) — TMR records exercising each `live_or_induced` form against `TmrParser`.
- given (a) `live_or_induced: null` (JSON null), (b) `live_or_induced: {kind: "tc-netem:partition"}`, (c) `live_or_induced: {kind: "other", detail: "cgroups"}` — all valid; and (d) `live_or_induced: {kind: null}`, (e) `live_or_induced: {"kind": "null"}`, (f) `live_or_induced: {kind: "other"}` (no detail) — all invalid
- when `TmrParser` validates each
- then (a)-(c) are accepted and (d)-(f) are rejected with a named error: `{kind: null}` and `{"kind": "null"}` because `kind` is never null (JSON `null` is the **single** "no technique" encoding), and `other` without `detail` because detail is required. A parser that accepts `{kind: null}` as equivalent to JSON `null` is smoke-only — it reintroduces the dual-encoding ambiguity R6-C7 closed. (R6: codex — union must be strict under `extra:forbid`.)

---

## US-2 — Happy-path-spine authoring (M2)

### TC-2.0: every user story has exactly one spine; failures anchor to a step  [spine]
**Data Strategy: STATIC** (tier: prompt/doc — doc-lint) — parse a real authored tests-pseudo fixture.
**Spine steps:** S1 author US → S2 author spine TC-0 → S3 author failure tests → S4 each cites spine_step_ref.
- given a fixture roadmap with US-X and a tests-pseudo with one `[spine]` test for US-X + two failure tests
- when the authoring lint runs
- then exactly one spine per US is found and every failure test carries a valid `spine_step_ref`.

### TC-2.1: an unanchored failure test is rejected  (branch @ S4)
**Data Strategy: STATIC** (tier: prompt/doc) — fault-induced fixture: a failure test with no `spine_step_ref`.
- given a failure test with no `spine_step_ref`
- when the authoring lint runs
- then it is flagged as "branch off an unplanted trunk" — rejected at authoring.

### TC-2.2: authoring docs actually produce a spine in a live run  (system-validation)
**Data Strategy: REAL-DATA** (tier: prompt/doc — `system-validation`) — a real scoped skill run on a fixture concept.
**why this tier:** a phase-doc rule's behavior is only provable by an LLM following it; can't pytest a prompt.
- given the updated 01/02 phase docs and a fixture feature with 2 user stories
- when a real (scoped) skill run authors the roadmap+tests
- then the produced tests-pseudo has one happy-path spine per user story.

---

## US-3 — Strict MOCK falsification (M2)

### TC-3.0: a MOCK with NO technique + genuine impossibility is accepted  [spine]
**Data Strategy: STATIC** (tier: prompt/doc) — a real test annotated `MOCK`, `live_or_induced: null`, impossibility matrix denying every technique.
**Spine steps:** S1 author MOCK → S2 set `live_or_induced: null` → S3 deny every technique (natural-wait/toxiproxy/tc-netem/external-kill/dev-account) → S4 accepted.
- given a MOCK with `live_or_induced: null` whose `why_impossible_to_reproduce_live` denies every live/induced technique AND which carries a non-empty `technical_constraint` (the citable impossibility reason, DD-3)
- when the MOCK-falsification check runs
- then it is accepted as a justified MOCK — the ONLY case MOCK is allowed — and the check asserts **BOTH** a non-empty `why_impossible_to_reproduce_live` AND a non-empty `technical_constraint` are present (§3.1 conditionally-required for `data_strategy = MOCK ∧ live_or_induced = null`); a check asserting only one is smoke-only. (R1 fix: the spine is a *justified* MOCK, not one that names a technique.)

### TC-3.1: a MOCK that NAMES a technique (or a dev-forceable condition) is promoted  (branch @ S2)
**Data Strategy: REAL-DATA** (tier: LLM-judgment — golden case) — planted: a MOCK with `live_or_induced: tc-netem:partition`; sibling planted on ">100 positions for pagination" (forceable on a dev account, no technique named).
- given a MOCK whose `live_or_induced` names a technique from the enum, OR whose `why_impossible_to_reproduce_live` names a condition forceable on dev infra
- when the check (B/D) runs
- then it is REJECTED as a justified MOCK and the required action is "promote to REAL-DATA" — naming a technique is itself proof the behavior can be induced. (R1: codex CRITICAL — v1 TC-3.0 had this backwards.)

### TC-3.2: a SYNTHETIC critical-seam test with empty why_impossible_to_reproduce_live is rejected  (DR-8)
**Data Strategy: REAL-DATA** (tier: code — pytest) — a TMR with `critical_seam: true`, `data_strategy: SYNTHETIC`, `why_impossible_to_reproduce_live: ""` (or absent).
- given a critical-seam TMR whose `data_strategy ∈ {SYNTHETIC, STATIC, MOCK-EXTERNAL, FRONTEND}` and whose `why_impossible_to_reproduce_live` is empty or absent
- when the MOCK-falsification / §4.3 check runs
- then it is REJECTED with a named error and the required action is "promote to REAL-DATA" — the DR-8 generalization (rule keys on real-ness, not the label) MUST fire on relabels of MOCK as SYNTHETIC/STATIC; a check that only fires on literal `MOCK` is smoke-only and re-opens the relabel-to-bypass loophole DR-8 closed.

---

## US-4 — Maturity ladder (M2)

### TC-4.0: a test carries a maturity and promotes nl→acceptance when accessors named  [spine]
**Data Strategy: REAL-DATA** (tier: code) — a TMR at `nl` whose elements all map to named accessors.
**Spine steps:** S1 nl authored → S2 accessors named → S3 promote to acceptance.
- given a TMR at `maturity: nl` whose elements all resolve to named concept-accessors
- when the promotion check runs
- then it emits PROMOTE nl→acceptance.

### TC-4.1: a concept never named stays at nl and is flagged  (branch @ S2)
**Data Strategy: REAL-DATA** (tier: code) — a TMR whose element references an unnamed concept.
- given a TMR whose element maps to no named accessor across N rounds
- when the promotion check runs
- then it stays `nl` and is flagged BLOCK (concept undesigned) — surfaces the real gap.

---

## US-5 — Parallel-subagent structured guardrails (M3)

### TC-5.0: five guardrails run as separate subagents, each returns structured test/US-keyed findings  [spine]
**Data Strategy: REAL-DATA** (tier: code/orchestration) — a real spec+tests fixture; assert the aggregation shape.
**Spine steps:** S1 revision written → S2 dispatch 5 subagents → S3 each returns structured findings → S4 aggregate+persist.
- given a revised spec fixture and the five guardrail personas
- when the round runs
- then five separate structured result sets return, each finding keyed to a test/US id, aggregated and persisted per round (never one combined prompt).

### TC-5.1: join keys are scoped to TMR-changing findings  (branch @ S3 — R2-corrected)
**Data Strategy: REAL-DATA** (tier: code) — two findings: a TMR-changing one missing `target.{user_story,test_id}`, and a CANON spec-section-scoped one carrying only `target.spec_section`.
- given a **TMR-changing** finding that omits `target.{user_story,test_id}` AND a **spec/contract-scoped** CONS/SCOPE/CANON finding carrying only `target.spec_section`/`target.contract`
- when aggregation runs
- then the TMR-changing finding is **rejected** (can't be journaled without a join key), while the spec/contract finding is **accepted as actionable but NOT journaled** unless its disposition changes a TMR/node field. (R2: codex — v1's blanket "any keyless finding rejected" was too strict.)

### TC-5.2: a guardrail subagent failure is fail-closed via a synthetic ORCH finding  (branch — R3)
**Data Strategy: REAL-DATA** (tier: code — pytest of the orchestrator) — a fixture where one of the five subagents times out / dies / returns invalid JSON.
- given a guardrail round where one subagent fails (timeout, crash, or unparseable output)
- when the orchestrator aggregates
- then it emits a synthetic **`ORCH`** finding — **blocking on the `gauntlet` action, warning on `critique`** — and never proceeds on partial findings as if green. (R3: gemini / R2: both — fail-closed, no false confidence.)

### TC-5.3: conflicting findings on the same target+field enter a conflict state  (branch — R3)
**Data Strategy: REAL-DATA** (tier: code — pytest) — two findings with contradictory `required_action` on the same `target.test_id` + field.
- given two guardrail findings whose `required_action` conflict on the same `target`+field
- when aggregation runs
- then the pair enters a **`conflict`** state requiring human/orchestrator disposition **before** any journaled field transition (no silent last-writer-wins). (R3: gemini / R2: both.)

---

## US-6 — TRACE spine-inversion (M3)

### TC-6.0: a US with prose but no spine is reported ORPHANED  [spine]
**Data Strategy: REAL-DATA** (tier: LLM-judgment — golden case) — planted: a US covered in prose, no spine test.
- given a spec with US-Y described in prose and no happy-path spine test for US-Y
- when TRACE runs
- then TRACE reports US-Y as ORPHANED (a traceability break), not as a test suggestion.

### TC-6.1: a non-spine missing test is NOT flagged by TRACE  (branch)
**Data Strategy: REAL-DATA** (tier: LLM-judgment — golden case) — a US with a spine but a missing minor edge test.
- given a US with a valid spine but a missing non-spine edge-case test
- when TRACE runs
- then TRACE does NOT flag it (the no-test-suggestions rule still holds for non-spine).

---

## US-7 — TCOV liveness guardrail (+ promoter) (M3)

> **Re-centered by morph reconciliation (DR-5, 2026-06-16).** DR-5 deleted `TestInputCollector`
> (raw test-source ingestion) and relocated coverage to US-8's `SpineCoverageChecker`. US-7's old
> spine TC-7.0 ("TCOV ingests standalone files into its input manifest") tested the deleted
> behavior, so US-7 was re-centered on its surviving distinctive deliverable, **`missing_liveness_test`**.
> The new spine is the liveness happy-path; the promoter (rule: US-4/§4.4) and `data_strategy_mismatch`
> (rule: US-3/§4.3) are secondary TCOV findings. See `reference/morph-reconciliation.md`.

### TC-7.0: a critical seam WITH a real/induced test passes TCOV (no missing_liveness_test)  [spine]
**Data Strategy: REAL-DATA** (tier: code — pytest of the TCOV liveness check) — a fixture TMR for a critical-seam happy-path input carrying a REAL-DATA (or induced) test with a recorded `live_or_induced` technique.
**Spine steps:** S1 load a critical-seam happy-path TMR (`critical_seam:true`) → S2 it is REAL-DATA, or carries a recorded `live_or_induced` technique → S3 TCOV runs its liveness check → S4 NO `missing_liveness_test` finding (the clean/pass case).
- given a critical-seam happy-path input (`critical_seam:true`) covered by a REAL-DATA or induced test with a recorded `live_or_induced` technique
- when TCOV runs its liveness check
- then it emits **no** `missing_liveness_test` finding (the critical seam is proven live). The negative branches are TC-7.1 (mock-only → block) and TC-7.2 (`criticality_unknown` → fail-closed). (Re-centered spine — DR-5 morph; positive counterpart to TC-7.1's `LIV-POS`/`LIV-NEG`.)

### TC-7.1: a critical seam with no REAL/induced test → blocking missing_liveness_test  (branch)
**Data Strategy: REAL-DATA** (tier: LLM-judgment — golden case) — planted corpus with stable fixture IDs: `LIV-POS` (critical-seam happy-path, `critical_seam:true`, covered only by a MOCK) and `LIV-NEG` (a non-critical happy-path covered only by a MOCK).
- given a critical-seam happy-path input (`critical_seam:true`, or `architecture_link` to a system-altitude boundary; `criticality_unknown` is treated as critical) covered only by a mock with no live/induced counterpart
- when TCOV runs
- then on `LIV-POS` it emits a blocking `missing_liveness_test` finding with `target.{user_story,test_id}` set; and on `LIV-NEG` (non-critical) it does NOT (false-positive guard). (R1: codex — criticality must be enumerable per §3.3; oracle needs planted IDs + a negative case.)

### TC-7.2: criticality_unknown on a system-altitude happy-path is treated as critical (fail-closed)  (branch @ S3 — R2)
**Data Strategy: REAL-DATA** (tier: code — pytest) — a TMR with `critical_seam:null`, `criticality_source:unknown`, `altitude:system`, covered only by a MOCK.
- given a system-altitude happy-path TMR whose `critical_seam` is JSON `null` and `criticality_source` is `unknown`, covered only by a mock
- when the liveness check / TCOV runs
- then it is treated as **critical** (fail-closed) and emits a blocking `missing_liveness_test` — never silently non-critical. (R2: codex — closes the `criticality_unknown` gap; `null`+`unknown` = critical-until-resolved.)

---

## US-8 — Deterministic F′ spine-coverage gate (M4)

> **Re-centered by morph reconciliation (SEC-1 reframe, recorded v10 / 2026-06-16).** The v4 SEC-1
> reframe (carried into v9) moved US-8's center of gravity: the **mechanical, non-bypassable gate is
> Fizzy-side** (`pipeline_advance` invoking this slice's F′ checker), and the **skill-side pre-check is
> advisory**. TC-8.0 + TC-INV-001 were never re-centered — they still labelled the skill-side pre-check
> **PRIMARY** and asserted it as the blocker, inverting the trust model.
> **Migration ledger:** `mechanical F′ gate → relocated→Fizzy (pipeline_advance, calls the §6 R4-2 checker
> contract `uv run gauntlet-check`)`; `skill-side pre-check → reframed (PRIMARY → advisory fail-fast)`; both
> anchored US-8 (spine TC-8.0 + invariant TC-INV-001). **Fate = Re-centered:** the distinctive survivor (the
> deterministic F′ coverage gate, owned by no other US) becomes the new primary — spine + invariant rewritten to
> the Fizzy mechanical gate with the skill-side check as advisory and the **negative oracle** that Fizzy refuses
> `pipeline_advance` when no F′ evidence is attached even if the advisory pre-check passed. Hard grep + soft scan:
> **0 orphaned spines** (the spine premise now names a LIVE capability — the Fizzy mechanical gate — not the
> retracted skill-side-PRIMARY behavior). See `reference/morph-reconciliation.md`.

<!-- tmr_uid: 01J0EXEMPLARULID00000000XY -->
### TC-8.0: a Fizzy gauntlet-entry transition with full spine coverage is admitted by the F′ checker  [spine]
**Data Strategy: REAL-DATA** (tier: code — pytest) — real fixture roadmap manifest + `tmr-registry.json`, full coverage, invoked through the §6 normative F′ checker contract.
**Spine steps:** S1 load roadmap US set + `tmr-registry.json` → S2 Fizzy invokes the F′ checker (`uv run gauntlet-check --action gauntlet --output json`) at the `pipeline_advance` boundary → S3 the checker parses each TMR via `TmrParser` and confirms every US has exactly one `active`, `spine:true` record at acceptable maturity → S4 exit 0 (`pass`), Fizzy admits the transition.
**Exemplar `TMR:` block** (the structured form §4.2 requires; **F′ parses the corresponding `tmr-registry.json` record, not this markdown block — this block is the generated-view mirror only**, never the `[spine]` tag):
```yaml
TMR:
  test_id: TC-8.0
  tmr_uid: 01J0EXEMPLARULID00000000XY    # compiler-allocated ULID (DR-4); illustrative, length-26
  title: a Fizzy gauntlet-entry transition with full spine coverage is admitted by the F′ checker
  user_story: US-8
  also_covers: []
  maturity: nl
  spine: true
  spine_steps: [S1, S2, S3, S4]
  spine_step_ref: null
  spine_of: null
  data_strategy: REAL-DATA
  live_or_induced: {kind: natural-wait}    # R6-C7 tagged union
  technical_constraint: null
  why_impossible_to_reproduce_live: null
  verification_mode: automated-integration
  verification_scope: targeted
  altitude: system
  tested_by: llm
  critical_seam: false
  criticality_source: explicit
  architecture_link: []
  accessors: []
  binding_status: unbound
  status: active                            # DR-3 lifecycle
  supersedes: []                            # array of tmr_uids, default [] (fix-2)
  tombstoned_at: null
  run_evidence: null                        # nl + pre-Phase-8 ⇒ null is valid (§3.1 partition)
  source_spec: adv-spec-202606151042-liveness-gate-test-ladder
```
- given a fixture roadmap (US-1..US-3) and a `tmr-registry.json` where each US has exactly one `status:active, spine:true` record at `nl` or `acceptance`, AND a fixture `pipeline_advance` call into the gauntlet lane
- when Fizzy invokes the F′ checker contract (§6 R4-2) as part of the mechanical transition gate
- then the checker emits `{outcome: "pass"}` (exit 0), Fizzy admits the transition, and the same registry passed through the **advisory** skill-side pre-check also returns pass (sanity); the **mechanical** admission is the Fizzy-gated branch, not the advisory branch (§6 SEC-1).
- **Negative oracle**: same fixture with the Fizzy checker invocation **stubbed out / not wired** — the advisory skill-side pre-check still returns pass, but Fizzy must **refuse `pipeline_advance`** because no F′ evidence was attached at the transition. A test that admits the transition on the advisory pass alone is smoke-only and reintroduces the SEC-1 honor-system hole.

### TC-8.1: an uncovered user story → exit 2  (branch @ S3)
**Data Strategy: REAL-DATA** (tier: code — pytest) — fixture where US-3 has no spine test.
- given the same fixture but US-3 has no `spine:true` test
- when the gate runs for `gauntlet`
- then it exits 2 naming US-3; bypass only with `--accept-missing-spine` + a logged reason (written to decisions.log).

### TC-8.2: maturity-awareness — an nl spine passes at debate→gauntlet  (branch @ S3)
**Data Strategy: REAL-DATA** (tier: code — pytest) — fixture with spine tests only at `nl`.
- given every US has a `spine:true` test at `maturity: nl`
- when the gate runs at the debate→gauntlet phase
- then it passes (does NOT demand `concrete`/live; that's G's Phase-8 gate).

### TC-8.3: critique action is advisory, not blocking  (branch — R1)
**Data Strategy: REAL-DATA** (tier: code — pytest) — fixture with a missing spine, gate invoked for `critique`.
- given a fixture with US-3 missing a spine, and the gate invoked for the `critique` action
- when the gate runs
- then it WARNS but does NOT exit 2 (advisory during critique); the same fixture exits 2 for `gauntlet` (blocking only at gauntlet entry).

### TC-8.4: a DUPLICATE happy-path spine for one US → exit 2 at gauntlet  (branch @ S3 — R1)
**Data Strategy: REAL-DATA** (tier: code — pytest) — `tmr-registry.json` fixture where US-2 has TWO active `spine:true` records.
- given a fixture roadmap (US-1..US-3) and a `tmr-registry.json` with two `status:active, spine:true` records for the same scalar `user_story: US-2`
- when the gate runs for `gauntlet`
- then it exits 2 naming the duplicated US (F′ enforces **exactly one**, not just ≥1); the same fixture WARNS (non-blocking) for `critique`. (R1: codex — §4.1 "exactly one" must be enforced, closing the §4.1↔§6 gap.)

---

## US-9 — Test provenance journal (M5)

### TC-9.0: a TMR-field change appends a driver-tagged record; per-US journey replays  [spine]
**Data Strategy: REAL-DATA** (tier: code — pytest) — drive a real maturity + data_strategy change, read back.
**Spine steps:** S1 create test → S2 change a field → S3 append record → S4 read journey for the US.
- given a test whose `data_strategy` changes MOCK→REAL-DATA driven by a TCOV finding
- when the change is applied
- then the journal appends `{subject_type:test, field:data_strategy, from:MOCK, to:REAL-DATA, driver:{type:guardrail, ref:<finding_id>}}`, and a per-US query replays the journey in order.

### TC-9.1: append-only — a prior record is never rewritten  (branch @ S3)
**Data Strategy: REAL-DATA** (tier: code — pytest) — two changes to the same test.
- given two successive field changes on one test
- when both are journaled
- then both records exist (append-only); the first is unmodified.

---

## US-10 — Altitude-triage provenance (M5)

### TC-10.0: node altitude journaled created→close with altitude_fit; queries answer  [spine]
**Data Strategy: REAL-DATA** (tier: code — pytest) — a node created subsystem, closed with a fit attestation.
**Spine steps:** S1 depth_triage created → S2 (optional) reclassify → S3 close altitude_fit → S4 query.
- given a node `created` at `subsystem` and closed with `altitude_fit: right`
- when the accuracy + distribution queries run
- then "of subsystem-tagged, % right by the end" counts it as correct, and the distribution histogram counts it under subsystem.

### TC-10.1: a silently-wrong altitude (stable but altitude_fit=too_low) is NOT counted correct  (branch @ S3)
**Data Strategy: REAL-DATA** (tier: code — pytest) — node stable at subsystem but close fit = too_low.
- given a node `created` subsystem, never reclassified, closed `altitude_fit: too_low`
- when the precision query runs
- then it is NOT counted correct (stability alone over-counts; the fit attestation corrects it).

---

## US-11 — Phase-8 pseudo→real promotion (M6)

### TC-11.0: a critical-seam test is promoted (producer-split), RUN, and required green  [spine]
**Data Strategy: REAL-DATA** (tier: code — pytest of the promotion-pass logic) — a fixture critical-seam test, with an owner-repo fixture supplying the executable test + bound accessors.
**Spine steps:** S1 select critical-seam/spine pseudo test → S2 Phase-8 emits a typed `promotion_request` (the skill does NOT write target-repo code) → S3 the owner-repo fixture supplies the executable test + bound accessors → S4 the skill-runner executes the declared command + captures typed `run_evidence`, required green.
- given a critical-seam test at `acceptance` with `run_evidence: null`, AND an owner-repo fixture that authors the executable test + binds the accessors
- when the Phase-8 promotion pass runs
- then it emits a `promotion_request{tmr_uid, repo, accessors[], command, expected_evidence, negative_oracle}`; the owner-repo fixture supplies the executable test/bound accessors; the **skill-runner** executes the declared `command` at the correct tier and **captures** typed `run_evidence{tier:"code", result:"pass", ...}` (it never trusts an owner-written `result:pass`). The test does NOT claim the skill writes target-repo code (DD-4 / R5-C2 producer split). (codex Patch 12.)

### TC-11.1: a declared-but-never-run REAL-DATA test counts as failing  (branch @ S3)
**Data Strategy: REAL-DATA** (tier: code — pytest) — a REAL-DATA test with `run_evidence: null` at close.
- given a REAL-DATA critical-seam test never promoted+run
- when implementation close is evaluated
- then it is treated as failing (not passing); spine/critical-seam may not be `spike`/exempt.

---

## US-12 — Version-fence (M6)

### TC-12.0: a legacy session (authoritative created_at < fence_cutover_ts) keeps its original rules  [spine]
**Data Strategy: REAL-DATA** (tier: code — pytest) — a session whose Fizzy card `created_at < fence_cutover_ts`.
- given a session whose **authoritative** timestamp (the Fizzy session-card `created_at`, per `ContractVersionResolver`) is `< fence_cutover_ts`
- when the gates evaluate it
- then `ContractVersionResolver` classifies it **legacy** and the new requirements do not apply (no retroactive failure) — fence status is decided by the immutable `created_at` vs `fence_cutover_ts`, **NOT** by the local `liveness_contract_version` marker.

### TC-12.1: a post-fence session (created_at ≥ fence_cutover_ts) is held to the new gates, even with a missing/lower marker  (branch)
**Data Strategy: REAL-DATA** (tier: code — pytest) — a session whose Fizzy card `created_at ≥ fence_cutover_ts`, with the local marker missing or lowered.
- given a session whose authoritative `created_at ≥ fence_cutover_ts`, missing a spine test, whose local `liveness_contract_version` marker is **absent or lower** than `tmr.v1`
- when the gate runs
- then `ContractVersionResolver` classifies it **post-fence** and the new F′ requirement applies (exit 2) — a deleted/lowered marker on a post-cutover session is **still post-fence**. A marker-only test (one that flips the outcome by editing the marker alone, ignoring `created_at`) is **invalid**.

---

## US-13 — Glossary / ADR / document-types (M7)

### TC-13.0: vocabulary present + no "spine" collision  [spine]
**Data Strategy: STATIC** (tier: prompt/doc — doc-lint) — grep the committed docs.
- given the updated CONTEXT.md, document-types.md, and the ADR
- when the doc-lint runs
- then "happy-path spine", TMR, maturity ladder, liveness terms are defined; "happy-path spine" is always qualified **in prose** (never bare "spine" colliding with "Architecture Spine") — the doc-lint targets **prose only**; the machine identifiers `spine` / `spine_steps` / `spine_step_ref` and the `[spine]` tag are canonical keystone tokens and are **exempt** (R1: codex/gemini, per spec §4.1); the ADR records the test-ladder/TMR/liveness decision + two-spec scope split.

---

## US-14 — Verification tiers (cross-cutting)

### TC-14.0: every task declares a verification tier driving its mode  [spine]
**Data Strategy: STATIC** (tier: prompt/doc — doc-lint of the execution plan) — parse task records.
- given the execution plan's task records
- when the tier-lint runs
- then every task declares a verification tier (code / prompt-doc / llm-judgment) and a `verification_mode` consistent with it (code→`automated-*`/`test-producer`; prompt-doc→`system-validation`/`manual-ux`; judgment→`system-validation` with a golden-case corpus oracle). (R1: codex — there is NO `golden-eval` member in `VALID_VERIFICATION_MODES`; assert only canonical modes.)

### TC-14.1: a code-seam task marked spike/exempt is flagged  (branch)
**Data Strategy: REAL-DATA** (tier: code — pytest of the lint) — a code-seam task with `verification_mode: static-check`.
- given a code-seam (F′/journal) task assigned an exempt mode
- when the tier-lint runs
- then it is flagged (critical code seams must be REAL-DATA pytest, not exempt).

---

## US-15 — Getting Started / bootstrap (R2)

### TC-15.0: the documented first-run path bootstraps and verifies a gate  [spine]
**Data Strategy: REAL-DATA** (tier: prompt/doc — `system-validation`) — follow the documented bootstrap on a fixture.
**Spine steps:** S1 start post-fence session → S2 author one [spine]/US → S3 run authoring lint → S4 attempt gauntlet → observe pass/exit-2.
- given the Getting Started doc and a fixture feature
- when an operator follows the steps verbatim
- then they reach a passing spine gate (full coverage) and a blocking `exit 2` (missing-spine fixture) without reading the implementation.

### TC-15.1: docs do NOT prescribe a copy-deploy step  (branch — anti-regression)
**Data Strategy: STATIC** (tier: prompt/doc — doc-lint) — grep the Getting Started doc.
- given the Getting Started / deploy docs
- when the doc-lint runs
- then they state the deployed skill is a symlink (edits live, no copy) and contain no **affirmative/prescriptive** `cp -r ... ~/.claude/skills` instruction — a *negative* warning ("do NOT run cp -r") is allowed and expected, so the lint forbids prescriptive copy steps, not every occurrence of the string. (R1: codex/gemini — the doc itself negatively mentions `cp -r`.)

<!-- P4_INVARIANT_TESTS_START -->
## Invariant Tests (Phase 4)

> Cross-cutting architectural-invariant tests derived from `architecture-invariants.json`
> (Phase 4, lightweight). These assert the **invariants hold across the system**, distinct from
> the per-feature TCs above. Per the semantic-oracle rule each carries a positive AND a
> negative/counterfactual assertion — a test that would still pass under the wrong behavior is
> smoke-only and does not satisfy the invariant.

### TC-INV-001: no gauntlet-entry path bypasses Fizzy's invocation of the F′ checker  (INV-001/002/003)
**Data Strategy: REAL-DATA** (tier: code — pytest) — enumerate every code path that transitions a post-fence session into the gauntlet.
- given the two enforcement layers — the **mechanical primary** Fizzy gauntlet-entry gate (calls the §6 R4-2 checker contract) and the **advisory** skill-side pre-check (`enforce_pipeline_card_gate` + the in-process pre-check, fail-fast only) — and a post-fence session
- when a session is dispatched into the gauntlet via `pipeline_advance` (the only mechanically gated path; direct `debate.py` invocation is the advisory-only path)
- then full-spine coverage passes both layers (mechanical: exit 0 + admit; advisory: warn-clean)
- assert (positive): a session with one `status:active, spine:true` TMR per US is admitted by `pipeline_advance` (Fizzy invokes the checker; checker returns `pass`)
- assert (negative — the actual non-bypassability claim): a session missing a spine is **blocked by Fizzy at `pipeline_advance`** (mechanical) regardless of whether the advisory skill-side pre-check ran or was skipped. A test that asserts the skill-side pre-check is the blocker is **wrong**: the skill-side pre-check is a prompt-enforced honor system (§6 SEC-1) and **cannot mechanically gate** an out-of-process MCP call. The mechanical gate is Fizzy's `pipeline_advance` refusal.
- assert (negative — checker-side failure modes): a Fizzy invocation where the checker times out / returns invalid JSON / is on an unrecognized `contract_version` / receives stale hashes → Fizzy **refuses the transition** (R4-2 fail-closed); a test that admits the transition on any of these is smoke-only.

### TC-INV-004: schema divergence is always a named rejection, never a silent drop  (INV-004)
**Data Strategy: REAL-DATA** (tier: code — pytest) — round-trip TMRs through the parser/validator.
- given a TMR with all-canonical fields, and a sibling TMR carrying one unknown field / unknown enum member
- when the parser/validator runs
- then the canonical TMR round-trips with no key dropped, the **immutable `tmr_uid` identity unchanged**, and the **coordinates `user_story`/`test_id` PRESERVED** (current coordinates, not identity; `session_id` asserted only for exported/container metadata, not a local field)
- assert (positive): every required key preserved; no enum coerced; identity keys on `tmr_uid`
- assert (negative): the divergent TMR is rejected with a named error **citing the offending field** — a test that passes when the unknown field is silently dropped is smoke-only

### TC-INV-008: the canonical TMR schema exists in exactly one location  (INV-008)
**Data Strategy: STATIC** (tier: code — static check / grep) — scan both repos for the TMR field table.
- given the canonical contract path and both repos
- when the duplicate-copy check runs
- assert (positive): the canonical `test-maturity-record-schema.md` exists and is the single source
- assert (negative): a planted second copy of the TMR field table (in either repo) makes the check FAIL — a check that only verifies the canonical file exists is smoke-only

### TC-INV-009: no consumer re-derives critical_seam  (INV-009)
**Data Strategy: STATIC** (tier: code — static check) — AST/grep over consumers of criticality.
- given the classifier (sole writer) and all consumers of `critical_seam`
- when the re-derivation check runs
- assert (positive): every consumer reads the normalized TMR `critical_seam` field
- assert (negative): a planted local derivation of criticality from `architecture_link` outside the classifier is caught — a check that ignores `architecture_link` usage is smoke-only

### TC-INV-010: partial guardrail results never read as green  (INV-010)
**Data Strategy: REAL-DATA** (tier: code — pytest of the orchestrator) — a round where one of five subagents fails.
- given a 5-guardrail round on the gauntlet action where one subagent times out / crashes / returns invalid JSON
- when the orchestrator aggregates
- assert (positive): 5/5 returns → aggregation proceeds normally
- assert (negative): 4/5 returns → a synthetic `ORCH` finding is emitted and the round does **NOT** complete green — a test that passes when the round completes on 4/5 is exactly the false-confidence hole this spec closes

### TC-INV-013: the journal is strictly append-only  (INV-013)
**Data Strategy: REAL-DATA** (tier: code — pytest) — two successive field changes on one subject.
- given a journal with record k already written
- when record k+1 is appended for the same subject
- assert (positive): both records exist, in order; a per-subject replay returns them in sequence
- assert (negative): the **byte range of record k is unchanged** after k+1 is appended, and no in-place edit API exists — a test asserting only "a new record exists" is smoke-only (it would pass even if record k were rewritten)

### TC-INV-015: a silently-wrong-but-stable altitude is not counted correct  (INV-015)
**Data Strategy: REAL-DATA** (tier: code — pytest) — node never reclassified, closed with a fit attestation.
- given a node created subsystem, never reclassified
- when the precision query runs
- assert (positive): closed `altitude_fit: right` → counted correct
- assert (negative): closed `altitude_fit: too_low` → **NOT** counted correct, despite altitude stability — a precision metric keyed on stability alone is smoke-only

### TC-INV-016: the version fence is non-retroactive, anchored on the authoritative created_at  (INV-016)
**Data Strategy: REAL-DATA** (tier: code — pytest) — the SAME missing-spine input under two authoritative timestamps.
- given an identical missing-spine session shape evaluated once with authoritative `created_at < fence_cutover_ts` (legacy) and once with `created_at ≥ fence_cutover_ts` (post-fence), per `ContractVersionResolver`
- when the F′ gate runs
- assert (positive): post-fence (authoritative `created_at ≥ fence_cutover_ts`) → exit 2
- assert (negative): legacy (same input, authoritative `created_at < fence_cutover_ts`) → NOT failed — the outcome flips on the **immutable created_at vs fence_cutover_ts**, NOT on the editable local marker; a gate that flips on the marker alone (or fails the legacy session retroactively) is wrong. A marker-only test is invalid.

### TC-INV-017: declared-but-never-run REAL-DATA critical-seam counts as failing  (INV-017)
**Data Strategy: REAL-DATA** (tier: code — pytest of close evaluation) — a critical-seam test at close.
- given a REAL-DATA / critical-seam / happy-path-spine test evaluated at implementation close
- when close is evaluated
- assert (positive): promoted + run-green (`run_evidence{tier:"code", env, result:"pass", ...}` — the DR-1 `code` variant) → close passes
- assert (negative): `run_evidence: null` → close **FAILS** (counts as failing), and the test may not be `spike`/exempt — a close that passes on null run_evidence is the exact liveness hole this spec exists to kill

### TC-INV-018: verification_mode is always canonical; no golden-eval member  (INV-018)
**Data Strategy: REAL-DATA** (tier: code — pytest + static-check lint) — parse execution-plan task records.
- given the execution plan's task records
- when the tier-lint runs
- assert (positive): every task's `verification_mode ∈ VALID_VERIFICATION_MODES`
- assert (negative): a task with `verification_mode: "golden-eval"` is rejected (no such enum member), and a code-seam task with an exempt mode (`artifact-sync`/`static-check`/`manual-ux`) is flagged — a lint that accepts golden-eval is smoke-only
<!-- P4_INVARIANT_TESTS_END -->

