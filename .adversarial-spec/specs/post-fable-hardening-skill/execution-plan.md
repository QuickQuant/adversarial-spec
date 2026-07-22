# Execution Plan: Post-Fable Hardening — Skill Slice (G1+G2+G5)

> **STATUS: APPROVED (Jason, 2026-07-22)** — approval delivered with the finalize+load
> directive ("finalize the plan, run the validation leg, emit fizzy-plan.json,
> pipeline_validate_plan, smoke the verify-commands, pipeline_load").
> Draft content unchanged at approval; this banner is the only delta.

> Session: `adv-spec-202607060132-post-fable-hardening-skill` · Card 5857 · Altitude: **system** (validation leg REQUIRED)
> Spec: `spec-final.md` v9.1 (sha `5d981350`) · Tests: `tests-spec.md` (128 TCs: 103 story + 25 invariant, 17 spines)
> Target architecture: v6, fingerprint `7fa0ae7a` (re-verified this session via `orchestration/compute_arch_fingerprint.py`), `spec_alignment_status: consumable_with_phase7_executable_adverse_suite_obligation`
> Gauntlet: 25 themes folded into spec (concern linkage below references theme IDs)

## Summary

- Tasks: **38** (S: 1, M: 15, L: 22)
- Workstreams: **4** — W0 (shared hardening substrate, 15), A (G1 operability, 7), B (G2 ascending arm, 11), C (G5 debate efficiency, 5)
- Gauntlet concerns addressed: 24 accepted themes of 25 (ACK-1 is acknowledged tradeoffs, not buildable)
- TCOV deferral families: all 20 (DF-1..DF-20) mapped to `tested_by` — full register-vs-plan diff in §"DF register mapping"
- Middleware candidates: all 11 (MW-001..MW-011) map 1:1 to typed W0 task cards (middleware-creator ready)
- Estimated effort: ~8–12 implementation weeks single-agent; W0 fans out to 3 streams after W0-2/W0-4

## Architecture Spine

Cross-cutting patterns from Target Architecture v6. All tasks must follow.

### Strict artifact envelope (MW-001)
- **Pattern:** every registry/receipt/manifest/report uses the §1 envelope; RFC 8785 JCS; `canonical_set()` for logical sets (duplicates REJECTED, never deduplicated); two profiles (`authority-signed` / `local-derived` with explicit `authority: null`).
- **Rule:** no ad-hoc JSON reads/writes of required artifacts; all validation through `hardening/artifacts.py`; missing/malformed/hash-invalid = fail closed, never "empty".
- **Reference:** Target Architecture §Artifact Validation; spec §1; Task W0-2.

### Durable state + StateTransaction (MW-002)
- **Pattern:** single-file = sidecar lock + expected-hash CAS + tmp/fsync/replace/dir-fsync; coupled multi-file = leased `StateTransaction` (PREPARED → PUBLISHING → COMMITTED, roll-forward-only after PUBLISHING, `transaction-corrupt` terminal + non-waivable).
- **Rule:** no direct writes to shared state; lease-then-locks in one canonical bytewise path order; readers run the post-lock nonterminal-scan barrier.
- **Reference:** Target Architecture §Durable State and Concurrency; spec §1; Task W0-4.

### One result vocabulary (MW-008, §5.2 enums)
- **Pattern:** `RemoteOperationResult` (sole definition §5.2), journal-only `PromotionSequenceResult`, `LocalReconciliationResult` (exactly `mirror-materialized|mirror-reconciliation-pending|mirror-reconciliation-corrupt`); CLI envelope `{status, code, check_id, subject, issues, remediation, data}`; exit 0/1/2 with blocking precedence.
- **Rule:** failure is never success-shaped; every path maps to exactly one named token; no new enums without spec bump.
- **Reference:** Target Architecture §CLI Boundary; spec §5.2; Tasks W0-3, W0-12.

### Authority boundary (MW-004/006/007/009)
- **Pattern:** signature validity ≠ authorization — TrustPolicy purpose scoping after verification; fizzy is the authority anchor (creation, snapshot, prepare, commit); conductor never self-attests; local files are validated mirrors.
- **Rule:** every recoverable remote mutation journals a durable intent (MW-011) BEFORE dispatch; uncertain outcomes resolve ONLY via the owning contract's status/idempotency lookup.
- **Reference:** Target Architecture §Outbound Integration Semantics; spec §1.1, §9; Tasks W0-7, W0-9, W0-10, W0-11, W0-12.

### Sole writers (MW-010)
- **Pattern:** one authoritative writer per mutation kind; Session TMR registry mutations only via `TmrRegistryWriter` (CAS + revision bump + journal coupling); static lint fails any other write-open call site.
- **Rule:** `criticality_classifier.py` and `record_verification_evidence.py` are the ONLY two mutation-kind owners; both go through the transaction API.
- **Reference:** Target Architecture §Source of Truth; spec §8.1; Tasks W0-13, B-3, B-4.

### Hook-plane isolation
- **Pattern:** hooks never import skill runtime; one slice dispatcher per event; typed `ALLOW|DENY|DIAGNOSTIC` verdicts; shared conformance fixtures run against BOTH hook-local and skill-runtime validators.
- **Rule:** no `hardening/` import from `.claude/hooks/`; preventive gates use blocking mode only.
- **Reference:** Target Architecture §Hook Plane; spec §5.2; Task A-2; INV-011.

---

## Workstream W0 — Shared Hardening Substrate (Wave 0)

All MW candidates map 1:1 to typed cards (middleware-creator source tasks). Package root: `skills/adversarial-spec/scripts/hardening/`.

#### W0-1: Scaffold `hardening/` package + Python 3.14 floor migration
- **Effort:** M · **Test Strategy:** test-after · **behavior_change:** true
- **Spec refs:** §1 (envelope preamble), target-architecture §Package and Component Boundaries, framework_version (3.14 W0 coordinated migration)
- **Concerns:** — (enabling task)
- **Description:** Create the `hardening/` package skeleton (module stubs per the component-boundary tree), bump `requires-python` to >=3.14, pin `rfc8785==0.1.4` + `cryptography==49.0.0`, add the clean-env wheel-install test the migration requires. No upward import from `gauntlet` (no app→app).
- **Acceptance:** package imports cleanly; `uv run adversarial-spec --help` still works (symlink bridge preserved — .architecture gotcha); wheel-install test green on 3.14.
- **implementation_status:** greenfield — no `hardening/` dir exists (`ls skills/adversarial-spec/scripts/hardening` → ENOENT, verified 2026-07-21)
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-0.0 (partial: toolchain)] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_hardening_package.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_hardening_package.py -q`]
- **architecture_refs:** [`.architecture/filesystem-map.md`, `.architecture/primer.md`]
- **Invariants:** — · **Surfaces:** cli_command · **Dependencies:** none

#### W0-2: MW-001 StrictArtifactCodec + canonical_sets
- **Effort:** L · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §1 (envelope, JCS, signature-byte contract, value normalization, profiles, canonical sets, discriminated authorization-fact schema OR-1)
- **Concerns:** CB-2 (hash/canonicalization gaps), SEC-1 (partial: fact schema)
- **Description:** `artifacts.py` + `canonical_sets.py`: bounded strict decode (dup-member/NaN/BOM/surrogate/negative-zero rejection), schema validation, JCS canonicalization, content-hash verify (excludes `content_hash`+`generated_at`+`authority.signature`), domain-prefix signature-byte assembly, `authority-signed`/`local-derived` profiles, `canonical_set()` with bytewise ordering + duplicate REJECTION, discriminated authorization-fact variant table (structural absence, no null placeholders).
- **Acceptance:** table-driven byte-level conformance suite (DF-1); a provisional and committed deferral fact with identical content hash differently; wrong-profile artifacts rejected as unauthorized vs malformed per §1.
- **implementation_status:** greenfield — no codec exists; nearest prior art is gauntlet checkpoint envelope (`gauntlet/persistence.py:560-583`), which stays untouched
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-INV-005, TC-INV-020 (hash side), TC-INV-023, DF-1] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_strict_artifact_codec.py`, `skills/adversarial-spec/scripts/tests/test_canonical_sets.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_strict_artifact_codec.py skills/adversarial-spec/scripts/tests/test_canonical_sets.py -q`]
- **architecture_refs:** [`.architecture/structured/components/gauntlet-persistence.md`, `.architecture/primer.md`, `.architecture/patterns.md`]
- **Invariants:** INV-002, INV-005, INV-020(hash), INV-023 · **Surfaces:** cli_command · **Dependencies:** W0-1

