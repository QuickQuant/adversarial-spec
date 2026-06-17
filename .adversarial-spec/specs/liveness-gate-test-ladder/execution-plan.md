# Execution Plan: Liveness Gate + Architecture-Linked Test Ladder (skill slice)

> **STATUS: APPROVED 2026-06-17 (Phase 7 Step 7).** Gates V1/V2/V3/V4 satisfied (0 exempt tasks, 0 unmapped behavior tasks). Next: validation leg (system altitude) → Step 9 emit (fizzy-plan.json) → pipeline_load.
>
> Session: adv-spec-202606151042-liveness-gate-test-ladder | Card 5715 | spec.md (finalized v12)
> Inputs: spec.md, tests-spec.md, gauntlet-concerns-2026-06-16.json (24 accepted/ack), architecture-invariants.json (32 active, reconciled v12), target-architecture.md (reconciled 2026-06-17), middleware-candidates.json
> Architecture fingerprints (post-reconcile): input/spec `7b145aab`, architecture `faae303b`. Staleness: PASS.

## Summary
- **Tasks:** 22 (S: 4, M: 13, L: 5) across 6 waves / 6 workstreams
- **Gauntlet concerns addressed:** 24 of 24 accepted/acknowledged (several already folded into v12; tasks carry the failure-modes as acceptance criteria). Cross-repo/external concerns listed under "Uncovered / external".
- **Active invariants:** 32/32 referenced by ≥1 task (coverage check below).
- **Recommendation:** multi-agent (Claude + Codex parallel on this board). Wave 0 shared contracts block the feature waves; sequence Wave 0 first.

## Altitude / emission note (resolve before Step 9)
`session_altitude` is **undeclared** on card 5715 (`session_altitude_source: "undeclared"`), but `altitude_at_debate_start = "system"`, the spec header declares **system** altitude, and the operator `next_action` directs the **system-altitude validation leg**. Decomposition below is emission-schema-agnostic. Two items to confirm at Step 9:
1. **Validation leg** (derive-conops → draft rows → normalize → check-rows) — runs because the session is system-altitude in intent; drafted before `pipeline_load`, committed with the plan.
2. **Emission schema** — v2 flat (`plan_schema_version: 2`, Step 9) vs v3 altitude tree (`plan_schema_version: 3`, Step 9b, SYS root + per-node `verification_binding`). Default lean: **v2 flat**, since `session_altitude` was never formally set; revisit if the operator wants the altitude tree.

---

## Architecture Spine
Cross-cutting patterns from the Target Architecture + finalized spec. **All tasks must follow.**

### S1 — One shared `TmrParser` (DD-7)
- **Pattern:** a single `TmrParser` is the ONLY component that loads/validates `tmr-registry.json` records.
- **Rule:** F′, the five guardrails, and emission MUST consume `TmrParser` — never write a per-gate parser. Unknown/missing key → named `schema_error` (never coerced to "0 spines").
- **Reference:** spec §4.2, INV-004; Task W0-2.

### S2 — One shared `SpineCoverageChecker` (DD-6/DD-7)
- **Pattern:** the "≥1 ∧ ≤1 happy-path-spine **designation** per US" rule is implemented once.
- **Rule:** authoring-lint (warn), F′ (block), TRACE (ORPHANED), TCOV (promote) all consume it — no re-implemented coverage logic. Counts only scalar `user_story` of `active`, `spine:true` records; ignores `also_covers[]`.
- **Reference:** spec §4.1/§6, INV-006; Task W0-4.

### S3 — Typed `GateResult` + one exit map (US-2)
- **Pattern:** every gate (F′ checker, staleness gate, ORCH aggregator) returns one typed `GateResult` `{outcome ∈ {pass,warn,block,setup_error,schema_error,orch_error}, findings[], override_eligible}`.
- **Rule:** one canonical `outcome → exit code` map (0/2/3/4/5) and `outcome → MCP error`. `outcome` is the only normative outcome field (no separate `result`). `schema_error`/`setup_error` are NOT override-eligible.
- **Reference:** spec §5.1/§6, INV-024; Task W0-3.

### S4 — Fail-closed everywhere
- **Rule:** partial guardrail results never read as green (synthetic ORCH); `criticality_unknown` on system altitude treated as critical; conflicts block phase-advance until disposed; transient transport failure is retried with bounded backoff BEFORE any ORCH (no self-DoS).
- **Reference:** INV-010/011/012/019; Tasks W2-1, W0-6, W1-4.

### S5 — `tmr-registry.json` is the system of record (DD-1)
- **Rule:** F′ and guardrails parse the **registry**, never embedded markdown YAML. `tests-pseudo.md` is a generated prose VIEW. The `[spine]` tag / `TMR:` blocks are display aids only.
- **Reference:** spec §3/§4.2/§6; Tasks W0-2, W3-2.

### S6 — Keystone schema referenced-not-copied; JSON-Schema is SoR (INV-008/DD-5)
- **Rule:** the TMR contract lives in ONE canonical file (`Brainquarters/shared-context/test-maturity-record-schema.md`), published as a JSON Schema (`extra: forbid`). Prose tables are hashed non-normative snapshots. Drift caught by a LINT that fails-first and NAMES the copy — never auto-deletes (FM-4); derived artifacts allowlisted by `generated-from:<sha256>` header.
- **Reference:** spec §3, INV-008/028; Task W0-1.

### S7 — Version-fenced; skill advisory, Fizzy mechanical (INV-016/003, SEC-1)
- **Rule:** new gates/fields apply only at `liveness_contract_version ≥ tmr.v1`; pre-fence sessions keep original rules. The skill-side F′ is an **advisory** fail-fast check; the **mechanical non-bypassable** gate is **Fizzy-side** (a HARD DEPENDENCY — see "Uncovered / external"). The word "mechanical" is reserved for the Fizzy gate.
- **Reference:** spec §1/§6/§8.2, INV-003/016/033; Tasks W1-1, W1-2, W1-3.

---

## Tasks

### Wave 0 — Foundation (shared contracts/middleware; blocks all feature waves)

#### W0-1: Keystone TMR JSON Schema (extra:forbid) + run_evidence union + schema_sha256 + contract test
- **US:** US-1 · **Effort:** M · **Test Strategy:** test-first · **Wave:** 0 · **Depends:** none
- **Surfaces:** outbound_integration, cli_command
- **Description:** Extend the canonical `test-maturity-record-schema.md` to the v12 field set (add `status` enum, `supersedes` array, required/optional partition) AND publish it as a machine-readable **JSON Schema (`extra: forbid`)** that is the source of truth (DD-5). Declare the `run_evidence` discriminated union (`code` / `system-validation` / `judgment` variants, DR-1) and the `live_or_induced` strict union (JSON null XOR tagged object, R6-C7). Regenerate the §3.1 `schema_sha256` snapshot and pin it. Add a **known-bad-payload contract test** proving fizzy *rejects* an unknown field + bad enum (not silently ignores).
- **Acceptance criteria:**
  - [ ] Canonical schema defines every Always-required + Optional + Conditionally-required field per spec §3.1 (incl. `tmr_uid`, `status`, `supersedes[]`, `tombstoned_at`, `critical_seam`, `criticality_source`).
  - [ ] JSON Schema with `extra: forbid` (Pydantic `extra='forbid'`); prose tables carry the current `schema_sha256`; CI fails on snapshot-hash drift.
  - [ ] [CB-2] `run_evidence` is a discriminated union on `tier`; `tier` hard-checked against `verification_mode` (compat map, not equality).
  - [ ] [CB-3/R6-C7] `live_or_induced` accepts JSON `null` XOR `{kind,detail?}` with non-null `kind`; `{kind:null}`/`{"kind":"null"}`/`{kind:"other"}`(no detail) rejected.
  - [ ] [INV-008/FM-4] a drift lint **fails-first and names** an unallowlisted copy — never `rm`s; `generated-from:<sha256>` header allowlists derived artifacts.
  - [ ] [DD-5] known-bad payload (unknown field + bad enum) is **rejected with a named error**, asserted by a contract test.
