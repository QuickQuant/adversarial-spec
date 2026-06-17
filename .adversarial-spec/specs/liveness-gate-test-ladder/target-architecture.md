---
schema_version: "1.0"
spec_slug: "liveness-gate-test-ladder"
phase_mode: "lightweight"
context_mode: "brownfield_feature"
framework: "Claude Code skill (prompt phase-docs) + Python 3.14 CLI (debate.py / adversaries.py / gauntlet)"
framework_version: "Python 3.14; in-repo skill (no external framework version)"
surfaces: ["cli_command", "background_job", "outbound_integration"]
roadmap_path: "specs/liveness-gate-test-ladder/roadmap/manifest.json"
tests_pseudo_path: "specs/liveness-gate-test-ladder/tests-pseudo.md"
architecture_fingerprint: "sha256:fcd7c0d1050feff6a6fa2014078b1edb10592fd4eb03279b28adb91cc35acf7a"
spec_fingerprint: "sha256:327f5f7acbf251d01af9571ca1ef56a8cadb40a680314331c378e52c1075bdae"
reconciled_at: "2026-06-17 (Phase-7 Step 2.5 reconcile-in-place, then validation-leg roadmap-manifest fix re-stamp; chain: input 302940c4(v3)->7b145aab(v12)->327f5f7a(manifest-fix); arch 5a4e6762->faae303b->fcd7c0d1)"
---

# Target Architecture — Liveness Gate + Architecture-Linked Test Ladder

> Phase 4 (lightweight, brownfield_feature). Originally derived from converged `spec-draft-v3.md`
> (Phase 3: codex AGREE + gemini test-completeness, 3 rounds). This doc extracts the
> **architectural invariants** the Gauntlet must stress-test and Phase 8 must verify; it
> does not restate the spec.
>
> **REVISED 2026-06-16 (CANON-r4-1, post `spec-draft-v6` fold):** INV-003 is **reframed**
> (SEC-1 — the mechanical non-bypassable gate is **Fizzy-side**; skill-side is advisory); INV-008
> is **lint-not-delete** (FM-4); INV-009 names the single-writer **`CriticalityClassifier`** (DD-2);
> INV-006 is a spine **designation** + shared **`SpineCoverageChecker`** (DD-6/DD-7); and
> **INV-019…INV-035** were added for the v6 components (see `architecture-invariants.json` — the
> machine-readable authority).
>
> **RECONCILED 2026-06-17 (Phase-7 Step 2.5, reconcile-in-place to finalized spec v12):** the v9
> post-gauntlet redesign deltas are now applied here. **INV-020 (FM-2 return-accounting), INV-022
> (RC-3 input-snapshot manifest), and INV-031 (SCA-1 TestInputCollector) are SUPERSEDED** (DR-6/DR-6/DR-5);
> **INV-001** override reason has no minimum length (DR-7); **INV-030** decisions.log stays plain text (DR-10).
> Active invariant count: **32** (35 minus 3 superseded). Both fingerprints recomputed (input/spec
> `7b145aab`, architecture `faae303b`); the old `input_fingerprint` was reproduced over `spec-draft-v3.md`
> to prove the algorithm. See `## Reconciliation` at the foot of this doc and the `reconciliation` blocks
> in `architecture-invariants.json` + `phase4_bootstrap`.

## Overview

This slice adds three load-bearing mechanisms to the **adversarial-spec skill itself**:
a non-bypassable **F′ happy-path-spine coverage gate** at gauntlet entry, a **strict-MOCK /
test-maturity ladder** with structured per-test records (TMR), and a **parallel-subagent
guardrail rearchitecture** whose findings feed an **append-only decision provenance journal**.
All of it is **version-fenced** (`liveness_contract_version = tmr.v1`) so in-flight sessions
are never retroactively failed.

The system under design is a **CLI + prompt-driven agent state machine**, not a web/API app.
Its "architecture" is the set of enforcement, validation, fail-closed, source-of-truth, and
provenance rules that keep a liveness hole (a critical seam specified-mocked-shipped but never
run live) from recurring. The keystone is a **shared TMR schema contract** co-owned with
`fizzy_pipeline_mcp` (separate coordinated spec); divergence of that contract is the exact
failure this work exists to prevent.