#### W0-3: MW-008 CliBoundary
- **Effort:** M · **Test Strategy:** test-after · **behavior_change:** true
- **Spec refs:** target-architecture §CLI Boundary; spec §5.2 (result tokens), §3 (exit mapping)
- **Concerns:** CB-1 (partial: result envelope), FM-3 (partial)
- **Description:** `cli_boundary.py`: shared strict argparse (`allow_abbrev=False`, unknown-arg rejection), one structured result envelope per invocation, exit mapping 0/1/2 with blocking precedence, no env-var gate inputs.
- **Acceptance:** INV-016 negative tests (abbreviation, unknown arg, envelope-always); help = successful help result.
- **implementation_status:** greenfield — no shared CLI adapter; `validation_emission.py:3423` has its own `_Parser` (stays; migration out of scope)
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-INV-016, TC-INV-004 (partial)] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_cli_boundary.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_cli_boundary.py -q`]
- **architecture_refs:** [`.architecture/structured/components/validation-emission.md`, `.architecture/patterns.md`]
- **Invariants:** INV-004, INV-010, INV-016 · **Surfaces:** cli_command · **Dependencies:** W0-1

#### W0-4: MW-002 DurableStateStore + StateTransaction coordinator
- **Effort:** L · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §1 (atomic-write protocol, StateTransaction: manifest, lease-then-locks, PREPARED/PUBLISHING/COMMITTED, recovery ownership, reader isolation, reachability GC)
- **Concerns:** RC-3 (THE StateTransaction theme), CB-2 (partial)
- **Description:** `state_store.py`: persistent-identity sidecar locks (fcntl direct, LOCK_SH/LOCK_EX), expected-hash CAS, atomic single-file writes, repo-scoped `.txn/` coordinator with leases, canonical bytewise lock order, roll-forward recovery, reader release-recover-retry protocol, `transaction-corrupt` terminal quarantine (non-waivable), reachability-only GC with commit certificates.
- **Acceptance:** DF-6 completeness matrix — reversed-lock-order rejection, held-lock timeout (`lock-acquisition-timeout`), sidecar replace/unlink protection, GC-vs-live-lease, crash at every protocol boundary (adverse suite hooks in W0-15); addresses .architecture CON-003/CON-004 class for new artifacts.
- **implementation_status:** greenfield — existing `gauntlet/persistence.py:74-152` protects single files only ("File atomicity does not create a transaction across multiple sidecars" — component doc LLM note); no coordinator exists
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-1.4, TC-INV-008, TC-INV-012 (store side), DF-6] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_durable_state_store.py`, `skills/adversarial-spec/scripts/tests/test_state_transaction.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_durable_state_store.py skills/adversarial-spec/scripts/tests/test_state_transaction.py -q`]
- **architecture_refs:** [`.architecture/structured/components/gauntlet-persistence.md`, `.architecture/concerns.md`, `.architecture/structured/flows.md`]
- **Invariants:** INV-008, INV-012 · **Surfaces:** cli_command, startup_migration · **Dependencies:** W0-1, W0-2

#### W0-5: Safe-path resolver + filesystem capability probes
- **Effort:** M · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §1 (descriptor-relative traversal, lock-capability probe, `filesystem-capability-unsupported`), target-architecture §Safe Paths and Filesystem Contract
- **Concerns:** US-1 (filesystem safety)
- **Description:** Session-root-relative resolution: per-component dir_fd walk with O_NOFOLLOW + fstat device/mount validation (normative; openat2 only via vetted binding passing the same fixtures); `..`/absolute/cross-session fail closed; bootstrap lock-capability probe proving cross-process shared/exclusive semantics.
- **Acceptance:** intermediate-symlink substitution blocked (TC-1.5); DF-8 induced submount rejection; unsupported filesystem = named capability failure, never silent.
- **implementation_status:** greenfield — spec §1 notes final-component checks alone are insufficient; no descriptor-relative walker exists in repo
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-1.5, TC-INV-012 (path side), DF-8] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_safe_paths.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_safe_paths.py -q`]
- **architecture_refs:** [`.architecture/structured/components/gauntlet-persistence.md`, `.architecture/primer.md`]
- **Invariants:** INV-006 (path clauses), INV-012 · **Surfaces:** cli_command, startup_migration · **Dependencies:** W0-1

#### W0-6: MW-003 HashChainedJournal
- **Effort:** M · **Test Strategy:** test-after · **behavior_change:** true
- **Spec refs:** §1.1 (journals = tamper-evidence + external anchoring), §10.2 (event log), §12
- **Concerns:** SEC-3 (partial: journal-head anchoring), RC-3 (partial)
- **Description:** `journal.py`: logical append (each event hashes predecessor), chain verification, event-head projection, external-anchor record emission (head → authority-side card comment/attestation).
- **Acceptance:** chain-break detection (TC-12.3 analogue at unit level); anchored-head verification round-trip.
- **implementation_status:** greenfield — `provenance_journal.py:77-362` is TMR-specific with different coupling; this is the generic substrate (provenance journal is NOT rewritten this slice)
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-12.3 (unit layer), TC-INV-009 (partial)] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_hash_chained_journal.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_hash_chained_journal.py -q`]
- **architecture_refs:** [`.architecture/structured/components/tmr-provenance.md`, `.architecture/structured/components/gauntlet-persistence.md`]
- **Invariants:** INV-009, INV-013 (partial) · **Surfaces:** cli_command · **Dependencies:** W0-2, W0-4

#### W0-7: MW-004 ReceiptVerifier + TrustPolicy evaluation
- **Effort:** L · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §1.1 (TrustPolicy purpose authorization, trust roots, key lifecycle), §5.4 (receipt binding + rejection set)
- **Concerns:** SEC-1, SEC-2, SEC-4 (verifier side)
- **Description:** `receipts.py` + `trust_policy.py`: trusted-key lookup from launcher config (outside conductor-writable state), exact-byte ed25519 verification (domain prefix ‖ JCS minus signature), THEN purpose-scoped TrustPolicy authorization (domain, key_id, keyset epoch, artifact type, purpose, principal, session scope, validity interval) under immutable policy identity + hash; purpose-preserving chained keyset rotation; full §5.4 rejection-set semantics.
- **Acceptance:** wrong-purpose key rejected across all receipt kinds (TC-15.8); DF-2 rotation/wrong-root/epoch-chain cases; DF-4 inherited-vs-new purpose + rotation-before-commit.
- **implementation_status:** greenfield — no signature verification exists in the skill runtime (grep cryptography: packaging only)
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-15.3, TC-15.8, TC-INV-006, DF-2, DF-4 (policy side)] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_receipt_verifier.py`, `skills/adversarial-spec/scripts/tests/test_trust_policy.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_receipt_verifier.py skills/adversarial-spec/scripts/tests/test_trust_policy.py -q`]
- **architecture_refs:** [`.architecture/primer.md`, `.architecture/structured/components/telegram-usage.md`, `.architecture/patterns.md`]
- **Invariants:** INV-006, INV-010, INV-024 · **Surfaces:** cli_command, outbound_integration · **Dependencies:** W0-2

#### W0-8: MW-005 PromotionPredicates (pure)
- **Effort:** L · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §8.1 (selection predicate, `is_concrete`), §9 (`is_promotion_ready` 6 conditions, `is_obligation_satisfied` explicit disjuncts, skip/deferred semantics, provisional/committed phases)
- **Concerns:** CB-4 (predicates not machine-defined), RC-1 (partial: predicate side)
- **Description:** `predicates.py`: pure functions over validated domain types (no I/O, no crypto). `is_concrete` exact enum equality; `is_promotion_ready(tmr, authorization_snapshot)` all six typed conditions (closed enums, newest-schema-valid evidence selection, equal-recency = validation failure, provenance condition 6); `is_obligation_satisfied` with `critical_seam != null` precondition and independent skip/deferred disjuncts (provisional pre-commit / committed post-commit, parent-scoped); `select_for_verification`.
- **Acceptance:** DF-5 mutation matrix (closed-enum rejection, null-seam override, transition-time revalidation hooks); TC-8.9 identity mutants; TC-7.3 selection-predicate mutation.
- **implementation_status:** greenfield — predicates exist only as spec prose; no `predicates.py`
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-7.2, TC-7.3, TC-8.9, TC-INV-021 (branch disjointness), DF-5] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_promotion_predicates.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_promotion_predicates.py -q`]
- **architecture_refs:** [`.architecture/structured/components/tmr-provenance.md`, `.architecture/primer.md`]
- **Invariants:** INV-021 · **Surfaces:** cli_command · **Dependencies:** W0-1 (types), B-1 (schema fields)

