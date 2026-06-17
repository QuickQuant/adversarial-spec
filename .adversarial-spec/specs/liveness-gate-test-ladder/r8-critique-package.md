# Spec: Liveness Gate + Architecture-Linked Test Ladder (adversarial-spec slice)

> Session: adv-spec-202606151042-liveness-gate-test-ladder | Card 5715 | Altitude: **system**
> Depth: technical/full | Draft: **v9** (post-gauntlet redesign) | Status: v8 converged at R7, then a full Phase-5 gauntlet on v8 (2 families, 380 concerns) surfaced real self-contradictions + a wrong subsystem design that collaborative debate missed. v9 folds 11 design decisions (`v9-design-decisions.md`, DR-1..11) and **removes ALL security machinery** — this is a local dev tool with a trusted operator + trusted own-ecosystem repos, so there is **no security threat model**; the gate catches *honest mistakes*, not a malicious actor. v9 removes real *machinery* (the snapshot/hash protocol, the security apparatus, `TestInputCollector`) though raw line count is ~flat — the redesign explanations + this changelog offset the deletions (both shrink at finalize). Re-converge pending.
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
> v5 changelog (R4 reframe-validation — codex+gemini both validated the SEC-1 direction with NO reversal; 5 hardening
> edits): R4-1 **activation rule** — `tmr.v1` is not mechanically enforced / the hole is not closed until the Fizzy gate
> lands AND an integration test proves a direct `pipeline_advance` fails closed without F′ evidence (slice-alone =
> advisory release; §1); R4-2 **normative F′ checker contract** — CLI/exit-codes/JSON + Fizzy fail-closed on any
> non-pass (§6); R4-3 §6/§0.2 framing — "mechanical" reserved for the Fizzy gate, skill-side = advisory contract check;
> R4-4 **authoring = prose-authored + LLM-compiled** to the validated registry (validate-on-emit + round-trip echo +
> human confirm; the registry stays SoR — preserves DD-1; §2/§4.2/§12.13, Jason); R4-5 **version fence anchored on the
> immutable Fizzy session-card creation timestamp** (local `created_at` = editable fallback tier only; §8.2).
> v6 changelog (remaining-accepts fold — the ~18 non-trust-model accepts from `gauntlet-concerns-2026-06-15.md`):
> **RC-1** `ProvenanceJournalWriter` (locked atomic append + idempotency + `expected_from`; Fizzy = single
> serializing writer of the persisted journal — §7); **RC-2** persisted `ConflictDispositionStore` (no
> crash-bypass; main loop refuses to advance while pending — §5.1); **RC-3** pinned per-round input-snapshot
> manifest + hash-agreement check (§5.1); **FM-1** transient retry/backoff before ORCH (no fail-closed self-DoS —
> §5.1); **FM-2** `N`-returned accounting (orchestrator-root death ≠ green — §5.1); **FM-4** lint-not-`rm` +
> `generated-from` source-hash allowlist (§3); **FM-5** structured TMR semantic-delta, not raw diff (§5.1);
> **SCA-1** bounded `TestInputCollector` + test-input manifest (no unbounded FS walk → context exhaustion —
> §5.3); **SCA-2** journal retention/index (§7); **DD-2** single-writer `CriticalityClassifier` (resolves the
> INV-009 re-derivation paradox; consumers reject unclassified records — §3.3); **DD-3** cited MOCK impossibility, reject scale/cost/time excuses,
> non-exhaustive technique enum, `natural-wait` scrutiny (§4.3); **DD-4** `promotion_request` vs executable
> realization split + required negative oracle + accessor-binding blocking dependency (§8.1); **DD-5**
> machine-readable JSON-Schema (`extra:forbid`) SoR, prose tables = hashed non-normative snapshots, verify fizzy
> rejects bad payloads (§3); **DD-6** one happy-path-spine *designation* per US + linked concrete tests via
> `spine_of`/`also_covers` (cross-cutting journeys; F′ single-designation check intact — §4.1); **DD-7** shared
> `SpineCoverageChecker` consumed by authoring-lint/F′/TRACE/TCOV (no re-implemented coverage logic — §6); **DD-8**
> tombstone/rename over a stable `tmr_uid` (§7); **DD-9** structured `decisions.log` JSONL + `decision_id` join
> (§7); **US-2** shared `GateResult` model + canonical outcome→exit map (§5.1/§6); **US-3** `acceptance` defined
> WITHOUT the façade (declared-pending accessors — §4.4); **US-4** tier-aware run_evidence receipt (code /
> system-validation / judgment) + criticality×env trust matrix (§8.1); **US-5** `golden_cases/manifest.json`
> schema (§9); **US-6** typed-transition conflict detection (cross-field) + deterministic headless
> force-accept-with-reason (§5.1); **US-7** strict typed coercion in `TmrParser`, reject ambiguous scalars (§4.2);
> **US-8** numeric `tmr.v<N>` comparator (no string-sort ambiguity; malformed → `version_fence_error` — §8.2). **Design-fork flagged
> (DD-6):** folded as an additive refinement (designation + linked tests), NOT a reversal of "exactly one spine
> per US" — F′ still keys on ≥1 ∧ ≤1 `spine:true` per US. No new debate findings were introduced; these are
> gauntlet-accepted fixes, pending one final convergence round.
> v7 changelog (R5 convergence round — codex/gpt-5.5 + gemini-3.1-pro, both agreed:false; 9 valid concerns,
> all applied — these are self-contradictions the v6 fold introduced, none reopen the locked trust model):
> **R5-C1** §4.2 — added `tmr_uid`/`spine_of`/`also_covers`/`technical_constraint` to the canonical field list
> (else `extra:forbid` would reject v6's own DD-6/DD-8/DD-3 records); **R5-G1** §4.2 — the regenerated prose view
> carries `tmr_uid` as a stable anchor so a prose rename is a DD-8 `rename`, not delete+add; **R5-C2** §8.1 —
> reconciled DD-4 vs SEC-4: owner repo AUTHORS/BINDS the test, the skill-runner EXECUTES the command + captures the
> typed receipt (receipt capture stays skill-side); **R5-C3** §3.1 — `live_or_induced` is now a tagged
> `{kind, detail?}` with an `other:<detail>` escape so DD-3's constructible techniques (clock-stub, cgroups) are
> representable under a still-strict validator; **R5-C4** §4.1/§6 — `also_covers[]` is NON-COVERING for F′ (each US
> needs its own scalar `spine:true`; F′ ignores `also_covers`); **R5-C5** §6 — Fizzy fail-closed blocks on ANY
> non-pass exit (`2|3|4|5`, incl. `setup_error`), not just `2|3|4`; **R5-C6** §4.3 — rewrote the opening MOCK
> bullet to match §0.2 (naming a technique ⇒ promote, never keep the MOCK); **R5-G2** §5.1 — headless
> auto-resolution is EXEMPT from the SEC-3 ≥50-char human floor (it records a typed MACHINE justification, not a
> self-generated free-text string; the floor governs interactive human overrides only); **R5-G3** §9 — the code
> tier demands semantic NEGATIVE oracles for the new infra components (SpineCoverageChecker, ConflictDispositionStore,
> CriticalityClassifier, ProvenanceJournalWriter, TestInputCollector, GateResult) — prove fail-closed, not just "runs".
> v8 changelog (R6 convergence re-review — codex/gpt-5.5 + gemini-3.1-pro; gemini [AGREE], codex 1 valid concern):
> **R6-C7** §3.1 — `live_or_induced` made a strict **union** (JSON `null` XOR a tagged object whose `kind` is
> never null); dropped `null` from the `kind` enum so the "no technique" case has a **single** encoding (JSON
> `null`, §4.3) — closes the R5-C3 ambiguity where both JSON `null` and `{kind: null}` looked valid under
> `extra:forbid`; `TmrParser` rejects `{kind: null}` / `{"kind": "null"}`. No trust-model change.
> v9 changelog (post-v8-gauntlet redesign — full rationale in `v9-design-decisions.md`; settled with the
> operator 2026-06-16 via a 3-tier control model: hard-gate metadata / soft-gate fidelity / operational guidance):
> **DR-1** `run_evidence` → discriminated union on an explicit `tier` field (code / system-validation /
> judgment), cross-checked vs `verification_mode`; exempt modes carry no receipt (§3.1/§8.1). **DR-2**
> `live_or_induced: null` disambiguated (`data_strategy=MOCK ∧ null ⇒ why_impossible present`). **DR-3** TMR
> gains `status: active|tombstoned` + `supersedes` + `tombstoned_at`; F′ counts only `active` (§4.2/§6/§7).
> **DR-4** `tmr_uid` = compiler-allocated ULID, hard-unique, immutable (§4.2). **DR-5** coverage = deterministic
> metadata diff validated by the `.architecture/` graph — kills `TestInputCollector` source-ingestion + token
> budget; LLM only spot-checks per-test adequacy (§5.2/§5.3). **DR-6** guardrails run **parallel** against
> orchestrator-passed identical content — the frozen-manifest / self-reported-hash / snapshot protocol is
> **DELETED**; typed findings with a `join_key` (§5.1). **DR-7** **NO security threat model — all security
> machinery stripped** (owner-repo "RCE", prompt-injection defenses, self-attested hashes, the "trust model"
> paragraph, YAML hardening — all deleted; dup-key handling KEPT as *correctness*, fault-injection blast-radius
> as *operational safety*, secret-redaction as *hygiene*; version fence KEPT as *compat*). **DR-8** MOCK
> falsification covers all non-REAL strategies (§4.3). **DR-9** env→real-pass rule tabulated — a critical seam
> needs `env:live` or a recorded technique (§8.1). **DR-10** decisions.log stays plain text; structured records
> live in the journal (§7). **DR-11** tests-pseudo header de-canonicalized (registry is SoR).
> **v9 morph fix (2026-06-16, post-authoring):** the v9 "consistency check passed (0 live refs)" claim missed a
> **user-story morph** — DR-5 deleted `TestInputCollector` + relocated coverage to US-8, orphaning US-7's spine
> `TC-7.0` (it tested the deleted ingest-files behavior; grep-clean because it named the behavior, not the dead
> symbol). US-7 **re-centered** on `missing_liveness_test`: spine rewritten to the liveness happy-path, §13 map +
> §5.3 corrected, promoter/`data_strategy_mismatch` demoted to secondary. The reconciliation flow + an
> `orphaned_spine` TCOV oracle were added to the skill so this class is caught at incorporation time, not by luck.
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
- Make it **impossible to reach the gauntlet through Fizzy's enforced transition path** without a
  phase-appropriate-maturity **happy-path spine** test for every user story. This impossibility claim is
  valid **only after** the coordinated Fizzy gate is deployed and tested (the **activation rule**, §1); it is
  **NOT** impossible via a direct/manual bypass until then. Until Fizzy enforcement lands, this slice provides
  **fail-fast local advisories + the F′ checker contract** — the skill-side check is advisory; the mechanical,
  non-bypassable gate is Fizzy-side (§6, SEC-1).
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

**Activation rule (R4 — release-gating; both critics CRITICAL).** `tmr.v1` is **not** considered
mechanically enforced, and this liveness hole is **not** closed, until the coordinated Fizzy spec lands a
gauntlet-entry gate that calls this slice's F′ checker **and** has an integration test proving a direct
`pipeline_advance` into the gauntlet lane **fails closed** without valid F′ evidence. Landing this skill slice
alone is an **advisory-only release** — it surfaces uncovered user stories early but mechanically blocks
nothing. The Fizzy-side gate MUST deploy concurrently with, or before, this slice for the guarantee to hold.

| Codebase | Owns | In this spec? |
|---|---|---|
| **adversarial-spec (this)** | authoring (A) + strict MOCK (B) + TRACE/TCOV folds (C, D) + F′ debate gate + provenance journal authorship (J) + structured-subagent guardrails (K) + Phase-8 promotion driver (G) + glossary/ADR (H) | ✅ |
| fizzy_pipeline_mcp | TMR persistence, `VALID_*` constants, run-evidence storage, **the mechanical F′ gate at gauntlet-entry** (calls this skill's F′ checker) + sweep-time enforcement, node-altitude journaling | ❌ separate coordinated spec — **HARD DEPENDENCY** for non-bypassability (SEC-1), not optional. **Deployment sequencing:** must deploy concurrently-with or before this slice (activation rule), else the hole stays open as advisory-only. |
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
2. Author **exactly one happy-path spine (TC-0) test per user story** as **prose** in `tests-pseudo.md`
   (named steps `S1…Sn`, `spine: true`; anchor each failure test to a spine step via `spine_step_ref`), then run
   the **compile step** (`/adversarial-spec` LLM compilation, R4-4) to emit **validated records** into
   **`tmr-registry.json`** — the system of record F′ parses. The compiler **validates every record on emit**
   (`TmrParser` field-for-field; malformed → `schema_error`, fail-closed) and **regenerates the canonical prose
   view**, surfacing an **echo-diff** for you to confirm before commit. *(The `[spine]` heading is a display aid —
   F′ parses the registry, not the tag. CB-7 + DD-1; authoring UX §12.13 RESOLVED R4: prose-authored + LLM-compiled.)*
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
exact failure this work exists to prevent. **Drift is caught by a lint, not an auto-delete (FM-4):**
if an unexpected copy appears, the lint **fails first and names it** — it **never `rm`s** a path
(INV-008 "delete any copy" would nuke test fixtures, generated docs, and archived tests that
legitimately embed the field table). **Derived artifacts are allowlisted** by a
`generated-from: <canonical-sha256>` header; a copy carrying a current source-hash header is a
sanctioned regeneration (lint passes), a copy without one is a blocking finding (lint fails, human
disposes). *(INV-008 reworded accordingly in `architecture-invariants.json` — CANON-r4 mirror.)*

The contract has **three coupled pieces**, all keyed to the data model:
1. **TMR** — the per-test record (`session · user_story · test_id`). **Stored as `tmr-registry.json`**
   (the local **system of record**, DD-1); `tests-pseudo.md` is a **generated prose view**, never
   authoritative. The canonical *schema* (field set + enums) is the keystone file above; the *records*
   live in the registry. *(Resolves the v3 §4.2 "feeder/view vs authoritative gate input" contradiction.)*
   **Machine-readable schema is the source of truth (DD-5).** The keystone is published as a
   **JSON Schema (`extra: forbid` / Pydantic `extra='forbid'`)** — Markdown cannot enforce
   unknown-field rejection or round-trip, so the prose tables in §3.1 are **non-normative snapshots**
   that each carry the schema's `schema_sha256`; CI fails if a snapshot hash drifts from the canonical
   schema. **fizzy's strict rejection is verified, not assumed (DD-5):** a contract test sends a
   known-bad payload (unknown field + bad enum) and asserts fizzy *rejects* it — popular validators
   default to silently ignoring extras (Pydantic `extra='ignore'`), the exact silent-drift vector this
   spec kills.
2. **Guardrail finding** — what each parallel-subagent guardrail returns, keyed to `user_story`/`test_id`.
3. **Decision provenance journal** — append-only, over `subject_type ∈ {test, node}`.

### 3.1 Shared enums (must match fizzy P0 field-for-field)
| Enum | Members | Source of truth |
|---|---|---|
| `maturity` | `nl` → `acceptance` → `concrete` | **NEW** (define here; fizzy P0 adds). `functional` is a design-doc alias for `concrete`; **canonical is `concrete`**. |
| `data_strategy` | `REAL-DATA`, `REAL-DATA + PROPERTY`, `SYNTHETIC`, `MOCK`, `MOCK-EXTERNAL`, `FRONTEND`, `STATIC` | skill (`CONTEXT.md` / `02-roadmap.md §9a`); fizzy P0 adds `VALID_DATA_STRATEGIES` |
| `live_or_induced` | **Either** JSON `null` **or** a **tagged object** `{kind, detail?}` whose `kind` is **never null**: `kind ∈ {natural-wait, toxiproxy:corrupt, toxiproxy:drop, tc-netem:latency, tc-netem:partition, external-kill, clock-stub, state-injection, other}`; `detail` is **required when `kind ∈ {other, state-injection}`** (the constructible technique, e.g. `cgroups`, `chmod 000`). JSON `null` is the **single** encoding for "no listed or constructible live/induced technique exists" (a genuinely justified MOCK, §4.3); a present technique is **only** a tagged object with non-null `kind`. The enum of *named* kinds is closed for validation, but `other:<detail>` keeps it **non-exhaustive in meaning** (R5-C3) so a DD-3 constructible technique is representable; `TmrParser` rejects `{kind: null}`, `{"kind": "null"}`, and `other`/`state-injection` with no `detail` (R6-C7). | **NEW** (define here; fizzy P0 adds `VALID_LIVENESS_TECHNIQUES` + the `other` escape) |
| `verification_mode` | `automated-unit`, `automated-integration`, `automated-contract`, `automated-component`, `test-producer`, `artifact-sync`, `static-check`, `manual-ux`, `system-validation` | **fizzy** (`VALID_VERIFICATION_MODES`) — reference, do not redefine |
| `verification_scope` | `targeted`, `full-suite`, `static`, `manual`, `end-to-end` | **fizzy** |
| `altitude` | `component`, `subsystem`, `system` | **fizzy** (`VALID_ALTITUDES`) |
| `tested_by` | `llm`, `user`, `both` (default `llm`) | **fizzy** (`VALID_TESTED_BY`) |
| `run_evidence.env` | `live`, `dev`, `ci` | **NEW** (extends fizzy v3 evidence block) |
| `run_evidence.result` | `pass`, `fail` | **fizzy** (`VALID_BASELINE_RESULTS`) |
| `run_evidence` (shape) | **discriminated union on an explicit `tier` field** (DR-1): one of the `code` / `system-validation` / `judgment` receipt variants defined in §8.1; `tier` is hard-checked against `verification_mode` (must agree). Exempt `verification_mode`s carry **no** `run_evidence`. | **NEW** — skill captures it by RUNNING the test (§8.1); never hand-written |
| `binding_status` | `unbound`, `bound` | **NEW** (acceptance→concrete promotion key; define here, fizzy P0 adds) |
| `critical_seam` | `true`, `false`, `null` (JSON null) | **NEW (R2)** — added to canonical §2; `null`+`criticality_source:unknown` = `criticality_unknown` (treated as critical) |
| `criticality_source` | `explicit`, `architecture_link`, `unknown` | **NEW (R2)** — companion to `critical_seam`; fizzy P0 adds |

**`null` is JSON `null`, not the string `"null"`** (R2: codex) — applies to `live_or_induced`,
`critical_seam`, `run_evidence.*`, `spine_step_ref`. For `live_or_induced`, JSON `null` means
"no live/induced technique exists" (justified MOCK); a present technique is represented **only** as a
tagged object whose `kind` is non-null — `{kind: null}` is rejected (R6-C7).

**Orthogonality (load-bearing):** `verification_mode` answers *unit vs integration*;
`data_strategy` answers *real vs faked*; `altitude` answers *how deep / how much rigor*. Three
independent axes — a critical-seam task sets all three. `data_strategy` is the genuinely missing
axis fizzy lacks.

### 3.2 Handshake (which repo lands constants first) — RESOLVED (R4, release-blocking)
fizzy P0 adds `VALID_DATA_STRATEGIES`, `VALID_LIVENESS_TECHNIQUES`, and `maturity`; this skill's registry
records + emission must match field-for-field. **Resolution (R4):** **fizzy P0 lands the constants + the
F′-checker `contract_version` first** (or concurrently). This skill's `TmrParser` **fails closed** on any
field/enum the current fizzy schema version doesn't support, and the Fizzy gate **fails closed** on a checker
`contract_version` it doesn't recognize — a mismatch is a **named blocking error** at gauntlet entry, never a
silent drop/accept. This handshake is **part of the activation rule (§1)**: enforcement is not "on" until both
sides agree on `tmr_schema_version` + checker `contract_version` (+ hash). Until then, TMR fields are
**optional + warn-first**, promoted to required behind the version fence (schema decision 5).

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
- **Single-writer `CriticalityClassifier` resolves the INV-009 paradox (DD-2).** INV-009 says
  consumers read only the normalized `critical_seam` and **never re-derive** it — but *detecting* an
  explicit-vs-architecture **disagreement** requires re-deriving from `architecture_link`. The
  resolution: **one `CriticalityClassifier` is the sole writer** of `critical_seam` +
  `criticality_source`, and it is the **only** component permitted to read `architecture_link`. It
  runs **once, before the guardrails**, performs the disagreement check internally (the one allowed
  re-derivation), and writes the normalized verdict. **Consumers reject an unclassified record**
  (`criticality_source` absent) rather than deriving their own — so no consumer re-derives, INV-009
  holds, and the disagreement is still caught (inside the classifier, not by every reader).

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
- Every user journey (== user story) declares **exactly one happy-path spine _designation_** (TC-0)
  with **named steps** `S1…Sn`. (Term is always written **"happy-path spine"**, never bare "spine" —
  see §10 / locked term decision.)
- **One designation, possibly many concrete tests (DD-6).** "Exactly one" constrains the *spine
  designation* per US (so F′ keys on **≥1 ∧ ≤1** `spine:true` record — §6 unchanged), **not** the
  number of executable tests realizing it. A US with multiple role/platform journeys, or a
  **cross-cutting journey spanning US-A + US-B**, designates **one** canonical spine and links
  additional concrete tests to it via `spine_of: <designation_id>` — authors **never duplicate a test
  to fake coverage**. Define the distinction explicitly in the authoring doc: **duplicate-concept**
  (two spine *designations* for one journey — a lint failure) vs **duplicate-coverage** (multiple
  legitimate concrete tests under one designation — allowed). A cross-US journey sets a scalar
  `user_story` to its **primary** US and lists co-covered US IDs in `also_covers[]`.
  **`also_covers[]` is NON-COVERING for F′ (R5-C4):** it is descriptive metadata only — it does **not**
  satisfy F′ for a secondary US. **Every US must still own its own scalar `spine:true` designation**
  (`user_story == US-x`); F′ counts only the scalar `user_story` of `spine:true` records and **ignores
  `also_covers[]`** when computing ≥1 ∧ ≤1 (§6). So a journey spanning US-A + US-B needs a spine
  designation owned by US-A and one owned by US-B (one may `also_covers` the other for traceability);
  it cannot use one spine to "cover" both for the gate.
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
**keys match the canonical keystone field-for-field**: `tmr_uid` (stable immutable identity — a **compiler-allocated ULID**, globally unique across the registry, immutable once minted; DD-8/DR-4),
`title`, `source_spec`, `test_id`, `user_story`, `also_covers` (DD-6 — **non-covering** co-covered US IDs),
`maturity`, `spine`/`spine_steps`/`spine_step_ref`, `spine_of` (DD-6 — links a concrete test to its
designation), `data_strategy`, `live_or_induced`, `technical_constraint` (DD-3 — the citable impossibility
reason for a justified MOCK), `why_impossible_to_reproduce_live`, `verification_mode`, `verification_scope`,
`altitude`, `tested_by`, `critical_seam`/`criticality_source`, `architecture_link`, `accessors`,
`binding_status`, `status` (`active`|`tombstoned`, default `active`; DR-3 — F′ counts only `active`), `supersedes` (`<tmr_uid>`|`null`; DR-3 — a replacement points at what it tombstones), `tombstoned_at`, `run_evidence`. **Every field used normatively by a v6 fix is in this canonical list**
(R5-C1) — `extra: forbid` (DD-5) would otherwise reject a valid DD-6/DD-8/DD-3 record. The keystone JSON
Schema is the authority; this prose list is a hashed non-normative snapshot (DD-5).
**`tests-pseudo.md` is the prose authoring surface AND the canonical generated VIEW (R4-4).** The human authors
prose there; an **LLM compile step** emits validated records into the registry; the canonical prose view is then
**regenerated** from the registry and an **echo-diff** against the authored prose is surfaced for confirmation
before commit. **The regenerated view carries each record's `tmr_uid` as a stable anchor (R5-G1)** — an
HTML comment above the test's heading (e.g. `<!-- tmr_uid: t-0a1b -->`) — so the compiler **diffs on
`tmr_uid`**: a prose **rename is detected as a rename, not delete+add**, it emits the DD-8 `rename` journal
record, and lineage survives a `TC-0 → TC-8.0` / US-renumber edit (without the anchor the human edits prose
that has no stable identity, breaking DD-8). **`tmr_uid` allocation (DR-4):** the compiler **mints** the ULID on first emit of a new TMR (a test authored with no `tmr_uid`), writing it to both the registry record and the prose anchor — **the LLM never allocates it**. `TmrParser` **rejects a duplicate `tmr_uid` or a duplicate prose anchor as a `schema_error`** (the rare copy-pasted-block-with-stale-anchor slip — the human deletes the duplicate; not normal flow). Authoring guidance: to make a new test, author it without a `tmr_uid` (or strip the anchor when copying a block) and let the compiler mint one. Its markdown headings, prose "Spine steps," and `[spine]` tag are **display aids only** — F′ and
the guardrails parse the **registry**, never embedded markdown YAML (DD-1: 7 adversaries flagged
LLM-authored-YAML-in-markdown as fragile + a dual source of truth). **The LLM compiler does NOT become the author
of record:** its output is `TmrParser`-validated on emit (malformed → `schema_error`, fail-closed; FM-3), echoed
back to prose, and human-confirmed — three guards that stop prose→registry compilation from re-introducing the
DD-1 fragility one level up. *(CB-4: `title` + `source_spec` are keystone fields per the TC-8.0 exemplar / TC-1.3.)*

**One shared `TmrParser`** loads + validates the registry field-for-field (unknown key / missing required
key → named `schema_error`, **never** coerced to "0 spines"; FM-3) and is the **only** TMR reader for F′,
guardrails, and emission (no per-gate parsers — DD-7).

**Strict typed coercion; no ambiguous scalars (US-7).** Because the registry is **JSON** (not
YAML-in-Markdown), most of the YAML coercion hazards are structurally gone — `null` is JSON `null`,
booleans are `true`/`false`, and `"REAL-DATA + PROPERTY"` is an unambiguous quoted string. The
remaining surface is the **LLM compile step** (prose → registry, §2/R4-4): the compiler emits typed
JSON and `TmrParser` **rejects, never coerces**, any ambiguous value — string `"null"`/`"~"`/`"None"`
where a JSON `null` is meant (would defeat `criticality_unknown` fail-closed), `spine:"true"`/`"yes"`/
`1` for a boolean, or a duplicate key. Each is a named `schema_error` (fail-closed), so the
coercion-bypass class (US-7: 5 adversaries) cannot resurrect itself one level up at compile time.

`verification_tier` (§9) is **feeder-only planning metadata** — it is NOT emitted to fizzy as a TMR field.
(The TC-8.0 exemplar in `tests-pseudo.md` shows the record shape; the authoritative copy is the registry entry.)

### 4.3 Strict MOCK falsification (B)
<!-- Addresses US-3 -->
- **The MOCK rule, stated to match §0.2 (R5-C6):** a justified `MOCK` must **deny that ANY listed or
  constructible technique** (`toxiproxy:corrupt/drop`, `tc-netem:latency/partition`, `external-kill`,
  `clock-stub`, `state-injection`, …) could induce the behavior live. **If a technique CAN be named,
  that is proof the behavior is inducible → promote to `REAL-DATA`** (the named technique goes in
  `live_or_induced`; `live_or_induced: null` is reserved for a genuinely justified MOCK). The earlier
  "name the technique that would make it live" phrasing inverted this — naming a technique is grounds
  to **promote**, never to keep the MOCK.
- **The rule keys on real-ness, not the label (DR-8).** For a **critical seam** the falsification
  requirement applies to **every non-REAL `data_strategy`** — `MOCK`, `MOCK-EXTERNAL`, `SYNTHETIC`,
  `STATIC`, `FRONTEND` — not just literal `MOCK`. Hard rule: `critical_seam = true ∧ data_strategy ∉
  {REAL-DATA, REAL-DATA + PROPERTY} ⇒ why_impossible_to_reproduce_live present and non-empty`; the soft
  gate judges whether the justification is honest. (Else a critical seam dodges the rule by relabelling
  itself `SYNTHETIC`/`STATIC`.)
- `live_or_induced:` is a **first-class field** (the technique pointer on a REAL-DATA/induced test),
  distinct from the prose justification; a justified MOCK sets it to `null` and carries a
  `technical_constraint` instead (DD-3). **`null` disambiguation (DR-2):** JSON `null` reads two ways —
  "justified MOCK, no technique" vs "plain REAL-DATA test, no fault" — so the sibling `data_strategy`
  disambiguates via a **hard cross-field rule: `data_strategy = MOCK ∧ live_or_induced = null ⇒
  why_impossible_to_reproduce_live present and non-empty`.** A REAL-DATA record with `live_or_induced:
  null` is simply a real test that induces no fault — no justification needed.
- Mirror the stricter standard into the PEDA/BURN/AUDT adversary prompt text
  (`scripts/adversaries.py`) and the `phases/03-debate.md` MOCK-falsification directive (line ~404).
- A `MOCK` whose `why_impossible_to_reproduce_live` names a condition **forceable on dev infra**
  (and that names no technique) is flagged; required action = **promote to REAL-DATA**.
- **Impossibility must be cited, not asserted (DD-3).** A justified MOCK carries a
  **`technical_constraint`** — a concrete, citable reason the boundary cannot be induced on dev infra
  (e.g. "requires a third-party prod webhook with no sandbox", a missing capability, a hardware
  dependency), **not** prose denial. **Scale / cost / time excuses are rejected** ("2³¹ items",
  "would exhaust the rate limit", "slow") — those are induced via **state-injection, clock-stub, or
  bounded fixtures**, so they `PROMOTE`, never exempt. The `VALID_LIVENESS_TECHNIQUES` enum is
  **non-exhaustive**: "no technique exists" means "no technique listed **or** constructible"
  (app-level fault injection, clock-stub, `cgroups`, `chmod 000`, `tc-netem` where `NET_ADMIN` is
  available) — the lint asks "could state-injection/clock-stub force this?" before accepting MOCK.
- **`natural-wait` is itself scrutinized (DD-3).** It is a real technique for genuine timing seams
  but a common loophole; a MOCK leaning on `natural-wait` must justify why a **clock-stub** can't
  replace the wait. A `tc-netem`-based technique records that it needs `NET_ADMIN` so an un-runnable
  environment surfaces as a setup error, not a silent pass.

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

**`acceptance` is defined WITHOUT the façade (US-3).** The concept-accessor façade is a non-goal
(§1.1, NG-2), so `acceptance` may not *depend* on it for meaning. At `acceptance` a test must:
(a) **compile / parse as executable code**, (b) bind a **real oracle** (concrete assertions, not a
TODO), and (c) declare its `accessors[]` as **named symbols** — each resolving to *either* an
existing API in the owner repo *or* a **declared-pending accessor** (a binding the owner repo owes,
tracked as a dependency). The façade, **where a target repo provides one**, is the *binding
mechanism* that flips `acceptance → concrete` (`binding_status unbound → bound`); where it does not
exist, `acceptance` still has executable meaning via real symbols, and the **missing binding is a
declared blocking dependency** on the owner repo — never a silent "label with no meaning." This keeps
`acceptance` reachable for repos with no façade and makes the façade an *accelerator*, not a
precondition.

---

## 5. Guardrail rearchitecture: parallel subagents + structured output
<!-- Addresses US-5, US-6, US-7 -->
**Blast zone:** `scripts/adversaries.py` (`REQUIREMENTS_TRACER`, `TEST_COVERAGE_AUDITOR`,
`GUARDRAILS` dict), `reference/guardrail-prompts.md`, `phases/03-debate.md` (invocation contract).

### 5.1 Parallel-subagent dispatch with structured findings (K)
<!-- Addresses US-5 -->
- **Each of the five guardrails (CONS/SCOPE/TRACE/CANON/TCOV) runs as its own parallel subagent**,
  launched together after each revision — **never one combined prompt** (persona dilution).
- Each subagent is **self-contained**: its persona prompt + **the input content the orchestrator passes
  it** (spec, `tests-pseudo.md`, roadmap manifest, canonical contract index, relevant `.architecture/*`)
  + **the round diff**. Subagents start fresh (no main-conversation inheritance) and **do not re-read
  live files themselves** — the orchestrator reads the inputs **once and hands every subagent identical
  content**, so all five provably evaluate the same bytes. The diff is how they learn "what changed."
- **No snapshot/hash protocol (DR-6).** Because guardrails are **read-only** and receive
  orchestrator-passed content (not self-read live files), there is **no mixed-snapshot race** to defend
  against — earlier drafts' frozen-manifest + per-subagent `content_sha256` self-reporting is **deleted**.
  The one residual ("another agent edits the branch mid-round") is **operational guidance, not a gate**:
  *don't modify this session's spec/tests from another context while a debate round is in flight.*
  (Trusted operator — no security/adversarial-writer threat model; see §0.3.)
- **Structured semantic delta, not raw text diff (FM-5).** The "what changed" signal is a
  **TMR semantic-delta** (`{test_id, field, old, new}` per changed record) **plus** the text diff, not
  the diff alone. A finding's join key (`test_id`/`user_story`) often sits **outside** the changed
  hunk; handing subagents the semantic delta means the key travels with the change, so a real finding
  isn't dropped by the CB-3 "no join key → rejected" rule for lack of nearby context.
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
- **Distinguish transient transport failure from a real guardrail failure (FM-1).** Fail-closed must
  not weaponize a 429/jitter into a self-DoS: a transient transport error (rate-limit, timeout,
  connection reset) is **retried with bounded backoff** (a per-round retry budget) **before** any
  `ORCH` is emitted; only a *real* guardrail failure (invalid JSON after retries, a persona that
  refuses, a genuine crash) becomes a blocking `ORCH`. The retry budget and backoff are part of the
  dispatch contract, so concurrent 429s during peak hours degrade gracefully instead of deadlocking
  the pipeline. *(FM-1: 7 adversaries — the No.1 operability risk of the fail-closed design.)*
- **A crashed orchestrator is not a pass (simplified, DR-6).** The orchestrator launches N subagents and
  awaits N; it trusts "0 findings = pass" **only** when all N returned. A subagent that dies / times out /
  returns invalid JSON is the leaf-`ORCH` case above. If the **orchestrator itself** dies mid-round, the
  round simply **did not complete** — nothing writes a pass — so no separate `expected/received`
  accounting machinery is needed (a serial/awaited fan-out can't half-report a green).
- **Conflict state (R2: both).** Two findings with conflicting `required_action` on the same
  `target`+field enter a **`conflict`** aggregation state requiring human/orchestrator disposition
  **before** any journaled field transition.
- **Conflicts are typed transitions, detected across fields (US-6).** Conflict detection keys on a
  **typed transition model** `{subject, field, from, to, action}`, **not** identical-`required_action`
  string match — so it catches **cross-field** semantic conflicts the narrow check misses
  (`promote` vs `delete` on the same TMR; `critical_seam` set true vs an `altitude` lowered to
  component). Two transitions whose `to` states are incompatible are a conflict regardless of wording.
- **Pending conflicts are PERSISTED — no crash-bypass (RC-2).** An unresolved conflict/disposition is
  written to a **discrete `pending-dispositions.json` state file** (a `ConflictDispositionStore`),
  **not** held only in memory and **not** in the append-only journal (which stores *accepted* changes
  only). The main loop **refuses to advance a phase while that file is non-empty**, and on
  restart/crash/timeout/laptop-close it **re-reads pending conflicts** — so a fail-closed mechanism
  can't silently fail *open* (RC-2: crash → restart sees no conflict → TMR still MOCK → proceeds clean
  was the exact silent-bypass hole).
- **Deterministic resolution in a headless loop (US-6).** "Human disposition" has **no tie-breaker in
  a headless CLI** → re-trigger → permanent deadlock. So every conflict has a **deterministic
  force-accept path**: in interactive mode a human disposes (typing a **reason for the audit log** —
  honest record, not a security floor); in headless mode the loop applies a **declared precedence**
  (fail-closed / higher-altitude / more-conservative transition wins) and records a **structured machine
  justification** — `{decision_id, resolution: "headless-precedence", precedence_rule,
  winning_transition, losing_transition}` (typed, not a free-text reason; journaled and auditable). The
  loop **never** loops forever and **never** silently picks a winner (the choice + rule are always
  recorded).
- This makes the C/D changes a **dispatch-mechanism change**, not just prompt edits: the
  `03-debate.md` invocation contract becomes a parallel-subagent dispatch + structured-aggregation
  spec.
- **Observability rationale:** `token_tracking` records by model only — today we cannot answer
  "dispatch vs inline %" nor "what did TCOV say about TC-1.5 in R2." Structured per-guardrail
  output closes that gap.
- **Shared `GateResult` model (US-2).** Every gate (the F′ checker, the staleness gate, the ORCH
  aggregator) returns **one typed `GateResult`** — `outcome ∈ {pass, warn, block, setup_error,
  schema_error, orch_error}` + `findings[]` + `override_eligible: bool` — instead of overloading a
  bare `exit 2`. There is **one canonical map** from `GateResult.outcome` → CLI exit code (the §6
  table) and → MCP structured-error code, so a **setup error** (missing manifest), a **policy
  violation** (uncovered US), a **schema error** (bad TMR), and an **orchestration error** (subagent
  death) are never conflated. `override_eligible` is set by the gate: a coverage `block` is
  overridable (logged ≥50-char reason); a `schema_error` / `setup_error` is **not** (fix the input,
  don't bypass it).

### 5.2 TRACE inversion (C)
<!-- Addresses US-6 -->
- Today TRACE is **forbidden** from flagging missing tests. **Invert specifically for the
  happy-path spine:** a journey with prose but **no happy-path spine test = `ORPHANED`** (a
  traceability break), not a test suggestion. The **general no-test-suggestions rule still holds**
  for everything else (a missing non-spine edge-case test is NOT flagged by TRACE).
- **Absorbs the dropped SPINE guardrail's semantic check (E dropped):** TRACE also judges whether
  the test *labeled* the spine is actually the **primary success path** for that journey (not an
  edge case mislabeled). TRACE already reasons about journeys/coverage, so this fits its persona.

### 5.3 TCOV: liveness guardrail (+ promoter) (D)
<!-- Addresses US-7 -->
> **Re-centered post-gauntlet (DR-5 morph, 2026-06-16).** DR-5 deleted `TestInputCollector` and
> relocated coverage to US-8's `SpineCoverageChecker`, so US-7's **primary, distinctive deliverable
> is now `missing_liveness_test`** (#4 below — owned by no other US; its happy-path is TC-7.0's
> re-centered spine). The **promoter** (#1; its rule lives in US-4/§4.4) and **`data_strategy_mismatch`**
> (#3; its rule lives in US-3/§4.3) are **secondary** TCOV findings — TCOV is where those rules fire,
> not where they are defined. (List order preserved to keep `§5.3 #N` cross-refs stable.)
1. **Promoter, not just auditor:** emit `PROMOTE nl→acceptance` for tests whose elements all map
   to named accessors; emit `BLOCK` when a concept is unnamed.
2. **Coverage is a metadata diff, NOT test-source ingestion (DR-5 — replaces `TestInputCollector`).**
   Don't feed raw test source to an LLM and ask "is everything covered" — that doesn't scale, and a
   partial/truncated read of a *coverage* check is worse than none (a false "covered"). Instead, every
   test carries its **`user_story` link as metadata** (a TMR field, established at **roadmap time** when
   the US + its `nl` tests are first authored). **Coverage = a deterministic diff over that metadata**
   (hard gate): every US has ≥1 linked `active` test of adequate maturity/strategy — an extension of F′'s
   existing "exactly one spine per US." The **`.architecture/` causality graph validates** a claimed
   test→US link (the test exercises module M; the architecture associates M with the US's area) — the
   same pattern `critical_seam` uses with `architecture_link`; validate where the code→US mapping is
   reliable, advisory-flag where it isn't. The **LLM's role shrinks to targeted per-test adequacy**
   (soft gate): "is **this** flagged test's oracle real / not a smoke test / not secretly mocking the
   boundary" — never "read all test source to judge global coverage." This **deletes** the
   `TestInputCollector`, its token budget, and the over-budget `setup_error` (SCA-1/SCA-3 evaporate —
   there is no source-ingestion step to overflow).
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

**INV-003 (reframed post-gauntlet, SEC-1):** non-bypassability is delivered **only** by the **Fizzy-side**
mechanical gate (below), not the skill-side prompt. The skill-side path is an **advisory contract check** — it
provides fail-fast advisories and **defines the exact F′ contract Fizzy enforces**. (The word "mechanical" is
reserved for the Fizzy gate; the skill-side check is advisory unless Fizzy calls it during `pipeline_advance`.)
The skill-side **advisory coverage check**:
- **Coverage check (advisory; mechanical only when Fizzy invokes it):** every user story in the **roadmap
  manifest** has **exactly one `active`** record in `tmr-registry.json` tagged `spine: true` referencing it
  — **≥1 AND ≤1** among non-tombstoned records (DR-3: `status: tombstoned` rows are inert and never counted)
  (R1: codex). Deterministic —
  structural absence *or duplication* an LLM can't hand-wave. A **duplicate** happy-path spine for one
  US → warn on `critique`, `exit 2` on `gauntlet` (same action-branching as the missing case). This
  makes §6 consistent with §4.1's "exactly one."
  **One shared `SpineCoverageChecker` (DD-7).** The "≥1 ∧ ≤1 happy-path spine per US" rule is
  implemented **once** and consumed by all four mechanisms that touch it — the **authoring lint**
  (author-time), **F′** (gate-time), **TRACE** (ORPHANED detection, §5.2), and **TCOV** (promoter,
  §5.3) — each with a crisp role (author-warn / block / traceability-flag / promote) but **no
  re-implemented coverage logic**, so the four can't drift to different wording or bypass behavior
  ("copy-the-easiest-check"). Pairs with the single `TmrParser` (one reader) above.
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
- **Override:** a coverage `block` is overridable via a logged override that records a **reason** to
  `sessions/<id>.decisions.log` — for the audit trail (an honest record, **not** a security control; DR-7).
  Spec a `--accept-missing-spine` + `--spine-override-reason '<reason>'`. (`schema_error` / `setup_error`
  remain **non-overridable** — fix the input, don't bypass it.)
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
- **F′ checker contract (normative — R4-2, both critics).** Fizzy invokes the skill's checker as a stable
  contract; the skill **never** embeds Fizzy logic and Fizzy **never** reimplements the parser:
  - **CLI:** `uv run gauntlet-check --session <session_dir> --roadmap-manifest <path> --tmr-registry <path> --action gauntlet --output json` (MCP-tool equivalent request fields: `session_dir`, `roadmap_manifest`, `tmr_registry`, `action`, `contract_version`).
  - **Exit codes (canonical `GateResult.outcome` → exit map, US-2):** `0` `pass` · `2` `block` (coverage failure or duplicate happy-path spine; `override_eligible:true`) · `3` `schema_error` (`TmrParser` reject; **not** overridable) · `4` `orch_error`/checker invocation/runtime error · `5` `setup_error` (missing manifest/registry; **not** overridable). `warn` (advisory `critique`) exits `0` with findings. The same `GateResult` maps to MCP structured-error codes for the Fizzy-side call.
  - **Output JSON:** `{contract_version, result, checked_at, session_id, roadmap_manifest_sha256, tmr_registry_sha256, findings[], evidence_id}`.
  - **Fizzy fail-closed rule:** checker-not-found, timeout, invalid JSON, schema mismatch, unsupported `contract_version`, stale evidence hash, or **any non-pass exit (`2|3|4|5` — including `5` `setup_error`)** → **blocks gauntlet entry** (R5-C5: only exit `0` `pass` admits entry; a missing manifest/registry `setup_error` must NOT slip through). Fizzy calls the checker **at transition time**; pre-attached F′ evidence is accepted **only if** its `roadmap_manifest_sha256` / `tmr_registry_sha256` match the current artifacts (no stale-evidence replay).
- **Parses `tmr-registry.json`, not embedded markdown (REVISED post-gauntlet; DD-1, resolves §12.3):**
  F′ reads each test's record from the structured **`tmr-registry.json`** (§4.2) — `user_story`,
  `spine`, `maturity` — plus the roadmap manifest's canonical US IDs. Parsing a pure structured file
  removes the LLM-authored-YAML-in-markdown failure class (7 adversaries). Each `spine:true` record has
  exactly one **scalar** `user_story`; **F′ counts coverage on that scalar only and IGNORES
  `also_covers[]`** (R5-C4), so every US needs its own owning spine designation. The markdown `[spine]`
  tag is a display aid only. Acceptable
  maturity at debate→gauntlet = `nl | acceptance | concrete` (`nl` passes; `concrete` + `run_evidence`
  is Phase-8/G, not F′).
- **Stale-tests precede F′; `--accept-tests-stale` does NOT bypass F′** (separate override).
- **Dependency:** depends on **A** — the TMR `spine:` / `maturity` / US-reference fields must exist
  to key on. The F′ parse couples the **roadmap-manifest US enumeration** ↔ the **`tmr-registry.json`
  spine records** (resolved R2/§12.3; DD-1 moved this off markdown).
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
cheap meta-analysis queries. **Evolution is NOT stored inline
on the TMR** — it lives only in this journal (schema decision 2).

**Concurrency is DESIGNED, not asserted (RC-1).** "Safe concurrent multi-agent writes" needs a real
writer: a **`ProvenanceJournalWriter`** that does **locked atomic append** (`O_APPEND` under a
`filelock`), stamps each record with a **`record_id`** and an **`idempotency_key`** (so a retried
write is de-duplicated, not double-appended), and applies an **`expected_from` optimistic check**
(the transition's `from` state must match the journal's current value for that field, else reject as
a stale write). **No two processes append to the same journal file**: the skill writes the
**session-live** journal; on close, **Fizzy is the single serializing writer** of the persisted
`.architecture/tests/registry.journal.jsonl` (via MCP) — the skill emits records *to* Fizzy, it does
**not** co-write the same file (RC-1's byte-interleaving / corruption hole when "two repos append
node records to one file"; §7.2).
- **Retention / bounded reads (SCA-2).** Per-US replay must **not** load the whole growing JSONL into
  memory. The journal is either **rotated with retention** (segment files + a compaction index) or
  backed by an **indexed immutable store** (SQLite append-only rows) so a `field: altitude` or
  `subject_id` query reads an index, not a full scan. Long sessions stay bounded; couples with RC-1's
  single-writer rule.
- **Deletion / tombstone / rename model (DD-8).** The journal tracks field changes but must also
  represent **delete / supersede / split / merge / rename** as **tombstone records** against a
  **stable identity** (an immutable `tmr_uid` separate from the human `test_id`). An identity-tuple
  rename (`TC-0 → TC-8.0`, a US renumber) appends a `rename` record linking old→new `tmr_uid`. Lineage is
  preserved. The journal records the tombstone/rename **event**; the registry's **`status` field (DR-3)**
  is the **current state** F′ reads — so a **tombstoned TMR no longer satisfies F′** (F′ counts only
  `active` records) **without F′ having to replay the journal**.
- **Durable override↔correction join (DD-9; decisions.log stays plain text — DR-10).** F′/gate
  **overrides** are noted in the existing **plain-text** `sessions/<id>.decisions.log` (the human ledger —
  unchanged convention). The **structured** override record (with a stable **`decision_id`**) lives in
  **this journal**, *not* by reformatting decisions.log to JSONL. To join "gate bypassed" ↔ "field
  corrected later," a journal record whose change was *driven by* an override **cites that `decision_id`**
  in its `driver` (§7.1). Two artifacts, each in its native format — no migration, no conflict with the
  live plain-text convention.

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
  `system-validation`; judgment → golden eval). **The skill RUNS the test itself and captures the typed
  `run_evidence` receipt (DR-1)** — it **never trusts a hand-written `result: pass`** (the receipt is
  captured by running, so the evidence isn't authored by hand). For a **critical seam** the receipt must
  also evidence the named technique was **active** (the induced fault actually applied), and a
  **best-effort mock-detection lint** flags a REAL-DATA/critical-seam test that imports a mock/patch of
  the boundary it claims to exercise (flag, not hard-block — AST detection is heuristic; this is the
  *soft gate* — you can't mechanically prove a test isn't secretly mocked).
- **No security threat model (DR-7).** This is a local dev tool with a trusted operator and trusted
  own-ecosystem owner repos. The gate catches **honest mistakes** (a forgotten spine, an accidental
  smoke test, a stale record, a real test mocked-by-accident), **not** a malicious actor — so the earlier
  "forgery bar / admin-adversary trust model" paragraph and YAML hardening are **deleted**. The skill
  still runs the test and Fizzy is still the enforcer (that's honest-mistake *non-bypassability*, not
  anti-attacker). Run artifacts **redact secrets before commit** — kept purely as *hygiene* (don't
  accidentally commit a secret), not as a defense.
- **The receipt is the `run_evidence` discriminated union (DR-1, US-4),** on an explicit `tier` field,
  hard-checked against the TMR's `verification_mode` (must agree). One variant per tier:
  - **`code`** (`automated-*` / `test-producer`): `{tier:"code", command, cwd, repo, commit, started_at,
    finished_at, exit, result, env, artifact_uri, artifact_sha256, runner, live_or_induced}` —
    `live_or_induced` lives **only** on this variant.
  - **`system-validation`** (a live scoped skill run on a fixture): `{tier:"system-validation",
    transcript_uri, transcript_sha256, model, model_settings, prompt_sha256, corpus_id, run_id, result,
    runner, captured_at}`.
  - **`judgment`** (golden-case LLM eval, US-5): `{tier:"judgment", golden_manifest_id,
    golden_manifest_sha256, model, model_settings, score, threshold, per_case_results, result, runner,
    captured_at}` — **`per_case_results`** so a golden-eval can't pass the aggregate `threshold` while
    silently missing the one critical planted defect.
  Exempt `verification_mode`s (`artifact-sync`/`static-check`/`manual-ux`) carry **no** receipt. A single
  flat `{result, env, commit, artifact}` could neither capture a non-code pass nor reproduce a fail — the
  tiered union can. **§3.1 declares the union (the schema); this section is its prose.**
- **env→"real pass" rule (DR-9 — a correctness rule, NOT a trust/security control).** For a **critical
  seam**, `run_evidence` must be `env: live` **OR** carry a recorded `live_or_induced` technique;
  `env: dev`/`ci` with no technique does **not** count as a real pass for a critical seam. Lower-criticality
  tiers accept `dev`/`ci`. (This is the small table §8.1 previously only referenced but never tabulated.)
- **Producer split — authoring vs execution, reconciled with SEC-4 (DD-4, R5-C2).** The skill's blast
  zone is **markdown phase-docs**; it does **not** author Python into arbitrary target repos. Split the
  two responsibilities cleanly so the SEC-4 "skill runs + captures the receipt" trust model is
  preserved:
  - **Authoring + binding = owner repo.** Phase-8 promotion **emits a typed `promotion_request`**
    `{tmr_uid, repo, accessors[], command, expected_evidence, negative_oracle}`; the **owner repo
    writes the executable test and binds the accessors** (the code-writing the skill won't do).
  - **Execution + receipt capture = the skill-runner / Fizzy-invoked checker (NOT the owner repo
    self-reporting).** The same skill-owned runner that SEC-4 names **executes the declared `command`**
    and **captures the typed `run_evidence` receipt** — it never trusts an owner-written `result:pass`.
    At sweep, Fizzy invokes that same skill checker/runner; the receipt is always captured by the
    skill-side runner, on either trigger.

  This removes the "phantom producer" (TC-11.0 wanted the skill pytested as code with no script
  defined) **without** moving execution-receipt capture off the skill/F′ contract — owner repo
  *authors/binds*, the skill-runner *executes and witnesses*.
- **Negative oracle required (DD-4).** A `promotion_request` for a critical seam **must** declare a
  **negative oracle** — the input/condition under which the test **fails** — so "green" can't be
  smoke-only (a test that passes against a dead boundary). Realization is not complete until both the
  positive and negative oracle are evidenced.
- **Accessor binding is a blocking dependency, not a footnote (DD-4).** Binding the spine's
  `accessors[]` (the `acceptance → concrete` flip, §4.4) is a **declared blocking dependency** on the
  owner repo — a `promotion_request` whose accessors are unbound **HALTS** the close (it does not slip
  through as an out-of-scope note).
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
- **Defined comparator — no string-sort ambiguity (US-8).** `liveness_contract_version ≥ tmr.v1` uses
  an **explicit numeric comparator**, not lexical string compare: the version is `tmr.v<N>` where `N`
  is a **base-10 integer compared numerically** (so `tmr.v10 > tmr.v2`, which a naive string sort gets
  wrong). There are **no prereleases** in this scheme (a malformed or non-`tmr.v<int>` value → a named
  `version_fence_error`, fail-closed as post-fence — §8.2 resolver), and **`null` / missing** is
  handled by the `ContractVersionResolver` read order above, never by the comparator. fizzy mirrors the
  same comparator on `verification_contract_version`.
- **`ContractVersionResolver` (REVISED R4-5; SEC-2, closes §12.4).** A single resolver with a defined read
  order decides fence status, anchored to an **immutable creation timestamp** vs a fixed `fence_cutover_ts` —
  NOT the editable marker alone. **Authoritative anchor = the server-side Fizzy session-card creation timestamp**
  (fetched via the Fizzy MCP) when a `fizzy_card_id` exists — it is **not locally editable**, so it genuinely
  defeats the `created_at`-edit downgrade (gemini R4). **Read order:** (1) `fizzy_card_id` present → use the Fizzy
  card timestamp; if the card exists but the timestamp is **unfetchable**, **fail closed as post-fence** + emit a
  named `version_fence_error` (never silently fall through to the editable local value); (2) cardless / legacy /
  local-only sessions → fall back to local `session-state.json` `created_at`, the **weaker, admin-editable tier**
  documented under the §8.1 trust model; missing/malformed → fail closed as post-fence. **A missing or lower
  `liveness_contract_version` on a session whose authoritative timestamp is ≥ `fence_cutover_ts` is POST-fence
  (fail-closed), not legacy** — deleting the marker cannot downgrade a new session to skip F′. A session is legacy
  **only** if the authoritative `created_at < fence_cutover_ts`. (Anchoring on the Fizzy timestamp is consistent
  with "Fizzy is the terminal auditor", SEC-1 — the fence leans on the same hard dependency.)
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

- **Semantic negative oracles required for the new infra components (R5-G3).** Per the test-adequacy
  rule, "imports and runs without crashing" is NOT adequate for the v6 fail-closed components — each
  must carry a **negative oracle that proves it fails CLOSED on incorrect semantics**, not just a happy
  path: **`SpineCoverageChecker`** (a US with zero / two `spine:true` designations → `block`, not pass);
  **`ConflictDispositionStore`** (a non-empty pending file → phase-advance REFUSED, and a kill+restart
  re-surfaces the conflict); **`CriticalityClassifier`** (an unclassified record → consumer REJECTS,
  never derives); **`ProvenanceJournalWriter`** (a stale `expected_from` → write REJECTED; a replayed
  `idempotency_key` → appended once); the **`GateResult` map** (a `schema_error`/`setup_error` is NOT `override_eligible`). A
  code-tier task for any of these is incomplete until its negative oracle exists.
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
- **Golden-case corpus is defined before judgment gates count (US-5).** The LLM-judgment tier is
  load-bearing (TC-3.1/6.0/7.1 depend on it) but unreproducible without a versioned corpus. Ship a
  **`golden_cases/manifest.json`** schema: **stable case IDs**, each case's **input fixture**,
  **expected findings** (the defect the guardrail must catch), **negatives** (clean inputs that must
  NOT trip a finding), **model + settings** (which model / temperature the judge runs at), a
  **pass threshold**, and **content hashes** of every fixture. A judgment gate (TRACE-finds-ORPHANED,
  TCOV-catches-falsifiable-MOCK) is **not "complete"** until its cases live in this manifest — so the
  eval is reproducible and versioned, not a one-off prompt.

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
| TMR emission → validation | skill (`tmr-registry.json` records, LLM-compiled from prose) | fizzy P0 validator | shared enum constants (field-for-field) | mismatch must be a **named rejection**, never silent |
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

1. ~~**Per-guardrail structured-finding schema (K output)**~~ **RESOLVED (DR-6):** each guardrail returns
   a typed finding `{guardrail, severity, join_key, finding_type, description, disposition}`;
   aggregation + conflict-detection is one deterministic pass over `join_key` (§5.1).
2. ~~**Parallel-subagent dispatch / orchestration spec**~~ **RESOLVED (DR-6):** guardrails run in parallel
   against **orchestrator-passed identical content** — no self-read, no frozen-manifest/hash snapshot
   (deleted, non-threat); leaf failure → `ORCH` fail-closed; a crashed orchestrator simply doesn't
   complete the round (§5.1).
3. **F′ deterministic parse** — ~~the roadmap-manifest US enumeration ↔ tests-pseudo spine-tag
   coupling~~ **RESOLVED R2 (codex):** F′ parses each test's structured `TMR:` block (§4.2) for
   `user_story`/`spine`/`maturity`, cross-referencing the roadmap manifest's canonical US IDs;
   markdown `[spine]` is display-only.
4. **Version-fence mechanism** — **RESOLVED (R4-5):** `ContractVersionResolver` anchored on the **immutable Fizzy
   session-card creation timestamp** (local `created_at` = editable fallback tier only) vs `fence_cutover_ts`; a
   missing marker on a post-cutover session = post-fence (fail-closed), defeating the created_at/marker downgrade.
   See §8.2. *(fizzy mirrors via `verification_contract_version`.)*
5. **Maturity-aware gate's exact phase → acceptable-maturity mapping** — confirm `nl`/`acceptance`
   pass at debate→gauntlet; `concrete` at Phase-8. *(largely resolved; confirm in R1.)*
6. **Golden-eval corpus** — **RESOLVED (v6, US-5):** a `golden_cases/manifest.json` schema (stable
   IDs, input fixtures, expected findings, negatives, model+settings, pass threshold, content hashes)
   defines where planted-defect fixtures live and gates "judgment-tier complete." See §9.
7. **Coordination handshake with the fizzy spec** — **RESOLVED (R4, release-blocking):** fizzy P0 lands the schema
   constants + checker `contract_version` first (or concurrently); both sides fail closed on an unrecognized
   field/enum/version; part of the **activation rule** (§1). Then prove the integrated Fizzy gate fails closed on
   missing F′ evidence, checker failure, invalid checker JSON, stale hashes, and direct `pipeline_advance`. *(§3.2.)*
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
11. **Test-ladder → `tmr-registry.json` migration (CB-6 + DD-1 + R4-4, gauntlet).** Post-DD-1, F′ parses the
    registry, not embedded markdown. The dogfood fixture needs a `tmr-registry.json` with a record (incl.
    `spine:true`) for all 15 `[spine]` tests (only TC-8.0 has a full block today) — produced via the R4-4 LLM
    compile step — plus the canonical prose-view regenerator + echo-diff for `tests-pseudo.md`. Until then F′ would
    not pass this draft. *(implementation fixture + compile/emission task.)*
12. **Remaining gauntlet accepts — FOLDED into v6** (NB: the **v9 post-gauntlet redesign supersedes
    several** — DR-6 deletes RC-3's pinned-snapshot manifest + FM-2's `N`-returned accounting; DR-5
    deletes SCA-1's `TestInputCollector`; DR-7 strips the security-framed items). RC-1 (`ProvenanceJournalWriter`), RC-2
    (persisted `ConflictDispositionStore`), RC-3 (pinned input-snapshot manifest), FM-1 (transient
    retry/backoff before ORCH), FM-2 (`N`-returned accounting), FM-4 (lint-not-delete + source-hash
    allowlist), FM-5 (semantic delta), SCA-1 (bounded `TestInputCollector` + manifest), SCA-2
    (journal retention/index), DD-2 (single-writer `CriticalityClassifier`), DD-3 (cited MOCK
    impossibility), DD-4 (`promotion_request` split + negative oracle), DD-5 (machine-readable schema
    SoR), DD-6 (one spine *designation* + linked tests), DD-7 (shared `SpineCoverageChecker`),
    DD-8 (tombstone/rename), DD-9 (`decision_id`
    join), US-2 (`GateResult`), US-3 (`acceptance` without façade), US-4 (tier-aware receipt +
    env-trust matrix), US-5 (golden corpus manifest),
    US-6 (typed-transition conflict + deterministic headless resolution), US-7 (strict typed
    coercion), US-8 (numeric version comparator). *(FM-3 / DD-1 / SEC-1..5 / US-1 + CB-1..7 were
    folded in v4–v5.)* Open
    only: **adversary leaderboard** + **final convergence round** before finalize.
13. **Authoring UX for `tmr-registry.json` (DD-1 follow-on).** **RESOLVED (R4, Jason):** **prose-authored +
    LLM-compiled** — the human authors prose in `tests-pseudo.md`; an LLM compile step emits **validated** records
    into the registry (system of record). Three mandatory guards keep the LLM compiler from re-introducing DD-1
    fragility: **validate-on-emit** (`TmrParser` field-for-field; malformed → `schema_error`, fail-closed),
    **round-trip echo** (regenerate prose, diff vs authored), **human confirm**. The registry — not the prose —
    remains the validated gate input. See §2/§4.2.

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
| US-7 | TCOV liveness guardrail (missing_liveness_test) + promoter | §5.3 | TC-7.0 |
| US-8 | Deterministic F′ gauntlet-entry gate | §6 | TC-8.0 |
| US-9 | Test-maturity provenance journal | §7.1 | TC-9.0 |
| US-10 | Altitude-triage provenance + altitude_fit | §7.2 | TC-10.0 |
| US-11 | Phase-8 pseudo→real promotion (RUN green) | §8.1 | TC-11.0 |
| US-12 | Version fence (no retroactive failure) | §8.2 | TC-12.0 |
| US-13 | Glossary / ADR / document-types | §10 | TC-13.0 |
| US-14 | Verification tiers (cross-cutting) | §9 | TC-14.0 |
| US-15 | Getting Started / bootstrap | §2 | TC-15.0 |

All 15 user stories have a corresponding spec section and a happy-path spine test. **Coverage caveat (CB-6 +
DD-1):** F′ parses each spine test's record from **`tmr-registry.json`** (§4.2), and the draft has a full record
only for the TC-8.0 exemplar — the other 14 spine tests exist as `[spine]`-tagged prose in `tests-pseudo.md` and
have **not yet been compiled into the registry**. **F′ would therefore NOT pass this draft as-is**; compiling a
registry record for every spine test (via the R4-4 LLM compile step) is a tracked remediation (§12 open item 11).


---

# APPENDIX: tests-pseudo.md (generated view; registry is SoR) — critique for v9-schema drift

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

### TC-1.3: the structured `TMR:` block converts field-for-field to the internal schema  (branch @ S2 — R3)
**Data Strategy: REAL-DATA** (tier: code — pytest) — parse a real `tests-pseudo` `TMR:` YAML block (the TC-8.0 exemplar) into the internal TMR record.
- given a test's structured `TMR:` block (all keystone keys incl. `title`, `source_spec`, `critical_seam`, `criticality_source`)
- when the parser converts it to the internal representation
- then every keystone field round-trips faithfully (no key dropped, no enum coerced); a block missing a required key or carrying an unknown key is rejected with a named error. (R3: gemini — the §4.2 block must parse field-for-field, not just "be present".)

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

### TC-8.0: full spine coverage passes the gate  [spine]
**Data Strategy: REAL-DATA** (tier: code — pytest) — real fixture roadmap manifest + tests-pseudo, full coverage.
**Spine steps:** S1 load roadmap US set → S2 parse each test's structured `TMR:` block → S3 every US has exactly one `spine:true` TMR at acceptable maturity → S4 pass.
**Exemplar `TMR:` block** (the structured form spec §4.2 requires; F′ parses THIS, not the markdown / `[spine]` tag):
```yaml
TMR:
  test_id: TC-8.0
  tmr_uid: 01J0EXEMPLARULID0000000000   # compiler-allocated ULID (DR-4); illustrative
  title: full happy-path-spine coverage passes the gate
  user_story: US-8
  maturity: nl
  spine: true
  spine_steps: [S1, S2, S3, S4]
  spine_step_ref: null
  data_strategy: REAL-DATA
  live_or_induced: {kind: natural-wait}   # R6-C7 tagged union (not the old scalar)
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
  status: active            # DR-3 lifecycle (default active)
  supersedes: null          # DR-3 rename/replace link
  run_evidence: null        # nl test — not yet run; no receipt (DR-1 union: receipt captured only on run)
  source_spec: adv-spec-202606151042-liveness-gate-test-ladder
```
*(R3: gemini — exemplar matches the canonical keystone Piece-1 field set including `title` + `source_spec`.)*
- given a fixture roadmap (US-1..US-3) and a tests-pseudo where each US has exactly one `spine:true` TMR block at `nl` or `acceptance`
- when the **F′ skill-side pre-check** runs before the Fizzy gauntlet-entry transition (PRIMARY; `enforce_pipeline_card_gate` is the standalone-fallback path and runs the identical check)
- then the gate passes (exit 0). (R2: parses the structured TMR block; skill-side placement is primary.)

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

<!-- P4_INVARIANT_TESTS_START -->
## Invariant Tests (Phase 4)

> Cross-cutting architectural-invariant tests derived from `architecture-invariants.json`
> (Phase 4, lightweight). These assert the **invariants hold across the system**, distinct from
> the per-feature TCs above. Per the semantic-oracle rule each carries a positive AND a
> negative/counterfactual assertion — a test that would still pass under the wrong behavior is
> smoke-only and does not satisfy the invariant.

### TC-INV-001: no gauntlet-entry path bypasses the F′ pre-check  (INV-001/002/003)
**Data Strategy: REAL-DATA** (tier: code — pytest) — enumerate every code path that transitions a post-fence session into the gauntlet.
- given the three enforcement layers (skill-side pre-check [PRIMARY], `enforce_pipeline_card_gate` [fallback], Fizzy sweep) and a post-fence session
- when a session is dispatched into the gauntlet **via Fizzy tools** (never invoking `debate.py` directly — the bypass that caused the originating incident)
- then full-spine coverage passes the PRIMARY skill-side pre-check (exit 0)
- assert (positive): a session with one spine:true TMR per US passes
- assert (negative): a session missing a spine is blocked at the skill-side pre-check **even though `enforce_pipeline_card_gate` was never reached** — a test that only exercises the `debate.py` path and passes is smoke-only

### TC-INV-004: schema divergence is always a named rejection, never a silent drop  (INV-004)
**Data Strategy: REAL-DATA** (tier: code — pytest) — round-trip TMRs through the parser/validator.
- given a TMR with all-canonical fields, and a sibling TMR carrying one unknown field / unknown enum member
- when the parser/validator runs
- then the canonical TMR round-trips with no key dropped and identity tuple unchanged
- assert (positive): every required key preserved; no enum coerced
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

### TC-INV-016: the version fence is non-retroactive  (INV-016)
**Data Strategy: REAL-DATA** (tier: code — pytest) — the SAME missing-spine input under two markers.
- given an identical missing-spine session shape evaluated once pre-fence and once post-fence
- when the F′ gate runs
- assert (positive): post-fence (`liveness_contract_version ≥ tmr.v1`) → exit 2
- assert (negative): pre-fence (same input) → NOT failed — the outcome flips on the version marker alone; a gate that fails the pre-fence session retroactively is wrong

### TC-INV-017: declared-but-never-run REAL-DATA critical-seam counts as failing  (INV-017)
**Data Strategy: REAL-DATA** (tier: code — pytest of close evaluation) — a critical-seam test at close.
- given a REAL-DATA / critical-seam / happy-path-spine test evaluated at implementation close
- when close is evaluated
- assert (positive): promoted + run-green (`run_evidence{result:pass}`) → close passes
- assert (negative): `run_evidence: null` → close **FAILS** (counts as failing), and the test may not be `spike`/exempt — a close that passes on null run_evidence is the exact liveness hole this spec exists to kill

### TC-INV-018: verification_mode is always canonical; no golden-eval member  (INV-018)
**Data Strategy: REAL-DATA** (tier: code — pytest + static-check lint) — parse execution-plan task records.
- given the execution plan's task records
- when the tier-lint runs
- assert (positive): every task's `verification_mode ∈ VALID_VERIFICATION_MODES`
- assert (negative): a task with `verification_mode: "golden-eval"` is rejected (no such enum member), and a code-seam task with an exempt mode (`artifact-sync`/`static-check`/`manual-ux`) is flagged — a lint that accepts golden-eval is smoke-only
<!-- P4_INVARIANT_TESTS_END -->

