#!/usr/bin/env python3
"""Emit the schema-3 (altitude) fizzy-plan.json for post-fable-hardening-skill.

Re-runnable: rebuilds the altitude tree from execution-plan data, calls
mini_spec_emission.emit_fizzy_plan, then post-processes bindings/definitions
with the plan's REAL test files and verify commands (the emitter's defaults
point at tests/test_<tid>.py, which is not this repo's layout), rewrites the
per-node artifacts with substantive content, recomputes their hashes with the
emitter's own primitive, and self-checks.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "skills/adversarial-spec/scripts"))
import mini_spec_emission as mse  # noqa: E402

SLUG = "post-fable-hardening-skill"
SESSION = "adv-spec-202607060132-post-fable-hardening-skill"
SPECDIR = REPO / ".adversarial-spec/specs" / SLUG
TESTS = "skills/adversarial-spec/scripts/tests"

DS = json.loads((SPECDIR / "dependency-semantics-draft.json").read_text())
DEPS = {t["task_id"]: t["depends_on"] for t in DS["tasks"]}
WS = {t["task_id"]: t["workstream"] for t in DS["tasks"]}

# tid: (title, description, [acceptance], effort, strategy, mode, scope,
#       impl_status, impl_evidence, [test_refs], [test_files basenames],
#       [concern_refs], [invariant_refs], [surface_scope], [arch_refs], [realizes], wave)
N = {
"W0-1": ("Scaffold hardening package + Python 3.14 floor",
 "Create skills/adversarial-spec/scripts/hardening/ per the target-architecture component tree; bump requires-python to >=3.14; pin rfc8785==0.1.4 + cryptography==49.0.0; clean-env wheel-install test. No upward import from gauntlet.",
 ["hardening package imports cleanly on 3.14", "uv run adversarial-spec --help still works (symlink bridge preserved)", "clean-env wheel-install test green"],
 "M","test-after","automated-unit","targeted","greenfield",
 "no hardening/ dir exists (ls -> ENOENT, verified 2026-07-21)",
 ["TC-0.0"],["test_hardening_package.py"],[],[],["cli_command"],
 [".architecture/filesystem-map.md",".architecture/primer.md"],["US-0"],0),
"W0-2": ("MW-001 StrictArtifactCodec + canonical_sets",
 "artifacts.py + canonical_sets.py: bounded strict decode (dup-member/NaN/BOM/surrogate/negative-zero rejection), schema validation, RFC 8785 JCS, content-hash verify with spec-exact exclusions, domain-prefix signature bytes, authority-signed/local-derived profiles, canonical_set() with bytewise order + duplicate REJECTION, discriminated authorization-fact variants (OR-1, structural absence).",
 ["byte-level conformance suite (DF-1) green incl. signed-bytes and profile cases", "provisional vs committed deferral facts hash differently", "duplicate set members rejected, never deduplicated"],
 "L","test-first","automated-unit","targeted","greenfield",
 "no codec exists; nearest prior art gauntlet/persistence.py:560-583 stays untouched",
 ["TC-INV-005","TC-INV-020","TC-INV-023"],["test_strict_artifact_codec.py","test_canonical_sets.py"],
 ["CB-2","SEC-1"],["INV-002","INV-005","INV-020","INV-023"],["cli_command"],
 [".architecture/structured/components/gauntlet-persistence.md",".architecture/primer.md",".architecture/patterns.md"],["US-8","US-15"],0),
"W0-3": ("MW-008 CliBoundary",
 "cli_boundary.py: shared strict argparse (allow_abbrev=False, unknown-arg rejection), one structured result envelope per invocation, exit mapping 0/1/2 with blocking precedence, no env-var gate inputs.",
 ["abbreviation and unknown args rejected with envelope output", "every invocation emits exactly one result envelope", "--help is a successful help result"],
 "M","test-after","automated-unit","targeted","greenfield",
 "no shared CLI adapter; validation_emission.py:3423 has its own _Parser (stays)",
 ["TC-INV-016","TC-INV-004"],["test_cli_boundary.py"],["CB-1","FM-3"],["INV-004","INV-010","INV-016"],["cli_command"],
 [".architecture/structured/components/validation-emission.md",".architecture/patterns.md"],["US-0"],0),
"W0-4": ("MW-002 DurableStateStore + StateTransaction",
 "state_store.py: persistent-identity fcntl sidecar locks, expected-hash CAS, atomic single-file writes, repo-scoped .txn/ coordinator with leases, canonical bytewise lock order, PREPARED/PUBLISHING/COMMITTED roll-forward recovery, reader release-recover-retry, transaction-corrupt terminal quarantine (non-waivable), reachability-only GC.",
 ["DF-6 completeness matrix green (reversed-lock-order, held-lock timeout, sidecar attacks, GC-vs-lease)", "crash at every protocol boundary recovers or quarantines, never mixed state", "readers never observe two generations"],
 "L","test-first","automated-unit","targeted","greenfield",
 "gauntlet/persistence.py:74-152 protects single files only; no coordinator exists",
 ["TC-1.4","TC-INV-008","TC-INV-012"],["test_durable_state_store.py","test_state_transaction.py"],
 ["RC-3","CB-2"],["INV-008","INV-012"],["cli_command","startup_migration"],
 [".architecture/structured/components/gauntlet-persistence.md",".architecture/concerns.md",".architecture/structured/flows.md"],["US-8","US-12"],0),
"W0-5": ("Safe-path resolver + filesystem capability probes",
 "Per-component dir_fd walk with O_NOFOLLOW + fstat device/mount validation (normative); ..-, absolute-, cross-session targets fail closed; bootstrap lock-capability probe proving cross-process shared/exclusive semantics; filesystem-capability-unsupported named failure.",
 ["intermediate-symlink substitution blocked (TC-1.5)", "induced submount rejected (DF-8)", "unsupported filesystem is a named capability failure, never silent"],
 "M","test-first","automated-unit","targeted","greenfield",
 "no descriptor-relative walker in repo; spec notes final-component checks insufficient",
 ["TC-1.5","TC-INV-012"],["test_safe_paths.py"],["US-1-theme"],["INV-006","INV-012"],["cli_command","startup_migration"],
 [".architecture/structured/components/gauntlet-persistence.md",".architecture/primer.md"],["US-0"],0),
"W0-6": ("MW-003 HashChainedJournal",
 "journal.py: logical append (each event hashes predecessor), chain verification, event-head projection, external-anchor record emission for authority-side anchoring.",
 ["chain break detected at unit level", "anchored-head verification round-trips"],
 "M","test-after","automated-unit","targeted","greenfield",
 "provenance_journal.py:77-362 is TMR-specific; generic substrate absent",
 ["TC-12.3","TC-INV-009"],["test_hash_chained_journal.py"],["SEC-3","RC-3"],["INV-009","INV-013"],["cli_command"],
 [".architecture/structured/components/tmr-provenance.md",".architecture/structured/components/gauntlet-persistence.md"],["US-12"],0),
"W0-7": ("MW-004 ReceiptVerifier + TrustPolicy",
 "receipts.py + trust_policy.py: trusted-key lookup from launcher config, exact-byte ed25519 verification (domain prefix || JCS minus signature), THEN purpose-scoped TrustPolicy authorization under immutable policy identity + hash; purpose-preserving chained keyset rotation; full 5.4 rejection-set semantics.",
 ["wrong-purpose key rejected across all receipt kinds (TC-15.8)", "DF-2 rotation/wrong-root/epoch-chain cases green", "signature validity without purpose authorization never authorizes"],
 "L","test-first","automated-unit","targeted","greenfield",
 "no signature verification exists in skill runtime (cryptography: packaging only)",
 ["TC-15.3","TC-15.8","TC-INV-006"],["test_receipt_verifier.py","test_trust_policy.py"],
 ["SEC-1","SEC-2","SEC-4"],["INV-006","INV-010","INV-024"],["cli_command","outbound_integration"],
 [".architecture/primer.md",".architecture/structured/components/telegram-usage.md",".architecture/patterns.md"],["US-15"],0),
"W0-8": ("MW-005 PromotionPredicates (pure)",
 "predicates.py: pure functions over validated types. is_concrete exact enum equality; is_promotion_ready six typed conditions incl. provenance condition 6; is_obligation_satisfied with critical_seam != null precondition and independent skip/deferred disjuncts (provisional pre-commit / committed post-commit, parent-scoped); select_for_verification.",
 ["DF-5 mutation matrix green (closed-enum rejection, null-seam override)", "TC-8.9 identity mutants rejected", "TC-7.3 selection-predicate mutants detected"],
 "L","test-first","automated-unit","targeted","greenfield",
 "predicates exist only as spec prose; no predicates.py",
 ["TC-7.2","TC-7.3","TC-8.9","TC-INV-021"],["test_promotion_predicates.py"],
 ["CB-4","RC-1"],["INV-021"],["cli_command"],
 [".architecture/structured/components/tmr-provenance.md",".architecture/primer.md"],["US-8"],0),
"W0-9": ("MW-009 AuthorizationSetBuilder",
 "authorization_set.py: validates receipts + successor inherited-obligation records against ONE registry generation into immutable ValidatedAuthorizationSet with authorization_set_hash per the exact spec formula; consumes TrustPolicySnapshot; emits canonical provisional transfer plan; obligation policy vs trust policy separation.",
 ["mixed-generation/caller-curated sets structurally impossible", "shuffled/duplicated facts rejected", "provisional vs committed sets hash differently (OR-1)"],
 "L","test-first","automated-unit","targeted","greenfield",
 "no builder exists",
 ["TC-8.9","TC-15.8","TC-INV-020","TC-INV-024"],["test_authorization_set_builder.py"],
 ["SEC-1","CB-2"],["INV-020","INV-024"],["cli_command"],
 [".architecture/structured/components/tmr-provenance.md",".architecture/primer.md",".architecture/patterns.md"],["US-8","US-15"],0),
"W0-10": ("MW-011 DurableOperationJournal",
 "operation_journal.py (imports no transport): operation_id + contract id + behavior fingerprint + canonical request hash journaled + fsynced BEFORE dispatch; intent-durable/in-flight/uncertain/resolved state machine; PromotionSequenceResult derivation from record absence; restart recovery.",
 ["crash before vs after dispatch distinguished by record presence (TC-8.12)", "same-id different-bytes retry = intent-mismatch", "DF-11 failure-injection table asserts owner/action/state"],
 "M","test-first","automated-unit","targeted","greenfield",
 "no operation journal exists",
 ["TC-8.12","TC-INV-017"],["test_operation_journal.py"],
 ["RC-2","FM-3","CB-1"],["INV-009","INV-017"],["cli_command","outbound_integration"],
 [".architecture/structured/components/gauntlet-persistence.md",".architecture/structured/flows.md"],["US-8"],0),
"W0-11": ("MW-006 LocalCapabilityVerifier + trusted-time watermark",
 "local_capabilities.py: offline signature/version/freshness verification of cached capability attestations; persisted monotonic authority-time watermark; max(local clock, watermark) expiry; every capability-state maps to exactly one deterministic token; release-signature validation.",
 ["wall-clock rollback cannot extend authorization, incl. across restarts", "DF-2 skew + missing-release cases green", "TC-3.3 local deferred-for-live-preflight distinguished from remote tokens"],
 "M","test-first","automated-unit","targeted","greenfield",
 "no local capability verifier exists",
 ["TC-3.3","TC-0.10"],["test_local_capability_verifier.py"],
 ["SEC-2","FM-1","CB-1"],["INV-013","INV-014"],["cli_command","startup_migration"],
 [".architecture/primer.md",".architecture/structured/components/validation-emission.md"],["US-0","US-16"],0),
"W0-12": ("MW-007 RemoteAuthorityClient",
 "remote_authority.py: snapshot upload/finalize, prepare, commit, status reconciliation, signed challenge-response probes (+ negative probes), behavior-fingerprint pinning, over injected transports; never dispatches a recoverable mutation without a durable MW-011 intent; OR-4 recovery split (uncertain prepare replays prepare; uncertain commit uses commit-status keyed by operation_id + receipt hash).",
 ["success tokens are real values, never exception-shaped (TC-8.11)", "fingerprint drift detected as state-stale (DF-3)", "recorded-fixture probes for all 9 consumed contracts (hermetic)"],
 "L","test-first","automated-unit","targeted","greenfield",
 "models.py / gauntlet model_dispatch are LLM transports, not authority contracts (CON-009 counter-pattern)",
 ["TC-8.10","TC-8.11","TC-16.4","TC-INV-004","TC-INV-017","TC-INV-019"],["test_remote_authority_client.py"],
 ["CB-1","SEC-5","RC-1","FM-3"],["INV-004","INV-007","INV-017","INV-019"],["outbound_integration"],
 [".architecture/structured/components/models-providers.md",".architecture/concerns.md",".architecture/structured/flows.md"],["US-8","US-16"],0),
"W0-13": ("MW-010 TmrRegistryWriter + sole-writer lint",
 "tmr_registry_writer.py: the single Session-TMR-registry persistence path (read revision, validate preconditions, write under canonical lock order, bump revision); stale expected-revision rejected; classifier-relevant change invalidates dependent evidence in the same transaction; authoring-lint fails any outside write-open call site.",
 ["DF-7 stale-revision + same-txn invalidation green", "sole-writer lint catches a violating fixture module", "serves both mutation-kind owners"],
 "L","test-first","automated-unit","targeted","greenfield",
 "tmr_compile_step/provenance_journal write the roadmap-level registry; Session-TMR writer absent",
 ["TC-7.5","TC-INV-003"],["test_tmr_registry_writer.py"],
 ["RC-3","DD-3"],["INV-003","INV-008"],["cli_command"],
 [".architecture/structured/components/tmr-provenance.md",".architecture/structured/components/gauntlet-persistence.md"],["US-7"],0),
"W0-14": ("Authority-matrix lint + consumer tests",
 "Matrix-driven consumer tests: for every spec 1.2 row, consumers branch only on validated authority state and fail closed with the named result on stale/missing/invalid mirror; undeclared-authority lint for security-fact reads with no declared row.",
 ["DF-9 complete row coverage", "lint catches a fixture module reading a mirror directly"],
 "M","test-first","test-producer","targeted","greenfield",
 "no authority-matrix suite exists",
 ["TC-INV-003"],["test_authority_matrix.py"],["US-4-theme"],["INV-003"],["cli_command"],
 [".architecture/primer.md",".architecture/patterns.md"],["US-8"],0),
"W0-15": ("Executable adverse suite (Phase 4 residual obligation)",
 "The executable end-to-end adverse suite deferred by Phase 4 publication: every R4 mandatory adverse case + all 13 R5 additions as executable tests over the real substrate. No design-walkthrough evidence claims.",
 ["all 13 R5 cases red-green against real modules", "R4 canonical-sequence traversal incl. snapshot registration", "suite runs under the standard runner"],
 "L","test-first","test-producer","targeted","greenfield",
 "dry-run-results.json is design-level only (its own text disclaims executed-boundary evidence)",
 ["TC-1.4","TC-1.5","TC-8.10"],["adverse/test_adverse_suite.py"],
 ["RC-1","RC-2","RC-3","SEC-3","SEC-4"],["INV-008","INV-017","INV-020","INV-021"],["cli_command","outbound_integration"],
 [".architecture/structured/flows.md",".architecture/structured/components/gauntlet-persistence.md"],["US-8"],0),
"A-1": ("gate_inventory.py + gates.json + doclint",
 "Maintain gates.json (classification enum, enforcement, owner, contract_id, violation_modes); normalized semantic form; doclint mapping phase-doc markers to gate_id; phase_docs_hash staleness; negative-test execution harness; hosts the authoring-lint family.",
 ["TC-1.0 inventory completeness incl. canonical Phases 1-8 + owned subflow units", "unmapped MUST marker fails doclint with file+line (TC-1.2)", "unclassified gate fails check"],
 "L","test-first","automated-unit","targeted","greenfield",
 "gate_inventory.py absent (verified)",
 ["TC-1.0","TC-1.2","TC-INV-001"],["test_gate_inventory.py"],
 ["DD-3","US-3-theme"],["INV-001","INV-010","INV-013"],["cli_command"],
 [".architecture/INDEX.md",".architecture/structured/components/harness-hooks.md",".architecture/patterns.md"],["US-1"],1),
"A-2": ("Hook-plane dispatcher + conformance fixtures",
 "One slice-owned dispatcher per event type in .claude/hooks/ (hook-local codec, NO skill imports); declarative versioned registration; duplicate/third-party handler detection at bootstrap; typed ALLOW/DENY/DIAGNOSTIC verdicts; blocking mode for preventive gates; shared conformance fixtures against both hook-local and skill validators; consolidate the three drifting role resolvers (CON-005).",
 ["duplicate handler detected + cross-surface fixture agreement (TC-2.4)", "internal failure becomes DENY for safety dispatchers", "async/exit-1/raise/malformed classifier cases never skip later blockers"],
 "L","test-first","automated-unit","targeted","partial",
 "hook plane exists (fizzy_payload_guard.py:86-147; three role resolvers dispatch_check.py:18-83, pipeline_continue.py:21-67, pipeline_idle_retry.py:24-70); dispatcher layer is new",
 ["TC-2.0","TC-2.2","TC-2.3","TC-2.4","TC-INV-011"],["test_hook_dispatcher_conformance.py"],
 ["DD-2"],["INV-011"],["hook-plane:cli_command"],
 [".architecture/structured/components/harness-hooks.md",".architecture/patterns.md",".architecture/concerns.md"],["US-2"],1),
"A-3": ("Judgment-gate corpus (rubrics + fixtures)",
 "rubrics/<gate_id>.md (<=~40 lines) + >=1 golden fixture per judgment gate under fixtures/conductor-competence/<gate_id>/; fixture schema validator consumed by BOOT-HARNESS.",
 ["every judgment row in gates.json has rubric + fixture", "fixtures schema-valid (TC-3.2)"],
 "M","test-after","automated-unit","targeted","greenfield",
 "no rubrics/ or fixtures/ dirs exist (verified)",
 ["TC-3.0","TC-3.2"],["test_judgment_corpus.py"],[],["INV-001"],["cli_command"],
 [".architecture/INDEX.md",".architecture/access-guide.md"],["US-3"],1),
"A-4": ("competence_harness.py + baselines + coverage manifest",
 "Harness runner: strict-JSON answer scoring (required subset next subset allowed; forbidden empty; exact citation equality; critical => >=1 required); exact arithmetic; bounded retry with attempt evidence + not-comparable threshold; coverage manifest; immutable identity-keyed baselines incl. environment fingerprint; waivable pre-session gate with MAX_PHASE_REGRESSION_POINTS=10.",
 ["vacuous [] fails critical fixtures (TC-6.4)", "missing/incompatible baseline blocks (TC-6.5)", "2-pass/2-fail scores exactly 50", "fingerprint drift => not-comparable (DF-12)"],
 "L","test-first","automated-unit","targeted","greenfield",
 "competence_harness.py absent (verified)",
 ["TC-6.0","TC-6.1","TC-6.3","TC-6.4","TC-6.5","TC-6.6"],["test_competence_harness.py"],
 ["OP-1"],["INV-010"],["cli_command"],
 [".architecture/structured/components/models-providers.md",".architecture/structured/components/telegram-usage.md"],["US-6"],1),
"A-5": ("Phase-doc spine units + 09-verification relocation",
 "Decompose phase docs into phases/<NN>-<phase>/spine.md + reference/*.md with single-owner pointers; relocate phases/09-verification.md under the Phase 8 tree with spine-step ownership + SKILL.md router update + decisions-log entries; architecture_refs resolver writing per-step context-load-manifest.",
 ["doclint pointer closure: zero dangling, exactly one owner", "09-verification.md gone from old path; router resolves (TC-4.x/5.x)", "context-load-manifest records resolved unit identities + hashes"],
 "L","test-after","automated-unit","targeted","partial",
 "flat phase docs exist; 0 spine files (verified); restructure + resolver new",
 ["TC-4.0","TC-4.2","TC-5.0","TC-5.2","TC-5.3"],["test_spine_units_closure.py"],
 ["US-3-theme"],["INV-001","INV-013"],["cli_command"],
 [".architecture/INDEX.md",".architecture/filesystem-map.md",".architecture/concerns.md"],["US-4","US-5"],1),
"A-6": ("Waiver flow: challenge, receipt acceptance, audit cache",
 "Blocking-checker challenge creation (immutable block_id, one-time nonce request, local-derived challenge envelope); receipt acceptance via MW-004 (challenge-byte binding, nonce-consumption receipt, authorization_kind precedence, non-waivable class rejection, consumption at protected transitions); nonces.jsonl audit cache; issuance idempotency by operation_id; surfacing in close report/checkpoint/card.",
 ["full 5.4 rejection set green (TC-15.x)", "wrong-block/reused-nonce replay rejected (TC-15.4)", "lost response returns original receipt by operation_id (TC-15.7)"],
 "L","test-first","automated-unit","targeted","greenfield",
 "no waiver machinery exists (telegram_bot.py is transport only)",
 ["TC-15.0","TC-15.2","TC-15.4","TC-15.7"],["test_waiver_flow.py"],
 ["SEC-4"],["INV-002","INV-006"],["cli_command","outbound_integration"],
 [".architecture/structured/components/telegram-usage.md",".architecture/structured/flows.md",".architecture/primer.md"],["US-15"],1),
"A-7": ("hardening_bootstrap.py (BOOT-* checks + live preflight)",
 "Bootstrap CLI: BOOT-GATES/HARNESS/RECON/REGISTRY/SPINE blocking + BOOT-ROUTER advisory; hermetic blocking path (no transport instantiation); --live-preflight REMOTE path via MW-007; deferred-state exit mapping by pending regime-sensitive transition; five-minute fresh-clone target; failure output contract.",
 ["fresh-clone clean run under 5 minutes with named checks (TC-0.0)", "regime branch distinguishes legacy/hardened/corrupt (TC-0.4)", "every blocking check passes under denied socket/DNS (TC-2.3)", "blocking precedence: advisory+blocking => exit 2"],
 "L","test-first","automated-integration","targeted","greenfield",
 "hardening_bootstrap.py absent (verified)",
 ["TC-0.0","TC-0.2","TC-0.4","TC-0.5","TC-0.6","TC-2.3","TC-INV-014"],["test_hardening_bootstrap.py"],
 ["FM-1","CB-1","US-3-theme"],["INV-002","INV-014"],["cli_command","startup_migration"],
 [".architecture/structured/components/validation-emission.md",".architecture/structured/components/harness-hooks.md",".architecture/filesystem-map.md"],["US-0"],1),
"B-1": ("TMR keystone-first schema extension (obligation fields)",
 "KEYSTONE-FIRST: add obligation_revision, obligation_policy_version, tmr_record_hash (+ required_liveness_class/required_environment/required_tier if absent) to Brainquarters/shared-context/test-maturity-record-schema.md FIRST, then mirror into tmr_schema.py with schema_sha256 drift tripwire. Resolves the 11 tests-spec SCHEMA GAP carries.",
 ["keystone edited before mirror (provable commit order)", "strict schema round-trip green", "obligation-identity projection hash stable under evidence-field changes"],
 "M","test-first","automated-unit","targeted","greenfield",
 "grep for all three fields = 0 in keystone AND tmr_schema.py (verified 2026-07-21)",
 ["TC-8.4"],["test_tmr_obligation_fields.py"],
 ["CB-2","DD-3"],["INV-024"],["cli_command"],
 [".architecture/structured/components/tmr-provenance.md",".architecture/primer.md"],["US-7","US-8"],0),
"B-2": ("verification_cards.py deterministic emitter + board upsert",
 "One card per qualifying TMR keyed (session_id, tmr_uid, obligation_revision, obligation_policy_version); registry_hash as provenance snapshot never key; supersede obsolete cards; pipeline_load upsert with stable local key + expected board revision; lost response resolved by authority query; board-ahead = local-mirror-stale.",
 ["identity stable across registry churn, zero duplicates (TC-7.4)", "empty selection emits no-op artifact with registry path+hash", "DF-7 stateful board fixture green"],
 "L","test-first","automated-unit","targeted","greenfield",
 "verification_cards.py absent (verified)",
 ["TC-7.0","TC-7.4","TC-7.6","TC-7.7","TC-7.8"],["test_verification_cards.py"],
 ["DD-3","RC-3"],["INV-003","INV-013"],["cli_command","outbound_integration"],
 [".architecture/structured/components/tmr-provenance.md",".architecture/structured/flows.md"],["US-7"],1),
"B-3": ("record_verification_evidence.py write-back + maturity authority",
 "The ONLY path from completed card to promotion-eligible evidence: validates card binding, evidence class, artifact hash, tmr_uid before registry update via TmrRegistryWriter; sole authorized writer of nl|acceptance -> concrete atomically with write-back.",
 ["card completion without registry update cannot count promotion-ready", "concurrency conflict retries from fresh read", "green-but-wrong evidence rejected (TC-8.4)"],
 "M","test-first","automated-unit","targeted","greenfield",
 "script absent (verified); spec names it as new sole writer",
 ["TC-7.2","TC-8.4"],["test_record_verification_evidence.py"],
 ["RC-3","DD-3"],["INV-003","INV-009"],["cli_command"],
 [".architecture/structured/components/tmr-provenance.md",".architecture/primer.md"],["US-7"],1),
"B-4": ("criticality_classifier.py resolution extension",
 "Extend existing classifier: resolution action recording rule version + source-artifact hash + architecture link for any false resolution; null preserved or resolved true otherwise; operator receipt-bound resolution decisions recorded by this sole writer; writes via TmrRegistryWriter.",
 ["sole-writer enforced by lint + runtime (TC-7.5)", "never defaults to false", "resolution records carry rule version + source hash"],
 "M","test-first","automated-unit","targeted","partial",
 "criticality_classifier.py EXISTS (60 lines; spec: already the sole writer today); resolution-record path new",
 ["TC-7.5"],["test_criticality_resolution.py"],
 ["CB-4","DD-3"],["INV-003"],["cli_command"],
 [".architecture/structured/components/tmr-provenance.md"],["US-7"],1),
"B-5": ("promotion_gate.py local evaluation + intent construction",
 "Local promotion evaluation over MW-005/MW-009; finalize-transition check (registry validity + plan, NO run evidence - deadlock rule); completion-gate quantifier over critical_seam != false; JCS promotion intent binding the complete spec-9 field list; pre-dispatch local generation re-read.",
 ["end-to-end local/remote split proven (TC-8.2)", "gateway replay blocked (TC-8.3)", "null-seam records cannot escape the quantifier", "successor_transfer_set byte-identical to provisional plan or intent-mismatch"],
 "L","test-first","automated-unit","targeted","greenfield",
 "promotion_gate.py absent (verified)",
 ["TC-8.0","TC-8.2","TC-8.3","TC-8.4","TC-8.5","TC-8.6","TC-8.9","TC-INV-018"],["test_promotion_gate.py"],
 ["RC-1","CB-4","SEC-1"],["INV-018","INV-020","INV-021"],["cli_command"],
 [".architecture/structured/components/tmr-provenance.md",".architecture/structured/flows.md",".architecture/primer.md"],["US-8"],1),
"B-6": ("Promotion remote sequence + authority-committed inheritance",
 "Wire the canonical runtime sequence (local eval -> REMOTE snapshot registration -> intent -> prepare -> commit) via MW-007/MW-011; successor derivation from authority commit record at required read-version; startup reconciliation gate; mirror materialization under StateTransaction with LocalReconciliationResult states; local-mirror-stale blocking + idempotent rematerialization; failure-ownership table.",
 ["prepare without registered snapshot rejected (TC-8.10)", "parent completion never observable without transfer facts (TC-8.13)", "rematerialization path green (TC-8.14)", "retention/GC protection (TC-8.15)"],
 "L","test-first","automated-integration","targeted","greenfield",
 "no remote promotion sequence exists",
 ["TC-8.10","TC-8.11","TC-8.12","TC-8.13","TC-8.14","TC-8.15","TC-8.16","TC-8.17","TC-8.18"],["test_promotion_sequence.py"],
 ["RC-1","SEC-3","FM-3"],["INV-017","INV-019","INV-020"],["outbound_integration","cli_command"],
 [".architecture/structured/flows.md",".architecture/structured/components/gauntlet-persistence.md",".architecture/structured/components/tmr-provenance.md"],["US-8"],1),
"B-7": ("ConOps walkthrough: script gen + typed predicates + evidence binding",
 "conops-walkthrough.md generated from happy-path spine tests deriving rows SOLELY from roadmap/conops.md; typed expected-observation predicates per class (API/CLI/GUI/human-judgment routes to rubric); evidence binding (row_id, script hash, operator identity, timestamp, artifact hash, provenance class); close-verifier rejection of stale/swapped/wrong-script evidence; canonical hash-regeneration order.",
 ["swapped/stale evidence rejected (TC-9.3)", "typed-predicate mismatch + human-judgment routing (TC-9.4)", "worked-fine prose fails", "conductor-only critical evidence insufficient"],
 "L","test-first","automated-unit","targeted","partial",
 "Phase 7 ConOps derive exists (validation_emission.py:688 handle_derive_conops); walkthrough layer new, EXTENDS it",
 ["TC-9.0","TC-9.2","TC-9.3","TC-9.4","TC-9.5","TC-9.6"],["test_conops_walkthrough.py"],
 ["SEC-3","DD-3"],["INV-013","INV-021"],["cli_command"],
 [".architecture/structured/components/validation-emission.md",".architecture/structured/flows.md"],["US-9"],1),
"B-8": ("Spine artifacts: close-binding DAG + BOOT-SPINE",
 "spine-core.json -> evidence-index.json -> spine-manifest.json with schema-enforced acyclic references and exact hash projections; BOOT-SPINE transitive validation (schema + spine_core_hash + evidence_index_hash + node-registry hash).",
 ["reverse edge rejected (TC-10.3)", "DF-18 envelope-field mutations under real generators", "missing-with-predecessor blocks"],
 "M","test-first","automated-unit","targeted","greenfield",
 "no spine artifacts exist",
 ["TC-10.0","TC-10.2","TC-10.3","TC-INV-018"],["test_spine_artifacts.py"],
 ["CB-3"],["INV-018"],["cli_command"],
 [".architecture/structured/components/validation-emission.md",".architecture/primer.md"],["US-10"],1),
"B-9": ("Contract boundary: registry, capability probes, plan lint",
 "Probe implementation for all 9 consumed contracts (signed challenge-response + negative probes + schema_sha256 behavior-fingerprint pinning + prepare/commit revalidation); registry-vs-contract-boundary.md drift check; execution-plan lint failing fizzy-repo-scoped tasks; per-delta G3 tracking pointers.",
 ["incompatible contract blocks advance (TC-16.3)", "live-preflight-unavailable vs local deferred distinguished (TC-3.3)", "fingerprint drift = state-stale (DF-3)", "contract-list drift fails reconciliation (DF-16)"],
 "L","test-first","automated-unit","targeted","partial",
 "contract-boundary.md EXISTS (Phase 4 artifact, hash-bound); probe CODE + lint new",
 ["TC-16.0","TC-16.2","TC-16.3","TC-16.4","TC-3.3"],["test_contract_boundary.py"],
 ["SEC-5","CB-1","DD-3"],["INV-007","INV-010"],["outbound_integration","cli_command"],
 [".architecture/structured/components/harness-hooks.md",".architecture/structured/flows.md",".architecture/concerns.md"],["US-16"],1),
"B-10": ("Regime lifecycle (spec 18): attestation, backfill, cross-regime transfer",
 "Regime materialization comparing authority-attested creation time against validated hardening-rollout-policy-v1 (binding policy identity+hash+keyset epoch); mirror validation against signed attestation; epoch-zero pre-rollout immutability; legacy materialization only for pre-contract sessions via historical lookup; creation-unprovable operator disposition; cross-regime deferral solely via obligation-transfer-v1 with conductor-produced provenance cap.",
 ["regime branch distinguishes by attestation never absence (TC-0.4)", "epoch-zero provisioning + immutable pre-rollout (TC-0.10)", "DF-10 regime-pair transfer matrix green", "local timestamp/manifest rewrite cannot decide regime"],
 "L","test-first","automated-unit","targeted","greenfield",
 "no regime machinery exists",
 ["TC-0.4","TC-0.10"],["test_regime_lifecycle.py"],
 ["FM-1","FM-2","US-2-theme"],["INV-002","INV-003","INV-014"],["startup_migration","outbound_integration"],
 [".architecture/structured/components/debate-session.md",".architecture/primer.md"],["US-0"],1),
"B-11": ("Phase 8 verification-subflow migration (OR-3 / DF-20)",
 "Atomic migration current_phase: verification -> {current_phase: implementation, current_step: verification} preserving artifacts + board state; idempotent single phase8_subflow_migration journey event; post-migration rejection of new current_phase: verification writes; canonical-order validator normalizes historical implementation -> verification transitions as legacy subflow events; SKILL.md canonical order updated.",
 ["all four DF-20 guarantees red-green", "resume checker passes implementation -> (subflow) -> complete journey", "migrated session resumes cleanly"],
 "M","test-first","automated-unit","targeted","greenfield",
 "the mismatch exists today (SKILL.md:75-108 vs phases/09-verification.md:184-198; .architecture FIND-002)",
 ["TC-1.0"],["test_phase8_subflow_migration.py"],
 [],["INV-002"],["startup_migration"],
 [".architecture/concerns.md",".architecture/structured/components/debate-session.md"],["US-1"],1),
"C-1": ("reconcile_derived.py: 4 adapters + lineage + snapshot consistency",
 "In-process adapter registry (tests-pseudo, tmr-registry, architecture-invariants, node-registry) with per-adapter dirty contracts + semantic_binding_fingerprint; reconciliation/lineage-map.json authored at refactor time, both-fingerprints-resolve validation; ONE immutable source snapshot per run with mixed-generation invalidation; envelope report bound to exact spec hash; --self-check for BOOT-RECON; hosts contract-list drift check.",
 ["rename without lineage dirty despite resolving anchor (TC-13.3/13.5)", "snapshot consistency + lineage artifact (TC-13.7)", "unavailable adapter blocks dispatch and convergence"],
 "L","test-first","automated-unit","targeted","greenfield",
 "reconcile_derived.py absent (verified)",
 ["TC-13.0","TC-13.2","TC-13.3","TC-13.4","TC-13.5","TC-13.6","TC-13.7"],["test_reconcile_derived.py"],
 ["US-3-theme","DD-3"],["INV-013","INV-022"],["cli_command"],
 [".architecture/structured/components/tmr-provenance.md",".architecture/structured/components/plan-analysis.md",".architecture/patterns.md"],["US-13"],1),
"C-2": ("Debate node registry: snapshot + hash-chained event log",
 "Versioned envelope snapshot (payload.nodes[] settled/volatile/derived) + hash-chained debate-nodes.events.jsonl under one StateTransaction; canonical leaf-heading extraction; checkpoint/resume lifecycle with durable manifest reference + fail-closed chain validation; round-metrics accumulation (KPI-7 baseline).",
 ["chain break detected (TC-12.3)", "corrupt artifacts preserved in place with named quarantine status", "resume restores the settled/volatile/derived split exactly"],
 "M","test-first","automated-unit","targeted","greenfield",
 "no node registry exists",
 ["TC-12.0","TC-12.2","TC-12.3"],["test_node_registry.py"],
 ["RC-3"],["INV-008","INV-013"],["cli_command"],
 [".architecture/structured/components/debate-session.md",".architecture/structured/components/gauntlet-persistence.md"],["US-12"],1),
"C-3": ("Freeze enforcement: debate.py payload assembly seam",
 "debate.py payload assembly excludes frozen nodes (one-line stub: node_id + settled round + hash); payload diffable against freeze list; changed frozen-node hash blocks dispatch until reopened by named concern; unresolvable critique anchors block freezing.",
 ["frozen-bytes mutation blocks dispatch (TC-11.3)", "real parser on induced fragments (TC-11.4)", "round N+1 carries exactly the volatile surface"],
 "M","test-first","automated-unit","targeted","partial",
 "debate.py exists (payload assembly debate.py:1086-1227); zero freeze logic (grep frozen|freeze = 0, verified)",
 ["TC-11.0","TC-11.2","TC-11.3","TC-11.4"],["test_freeze_payload_assembly.py"],
 [],["INV-013"],["cli_command"],
 [".architecture/structured/components/debate-session.md",".architecture/structured/flows.md"],["US-11"],1),
"C-4": ("False-convergence guard: quorum, press, Phase 4 exit gate",
 "Computed quorum (distinct identities x registry-validated families; content-derived verdicts override contradicting agreed flags -> registry event); convergence requires clean reconciliation report for the EXACT agreed spec hash; Phase 4 exit gate binding claimed rounds to authority round records; press mechanization (MIN_PRESS_JUSTIFICATION_CHARS=280 NFC, structured verdict rules).",
 ["card-5715 R3/R7 replays flagged (TC-14.2)", "failed press excludes AGREE from quorum (TC-14.4)", "DF-15 induced round registries green"],
 "L","test-first","automated-unit","targeted","greenfield",
 "convergence today is prose-checked; this session's 4 live false-convergence instances are the fixture corpus",
 ["TC-14.0","TC-14.2","TC-14.3","TC-14.4","TC-14.5","TC-14.6"],["test_convergence_guard.py"],
 ["DD-1"],["INV-013"],["cli_command","outbound_integration"],
 [".architecture/structured/components/debate-session.md",".architecture/structured/components/models-providers.md"],["US-14"],1),
"C-5": ("Critic-runner stdout contract + provenance-coupled salvage",
 "One shared parser ([AGREE] xor critique+[SPEC], line-start markers, first-wins, duplicate-conflict invalid, size cap, escape rule) with fixture tests; debate_return_quality invalid marking; salvage flow (original path + SHA-256 at discovery + timestamp + dispatch id, copy + decisions-log entry through ONE StateTransaction); agentic-CLI prompts demand stdout-only.",
 ["DF-17 parser edge fixtures green", "crash-injected salvage never exposes artifact without provenance record", "salvaged report recorded as violation evidence, never raw return"],
 "M","test-first","automated-unit","targeted","partial",
 "dispatch/return handling exists in models.py + fizzy round machinery (R3 gemini salvage was manual - the live incident this mechanizes); shared parser + transactional salvage new",
 ["TC-INV-015"],["test_critic_output_contract.py"],
 ["DD-4"],["INV-015"],["cli_command"],
 [".architecture/structured/components/models-providers.md",".architecture/structured/components/debate-session.md"],["US-14"],1),
}

SUBSYSTEMS = {
 "SS-W0": ("Shared hardening substrate", "adversarial_spec.hardening package: MW-001..MW-011 plus scaffold, safe paths, authority-matrix suite, and the executable adverse suite.",
           ["every MW candidate lands as its own verified component", "adverse suite green over the real substrate"],
           ["W0-%d" % i for i in range(1, 16)], ["US-0","US-7","US-8","US-12","US-15","US-16"]),
 "SS-A": ("G1 operability", "Gate inventory + doclint, hook dispatcher, judgment corpus, competence harness, spine units, waiver flow, bootstrap.",
          ["all G1 components verified; bootstrap integrates them under 5 minutes"],
          ["A-%d" % i for i in range(1, 8)], ["US-0","US-1","US-2","US-3","US-4","US-5","US-6","US-15"]),
 "SS-B": ("G2 ascending arm", "TMR keystone fields, verification cards, evidence write-back, criticality resolution, promotion local+remote, ConOps walkthrough, spine DAG, contract probes, regime lifecycle, subflow migration.",
          ["promotion path proven end-to-end against contract fixtures", "all G2 components verified"],
          ["B-%d" % i for i in range(1, 12)], ["US-0","US-1","US-7","US-8","US-9","US-10","US-16"]),
 "SS-C": ("G5 debate efficiency", "Reconciliation gate, node registry, freeze seam, false-convergence guard, critic output contract.",
          ["a full debate round exercises freeze, reconciliation, and the convergence guard"],
          ["C-%d" % i for i in range(1, 6)], ["US-11","US-12","US-13","US-14"]),
}

ALL_US = [f"US-{i}" for i in range(17)]
FULL_SUITE = f"uv run pytest {TESTS} -q"


def node_for(tid):
    (title, desc, ac, eff, strat, mode, scope, ist, iev, trefs, tfiles,
     crefs, irefs, srefs, arefs, realizes, wave) = N[tid]
    return {
        "task_id": tid, "title": title, "description": desc,
        "acceptance_criteria": ac, "effort": eff, "strategy": strat,
        "verification_mode": mode, "verification_scope": scope,
        "implementation_status": ist, "depends_on": DEPS[tid],
        "architecture_refs": arefs, "realizes_refs": realizes,
        "rationale": desc.split(".")[0],
        "children": [],
        "_extra": {
            "implementation_evidence": iev,
            "test_refs": trefs,
            "test_files": [f"{TESTS}/{f}" for f in tfiles],
            "verify_commands": [f"uv run pytest {' '.join(f'{TESTS}/{f}' for f in tfiles)} -q"],
            "concern_refs": crefs, "invariant_refs": irefs,
            "surface_scope": srefs, "wave": wave, "workstream": WS[tid],
            "tested_by": "llm", "behavior_change": tid != "W0-15",
            "exemption_reason": None,
            "verification_notes": None,
        },
    }


def build_tree():
    subs = []
    for sid, (title, desc, ac, members, realizes) in SUBSYSTEMS.items():
        subs.append({
            "task_id": sid, "title": title, "description": desc,
            "acceptance_criteria": ac, "effort": "L", "strategy": "test-first",
            "verification_mode": "automated-integration", "verification_scope": "full-suite",
            "implementation_status": "greenfield", "depends_on": [],
            "architecture_refs": [".architecture/primer.md", ".architecture/overview.md"],
            "realizes_refs": realizes, "rationale": desc.split(".")[0],
            "children": [node_for(t) for t in members],
            "_extra": {
                "implementation_evidence": "aggregation node; see child components",
                "test_refs": [], "test_files": [], "verify_commands": [FULL_SUITE],
                "concern_refs": [], "invariant_refs": [], "surface_scope": [],
                "wave": 0 if sid == "SS-W0" else 1, "workstream": sid.split("-")[1],
                "tested_by": "llm", "behavior_change": True,
                "exemption_reason": None, "verification_notes": None,
            },
        })
    return {"system": {
        "task_id": "SYS", "title": "Post-Fable Hardening skill slice (G1+G2+G5)",
        "description": "Harden the adversarial-spec skill for post-Fable conductors: mechanized gates, competence harness, V-model ascending arm with authority-committed promotion, debate freeze/reconciliation/convergence guards, over a shared hardening substrate.",
        "acceptance_criteria": ["all subsystems verified; system verification report passes; Phase 8 sweep succeeds"],
        "effort": "L", "strategy": "test-first",
        "verification_mode": "automated-integration", "verification_scope": "full-suite",
        "implementation_status": "greenfield", "depends_on": [],
        "architecture_refs": [".architecture/primer.md", ".architecture/overview.md"],
        "conops_refs": ALL_US, "user_story_refs": ALL_US,
        "rationale": "spec-final.md v9.1 root system node",
        "children": subs,
        "_extra": {
            "implementation_evidence": "system root; see subsystems",
            "test_refs": [], "test_files": [], "verify_commands": [FULL_SUITE],
            "concern_refs": [], "invariant_refs": [], "surface_scope": [],
            "wave": 0, "workstream": "SYS", "tested_by": "llm",
            "behavior_change": True, "exemption_reason": None, "verification_notes": None,
        },
    }}


def main():
    tree = build_tree()
    plan = mse.emit_fizzy_plan(tree, session_id=SESSION, slug=SLUG,
                               with_artifact_manifest=True, artifact_root=REPO)

    # collect _extra by walking the tree
    extras = {}
    def walk(n):
        extras[n["task_id"]] = n["_extra"]
        for c in n.get("children", []): walk(c)
    walk(tree["system"])

    seq = {}
    for i, task in enumerate(plan["tasks"], start=1):
        tid = task["task_id"]
        extra = extras[tid]
        task.update(extra)
        task["test_targets"] = extra["test_files"] or [TESTS]
        ds_task = next((t for t in DS["tasks"] if t["task_id"] == tid), None)
        if ds_task:
            task["scope_refs"] = ds_task["scope_refs"]
            task["active_path"] = ds_task["active_path"]
            task["safety_implements"] = ds_task["safety_implements"]
            task["safety_consumes"] = ds_task["safety_consumes"]
        # unique convention-compliant requirement ids
        task["requirement_metadata"]["requirement_id"] = f"REQ-{i}"
        task["requirement_metadata"]["owner"] = "adv-spec conductor"
        seq[tid] = i
        # real verification bindings: substantive artifact + real commands
        for kind, binding in task["verification_binding"].items():
            vc = extra["verify_commands"] if kind == "component_verification" and extra["test_files"] else [FULL_SUITE]
            art = extra["test_files"][0] if (kind == "component_verification" and extra["test_files"]) else TESTS
            binding["artifact"] = art
            binding["verify_commands"] = vc
            content = (
                f"# {tid} {kind.replace('_',' ').title()}\n\n"
                f"Task: {task['title']}\n\n"
                f"Acceptance criteria:\n" + "".join(f"- {a}\n" for a in task["acceptance_criteria"]) +
                f"\nVerify commands:\n" + "".join(f"- `{c}`\n" for c in vc) +
                f"\nEvidence: pytest output showing collected+run tests for the named files; "
                f"invariants {', '.join(extra['invariant_refs']) or 'n/a'}; "
                f"concerns {', '.join(extra['concern_refs']) or 'n/a'}.\n"
            )
            path = REPO / binding["plan_artifact"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            binding["plan_hash"] = mse._sha256_prefix_bytes(content.encode())
        # substantive definition artifact
        defpath = REPO / task["spec_refs"]["definition_artifact"]
        defcontent = (
            f"# {tid} {task['altitude'].title()} Mini-Spec\n\n"
            f"Title: {task['title']}\n\n{task['description']}\n\n"
            f"Acceptance criteria:\n" + "".join(f"- {a}\n" for a in task["acceptance_criteria"]) +
            f"\nSpec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task {tid}.\n"
            f"Implementation status: {task['implementation_status']} — {extra['implementation_evidence']}\n"
        )
        defpath.parent.mkdir(parents=True, exist_ok=True)
        defpath.write_text(defcontent)
        task["spec_refs"]["definition_hash"] = mse._sha256_prefix_bytes(defcontent.encode())
        if task["altitude"] == "system":
            task["system_spec_path"] = task["spec_refs"]["definition_artifact"]
        if task["altitude"] == "subsystem":
            task["subsystem_spec_path"] = task["spec_refs"]["definition_artifact"]

    check = mse.self_check_plan(plan)
    manifest = plan.pop("_artifact_manifest", None)
    out = SPECDIR / "fizzy-plan.json"
    out.write_text(json.dumps(plan, indent=1))
    print(json.dumps({"self_check": check, "tasks": len(plan["tasks"]),
                      "artifacts": len(manifest or [])}))


if __name__ == "__main__":
    main()