#### W0-9: MW-009 AuthorizationSetBuilder
- **Effort:** L · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §1 (`authorization_set_hash` formula, discriminated facts), §1.1 (ValidatedAuthorizationSet), §9 (provisional transfer plan)
- **Concerns:** SEC-1 (core), CB-2 (partial)
- **Description:** `authorization_set.py`: stateful validation of receipts + successor inherited-obligation records against ONE registry generation → immutable `ValidatedAuthorizationSet` with `authorization_set_hash` per the exact §1 domain-separated formula; consumes `TrustPolicySnapshot`; emits the canonical provisional transfer plan from validated `tmr-deferred` receipts; obligation policy vs trust policy separation.
- **Acceptance:** mixed-generation/caller-curated sets structurally impossible; DF-4 generation race; shuffled/duplicated facts rejected (adverse case 7); provisional vs committed sets hash differently (OR-1).
- **implementation_status:** greenfield
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-8.9 (snapshot input), TC-15.8, TC-INV-020, TC-INV-024, DF-4] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_authorization_set_builder.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_authorization_set_builder.py -q`]
- **architecture_refs:** [`.architecture/structured/components/tmr-provenance.md`, `.architecture/primer.md`, `.architecture/patterns.md`]
- **Invariants:** INV-020, INV-024 · **Surfaces:** cli_command · **Dependencies:** W0-4, W0-7

#### W0-10: MW-011 DurableOperationJournal
- **Effort:** M · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §9 (durable operation journal: intent-durable pre-dispatch record, `remote-uncertain`, `PromotionSequenceResult` derivation, same-bytes retry, per-contract result families)
- **Concerns:** RC-2 (core), FM-3 (partial), CB-1 (partial)
- **Description:** `operation_journal.py` (runtime-local, imports no transport): `operation_id` + contract id + behavior fingerprint + canonical request hash journaled + fsynced BEFORE dispatch; state machine intent-durable/in-flight/uncertain/resolved; `(contract_id, result_token)` outcomes; `-not-attempted` derivation from record absence; restart recovery.
- **Acceptance:** TC-8.12 crash before/after dispatch distinguishable by record presence, never transport guessing; same-id different-bytes = `intent-mismatch` (client side); DF-11 failure-injection table asserting owner/action/state.
- **implementation_status:** greenfield
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-8.12, TC-INV-017, DF-11] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_operation_journal.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_operation_journal.py -q`]
- **architecture_refs:** [`.architecture/structured/components/gauntlet-persistence.md`, `.architecture/structured/flows.md`]
- **Invariants:** INV-009, INV-017 · **Surfaces:** cli_command, outbound_integration · **Dependencies:** W0-4, W0-6

#### W0-11: MW-006 LocalCapabilityVerifier + trusted-time watermark
- **Effort:** M · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §1 (trusted time, monotonic authority-time watermark), §5.2 (capability-state result matrix), §3 (hermetic split)
- **Concerns:** SEC-2 (partial), FM-1 (partial), CB-1 (capability matrix)
- **Description:** `local_capabilities.py`: offline signature/version/freshness verification of cached capability attestations; monotonic authority-time watermark (never decremented, persisted); `max(local clock, watermark)` expiry; every §5.2 capability-state → exactly one deterministic token (`deferred-for-live-preflight` vs broken vs `authority-capability-missing` etc.); release-signature validation (`release-signature-missing/invalid`).
- **Acceptance:** wall-clock rollback cannot extend authorization (incl. across restarts); DF-2 rollback/skew + missing-release cases; TC-3.3 local vs remote token distinction (local half).
- **implementation_status:** greenfield
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-3.3 (local half), TC-0.10 (attestation validation), DF-2] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_local_capability_verifier.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_local_capability_verifier.py -q`]
- **architecture_refs:** [`.architecture/primer.md`, `.architecture/structured/components/validation-emission.md`]
- **Invariants:** INV-013 (freshness), INV-014 · **Surfaces:** cli_command, startup_migration · **Dependencies:** W0-7

#### W0-12: MW-007 RemoteAuthorityClient
- **Effort:** L · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §5.2 (RemoteOperationResult — sole definition), §8.2 (probes, behavior fingerprint), §9 (prepare/commit/status, recovery split OR-4), §11.2 (snapshot upload/finalize two-layer idempotency)
- **Concerns:** CB-1 (core), SEC-5, RC-1 (client legs), FM-3
- **Description:** `remote_authority.py`: snapshot upload/finalize, prepare, commit, status reconciliation, signed challenge-response capability probes (+ negative probes), behavior-fingerprint pinning, over injected transports; never dispatches a recoverable mutation without a durable MW-011 intent; uncertain-prepare replays prepare by `operation_id` (no receipt hash exists); uncertain-commit uses `promotion-commit-status-v1` keyed by `operation_id` + prepare receipt hash (OR-4 split); every result is exactly one §5.2 token.
- **Acceptance:** TC-8.11 success tokens never exception-shaped; DF-3 fingerprint drift = `state-stale`; contract fixtures for all 9 consumed contracts (recorded fixtures — hermetic; live boundary is preflight-only per CONS-V8).
- **implementation_status:** greenfield — existing model transports (`models.py`, `gauntlet/model_dispatch.py`) are LLM dispatch, not authority contracts; do NOT extend them (CON-009 counter-pattern)
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-8.10 (client half), TC-8.11, TC-16.4, TC-INV-004, TC-INV-017, TC-INV-019 (client half), DF-3] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_remote_authority_client.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_remote_authority_client.py -q`]
- **architecture_refs:** [`.architecture/structured/components/models-providers.md`, `.architecture/concerns.md`, `.architecture/structured/flows.md`]
- **Invariants:** INV-004, INV-007 (client side), INV-017, INV-019 · **Surfaces:** outbound_integration · **Dependencies:** W0-2, W0-7, W0-10

#### W0-13: MW-010 TmrRegistryWriter + sole-writer static lint
- **Effort:** L · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §8.1 (registry transaction API, sole-writer lint, board upsert idempotency), §1.2 (TMR registry = LOCAL-authoritative row)
- **Concerns:** RC-3 (registry pair), DD-3 (sole-writer enforcement)
- **Description:** `tmr_registry_writer.py`: the single persistence path for the Session TMR registry — read revision → validate preconditions → write under canonical lock order → bump revision; stale expected-revision rejected (retry from fresh read); classifier-relevant change invalidates dependent evidence in the same transaction; authoring-lint rule failing any write-open call site outside the two sole writers.
- **Acceptance:** DF-7 stale-revision + same-txn invalidation + sole-writer lint (static fixture with a violating module); serves both mutation-kind owners (B-3, B-4).
- **implementation_status:** greenfield — `tmr_compile_step.py`/`provenance_journal.py` write the roadmap-level registry; the Session TMR registry writer does not exist
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-7.5 (writer side), TC-INV-003, DF-7] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_tmr_registry_writer.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_tmr_registry_writer.py -q`]
- **architecture_refs:** [`.architecture/structured/components/tmr-provenance.md`, `.architecture/structured/components/gauntlet-persistence.md`]
- **Invariants:** INV-003, INV-008 (consumer) · **Surfaces:** cli_command · **Dependencies:** W0-4, W0-6, B-1

#### W0-14: Per-fact authority-matrix lint + consumer tests
- **Effort:** M · **Test Strategy:** test-producer · **behavior_change:** true
- **Spec refs:** §1.2 (per-fact authority matrix)
- **Concerns:** US-4 (the meta-fix organizing RC-1/SEC-*/FM-1)
- **Description:** Matrix-driven consumer test suite: for every §1.2 row, tests assert consumers branch only on validated authority state and fail closed with the named result on stale/missing/invalid mirror; authoring-lint rule flagging security-fact reads with no declared authority row (undeclared-authority lint).
- **Acceptance:** DF-9 complete row coverage; lint catches a fixture module reading a mirror directly.
- **implementation_status:** greenfield
- **verification_mode:** test-producer · **scope:** targeted
- **test_refs:** [DF-9, TC-INV-003 (consumer side)] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_authority_matrix.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_authority_matrix.py -q`]
- **architecture_refs:** [`.architecture/primer.md`, `.architecture/patterns.md`]
- **Invariants:** INV-003 · **Surfaces:** cli_command · **Dependencies:** W0-2
- **Note:** lint half lands with the A-1 authoring-lint family; test half is W0-adjacent.