## Goals and Non-Goals (from roadmap manifest)

**Goals:** G-1 impossible to reach the gauntlet without a phase-appropriate happy-path spine
test per US · G-2 every MOCK names the live/induced technique or is promoted to REAL-DATA ·
G-3 structured, persisted, test/US-keyed guardrail output · G-4 durable decision provenance
journal (test-maturity + altitude-triage) · G-5 shared TMR schema contract, schema-first ·
G-6 classify every deliverable by verification tier · G-7 version-fence the new gates.

**Non-Goals:** NG-1 fizzy-side persistence/enforcement (separate spec) · NG-2 concept-accessor
façade/bindings/lint (target-repo) · NG-3 dogfooding on this session · NG-4 sessions-stats
dashboard · NG-5 backfilling provenance · NG-6 prediction-prime live-fill + fault-injection infra.

## Framework Profile

```json
{
  "profile_type": "single",
  "category": "cli",
  "framework": "Claude Code skill (prompt phase-docs) + Python 3.14 CLI",
  "framework_version": "Python 3.14; in-repo, no external framework",
  "runtime": "python",
  "deployment_target": "serverful",
  "enabled_features": ["fizzy-mcp-pipeline", "parallel-subagent-dispatch"],
  "subprofiles": {
    "rendering_model": "N/A",
    "data_access_model": "file artifacts (session-state.json, tests-pseudo.md, roadmap manifest, journal jsonl) + Fizzy MCP for pipeline state",
    "mutation_model": "CLI actions (debate.py critique|gauntlet) + Fizzy pipeline tool calls + atomic file writes",
    "cache_model": "N/A",
    "error_model": "process exit codes (exit 2 = gate block) + structured findings (ORCH/conflict) + named validation rejections"
  },
  "enforcement_model": "REFRAMED (SEC-1): the MECHANICAL non-bypassable gate is (1) Fizzy-side at gauntlet-entry — pipeline_advance refuses without valid F′ evidence and calls the skill's F′ checker contract [PRIMARY, HARD DEPENDENCY]; (2) skill-side pre-check + debate.py enforce_pipeline_card_gate() are ADVISORY fail-fast checks (a local pre-check cannot gate an out-of-process MCP call); (3) Fizzy sweep [persistence side]. Non-bypassability holds only after the coordinated Fizzy spec lands AND the activation-rule integration test passes.",
  "notes": "deployment_target 'serverful' = local Claude Code host / developer workstation. The prompt/doc 'agent-followed' surface (phase-doc behavior) is NOT a code execution surface; it is verified via the verification-tier model (system-validation live runs + fault-induced fixtures), per §9 of the spec. fizzy_pipeline_mcp is an external coordinated codebase reached via the TMR schema contract (outbound_integration), not part of this profile."
}
```

## Applicable Execution Surfaces

Category `cli` → category-native surfaces (no web surfaces apply: no auth/CSRF/caching/HTTP):

| surface_id | In-scope use in this slice |
|---|---|
| `cli_command` | `debate.py` actions (`critique`/`gauntlet`); F′ gate in `enforce_pipeline_card_gate()` / skill-side pre-check; override flags (`--accept-missing-spine` + `--spine-override-reason`); authoring lint; doc-lints |
| `background_job` | Parallel guardrail subagent dispatch + structured aggregation; append-only provenance journal writer |
| `outbound_integration` | TMR schema handshake with fizzy's validator (field-for-field enum constants); `run_evidence` block to fizzy sweep |

**Excluded surfaces (rationale):** `request_response`, `mutation_entrypoint`, `client_runtime`,
`webhook`, `realtime_streaming`, `scheduled_work`, `startup_migration`, `public_api`,
`data_stream` — N/A: no HTTP/UI/streaming/scheduling/library-export surface in this slice.

## Concern Assessments (in-scope only — lightweight)

In-scope concern categories: `enforcement`, `validation`, `error_handling`, `sot`,
`observability`, `config`, `integration`. Out of scope (N/A for a local dev skill, no untrusted
input/multitenancy/auth/caching): identity, security, caching.