- **Concerns:** CB-1 (status/tombstone), CB-2 (run_evidence union), CB-8 (canonical SoR residue), FM-4 (lint-not-delete), DD-5
- **Invariants:** INV-004, INV-008, INV-028 · **Surfaces:** outbound_integration, cli_command
- **behavior_change:** true · **verification_mode:** automated-contract · **verification_scope:** targeted
- **architecture_refs:** `.architecture/structured/components/emission-toolchain.md`, `.architecture/structured/cross-references.md`, `.architecture/primer.md`
- **implementation_status:** partial · **evidence:** `Brainquarters/shared-context/test-maturity-record-schema.md` exists (262 L; 19 hits for tmr_uid/live_or_induced/critical_seam/maturity) — extend to v12 + add JSON-Schema artifact (greenfield sub-part: no `*.schema.json` yet).
- **test_refs:** TC-1.0, TC-1.1, TC-1.2, TC-1.3, TC-1.4, TC-INV-004, TC-INV-008
- **test_files:** `skills/adversarial-spec/scripts/tests/test_tmr_schema_contract.py`
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_tmr_schema_contract.py -q`
- **notes:** Schema-first: fizzy P0 must add VALID_TMR_STATUS/VALID_DATA_STRATEGIES/VALID_LIVENESS_TECHNIQUES field-for-field (handshake = activation rule). schema_sha256 is a tracked finalize/impl value, computed here.

#### W0-2: `TmrParser` — shared registry reader/validator, strict typed coercion, named schema_error
- **US:** US-1, US-7 · **Effort:** M · **Test Strategy:** test-first · **Wave:** 0 · **Depends:** W0-1
- **Description:** Implement the single `TmrParser` (MW-001) that loads + validates `tmr-registry.json` field-for-field against the keystone JSON Schema. Strict typed coercion — reject (never coerce) ambiguous scalars (`"null"`/`"~"`/`"None"`, `"true"`/`"yes"`/`1` for booleans), unknown/missing keys, **duplicate JSON keys** (dup-preserving parse, CB-6), and **duplicate `tmr_uid`** → named `schema_error` (fail-closed, FM-3). The ONLY TMR reader for F′, guardrails, emission (DD-7).
- **Acceptance criteria:**
  - [ ] Valid registry record round-trips with no key dropped; identity keys on immutable `tmr_uid`.
  - [ ] Unknown key / missing required key / bad enum / ambiguous scalar → named `schema_error` citing the field (never coerced to "0 spines").
  - [ ] [CB-6] duplicate JSON keys are detected via a dup-preserving parse (not silently last-wins).
  - [ ] [US-7] string `"null"` where JSON `null` is meant is rejected (preserves `criticality_unknown` fail-closed).
  - [ ] No other module parses TMRs (grep: single reader).
- **Concerns:** CB-6 (dup keys), CB-7 (uid uniqueness), US-7 (coercion), US-4 (ID hygiene — ack low)
- **Invariants:** INV-004 · **Surfaces:** cli_command, outbound_integration
- **behavior_change:** true · **verification_mode:** automated-unit · **verification_scope:** targeted
- **architecture_refs:** `.architecture/structured/components/debate-engine.md`, `.architecture/structured/components/session.md`, `.architecture/primer.md`
- **implementation_status:** greenfield · **evidence:** `grep -rIl TmrParser scripts/` → 0; `tmr-registry` → 0 files. No implementer.
- **test_refs:** TC-1.0, TC-1.3, TC-1.4, TC-INV-004 · **test_files:** `skills/adversarial-spec/scripts/tests/test_tmr_parser.py`
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_tmr_parser.py -q`

#### W0-3: `GateResult` model + canonical outcome→exit map
- **US:** US-2 · **Effort:** S · **Test Strategy:** test-first · **Wave:** 0 · **Depends:** none
- **Description:** Implement the typed `GateResult` (MW-006): `{outcome ∈ {pass,warn,block,setup_error,schema_error,orch_error}, findings[], override_eligible}` + one canonical `outcome → exit code` map (0/2/3/4/5 per tests-spec) and `outcome → MCP structured-error`. `override_eligible` set by the gate (coverage block → true; schema/setup → false).
- **Acceptance criteria:**
  - [ ] One mapping function `outcome → exit`; pass=0, block=2, schema_error=3, orch_error=4, setup_error=5; `warn` exits 0 with findings.
  - [ ] `outcome` is the only normative outcome field (no `result` on the envelope).
  - [ ] `schema_error`/`setup_error` are NOT `override_eligible`; coverage `block` is.
- **Concerns:** US-2 (GateResult), FM-1 (setup_error not conflated)
- **Invariants:** INV-024 · **Surfaces:** cli_command
- **behavior_change:** true · **verification_mode:** automated-unit · **verification_scope:** targeted
- **architecture_refs:** `.architecture/structured/components/debate-engine.md`, `.architecture/primer.md`
- **implementation_status:** greenfield · **evidence:** `grep GateResult scripts/` → 0.
- **test_refs:** TC-INV-018 (exit-map indirectly), TC-8.0/8.1 (consume) · **test_files:** `skills/adversarial-spec/scripts/tests/test_gate_result.py`
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_gate_result.py -q`
- **notes:** Negative oracle (R5-G3): `schema_error`/`setup_error` must NOT be override_eligible.

#### W0-4: `SpineCoverageChecker` — ≥1∧≤1 designation rule
- **US:** US-8 · **Effort:** M · **Test Strategy:** test-first · **Wave:** 0 · **Depends:** W0-2
- **Description:** Implement the shared `SpineCoverageChecker` (MW-002): pure function `(roadmap US set, parsed TMRs, phase) → pass | uncovered[] | duplicate[]`. Counts only scalar `user_story` of `active`, `spine:true` records; ignores `also_covers[]`. Consumed by authoring-lint, F′, TRACE, TCOV (no re-implementation).
- **Acceptance criteria:**
  - [ ] Full coverage → pass; a US with 0 → uncovered; a US with 2 active spine:true → duplicate.
  - [ ] `status: tombstoned` records are inert (never counted).
  - [ ] `also_covers[]` does NOT satisfy coverage for a secondary US.
  - [ ] Negative oracle (R5-G3): a US with zero/two designations → block (not pass).
- **Concerns:** DD-6 (designation), DD-7 (shared checker)
- **Invariants:** INV-006 · **Surfaces:** cli_command
- **behavior_change:** true · **verification_mode:** automated-unit · **verification_scope:** targeted
- **architecture_refs:** `.architecture/structured/components/debate-engine.md`, `.architecture/primer.md`
- **implementation_status:** greenfield · **evidence:** `grep SpineCoverageChecker scripts/` → 0.
- **test_refs:** TC-8.0, TC-8.4, TC-INV-001 · **test_files:** `skills/adversarial-spec/scripts/tests/test_spine_coverage_checker.py`
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_spine_coverage_checker.py -q`