#### W0-15: Executable adverse suite (Phase 4 residual obligation)
- **Effort:** L · **Test Strategy:** test-producer · **behavior_change:** false (test-only)
- **Spec refs:** target-architecture §Dry-run Summary (mandatory adverse cases R4 + R5 additions 1–13); `residual_phase7_obligation` header field
- **Concerns:** RC-1, RC-2, RC-3, SEC-3, SEC-4 (adverse traversal of all)
- **Description:** The executable end-to-end adverse suite the Phase 4 publication deferred to Phase 7 (pre-load gate 3): every R4 mandatory adverse case + every R5 addition (reader race, durable identity across restart, canonical-set shuffles, hook verdict failures, lock-sidecar attacks, cross-device staging, snapshot-omission journaling, conductor-only evidence) as executable tests over the real substrate — no design-walkthrough evidence claims.
- **Acceptance:** all 13 R5 cases + R4 canonical-sequence traversal red-green against the real modules; suite runs in CI via the standard runner.
- **implementation_status:** greenfield — `dry-run-results.json` is design-level only (its own text disclaims executed-boundary evidence)
- **verification_mode:** test-producer · **scope:** targeted
- **test_refs:** [adverse suite = evidence for TC-1.4/TC-1.5/TC-8.10–8.15 families] · **test_files:** [`skills/adversarial-spec/scripts/tests/adverse/test_adverse_suite.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/adverse -q`]
- **architecture_refs:** [`.architecture/structured/flows.md`, `.architecture/structured/components/gauntlet-persistence.md`]
- **Invariants:** INV-008, INV-017, INV-020, INV-021 (adverse traversal) · **Surfaces:** cli_command, outbound_integration · **Dependencies:** W0-4, W0-5, W0-9, W0-10, W0-12

---

## Workstream A — G1 Operability

#### A-1: gate_inventory.py + gates.json + doclint (authoring-lint family)
- **Effort:** L · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §5.1, §5.2 (negative-test executor, dependency-semantics gate marker), §6.2 (doclint pointer closure)
- **Concerns:** DD-3 (partial: registry enumeration), US-3 (partial)
- **Description:** `gate_inventory.py` (via MW-008): maintain `gates.json` (classification enum, enforcement, owner, contract_id for fizzy-owned, violation_modes[]), normalized semantic form (content-hash exclusions), doclint mapping phase-doc markers → gate_id, `phase_docs_hash` staleness, negative-test execution harness; hosts the authoring-lint family (incl. W0-13 sole-writer + W0-14 undeclared-authority rules).
- **Acceptance:** TC-1.0 inventory completeness (incl. canonical Phases 1–8 + owned subflow units per OR-3); TC-1.2 unmapped marker fails; unclassified gate fails `check`.
- **implementation_status:** greenfield — `gate_inventory.py` absent (verified)
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-1.0, TC-1.2, TC-INV-001] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_gate_inventory.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_gate_inventory.py -q`]
- **architecture_refs:** [`.architecture/INDEX.md`, `.architecture/structured/components/harness-hooks.md`, `.architecture/patterns.md`]
- **Invariants:** INV-001, INV-010, INV-013 (doclint) · **Surfaces:** cli_command · **Dependencies:** W0-2, W0-3

#### A-2: Hook-plane dispatcher + conformance fixtures
- **Effort:** L · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §5.2 (hook-plane architecture: one dispatcher per event, typed verdicts, duplicate-handler detection, shared conformance fixtures), target-architecture §Hook Plane
- **Concerns:** DD-2 (core)
- **Description:** One slice-owned dispatcher per event type in `.claude/hooks/` (hook-local codec, NO skill imports — INV-011); declarative versioned registration; bootstrap duplicate/third-party handler detection (BOOT-GATES extension); typed `ALLOW|DENY|DIAGNOSTIC`; blocking mode mandatory for preventive gates (async = lint failure); shared conformance fixture suite run against BOTH hook-local and skill validators; consolidate the three drifting role resolvers into ONE hook-local helper (resolves .architecture CON-005).
- **Acceptance:** TC-2.4 duplicate handler detected + cross-surface fixture agreement; internal failure → DENY for safety dispatchers; adverse case 9 (classifier exit-1/raise/malformed/async) covered.
- **implementation_status:** partial — hook plane exists (`.claude/hooks/`, `fizzy_payload_guard.py:86-147`, three role resolvers at `dispatch_check.py:18-83`/`pipeline_continue.py:21-67`/`pipeline_idle_retry.py:24-70`); dispatcher/typed-verdict/conformance layer is new
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-2.0, TC-2.2, TC-2.3, TC-2.4, TC-INV-011] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_hook_dispatcher_conformance.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_hook_dispatcher_conformance.py -q`]
- **architecture_refs:** [`.architecture/structured/components/harness-hooks.md`, `.architecture/patterns.md`, `.architecture/concerns.md`]
- **Invariants:** INV-011 · **Surfaces:** hook-plane:cli_command · **Dependencies:** W0-1 (repo layout only; NO hardening imports)

#### A-3: Judgment-gate corpus (rubrics + fixtures)
- **Effort:** M · **Test Strategy:** test-after · **behavior_change:** true
- **Spec refs:** §5.3, §7 (fixtures double as harness items)
- **Concerns:** — (US-3)
- **Description:** `rubrics/<gate_id>.md` (≤~40 lines each) + ≥1 golden fixture per judgment gate under `fixtures/conductor-competence/<gate_id>/`; fixture schema (`state.json` + `question.md` + `expected.json`); schema validator consumed by BOOT-HARNESS.
- **Acceptance:** every `judgment` row in gates.json has rubric + fixture; fixtures schema-valid; TC-3.2 rubric/fixture completeness.
- **implementation_status:** greenfield — no `rubrics/` or `fixtures/` dirs exist (verified)
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-3.0, TC-3.2] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_judgment_corpus.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_judgment_corpus.py -q`]
- **architecture_refs:** [`.architecture/INDEX.md`, `.architecture/access-guide.md`]
- **Invariants:** INV-001 (fixture leg) · **Surfaces:** cli_command · **Dependencies:** A-1
- **Note:** TC-6.2 keeps its stub model (concrete `technical_constraint` recorded in spec §14).

#### A-4: competence_harness.py + baselines + coverage manifest
- **Effort:** L · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §7 (answer schema, exact scoring, transport policy, attempt evidence, coverage manifest, report identity, pre-session gate, baseline identity + environment fingerprint, `MAX_PHASE_REGRESSION_POINTS = 10`)
- **Concerns:** OP-1 (core)
- **Description:** Harness runner (via MW-008): strict-JSON answer scoring (`required ⊆ next ⊆ allowed`, forbidden empty-intersection, exact citation equality, critical ⇒ ≥1 required); exact arithmetic; bounded retry w/ attempt evidence + `not-comparable` on infra-failure threshold; coverage manifest validation; immutable baselines keyed by full identity incl. environment fingerprint; pre-session gate (waivable).
- **Acceptance:** TC-6.4 vacuous `[]` fails critical fixtures; TC-6.5 missing/incompatible baseline blocks; 2-pass/2-fail = exactly 50; DF-12 threshold-boundary + fingerprint-drift → `not-comparable`.
- **implementation_status:** greenfield — `competence_harness.py` absent (verified)
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-6.0, TC-6.1, TC-6.3, TC-6.4, TC-6.5, TC-6.6, DF-12] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_competence_harness.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_competence_harness.py -q`]
- **architecture_refs:** [`.architecture/structured/components/models-providers.md`, `.architecture/structured/components/telegram-usage.md`]
- **Invariants:** INV-010 (constant binding) · **Surfaces:** cli_command · **Dependencies:** W0-3, A-3