### Enforcement (Concern 3) — the core of this slice
**Decision (REFRAMED — SEC-1):** The MECHANICAL, non-bypassable F′ gate is **Fizzy-side**:
`pipeline_advance` into the gauntlet lane **refuses unless valid F′ evidence is attached**, and Fizzy
**calls this skill's F′ checker contract** (`uv run gauntlet-check` / MCP tool) at transition time
(fail-closed on checker-not-found/timeout/invalid-JSON/schema-mismatch/unsupported `contract_version`/
stale evidence hash/exit 2|3|4). The **skill-side pre-check + `enforce_pipeline_card_gate` are ADVISORY
fail-fast checks** — a local pre-check cannot gate an out-of-process MCP call, so it is **not** the
non-bypassable layer. True non-bypassability is a **HARD DEPENDENCY** on the coordinated Fizzy spec
plus the **activation rule** (an integration test must prove a direct `pipeline_advance` fails closed
without F′ evidence). F′ still branches on `args.action`: **block (`exit 2`) on `gauntlet`, warn
(non-blocking) on `critique`**. **Surfaces:** `cli_command`, `outbound_integration`.
**Framework primitive:** process exit codes + the existing `enforce_pipeline_card_gate()` gate
chain (sibling to the tests-pseudo staleness gate). **Default status:** overridden — the existing
gate applies uniformly to both actions; F′ is the first check that must branch on action.
**Failure mode prevented:** reaching the gauntlet with a critical-seam happy path never proven
live (the originating incident). **Bypass rule:** only a logged `--accept-missing-spine` +
`--spine-override-reason '<≥50 chars>'` (stricter than the bare `--accept-tests-stale` flag),
written to `sessions/<id>.decisions.log`. **Invariant refs:** INV-001, INV-002, INV-003, INV-006.

### Validation (Concern 5)
**Decision:** TMR records validate **field-for-field against the canonical contract**; an
unrecognized field or enum member is a **named rejection, never a silent drop/accept**. Authoring
lint enforces **exactly one happy-path spine per US** and a valid `spine_step_ref` on every
failure test. MOCK falsification: a MOCK is sole evidence **only** when `live_or_induced: null`
AND no live/induced technique exists. **Surfaces:** `cli_command` (skill emit, authoring lint),
`outbound_integration` (fizzy validator). **Failure mode prevented:** schema drift between repos;
unanchored failure tests; convenience-MOCKs masquerading as impossibility.
**v6 additions:** cited MOCK impossibility / reject scale-cost-time excuses (DD-3), machine-readable
JSON-Schema SoR + known-bad-payload contract test (DD-5), strict typed coercion in `TmrParser` (US-7).
*(SUPERSEDED: bounded `TestInputCollector` (SCA-1) — DR-5 replaced TCOV source-ingestion with a metadata diff.)*
**Invariant refs:** INV-004, INV-005, INV-006, INV-007, INV-018, INV-026, INV-028. *(INV-031 superseded.)*