#### W0-5: `ProvenanceJournalWriter` — locked atomic append + idempotency + expected_from + tombstone/rename
- **US:** US-9 · **Effort:** L · **Test Strategy:** test-first · **Wave:** 0 · **Depends:** none (uses W0-2 record shapes)
- **Description:** Implement the append-only provenance journal writer (MW-003) over `subject_type ∈ {test, node}`. Locked atomic append (`O_APPEND` under `filelock`), `record_id` + `idempotency_key` (retry de-dup) + `expected_from` optimistic check (stale write reject). Tombstone/rename over the stable `tmr_uid` (DD-8): rename keeps `tmr_uid`; replace/split/merge mints new + sets `supersedes[]`. Atomic "update registry + append journal" (RC-3). Bounded/indexed replay (rotation+index or SQLite, SCA-2). Registry/decisions.log/pending-dispositions get locking too (RC-2). The skill writes the session-live journal; **Fizzy is the single writer** of the persisted `.architecture/tests/registry.journal.jsonl` (RC-1).
- **Acceptance criteria:**
  - [ ] [INV-013] append-only: two field changes → two records; prior record byte-range unchanged (no in-place edit API).
  - [ ] [INV-014] journals on accepted state changes (created/promotion/binding_status/run_evidence) even with no guardrail finding behind them.
  - [ ] [RC-1] a replayed `idempotency_key` appends once; a stale `expected_from` is rejected.
  - [ ] [RC-3] registry update + journal append are atomic (no orphaned journal entry on crash).
  - [ ] [DD-8/INV-029] rename keeps `tmr_uid` (emits rename event); replace/split/merge tombstones + sets `supersedes[]`; a tombstoned TMR no longer satisfies F′.
  - [ ] [SCA-2/INV-032] per-US/per-subject replay reads an index, not a full-file scan.
  - [ ] [INV-030] a plain-text decisions.log `decision_id` joins to an override-driven journal record's `driver` (decisions.log stays plain text — DR-10).
- **Concerns:** RC-1, RC-2, RC-3, SCA-2, DD-8, DD-9 (DD-2 decisions.log conflict resolved by DR-10)
- **Invariants:** INV-013, INV-014, INV-023, INV-029, INV-030, INV-032 · **Surfaces:** background_job, cli_command
- **behavior_change:** true · **verification_mode:** automated-unit · **verification_scope:** targeted
- **architecture_refs:** `.architecture/structured/components/session.md`, `.architecture/structured/components/gauntlet.md` (persistence/FileLock pattern), `.architecture/structured/flows.md`
- **implementation_status:** greenfield · **evidence:** `grep ProvenanceJournalWriter scripts/` → 0. (FileLock/atomic-write pattern exists in `gauntlet/persistence.py` — reuse the pattern, not the module.)
- **test_refs:** TC-9.0, TC-9.1, TC-INV-013 · **test_files:** `skills/adversarial-spec/scripts/tests/test_provenance_journal.py`
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_provenance_journal.py -q`

#### W0-6: `CriticalityClassifier` — sole writer of critical_seam/criticality_source
- **US:** US-7 · **Effort:** M · **Test Strategy:** test-first · **Wave:** 0 · **Depends:** W0-2
- **Description:** Implement `CriticalityClassifier` (MW-004): the SOLE writer of `critical_seam`+`criticality_source` and the ONLY reader of `architecture_link`. Runs once before guardrails; performs the explicit-vs-architecture disagreement check internally (the one allowed re-derivation). `criticality_unknown` (`critical_seam:null` + `criticality_source:unknown`) on a system-altitude happy path → treated as **critical** until resolved; disagreement → fail closed as critical + blocking finding. Consumers reject an unclassified record (INV-009 paradox resolution, DD-2).
- **Acceptance criteria:**
  - [ ] [INV-009] only this component reads `architecture_link`; consumers read the normalized `critical_seam` and reject an unclassified record (grep: no other re-derivation).
  - [ ] [INV-011] `criticality_unknown` on system altitude → critical; explicit vs architecture-derived disagreement → critical + blocking finding.
  - [ ] Negative oracle (R5-G3): an unclassified record → consumer REJECTS, never derives.
- **Concerns:** DD-2 (single-writer)
- **Invariants:** INV-009, INV-011 · **Surfaces:** cli_command, background_job
- **behavior_change:** true · **verification_mode:** automated-unit · **verification_scope:** targeted
- **architecture_refs:** `.architecture/structured/components/debate-engine.md`, `.architecture/structured/cross-references.md`, `.architecture/primer.md`
- **implementation_status:** greenfield · **evidence:** `grep CriticalityClassifier scripts/` → 0.
- **test_refs:** TC-7.2, TC-INV-009 · **test_files:** `skills/adversarial-spec/scripts/tests/test_criticality_classifier.py`
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_criticality_classifier.py -q`

### Wave 1 — Gates & enforcement

#### W1-1: F′ checker `gauntlet-check` CLI + MCP contract + console script
- **US:** US-8 · **Effort:** L · **Test Strategy:** test-first · **Wave:** 1 · **Depends:** W0-2, W0-3, W0-4
- **Description:** Implement the normative F′ checker contract (spec §6 R4-2) as an executable: `uv run gauntlet-check --session <dir> --roadmap-manifest <path> --tmr-registry <path> --action gauntlet --output json`, exposed as a **new console script** in `pyproject.toml` (OP-2). Emits the canonical `GateResult` envelope `{contract_version, outcome, checked_at, session_id, roadmap_manifest_sha256, tmr_registry_sha256, findings, override_eligible, evidence_id}`. Uses `TmrParser` + `SpineCoverageChecker`; never reimplements either. Exit map per W0-3. Path canonical-root check on checker inputs (SEC-5 partial).
- **Acceptance criteria:**
  - [ ] [INV-001] full coverage → exit 0 `pass`; uncovered US → exit 2 naming the US; duplicate spine → exit 2.
  - [ ] [INV-002] branches on action: block on `gauntlet`, warn (exit 0) on `critique`.
  - [ ] [US-8] maturity-aware: an `nl` spine passes at debate→gauntlet (does NOT demand `concrete`).
  - [ ] `schema_error` → exit 3 (not overridable); `setup_error` (missing manifest/registry) → exit 5 (not overridable).
  - [ ] Output JSON matches the canonical `GateResult` envelope; `outcome` is the only outcome field.
  - [ ] [OP-2] `gauntlet-check` is a real console_script in `pyproject.toml` (`[project.scripts]`).
  - [ ] Override: `--accept-missing-spine` + `--spine-override-reason` (non-empty, non-ws; no min length) writes to `decisions.log`.
- **Concerns:** OP-2 (entry point), US-2 (checker-vs-liveness contract), US-3 (phase source), SEC-5 (path canonical-root), SEC-6 (override floor — ack)
- **Invariants:** INV-001, INV-002, INV-003 · **Surfaces:** cli_command, outbound_integration
- **behavior_change:** true · **verification_mode:** automated-integration · **verification_scope:** targeted
- **architecture_refs:** `.architecture/structured/components/debate-engine.md`, `.architecture/structured/components/emission-toolchain.md`, `.architecture/structured/flows.md`
- **implementation_status:** greenfield · **evidence:** `pyproject.toml [project.scripts]` has only `adversarial-spec` (no `gauntlet-check`); no checker module.
- **test_refs:** TC-8.0, TC-8.1, TC-8.2, TC-8.3, TC-8.4, TC-INV-001 · **test_files:** `skills/adversarial-spec/scripts/tests/test_gauntlet_check_cli.py`
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_gauntlet_check_cli.py -q`
- **notes:** This DEFINES the contract Fizzy invokes; the mechanical non-bypassable gate is Fizzy-side (see Uncovered/external). The skill never embeds Fizzy logic.

#### W1-2: F′ integration into `debate.py enforce_pipeline_card_gate` (branch on action)
- **US:** US-8 · **Effort:** M · **Test Strategy:** test-first · **Wave:** 1 · **Depends:** W1-1
- **Description:** Wire the advisory skill-side F′ check into `enforce_pipeline_card_gate()` as a **sibling to the tests-pseudo staleness gate**, the first check that **branches on `args.action`** — block (exit 2) on `gauntlet`, warn on `critique`. `--accept-tests-stale` does NOT bypass F′ (separate `--accept-missing-spine` override → `decisions.log`). Advisory only — not the non-bypassable layer.
- **Acceptance criteria:**
  - [ ] [INV-002] same missing-spine fixture: exit 2 for `gauntlet`, warn for `critique`.
  - [ ] F′ runs as a sibling gate (does not regress the existing pipeline-card / staleness gates).
  - [ ] `--accept-missing-spine` + reason logged to `decisions.log`; `--accept-tests-stale` does not bypass F′.
- **Concerns:** US-8 (placement), SEC-1 (advisory framing)
- **Invariants:** INV-002, INV-030 (override→decisions.log) · **Surfaces:** cli_command
- **behavior_change:** true · **verification_mode:** automated-integration · **verification_scope:** targeted
- **architecture_refs:** `.architecture/structured/components/debate-engine.md`, `.architecture/structured/flows.md`
- **implementation_status:** partial · **evidence:** `debate.py:1351 def enforce_pipeline_card_gate`; `:1370 round_actions = {"critique","gauntlet"}` (applies uniformly today — F′ must add the action branch).
- **test_refs:** TC-8.3, TC-INV-001 · **test_files:** `skills/adversarial-spec/scripts/tests/test_fprime_gate_integration.py`
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_fprime_gate_integration.py -q`