#### A-5: Phase-doc spine units + pointer closure + 09-verification relocation
- **Effort:** L · **Test Strategy:** test-after · **behavior_change:** true
- **Spec refs:** §6.1 (spine units, ownership rule, verification-document ownership OR-3), §6.2 (context-load manifest, move ≠ delete)
- **Concerns:** US-3 (partial: altitude components)
- **Description:** Decompose phase docs into `phases/<NN>-<phase>/spine.md` + `reference/*.md` with single-owner pointers; relocate `phases/09-verification.md` → `phases/08-implementation/reference/verification.md` with Phase 8 spine step ownership + SKILL.md router update + decisions-log entries; `architecture_refs` resolver writing per-step `context-load-manifest` (narrowed mechanized claim).
- **Acceptance:** doclint pointer closure zero dangling + exactly one owner (mechanized via A-1); TC-4.0/4.2, TC-5.0/5.2/5.3; no `09-verification.md` at old path; router resolves.
- **implementation_status:** partial — flat phase docs exist (`skills/adversarial-spec/phases/*.md`, 0 spine files verified); restructure + resolver are new
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-4.0, TC-4.2, TC-5.0, TC-5.2, TC-5.3] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_spine_units_closure.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_spine_units_closure.py -q`]
- **architecture_refs:** [`.architecture/INDEX.md`, `.architecture/filesystem-map.md`, `.architecture/concerns.md`]
- **Invariants:** INV-001 (marker closure), INV-013 (phase_docs_hash) · **Surfaces:** cli_command · **Dependencies:** A-1

#### A-6: Waiver flow — challenge creation, receipt acceptance, audit cache
- **Effort:** L · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §5.4 (entire), §1.1 (operator-held keys)
- **Concerns:** SEC-4 (core), US-3 (partial)
- **Description:** Blocking-checker challenge creation (immutable `block_id`, one-time nonce request, `local-derived` challenge envelope), receipt acceptance via MW-004 (challenge-byte binding, nonce-consumption receipt validation, precedence/`authorization_kind` rules, non-waivable class rejection at challenge creation, consumption-at-protected-transition), `nonces.jsonl` audit cache, issuance idempotency by `operation_id` (MW-011), close-report/checkpoint/card surfacing.
- **Acceptance:** full §5.4 rejection set as negative tests (TC-15.x); TC-15.4 wrong-block/reused-nonce replay; TC-15.7 lost-response → original receipt; DF-14 stateful bridge conformance (substitution, cross-session nonce, revoked principal) against recorded bridge fixtures.
- **implementation_status:** greenfield — no waiver machinery exists (telegram_bot.py is transport only, stays)
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-15.0, TC-15.2–TC-15.8, DF-14] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_waiver_flow.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_waiver_flow.py -q`]
- **architecture_refs:** [`.architecture/structured/components/telegram-usage.md`, `.architecture/structured/flows.md`, `.architecture/primer.md`]
- **Invariants:** INV-002, INV-006 · **Surfaces:** cli_command, outbound_integration · **Dependencies:** W0-7, W0-9, W0-10

#### A-7: hardening_bootstrap.py (BOOT-* checks + live preflight)
- **Effort:** L · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §3 (check table, hermetic split, deferred-state exit mapping, attestation provisioning, exit codes, failure output contract), §5.2 (no-network rule)
- **Concerns:** FM-1 (partial), CB-1 (exit mapping), US-3
- **Description:** Bootstrap CLI (via MW-008): BOOT-GATES / BOOT-HARNESS / BOOT-RECON / BOOT-REGISTRY (regime branch via MW-006, registry check per regime) / BOOT-SPINE (transitive validation w/ predecessor rule) / BOOT-ROUTER (advisory only); hermetic blocking path (import-boundary: no transport instantiation — INV-014); `--live-preflight` REMOTE path via MW-007; deferred→exit mapping by pending regime-sensitive transition; five-minute fresh-clone target.
- **Acceptance:** TC-0.x family (TC-0.0 clean run, TC-0.4 regime branch, TC-0.5/0.6 validators/bootstrap split, TC-0.10 epoch-zero); TC-2.3 denied-socket inventory of every blocking check.
- **implementation_status:** greenfield — `hardening_bootstrap.py` absent (verified)
- **verification_mode:** automated-integration · **scope:** targeted
- **test_refs:** [TC-0.0–TC-0.10, TC-2.3, TC-INV-014] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_hardening_bootstrap.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_hardening_bootstrap.py -q`]
- **architecture_refs:** [`.architecture/structured/components/validation-emission.md`, `.architecture/structured/components/harness-hooks.md`, `.architecture/filesystem-map.md`]
- **Invariants:** INV-002, INV-014 · **Surfaces:** cli_command, startup_migration · **Dependencies:** W0-11, A-1, A-4, B-8 (spine artifacts for BOOT-SPINE), C-1 (BOOT-RECON self-check)

---

## Workstream B — G2 Ascending Arm

#### B-1: TMR keystone-first schema extension (obligation fields)
- **Effort:** M · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §5.4 (`obligation` block, `tmr_record_hash` canonical projection), §8.1 (card key), §9 (predicates consume the fields)
- **Concerns:** CB-2 (tmr_record_hash projection), DD-3 (partial)
- **Description:** **Keystone-first (pre-load gate 2):** add `obligation_revision`, `obligation_policy_version`, `tmr_record_hash` (+ the three canonical requirement-field tokens `required_liveness_class` / `required_environment` / `required_tier` if absent) to `Brainquarters/shared-context/test-maturity-record-schema.md` FIRST, then mirror into `tmr_schema.py` with `schema_sha256` drift tripwire (TC-0.5-style). The 11 SCHEMA GAP carries in tests-spec.md resolve against these fields.
- **Acceptance:** keystone edited before mirror commit (commit order provable); strict schema round-trip; obligation-identity projection hash stable under evidence-field changes (waiver survives evidence write-back, invalidates on obligation change).
- **implementation_status:** greenfield fields on partial surface — keystone + `tmr_schema.py` exist; grep for all three fields = 0 in both (verified 2026-07-21)
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-7.x schema legs, TC-8.4 (identity), 11 tests-spec SCHEMA GAP carries] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_tmr_obligation_fields.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_tmr_obligation_fields.py -q`]
- **architecture_refs:** [`.architecture/structured/components/tmr-provenance.md`, `.architecture/primer.md`]
- **Invariants:** INV-024 (field separation) · **Surfaces:** cli_command · **Dependencies:** none (earliest B task; blocks W0-8, W0-13)

#### B-2: verification_cards.py — deterministic emitter + board upsert
- **Effort:** L · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §8.1 (card content, deterministic emission key, no-op artifact, registry provenance, board upsert idempotency)
- **Concerns:** DD-3 (row identity), RC-3 (upsert)
- **Description:** One card per qualifying TMR keyed `(session_id, tmr_uid, obligation_revision, obligation_policy_version)`; `registry_hash` as provenance snapshot never key; supersede obsolete cards; `pipeline_load` upsert with stable local key as idempotency key + expected board revision; lost response → authority query; board-ahead = `local-mirror-stale`.
- **Acceptance:** TC-7.4 identity stable across registry churn (no duplicates); DF-7 stateful board fixture; empty selection emits no-op artifact with `tmr_registry_path`+hash.
- **implementation_status:** greenfield — `verification_cards.py` absent (verified)
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-7.0, TC-7.4, TC-7.6, TC-7.7, TC-7.8, DF-7] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_verification_cards.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_verification_cards.py -q`]
- **architecture_refs:** [`.architecture/structured/components/tmr-provenance.md`, `.architecture/structured/flows.md`]
- **Invariants:** INV-003, INV-013 · **Surfaces:** cli_command, outbound_integration · **Dependencies:** B-1, W0-8, W0-13

#### B-3: record_verification_evidence.py — evidence write-back + maturity authority
- **Effort:** M · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §8.1 (evidence write-back sole path, maturity promotion authority, atomic with write-back)
- **Concerns:** RC-3 (evidence write-back CAS), DD-3
- **Description:** The ONLY path from completed card to promotion-eligible evidence: validates card binding, evidence class, artifact hash, `tmr_uid` before registry update via `TmrRegistryWriter`; sole authorized writer of `nl|acceptance → concrete` atomically with write-back.
- **Acceptance:** card completion without registry update structurally cannot count promotion-ready; optimistic-concurrency conflict retries from fresh read.
- **implementation_status:** greenfield — script absent (verified); named by spec as new sole writer
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-7.2 (evidence leg), TC-8.4 (green-but-wrong evidence)] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_record_verification_evidence.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_record_verification_evidence.py -q`]
- **architecture_refs:** [`.architecture/structured/components/tmr-provenance.md`, `.architecture/primer.md`]
- **Invariants:** INV-003, INV-009 · **Surfaces:** cli_command · **Dependencies:** W0-13, B-1

