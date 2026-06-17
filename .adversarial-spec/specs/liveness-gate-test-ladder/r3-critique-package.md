# R3 CRITIQUE PACKAGE — Liveness Gate + Test Ladder (adversarial-spec skill slice)

> **ROUND 3 FOCUS = REFINEMENT / CONVERGENCE.** Two rounds done (R1 requirements, R2 architecture).
> This is the polish + final-consistency round. Check ONLY:
> 1. **Cross-section consistency** — any remaining contradiction across §0–§13 (esp. the R2 additions:
>    critical_seam/criticality_source in §3.1/§3.3, structured TMR block §4.2, F′ skill-side §6,
>    fail-closed/conflict §5.1, journal-from-state-changes §7, override→decisions.log §12.10).
> 2. **TMR fidelity** — does spec §3 + the TC-8.0 exemplar `TMR:` block match the canonical keystone
>    (Appendix B, now incl. critical_seam + criticality_source) field-for-field?
> 3. **Edge cases / final gaps** — anything that would break at implementation (the 3 deferred TCOV
>    tests: ORCH fail-closed on subagent death, conflict-state resolution, full TMR-block conversion).
> 4. **US completeness** — all 15 user stories still covered (§13 map)?
>
> **If the spec is sound, respond [AGREE].** Do NOT re-open R1/R2-resolved items (see the v2+v3
> changelogs at the top of PART 1). Do NOT relitigate locked decisions (happy-path-spine term;
> no-dogfood+version-fence; two coordinated specs; no new adversaries; subagent guardrails→journal;
> override stays in decisions.log). Surface only NEW, concrete, implementation-blocking issues.

---

# PART 1 — SPEC UNDER CRITIQUE (spec-draft-v3.md)

# Spec: Liveness Gate + Architecture-Linked Test Ladder (adversarial-spec slice)

> Session: adv-spec-202606151042-liveness-gate-test-ladder | Card 5715 | Altitude: **system**
> Depth: technical/full | Draft: **v3** (post-R2) | Status: R2 incorporated (architecture); R3 (refinement) next
> R1 changelog: F′ exactly-one happy-path spine; canonical `verification_mode`; MOCK-rule fix; prose/token rule.
> R2 changelog: `critical_seam`+`criticality_source` promoted to REAL keystone fields (added to canonical §1/§2);
> structured `TMR:` block required per test (F′ parses it, not prose); F′ **skill-side pre-check is PRIMARY**
> (gates the Fizzy path, not just standalone debate.py); guardrail subagents **fail-closed** (synthetic ORCH
> finding) + **conflict** state; only TMR-changing findings need test join keys; journal derives from accepted
> state changes; override→journal resolved (decisions.log + driver-ref, no `subject_type:session`); maturity
> threshold reconciled (`nl` passes at debate→gauntlet); `spike` is a *test_strategy*, not a verification_mode.
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
- Make it **impossible to reach the gauntlet** without a phase-appropriate-maturity **happy-path
  spine** test for every user story.
- Force every `MOCK` to **name the live/induced technique** or be promoted to `REAL-DATA`.
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
*persists and enforces* the same fields at sweep. The **TMR field set is the keystone** — agreed
schema-first before either side builds.

| Codebase | Owns | In this spec? |
|---|---|---|
| **adversarial-spec (this)** | authoring (A) + strict MOCK (B) + TRACE/TCOV folds (C, D) + F′ debate gate + provenance journal authorship (J) + structured-subagent guardrails (K) + Phase-8 promotion driver (G) + glossary/ADR (H) | ✅ |
| fizzy_pipeline_mcp | TMR persistence, `VALID_DATA_STRATEGIES`/`VALID_LIVENESS_TECHNIQUES`/`maturity` constants, run-evidence storage, sweep-time enforcement, node-altitude journaling | ❌ separate coordinated spec |
| prediction-prime | concept-accessor façade + bindings + fail-closed lint; live-fill (Track A); fault-injection infra | ❌ flagged unassigned; out of skill scope |

**Reality check (verified against fizzy code 2026-06-15):** there is **no "M-4b test-lineage
gate"** to extend — it is a phantom both prediction-prime source plans inherited. fizzy's NASA
V-model altitude system *is* built (`VALID_ALTITUDES`, `ALTITUDE_OBLIGATIONS`,
`mark_system_validation_complete`, `VALID_VERIFICATION_MODES`/`MODE_SCOPE_MATRIX`). The new work
attaches `data_strategy` + liveness as two **missing axes** on that model, and the spine/REAL-DATA
obligation as a new **altitude-scaled right-arm obligation** — not a parallel state machine.