#### W1-3: `ContractVersionResolver` + version fence
- **US:** US-12 · **Effort:** M · **Test Strategy:** test-first · **Wave:** 1 · **Depends:** W0-3
- **Description:** Implement `ContractVersionResolver` (MW-007): fence-status resolver with a defined read order anchored on the **immutable Fizzy session-card creation timestamp** vs `fence_cutover_ts` (local `created_at` = editable fallback tier). Numeric `tmr.v<N>` comparator (`tmr.v10 > tmr.v2`). Card present but timestamp unfetchable → fail-closed post-fence + `version_fence_error`. Missing/lower marker on a post-cutover session = post-fence (defeats the marker-deletion downgrade).
- **Acceptance criteria:**
  - [ ] [INV-016] legacy (`created_at < fence_cutover_ts`) → original rules (no retroactive failure); same input post-fence → new F′ applies (exit 2).
  - [ ] [INV-033] outcome flips on the immutable `created_at` vs `fence_cutover_ts`, NOT the editable local marker.
  - [ ] numeric comparator: `tmr.v10 > tmr.v2`; malformed `tmr.v<int>` → `version_fence_error` fail-closed post-fence.
  - [ ] timestamp unfetchable → fail-closed post-fence + `version_fence_error`.
- **Concerns:** SEC-2 (marker downgrade), FM-2 (Fizzy outage = fence outage — fail-closed by design; offline-DoS tradeoff acknowledged), US-8 (numeric comparator)
- **Invariants:** INV-016, INV-033 · **Surfaces:** cli_command
- **behavior_change:** true · **verification_mode:** automated-unit · **verification_scope:** targeted
- **architecture_refs:** `.architecture/structured/components/session.md`, `.architecture/structured/components/debate-engine.md`, `.architecture/primer.md`
- **implementation_status:** greenfield · **evidence:** `grep ContractVersionResolver scripts/` → 0.
- **test_refs:** TC-12.0, TC-12.1, TC-INV-016 · **test_files:** `skills/adversarial-spec/scripts/tests/test_contract_version_resolver.py`
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_contract_version_resolver.py -q`

#### W1-4: `ConflictDispositionStore` — persisted pending dispositions
- **US:** US-6 · **Effort:** M · **Test Strategy:** test-first · **Wave:** 1 · **Depends:** W0-5
- **Description:** Implement `ConflictDispositionStore` (MW-005): persists pending conflict dispositions to a discrete `pending-dispositions.json` keyed on a typed transition `{subject,field,from,to,action}` (US-6). Main loop refuses to advance a phase while non-empty; survives crash/restart (re-reads pending). Headless deterministic resolution via declared precedence + structured machine justification (no deadlock, no silent winner).
- **Acceptance criteria:**
  - [ ] [INV-012] contradictory `required_action` on same target+field → `conflict` state before any journaled transition.
  - [ ] [INV-021/RC-2] pending file non-empty → phase-advance REFUSED; kill+restart re-surfaces the conflict (no silent fail-open).
  - [ ] [INV-025/US-6] conflict detection on typed transition (cross-field, e.g. promote vs delete); headless precedence resolution records `{decision_id, resolution, precedence_rule, winning/losing_transition}`.
  - [ ] Negative oracle (R5-G3): a non-empty pending file → phase-advance REFUSED, and a kill+restart re-surfaces it.
- **Concerns:** RC-2 (persisted store), US-6 (typed transition + headless resolution)
- **Invariants:** INV-012, INV-021, INV-025 · **Surfaces:** cli_command, background_job
- **behavior_change:** true · **verification_mode:** automated-unit · **verification_scope:** targeted
- **architecture_refs:** `.architecture/structured/components/session.md`, `.architecture/structured/flows.md`, `.architecture/primer.md`
- **implementation_status:** greenfield · **evidence:** `grep ConflictDispositionStore scripts/` → 0.
- **test_refs:** TC-5.3 · **test_files:** `skills/adversarial-spec/scripts/tests/test_conflict_disposition_store.py`
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_conflict_disposition_store.py -q`

#### W1-5: Verification-tier lint + `golden_cases/manifest.json` corpus & schema
- **US:** US-14, US-5 · **Effort:** M · **Test Strategy:** test-first · **Wave:** 1 · **Depends:** W0-3
- **Description:** (a) Ship the `golden_cases/manifest.json` schema (stable case IDs, input fixture, expected findings, negatives, model+settings, pass threshold, content hashes) — the reproducible oracle for the LLM-judgment tier (US-5). (b) Implement the verification-tier lint: every execution-plan task declares a tier (code/prompt-doc/llm-judgment) driving a consistent `verification_mode`; a code-seam task assigned an exempt mode is flagged; no `golden-eval` member exists in `VALID_VERIFICATION_MODES` (judgment uses `system-validation` + golden corpus).
- **Acceptance criteria:**
  - [ ] [US-5] `golden_cases/manifest.json` schema with stable IDs, fixtures, expected findings, negatives, model+settings, threshold, content hashes.
  - [ ] [INV-018] every task `verification_mode ∈ VALID_VERIFICATION_MODES`; `golden-eval` rejected (no such member); code-seam + exempt mode → flagged.
  - [ ] `judgment` gates (TRACE-finds-ORPHANED, TCOV-catches-MOCK) are "complete" only when their cases live in the manifest.