#### B-4: criticality_classifier.py extension — resolution path
- **Effort:** M · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §8.1 (criticality resolution: sole writer, decision record, never-default-false, operator receipt-bound resolution)
- **Concerns:** CB-4 (null-seam), DD-3
- **Description:** Extend the existing classifier: resolution action recording rule version + source-artifact hash + architecture link for any `false` resolution; `null` preserved or resolved `true` otherwise; operator receipt-bound criticality-resolution decisions recorded by this sole writer; all writes via `TmrRegistryWriter`.
- **Acceptance:** TC-7.5 sole-writer enforced (lint + runtime); never defaults to `false`; predicates receive resolved values only.
- **implementation_status:** partial — `criticality_classifier.py` EXISTS (60 lines; spec: "already the sole writer today; it resolves unknown system records conservatively"); resolution-record path + writer API migration are new
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-7.5] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_criticality_resolution.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_criticality_resolution.py -q`]
- **architecture_refs:** [`.architecture/structured/components/tmr-provenance.md`]
- **Invariants:** INV-003 · **Surfaces:** cli_command · **Dependencies:** W0-13, B-1

#### B-5: promotion_gate.py — local evaluation + intent construction
- **Effort:** L · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §9 (enforcement points: finalize check vs completion gate, quantifier over `critical_seam != false`, defense in depth, intent field list — the SOLE binding set, local generation re-check)
- **Concerns:** RC-1 (evaluation side), CB-4, SEC-1 (intent binding)
- **Description:** Local promotion evaluation over MW-005 predicates + MW-009 snapshots; finalize-transition check (registry validity + verification plan, NO run evidence — deadlock rule); completion-gate quantifier (`null` cannot escape); JCS promotion-intent construction binding the complete §9 field list (registry hash/version, card set, evidence-index hash, receipt ids, ConOps evidence hash, session id, CAS version, snapshot_id + authority root, spine_manifest_hash, successor_transfer_set, authorization_set_hash); pre-dispatch local generation re-read.
- **Acceptance:** TC-8.2 end-to-end local/remote split; TC-8.3 gateway replay blocked; TC-8.4/8.5 mutation tests; byte-identical `successor_transfer_set` copy from provisional plan (mismatch = `intent-mismatch`).
- **implementation_status:** greenfield — `promotion_gate.py` absent (verified)
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-8.0, TC-8.2–TC-8.9, TC-INV-018 (intent edge), DF-5 (gate side)] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_promotion_gate.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_promotion_gate.py -q`]
- **architecture_refs:** [`.architecture/structured/components/tmr-provenance.md`, `.architecture/structured/flows.md`, `.architecture/primer.md`]
- **Invariants:** INV-018 (edge), INV-020, INV-021 · **Surfaces:** cli_command · **Dependencies:** W0-8, W0-9, B-2, B-3, B-7 (ConOps evidence hash), B-8 (spine_manifest_hash)

#### B-6: Promotion remote sequence + authority-committed inheritance
- **Effort:** L · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §9 (inheritance protocol, derived-read consistency, local mirrors, retention/GC, failure ownership), §11.2 (snapshot registration sequencing), §5.2 (local reconciliation states)
- **Concerns:** RC-1 (THE core theme), SEC-3, FM-3
- **Description:** Wire the canonical runtime sequence: local eval → REMOTE snapshot registration → intent → REMOTE prepare → REMOTE commit (all via MW-007 + MW-011); successor derivation from authority commit record at required read-version; startup reconciliation gate before TMR compilation/card emission/promotion evaluation; mirror materialization under StateTransaction with `LocalReconciliationResult` states; `local-mirror-stale` blocking + idempotent rematerialization; failure-ownership table (every partial outcome names owner + action).
- **Acceptance:** TC-8.10 prepare-without-snapshot rejected; TC-8.13 parent completion never observable without transfer facts + stale-mirror blocks; TC-8.14 rematerialization; TC-8.15 retention/GC protection; DF-11 ownership table; DF-13 tampered-leaf/root + conductor-only critical evidence + journal-head anchoring.
- **implementation_status:** greenfield
- **verification_mode:** automated-integration · **scope:** targeted
- **test_refs:** [TC-8.10–TC-8.18, DF-11, DF-13] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_promotion_sequence.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_promotion_sequence.py -q`]
- **architecture_refs:** [`.architecture/structured/flows.md`, `.architecture/structured/components/gauntlet-persistence.md`, `.architecture/structured/components/tmr-provenance.md`]
- **Invariants:** INV-017, INV-019, INV-020 · **Surfaces:** outbound_integration, cli_command · **Dependencies:** B-5, W0-12, W0-10

#### B-7: ConOps walkthrough — script gen + typed predicates + evidence binding
- **Effort:** L · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §11.1 (script, evidence types, typed predicates, lifecycle link to Phase 7 ConOps, evidence binding, provenance classes, row-identity ownership)
- **Concerns:** SEC-3 (provenance classes), DD-3 (row identity)
- **Description:** `conops-walkthrough.md` generation from happy-path spine tests (deriving rows SOLELY from `roadmap/conops.md` — row-identity owner); typed expected-observation predicates per class (API/CLI/GUI/human-judgment routing to §5.3 rubric); evidence binding (row_id, script hash, operator identity, timestamp, artifact hash, provenance class); close-verifier rejection of missing/stale/swapped/wrong-script/non-matching evidence; canonical hash-regeneration order.
- **Acceptance:** TC-9.3 swapped/stale evidence rejected; TC-9.4 typed-predicate mismatch + human-judgment routing; "worked fine" prose fails; critical-seam conductor-only evidence insufficient (condition 6 wiring).
- **implementation_status:** partial — Phase 7 ConOps derive exists (`validation_emission.py:688` `handle_derive_conops`, hash-bound); walkthrough layer + typed predicates are new and EXTEND it (never replace)
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-9.0–TC-9.6] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_conops_walkthrough.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_conops_walkthrough.py -q`]
- **architecture_refs:** [`.architecture/structured/components/validation-emission.md`, `.architecture/structured/flows.md`]
- **Invariants:** INV-013, INV-021 (provenance) · **Surfaces:** cli_command · **Dependencies:** W0-2, W0-8

#### B-8: Spine artifacts — close-binding DAG + BOOT-SPINE
- **Effort:** M · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §11.2 (spine-core → evidence-index → spine-manifest DAG, reverse edges forbidden, hash projections)
- **Concerns:** CB-3 (core)
- **Description:** Three-artifact production chain with schema-enforced acyclic references; `spine-core.json` (bindings + pointers + ConOps script hash), `evidence-index.json` (spine_core_hash + per-item evidence hashes + provenance classes), `spine-manifest.json` (three hashes only); BOOT-SPINE transitive validation (schema + spine_core_hash + evidence_index_hash + node-registry hash).
- **Acceptance:** TC-10.3 reverse edge rejected; DF-18 included/excluded envelope-field mutations under real generators; predecessor-linkage rule (missing-with-predecessor blocks).
- **implementation_status:** greenfield
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-10.0, TC-10.2, TC-10.3, TC-INV-018, DF-18] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_spine_artifacts.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_spine_artifacts.py -q`]
- **architecture_refs:** [`.architecture/structured/components/validation-emission.md`, `.architecture/primer.md`]
- **Invariants:** INV-018 · **Surfaces:** cli_command · **Dependencies:** W0-2, W0-6

#### B-9: Contract boundary — registry, capability probes, plan lint
- **Effort:** L · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §8.2 (complete consumed-contract registry — 9 contracts, probes prove capability not presence, behavior fingerprint, capability absence rule), §5.1 (owner: fizzy rows)
- **Concerns:** SEC-5 (core), CB-1 (partial), DD-3 (registry enumeration)
- **Description:** Probe implementation for all 9 consumed contracts (signed challenge-response + negative probes + `schema_sha256` behavior fingerprint pinning + prepare/commit revalidation); registry-vs-`contract-boundary.md` drift check (fails reconciliation); execution-plan lint failing tasks scoped to fizzy-repo files; per-delta G3 tracking pointers.
- **Acceptance:** TC-16.0–16.4 (incompatible contract blocks advance; prepare-boundary test); TC-3.3 remote half (`live-preflight-unavailable` vs local deferred); DF-3 fingerprint drift → `state-stale`; DF-16 contract-list drift test.
- **implementation_status:** partial — `contract-boundary.md` EXISTS (Phase 4 artifact, hash-bound into arch fingerprint); probe CODE + lint are new
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-16.0–TC-16.4, TC-3.3, DF-3, DF-16 (registry half)] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_contract_boundary.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_contract_boundary.py -q`]
- **architecture_refs:** [`.architecture/structured/components/harness-hooks.md`, `.architecture/structured/flows.md`, `.architecture/concerns.md`]
- **Invariants:** INV-007, INV-010 · **Surfaces:** outbound_integration, cli_command · **Dependencies:** W0-11, W0-12

