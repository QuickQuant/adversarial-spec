# Spec: Liveness Gate + Architecture-Linked Test Ladder (adversarial-spec slice)

> Session: adv-spec-202606151042-liveness-gate-test-ladder | Card 5715 | Altitude: **system**
> Depth: technical/full | Draft: **v4** (post-gauntlet) | Status: gauntlet synthesized (507→32); CB-1..7 + trust-model reframe (SEC-1/2/3/4, DD-1) incorporated; ~20 remaining accepts + test-ladder→registry migration tracked for next pass
> R1 changelog: F′ exactly-one happy-path spine; canonical `verification_mode`; MOCK-rule fix; prose/token rule.
> R2 changelog: `critical_seam`+`criticality_source` promoted to REAL keystone fields (added to canonical §1/§2);
> structured `TMR:` block required per test [**SUPERSEDED v4/DD-1: records live in `tmr-registry.json`**]; F′
> **skill-side pre-check is PRIMARY** [**SUPERSEDED v4/SEC-1: the Fizzy-side gate is the mechanical one**]
> (gates the Fizzy path, not just standalone debate.py); guardrail subagents **fail-closed** (synthetic ORCH
> finding) + **conflict** state; only TMR-changing findings need test join keys; journal derives from accepted
> state changes; override→journal resolved (decisions.log + driver-ref, no `subject_type:session`); maturity
> threshold reconciled (`nl` passes at debate→gauntlet); `spike` is a *test_strategy*, not a verification_mode.
> v4 changelog (post-gauntlet CB-cluster): CB-1 §2.1 maturity contradiction → `nl` passes; CB-2 §0.2 MOCK-rule
> un-inverted; CB-3 §11 join-key scoped to TMR-changing findings; CB-4 §4.2 adds `title`+`source_spec`; CB-5
> promotion needs ≥1 accessor (`all([])` guard); CB-6 §13 coverage claim corrected (14 spine tests still need
> `TMR:` blocks); CB-7 bootstrap authors `TMR.spine`, not the `[spine]` tag.
> v4 trust-model reframe (post-gauntlet, Jason-approved): SEC-1 the non-bypassable gate is **Fizzy-side** (calls
> the skill's F′ checker); skill-side = fail-fast; the fizzy spec is now a HARD DEPENDENCY (INV-003 reframed).
> DD-1 TMR records move to **`tmr-registry.json`** (system of record); `tests-pseudo.md` = generated view. SEC-2
> fence keyed on immutable `created_at` (defeats marker-deletion downgrade). SEC-3 override reason = non-whitespace
> floor. SEC-4 skill RUNS tests + captures a typed receipt; honest local-admin trust model. ~20 remaining accepts next.
> Keystone contract (referenced, never copied):
> `Brainquarters/shared-context/test-maturity-record-schema.md`
> Plan: `docs/plans/liveness-gate-and-test-ladder.md`
> **Version fence:** the new gates/fields land behind `liveness_contract_version = tmr.v1`.
> Sessions started before the fence keep their original rules (no retroactive failure).

---

## 0. Problem & Goals

### 0.1 The failure this closes
A critical integration seam (prediction-prime's feed→`bookCache` happy path) was specified,
mocked, and shipped **without ever being proven live**. The algo "runs but never fills": the
happy-path input was only ever a fake-socket unit test. The spec covered it (TRACE green),
acceptance tests were well-specified (TCOV green on what it could *see*), and **not one
REAL-DATA test ever executed against a live gateway**. Two mechanisms trace directly to *this
skill*:

1. **The MOCK-justification bar degraded** from "impossible to reproduce live" to "hard to make
   deterministic." Convenience got accepted as impossibility.
2. **The between-round guardrails are document linters** (correctly — they run nothing), and
   **nothing downstream forces a critical-seam REAL-DATA test to actually execute before the
   gauntlet.** TRACE traces requirement→spec-*section* and is forbidden from flagging missing
   tests; TCOV audits only the declared `tests-pseudo`/`tests-spec` ledger, so standalone test
   files (e.g. `gateway/tests/*.mjs`) are invisible. All guardrails pass green while no
   REAL-DATA test has run.

### 0.2 Goals
- Make it **impossible to reach the gauntlet** (via the **Fizzy-enforced** path, SEC-1) without a
  phase-appropriate-maturity **happy-path spine** test for every user story — the skill-side check is
  fail-fast; the mechanical gate is Fizzy-side (§6).
- Require every `MOCK` to **prove no live/induced technique exists** (`live_or_induced: null` + a falsification
  denying every technique) — otherwise **promote to `REAL-DATA`**. *(A justified MOCK names NO technique; naming one
  is itself proof the behavior can be induced — see §4.3. CB-2: v3's "name the technique or promote" inverted the rule.)*
- Give the five guardrails **structured, persisted, test/US-keyed** output (provenance + meta-analysis).
- Provide a durable **decision provenance journal** (test-maturity journey + altitude-triage),
  generalized over `subject_type ∈ {test, node}`.
- Define a **shared TMR schema contract** with fizzy, **schema-first** (field-for-field).
- Classify every deliverable by **verification tier**; apply this project's liveness interpretation.
- **Version-fence** the new gates so in-flight sessions are unaffected.

### 0.3 Governing principle
Acceptance criteria for a **critical seam** are **LIVE or fault-induced**, never unit-green; a
mock is supplementary coverage, never sole evidence. The fix for a liveness hole must itself be
gated on liveness. **Rigor scales with altitude** — the happy-path-spine + REAL-DATA obligation
binds hardest at system altitude / critical seams and lightens (never to zero) for
component-altitude work, matching fizzy's existing `altitude → obligation` model.

---

## 1. Scope & the two-spec split

This is the **adversarial-spec skill slice** (features A, B, C, D, F′, G, H, J, K +
keystone + verification tiers + version fence). The skill **authors and emits** the Test Maturity
Record (TMR) and **drives** the pseudo→real promotion. A **separate, coordinated fizzy spec**
*persists and enforces* the same fields at sweep **and mechanically enforces F′ at gauntlet-entry by
calling the checker this slice defines**. Post-gauntlet (SEC-1) that fizzy gate is a **hard
dependency** for the "non-bypassable" claim — this slice alone delivers fail-fast advisories plus the
F′ contract, not a mechanical gate. The **TMR field set is the keystone** — agreed schema-first before
either side builds.

| Codebase | Owns | In this spec? |
|---|---|---|
| **adversarial-spec (this)** | authoring (A) + strict MOCK (B) + TRACE/TCOV folds (C, D) + F′ debate gate + provenance journal authorship (J) + structured-subagent guardrails (K) + Phase-8 promotion driver (G) + glossary/ADR (H) | ✅ |
| fizzy_pipeline_mcp | TMR persistence, `VALID_*` constants, run-evidence storage, **the mechanical F′ gate at gauntlet-entry** (calls this skill's F′ checker) + sweep-time enforcement, node-altitude journaling | ❌ separate coordinated spec — **HARD DEPENDENCY** for non-bypassability (SEC-1), not optional |
| prediction-prime | concept-accessor façade + bindings + fail-closed lint; live-fill (Track A); fault-injection infra | ❌ flagged unassigned; out of skill scope |

**Reality check (verified against fizzy code 2026-06-15):** there is **no "M-4b test-lineage
gate"** to extend — it is a phantom both prediction-prime source plans inherited. fizzy's NASA
V-model altitude system *is* built (`VALID_ALTITUDES`, `ALTITUDE_OBLIGATIONS`,
`mark_system_validation_complete`, `VALID_VERIFICATION_MODES`/`MODE_SCOPE_MATRIX`). The new work
attaches `data_strategy` + liveness as two **missing axes** on that model, and the spine/REAL-DATA
obligation as a new **altitude-scaled right-arm obligation** — not a parallel state machine.

### 1.1 Non-goals
- fizzy-side persistence/enforcement (separate coordinated spec) — **a hard dependency, not optional**:
  the mechanical, non-bypassable F′ gate lives there (SEC-1); this slice defines the contract it enforces.
- The concept-accessor façade / bindings / fail-closed lint (target-repo + its CI).
- **Dogfooding these changes on this very session** — author/run on the *current* skill version;
  version the changes.
- The sessions-stats dashboard — deferred, forward-only, separate trigger (after this card hits
  debate R2). No backfill.
- Backfilling provenance for past sessions.
- prediction-prime live-fill work (Track A) and fault-injection infra (B6).

---

## 2. Getting Started (bootstrap)
<!-- Addresses US-15 -->

**Audience:** an operator who wants to bootstrap the liveness gate + test ladder and verify a gate
locally in minutes, without reading the implementation.

**Prerequisites**
- A Claude Code session with the `adversarial-spec` skill available.
- `~/.claude/skills/adversarial-spec` is a **symlink** to the source tree
  (`skills/adversarial-spec/`). **Edits to source are live immediately — there is NO copy step.**
  Do **not** run `cp -r … ~/.claude/skills` (this corrects the stale CLAUDE.md "manual copy" line).
- Python 3.14+, `uv`, and the repo's test deps (`uv run pytest` works).

**First-run path (post-fence session)**
1. Start a **post-fence** `/adversarial-spec` session (its `liveness_contract_version` ≥ `tmr.v1`).
2. Author **exactly one happy-path spine (TC-0) test per user story**, each with a **TMR record
   (`spine: true`)** in **`tmr-registry.json`** and named steps `S1…Sn`; anchor each failure test to a spine step
   via `spine_step_ref`. *(`tests-pseudo.md` is the generated prose view; the `[spine]` heading is a display aid —
   F′ parses the registry, not the tag. CB-7 + DD-1. Authoring UX — direct-registry vs prose-emitted — is §12.13.)*
3. Run the **authoring lint** — it confirms one happy-path spine per US and that every failure
   test carries a valid `spine_step_ref`.
4. Enter **debate**; iterate. (The F′ gate is *advisory* here — it warns about uncovered US but
   does not block, so early debate proceeds while tests mature.)
5. **Attempt gauntlet entry** and observe the F′ gate: full spine coverage → pass; a US with no
   spine test → `exit 2` naming the uncovered US. *(This is the fail-fast advisory; the **mechanical**
   block is Fizzy-side at the gauntlet transition — §6, SEC-1.)*

**Run the F′ gate against a fixture (no implementation reading required)**
- Full-coverage fixture → gate passes (exit 0).
- Missing-spine fixture → gate `exit 2` naming the uncovered US.
- Bypass only via a logged override (`--accept-…` + a ≥50-char reason written to
  `sessions/<id>.decisions.log`).

**Time to value:** an operator reaches a passing spine gate and a blocking `exit 2` on the two
fixtures within minutes, having only authored `nl` tests.

**Failure / prerequisite-not-met handling**
- No roadmap manifest → the gate cannot enumerate user stories; it reports the missing manifest
  rather than passing silently.
- `tests-pseudo.md` absent → the authoring lint emits a blocking setup warning (not a silent pass).

### 2.1 Lifecycle of one test under these gates (end-to-end walkthrough)
<!-- Addresses US-15 (gemini R1: end-to-end journey) -->
Follows the canonical worked example (keystone schema §5, "arm→fill"):
1. **roadmap/debate (`nl`):** author the happy-path spine TC-0 (`spine:true`, named steps, a
   `data_strategy` + `live_or_induced`); failure tests cite `spine_step_ref`. F′ is *advisory* here.
2. **debate (`nl`→`acceptance`):** a TCOV/TRACE finding may flip a field (e.g. `data_strategy`
   MOCK→REAL-DATA); each flip appends a Piece-3 journal transition citing the driver; tests promote
   to `acceptance` as accessors get named.
3. **debate→gauntlet (F′):** every US has exactly one `spine:true` test at **any phase-appropriate maturity**
   (`nl | acceptance | concrete`; **`nl` passes**) → **passes**. F′ checks existence at acceptable maturity, NOT
   executability — the `concrete`/live-run demand is the Phase-8/G gate. *(CB-1: reconciled with §4.4/§6/TC-8.2;
   v3's stray "≥`acceptance`" here was the contradiction.)*
4. **implementation (G):** `binding_status unbound→bound`; the spine RUN live →
   `run_evidence{result:pass, env:dev, artifact}`; `maturity acceptance→concrete`. fizzy sweep
   requires the spine `concrete`+green before any failure-branch card completes.
5. **close:** the US's TMRs + journal promote into `.architecture/tests/registry.json`, linked to the
   architecture node — so the suite outlives the spec and re-runs when the node changes.

---

## 3. Keystone: shared TMR schema contract (schema-first)
<!-- Addresses US-1 -->

**The contract lives in one canonical file and is referenced, never copied:**
`Brainquarters/shared-context/test-maturity-record-schema.md`. Divergence of this contract is the
exact failure this work exists to prevent. If a copy appears in either repo, delete it.

The contract has **three coupled pieces**, all keyed to the data model:
1. **TMR** — the per-test record (`session · user_story · test_id`). **Stored as `tmr-registry.json`**
   (the local **system of record**, DD-1); `tests-pseudo.md` is a **generated prose view**, never
   authoritative. The canonical *schema* (field set + enums) is the keystone file above; the *records*
   live in the registry. *(Resolves the v3 §4.2 "feeder/view vs authoritative gate input" contradiction.)*
2. **Guardrail finding** — what each parallel-subagent guardrail returns, keyed to `user_story`/`test_id`.
3. **Decision provenance journal** — append-only, over `subject_type ∈ {test, node}`.

### 3.1 Shared enums (must match fizzy P0 field-for-field)
| Enum | Members | Source of truth |
|---|---|---|
| `maturity` | `nl` → `acceptance` → `concrete` | **NEW** (define here; fizzy P0 adds). `functional` is a design-doc alias for `concrete`; **canonical is `concrete`**. |
| `data_strategy` | `REAL-DATA`, `REAL-DATA + PROPERTY`, `SYNTHETIC`, `MOCK`, `MOCK-EXTERNAL`, `FRONTEND`, `STATIC` | skill (`CONTEXT.md` / `02-roadmap.md §9a`); fizzy P0 adds `VALID_DATA_STRATEGIES` |
| `live_or_induced` | `natural-wait`, `toxiproxy:corrupt`, `toxiproxy:drop`, `tc-netem:latency`, `tc-netem:partition`, `external-kill`, `null` | **NEW** (define here; fizzy P0 adds `VALID_LIVENESS_TECHNIQUES`) |
| `verification_mode` | `automated-unit`, `automated-integration`, `automated-contract`, `automated-component`, `test-producer`, `artifact-sync`, `static-check`, `manual-ux`, `system-validation` | **fizzy** (`VALID_VERIFICATION_MODES`) — reference, do not redefine |
| `verification_scope` | `targeted`, `full-suite`, `static`, `manual`, `end-to-end` | **fizzy** |
| `altitude` | `component`, `subsystem`, `system` | **fizzy** (`VALID_ALTITUDES`) |
| `tested_by` | `llm`, `user`, `both` (default `llm`) | **fizzy** (`VALID_TESTED_BY`) |
| `run_evidence.env` | `live`, `dev`, `ci` | **NEW** (extends fizzy v3 evidence block) |
| `run_evidence.result` | `pass`, `fail` | **fizzy** (`VALID_BASELINE_RESULTS`) |
| `run_evidence` (shape, SEC-4) | typed receipt `{command, cwd, repo, commit, started_at, finished_at, result, env, artifact_uri, artifact_sha256, runner, verification_mode, live_or_induced}` | **NEW** — skill captures it by RUNNING the test (§8.1); never hand-written |
| `binding_status` | `unbound`, `bound` | **NEW** (acceptance→concrete promotion key; define here, fizzy P0 adds) |
| `critical_seam` | `true`, `false`, `null` (JSON null) | **NEW (R2)** — added to canonical §2; `null`+`criticality_source:unknown` = `criticality_unknown` (treated as critical) |
| `criticality_source` | `explicit`, `architecture_link`, `unknown` | **NEW (R2)** — companion to `critical_seam`; fizzy P0 adds |

**`null` is JSON `null`, not the string `"null"`** (R2: codex) — applies to `live_or_induced`,
`critical_seam`, `run_evidence.*`, `spine_step_ref`.

**Orthogonality (load-bearing):** `verification_mode` answers *unit vs integration*;
`data_strategy` answers *real vs faked*; `altitude` answers *how deep / how much rigor*. Three
independent axes — a critical-seam task sets all three. `data_strategy` is the genuinely missing
axis fizzy lacks.

### 3.2 Handshake (which repo lands constants first)
fizzy P0 adds `VALID_DATA_STRATEGIES`, `VALID_LIVENESS_TECHNIQUES`, and `maturity`; this skill's
`tests-pseudo.md` TMR row and emission must match field-for-field. **Decision needed in Round 1:**
which repo lands the constants first, and how a mismatch is *detected* (fizzy P0 validation
rejects an unrecognized field/enum member with a named error; it must never silently drop/accept).
Until then, TMR fields are **optional + warn-first**, promoted to required behind the version fence
(schema decision 5).

### 3.3 Critical-seam classification (R1 keystone addition — coordinate with fizzy)
The liveness obligation (`missing_liveness_test` in §5.3, the Phase-8 promotion in §8.1) only has
teeth if "critical seam" is **operationally enumerable**. v1 left it undefined (R1: codex HIGH). Add
a criticality source to the TMR contract:
- **`critical_seam: true | false | null`** — the normalized TMR field consumers read (never an
  independent local derivation).
- **`criticality_source: explicit | architecture_link | unknown`** — how it was set: `explicit`
  (author-set), `architecture_link` (derived from an `architecture_link` resolving to a
  **system-altitude integration boundary** — the V-model ranks altitude), or `unknown`.
  `architecture_link` is an **input** to classification, not a parallel contract.
- **Fail-closed (R2):** `critical_seam:null` + `criticality_source:unknown` = `criticality_unknown`
  → a system-altitude happy-path input is treated as **critical** until resolved (never silently
  non-critical — the exact degradation this spec kills). If explicit and architecture-derived values
  **disagree** → fail closed as critical + emit a blocking finding.

**Promoted to REAL keystone fields (R2: both critics, CRITICAL).** v2 referenced `critical_seam` as
if canonical while it was absent from the contract — fizzy would reject/drop it. `critical_seam` +
`criticality_source` are now **added to the canonical keystone** (`…/test-maturity-record-schema.md`
§1 enums + §2 TMR). fizzy P0 must validate both. Tracked as coordination item §12.7.

---

## 4. Authoring: happy-path spine + maturity ladder
<!-- Addresses US-2, US-3, US-4 -->
**Blast zone:** `phases/01-init-and-requirements.md`, `phases/02-roadmap.md` (§9/§9a),
`reference/document-types.md` (row format).

### 4.1 The happy-path-spine model (A)
<!-- Addresses US-2 -->
- Every user journey (== user story) declares **exactly one happy-path spine test (TC-0)** with
  **named steps** `S1…Sn`. (Term is always written **"happy-path spine"**, never bare "spine" —
  see §10 / locked term decision.)
- Every failure/error test **cites the spine step it branches from** (`spine_step_ref`, e.g.
  `"S4"`). A failure test with **no anchor** is **rejected at authoring** ("a branch off an
  unplanted trunk").
- Add the asymmetry note to the authoring doc: the happy-path spine *event* is easy to reproduce
  live, but the happy-path spine *test* is the hardest to write — which is why it gets deferred into
  never. Naming this is what keeps it from being skipped.
- **Prose vs machine tokens (R1: codex/gemini).** The locked rule forbids **bare "spine" in prose**
  (it collides with "Architecture Spine") — prose always says **"happy-path spine."** But the machine
  identifiers `spine` / `spine_steps` / `spine_step_ref` and the `[spine]` tag are the **canonical
  keystone TMR field names** (US-1, field-for-field with fizzy) and are **kept verbatim** — renaming
  them to `happy_path_spine*` would break the cross-repo contract. TC-13.0's doc-lint therefore
  targets **prose only**, not machine tokens. *(Rejected gemini's field/tag rename; accepted the
  prose-discipline point.)*

### 4.2 Structured TMR records in `tmr-registry.json` (A) — REVISED post-gauntlet (DD-1)
Each test's TMR is a **structured record in `tmr-registry.json`** — the **local system of record** — whose
**keys match the canonical keystone field-for-field**: `title`, `source_spec`, `test_id`, `user_story`,
`maturity`, `spine`/`spine_steps`/`spine_step_ref`, `data_strategy`, `live_or_induced`,
`why_impossible_to_reproduce_live`, `verification_mode`, `verification_scope`, `altitude`, `tested_by`,
`critical_seam`/`criticality_source`, `architecture_link`, `accessors`, `binding_status`, `run_evidence`.
**`tests-pseudo.md` is a generated prose VIEW** (human-readable), regenerated from the registry — its
markdown headings, prose "Spine steps," and `[spine]` tag are **display aids only**. F′ and the guardrails
parse the **registry**, never embedded markdown YAML (DD-1: 7 adversaries flagged
LLM-authored-YAML-in-markdown as fragile + a dual source of truth). *(CB-4: `title` + `source_spec` are
keystone fields per the TC-8.0 exemplar / TC-1.3.)*

**One shared `TmrParser`** loads + validates the registry field-for-field (unknown key / missing required
key → named `schema_error`, **never** coerced to "0 spines"; FM-3) and is the **only** TMR reader for F′,
guardrails, and emission (no per-gate parsers — DD-7).

`verification_tier` (§9) is **feeder-only planning metadata** — it is NOT emitted to fizzy as a TMR field.
(The TC-8.0 exemplar in `tests-pseudo.md` shows the record shape; the authoritative copy is the registry entry.)

### 4.3 Strict MOCK falsification (B)
<!-- Addresses US-3 -->
- Tighten `why_impossible_to_reproduce_live:` from a prose impossibility claim to **naming the
  technique that WOULD make it live**: `toxiproxy:corrupt/drop`, `tc-netem:latency/partition`,
  `external-kill`, `natural-wait`. `MOCK`-only is accepted **only when no technique exists**.
- Promote `live_or_induced:` to a **first-class field** (the technique pointer), distinct from the
  prose justification.
- Mirror the stricter standard into the PEDA/BURN/AUDT adversary prompt text
  (`scripts/adversaries.py`) and the `phases/03-debate.md` MOCK-falsification directive (line ~404).
- A `MOCK` whose `why_impossible_to_reproduce_live` names a condition **forceable on dev infra**
  (and that names no technique) is flagged; required action = **promote to REAL-DATA**.

### 4.4 The maturity ladder (phase-appropriate rigor) (US-4)
<!-- Addresses US-4 -->
| Level | What it is | Phase it's appropriate in |
|---|---|---|
| `nl` | natural-language test (the existing `(stage: nl)` form) | roadmap / debate |
| `acceptance` | executable against the concept-accessor façade — compiles, real oracle, accessors **unbound** ("attempted code") | post-debate / early execution |
| `concrete` | accessors **bound**, test actually executes (live-run for REAL-DATA) | implementation |

**Principle:** every US must have a happy-path spine test, but **only at the maturity appropriate
to the current phase** — never demand max rigor early. Debate-time accepts `nl`/`acceptance`;
`concrete`/live-run is the separate Phase-8 gate (G). **Promotion is as-early-as-possible**: a test
stuck at `nl` across rounds is itself a flag. A TMR at `nl` with **≥1 element**, whose elements **all** resolve to
**named concept-accessors** → `PROMOTE nl→acceptance`. **An empty `accessors` list does NOT auto-promote** —
`all([])` is vacuously `True`, so promotion requires **at least one** named accessor (CB-5). An element that maps to
**no named accessor across N rounds** → stays `nl` and is flagged `BLOCK` (concept undesigned — surfaces the real gap).

---

## 5. Guardrail rearchitecture: parallel subagents + structured output
<!-- Addresses US-5, US-6, US-7 -->
**Blast zone:** `scripts/adversaries.py` (`REQUIREMENTS_TRACER`, `TEST_COVERAGE_AUDITOR`,
`GUARDRAILS` dict), `reference/guardrail-prompts.md`, `phases/03-debate.md` (invocation contract).

### 5.1 Parallel-subagent dispatch with structured findings (K)
<!-- Addresses US-5 -->
- **Each of the five guardrails (CONS/SCOPE/TRACE/CANON/TCOV) runs as its own parallel subagent**,
  launched together after each revision — **never one combined prompt** (persona dilution).
- Each subagent is **self-contained**: its persona prompt + file pointers it reads itself (spec,
  `tests-pseudo.md`, roadmap manifest, canonical contract index, `.architecture/*`) + **the round
  diff**. Subagents start fresh (no main-conversation inheritance); the diff is how they learn
  "what changed."
- Each emits **structured findings keyed to test/US IDs** (Piece 2 of the keystone), not prose.
- The main loop **aggregates the N structured returns**, writes the per-round provenance entries
  (J), and drives the fix/approve/dismiss workflow.
- **Join keys scoped to TMR-changing findings (R2: codex).** Only findings that would change a TMR
  field require `target.{user_story, test_id}`. CONS/SCOPE/CANON findings are legitimately
  **spec-section/contract-scoped** (`target.spec_section` / `target.contract`) — they stay actionable
  but are **not journaled** unless their disposition changes a TMR or node field. *(v1's blanket
  "no join key → rejected" was too strict.)*
- **Fail-closed on subagent failure (R2: both, CRITICAL).** If a guardrail subagent dies, times out,
  or returns invalid JSON, the orchestrator emits a synthetic **`ORCH`** finding — **blocking on
  `gauntlet`, warning on `critique`**. Never proceed on partial findings (that is false confidence,
  the very failure class this spec exists to kill).
- **Conflict state (R2: both).** Two findings with conflicting `required_action` on the same
  `target`+field enter a **`conflict`** aggregation state requiring human/orchestrator disposition
  **before** any journaled field transition.
- This makes the C/D changes a **dispatch-mechanism change**, not just prompt edits: the
  `03-debate.md` invocation contract becomes a parallel-subagent dispatch + structured-aggregation
  spec.
- **Observability rationale:** `token_tracking` records by model only — today we cannot answer
  "dispatch vs inline %" nor "what did TCOV say about TC-1.5 in R2." Structured per-guardrail
  output closes that gap.

### 5.2 TRACE inversion (C)
<!-- Addresses US-6 -->
- Today TRACE is **forbidden** from flagging missing tests. **Invert specifically for the
  happy-path spine:** a journey with prose but **no happy-path spine test = `ORPHANED`** (a
  traceability break), not a test suggestion. The **general no-test-suggestions rule still holds**
  for everything else (a missing non-spine edge-case test is NOT flagged by TRACE).
- **Absorbs the dropped SPINE guardrail's semantic check (E dropped):** TRACE also judges whether
  the test *labeled* the spine is actually the **primary success path** for that journey (not an
  edge case mislabeled). TRACE already reasons about journeys/coverage, so this fits its persona.

### 5.3 TCOV: promoter + liveness (D)
<!-- Addresses US-7 -->
1. **Promoter, not just auditor:** emit `PROMOTE nl→acceptance` for tests whose elements all map
   to named accessors; emit `BLOCK` when a concept is unnamed.
2. **Ingest ALL test files** for in-scope owner paths, not just the `tests-pseudo`/`tests-spec`
   ledger (standalone `*.test.*` files are otherwise invisible). Update the `03-debate.md`
   input contract accordingly.
3. **Strict `data_strategy_mismatch`** (require the fault-injection technique; align with B).
4. **New category `missing_liveness_test`:** a **critical seam** whose happy-path input has **no
   REAL/induced test** (covered only by a mock with no live/induced counterpart) is a **blocking**
   finding.

**Critical-seam classification source (R1: codex — required for #4 to be operational).**
`missing_liveness_test` (and G's Phase-8 obligation) hinge on knowing *which* tests are critical
seams — but nothing in v1 made that enumerable. A TMR row that can trigger `missing_liveness_test`
must expose a criticality source: an explicit **`critical_seam: true|false`** field, **or** derived
from `architecture_link` pointing at a **system-altitude integration boundary**. If criticality
cannot be determined for a system-altitude happy-path input, **fail closed as `criticality_unknown`**
(treated as critical until resolved). See §3.3 — this is a **keystone addition** to coordinate with
the fizzy spec.

### 5.4 Dropped, by decision (no new adversaries)
- **E — new SPINE guardrail: DROPPED.** Its checks split across pieces already touched: *coverage*
  → deterministic gate **F′** + early surfacing via **C**; *semantics* → **C** (is-it-the-happy-path)
  and **D** (TCOV `weak_oracle` + `data_strategy_mismatch`). Guardrail set stays at **five**.
- **F — absent-test gauntlet adversary: DROPPED.** Reaching the gauntlet *at all* without
  happy-path-spine coverage is the failure, so enforcement belongs **before** the gauntlet (F′),
  not as a hostile persona inside it (too late; probabilistic; architecture already designed).

---

## 6. Deterministic happy-path-spine coverage gate (F′)
<!-- Addresses US-8 -->
**Blast zone:** `scripts/debate.py` — `enforce_pipeline_card_gate()` (runs in `main()` before
**every** `critique`/`gauntlet` action), as a **sibling to the existing tests-pseudo staleness
gate**.

**INV-003 (reframed post-gauntlet, SEC-1):** non-bypassability is delivered by the **Fizzy-side**
mechanical gate (below), not the skill-side prompt; this slice provides fail-fast advisories + the F′
contract Fizzy enforces. With that reframe, the **teeth** are:
- **Mechanical check:** every user story in the **roadmap manifest** has **exactly one** test in
  `tests-pseudo.md` tagged `spine: true` referencing it — **≥1 AND ≤1** (R1: codex). Deterministic —
  structural absence *or duplication* an LLM can't hand-wave. A **duplicate** happy-path spine for one
  US → warn on `critique`, `exit 2` on `gauntlet` (same action-branching as the missing case). This
  makes §6 consistent with §4.1's "exactly one."
- **Blocks gauntlet entry only:** on the `gauntlet` action, any uncovered US → **`exit 2`** naming
  the user story. **Advisory (warn, non-blocking) during `critique`** so early debate isn't blocked
  while tests are still maturing. *(R1 roadmap-debate decision.)* **NB (code-confirmed):** the
  existing `enforce_pipeline_card_gate` applies its checks *uniformly* to both `critique` and
  `gauntlet` (`round_actions={"critique","gauntlet"}`, `debate.py:1370`); F′ is the first check that
  must **branch on `args.action`** — block on `gauntlet`, warn on `critique`.
- **Maturity-aware (load-bearing):** the gate requires a spine test *at the level appropriate to
  the current phase*. At debate→gauntlet an `nl` (or `acceptance`) spine **passes**; it checks
  *existence at acceptable maturity for this phase*, **not** executability. The `concrete`/live-run
  demand is deferred to **G**.
- **Override:** bypass only via a logged override requiring a **≥50-char reason** written to
  `sessions/<id>.decisions.log`. **NB (code-confirmed):** the staleness gate's `--accept-tests-stale`
  is a *bare logged flag* (no reason required); only `IntentionalOverride` demands the ≥50-char
  reason. F′'s override is therefore **stricter than `--accept-tests-stale`** — spec a new
  `--accept-missing-spine` + `--spine-override-reason '<≥50 chars>'` mirroring the `IntentionalOverride`
  reason check, not the bare stale flag. **SEC-3: the ≥50-char floor counts non-whitespace characters
  and rejects all-whitespace / zero-width-only reasons** — a bare mechanical length check is gameable.
- **Placement (REVISED post-gauntlet — supersedes R2 §12.9; SEC-1):** a skill-side pre-check is a
  **prompt-enforced honor system** — it cannot mechanically gate an out-of-process Fizzy MCP call (an
  agent can call `pipeline_advance` directly), so it is **not** the non-bypassable layer. The
  **MECHANICAL, non-bypassable gate is Fizzy-side**: `pipeline_advance` into the gauntlet lane
  **refuses unless F′ evidence is attached**, and Fizzy **calls this skill's F′ checker** — exposed as
  an executable contract (`uv run gauntlet-check` / an MCP tool) so Fizzy **never reimplements** the
  parser (closes the cross-repo drift risk, DD-7/ARCH-628bc154). The skill-side pre-check and
  `enforce_pipeline_card_gate` (standalone) are **fail-fast advisories** that catch the common path
  early. **True non-bypassability REQUIRES the coordinated Fizzy spec — now a HARD DEPENDENCY, not an
  optional "layer 3."** This slice **DEFINES the F′ contract** (check signature + evidence shape) that
  Fizzy enforces; INV-003 is reframed accordingly (§6 head note).
- **Parses `tmr-registry.json`, not embedded markdown (REVISED post-gauntlet; DD-1, resolves §12.3):**
  F′ reads each test's record from the structured **`tmr-registry.json`** (§4.2) — `user_story`,
  `spine`, `maturity` — plus the roadmap manifest's canonical US IDs. Parsing a pure structured file
  removes the LLM-authored-YAML-in-markdown failure class (7 adversaries). Each `spine:true` record has
  exactly one **scalar** `user_story`; the markdown `[spine]` tag is a display aid only. Acceptable
  maturity at debate→gauntlet = `nl | acceptance | concrete` (`nl` passes; `concrete` + `run_evidence`
  is Phase-8/G, not F′).
- **Stale-tests precede F′; `--accept-tests-stale` does NOT bypass F′** (separate override).
- **Dependency:** depends on **A** — the TMR `spine:` / `maturity` / US-reference fields must exist
  to key on. The F′ parse couples the **roadmap-manifest US enumeration** ↔ **`tests-pseudo.md`
  spine tags**; that format coupling is called out as an open question (§12).
- **Two gates, two phases, one concept:** F′ is the *debate-time, document-only* gate (coverage
  declared + REAL-DATA-or-justified). The *live-run* gate (the declared spine test actually RUN
  green against live/dev) is **G** at the Phase-8 / fizzy-sweep handoff.

---

## 7. Decision provenance journal (J)
<!-- Addresses US-9, US-10 -->
**Blast zone:** new append-only writer; session detail (live) → `.architecture/tests/registry.journal.jsonl`
(on close, fizzy-side persistence). **Hard prerequisite: structured guardrail output (K, §5.1).**

A **single append-only journal** over **any tracked classification decision** — one record per
change to a tracked field, generalized over `subject_type ∈ {test, node}` (one record shape; see
keystone Piece 3). Indexed by (`subject_type`, `subject_id`); carries `session`. Append-only suits
cheap meta-analysis queries + safe concurrent multi-agent writes. **Evolution is NOT stored inline
on the TMR** — it lives only in this journal (schema decision 2).

### 7.1 Test-maturity journey (`subject_type: test`)
<!-- Addresses US-9 -->
- Each user story's test journey: every test tied to a US, its maturity moves
  (`nl→acceptance→concrete`), `data_strategy` changes (`MOCK→REAL-DATA`), spine designation —
  tagged with the **driver** (`debate_round` / `guardrail` TCOV/TRACE / `human_correction` /
  `promotion`).
- The ledger is **derived from accepted STATE CHANGES (R2: codex)** — guardrail findings are **one**
  driver, not the only one. Valid drivers: `guardrail`, `debate_round`, `human_correction`,
  `promotion`, `depth_triage`, `reclassification`, `close_attestation`, Phase-8 `run_evidence`. A
  `created` / promotion / `binding_status` / `run_evidence` change journals even with no guardrail
  finding behind it. Example chain: `TCOV-r2-7a3f` (finding) → orchestrator accepts → TMR
  `data_strategy` MOCK→REAL-DATA → transition recorded with `driver=guardrail:TCOV-r2-7a3f`.
- **Append-only invariant:** two successive field changes on one test produce two records; the
  first is never rewritten. A per-US query replays the journey in order.

### 7.2 Altitude-triage provenance (`subject_type: node`)
<!-- Addresses US-10 -->
- Records the life of a node's altitude: `created` @ depth-triage (initial altitude + blast-radius
  rationale) → `altitude` reclassifications (driver `reclassification` / `gauntlet_concern` /
  `human_correction`) → close-time **`altitude_fit` ∈ {right, too_high, too_low}** (driver
  `close_attestation`).
- **Queries this unlocks** (over `field: altitude`/`altitude_fit`): *altitude distribution*
  (histogram of altitudes identified); *subsystem triage precision* (`count(first==subsystem AND
  last==subsystem AND altitude_fit==right) ÷ count(first==subsystem)`); *full calibration* (3×3
  initial×final confusion matrix).
- **Why `altitude_fit` is required, not just stability:** reclassification only catches altitudes
  someone actively fixed; a silently-wrong altitude nobody changed looks "stable" and would falsely
  count as accurate. The close attestation corrects the over-count.
- **Split:** the skill's Phase-7 depth-triage step (`07-execution.md`) contributes the initial
  altitude + rationale. **The node-altitude journaling + close `altitude_fit` are fizzy-side**
  (emit at the existing change-detection hook `pipeline.py:6263`, where the change is detected and
  currently discarded; `altitude_fit` is new). The skill consumes/queries it for meta-analysis.

---

## 8. Phase-8 pseudo→real promotion + version fence (G)
<!-- Addresses US-11, US-12 -->
**Blast zone:** `phases/08-implementation.md`, `phases/07-execution.md`.

### 8.1 Pseudo→real promotion pass (G) — US-11
<!-- Addresses US-11 -->
- Add an explicit promotion pass **before implementation closes**: each pseudo test that is
  REAL-DATA / critical-seam / happy-path-spine gets **written as a real executable test, RUN, and
  required green** against the correct verification tier (code → pytest; prompt/doc →
  `system-validation`; judgment → golden eval). **The skill RUNS the test itself and captures a typed
  execution receipt (SEC-4)** — `run_evidence{command, cwd, repo, commit, started_at, finished_at,
  result, env, artifact_uri, artifact_sha256, runner, verification_mode, live_or_induced}` — it **never
  trusts a hand-written `result: pass`**. For a **critical seam** the receipt must also evidence the
  named technique was **active** (the induced fault actually applied), and a **best-effort
  mock-detection lint** flags a REAL-DATA/critical-seam test that imports a mock/patch of the boundary
  it claims to exercise (flag, not hard-block — AST detection is heuristic).
- **Trust model (SEC-4/SEC-5, stated honestly):** this is a **local CLI where the developer is admin**
  — files, `created_at`, and registry entries are all editable. The gate **raises the forgery bar**
  (skill-run + typed receipt + mock lint) and **produces auditable evidence**, but does **not** claim
  cryptographic non-forgeability it cannot deliver; **Fizzy is the terminal auditor/enforcer** of that
  evidence (SEC-1). YAML is loaded with `yaml.safe_load`, anchors/aliases rejected, and run artifacts
  redacted before commit (SEC-5).
- A pseudo test **never promoted-and-run = failing.** A declared-but-never-run REAL-DATA
  critical-seam test counts as **failing**, not passing.
- Phase 7: a **spine / critical-seam** test **cannot** be assigned a `spike` **test_strategy** nor an
  **exempt `verification_mode`** (`artifact-sync` / `static-check` / `manual-ux`). (R2: codex — `spike`
  is a *test_strategy*, a different axis from `verification_mode`; don't conflate them.)
- Enforcement at sweep is **fizzy's** job; the skill **drives** the promotion and passes
  `run_evidence`. Document the handoff so a **blocked first-fill HALTS downstream** instead of being
  parked.

### 8.2 Version fence (US-12)
<!-- Addresses US-12 -->
- A version marker **`liveness_contract_version` (e.g. `tmr.v1`)** gates the new requirements.
  Sessions started **before** it keep their original rules (no retroactive failure of in-flight
  sessions such as `validation-leg-process`).
- **`ContractVersionResolver` (REVISED post-gauntlet; SEC-2, closes §12.4).** A single resolver with a
  defined read order decides fence status, anchored to the **immutable session `created_at` vs a fixed
  `fence_cutover_ts`** — NOT the editable marker alone. **A missing marker on a session created ≥
  `fence_cutover_ts` is POST-fence (fail-closed), not legacy** — so deleting `liveness_contract_version`
  from `session-state.json` cannot downgrade a new session to skip F′ (the downgrade attack). The marker
  is an *assertion* that must be ≥ the derived value; a session is legacy **only** if `created_at <
  fence_cutover_ts`. (Residual: a local admin can also edit `created_at` — a higher bar, accepted under
  the §8.1 trust model.)
- A **post-fence** session missing a spine test → the new F′ requirement applies (`exit 2`).
- On the fizzy side this corresponds to a `verification_contract_version` bump (or altitude gating)
  so legacy cards aren't retroactively failed. TMR fields are optional + warn-first, promoted to
  required behind the fence (schema decision 5).

---

## 9. Verification tiers (cross-cutting)
<!-- Addresses US-14 -->
This skill is **part code, part prompts** — so each deliverable declares a verification tier, and
the tier determines the `verification_mode`:

| Tier | What it covers | How it's verified |
|---|---|---|
| **code** | executable Python: F′ gate, provenance journal writer, validators, emission, the lints | **REAL-DATA pytest** against real artifact fixtures (real roadmap-manifest + tests-pseudo fixtures). A code seam may NOT be `spike`/exempt. |
| **prompt/doc** | phase-doc / guardrail-prompt behavior (authoring rules, TRACE/TCOV persona changes, Getting Started) | **STATIC doc-lint** + **`system-validation`** live (scoped) skill run + **fault-induced fixtures** (broken specs the gate must catch). A phase-doc rule's behavior is only provable by an LLM following it. |
| **LLM-judgment** | guardrail *catch quality* (does TRACE find the ORPHANED US? does TCOV catch the falsifiable MOCK?) | **golden-case eval** against a planted-defect corpus (REAL-DATA + PROPERTY). |

- Every task in the execution plan declares its tier; a **code-seam** task assigned an **exempt
  mode** is **flagged**. (Code-confirmed: fizzy `EXEMPT_MODES = {artifact-sync, static-check,
  manual-ux}`; `AUTOMATED_MODES` = the five `automated-*`/`test-producer` modes; `system-validation`
  is its *own* category — neither automated nor exempt — so it is the correct mode for the prompt/doc
  tier's live close, not a relabeled E2E unit run.)
- **No `golden-eval` verification_mode exists (R1: codex).** The LLM-judgment tier's
  `verification_mode` is **`system-validation`** (its own canonical category — confirmed not in
  `AUTOMATED_MODES` nor `EXEMPT_MODES`) with a **golden-case corpus as the *oracle***. Golden-eval is
  a corpus/oracle, not a new enum member. (TC-14.0 fixed to assert canonical modes only.)
- The **`system-validation` close** exercises the prompt/doc tier (the live-run verification
  mechanism for prompt/doc deliverables already exists in this repo via the validation-leg work).

---

## 10. Glossary / ADR / document-types (H)
<!-- Addresses US-13 -->
**Blast zone:** `CONTEXT.md`, `reference/document-types.md`, new ADR.

- **`CONTEXT.md`:** add entries for **happy-path spine**, **TMR**, **maturity ladder**, and
  **liveness**. Resolve the **"Architecture Spine" collision**: "Architecture Spine" already means
  the execution-plan file-structure list (`07-execution.md`, `08-implementation.md`, glossary). The
  new test concept is the **"happy-path spine" (TC-0)** — always written with the `happy-path`
  qualifier, **never bare "spine."**
- **`reference/document-types.md`:** update the `tests-pseudo.md` row format to the extended TMR row.
- **New ADR:** record the test-ladder / TMR / liveness-gate decision **and** the two-spec
  cross-project scope split.

---

## 11. Information Flows

| Flow | Source | Destination | Mechanism | Notes |
|---|---|---|---|---|
| TMR emission → validation | skill (`tests-pseudo.md` emit) | fizzy P0 validator | shared enum constants (field-for-field) | mismatch must be a **named rejection**, never silent |
| Round diff → guardrail subagents | main loop | 5 parallel subagents | self-contained dispatch (prompt + file pointers + diff) | subagents start fresh; diff = "what changed" |
| Guardrail findings → aggregation | 5 subagents | main loop | structured Piece-2 returns (test/US-keyed) | only a **TMR-changing** finding lacking `target.{user_story,test_id}` is rejected; spec/contract-scoped findings carry `target.spec_section`/`target.contract` and are accepted (journaled only if they change a TMR/node field) — per §5.1 (CB-3) |
| Disposition → provenance | main loop | append-only journal | Piece-3 transition citing `finding_id` driver | append-only; inline evolution forbidden |
| Roadmap US set ↔ TMR records | roadmap manifest + `tmr-registry.json` | F′ checker (skill, called by Fizzy gate) | deterministic parse via shared `TmrParser` | DD-1: registry, not embedded markdown; Fizzy enforces (SEC-1) |
| Promotion run-evidence | Phase-8 promotion pass | fizzy sweep | `run_evidence` block (extends fizzy v3) | sweep enforces REAL-DATA→live run |

*(No external third-party APIs are introduced by this spec — §2.7's SDK-verification step is N/A;
the only cross-system contract is the in-repo/cross-repo TMR schema, handled schema-first in §3.)*

---

## 12. Open questions & assumptions (debate / lookup targets)

Carried from requirements `unknowns`; to be resolved by lookup where cheaper than a debate round
(seeded into `lookup-log.md`), else by Round-N debate or Jason:

1. **Per-guardrail structured-finding schema (K output)** — refine the Piece-2 taxonomy per
   guardrail beyond the keystone's examples. *(debate — R2 design.)*
2. **Parallel-subagent dispatch replacing the inline/critique flow in `03-debate.md`** — the exact
   orchestration spec (how subagents are launched, how returns aggregate, failure handling).
   *(debate — R2; lookup the current `03-debate.md` invocation contract.)*
3. **F′ deterministic parse** — ~~the roadmap-manifest US enumeration ↔ tests-pseudo spine-tag
   coupling~~ **RESOLVED R2 (codex):** F′ parses each test's structured `TMR:` block (§4.2) for
   `user_story`/`spine`/`maturity`, cross-referencing the roadmap manifest's canonical US IDs;
   markdown `[spine]` is display-only.
4. **Version-fence mechanism** — **RESOLVED post-gauntlet (SEC-2):** `ContractVersionResolver` keyed on
   immutable `created_at` vs `fence_cutover_ts`; a missing marker on a post-cutover session = post-fence
   (fail-closed), defeating the marker-deletion downgrade. See §8.2. *(fizzy mirrors via
   `verification_contract_version`.)*
5. **Maturity-aware gate's exact phase → acceptable-maturity mapping** — confirm `nl`/`acceptance`
   pass at debate→gauntlet; `concrete` at Phase-8. *(largely resolved; confirm in R1.)*
6. **Golden-eval corpus** — where planted-defect fixtures live and how many. *(debate / Jason.)*
7. **Coordination handshake with the fizzy spec** — which repo lands the schema constants first
   (§3.2). *(Jason / cross-session decision.)*
8. **Concept-accessor façade/binding ownership gap** — unassigned in all three source reports;
   out of skill scope but **flagged** (target-repo + its CI). *(Jason — assign.)*
9. **F′ placement under the pipeline-card fence** — **REVISED post-gauntlet (SEC-1, supersedes R2):**
   skill-side pre-check is a **fail-fast advisory** (prompt-enforced, not mechanical); the
   **non-bypassable gate is Fizzy-side** (calls the skill's F′ checker at gauntlet-entry) and is now a
   **hard dependency**, not "layer 3." See §6.
10. **Override → provenance-journal coupling (R1: gemini, deferred).** An F′ override is canonically
    audited in `sessions/<id>.decisions.log`. Should it *also* emit a Piece-3 journal record? The
    journal is keyed to *field changes* over `{test, node}`; a gate-bypass is a session-level event,
    not a TMR/node field change, so it doesn't fit the current schema cleanly. **RESOLVED R2 (codex
    over gemini):** keep overrides in `sessions/<id>.decisions.log`; the journal stays `{test, node}`
    field-changes only (NO `subject_type:session`/`gate` scope-creep). If an override later changes a
    TMR, *that* change is journaled with a `driver` ref to the decision-log entry — preserving the
    audit link without diluting the journal's purpose.
11. **Test-ladder → `tmr-registry.json` migration (CB-6 + DD-1, gauntlet).** Post-DD-1, F′ parses the registry,
    not embedded markdown. The dogfood fixture needs a `tmr-registry.json` with a record (incl. `spine:true`) for
    all 15 `[spine]` tests (only TC-8.0 has a full block today), plus the prose-view generator for `tests-pseudo.md`.
    Until then F′ would not pass this draft. *(implementation fixture + emission task.)*
12. **Remaining ~20 gauntlet accepts** (RC-1/2/3 journal-concurrency + snapshots, FM-1..5, SCA-1/2, DD-2..9,
    US-1..8) — synthesized in `gauntlet-concerns-2026-06-15.md`; fold into the spec or carry as an
    execution-planning checklist next pass. *(Jason-scoped: CB + trust-model first; these next.)*
13. **Authoring UX for `tmr-registry.json` (DD-1 follow-on).** Does the human author the registry directly (raw
    JSON, worse UX) or author prose in `tests-pseudo.md` that an emission step compiles into the registry (better
    UX, needs a generator + round-trip)? Decide before the §2 bootstrap is finalized. *(design — next pass.)*

---

## 13. User-story coverage map

| US | Story (abbrev) | Spec section(s) | Spine test |
|----|----------------|-----------------|------------|
| US-1 | Shared TMR field set + enums (keystone) | §3 | TC-1.0 |
| US-2 | One happy-path spine/US; failures anchored | §4.1, §4.2 | TC-2.0 |
| US-3 | MOCK names live/induced technique or promote | §4.3 | TC-3.0 |
| US-4 | Maturity ladder nl→acceptance→concrete | §4.4 | TC-4.0 |
| US-5 | Parallel-subagent structured guardrails | §5.1 | TC-5.0 |
| US-6 | TRACE flags US-without-spine as ORPHANED | §5.2 | TC-6.0 |
| US-7 | TCOV promoter + ingest-all + missing_liveness_test | §5.3 | TC-7.0 |
| US-8 | Deterministic F′ gauntlet-entry gate | §6 | TC-8.0 |
| US-9 | Test-maturity provenance journal | §7.1 | TC-9.0 |
| US-10 | Altitude-triage provenance + altitude_fit | §7.2 | TC-10.0 |
| US-11 | Phase-8 pseudo→real promotion (RUN green) | §8.1 | TC-11.0 |
| US-12 | Version fence (no retroactive failure) | §8.2 | TC-12.0 |
| US-13 | Glossary / ADR / document-types | §10 | TC-13.0 |
| US-14 | Verification tiers (cross-cutting) | §9 | TC-14.0 |
| US-15 | Getting Started / bootstrap | §2 | TC-15.0 |

All 15 user stories have a corresponding spec section and a happy-path spine test (`[spine]`) in
`tests-pseudo.md`. **Coverage caveat (CB-6):** F′ parses each spine test's structured `TMR:` block (§4.2), and the
draft `tests-pseudo.md` currently carries the full block only for the TC-8.0 exemplar — the other 14 spine tests
use `[spine]` prose markers. **F′ would therefore NOT pass this draft as-is**; emitting a `TMR: {spine: true, …}`
block for every spine test is a tracked remediation (§12 open item 11).