- **Concerns:** US-5 (golden corpus), (supports US-6/US-7 judgment gates)
- **Invariants:** INV-018 · **Surfaces:** cli_command
- **behavior_change:** true · **verification_mode:** automated-unit · **verification_scope:** targeted
- **architecture_refs:** `.architecture/structured/components/adversaries.md`, `.architecture/structured/components/gauntlet.md`, `.architecture/primer.md`
- **implementation_status:** greenfield · **evidence:** `grep golden_cases skills/adversarial-spec/` → 0.
- **test_refs:** TC-14.0, TC-14.1, TC-INV-018 · **test_files:** `skills/adversarial-spec/scripts/tests/test_verification_tier_lint.py`
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_verification_tier_lint.py -q`

### Wave 2 — Guardrail rearchitecture

#### W2-1: Parallel-subagent dispatch + structured findings + aggregation + ORCH fail-closed + retry
- **US:** US-5 · **Effort:** L · **Test Strategy:** test-first · **Wave:** 2 · **Depends:** W0-5, W1-4, W0-3
- **Description:** Rearchitect the five guardrails (CONS/SCOPE/TRACE/CANON/TCOV) to run as **separate parallel subagents** (never one combined prompt), each self-contained (persona + orchestrator-passed identical content + the round diff + a TMR **semantic delta** `{test_id,field,old,new}`). Subagents do NOT self-read live files (no snapshot/hash protocol — DR-6). Aggregate N structured findings (keyed to test/US IDs); join keys required only on TMR-changing findings (spec/contract findings carry `target.spec_section`/`target.contract`). Subagent death/timeout/invalid-JSON → synthetic `ORCH` (block on gauntlet, warn on critique); transient transport error retried with bounded backoff BEFORE any ORCH (FM-1). Drives fix/approve/dismiss + writes per-round provenance (via W0-5). Updates `phases/03-debate.md` invocation contract.
- **Acceptance criteria:**
  - [ ] [US-5] five separate structured result sets, each finding keyed to a test/US id, aggregated+persisted per round (never one combined prompt).
  - [ ] [INV-035/FM-5] subagents receive the TMR semantic-delta + text diff (join keys outside the hunk not dropped).
  - [ ] [INV-010] one subagent fails → synthetic ORCH, round does NOT complete green on gauntlet (4/5 ≠ pass).
  - [ ] [INV-019/FM-1] transient 429/timeout retried with bounded backoff before ORCH (no self-DoS).
  - [ ] join keys scoped to TMR-changing findings (R2/CB-3); spec/contract findings accepted but journaled only if they change a TMR/node field.
  - [ ] Negative oracle (R5-G3 / TC-INV-010): 4/5 returns → ORCH, not green.
- **Concerns:** DD-1 (§12.1 resolved), FM-1 (transient retry), FM-3/FM-5 (semantic delta), SCA-1 (retry budget), SEC-2 (prompt injection — echo/confirm at compile, semantic check here), SEC-4 (snapshot self-attestation — superseded DR-6)
- **Invariants:** INV-010, INV-019, INV-035 · **Surfaces:** background_job, cli_command
- **behavior_change:** true · **verification_mode:** automated-integration · **verification_scope:** targeted
- **architecture_refs:** `.architecture/structured/components/adversaries.md`, `.architecture/structured/components/models.md`, `.architecture/structured/components/debate-engine.md`, `.architecture/structured/flows.md`
- **implementation_status:** partial · **evidence:** `adversaries.py` GUARDRAILS personas exist (`REQUIREMENTS_TRACER:1174`, `TEST_COVERAGE_AUDITOR:1284`); current dispatch is not parallel-subagent + structured. `03-debate.md` invocation contract exists.
- **test_refs:** TC-5.0, TC-5.1, TC-5.2, TC-5.3, TC-INV-010 · **test_files:** `skills/adversarial-spec/scripts/tests/test_guardrail_orchestration.py`
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_guardrail_orchestration.py -q`
- **notes:** Conflict-state handoff to W1-4 (ConflictDispositionStore); journal writes via W0-5.

#### W2-2: TRACE spine-inversion (ORPHANED)
- **US:** US-6 · **Effort:** M · **Test Strategy:** test-first · **Wave:** 2 · **Depends:** W0-4, W1-5, W2-1
- **Description:** Invert TRACE specifically for the happy-path spine: a journey with prose but no spine test = `ORPHANED` (traceability break), not a test suggestion. The general no-test-suggestions rule still holds for non-spine. TRACE also absorbs the dropped SPINE guardrail's semantic check (is the labeled spine actually the primary success path). Edit `adversaries.py` REQUIREMENTS_TRACER + `reference/guardrail-prompts.md`. Verified judgment-tier via golden corpus.
- **Acceptance criteria:**
  - [ ] [§5.2] US with prose but no spine → ORPHANED.
  - [ ] non-spine missing edge test → NOT flagged (false-positive guard, TC-6.1).
  - [ ] uses `SpineCoverageChecker` (no re-implemented coverage logic).
- **Concerns:** (US-6 inversion) — folded; supports OP-3 early surfacing
- **Invariants:** INV-006 (consumes checker) · **Surfaces:** background_job
- **behavior_change:** true · **verification_mode:** system-validation · **verification_scope:** end-to-end
- **architecture_refs:** `.architecture/structured/components/adversaries.md`, `.architecture/structured/components/prompts.md`
- **implementation_status:** partial · **evidence:** `adversaries.py:1174 REQUIREMENTS_TRACER` exists; `reference/guardrail-prompts.md` exists.
- **test_refs:** TC-6.0, TC-6.1 · **test_files:** `golden_cases/manifest.json` (trace-orphaned cases); `skills/adversarial-spec/scripts/tests/test_trace_golden.py`
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_trace_golden.py -q`
- **notes:** Judgment-tier: corpus from W1-5; non-exempt (system-validation, not a relabeled exempt mode).

#### W2-3: TCOV liveness guardrail (`missing_liveness_test`) + promoter + data_strategy_mismatch
- **US:** US-7 · **Effort:** L · **Test Strategy:** test-first · **Wave:** 2 · **Depends:** W0-2, W0-4, W0-6, W1-5
- **Description:** Re-center TCOV (DR-5 morph): primary deliverable `missing_liveness_test` — a critical seam whose happy-path input has no REAL/induced test (mock-only) is a **blocking** finding. Coverage is a **deterministic metadata diff** over each test's `user_story` link (via `SpineCoverageChecker`) — NOT test-source ingestion (TestInputCollector deleted). LLM role shrinks to targeted per-test adequacy (real oracle / not smoke / not secretly mocked). Secondary: the promoter (`PROMOTE nl→acceptance` when accessors named; `BLOCK` when unnamed — CB-5 guard: ≥1 named accessor) and `data_strategy_mismatch`. Edit `adversaries.py` TEST_COVERAGE_AUDITOR + `guardrail-prompts.md`.
- **Acceptance criteria:**
  - [ ] [§5.3] critical seam with real/induced test → no `missing_liveness_test` (TC-7.0); mock-only critical seam → blocking `missing_liveness_test` (TC-7.1 LIV-POS); non-critical mock-only → not flagged (LIV-NEG).
  - [ ] [INV-011] `criticality_unknown` on system altitude → treated critical (consumes `CriticalityClassifier`, no re-derivation).
  - [ ] [CB-5] promoter requires ≥1 named accessor (empty `accessors` does NOT auto-promote).
  - [ ] coverage is a metadata diff (no test-source ingestion; no TestInputCollector resurrected — DR-5).
- **Concerns:** SCA-1/SCA-3 (evaporate via DR-5), DD-3 (data_strategy), CB-5
- **Invariants:** INV-011 · **Surfaces:** background_job, cli_command
- **behavior_change:** true · **verification_mode:** automated-unit · **verification_scope:** targeted
- **architecture_refs:** `.architecture/structured/components/adversaries.md`, `.architecture/structured/components/prompts.md`, `.architecture/structured/cross-references.md`
- **implementation_status:** partial · **evidence:** `adversaries.py:1284 TEST_COVERAGE_AUDITOR` exists; DR-5 deleted TestInputCollector (never built — `grep` 0).
- **test_refs:** TC-7.0, TC-7.1, TC-7.2, TC-4.0, TC-4.1 (promoter) · **test_files:** `skills/adversarial-spec/scripts/tests/test_tcov_liveness.py`; `golden_cases/manifest.json` (LIV cases)
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_tcov_liveness.py -q`
- **notes:** TC-7.1 is judgment-tier (golden corpus, W1-5); TC-7.0/7.2/4.x are code-tier.

