# Plan: Liveness Gate + Architecture-Linked Test Ladder (adversarial-spec slice)

> Date: 2026-06-15 | Owner: Jason | Status: draft for evaluation
> Origin: prediction-prime gateway "runs but never fills" incident. Source plans:
> `prediction-prime/docs/plans/live-book-path-and-liveness-gate.md` (Track B/C) and
> `prediction-prime/docs/plans/test-ladder-fizzy-and-adversarial-spec-design.md` (§4).
> Scope of THIS plan: changes to the **adversarial-spec skill only**
> (`skills/adversarial-spec/`). The fizzy-side enforcement (TMR persistence, run-evidence,
> sweep gate) and prediction-prime infra (fault injection, live fills) are out of scope here
> and tracked in their own repos.

## The failure this closes

A critical integration seam (prediction-prime's feed→`bookCache` happy path) was specified,
mocked, and shipped without ever being proven live. The algo "runs but never fills" because the
happy-path input was only ever a fake-socket unit test; the spec covered it (TRACE green);
acceptance tests were well-specified (TCOV green on what it could see); and **not one REAL-DATA
test ever executed against a live gateway**. Two mechanisms trace directly to this skill:

1. **The MOCK-justification gate degraded** from "impossible to reproduce live" to "hard to make
   deterministic." Convenience/determinism got accepted as impossibility.
2. **The between-round guardrails are document linters (correctly — they run nothing), but nothing
   downstream forces a critical-seam REAL-DATA test to actually execute before close.** TRACE
   traces requirement→spec-*section* and is forbidden from flagging missing tests; TCOV audits only
   the declared `tests-pseudo/tests-spec` ledger, so standalone test files (e.g.
   `gateway/tests/*.mjs`) are invisible. All guardrails pass green while no REAL-DATA test has run.

## Principle threaded through every change

Acceptance criteria for a **critical seam** are **LIVE or fault-induced**, never unit-green. A mock
is supplementary coverage, never sole evidence. The fix for a liveness hole must itself be gated on
liveness. **Rigor scales with altitude** — the happy-path-spine + REAL-DATA obligation binds hardest
at system altitude / critical seams and lightens (never to zero) for component-altitude work, matching
fizzy's existing altitude→obligation model. The skill's "critical seam" ≈ fizzy's high-altitude /
system-validation journey.

## Test maturity ladder (phase-appropriate rigor)

Canonical 3-level ladder (glossary `nl/acceptance/concrete`; design doc calls `concrete`→`functional`):

| Level | What it is | Phase it's appropriate in |
|---|---|---|
| `nl` | natural-language test (the `(stage: nl)` form already in `02-roadmap.md:140`) | roadmap / debate |
| `acceptance` | executable against the concept-accessor façade — compiles, real oracle, accessors *unbound* ("attempted code") | post-debate / early execution |
| `concrete` / `functional` | accessors bound, test actually executes (live-run for REAL-DATA) | implementation |

**Principle:** every user story must have a happy-path spine test, but **only at the maturity
appropriate to the current phase** — never demand max rigor early. The debate gate (F′) accepts `nl`
or `acceptance`; the live-run/`concrete` demand is the separate Phase-8 gate (G). Promotion is
as-early-as-possible (a test stuck at `nl` across rounds is itself a flag). **The US↔test↔maturity
machinery is the keystone** (shared with fizzy's TMR schema) — design it carefully: how user stories
are enumerated, how a test declares which US it is the spine for, how maturity is tracked/promoted,
and what level each phase's gate requires.

## Scope boundary

| Codebase | Owns | This plan? |
|---|---|---|
| prediction-prime | Track A live book path/first fill, B6/B7 fault-injection infra | ❌ |
| fizzy_pipeline_mcp | §5: **BUILD** data_strategy + liveness + happy-path-spine schema & gates (there is **no M-4b gate to extend** — see Reality check), `pipeline_test` run-evidence, execution-verification gate in sweep, TMR registry, B4/B8 *enforcement* | ❌ separate, coordinated spec |
| **adversarial-spec (this)** | §4 authoring + TRACE/TCOV/SPINE guardrails + phase placement; parent B1/B2/B3/B5; B9 pseudo→real promotion pass | ✅ |
| prediction-prime (also) | concept-accessor **façade + bindings file + fail-closed lint** (design §2–3) — the executable form of *its own* contracts.md, in *its own* CI | ❌ unassigned in all 3 reports; flag |

Coupling note: this skill **authors and emits** the Test Maturity Record (TMR) fields and **drives**
the pseudo→real promotion; fizzy **persists and enforces** them at sweep. The TMR field set is the
shared contract — it must be agreed (schema-first) before either side builds.

## Reality check (verified against fizzy code 2026-06-15)

The fizzy-side report did a code-level reality check that corrects a premise **both** prediction-prime
source plans inherited. Confirmed against `fizzy-pipeline-mcp/src/`:
- **The "M-4b test-lineage gate" does not exist.** Zero hits for M-4b / test-lineage / an
  nl→acceptance→concrete ladder. `sweep_passed_tasks` (`pipeline.py:4437`) gates on lane uniformity,
  `test_result=="pass"`, and verification-evidence/step-attestation — not test maturity. The only
  `MATURITY_RANK` is over `implementation_status` (greenfield<partial<already-built), a different axis.
  ⇒ Do not write "extend M-4b" anywhere; fizzy must **build** the gate.
- **data_strategy / live_or_induced / spine are absent** — genuinely new axes.
- **The NASA V-model altitude system is built and landed** (`VALID_ALTITUDES`, `ALTITUDE_OBLIGATIONS`
  = pure function of altitude, `mark_system_validation_complete`, `VALID_VERIFICATION_MODES` /
  `MODE_SCOPE_MATRIX`). New work attaches data_strategy + liveness as two missing **axes** on this
  model and the spine/REAL-DATA obligation as a new **altitude-scaled right-arm obligation** — not a
  parallel state machine.

Consequence for this skill: per-test-case **Data Strategy** (already in `02-roadmap.md` §9a) must
propagate to fizzy's new task-card `data_strategy` field; `verification_mode` (unit/integration) and
`data_strategy` (real/faked) are **orthogonal** and both required for critical-seam tasks.

## What already exists (extend, do not rebuild)

- `why_impossible_to_reproduce_live:` mechanism — `phases/02-roadmap.md:428`, attacked by PEDA/BURN/AUDT
  (`scripts/adversaries.py:158,302,664`). Tighten; don't reinvent.
- happy-path + error-case test requirement — `phases/02-roadmap.md:43`. Upgrade to spine model.
- `verification_mode` + `test_refs` + `automated-*` machinery — `phases/07-execution.md:262–524`. Extend.
- Five-guardrail framework — `GUARDRAILS` dict (`scripts/adversaries.py:1346`), wired through
  `phases/03-debate.md`. Add a sixth.
- tests-pseudo.md staleness gate — `scripts/debate.py:1361`. Good foundation.
- Guardrails run nothing **by design** (per design §4.5 + parent B9 corrected). The execution gate
  belongs at the Phase 8 pseudo→real handoff + fizzy sweep — NOT inside debate. Do not make debate
  guardrails execute tests.

## Resolved: the term is "happy-path spine" (Jason, 2026-06-15)

"Architecture Spine" already means the execution-plan file-structure list (`phases/07-execution.md:210`,
`phases/08-implementation.md:406`, glossary). The new test concept is the **"happy-path spine" (TC-0)** —
always written with the `happy-path` qualifier, **never bare "spine"**, to avoid colliding with
Architecture Spine. `CONTEXT.md` gets an explicit glossary entry distinguishing the two.

---

## Changes (blast zone, file by file)

### A. Authoring — `phases/01-init-and-requirements.md` + `phases/02-roadmap.md`
- Upgrade `02-roadmap.md:43`: every user journey declares **exactly one** happy-path spine test (TC-0)
  with **named steps** S1…Sn.
- Every failure/error test cites the spine step it branches from (`spine_step_ref`); a failure test
  with no anchor is rejected at authoring.
- Add TMR fields to the `tests-pseudo.md` row format (§9): `maturity` (nl/acceptance/functional),
  `live_or_induced`, `architecture_link`, `accessors`, `spine`/`spine_step_ref`. Today only
  `Data Strategy:` + `why_impossible_to_reproduce_live:` exist.
- Add the asymmetry note: the spine *event* is easy to reproduce live, but the spine *test* is the
  hardest to write — which is why it gets deferred into never.

### B. Strict MOCK falsification (parent B2) — `phases/02-roadmap.md` §9a + adversary prompts
- Tighten `why_impossible_to_reproduce_live:` from a prose impossibility claim to **naming the
  technique that WOULD make it live**: `toxiproxy:corrupt/drop`, `tc-netem:latency/partition`,
  `external-kill`, `natural-wait`. MOCK-only accepted ONLY when no technique exists.
- Promote `live_or_induced:` to a first-class field (technique pointer), distinct from the prose
  justification.
- Mirror the stricter standard into PEDA/BURN/AUDT prompt text (`scripts/adversaries.py:158,302,306,664`)
  and the `phases/03-debate.md:404` directive.

### C. TRACE — `scripts/adversaries.py` (`REQUIREMENTS_TRACER`, 1174–1216) + `reference/guardrail-prompts.md`
- Today TRACE is forbidden from flagging missing tests (line 1210). **Invert specifically for the
  spine:** a journey with prose but no happy-path spine test = ORPHANED, a traceability break — not a
  test suggestion. Keep the general no-test-suggestions rule for everything else.
- **Absorbs SPINE's semantic check (E dropped):** also judge whether the test *labeled* spine is
  actually the **primary success path** for that journey (not an edge case mislabeled). TRACE already
  reasons about journeys/coverage, so this fits its persona.

### D. TCOV — `scripts/adversaries.py` (`TEST_COVERAGE_AUDITOR`, 1284–1343) + `reference/guardrail-prompts.md` + `phases/03-debate.md` invocation contract (line 889)
1. **Promoter, not just auditor:** emit `PROMOTE nl→acceptance` for tests whose elements all map to
   named accessors; emit `BLOCK` when a concept is unnamed.
2. **Ingest ALL test files** for in-scope owner paths, not just the ledger. Update the `03-debate.md:889`
   input contract.
3. **Strict `data_strategy_mismatch`** (category #9, line 1316): require the fault-injection technique.
4. **New category `missing_liveness_test`:** a critical seam whose happy-path input has no REAL/induced
   test is a **blocking** finding.

### E. ~~New SPINE guardrail~~ — **DROPPED** (Jason, 2026-06-15); no 6th mini-adversary
Keep the guardrail set at five (CONS/SCOPE/TRACE/CANON/TCOV). SPINE's intended checks split across
pieces we already touch, so a new persona + extra per-round LLM call isn't warranted:
- *coverage* (every journey has a happy-path spine; exactly one; failures anchored to a named spine
  step) → deterministic gate **F′** (structural — no LLM needed) + early surfacing via **C**.
- *semantics* (is the declared spine actually the primary success path? oracle real? strategy
  REAL-DATA-or-justified?) → **C** (is-it-the-happy-path) and **D** (TCOV `weak_oracle` +
  `data_strategy_mismatch`).

### F. ~~Absent-test gauntlet adversary (parent B5)~~ — **DROPPED** (Jason, 2026-06-15)
No new gauntlet persona. Reaching the gauntlet (Phase 5) *at all* without happy-path-spine coverage is
the failure — so enforcement belongs **before** the gauntlet, not as a hostile persona inside it (too
late; probabilistic; the architecture is already designed). Replaced by F′ + the existing between-round
guardrails (C/D/E).

### F′. Deterministic happy-path-spine coverage gate at the gauntlet-entry chokepoint — `scripts/debate.py`
The **teeth** that make spine coverage non-bypassable:
- Add a gate to `enforce_pipeline_card_gate()` (`debate.py:1351`, runs in `main()` before **every**
  `critique`/`gauntlet` action) as a sibling to the existing tests-pseudo staleness gate (`:1456`).
- Mechanical check: **every user story in the roadmap manifest has ≥1 test in `tests-pseudo.md` tagged
  `spine: true` that references it.** Any uncovered user story → `exit 2`; bypass only via a logged
  override (mirror `--accept-tests-stale` / `IntentionalOverride` ≥50-char reason →
  `sessions/<id>.decisions.log`).
- **Maturity-aware (load-bearing):** the gate requires a spine test *at the level appropriate to the
  current phase*, never max rigor early. At debate→gauntlet an `nl` (or `acceptance`) spine **passes**;
  the `concrete`/`functional` + live-run demand is deferred to **G**. The gate checks *existence at an
  acceptable maturity for this phase*, not executability. (See "Test maturity ladder" above.)
- Because the gate fires on the `gauntlet` action, **you cannot run the gauntlet without a
  test-covered happy path for every user story** — exactly the requirement. Depends on **A** (the TMR
  `spine:`/`maturity`/US-reference fields must exist to key on).
- This is deterministic (structural absence — an LLM can't hand-wave it). The semantic layer code
  can't judge — is the declared spine actually the primary success path? oracle real? strategy
  REAL-DATA-or-justified? — is supplied by **C** (TRACE-spine-inversion, surfaces as early as Round 1)
  and **D** (TCOV). No 6th adversary (E dropped).
- **Note:** this is the *debate-time, document-only* spine gate (coverage declared + REAL-DATA-or-justified).
  The *live-run* spine gate (the declared spine test actually RUN green against live/dev) is **G** at the
  Phase 8 / fizzy-sweep handoff. Two gates, two phases, one happy-path-spine concept.

### G. Pseudo→real promotion pass (parent B9-corrected + B4) — `phases/08-implementation.md` + `phases/07-execution.md`
- Add an explicit promotion pass before implementation closes: each pseudo test that is REAL-DATA /
  critical-seam / happy-path-spine gets written as a real executable test, **RUN**, and required green
  against live/dev infra. A pseudo test never promoted-and-run = **failing**.
- Phase 7: spine/critical-seam tests cannot be assigned a `spike`/exempt `verification_mode`.
- Enforcement at sweep is fizzy's job; the skill drives the promotion and passes `run_evidence`.
  Document the handoff so a blocked first-fill HALTS downstream instead of being parked (B8).

### H. Reference / glossary
- `CONTEXT.md`: add TMR, the spine term (qualified, post-decision), liveness vocabulary; resolve the
  Architecture-Spine collision.
- `reference/document-types.md`: updated `tests-pseudo.md` row format.
- New ADR recording the test-ladder / TMR / liveness-gate decision and the cross-project scope split.

### J. Per-session decision provenance journal (meta-analysis substrate) — NEW (Jason, 2026-06-15)
Goal: for **every** session, actively track how key classification decisions evolved. Generalized over
`subject_type ∈ {test, node}` (one append-only journal — see schema Piece 3 / §4a):
- **`test`** — each user story's test journey: every test tied to a US, its maturity moves
  (`nl→acceptance→concrete`), `data_strategy` changes (`MOCK→REAL-DATA`), spine designation — tagged
  with the **driver** (debate round / guardrail TCOV/TRACE / human correction).
- **`node`** — the **altitude-triage** decision per task node: `created`@depth_triage →
  reclassifications → close `altitude_fit` (`right|too_high|too_low`).
- **Meta-analysis queries this unlocks** (all over the one journal): test-journey replay; altitude-triage
  accuracy ("of nodes tagged subsystem, % right by the end" = stable AND `altitude_fit==right`); and
  **altitude distribution** (histogram of altitudes identified — count nodes by altitude).
- Home: append-only `…/registry.journal.jsonl`; promote into `.architecture` test registry on close
  (design §5.4/§5.5 — fizzy-side persistence). Node-altitude journaling + close `altitude_fit` are
  fizzy-side (emit at the existing change-detection hook `pipeline.py:6263`; `altitude_fit` is new).
- **Hard prerequisite — structured guardrail output (K):** guardrails today emit prose the orchestrator
  reads and discards. The journal needs findings emitted as **structured records keyed to test/US IDs**
  and persisted. Provenance journal and structured-output guardrails land together.

### K. Guardrail execution: parallel subagents + structured output — DECIDED (Jason, 2026-06-15)
**Observability gap (verified 2026-06-15):** `token_tracking` records by model only — no guardrail tag;
inline runs leave no structured trace at all; dispatched runs are indistinguishable from debate
critiques. We cannot today answer "dispatch vs inline %," nor "what did TCOV say about TC-1.5 in R2."
- **Decision: each guardrail runs as its own parallel subagent**, launched together after each revision,
  each emitting **structured findings keyed to test/US IDs** (not prose), persisted per round.
- Each subagent is self-contained: prompt (the guardrail persona) + file pointers it reads itself
  (spec, `tests-pseudo.md`, roadmap manifest, contract index, `.architecture/*`) + **the round diff**.
  Subagents start fresh (no main-conversation inheritance) — that diff is how they get "what changed."
- The main loop aggregates the N structured returns → writes the per-round provenance entries (J) and
  drives the fix/approve workflow.
- **This makes the C/D changes a dispatch-mechanism change, not just prompt edits:** the `03-debate.md`
  invocation contract (currently "assemble inputs → critique-or-inline") becomes a **parallel-subagent
  dispatch + structured-aggregation** spec. Never one combined prompt (persona dilution).
- Per-guardrail structured-finding schema (test/US-id keyed) is part of the TMR/machinery keystone.

---

## Decisions (resolved + open)

1. ✅ **Spine naming** — "happy-path spine" (Jason, 2026-06-15). See Resolved section above.
2. ✅ **Scope split** — **two coordinated specs**, schema-first: one adversarial-spec session (A–H
   here) + one fizzy session (all of §5, P0→P3). The shared **TMR field set is the keystone** — agree
   it before either side builds; fizzy's P0 schema constants and this skill's `tests-pseudo.md` TMR
   row must match field-for-field. (Both this analysis and the fizzy report converge here.)
3. ✅ **No dogfood now** (Jason, 2026-06-15) — premature. Author/run with the **current** skill
   version; **version the changes newly** so the new gates apply to *new* specs going forward, not
   retroactively to in-flight sessions (e.g. `validation-leg-process`). Mirrors the fizzy-side
   back-compat fence (gate behind a version bump / altitude, legacy sessions untouched).
4. ✅ **No new adversaries** (Jason, 2026-06-15) — drop BOTH the absent-test gauntlet persona (F) AND
   the proposed SPINE 6th guardrail (E). Keep five guardrails. Enforce happy-path-spine coverage with
   the **deterministic gate at the gauntlet-entry chokepoint** (F′); fold the semantic checks into
   **C** (TRACE: is the labeled spine the real primary path?) and **D** (TCOV: oracle + data_strategy).
   Mini-adversaries alone can't be a hard gate (LLM, advisory, overridable) — the *force* is the
   deterministic check at the chokepoint that already gates the gauntlet action.
5. ✅ **Guardrail execution mechanism (K)** — **parallel subagents** (Jason, 2026-06-15), each emitting
   structured test/US-keyed findings persisted per round to feed the test-journey ledger (J). Never one
   combined prompt. Makes C/D a dispatch-mechanism change, not just prompt edits.

## Versioning (per decision 3)

Fence the new authoring requirements + guardrails so they activate for new specs only:
- skill/phase-doc changes carry a version marker; in-flight sessions keep the rules they started under;
- on the fizzy side this corresponds to a `verification_contract_version` bump (or altitude gating) so
  legacy cards aren't retroactively failed.

## Sequencing

P0 **shared TMR schema** (jointly with fizzy) → authoring + strict-MOCK (A, B) → P1 guardrail edits
(C, D) + deterministic spine gate (F′) → P2 phase-placement promotion pass (G) → structured-output
guardrails + test-journey ledger (K, J) → glossary/ADR (H)
throughout. The document-only guardrail edits (C/D) and the spine gate (F′) are independent and can
parallelize. fizzy's P0 schema is the hard prerequisite for G's enforcement to mean anything; K is the
prerequisite for J.