### 1.1 Non-goals
- fizzy-side persistence/enforcement (separate coordinated spec).
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
2. In `tests-pseudo.md`, author **exactly one `[spine]` (TC-0) test per user story** with named
   steps `S1…Sn`; anchor each failure test to a spine step via `spine_step_ref`.
3. Run the **authoring lint** — it confirms one happy-path spine per US and that every failure
   test carries a valid `spine_step_ref`.
4. Enter **debate**; iterate. (The F′ gate is *advisory* here — it warns about uncovered US but
   does not block, so early debate proceeds while tests mature.)
5. **Attempt gauntlet entry** and observe the F′ gate: full spine coverage → pass; a US with no
   spine test → `exit 2` naming the uncovered US.

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
3. **debate→gauntlet (F′):** every US has exactly one `spine:true` test at ≥`acceptance` → **passes**
   (F′ does NOT demand `concrete`/live here).
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
1. **TMR** — the per-test record (`session · user_story · test_id`).
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

### 4.2 Structured `TMR:` block in the `tests-pseudo.md` row format (A)
Each test carries a **structured `TMR:` block** (YAML) whose **keys match the canonical keystone
field-for-field** (R2: codex — v2's prose rows couldn't be robustly parsed by F′): `test_id`,
`user_story`, `maturity`, `spine`/`spine_steps`/`spine_step_ref`, `data_strategy`, `live_or_induced`,
`why_impossible_to_reproduce_live`, `verification_mode`, `verification_scope`, `altitude`,
`tested_by`, `critical_seam`/`criticality_source`, `architecture_link`, `accessors`,
`binding_status`, `run_evidence`. Markdown headings, prose "Spine steps," and the `[spine]` tag are
**display aids only** — the `TMR:` block is what F′ and the guardrails parse.

`verification_tier` (§9) is **feeder-only planning metadata** — it is NOT emitted to fizzy as a TMR
field. The `tests-pseudo.md` row remains a **feeder/view** of the canonical TMR (§3) — never the
system of record. (See tests-pseudo.md TC-8.0 for the exemplar block.)

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
stuck at `nl` across rounds is itself a flag. A TMR at `nl` whose elements all resolve to **named
concept-accessors** → `PROMOTE nl→acceptance`; an element that maps to **no named accessor across N
rounds** → stays `nl` and is flagged `BLOCK` (concept undesigned — surfaces the real gap).

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

The **teeth** that make happy-path-spine coverage non-bypassable:
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
  reason check, not the bare stale flag.
- **Placement (R2: both, resolved §12.9) — defense-in-depth, three layers:** the **PRIMARY**
  enforcement is a **skill-side pre-check immediately before the Fizzy gauntlet-entry transition**
  (`pipeline_advance` into the gauntlet lane / gauntlet dispatch) — because this session dispatches
  via Fizzy tools, not standalone `debate.py`, so `enforce_pipeline_card_gate` alone would be
  bypassed. `enforce_pipeline_card_gate` remains the **standalone fallback**; **fizzy also enforces**
  at sweep.
- **Parses the structured `TMR:` block, not prose (R2: codex, resolves §12.3):** F′ reads each
  test's `TMR:` block (§4.2) — `user_story`, `spine`, `maturity` — plus the roadmap manifest's
  canonical US IDs. Each `spine:true` TMR has exactly one **scalar** `user_story`; the markdown
  `[spine]` tag is a display aid only. Acceptable maturity at debate→gauntlet = `nl | acceptance |
  concrete` (`nl` passes; `concrete` + `run_evidence` is Phase-8/G, not F′).
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
  `system-validation`; judgment → golden eval). It records `run_evidence{result, env, commit,
  artifact}`.
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
| Guardrail findings → aggregation | 5 subagents | main loop | structured Piece-2 returns (test/US-keyed) | finding without join key → rejected |
| Disposition → provenance | main loop | append-only journal | Piece-3 transition citing `finding_id` driver | append-only; inline evolution forbidden |
| Roadmap US set ↔ spine tags | roadmap manifest + `tests-pseudo.md` | F′ gate (`debate.py`) | deterministic parse | format coupling = open question (§12) |
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
4. **Version-fence mechanism** — skill marker shape vs fizzy `verification_contract_version` vs
   altitude gating; where the marker is stored and read. *(debate — coordinate with fizzy spec.)*