#### W2-4: Strict MOCK falsification (PEDA/BURN/AUDT + 03-debate)
- **US:** US-3 · **Effort:** M · **Test Strategy:** test-first · **Wave:** 2 · **Depends:** W0-2, W1-5
- **Description:** Implement the strict MOCK rule (spec §4.3): a justified MOCK must deny that ANY listed or constructible technique could induce the behavior — naming a technique proves inducibility → **promote to REAL-DATA**. Keys on real-ness not the label (DR-8): applies to every non-REAL `data_strategy` for a critical seam. Justified MOCK carries a cited `technical_constraint` (DD-3); scale/cost/time excuses rejected → promote; `natural-wait` scrutinized vs clock-stub. Mirror into `adversaries.py` PEDA/BURN/AUDT prompt text + `phases/03-debate.md` MOCK-falsification directive (~line 404).
- **Acceptance criteria:**
  - [ ] [INV-007] MOCK is sole evidence ONLY when `live_or_induced: null` AND no technique exists; naming a technique → reject/promote (TC-3.1).
  - [ ] [DR-8] critical seam + non-REAL `data_strategy` with empty `why_impossible_to_reproduce_live` → rejected/promote (TC-3.2; not just literal MOCK).
  - [ ] [INV-026/DD-3] justified MOCK carries a non-empty `technical_constraint`; scale/cost/time excuses rejected (TC-3.0 asserts BOTH `why_impossible…` AND `technical_constraint`).
- **Concerns:** CB-3 (REAL vs MOCK), CB-4 (all non-REAL), DD-3 (cited impossibility)
- **Invariants:** INV-007, INV-026 · **Surfaces:** background_job, cli_command
- **behavior_change:** true · **verification_mode:** automated-unit · **verification_scope:** targeted
- **architecture_refs:** `.architecture/structured/components/adversaries.md`, `.architecture/structured/components/prompts.md`
- **implementation_status:** partial · **evidence:** PEDA/BURN/AUDT personas in `adversaries.py`; `03-debate.md` MOCK directive ~line 404.
- **test_refs:** TC-3.0, TC-3.1, TC-3.2 · **test_files:** `skills/adversarial-spec/scripts/tests/test_mock_falsification.py`; `golden_cases/manifest.json` (TC-3.1)
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_mock_falsification.py -q`
- **notes:** TC-3.1 judgment-tier (golden corpus); TC-3.0/3.2 code/doc-tier.

### Wave 3 — Authoring & maturity

#### W3-1: Happy-path spine + maturity ladder authoring (phases 01/02 + document-types)
- **US:** US-2, US-4 · **Effort:** M · **Test Strategy:** test-first · **Wave:** 3 · **Depends:** W0-4
- **Description:** Add the happy-path-spine authoring model + maturity ladder to the phase docs: every US declares exactly one spine designation (TC-0, named steps S1…Sn); failure tests cite `spine_step_ref` (unanchored → rejected). One designation, many concrete tests via `spine_of`. The maturity ladder (`nl`→`acceptance`→`concrete`); `acceptance` defined WITHOUT the façade (US-3). Authoring lint (uses `SpineCoverageChecker`). Edit `phases/01-init-and-requirements.md`, `phases/02-roadmap.md` (§9/§9a), `reference/document-types.md` (TMR row format).
- **Acceptance criteria:**
  - [ ] [INV-005] failure test with no `spine_step_ref` → rejected at authoring ("branch off an unplanted trunk", TC-2.1).
  - [ ] [INV-006] authoring lint confirms exactly one spine per US (consumes `SpineCoverageChecker`).
  - [ ] [US-4] maturity ladder documented; `acceptance` has executable meaning without the façade; `nl` with all-named accessors → `PROMOTE` (≥1 accessor; empty does not auto-promote).
  - [ ] [TC-2.2] a live scoped skill run on a 2-US fixture produces exactly one spine per US.
- **Concerns:** CB-8 (generated view), DD-6 (designation)
- **Invariants:** INV-005, INV-006 · **Surfaces:** cli_command
- **behavior_change:** true · **verification_mode:** system-validation · **verification_scope:** end-to-end
- **architecture_refs:** `.architecture/structured/components/debate-engine.md`, `.architecture/primer.md`
- **implementation_status:** partial · **evidence:** `phases/01-init-and-requirements.md`, `phases/02-roadmap.md`, `reference/document-types.md` exist.
- **test_refs:** TC-2.0, TC-2.1, TC-2.2, TC-4.0, TC-4.1 · **test_files:** `skills/adversarial-spec/scripts/tests/test_authoring_lint.py` (TC-2.0/2.1 doc-lint as pytest); system-validation run for TC-2.2
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_authoring_lint.py -q`
- **notes:** Spine TC-2.0 realized as automated doc-lint + a system-validation live run (TC-2.2) — non-exempt (spine may not be exempt, §8.1).

#### W3-2: LLM compile step (prose→registry) + prose-view regen + echo-diff + `tmr_uid` ULID allocation
- **US:** US-1 · **Effort:** L · **Test Strategy:** test-first · **Wave:** 3 · **Depends:** W0-1, W0-2, W0-5
- **Description:** Implement the R4-4 authoring compile step: human authors prose in `tests-pseudo.md`; an LLM compile step emits **validated** records into `tmr-registry.json` (validate-on-emit via `TmrParser`; malformed → `schema_error`, fail-closed); regenerate the canonical prose VIEW + surface an **echo-diff** (explicit semantic diff) for human confirm before commit. The compiler **mints** the `tmr_uid` ULID on first emit (LLM never allocates); writes it to record + prose anchor; diffs on `tmr_uid` (rename detected as rename, DD-8); rejects duplicate `tmr_uid`/anchor. Cite-resolve accessor symbols (FM-5). Echo+confirm mitigates prompt-injection (SEC-2).
- **Acceptance criteria:**
  - [ ] [CB-7/DR-4] compiler mints a 26-char ULID `tmr_uid` on first emit; LLM never allocates; duplicate `tmr_uid`/anchor → `schema_error`.
  - [ ] validate-on-emit (`TmrParser`); malformed → `schema_error` fail-closed (FM-3).
  - [ ] prose-view regenerated from registry; echo-diff surfaced as an explicit semantic diff (not a blind rubber-stamp); human confirm gate.
  - [ ] [DD-8] a prose rename (`TC-0 → TC-8.0`) diffs on `tmr_uid` → rename event, not delete+add.
  - [ ] [FM-5/SEC-2] compile cite-resolves accessor symbols; echo+confirm is the backstop.