### Error Handling (Concern 4) — fail-closed everywhere
**Decision:** Three fail-closed rules. (a) A guardrail subagent that dies/times-out/returns
invalid JSON → synthetic **`ORCH`** finding, **blocking on `gauntlet`, warning on `critique`**;
never proceed on partial findings as if green. (b) `criticality_unknown` (`critical_seam: null` +
`criticality_source: unknown`) on a **system-altitude** happy path → treated as **critical** until
resolved; explicit vs architecture-derived disagreement → fail closed as critical + blocking
finding. (c) Conflicting findings (contradictory `required_action` on the same `target`+field) →
**`conflict`** state requiring disposition **before** any journaled transition.
**Surfaces:** `background_job` (aggregation), `cli_command`. **Failure mode prevented:** false
confidence from partial/ambiguous guardrail results — the failure class this spec exists to kill.
**v6 additions:** transient-retry-before-ORCH (FM-1), persisted `ConflictDispositionStore` (RC-2),
typed `GateResult` (US-2/FM-3), typed-transition conflict + deterministic headless resolution (US-6),
semantic-delta to subagents (FM-5). *(SUPERSEDED: orchestrator expected/received accounting (FM-2) —
DR-6 simplified to a serial/awaited fan-out that can't half-report green.)*
**Invariant refs:** INV-010, INV-011, INV-012, INV-019, INV-021, INV-024, INV-025, INV-035. *(INV-020 superseded.)*

### Source of Truth (Concern 6)
**Decision (REVISED — v6):** The TMR schema contract lives in **exactly one canonical file**
(`Brainquarters/shared-context/test-maturity-record-schema.md`), published as a **machine-readable
JSON Schema / Pydantic `extra='forbid'`** that is the source of truth (DD-5); the spec's prose enum
tables are **non-normative snapshots carrying `schema_sha256`**. **Referenced, never copied** — drift
is caught by a **lint that fails-first and names the copy, never auto-deletes** (FM-4); derived
artifacts are allowlisted by a `generated-from:<canonical-sha256>` header. **`tmr-registry.json` is the
local system of record (DD-1)**; `tests-pseudo.md` is a **generated prose VIEW**, never authoritative.
A single **`CriticalityClassifier`** is the **sole writer** of `critical_seam` + `criticality_source`
and the **only** reader of `architecture_link`; consumers read the normalized field and **reject an
unclassified record** rather than re-deriving (DD-2 — resolves the INV-009 paradox). **Surfaces:**
`outbound_integration`, `cli_command`. **Failure mode prevented:** the divergence-of-contract failure
(tests-pseudo drifting v2→v7 unchecked) + the auto-delete-real-artifacts hazard. **Invariant refs:**
INV-008, INV-009, INV-028.

### Observability (Concern 7) — the provenance journal
**Decision:** A **single append-only journal** over `subject_type ∈ {test, node}`: one record per
change to a tracked field, **derived from accepted STATE CHANGES** (guardrail findings are one
driver among many: `created`/`promotion`/`binding_status`/`run_evidence` journal even with no
finding behind them). A prior record is **never rewritten**; evolution is **not** stored inline on
the TMR. Node-altitude records require a close-time **`altitude_fit ∈ {right, too_high, too_low}`**
(stability alone over-counts a silently-wrong altitude). **Surfaces:** `background_job` (writer),
`cli_command` (queries). **Failure mode prevented:** unanswerable meta-analysis ("what did TCOV say
about TC-1.5 in R2"; "was this altitude actually right"). **v6 additions:** `ProvenanceJournalWriter`
locked atomic append + idempotency (RC-1), tombstone/rename over stable `tmr_uid` (DD-8),
**plain-text** `decisions.log` + `decision_id` join (DD-9 as revised by DR-10 — NOT JSONL),
bounded/indexed replay (SCA-2). **Invariant refs:**
INV-013, INV-014, INV-015, INV-023, INV-029, INV-030, INV-032.

### Configuration (Concern 9) — the version fence
**Decision:** `liveness_contract_version` (`tmr.v1`) gates every new requirement. Sessions started
**before** the fence keep their original rules (**no retroactive failure** of in-flight sessions
such as `validation-leg-process`). TMR fields are **optional + warn-first** until promoted to
required **behind the fence**. **v6 addition:** `ContractVersionResolver` anchored on the immutable
Fizzy session-card timestamp (defeats the marker-deletion downgrade) + numeric `tmr.v<N>` comparator
(SEC-2/US-8). **Surfaces:** `cli_command`. **Failure mode prevented:** breaking in-flight sessions by
tightening rules mid-stream; a trivial downgrade attack by deleting the marker. **Invariant refs:**
INV-016, INV-033.

### Integration / Delivery Semantics (Concern 11 — triggered: outbound + background)
**Decision:** The cross-repo TMR handshake is **schema-first** — fizzy P0 adds
`VALID_DATA_STRATEGIES`/`VALID_LIVENESS_TECHNIQUES`/`maturity`/`critical_seam`/`criticality_source`;
the skill's emission matches **field-for-field**; a mismatch is a **named rejection, never silent**.
Phase-8 delivery semantics: a REAL-DATA / critical-seam / happy-path-spine pseudo test
**declared-but-never-run counts as FAILING**; `run_evidence{result, env, commit, artifact}` is
required; such a test may **not** be a `spike` `test_strategy` nor an exempt `verification_mode`.
A blocked first-fill **HALTS downstream** (not parked). The journal's append-only shape gives safe
concurrent multi-agent writes (idempotent, via the `ProvenanceJournalWriter`, RC-1).
**v6 additions:** Phase-8 emits a typed `promotion_request` (skill ≠ producer of target-repo code) +
required negative oracle + accessor-binding-blocks-close (DD-4); skill RUNS the test + captures a
tier-aware typed receipt + env-trust-by-criticality matrix (SEC-4/US-4). **Surfaces:**
`outbound_integration`, `cli_command`. **Invariant refs:** INV-004, INV-017, INV-018, INV-027, INV-034.

## Concern × Surface Matrix (recommended for lightweight)

Columns are the category-native in-scope surfaces. Cells name **primitive · enforcement owner ·
bypass risk · invariant**.

| Concern | cli_command | background_job | outbound_integration |
|---|---|---|---|
| enforcement | F′ checker / GateResult exit map · skill pre-check **advisory** (SEC-1) · *advisory-only until Fizzy gate lands (activation rule)* · INV-001/002/003/024 | N/A | **Fizzy-side mechanical gate** at gauntlet-entry calls F′ checker (PRIMARY) + sweep enforces spine `concrete`+green · fizzy · INV-003/001 |
| validation | authoring lint + TMR emit · skill · *unanchored test slips if lint skipped* · INV-005/006 | N/A | field-for-field enum validate · fizzy validator · *silent drop* · INV-004/018 |
| error_handling | exit codes / blocking findings · debate.py · — · INV-011 | ORCH + conflict aggregation · orchestrator · *partial-green false confidence* · INV-010/012 | named rejection on mismatch · fizzy · INV-004 |
| sot | reads normalized critical_seam · consumers · *local re-derivation* · INV-009 | journal append (feeder) · writer · — · INV-013 | canonical contract referenced-not-copied · both repos · *copy drift* · INV-008 |
| observability | journey/altitude queries · skill · — · INV-014/015 | append-only journal writer · writer · *inline mutation* · INV-013 | run_evidence emission · skill→fizzy · — · INV-017 |
| config | version-fence read at gate · debate.py/skill · *retroactive failure* · INV-016 | N/A | verification_contract_version mirror · fizzy · INV-016 |
| integration | run_evidence drive · skill · *blocked-fill parked not halted* · INV-017 | N/A | schema handshake · both repos · *unrecognized field accepted* · INV-004 |

## Architectural Invariants (human-readable)

```
INV-001: [enforcement] Every post-fence session reaching the `gauntlet` action has exactly one
         spine:true TMR per roadmap user story at acceptable maturity (nl|acceptance|concrete);
         missing OR duplicate → exit 2. Bypass only via a logged override reason (non-empty,
         non-whitespace; NO minimum length — DR-7).
INV-002: [enforcement] F′ branches on action: block (exit 2) on `gauntlet`, warn (non-blocking)
         on `critique`. It is the first enforce_pipeline_card_gate check that branches on action.
INV-003: [enforcement] REFRAMED (SEC-1): the MECHANICAL non-bypassable F′ gate is FIZZY-SIDE —
         pipeline_advance into gauntlet refuses without valid F′ evidence and calls the skill's F′
         checker contract at transition time. Skill-side pre-check + enforce_pipeline_card_gate are
         ADVISORY. Non-bypassability is a HARD DEPENDENCY on the Fizzy spec + the activation rule.
INV-004: [validation] A TMR with an unrecognized field or enum member is rejected with a NAMED
         error citing the field — never silently dropped or accepted. Valid TMRs round-trip with
         no key dropped and the identity tuple session·user_story·test_id unchanged.
INV-005: [validation] Every failure/error test cites a valid spine_step_ref; an unanchored
         failure test is rejected at authoring ("branch off an unplanted trunk").
INV-006: [validation] Every user story declares exactly one happy-path spine DESIGNATION (≥1 AND ≤1
         spine:true); extra concrete tests link via spine_of (DD-6). One shared SpineCoverageChecker
         implements the rule, consumed by authoring-lint/F′/TRACE/TCOV — no re-implementation (DD-7).
INV-007: [validation] A MOCK is sole evidence ONLY when live_or_induced is null AND no live/induced
         technique exists; a MOCK naming a technique (or a dev-forceable condition) → reject,
         promote to REAL-DATA.
INV-008: [sot] The TMR schema contract exists in exactly one canonical file (machine-readable
         JSON-Schema SoR, DD-5), referenced never copied. Drift caught by a LINT that fails-first and
         NAMES the copy — NEVER auto-deletes (FM-4); derived artifacts allowlisted by source-hash
         header. tmr-registry.json is the system of record; tests-pseudo.md is a generated VIEW (DD-1).
INV-009: [sot] A single CriticalityClassifier is the SOLE writer of critical_seam/criticality_source
         and the ONLY reader of architecture_link; it does the disagreement check internally (DD-2).
         Consumers read only the normalized field and REJECT an unclassified record — never re-derive.
INV-010: [error_handling] A guardrail subagent that dies/times-out/returns invalid JSON yields a
         synthetic ORCH finding — blocking on gauntlet, warning on critique. Never proceed on
         partial findings as if green.
INV-011: [error_handling] criticality_unknown (critical_seam:null + criticality_source:unknown) on
         a system-altitude happy-path input is treated as CRITICAL until resolved; explicit vs
         architecture-derived disagreement → fail closed as critical + blocking finding.
INV-012: [error_handling] Conflicting findings (contradictory required_action on same target+field)
         enter a conflict state requiring disposition BEFORE any journaled transition.
INV-013: [observability] The provenance journal is append-only over subject_type ∈ {test, node}:
         every tracked-field change appends one record; a prior record is never rewritten; evolution
         is not stored inline on the TMR.
INV-014: [observability] The journal is derived from accepted STATE CHANGES, not guardrail findings
         alone — created/promotion/binding_status/run_evidence changes journal even with no finding.
INV-015: [observability] node altitude_fit (right|too_high|too_low) at close is required; altitude
         stability alone must not count a silently-wrong altitude as correct.
INV-016: [config] New gates/fields apply only to sessions at liveness_contract_version ≥ tmr.v1;
         pre-fence sessions keep their original rules (no retroactive failure). TMR fields are
         optional+warn-first until promoted to required behind the fence.
INV-017: [integration] A REAL-DATA / critical-seam / happy-path-spine pseudo test that is
         declared-but-never-run counts as FAILING; run_evidence{result,env,commit,artifact} is
         required; such a test may NOT be spike test_strategy nor an exempt verification_mode.
INV-018: [validation] verification_mode values are drawn ONLY from fizzy's canonical
         VALID_VERIFICATION_MODES — there is NO golden-eval member; the LLM-judgment tier uses
         system-validation with a golden-case corpus oracle defined by golden_cases/manifest.json
         (US-5). A code-seam task assigned an exempt mode (artifact-sync/static-check/manual-ux) is flagged.

# --- Added v6 (CANON-r4-1) — full detail in architecture-invariants.json ---
INV-019: [error_handling] FM-1: transient transport failure retried with bounded backoff before any
         ORCH; only a real guardrail failure → ORCH (no fail-closed self-DoS).
INV-020: [error_handling] SUPERSEDED (DR-6) — orchestrator expected/received return-accounting
         machinery removed. A serial/awaited fan-out cannot half-report a green; a crashed
         orchestrator simply does not complete the round (nothing writes a pass). Subagent death is
         covered by the leaf-ORCH rule (INV-010/INV-019).
INV-021: [error_handling] RC-2: pending conflict dispositions persisted to pending-dispositions.json
         (ConflictDispositionStore); main loop refuses to advance while non-empty; survives crash.
INV-022: [validation] SUPERSEDED (DR-6) — per-round pinned input-snapshot manifest + content_sha256
         self-reporting removed. Guardrails are read-only and receive orchestrator-passed identical
         bytes (not self-read live files), so there is no mixed-snapshot race. Residual "don't edit a
         session's files mid-round from another context" is operational guidance, not a gate (§0.3).
INV-023: [observability] RC-1: ProvenanceJournalWriter = locked atomic append + record_id +
         idempotency_key + expected_from; Fizzy is the single writer of the persisted journal.
INV-024: [error_handling] US-2/FM-3: every gate returns a typed GateResult {pass,warn,block,
         setup_error,schema_error,orch_error} + canonical outcome→exit map; schema/setup not overridable;
         a parse failure is schema_error, never coerced to "0 spines".
INV-025: [error_handling] US-6: conflict detection on a typed transition {subject,field,from,to,action}
         (cross-field); headless resolution via declared precedence + structured override; no deadlock.
INV-026: [validation] DD-3: justified MOCK carries a citable technical_constraint; scale/cost/time
         excuses rejected → promote; technique enum non-exhaustive; natural-wait scrutinized.
INV-027: [integration] DD-4: Phase-8 emits a typed promotion_request; executable realization is
         owner-repo/Fizzy; negative oracle required; unbound accessors HALT the close.
INV-028: [sot] DD-5: machine-readable JSON-Schema (extra=forbid) is SoR; prose tables = hashed
         non-normative snapshots; fizzy's strict rejection verified via a known-bad payload.
INV-029: [observability] DD-8: delete/supersede/split/merge/rename as tombstone records over a stable
         tmr_uid; a tombstoned TMR no longer satisfies F′.
INV-030: [observability] DD-9 (REVISED DR-10): decisions.log stays PLAIN TEXT (the live project
         convention; NOT JSONL) with a stable decision_id; an override-driven provenance-journal
         record cites the decision_id in its driver (durable bypass↔correction join across the two
         native-format artifacts — no JSONL migration).
INV-031: [validation] SUPERSEDED (DR-5) — TestInputCollector removed. TCOV coverage is now a
         deterministic metadata diff over each test's user_story link (SpineCoverageChecker, INV-006),
         not test-source ingestion; the LLM role shrinks to targeted per-test adequacy. SCA-1/SCA-3
         (token budget / over-budget setup_error) evaporate — no source-ingestion step to overflow.
INV-032: [observability] SCA-2: per-US journal replay reads a bounded/indexed store (rotation+index or
         SQLite rows), not a full-file scan.
INV-033: [config] SEC-2/US-8: ContractVersionResolver anchors the fence on the immutable Fizzy
         session-card timestamp (local created_at = editable fallback); unfetchable→fail-closed
         post-fence; numeric tmr.v<N> comparator (tmr.v10 > tmr.v2).
INV-034: [enforcement] SEC-4/US-4: Phase-8 RUNS the test + captures a tier-aware typed receipt (code/
         system-validation/judgment); never trusts hand-written result; env-trust scored by criticality
         (dev ≠ live for an external critical seam); mock-detection lint flags boundary mocks.
INV-035: [validation] FM-5: subagents receive a structured TMR semantic-delta {test_id,field,old,new}
         + the text diff (not raw diff alone) so join keys outside the hunk aren't dropped (CB-3).
```

Machine-readable form: `architecture-invariants.json`. Invariant-derived cross-cutting tests:
`tests-pseudo.md` § Invariant Tests (Phase 4), `TC-INV-001..018`.

## Middleware Candidates (advisory — lightweight)

Identified as genuinely reusable typed primitives; advisory only (does not block execution
planning). Full schema in `middleware-candidates.json`.

- **MW-001 TmrParser** — loads + validates **`tmr-registry.json`** records (DD-1 — JSON SoR, **not**
  embedded markdown YAML) field-for-field with **strict typed coercion** (rejects ambiguous scalars,
  US-7) → internal TMR record (unknown/missing key → named `schema_error`). The **only** TMR reader for
  F′, the five guardrails, and emission (no per-gate parsers — DD-7).
- **MW-002 SpineCoverageChecker** — pure function (roadmap US set + parsed TMRs) → pass | uncovered
  list | duplicate list (the ≥1∧≤1 **designation** rule, DD-6). Consumed by authoring-lint, F′, TRACE,
  and TCOV — no re-implementation (DD-7). Depends on MW-001.
- **MW-003 ProvenanceJournalWriter** — **locked atomic append** over subject_type ∈ {test, node} with
  record_id + idempotency_key + expected_from (RC-1); tombstone/rename over a stable tmr_uid (DD-8).
  Fizzy is the single writer of the persisted journal. Reused by guardrail aggregation, Phase-8
  promotion, depth-triage.
- **MW-004 CriticalityClassifier** — sole writer of `critical_seam`/`criticality_source`, only reader
  of `architecture_link`, runs before guardrails; does the disagreement check internally (DD-2).
- **MW-005 ConflictDispositionStore** — persists pending conflict dispositions (RC-2) keyed on a typed
  transition {subject,field,from,to,action} (US-6); phase-advance guard reads it; survives crash.
- **MW-006 GateResult** — the typed return of every gate (outcome + findings + override_eligible) with
  one canonical outcome→exit map (US-2/FM-3).
- **MW-007 ContractVersionResolver** — fence-status resolver anchored on the immutable Fizzy card
  timestamp, numeric `tmr.v<N>` comparator (SEC-2/US-8).
- ~~**MW-008 TestInputCollector**~~ — **SUPERSEDED (DR-5)**: TCOV no longer ingests test source; coverage
  is a deterministic metadata diff via MW-002 SpineCoverageChecker. No collector, no token budget, no
  over-budget `setup_error` (SCA-1/SCA-3 evaporate).

## Dry-run Summary

`lightweight` dry-run: one highest-risk archetype per applicable surface. Results recorded in
`dry-run-results.json` after draft approval (pre-publish). Highest-risk archetypes:
- `cli_command`: F′ gate on a missing-spine fixture must `exit 2` on `gauntlet`, warn on `critique` (INV-001/002).
- `background_job`: a 4/5-subagent round must emit ORCH and NOT complete green on `gauntlet` (INV-010).
- `outbound_integration`: a TMR with an unknown enum member must produce a named rejection (INV-004).

## Open Questions (carried from spec §12)

- ~~Coordination handshake: which repo lands the shared schema constants first~~ **RESOLVED (R4, §3.2):**
  fizzy P0 lands constants + checker `contract_version` first/concurrently; both sides fail closed on
  unrecognized field/enum/version; part of the activation rule.
- ~~Golden-eval corpus location + size~~ **RESOLVED (v6, US-5):** `golden_cases/manifest.json` schema
  (stable IDs, fixtures, expected findings, negatives, model+settings, threshold, hashes — INV-018).
- ~~Version-fence marker storage/read shape~~ **RESOLVED (R4-5/SEC-2, INV-033):** `ContractVersionResolver`
  anchored on the immutable Fizzy session-card timestamp; local `created_at` = editable fallback tier.
- **Still open:** Concept-accessor façade/binding ownership — out of skill scope, flagged unassigned
  (§12.8). v6 (US-3) defines `acceptance` *without* the façade, so it's an accelerator, not a blocker.

## Reconciliation (2026-06-17, Phase-7 Step 2.5 — reconcile-in-place)

Performed by the Phase-7 execution agent as a content patch (no model dispatch), per `07-execution.md`
Step 2.5 path (a). The target architecture was published at CANON-r4-1 (v6-era) but the spec finalized at
**v12**; the v9 post-gauntlet redesign changed the invariant set. Deltas applied:

| Invariant / artifact | Before | After | Driver |
|---|---|---|---|
| INV-001 | override reason ≥50 chars | no minimum length (non-empty, non-whitespace) | DR-7 |
| INV-020 | active (orchestrator expected/received accounting) | **superseded** (serial/awaited fan-out can't half-report green) | DR-6 |
| INV-022 | active (per-round input-snapshot manifest + content_sha256) | **superseded** (orchestrator-passed identical bytes; no mixed-snapshot race) | DR-6 |
| INV-030 | structured decisions.log JSONL | plain text + decision_id join via journal driver | DR-10 |
| INV-031 + MW-008 | active (TestInputCollector + token budget) | **superseded** (TCOV coverage = metadata diff via SpineCoverageChecker; SCA-1/SCA-3 evaporate) | DR-5 |
| input/spec fingerprint | `sha256:302940c4` (v3-era) | `sha256:7b145aab` (over finalized spec.md) | recompute |
| architecture fingerprint | `sha256:5a4e6762` (v3-era composite) | `sha256:faae303b` (forward recompute; basis in bootstrap reconciliation block) | recompute |

Active invariants: **32** (of 35; INV-020/022/031 superseded, retained for lineage). The old
`input_fingerprint` was reproduced over `spec-draft-v3.md` to prove the algorithm before recomputing.
Dry-run archetypes re-traced (they reference INV-001/002/010/004 — none superseded; conclusions
unchanged). Machine-readable authority: `architecture-invariants.json` (`reconciliation` block);
fingerprint chain recorded in `phase4_bootstrap.reconciliation`.