5. **Maturity-aware gate's exact phase → acceptable-maturity mapping** — confirm `nl`/`acceptance`
   pass at debate→gauntlet; `concrete` at Phase-8. *(largely resolved; confirm in R1.)*
6. **Golden-eval corpus** — where planted-defect fixtures live and how many. *(debate / Jason.)*
7. **Coordination handshake with the fizzy spec** — which repo lands the schema constants first
   (§3.2). *(Jason / cross-session decision.)*
8. **Concept-accessor façade/binding ownership gap** — unassigned in all three source reports;
   out of skill scope but **flagged** (target-repo + its CI). *(Jason — assign.)*
9. **F′ placement under the pipeline-card fence** — **RESOLVED R2 (both critics):** skill-side
   pre-check before the Fizzy gauntlet-entry transition is **PRIMARY**; `enforce_pipeline_card_gate`
   is the standalone fallback; fizzy also enforces at sweep (defense-in-depth, 3 layers). See §6.
10. **Override → provenance-journal coupling (R1: gemini, deferred).** An F′ override is canonically
    audited in `sessions/<id>.decisions.log`. Should it *also* emit a Piece-3 journal record? The
    journal is keyed to *field changes* over `{test, node}`; a gate-bypass is a session-level event,
    not a TMR/node field change, so it doesn't fit the current schema cleanly. **RESOLVED R2 (codex
    over gemini):** keep overrides in `sessions/<id>.decisions.log`; the journal stays `{test, node}`
    field-changes only (NO `subject_type:session`/`gate` scope-creep). If an override later changes a
    TMR, *that* change is journaled with a `driver` ref to the decision-log entry — preserving the
    audit link without diluting the journal's purpose.

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