- **Concerns:** CB-7 (uid allocation), FM-5 (semantic-wrong records), SEC-2 (injection), CB-8 (generated view)
- **Invariants:** INV-029 (rename/tombstone), INV-004 (validate-on-emit) · **Surfaces:** cli_command, background_job
- **behavior_change:** true · **verification_mode:** automated-unit · **verification_scope:** targeted
- **architecture_refs:** `.architecture/structured/components/debate-engine.md`, `.architecture/structured/components/emission-toolchain.md`, `.architecture/structured/components/session.md`
- **implementation_status:** greenfield · **evidence:** no compile step; `tmr-registry` 0 hits.
- **test_refs:** TC-1.0 (round-trip), TC-1.3, TC-INV-004 · **test_files:** `skills/adversarial-spec/scripts/tests/test_tmr_compile_step.py`
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_tmr_compile_step.py -q`

### Wave 4 — Phase-8 promotion & provenance

#### W4-1: Phase-8 pseudo→real promotion — promotion_request, run_evidence capture, negative oracle, mock-lint, DR-9 matrix
- **US:** US-11 · **Effort:** L · **Test Strategy:** test-first · **Wave:** 4 · **Depends:** W0-1, W0-2, W0-6
- **Description:** Add a Phase-8 promotion pass (edit `phases/08-implementation.md`, `phases/07-execution.md`): each REAL-DATA/critical-seam/happy-path-spine pseudo test is written real, RUN, required green against its tier. **Producer split (DD-4):** the skill emits a typed `promotion_request{tmr_uid, repo, accessors[], command, expected_evidence, negative_oracle}`; the owner repo authors/binds; the **skill-runner executes the declared command and captures the typed `run_evidence` receipt** (never trusts an owner-written `result:pass`). DR-9 env→real-pass matrix applied at close. Negative oracle required for critical seams (DD-4). Best-effort mock-detection lint (AST flag, not hard-block). Unbound accessors HALT close. Declared-but-never-run REAL-DATA critical-seam = FAILING.
- **Acceptance criteria:**
  - [ ] [INV-017] declared-but-never-run REAL-DATA critical-seam → counts as FAILING (close fails on `run_evidence: null`, TC-11.1); spine/critical-seam may not be `spike`/exempt.
  - [ ] [INV-027/DD-4] emits typed `promotion_request`; owner repo authors/binds; negative oracle required; unbound accessors HALT close.
  - [ ] [INV-034/SEC-4] skill-runner RUNS the test + captures the tier receipt; never trusts hand-written `result:pass`; mock-detection lint flags a boundary mock.
  - [ ] [CB-5/DR-9] env→real-pass matrix enforced (dev/ci needs a recorded technique for a critical seam; `null` → not a real pass).
  - [ ] Negative oracle (TC-INV-017): close that passes on null `run_evidence` is the exact hole this closes — must FAIL.
- **Concerns:** US-1 (negative oracle), CB-5 (env-trust matrix), DD-4 (producer split/negative oracle), SEC-1 (skill-runner executes — non-bypassability is Fizzy-side)
- **Invariants:** INV-017, INV-027, INV-034 · **Surfaces:** cli_command, outbound_integration
- **behavior_change:** true · **verification_mode:** automated-integration · **verification_scope:** targeted
- **architecture_refs:** `.architecture/structured/components/debate-engine.md`, `.architecture/structured/components/gauntlet.md`, `.architecture/structured/flows.md`
- **implementation_status:** partial · **evidence:** `phases/08-implementation.md`, `phases/07-execution.md` exist; `run_evidence` capture + `promotion_request` greenfield (0 hits).
- **test_refs:** TC-11.0, TC-11.1, TC-INV-017 · **test_files:** `skills/adversarial-spec/scripts/tests/test_phase8_promotion.py`
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_phase8_promotion.py -q`
- **notes:** Owner-repo code-authoring + command sandboxing are out of skill scope (SEC-1/SEC-3 → Uncovered/external). The skill-runner executing the declared command is the skill's responsibility.

#### W4-3: Altitude-triage provenance + altitude_fit (skill side)
- **US:** US-10 · **Effort:** M · **Test Strategy:** test-after · **Wave:** 4 · **Depends:** W0-5
- **Description:** Skill-side: the Phase-7 depth-triage step (`07-execution.md`) contributes the initial node altitude + blast-radius rationale (`created` journal record). Consume/query the node-altitude journal for meta-analysis (altitude distribution, subsystem triage precision, 3×3 confusion matrix). Close-time `altitude_fit ∈ {right, too_high, too_low}` (driver `close_attestation`). NOTE: the node-altitude journaling + close `altitude_fit` *enforcement* is fizzy-side (emit at `pipeline.py:6263`); the skill emits/queries.
- **Acceptance criteria:**
  - [ ] [INV-015] `altitude_fit: right` counts correct in the distribution; `altitude_fit: too_low` on a stable node → NOT counted correct (stability alone over-counts).
  - [ ] node journal records `created` @ depth-triage with initial altitude + rationale.
  - [ ] meta-analysis queries (distribution histogram, subsystem precision) answer over `subject_type: node`.
- **Concerns:** (US-10 provenance) — folded
- **Invariants:** INV-015 · **Surfaces:** cli_command, background_job
- **behavior_change:** true · **verification_mode:** automated-unit · **verification_scope:** targeted
- **architecture_refs:** `.architecture/structured/components/session.md`, `.architecture/structured/flows.md`, `.architecture/primer.md`
- **implementation_status:** partial · **evidence:** depth-triage altitude exists in `07-execution.md` flow; node journaling consumes W0-5 (skill side) — fizzy-side journaling/enforcement is external.
- **test_refs:** TC-10.0, TC-10.1, TC-INV-015 · **test_files:** `skills/adversarial-spec/scripts/tests/test_altitude_provenance.py`
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_altitude_provenance.py -q`

### Wave 5 — Docs, dogfood, integration

#### W5-1: Glossary / ADR / document-types (happy-path-spine collision)
- **US:** US-13 · **Effort:** S · **Test Strategy:** test-after · **Wave:** 5 · **Depends:** none (doc-only)
- **Description:** Add `CONTEXT.md` entries for **happy-path spine**, **TMR**, **maturity ladder**, **liveness**; resolve the "Architecture Spine" collision (test concept is "happy-path spine" — always qualified in prose; machine tokens `spine`/`spine_steps`/`spine_step_ref`/`[spine]` exempt). Update `reference/document-types.md` `tests-pseudo.md` row to the extended TMR row. New ADR recording the test-ladder/TMR/liveness decision + the two-spec cross-project scope split.
- **Acceptance criteria:**
  - [ ] [TC-13.0] "happy-path spine", TMR, maturity ladder, liveness defined; "happy-path spine" always qualified in PROSE (never bare "spine"); machine tokens exempt; ADR records the decision + two-spec split.
- **Concerns:** CB-8 (canonical SoR doc), DD-6 (editorial)
- **Invariants:** (vocabulary; no new code invariant) · **Surfaces:** cli_command (doc-lint)
- **behavior_change:** false · **verification_mode:** automated-unit · **verification_scope:** targeted
- **architecture_refs:** `.architecture/INDEX.md`, `.architecture/primer.md`
- **implementation_status:** partial · **evidence:** `CONTEXT.md`, `reference/document-types.md` exist; new ADR greenfield.
- **test_refs:** TC-13.0 · **test_files:** `skills/adversarial-spec/scripts/tests/test_glossary_doclint.py`
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_glossary_doclint.py -q`
- **notes:** TC-13.0 spine realized as an automated doc-lint pytest (grep assertions) — non-exempt, satisfying §8.1's "spine may not be exempt".

#### W5-2: Getting Started bootstrap (no copy-deploy; symlink note)
- **US:** US-15 · **Effort:** M · **Test Strategy:** test-first · **Wave:** 5 · **Depends:** W1-1, W3-1
- **Description:** Author the §2 Getting Started bootstrap (likely a new `reference/getting-started-liveness-gate.md` + SKILL/phase pointer): post-fence first-run path (author one spine/US → compile → authoring lint → attempt gauntlet → observe pass/exit-2), run the F′ gate against full-coverage + missing-spine fixtures. Must state the deployed skill is a **symlink** (edits live, no copy) and contain NO prescriptive `cp -r … ~/.claude/skills` step (a negative warning is allowed).
- **Acceptance criteria:**
  - [ ] [TC-15.0] following the documented bootstrap reaches a passing spine gate (full coverage) AND a blocking `exit 2` (missing-spine fixture) without reading the implementation.
  - [ ] [TC-15.1] docs state symlink (edits live, no copy); no AFFIRMATIVE `cp -r … ~/.claude/skills` instruction (negative warning allowed).