#### B-10: Regime lifecycle (§18) — attestation, backfill, cross-regime transfer
- **Effort:** L · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §18 (rollout cutoff consumption, regime attestation, historical lookup/backfill, `creation-unprovable`, pre-rollout immutability, branching, cross-regime `obligation-transfer-v1`), §1 (session lifecycle record), §3 (BOOT-REGISTRY branch)
- **Concerns:** FM-1 (core), FM-2 (core), US-2
- **Description:** Regime materialization comparing authority-attested creation time against validated `hardening-rollout-policy-v1` (binding policy identity + hash + keyset epoch into the materialization record); mirror validation against signed attestation; epoch-zero pre-rollout handling (immutable); legacy materialization ONLY for pre-contract sessions via historical lookup; `creation-unprovable` operator disposition; cross-regime deferral solely via `obligation-transfer-v1` with `conductor-produced` provenance cap.
- **Acceptance:** TC-0.4 regime branch (legacy/hardened/corrupt distinguished by regime, never absence); TC-0.10 epoch-zero + immutability; DF-10 regime-pair transfer matrix; local timestamp/manifest rewrite cannot decide regime.
- **implementation_status:** greenfield
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-0.4, TC-0.10, DF-10] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_regime_lifecycle.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_regime_lifecycle.py -q`]
- **architecture_refs:** [`.architecture/structured/components/debate-session.md`, `.architecture/primer.md`]
- **Invariants:** INV-002, INV-003 (authority rows), INV-014 · **Surfaces:** startup_migration, outbound_integration · **Dependencies:** W0-11, W0-12
- **External dependency (NOT a task):** one-time rollout-policy issuance is fizzy/operator-side setup (§18) — recorded on roadmap, out of plan scope.

#### B-11: Phase 8 verification subflow migration (OR-3 / DF-20)
- **Effort:** M · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §8.1 U1 (subflow, `current_step: verification` sole field), lifecycle-state migration block, §6.1 (doc ownership — coordinated with A-5)
- **Concerns:** — (operator decision CON-002 resolution; .architecture CON-002/FIND-002)
- **Description:** Atomic migration `current_phase: verification` → `{current_phase: implementation, current_step: verification}` preserving artifacts + board state; idempotent single `phase8_subflow_migration` journey event (zero additional on rerun); post-migration rejection of every new `current_phase: verification` write; canonical-order validator normalizes historical `implementation → verification` transitions as legacy subflow events; SKILL.md canonical-order text updated.
- **Acceptance:** DF-20 all four guarantees red-green; resume checker passes an `implementation → (subflow) → complete` journey; migrated session resumes cleanly.
- **implementation_status:** greenfield (migration) over partial surface — the mismatch exists today (`SKILL.md:75-108` vs `phases/09-verification.md:184-198`, .architecture FIND-002)
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [DF-20, TC-1.0 (inventory leg)] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_phase8_subflow_migration.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_phase8_subflow_migration.py -q`]
- **architecture_refs:** [`.architecture/concerns.md`, `.architecture/structured/components/debate-session.md`]
- **Invariants:** INV-002 · **Surfaces:** startup_migration · **Dependencies:** none hard (coordinates with A-5 doc move)

---

## Workstream C — G5 Debate Efficiency

#### C-1: reconcile_derived.py — 4 adapters + lineage + snapshot consistency
- **Effort:** L · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §12.1 (per-adapter dirty contracts, semantic fingerprints, lineage-map artifact, source-snapshot consistency, fail-closed unavailable adapter)
- **Concerns:** US-3 (partial), DD-3 (drift check consumer)
- **Description:** In-process adapter registry (tests-pseudo, tmr-registry, architecture-invariants, node-registry) with per-adapter dirty contracts + `semantic_binding_fingerprint`; `reconciliation/lineage-map.json` (§1 envelope) authored at refactor time, validated both-resolve; ONE immutable source snapshot per run (git tree hash), mixed-generation invalidation; §1-envelope report bound to exact spec hash; `--self-check` for BOOT-RECON; hosts B-9's contract-list drift check.
- **Acceptance:** TC-13.3/13.5 rename-without-lineage dirty despite resolving anchor; TC-13.7 snapshot consistency + lineage artifact; DF-16 ConOps row mutation; DF-19 lineage envelope/hash binding + mapping kinds.
- **implementation_status:** greenfield — `reconcile_derived.py` absent (verified)
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-13.0, TC-13.2–TC-13.7, DF-16, DF-19] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_reconcile_derived.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_reconcile_derived.py -q`]
- **architecture_refs:** [`.architecture/structured/components/tmr-provenance.md`, `.architecture/structured/components/plan-analysis.md`, `.architecture/patterns.md`]
- **Invariants:** INV-013, INV-022 (fingerprint consumption) · **Surfaces:** cli_command · **Dependencies:** W0-2, W0-4

#### C-2: Debate node registry — snapshot + hash-chained event log
- **Effort:** M · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §10.2 (debate-nodes.json envelope snapshot, `node_content_hash` naming, event log, round metrics, quarantine, lifecycle rule)
- **Concerns:** RC-3 (coupled pair: snapshot + event log)
- **Description:** Versioned §1-envelope snapshot (`payload.nodes[]` settled/volatile/derived) + hash-chained `debate-nodes.events.jsonl` (MW-003) under one StateTransaction; canonical leaf-heading extraction; checkpoint/resume lifecycle with durable manifest reference + fail-closed chain validation; round-metrics accumulation (KPI-7 baseline).
- **Acceptance:** TC-12.3 chain break detected; corrupt artifacts preserved in place with named quarantine status; resume restores split exactly.
- **implementation_status:** greenfield
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-12.0, TC-12.2, TC-12.3] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_node_registry.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_node_registry.py -q`]
- **architecture_refs:** [`.architecture/structured/components/debate-session.md`, `.architecture/structured/components/gauntlet-persistence.md`]
- **Invariants:** INV-008 (consumer), INV-013 · **Surfaces:** cli_command · **Dependencies:** W0-4, W0-6

#### C-3: Freeze enforcement — debate.py payload assembly seam
- **Effort:** M · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §10.1 (node definition, freeze eligibility, content hash, enforcement)
- **Concerns:** — (US-11)
- **Description:** `debate.py` payload assembly excludes frozen nodes (one-line stub: node_id + settled round + hash); payload diffable against freeze list; changed frozen-node hash blocks dispatch until reopened by named concern; unresolvable critique anchors block freezing.
- **Acceptance:** TC-11.3 frozen-bytes mutation blocks dispatch; TC-11.4 real parser on induced fragments; round N+1 carries exactly the volatile surface.
- **implementation_status:** partial — `debate.py` exists (payload assembly at `debate.py:1086-1227`); zero freeze logic today (grep 'frozen|freeze' = 0, verified)
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-11.0, TC-11.2–TC-11.4] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_freeze_payload_assembly.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_freeze_payload_assembly.py -q`]
- **architecture_refs:** [`.architecture/structured/components/debate-session.md`, `.architecture/structured/flows.md`]
- **Invariants:** INV-013 · **Surfaces:** cli_command · **Dependencies:** C-2

#### C-4: False-convergence guard — quorum, press, Phase 4 exit gate
- **Effort:** L · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §12.2 (three convergence requirements, executable quorum, round-lifecycle gate, press mechanization)
- **Concerns:** DD-1 (core)
- **Description:** Computed quorum (distinct identities × registry-validated families, content-derived verdicts override contradicting `agreed` flags → registry event); convergence requires clean reconciliation report for the EXACT agreed spec hash; Phase 4 exit gate binding claimed rounds to authority round records; press mechanization (`MIN_PRESS_JUSTIFICATION_CHARS = 280` NFC, structured verdict, sustain-cites-volatile-node, revise-has-source-bound-finding).
- **Acceptance:** TC-14.2 card-5715 R3/R7 replays flagged; TC-14.4 failed press excludes AGREE; TC-14.3/14.5 real convergence evaluator on induced round files; DF-15 induced round registries (duplicates, false agreed, missing board records).
- **implementation_status:** greenfield — convergence today is prose-checked (this session's own 4 live false-convergence instances are the fixture corpus)
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-14.0, TC-14.2–TC-14.6, DF-15] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_convergence_guard.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_convergence_guard.py -q`]
- **architecture_refs:** [`.architecture/structured/components/debate-session.md`, `.architecture/structured/components/models-providers.md`]
- **Invariants:** INV-013 · **Surfaces:** cli_command, outbound_integration · **Dependencies:** C-1, C-2