All 15 user stories have a corresponding spec section and a happy-path spine test in
`tests-pseudo.md`. No user story is uncovered (F′ would pass on this draft's coverage shape).

---

# APPENDIX A — tests-pseudo.md (current, synced to v3)

# tests-pseudo.md — Liveness Gate + Test Ladder

> Session: adv-spec-202606151042-liveness-gate-test-ladder | maturity stage: nl
> Canonical source of truth for tests. roadmap/manifest.json links here.
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
- given a TMR with every field set to a valid enum member (data_strategy, live_or_induced, maturity, spine, run_evidence.env)
- when the skill emits it and fizzy's validator runs
- then it is accepted AND a **semantic round-trip** holds: all required keys (`session`,`user_story`,`test_id`,`maturity`,`data_strategy`,`spine`,`run_evidence`) are preserved, the identity tuple `session·user_story·test_id` is unchanged, every enum member is recognized, and **no field is silently dropped**. (R1: codex — enum/field-presence alone is insufficient.)

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
- given a MOCK with `live_or_induced: null` whose `why_impossible_to_reproduce_live` denies every live/induced technique
- when the MOCK-falsification check runs
- then it is accepted as a justified MOCK — the ONLY case MOCK is allowed. (R1 fix: the spine is a *justified* MOCK, not one that names a technique.)

### TC-3.1: a MOCK that NAMES a technique (or a dev-forceable condition) is promoted  (branch @ S2)
**Data Strategy: REAL-DATA** (tier: LLM-judgment — golden case) — planted: a MOCK with `live_or_induced: tc-netem:partition`; sibling planted on ">100 positions for pagination" (forceable on a dev account, no technique named).
- given a MOCK whose `live_or_induced` names a technique from the enum, OR whose `why_impossible_to_reproduce_live` names a condition forceable on dev infra
- when the check (B/D) runs
- then it is REJECTED as a justified MOCK and the required action is "promote to REAL-DATA" — naming a technique is itself proof the behavior can be induced. (R1: codex CRITICAL — v1 TC-3.0 had this backwards.)

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

### TC-5.1: a guardrail finding with no test/US key is rejected  (branch @ S3)
**Data Strategy: REAL-DATA** (tier: code) — a malformed finding lacking the join key.
- given a guardrail return whose finding omits `target.{user_story,test_id}`
- when aggregation runs
- then the finding is rejected/flagged (can't be journaled without a key).

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

## US-7 — TCOV promoter + liveness (M3)

### TC-7.0: TCOV ingests standalone owner test files, not just the ledger  [spine]
**Data Strategy: REAL-DATA** (tier: code — pytest of the input collector) — a fixture with a standalone test file outside tests-pseudo; assert the file enters TCOV's input manifest. (R1: codex — input collection is *deterministic code*, not judgment; TCOV's judgment *quality* is the golden cases TC-6.0/7.1.)
- given an owner path with a standalone `*.test.*` file and a tests-pseudo ledger
- when TCOV runs
- then TCOV's input includes the standalone file (it would otherwise be invisible).

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

### TC-8.0: full spine coverage passes the gate  [spine]
**Data Strategy: REAL-DATA** (tier: code — pytest) — real fixture roadmap manifest + tests-pseudo, full coverage.
**Spine steps:** S1 load roadmap US set → S2 parse each test's structured `TMR:` block → S3 every US has exactly one `spine:true` TMR at acceptable maturity → S4 pass.
**Exemplar `TMR:` block** (the structured form spec §4.2 requires; F′ parses THIS, not the markdown / `[spine]` tag):
```yaml
TMR:
  test_id: TC-8.0
  user_story: US-8
  maturity: nl
  spine: true
  spine_steps: [S1, S2, S3, S4]
  spine_step_ref: null
  data_strategy: REAL-DATA
  live_or_induced: natural-wait
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
  run_evidence: {ts: null, result: null, commit: null, env: null, artifact: null}
```
- given a fixture roadmap (US-1..US-3) and a tests-pseudo where each US has exactly one `spine:true` TMR block at `nl` or `acceptance`
- when the **F′ skill-side pre-check** runs before the Fizzy gauntlet-entry transition (PRIMARY; `enforce_pipeline_card_gate` is the standalone-fallback path and runs the identical check)
- then the gate passes (exit 0). (R2: parses the structured TMR block; skill-side placement is primary.)

### TC-8.1: an uncovered user story → exit 2  (branch @ S3)
**Data Strategy: REAL-DATA** (tier: code — pytest) — fixture where US-3 has no spine test.
- given the same fixture but US-3 has no `spine:true` test
- when the gate runs for `gauntlet`
- then it exits 2 naming US-3; bypass only with `--accept-...` + a logged ≥50-char reason (written to decisions.log).

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
**Data Strategy: REAL-DATA** (tier: code — pytest) — fixture where US-2 has TWO `spine:true` tests.
- given a fixture roadmap (US-1..US-3) and a tests-pseudo where US-2 has two `spine:true` tests
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

### TC-11.0: a critical-seam test is promoted, RUN, and required green  [spine]
**Data Strategy: REAL-DATA** (tier: code — pytest of the promotion-pass logic) — a fixture critical-seam test.
**Spine steps:** S1 select critical-seam/spine pseudo test → S2 write real test → S3 RUN → S4 require green.
- given a critical-seam test at `acceptance` with `run_evidence: null`
- when the Phase-8 promotion pass runs
- then it produces a real test, runs it at the correct tier, and records `run_evidence{result:pass}`.

### TC-11.1: a declared-but-never-run REAL-DATA test counts as failing  (branch @ S3)
**Data Strategy: REAL-DATA** (tier: code — pytest) — a REAL-DATA test with `run_evidence: null` at close.
- given a REAL-DATA critical-seam test never promoted+run
- when implementation close is evaluated
- then it is treated as failing (not passing); spine/critical-seam may not be `spike`/exempt.

---

## US-12 — Version-fence (M6)

### TC-12.0: a pre-fence session keeps its original rules  [spine]
**Data Strategy: REAL-DATA** (tier: code — pytest) — a session started before the version marker.
- given a session whose version marker predates the new gates
- when the gates evaluate it
- then the new requirements do not apply (no retroactive failure).

### TC-12.1: a post-fence session is held to the new gates  (branch)
**Data Strategy: REAL-DATA** (tier: code — pytest) — a session started after the marker.
- given a post-fence session missing a spine test
- when the gate runs
- then the new F′ requirement applies (exit 2).

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


---

# APPENDIX B — Canonical TMR keystone (now incl. critical_seam + criticality_source; verify field-for-field)

<!-- CANONICAL SOURCE OF TRUTH — cross-project contract. Do NOT copy into either repo. -->
> **Canonical TMR / guardrail-finding / provenance-journal contract.** Single source of truth (US-1).
> Referenced (never duplicated) by both coordinated specs:
> - adversarial-spec skill spec — Fizzy card 5715 (adversarial-spec board)
> - fizzy-pipeline-mcp spec — separate coordinated session
> Both repos build to THIS file field-for-field; a mismatch must be caught by fizzy P0 validation, not
> silently. If you find a copy in either repo, delete it — divergence of this contract is the exact
> failure this work exists to prevent.

---

# Schema: Test Maturity Record + Guardrail Findings + Provenance Ledger (keystone contract)

> Date: 2026-06-15 | Status: draft for the adversarial-spec session (keystone both specs depend on)
> Companion to `liveness-gate-and-test-ladder.md`. This is the **one cohesive data model** that
> changes A, C, D, F′, G, J, K all key on — and the **field-for-field contract** with
> `fizzy-pipeline-mcp` (which persists/enforces what this skill authors/emits).

Three coupled pieces:
1. **TMR** — the per-test record (what a test *is*). Keyed `session · user_story · test_id`.
2. **Guardrail finding** — what each parallel-subagent guardrail returns (what's *wrong/changed*),
   keyed to `user_story`/`test_id`.
3. **Decision provenance journal** — append-only record of how any tracked classification *evolved*,
   over `subject_type ∈ {test, node}` (test-maturity journey **and** altitude-triage). Built by
   aggregating #2 for tests; fed by depth-triage + close attestation for nodes. Keyed
   `subject_type · subject_id`.

---

## 0. Lifecycle & system of record

| Phase | Working home (system of record while live) | Form |
|---|---|---|
| requirements/roadmap | session detail + `tests-pseudo.md` (the human-authored **feeder/view**) | `nl` TMRs |
| debate | session detail (TMRs mutate; guardrail findings + transitions accumulate per round) | `nl`→`acceptance` |
| execution/implementation | fizzy task cards (TMR fields validated/persisted) + `tests-spec.md` | `acceptance`→`concrete` |
| close | **`.architecture/tests/registry.json`** — durable, linked to architecture nodes (fizzy writes on completion) | promoted TMRs + ledger |

`tests-pseudo.md` / `tests-spec.md` are **feeders/views**, never the system of record. Linkage to
`.architecture` (not to the spec) is what makes the suite outlive the spec and re-run when a linked
node changes.

---

## 1. Shared enums (the fizzy contract)

Field names + enum members below MUST match across this skill's emission and fizzy's P0 schema
constants. **Source-of-truth column** says who owns the canonical list.

| Enum | Members | SoT |
|---|---|---|
| `maturity` | `nl` → `acceptance` → `concrete` | **NEW** — define here; fizzy P0 adds (`functional` is a design-doc alias for `concrete`; canonical is `concrete`) |
| `data_strategy` | `REAL-DATA`, `REAL-DATA + PROPERTY`, `SYNTHETIC`, `MOCK`, `MOCK-EXTERNAL`, `FRONTEND`, `STATIC` | skill (CONTEXT.md / `02-roadmap.md §9a`); **fizzy P0 adds `VALID_DATA_STRATEGIES`** |
| `live_or_induced` | `natural-wait`, `toxiproxy:corrupt`, `toxiproxy:drop`, `tc-netem:latency`, `tc-netem:partition`, `external-kill`, `null` | **NEW** — define here; **fizzy P0 adds `VALID_LIVENESS_TECHNIQUES`** |
| `verification_mode` | `automated-unit`, `automated-integration`, `automated-contract`, `automated-component`, `test-producer`, `artifact-sync`, `static-check`, `manual-ux`, `system-validation` | **fizzy** (`pipeline.py:167` `VALID_VERIFICATION_MODES`) — reference, do not redefine |
| `verification_scope` | `targeted`, `full-suite`, `static`, `manual`, `end-to-end` | **fizzy** (`pipeline.py:182`) |
| `altitude` | `component`, `subsystem`, `system` | **fizzy** (`pipeline.py:224` `VALID_ALTITUDES`) |
| `tested_by` | `llm`, `user`, `both` (default `llm`) | **fizzy** (`pipeline.py:206` `VALID_TESTED_BY`) |
| `run_evidence.env` | `live`, `dev`, `ci` | **NEW** — extends fizzy's existing v3 evidence block (`test_task` @ `pipeline.py:3858`) |
| `run_evidence.result` | `pass`, `fail` | **fizzy** (`VALID_BASELINE_RESULTS`) |
| `critical_seam` | `true`, `false`, `null` (JSON null) | **NEW (R2, adv-spec card 5715)** — define here; fizzy P0 adds. `null` + `criticality_source:unknown` = `criticality_unknown`, treated as critical |
| `criticality_source` | `explicit`, `architecture_link`, `unknown` | **NEW (R2, adv-spec card 5715)** — companion to `critical_seam`; `architecture_link` is an *input* to classification, not a parallel contract; fizzy P0 adds |

**Orthogonality (load-bearing):** `verification_mode` answers *unit vs integration*; `data_strategy`
answers *real vs faked*; `altitude` answers *how deep / how much rigor*. They are independent axes —
a critical-seam task needs all three set. `data_strategy` is the genuinely missing axis fizzy lacks.

---

## 2. Piece 1 — Test Maturity Record (TMR)

```jsonc
{
  "test_id": "TC-arm-fill-spine",
  "title": "Trader arms a pure pair; both legs fill; arb captured",
  "user_story": "US-2",                  // journey == user story (Q4). string | string[]: a spine is 1:1 with its US;
                                         // shared utility tests may carry a list e.g. ["US-2","US-5"] (N:1) (Q1).
  "maturity": "nl",                      // nl | acceptance | concrete

  // ── the spine model ──
  "spine": true,                         // is this the happy-path spine (TC-0) for US-2?
  "spine_steps": ["S1","S2","S3","S4","S5","S6"], // named steps (spine only); failures branch off these
  "spine_step_ref": null,                // failure tests set this (e.g. "S4"); spine itself = null

  // ── data + liveness axes ──
  "data_strategy": "REAL-DATA",
  "live_or_induced": "natural-wait",     // technique that makes it live; null only if truly impossible
  "why_impossible_to_reproduce_live": null, // REQUIRED prose iff data_strategy is MOCK* AND live_or_induced==null

  // ── verification axes (fizzy-owned enums) ──
  "verification_mode": "automated-integration",
  "verification_scope": "end-to-end",
  "altitude": "system",                  // scales the live/spine obligation
  "tested_by": "both",                   // llm | user | both — who can execute it

  // ── architecture linkage + façade ──
  "architecture_link": ["component:gateway","contract:bookCache","flow:arm-to-fill"], // must resolve under .architecture/; required by `acceptance`, may lag/empty at `nl` (Q3)
  "accessors": ["arm_algo","legs_of","algo_id","leg_algo_id","fill_of"], // concept-accessor names (façade; binding is target-repo)
  "binding_status": "unbound",           // unbound | bound  (acceptance→concrete promotion key)

  // ── criticality (R2, adv-spec card 5715) — drives the liveness obligation (missing_liveness_test, Phase-8) ──
  "critical_seam": false,                // true | false | null. null + criticality_source:unknown = criticality_unknown → treated as critical for system-altitude happy-paths until resolved
  "criticality_source": "explicit",      // explicit | architecture_link | unknown. architecture_link is an INPUT to classification, not a parallel contract; if explicit and derived disagree → fail closed as critical + blocking finding

  // ── execution evidence (extends fizzy v3 evidence block) ──
  "run_evidence": { "ts": null, "result": null, "commit": null, "env": null, "artifact": null },
  // null until executed; a REAL-DATA spine needs result=="pass" with env in {live,dev} + artifact
  // (e.g. a real fill id or a /books snapshot path).

  // ── provenance ──
  "source_spec": "take-take-chunk-execution-state-machine" // provenance, NOT system of record
  // Evolution is NOT stored inline — it lives in Piece 3, a separate append-only journal keyed by test_id (Q2).
}
```

**Fail-closed invariant (from design §3):** an `accessor` that is unbound or no-op MUST fail, never
skip/return a plausible value. A silently no-op binding rebuilds the exact fake-socket failure this
whole effort kills. The binding layer + lint live **target-repo / its CI** (unassigned in all source
reports — flag); the skill only authors the accessor *names*.

---

## 3. Piece 2 — Structured guardrail finding (parallel-subagent return)

Each of the five guardrails runs as its own subagent (decision K) and returns a list of these.
**Keyed to the data model** (`user_story` / `test_id`) — that keying is what lets findings drive the
provenance ledger.

```jsonc
{
  "guardrail": "TCOV",                    // CONS | SCOPE | TRACE | CANON | TCOV
  "round": 2,                             // debate round
  "finding_id": "TCOV-r2-7a3f",          // stable
  "category": "data_strategy_mismatch",  // each guardrail's own taxonomy (TCOV: weak_oracle | data_strategy_mismatch | missing_liveness_test | ...; TRACE: ORPHANED | PARTIAL | CONTRADICTED; ...)
  "severity": "blocking",                // blocking | warning
  "target": {                            // what it's about — the join keys
    "user_story": "US-2",
    "test_id": "TC-1.5",
    "spec_section": "§6.4",
    "contract": "bookCache"
  },
  "claim": "TC-1.5 stamps MOCK on a condition reproducible by funding a dev account.",
  "required_action": "Promote to REAL-DATA; live_or_induced: natural-wait.",
  "disposition": null                    // filled at fix/approve: accepted | fixed | dismissed | deferred (+ reason)
}
```

When the orchestrator resolves a finding (fix/approve/dismiss), it stamps `disposition` and — if the
resolution changed a TMR field — emits a Piece-3 transition citing this `finding_id` as the driver.

---

## 4. Piece 3 — Decision provenance journal (append-only, Q2; generalized)

A **single append-only journal** over **any tracked classification decision** — not just tests — one
record appended per change to a tracked field. Generalized to two subject types so future "track X's
provenance" wants are just a new `(subject_type, field)`:
- `subject_type: test` — the test-maturity journey (maturity / data_strategy / live_or_induced / spine
  / binding_status / run_evidence).
- `subject_type: node` — the **altitude-triage** decision per task node (altitude), incl. a close-time
  fit judgment. See §4a.

Indexed by (`subject_type`, `subject_id`); carries `session`. Append-only suits cheap meta-analysis
queries + safe concurrent multi-agent writes. Home: session detail while live →
`.architecture/tests/registry.journal.jsonl` on close. One record:

```jsonc
{
  "session": "adv-spec-202606151042-liveness-gate-test-ladder",
  "subject_type": "test",                // test | node
  "subject_id": "TC-1.5",                // test_id (tests) | task_id (nodes)
  "user_story": "US-2",                  // tests only (grouping); null for nodes
  "ts": "2026-06-15T10:42:00Z",
  "phase": "debate.R2",                  // requirements | roadmap | debate.Rn | gauntlet | execution | implementation
  "field": "data_strategy",              // tests: maturity|data_strategy|live_or_induced|spine|spine_step_ref|binding_status|run_evidence ; nodes: altitude|altitude_fit ; both: created
  "from": "MOCK",
  "to": "REAL-DATA",
  "driver": {
    "type": "guardrail",                 // debate_round|guardrail|human_correction|gauntlet_concern|promotion|depth_triage|reclassification|close_attestation
    "ref": "TCOV-r2-7a3f"                // finding_id | concern id | round | user id | triage-run
  },
  "note": "MOCK justification falsifiable per TCOV; reproducible on dev account."
}
```

### 4a. Altitude-triage provenance (`subject_type: node`)

Records the life of a node's altitude so triage calibration is measurable:
- `created` @ `depth_triage` (initial altitude + blast-radius rationale as `note`/`driver`),
- `altitude` reclassifications (from→to, driver `reclassification` / `gauntlet_concern` / `human_correction`),
- `altitude_fit` @ close (`driver: close_attestation`, `to ∈ {right, too_high, too_low}` + rationale).

**fizzy-side (coordinated spec, NOT this skill):** the change is **already detected** at
`pipeline.py:6263` (`changed.append("altitude")`) but discarded — emit a journal record there instead.
Session-level `altitude_at_debate_start` already exists (`pipeline.py:11962`) as partial precedent.
The close-time `altitude_fit` attestation is **new**. The skill's Phase-7 depth-triage step
(`07-execution.md`) contributes the initial altitude + rationale.

**The queries** (over `subject_type:node`, `field:altitude`/`altitude_fit`):
- *Altitude distribution* = histogram counting nodes by altitude (use `created` records for
  as-identified-at-triage; use last value per node for as-resolved). Answers "what is the overall
  distribution of altitudes we identified."
- *Subsystem triage precision* = count(first altitude==`subsystem` AND last altitude==`subsystem` AND
  `altitude_fit`==`right`) ÷ count(first altitude==`subsystem`).
- *Full calibration* = the 3×3 `initial × final` altitude confusion matrix.
- **Why `altitude_fit` is required, not just stability:** reclassification only catches altitudes
  someone actively fixed; a silently-wrong altitude nobody changed looks "stable" and would falsely
  count as accurate. Stability over-counts correctness; the close attestation corrects it.

**Composition:** the ledger is *derived* — aggregating Piece-2 findings + their dispositions across
rounds yields Piece-3 entries. Example chain: `TCOV-r2-7a3f` (finding) → orchestrator accepts → TMR
`data_strategy` MOCK→REAL-DATA → transition recorded with `driver=guardrail:TCOV-r2-7a3f`. The "test
journey" you want for meta-analysis = the `transitions[]` list per test, plus the spine/branch shape
per user story.

---

## 5. Worked example — US-2 "arm→fill" across the session

- **roadmap (`nl`):** author spine `TC-arm-fill-spine` (steps S1..S6, `spine:true`, `data_strategy:REAL-DATA`,
  `live_or_induced:natural-wait`). Failure tests `TC-partial-unwind` (`spine_step_ref:"S4"`),
  `TC-untrusted-book` (`spine_step_ref:"S2"`). Transition: `created` ×3, driver `debate_round:R0`.
- **debate R1 (TRACE subagent):** US-2 traced to spine ✓ (no ORPHANED finding). 
- **debate R2 (TCOV subagent):** `TCOV-r2-7a3f` data_strategy_mismatch on `TC-1.5` → accepted →
  transition `data_strategy MOCK→REAL-DATA`. TMRs promote `nl→acceptance` as accessors get named
  (transition `maturity`, driver `promotion`).
- **F′ gate (debate→gauntlet):** every US has a `spine:true` test at ≥`acceptance` → **passes** (does
  NOT demand `concrete`/live here).
- **implementation (G):** gateway shape lands; `binding_status unbound→bound`; spine RUN live →
  `run_evidence {result:pass, env:dev, artifact:"fill_8821"}`; `maturity acceptance→concrete`. fizzy
  sweep: spine `concrete`+green before any failure-branch card completes.
- On close: all US-2 TMRs + ledgers promoted into `.architecture/tests/registry.json` under
  `component:gateway` / `contract:bookCache`.

---

## 6. Consumer coupling (who keys on what)

| Consumer | Reads / writes |
|---|---|
| **A** authoring | writes Piece-1 TMRs in `tests-pseudo.md` at `nl` |
| **C/D** guardrail subagents | emit Piece-2 findings keyed by `user_story`/`test_id` |
| **F′** debate gate | reads `user_story`+`spine`+`maturity` → every US has a spine test at phase-acceptable maturity |
| **J** provenance | aggregates Piece-2 + dispositions → Piece-3 `transitions[]` |
| **G** Phase-8 promotion | reads/writes `binding_status`, `run_evidence`, `maturity` |
| **fizzy sweep** | enforces `maturity` + `run_evidence` (REAL-DATA→live run) + spine-before-branch |
| **fizzy P0** | adds `VALID_DATA_STRATEGIES`, `VALID_LIVENESS_TECHNIQUES`, `maturity`, and validates the new per-task fields (`_validate_v2_task` / `_build_v2_metadata`) |

---

## 7. Schema decisions (resolved — Jason, 2026-06-15)

1. ✅ **`user_story` cardinality** — `string | string[]`: a **spine is strictly 1:1** with its US;
   shared utility tests may be **N:1** (carry a list).
2. ✅ **Ledger storage** — **separate append-only journal** keyed by `test_id` (Piece 3), NOT inline
   `transitions[]` on the TMR. Better for meta-analysis queries + concurrent multi-agent writes.
3. ✅ **`architecture_link`** — **may lag**: required by `acceptance`, optional/empty at `nl`. F′ needs
   only `user_story`+`spine` at `nl`.
4. ✅ **journey == user_story** — the US is the grouping key; the spine is its anchor; failure tests
   branch off the spine's named steps. No separate journey id.
5. ✅ **Back-compat** — TMR fields optional + warn first, promoted to required behind the version fence
   (plan decision 3) so in-flight sessions aren't retroactively failed.