- **Concerns:** OP-3 (visible status caveat for activation), CB-8
- **Invariants:** (bootstrap; exercises INV-001 path) · **Surfaces:** cli_command
- **behavior_change:** false · **verification_mode:** system-validation · **verification_scope:** end-to-end
- **architecture_refs:** `.architecture/structured/components/debate-engine.md`, `.architecture/primer.md`
- **implementation_status:** partial · **evidence:** §2 content is new doc; `reference/` exists; CLAUDE.md symlink fact already corrected (skill-deploy-is-symlink).
- **test_refs:** TC-15.0, TC-15.1 · **test_files:** `skills/adversarial-spec/scripts/tests/test_getting_started_doclint.py` (TC-15.1); system-validation run (TC-15.0)
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_getting_started_doclint.py -q`
- **notes:** Spine TC-15.0 = system-validation (live bootstrap run) — non-exempt.

#### W5-3: Dogfood fixture — `tmr-registry.json` with all 15 spine records via compile step (§12 item 11)
- **US:** — (closes activation gap OP-3 / §12.11) · **Effort:** M · **Test Strategy:** test-after · **Wave:** 5 · **Depends:** W1-1, W3-2
- **Description:** Produce a `tmr-registry.json` containing a validated record (incl. `spine:true`) for **all 15** `[spine]` tests (today only TC-8.0 has a full block) — via the R4-4 LLM compile step (W3-2) — plus the regenerated prose view + echo-diff for `tests-pseudo.md`. This is the fixture that makes F′ actually pass this slice (until now F′ would NOT pass the draft — the OP-3/§12.11 activation gap). Verified by running the F′ checker (W1-1) against it.
- **Acceptance criteria:**
  - [ ] all 15 spine tests have an `active`, `spine:true` registry record (compiled, `TmrParser`-valid).
  - [ ] F′ checker (W1-1) returns `pass` (exit 0) against the dogfood registry + roadmap manifest.
  - [ ] prose view regenerated; echo-diff clean.
- **Concerns:** OP-3 (red F′ data path), §12.11 (registry migration)
- **Invariants:** INV-001 (exercises) · **Surfaces:** cli_command
- **behavior_change:** false · **verification_mode:** automated-integration · **verification_scope:** targeted
- **architecture_refs:** `.architecture/structured/components/debate-engine.md`, `.architecture/primer.md`
- **implementation_status:** greenfield · **evidence:** `tmr-registry` 0 hits; only TC-8.0 has a TMR block in tests-pseudo.
- **test_refs:** TC-8.0, TC-INV-001 · **test_files:** `skills/adversarial-spec/scripts/tests/test_dogfood_fprime.py`
- **verify_commands:** `uv run pytest skills/adversarial-spec/scripts/tests/test_dogfood_fprime.py -q`

---

## Dependency Graph
```
Wave 0 (foundation): W0-1 → W0-2 → {W0-4, W0-6}; W0-3; W0-5 (independent)
Wave 1: W0-2,W0-3,W0-4 → W1-1 → W1-2;  W0-3 → W1-3;  W0-5 → W1-4;  W0-3 → W1-5
Wave 2: W0-5,W1-4,W0-3 → W2-1;  W0-4,W1-5,W2-1 → W2-2;  W0-2,W0-4,W0-6,W1-5 → W2-3;  W0-2,W1-5 → W2-4
Wave 3: W0-4 → W3-1;  W0-1,W0-2,W0-5 → W3-2
Wave 4: W0-1,W0-2,W0-6 → W4-1;  W0-5 → W4-3
Wave 5: W5-1 (independent);  W1-1,W3-1 → W5-2;  W1-1,W3-2 → W5-3
```

## Workstreams (Claude + Codex parallel)
- **Stream A — Core contracts/parsers:** W0-1, W0-2, W0-3, W0-4
- **Stream B — Journal/classifier/conflict:** W0-5, W0-6, W1-4
- **Stream C — Gates/fence:** W1-1, W1-2, W1-3
- **Stream D — Guardrails + tiers:** W1-5, W2-1, W2-2, W2-3, W2-4
- **Stream E — Authoring/compile/Phase-8:** W3-1, W3-2, W4-1, W4-3
- **Stream F — Docs/dogfood:** W5-1, W5-2, W5-3
- **Merge points:** Wave 0 completion gates all feature waves (highest-risk merge first: Stream A). W3-2 + W1-1 → W5-3 (dogfood proves the end-to-end F′ path).

## Invariant coverage check (32 active → all covered)
INV-001 W1-1,W1-2 · INV-002 W1-1,W1-2 · INV-003 W1-1 · INV-004 W0-1,W0-2,W3-2 · INV-005 W3-1 · INV-006 W0-4,W3-1,W2-2 · INV-007 W2-4 · INV-008 W0-1 · INV-009 W0-6 · INV-010 W2-1 · INV-011 W0-6,W2-3 · INV-012 W1-4 · INV-013 W0-5 · INV-014 W0-5 · INV-015 W4-3 · INV-016 W1-3 · INV-017 W4-1 · INV-018 W1-5 · INV-019 W2-1 · INV-021 W1-4 · INV-023 W0-5 · INV-024 W0-3 · INV-025 W1-4 · INV-026 W2-4 · INV-027 W4-1 · INV-028 W0-1 · INV-029 W0-5,W3-2 · INV-030 W0-5,W1-2 · INV-032 W0-5 · INV-033 W1-3 · INV-034 W4-1 · INV-035 W2-1
**(Superseded — not required: INV-020, INV-022, INV-031.)** All 32 active invariants referenced by ≥1 task. ✅

## Uncovered concerns / cross-repo external dependencies (NOT skill tasks)
- **SEC-1 (HARD DEPENDENCY) — Fizzy-side mechanical F′ gate.** Non-bypassability requires the coordinated fizzy spec: `pipeline_advance` into the gauntlet lane refuses without valid F′ evidence and calls this slice's `gauntlet-check` contract; plus the **activation-rule integration test** proving a direct `pipeline_advance` fails closed. This slice DEFINES the contract (W1-1) but the mechanical gate + TMR persistence + `VALID_*` constants live in fizzy. Until it deploys, this slice is **advisory-only**. (Handover already written: fizzy repo `HANDOVER-reconcile-v4-to-skill-v12.md`.)
- **SEC-3 — fault-injection safety envelope** (PID/namespace/resource scoping, preflight, cleanup): prediction-prime fault-injection infra (NG-6) — out of skill scope.
- **SEC-1 owner-repo command sandbox / SEC-5 checker-tamper** — owner-repo + fizzy responsibility; the skill-runner executes the declared command (W4-1) but the sandbox/allowlist is owner-repo/fizzy.
- **FM-2 offline-DoS tradeoff** — version fence fails closed when the Fizzy card timestamp is unfetchable (W1-3); a cache/degraded-mode is explicitly NOT in this slice (accepted tradeoff, fail-closed by design).
- **FM-4 deploy choreography** — skill + fizzy constants + checker entry + integration test must land together; deploy ordering/rollback is the activation rule (cross-repo), surfaced as a release note, not a skill task.
- **OP-1 observability (metrics/SLO/runbook)** — partially addressed by structured guardrail output (W2-1); full metrics/runbook deferred (acknowledge).
- **Concept-accessor façade/bindings/fail-closed lint** — target-repo + its CI (NG-2). `acceptance` is defined without the façade (US-3), so it's an accelerator not a blocker.

## Concern disposition summary (24 accepted/acknowledged)
Addressed by tasks: CB-1 (W0-1,W0-5), CB-2 (W0-1,W4-1), CB-3 (W0-1,W2-4), CB-4 (W2-4), CB-5 (W2-3,W4-1), CB-6 (W0-2), CB-7 (W0-2,W3-2), CB-8 (W0-1,W3-1,W5-1), SEC-2 (W2-1,W3-2), SEC-5 (W1-1 partial), SEC-6 (W1-1 ack), RC-2 (W0-5,W1-4), RC-3 (W0-5), FM-1 (W0-3,W2-1), FM-5 (W2-1,W3-2), OP-2 (W1-1), OP-3 (W5-3), SCA-1 (W2-1), SCA-2 (W0-5), DD-1 (W2-1), DD-2 (W0-5), US-1 (W4-1), US-2 (W1-1), US-3 (W1-1), US-4 (W0-2 ack).
External/superseded: SEC-1/SEC-3 (external), SEC-4/RC-1-snapshot/FM-3-accounting/SCA-3 (superseded by DR-5/DR-6), FM-2/FM-4/OP-1 (acknowledged/external), DD-3/DD-4/DD-5/DD-6 (folded into the schema/Phase-8 tasks).