#### C-5: Critic-runner stdout contract + provenance-coupled salvage
- **Effort:** M · **Test Strategy:** test-first · **behavior_change:** true
- **Spec refs:** §12.3 (strict grammar, shared parser, salvage flow, prompt requirements)
- **Concerns:** DD-4 (core)
- **Description:** One shared parser (`[AGREE]` xor critique+`[SPEC]`, line-start markers, first-wins, duplicate-conflict = invalid, size cap, escape rule) with fixture tests; `debate_return_quality` invalid marking; salvage flow: original path + SHA-256 at discovery + timestamp + dispatch id, copy + decisions-log entry published through ONE StateTransaction; agentic-CLI prompts demand stdout-only.
- **Acceptance:** DF-17 parser edge fixtures + crash-injected salvage (reader never sees artifact without provenance record); salvaged report = violation evidence, never raw return.
- **implementation_status:** partial — dispatch/return handling exists in `models.py`/fizzy round machinery (R3 gemini salvage was manual — the live incident this mechanizes); shared parser + transactional salvage are new
- **verification_mode:** automated-unit · **scope:** targeted
- **test_refs:** [TC-INV-015, DF-17] · **test_files:** [`skills/adversarial-spec/scripts/tests/test_critic_output_contract.py`]
- **verify_commands:** [`uv run pytest skills/adversarial-spec/scripts/tests/test_critic_output_contract.py -q`]
- **architecture_refs:** [`.architecture/structured/components/models-providers.md`, `.architecture/structured/components/debate-session.md`]
- **Invariants:** INV-015 · **Surfaces:** cli_command · **Dependencies:** W0-2, W0-4

---

## Dependency Graph (summary)

```
B-1 ──► W0-8, W0-13, B-2/3/4
W0-1 ──► W0-2 ──► W0-3/W0-4/W0-7 ──► (fanout)
W0-4 ──► W0-6, W0-9, W0-10, C-1, C-2, C-5
W0-7 ──► W0-9, W0-11, A-6
W0-10 + W0-7 + W0-2 ──► W0-12 ──► B-6, B-9, B-10
W0-13 ──► B-2, B-3, B-4
A-1 ──► A-3 ──► A-4;  A-1 ──► A-5
B-2 + B-3 + B-7 + B-8 ──► B-5 ──► B-6
C-2 ──► C-3;  C-1 + C-2 ──► C-4
A-7 (bootstrap) ⇐ merge point: W0-11, A-1, A-4, B-8, C-1
W0-15 (adverse suite) ⇐ W0-4, W0-5, W0-9, W0-10, W0-12
```

Merge points by risk: (1) B-5/B-6 promotion path (highest — merge first), (2) A-7 bootstrap (integrates 5 streams), (3) W0-15 adverse suite (proves the substrate), (4) C-4 convergence guard.

## DF register mapping (pre-load gate 1 — register-vs-plan diff)

| DF | TCOV finding # | Obligation | Task(s) carrying it in `tested_by` |
|---|---|---|---|
| DF-1 | 9 | envelope byte-level conformance suite | W0-2 |
| DF-2 | 11 | trusted time / release bootstrap / key lifecycle | W0-7, W0-11 |
| DF-3 | 12 | capability challenge + behavior fingerprint | W0-12, B-9 |
| DF-4 | 13 | TrustPolicy snapshot full matrix | W0-7, W0-9 |
| DF-5 | 14 | promotion predicate mutation matrix | W0-8, B-5 |
| DF-6 | 15 | StateTransaction completeness | W0-4 |
| DF-7 | 16 | TmrRegistryWriter + board upsert | W0-13, B-2 |
| DF-8 | 17 | device/mount-boundary traversal | W0-5 |
| DF-9 | 18 | per-fact authority matrix consumer tests | W0-14 |
| DF-10 | 20 | cross-regime matrix | B-10 |
| DF-11 | 21 | partial-outcome ownership table | W0-10, B-6 |
| DF-12 | 22 | harness comparability | A-4 |
| DF-13 | 23 | evidence security remainder | B-6 |
| DF-14 | 24 | waiver protocol remainder | A-6 |
| DF-15 | 25 | quorum + arch-round lifecycle | C-4 |
| DF-16 | 26 | contract registry + row ownership drift | C-1, B-9 |
| DF-17 | 27 | critic grammar + salvage transaction | C-5 |
| DF-18 | 28 | DAG projection oracle | B-8 |
| DF-19 | 29 | lineage artifact oracle | C-1 |
| DF-20 | v9.1 | Phase 8 subflow migration mechanics | B-11 |

**All 20 families mapped; zero unmapped rows.** (Blocking rule satisfied — no silent drops.)

## Invariant coverage (all 24)

INV-001 A-1/A-3 · INV-002 W0-2/A-6/A-7/B-10/B-11 · INV-003 W0-13/W0-14/B-2/B-3/B-4/B-10 · INV-004 W0-3/W0-12 · INV-005 W0-2 · INV-006 W0-5/W0-7/A-6 · INV-007 W0-12/B-9 · INV-008 W0-4/W0-13/C-2/W0-15 · INV-009 W0-6/W0-10/B-3 · INV-010 W0-3/W0-7/A-1/A-4/B-9 · INV-011 A-2 · INV-012 W0-4/W0-5 · INV-013 W0-6/W0-11/A-1/A-5/B-2/B-7/C-1/C-2/C-3/C-4 · INV-014 W0-11/A-7/B-10 · INV-015 C-5 · INV-016 W0-3 · INV-017 W0-10/W0-12/B-6 · INV-018 B-5/B-8 · INV-019 W0-12/B-6 · INV-020 W0-9/B-5/B-6/W0-15 · INV-021 W0-8/B-5/B-7/W0-15 · INV-022 C-1 · INV-023 W0-2 · INV-024 W0-7/W0-9/B-1

No uncovered invariant.

## Uncovered Concerns

- **ACK-1** — deliberate fail-closed tradeoffs; acknowledged design decisions, not buildable work. No task by design.
- All other 24 themes map to ≥1 task above.

## Middleware-creator readiness

MW-001→W0-2 · MW-002→W0-4 · MW-003→W0-6 · MW-004→W0-7 · MW-005→W0-8 · MW-006→W0-11 · MW-007→W0-12 · MW-008→W0-3 · MW-009→W0-9 · MW-010→W0-13 · MW-011→W0-10. Each candidate ID appears in its task title/metadata at emission; each task declares `test_files` usable as `test_suite_path`.

## Scope closure

- **Active:** W0, A, B, C as listed.
- **Deferred (explicitly out of slice):** §13 usage router (own session; parked files return there as verify/port — phantom-hole rule), §13.1 perf envelope (measurement-first pass), G3 leaf-blob snapshot registration (consumed-contract extension point), rollout-policy one-time issuance (fizzy/operator-side external dependency), mapcodebase refresh (discharged externally).
- **Excluded:** G4 dispatch reliability; fizzy-repo file changes (plan lint enforces).
- **Operator-approved exceptions:** none.

## Over-decomposition check

38 tasks vs 19 spec sections (threshold 2× = 38): at the line, justified by 128 TCs / 24 invariants / 20 DF families / the 1:1 MW-card requirement (middleware-creator contract forbids merging substrate tasks). No same-section S-effort duplicates to merge.
