# Test Pseudocode — Bounded Pipeline Reform & Hardening Alignment

> v2 — 2026-09-15 (R1 sync: custody boundary, evidence classes, waiver semantics, US-13..16, gate-specific binding rules, discovery scope, absent-vs-malformed version). 17 spines / 63 TCs.
> v1 — 2026-09-15. Canonical source of truth for tests; `roadmap/manifest.json` links here.
> One active `spine: true` per user story (TC-X.0 convention). Failure/branch tests cite
> `spine_of` + `spine_step_ref`. Maturity: all `nl` (roadmap phase); promotion to
> `acceptance` happens in debate.
> "Real data" for this project = the real keystone file, real repo checkouts and git
> worktrees, the live fizzy-pipeline-mcp validator, and real session logs. The packet's
> incident-derived golden fixtures (15 incidents + 3 controls) are SYNTHETIC: they prove
> validator behavior, never that a live boundary was exercised (R1, codex CRIT-3).
> Reject-code names are the 22 codes in packet `03-test-suite-contract.md` §5 (amended 2026-09-14).

---

## US-0: Bootstrap verifies the hardening toolchain (M0)

### TC-0.0: Bootstrap on a healthy checkout [spine: US-0]
**Data Strategy: REAL-DATA** — runs on the actual repo checkout with the sibling Brainquarters keystone; nothing manufactured.
spine_steps: S1 invoke bootstrap command, S2 probes run (deps, keystone sha pin, packet schemas, TMR/promotion/emitter suites), S3 ready verdict emitted
```
given: fresh checkout of adversarial-spec at HEAD, Brainquarters checked out beside it, uv env synced
when:  the documented bootstrap command runs
then:  keystone pin matches schema_sha256(); 3 packet schemas meta-validate; targeted suites green
assert: exit 0; report names each probe with pass/degraded/broken; wall time < 5 min
```

### TC-0.1: Keystone drift reported as degraded, never repaired [spine_of: TC-0.0, spine_step_ref: S2]
**Data Strategy: SYNTHETIC** — a drifted pin must be manufactured; the real keystone is pinned correctly.
```
given: a copy of the keystone with schema_sha256 altered by one hex digit (TMR_KEYSTONE_PATH override)
when:  bootstrap runs
then:  probe "keystone pin" is degraded with expected vs found hashes named
assert: exit != 0; keystone file bytes unchanged after the run (never repaired in the keystone's direction)
```

## US-1: Target-bound test obligations (M1)

### TC-1.0: Triggered test compiles into a bound TMR and round-trips [spine: US-1]
**Data Strategy: REAL-DATA** — uses this session's own tests-pseudo entries and the real compile step.
spine_steps: S1 author a triggered test (critical seam + money effect) with Outcome/Caller/Proof-target annotations, S2 compile into TMR carrying target_binding, S3 validate, dump, reload identical, S4 binding survives registry write-back
```
given: a tests-pseudo entry annotated Outcome obligation / Intended caller / Proof target
when:  tmr_compile_step compiles it and the registry is written and reloaded
then:  the TMR carries target_binding with outcome_id, caller_id, caller_kind, path_id, entrypoint, authority_ref, authority_role
assert: dump(validate(dump(record))) == dump(record); binding_version == 1; extra keys rejected (additionalProperties false)
```

### TC-1.1: Untriggered record without binding validates unchanged [spine_of: TC-1.0, spine_step_ref: S3]
**Data Strategy: REAL-DATA** — the 15-record liveness-gate dogfood registry, none of which carries a binding.
```
given: the existing dogfood tmr-registry.json (15 records, no target_binding)
when:  validated under the extended schema
then:  every record validates; target_binding_status reads legacy-unbound
assert: zero SchemaValidationError; compile echo_diff == []
```

### TC-1.2: Triggered record lacking a binding — gate-specific behavior [spine_of: TC-1.0, spine_step_ref: S3]
**Data Strategy: SYNTHETIC** — needs a record that is simultaneously triggered (spine, critical seam) and unbound.
```
given: a REAL-DATA spine record, critical_seam true, maturity concrete, target_binding null
when:  promotion validation runs under enforcement mode
then:  reject TMR_TARGET_BINDING_REQUIRED naming the trigger reason
assert: per gate — compile: warning with unresolved status (never a silent partial binding); finalize (v6): TMR_TARGET_BINDING_REQUIRED; promotion (v6): reject; at nl/acceptance in compile: warning only (US-2). The record is never presented as complete while unresolved
```

### TC-1.3: Expected target fields are in the obligation hash; observed fields are not [spine_of: TC-1.0, spine_step_ref: S4] [BVA]
**Data Strategy: SYNTHETIC** — one-field-at-a-time mutation needs exact control (OQ-1 accepted).
```
given: a bound record R and its compute_tmr_record_hash
when:  each expected field (outcome_id, caller_id, path_id, authority_ref, producer_contract.hash, consumer_contract.hash, runtime_chain_required, predecessor_path_ids) is mutated one at a time
then:  the hash changes for every expected-field mutation
when:  each observed field (run_evidence.target_observation.*, PID, start time, artifact URI) is mutated
then:  the hash is unchanged
assert: the projection field set equals keystone 2b as amended: the existing ten fields plus the COMPLETE expected-target list the spec enumerates (outcome_id, caller_id, caller_kind, path_id, entrypoint, authority_ref, authority_role, producer_contract, consumer_contract, runtime_chain_required, terminal_oracle, equivalence_group, predecessor_path_ids); the spec, not this test, owns that list; stored tmr_record_hash is never trusted over the recomputation
```

### TC-1.4: Keystone step 2 lands keystone-first with sha re-pin [spine_of: TC-1.0, spine_step_ref: S2]
**Data Strategy: REAL-DATA** — git history of Brainquarters and adversarial-spec.
```
given: the commit that adds target_binding to the canonical keystone and the commit that mirrors it
when:  test_keystone_commit_precedes_this_mirror and the sha tripwires run
then:  keystone commit timestamp <= mirror commit timestamp; KEYSTONE_SCHEMA_SHA256 == schema_sha256() == keystone header pin == machine schema $comment
assert: no unallowlisted prose copy of the keystone in either repo (lint_tmr_schema_copies)
```

## US-2: Progressive binding population (M1)

### TC-2.0: Binding populates across the maturity ladder [spine: US-2]
**Data Strategy: SYNTHETIC** — controlled records at each maturity to isolate the ladder rule.
spine_steps: S1 nl record carries identity fields only, S2 acceptance adds contracts and terminal oracle, S3 concrete carries the full set, S4 each step validates
```
given: the same obligation authored at nl, acceptance, concrete
when:  each is validated
then:  nl accepts outcome_id + caller + path with list fields defaulting to []; acceptance additionally requires producer/consumer contracts and terminal_oracle; concrete requires all fifteen
assert: list fields (predecessor_path_ids, runtime_slots, fixture_provenance) default to [] and never to null; a concrete record missing any required field is rejected naming the field
```

### TC-2.1: Missing-target diagnostic is actionable [spine_of: TC-2.0, spine_step_ref: S4]
**Data Strategy: SYNTHETIC** — a deliberately incomplete annotation.
```
given: a triggered tests-pseudo entry with Outcome obligation but no Proof target
when:  compiled
then:  the diagnostic names the test_id, the missing annotation, and the trigger that demanded it
assert: compile does not emit a partial binding silently
```

### TC-2.2: Duplicate stable ids are rejected [spine_of: TC-2.0, spine_step_ref: S2]
**Data Strategy: SYNTHETIC** — two entries deliberately share an outcome_id with different semantics.
```
given: two tests declaring outcome_id OUT-X for different observable outcomes
when:  compiled
then:  reject naming both test_ids and the colliding id
assert: same outcome_id shared by an equivalence_group member is accepted
```

## US-3: Triggered authority census (M3)

### TC-3.0: Structural trigger produces a validated census in the fingerprint [spine: US-3]
**Data Strategy: REAL-DATA** — Phase 4 run of this session against the real skill repo (multiple emitters of plan JSON: doc template and mini_spec_emission).
spine_steps: S1 trigger evaluates structural reasons, S2 census authored with every outcome-equivalent path, S3 validate_authority_paths passes, S4 census hash enters the architecture fingerprint
```
given: a change with two callable paths producing one external effect
when:  Phase 4 runs
then:  authority-paths.json has triggered:true with structural_reasons, a declared discovery scope (repos, entrypoint classes, callers searched) with evidence refs, every path bound to invariant ids and a concrete entrypoint, one target authority per outcome, unresolved uncertainty listed rather than omitted
assert: fingerprint includes the census sha256; an independent seat (not the census author) accepts that the discovery scope supports the completeness claim; re-running replaces the census atomically (no stacking). Under v6 this obligation rides the D0 decomposition artifact (no Target-Architecture lane)
```

### TC-3.1: Single-path, non-deployed component records triggered:false only [spine_of: TC-3.0, spine_step_ref: S1]
**Data Strategy: SYNTHETIC** — packet control CTRL-002.
```
given: CTRL-002 fixture (one path, in-process, no role change)
when:  the trigger evaluates
then:  triggered:false with a rationale line; no authority-paths.json demanded
assert: zero additional fields required of the author; expected_reject_codes == []
```

### TC-3.2: Uncensused sibling and missing predecessor proof are typed rejects [spine_of: TC-3.0, spine_step_ref: S3]
**Data Strategy: SYNTHETIC** — golden ASP-HARDEN-006 (four flatten paths, two authoritative, no coexistence policy).
```
given: ASP-HARDEN-006 fixture
when:  validate_authority_paths runs
then:  PROOF_PATH_UNCENSUSED and PREDECESSOR_NEGATIVE_PROOF_MISSING
assert: all four paths visible in the report; exactly one target authority selected; each predecessor has a disposition or the reject names it
```

### TC-3.3: Trigger decision table [spine_of: TC-3.0, spine_step_ref: S1]
**Data Strategy: SYNTHETIC** — combinatorial.

| # | equivalent_effect_paths | separate_runtime | authority_role_change | triggered |
|---|---|---|---|---|
| 1 | no | no | no | false |
| 2 | yes | no | no | true |
| 3 | no | yes | no | true |
| 4 | no | no | yes | true |
| 5 | yes | yes | yes | true |
| 6 | keyword "migrate" in prose only | no | no | false |
```
assert: row 6 proves keywords are discovery hints, never triggers
```

## US-4: Cutover chains in execution planning (M3)

### TC-4.0: Role-changing path expands into a complete cutover chain that emits a strict-int plan [spine: US-4]
**Data Strategy: REAL-DATA** — real census delta from TC-3.0 fed through dependency_semantics and mini_spec_emission; plan validated by the live fizzy-pipeline-mcp `pipeline_validate_plan`.
spine_steps: S1 census current->target delta, S2 build_cutover_obligations yields source, consumers, artifact, activation, running identity, acceptance, predecessor probe, retirement nodes, S3 plan emitted schema 3 with type(plan_schema_version) is int, S4 Fizzy validate and load classify identically
```
given: one path with current_role authoritative -> target_role retiring and a successor path
when:  Phase 7 planning runs
then:  every chain node is a plan task or carries not_applicable(reason)
assert: pipeline_validate_plan returns [] ; pipeline_load dry classification == validate classification (VALIDATE_LOAD_CLASSIFICATION_DIVERGENCE absent)
```

### TC-4.1: Silent omission of a chain node is rejected; not_applicable(reason) is accepted [spine_of: TC-4.0, spine_step_ref: S2]
**Data Strategy: SYNTHETIC** — controlled omission.
```
given: a chain missing its retirement node with no annotation, and the same chain with retirement: not_applicable("in-process library, no activation")
when:  build_cutover_obligations validates
then:  first is rejected naming the node; second is accepted only after an independent reviewer marks the inapplicability accepted
assert: blank reason is rejected; a non-blank reason without reviewer acceptance stays unresolved and blocks the chain
```

### TC-4.2: Non-integer plan discriminator is rejected at self-check and at Fizzy [spine_of: TC-4.0, spine_step_ref: S4]
**Data Strategy: REAL-DATA** — live fizzy-pipeline-mcp validator, not a stub; golden ASP-HARDEN-009/010 values.
```
given: an otherwise valid plan with plan_schema_version "2", then true, then 3.0
when:  self_check_plan runs, then pipeline_validate_plan runs
then:  both report PLAN_SCHEMA_VERSION_TYPE_INVALID; neither downgrades to legacy validation
assert: a missing key is grandfathered with WRONG_SCHEMA_VERSION locally and legacy handling in Fizzy, and the two agree on that classification
```

### TC-4.3: Consumer scheduled before its authority fails the schedule postcondition [spine_of: TC-4.0, spine_step_ref: S3]
**Data Strategy: SYNTHETIC** — golden ASP-HARDEN-003.
```
given: consumer task depending on predecessor risk model, no dependency edge to the canonical authority task
when:  schedule postcondition runs on the emitted plan
then:  SCHEDULE_POSTCONDITION_FAILED naming the consumer and the missing edge
assert: consumer remains blocked in the materialized schedule
```

### TC-4.4: Every censused caller gets a consumer task [spine_of: TC-4.0, spine_step_ref: S2]
**Data Strategy: SYNTHETIC** — census with three callers of the migrating path.
```
given: census listing product, operator, and harness callers
when:  cutover obligations are built
then:  one consumer task per caller; harness caller task carries caller_equivalence_ref or is rejected
assert: a caller in the census with no task fails the D1 gate
```

## US-5: Observed target at promotion (M2)

### TC-5.0: Runner-produced observation matching the binding closes promotion [spine: US-5]
**Data Strategy: REAL-DATA** — the real skill-runner executing a real test command in this repo; observation captured by the runner.
spine_steps: S1 validated bound record, S2 runner executes and captures target_observation (caller, path, authority, contract hashes, runtime receipt, PID + start time), S3 compare_target_observation matches, S4 evaluate_phase8_close can_close true
```
given: a bound record whose binding names the real command's caller/path/authority and contract hashes
when:  capture_run_evidence runs with the real runner
then:  evidence.target_observation is populated by the runner; owner_written fields ignored
assert: no PROOF_* issues; can_close is True; observation carries runtime_receipt_id and pid_start_time
```

### TC-5.1: Harness caller cannot discharge a product-route obligation [spine_of: TC-5.0, spine_step_ref: S3]
**Data Strategy: SYNTHETIC** — golden ASP-HARDEN-005.
```
given: binding PATH-FLATTEN-V3 product caller; observation PATH-EXIT-V2 harness caller, env live, no equivalence ref
when:  compare_target_observation runs
then:  PROOF_CALLER_MISMATCH, PROOF_PATH_MISMATCH, PROOF_AUTHORITY_ROLE_MISMATCH
assert: env live does not widen evidence; can_close False
```

### TC-5.2: Old running process cannot discharge a fresh package [spine_of: TC-5.0, spine_step_ref: S2]
**Data Strategy: SYNTHETIC** — golden ASP-HARDEN-007.
```
given: intended and packaged source 56112c37, running source 05742a38
when:  runtime identity is compared
then:  RUNTIME_IDENTITY_INCOMPLETE and PACKAGE_COMPONENT_UNPROVEN
assert: the reject names the broken link (activation -> running)
```

### TC-5.3: Owner-authored observation is rejected [spine_of: TC-5.0, spine_step_ref: S2]
**Data Strategy: SYNTHETIC** — an observation block hand-written into the record.
```
given: a record whose run_evidence.target_observation was written by the owner (no runner receipt id)
when:  promotion validates
then:  reject naming the missing runtime_receipt_id; observation discarded
assert: the runner's own observation on re-run replaces it
```

### TC-5.4: Stale process receipt is rejected by PID start time and freshness [spine_of: TC-5.0, spine_step_ref: S2] [BVA]
**Data Strategy: REAL-DATA** — a real long-lived process on the proof host and a real re-exec.
```
given: a receipt captured against PID P with start time T; the process is restarted so PID P now has start time T' > T
when:  the old receipt is presented at promotion
then:  RUNTIME_IDENTITY_INCOMPLETE (stale receipt)
assert: at boundary: receipt captured within FRESHNESS_WINDOW (value per OQ-7) is accepted; one second past it is rejected; a process restart inside the window also invalidates (event-based, not only time-based)
```

### TC-5.5: Reachable terminal state missing from the oracle matrix is rejected [spine_of: TC-5.0, spine_step_ref: S3]
**Data Strategy: SYNTHETIC** — golden ASP-HARDEN-013.
```
given: system state machine with terminal states {completed, partial, rejected, timeout}; terminal_oracle.accepted_states lists {completed}
when:  the terminal enum is compared
then:  TERMINAL_ENUM_UNCOVERED naming the three uncovered states
assert: a timeout cannot hide a real terminal enum
```

## US-6: Typed fixture provenance (M2)

### TC-6.0: Constructed producer without the word "mock" is a typed ceiling [spine: US-6]
**Data Strategy: SYNTHETIC** — golden ASP-HARDEN-012.
spine_steps: S1 fixture_provenance declared per replaced boundary, S2 classifier evaluates each boundary against the obligation's real-producer requirement, S3 ceiling applied
```
given: helper makeEnvelope replacing the gateway producer; contains_word_mock false; obligation binds a real producer
when:  promotion validates
then:  FIXTURE_PROVENANCE_CEILING naming the boundary
assert: lexical absence of "mock" raises nothing
```

### TC-6.1: Prose saying "no mocks used" no longer halts [spine_of: TC-6.0, spine_step_ref: S2]
**Data Strategy: REAL-DATA** — the exact Defect C reproduction record.
```
given: a REAL-DATA critical record titled "Verified real test - no mocks used anywhere", fixture_provenance []
when:  promotion validates
then:  no halt; at most an advisory note
assert: boundary_mock_detected is advisory severity, never halt
```

### TC-6.2: BVA fixture on a pure formula pays no provenance ceiling [spine_of: TC-6.0, spine_step_ref: S2]
**Data Strategy: SYNTHETIC** — packet control CTRL-001.
```
given: CTRL-001 fixture (exact synthetic values, no boundary replaced)
when:  provenance classifier runs
then:  no ceiling; expected_reject_codes == []
assert: requires_target_binding returns false for the record
```

## US-7: Custody ledger (M4)

### TC-7.0: Pipeline-owned worktree is created, budgeted, dispositioned, and closed [spine: US-7]
**Data Strategy: REAL-DATA** — real git worktrees in a scratch clone of this repo; ledger rows written by the pipeline.
spine_steps: S1 create row on worktree creation, S2 budget accounting counts pipeline-owned active rows, S3 disposition recorded (integrated | preserved | abandoned | retired) with evidence, S4 validate_custody_close returns no unresolved rows at Session close
```
given: budget 4; a session creates two worktrees
when:  both are integrated and dispositioned
then:  validate_custody_close returns []
assert: each row carries custody_id, kind, path, created_by, disposition, evidence_ref
```

### TC-7.1: Aggregate count delta cannot close rows [spine_of: TC-7.0, spine_step_ref: S3]
**Data Strategy: SYNTHETIC** — golden ASP-HARDEN-014 (307 -> 72, no dispositions).
```
given: before_count 307, after_count 72, itemized_dispositions []
when:  validate_custody_close runs
then:  CUSTODY_DISPOSITION_INCOMPLETE for every in-scope row
assert: unknown actor and preservation status stay visible in the report
```

### TC-7.2: Budget breach blocks creation and never deletes [spine_of: TC-7.0, spine_step_ref: S2] [BVA]
**Data Strategy: REAL-DATA** — real worktrees so "existing items untouched" is checked on disk. Boundary is the PROJECTED total after creation (R1, codex CRIT-5).
```
given: budget 4; active pipeline-owned items 3 (projected 4 = at boundary) then 4 (projected 5 = just outside); requested_action delete_oldest on the second; no operator exception
when:  a new creation is requested
then:  at projected 4 the creation is accepted; at projected 5 CUSTODY_BUDGET_BREACH and CUSTODY_DESTRUCTIVE_PREVIEW_INCOMPLETE; two concurrent requests at projected 4 admit exactly one
assert: all existing worktrees still exist on disk after validation; validator performed no filesystem writes
```

### TC-7.3: Independent reviewer checkout is outside the budget [spine_of: TC-7.0, spine_step_ref: S2]
**Data Strategy: SYNTHETIC** — packet control CTRL-003.
```
given: a checkout with pipeline_owned false
when:  budget accounting runs
then:  it is excluded; expected_reject_codes == []
assert: adopting it (pipeline depends on it) flips it into scope with a row required
```

### TC-7.4: Transient tool-turn subagent workspace is exempt [spine_of: TC-7.0, spine_step_ref: S1]
**Data Strategy: REAL-DATA** — a real worktree created and removed within one Agent tool turn (OQ-2).
```
given: a subagent branch + worktree created and cleaned within a single tool turn
when:  the ledger is inspected after the turn
then:  no row demanded; a worktree that survives the turn boundary demands a row
assert: CUSTODY_ENTRY_MISSING fires only for the surviving one
```

### TC-7.5: Operator exception exceeds budget but authorizes nothing destructive [spine_of: TC-7.0, spine_step_ref: S2]
**Data Strategy: SYNTHETIC** — exception line with and without a removal request.
```
given: budget 4, active 5, operator_exception present
when:  creation is requested, then removal is requested without an itemized preview
then:  creation accepted; removal rejected CUSTODY_DESTRUCTIVE_PREVIEW_INCOMPLETE
assert: preview must carry dirty/untracked/ignored inventory, runtime dependency check, recovery ref, and exact operator authorization before apply
```

### TC-7.6: Missing row for a durable pipeline-owned branch [spine_of: TC-7.0, spine_step_ref: S1]
**Data Strategy: REAL-DATA** — real branch created by the pipeline path without a ledger write (fault induced by disabling the ledger writer).
```
given: a pipeline-created branch surviving the session with no row
when:  validate_custody_close runs
then:  CUSTODY_ENTRY_MISSING naming the branch
assert: this is the golden case the 2026-09-14 catalog lacked
```

### TC-7.7: Plan-produced budget and expected rows reach the ledger intact [spine_of: TC-7.0, spine_step_ref: S1]
**Data Strategy: REAL-DATA** — real Phase 7 planning output from TC-4.0 fed into the ledger (C-18 contract test for E-10).
```
given: a plan whose obligations declare custody budget 4 and two expected rows (worktree, branch)
when:  the ledger initializes from the plan, then the same plan with the budget field dropped, then with an expected row corrupted
then:  first: ledger carries budget 4 + two expected rows; second and third: reject naming the missing/corrupted field (never a silent default budget)
assert: a session whose ledger budget was defaulted rather than plan-produced cannot close
```

## US-8: Critic and adversary prompts (M5)

### TC-8.0: Guardrail prompt surfaces a wrong-route REAL-DATA test [spine: US-8]
**Data Strategy: REAL-DATA** — a real debate round through the pipeline dispatch on a spec seeded with a v2-route test claiming a v3 obligation; system-validation tier evidence.
spine_steps: S1 spec carries the seeded wrong-route test, S2 a critic seat runs with the updated guardrail prompt, S3 the return names the route mismatch as a finding
```
given: spec-draft with TC declaring REAL-DATA against /exit while the obligation is /flatten
when:  one debate round runs
then:  at least one finding names the retired/non-product path
assert: judged by a cross-vendor seat against a golden manifest; score >= threshold
```

### TC-8.1: Gauntlet broker refuses cross-path answers [spine_of: TC-8.0, spine_step_ref: S2]
**Data Strategy: SYNTHETIC** — GT-REQUEST fixture asking about path B with an observation of path A available.
```
given: broker holds the session census (authority-paths.json) and a real observation of PATH-A
when:  a seat files GT-REQUEST about PATH-B; then the census is removed/corrupted and the request repeats
then:  first: BLOCKED "observation is of a different path" (PATH-B located via the census); second: BLOCKED "census missing/unreadable", never an answer
assert: fixture/claim ceiling stays attached to any fixture-derived observation; a seat never receives census content it can mutate (C-20)
```

### TC-8.2: Identity-contradiction question is asked and answered [spine_of: TC-8.0, spine_step_ref: S3]
**Data Strategy: SYNTHETIC** — golden ASP-HARDEN-004 (asset id side vs wire outcome).
```
given: spec with two identity fields that can disagree and no contradiction case
when:  the guardrail prompt runs
then:  finding CONTRADICTORY_IDENTITY_UNTESTED naming both fields
assert: adding the precedence test clears the finding on the next round
```

## US-9: Finalize binding and ORACLE alignment (M5)

### TC-9.0: TCOV repointed to ORACLE requires an executable witness [spine: US-9]
**Data Strategy: REAL-DATA** — real finalize run on this session's own spec and tests-pseudo.
spine_steps: S1 ORACLE consumes obligations, bound suite, controls, and the synthesized diff, S2 each scored oracle fails the known-bad control and passes the known-good control, S3 triggered tests without binding are rejected, S4 finalize proceeds only with residue recorded for unvalidated oracles
```
given: spec-final candidate with obligations and a bound suite
when:  ORACLE runs
then:  every oracle has G pass / M fail across three clean fixed-seed runs
assert: an oracle without honest G/M is recorded UNVALIDATED_ORACLE residue and never admitted to reconciliation burn-down
```

### TC-9.1: Triggered test without binding fails finalize [spine_of: TC-9.0, spine_step_ref: S3]
**Data Strategy: SYNTHETIC** — one triggered test with binding removed.
```
given: tests-pseudo with a spine test lacking Proof target
when:  ORACLE/TCOV runs
then:  TMR_TARGET_BINDING_REQUIRED for that test
assert: finalize cannot advance; the reject names test_id and trigger
```

### TC-9.2: Concern closure requires an enforcing test and proof target [spine_of: TC-9.0, spine_step_ref: S4]
**Data Strategy: SYNTHETIC** — a gauntlet concern dispositioned "fixed by task W2-3" with no test.
```
given: concern CB-7 closed by implementation task only
when:  finalize validates concern dispositions
then:  closure rejected; requires enforcing test id + proof target
assert: same concern with test + target closes
```

### TC-9.3: Permissive assertion wider than the canonical schema [spine_of: TC-9.0, spine_step_ref: S2]
**Data Strategy: SYNTHETIC** — golden ASP-HARDEN-002; the assertion DSL is a debate decision.
```
given: canonical type string; test accepts number or string
when:  the assertion-vs-schema check runs
then:  CONTRACT_ASSERTION_WIDER_THAN_SCHEMA
assert: the check operates on a declared assertion shape, not on parsing arbitrary test code
```

## US-10: Golden replay and mutation proof (M6)

### TC-10.0: All eighteen golden cases replay with their expected codes [spine: US-10]
**Data Strategy: SYNTHETIC** — the packet catalog is incident-derived synthetic fixtures by construction.
spine_steps: S1 load catalog, S2 route each case to its validator, S3 compare codes, S4 report
```
given: 05-golden-regression-catalog.json (18 cases)
when:  the replay harness runs
then:  15 incident cases produce exactly their expected_reject_codes; CTRL-001/002/003 produce []
assert: order-insensitive equality on code sets; no case is skipped or marked UNVERIFIABLE
```

### TC-10.1: One-field mutation produces its specific code [spine_of: TC-10.0, spine_step_ref: S3]
**Data Strategy: SYNTHETIC** — mutation matrix from packet 04 §5.4.
```
given: a passing proof fixture
when:  caller, route, authority role, producer hash, consumer hash, artifact sha, activation target, PID/start time, terminal enum, predecessor probe, custody id/disposition are each mutated alone
then:  each mutation yields exactly its named reject code
assert: no mutation yields [] (a decorative field)
```

### TC-10.2: Previously unexercised codes have cases [spine_of: TC-10.0, spine_step_ref: S1]
**Data Strategy: SYNTHETIC** — new cases for PROOF_OUTCOME_MISMATCH, TMR_TARGET_BINDING_REQUIRED, VALIDATE_LOAD_CLASSIFICATION_DIVERGENCE, CUSTODY_ENTRY_MISSING.
```
given: the amended catalog
when:  the code-coverage check runs
then:  every code in contract §5 (22) appears in at least one golden or mutation case
assert: set(§5) - set(used) == {}
```

## US-11: Rollout and grandfathering (M6)

### TC-11.0: Enforcement fence decision table [spine: US-11]
**Data Strategy: REAL-DATA** — two real session cards on the board, pipeline_version 5 and 6, read off pipeline_metadata.
spine_steps: S1 read pipeline_version from the session card, S2 select mode, S3 apply

| # | pipeline_version | triggered test unbound | result |
|---|---|---|---|
| 1 | 5 | yes | warning, promotion proceeds |
| 2 | 6 | yes | TMR_TARGET_BINDING_REQUIRED reject |
| 3 | 6 | no | accept |
| 4 | absent (grandfathered card) | yes | legacy behavior, warning |
| 5 | malformed / unreadable metadata | yes | reject (never legacy) |
```
assert: mode is never inferred from file age or spec version; only the card's pipeline_version; absent and malformed are different rows
```

### TC-11.1: Legacy TMRs remain readable and visibly unbound [spine_of: TC-11.0, spine_step_ref: S3]
**Data Strategy: REAL-DATA** — the post-fable-hardening session's real registry.
```
given: a registry authored before target_binding existed
when:  loaded under the extended schema
then:  every record validates; target_binding_status legacy-unbound in the dump
assert: legacy evidence cannot discharge a newly bound obligation; only new evidence from the intended target can. An operator waiver records accepted risk with authority and expiry and leaves the obligation visibly undischarged; a process-failure note attributes and discharges nothing (INV-10)
```

### TC-11.2: Unknown fields survive cross-version writers [spine_of: TC-11.0, spine_step_ref: S3]
**Data Strategy: SYNTHETIC** — a record with a future field written by a newer writer.
```
given: a registry entry carrying a field this version does not know, marked by contract version
when:  an older writer rewrites the registry
then:  the unknown field is preserved byte-for-byte
assert: strict validation still rejects unknown fields that carry no contract-version marker
```

### TC-11.3: Skill edits ship as W-tasks post-finalize [spine_of: TC-11.0, spine_step_ref: S2]
**Data Strategy: REAL-DATA** — git log of this branch.
```
given: the session branch from card creation through finalize
when:  phase-doc and script diffs are listed
then:  no phase-doc edit lands before the finalize transition except the recorded Defect A/B hotfixes
assert: every post-finalize skill edit maps to a Task Card id
```

### TC-11.4: Existing suites stay green with the skip set unchanged [spine_of: TC-11.0, spine_step_ref: S3]
**Data Strategy: REAL-DATA** — full adversarial-spec and Fizzy suites.
```
given: baseline skip set recorded at session open (adversarial-spec: 1 skipped; 2 pre-existing gemini-cli provider failures noted)
when:  the full suites run after each wave
then:  no new failures; skip set unchanged
assert: the two pre-existing provider failures are dispositioned, not hidden
```

## US-12: Dogfood on the v6 bounded pipeline (M7)

### TC-12.0: This session walks the canonical v6 order with D0 adequacy satisfied [spine: US-12]
**Data Strategy: REAL-DATA** — this session's own journey log and board card.
spine_steps: S1 requirements -> roadmap, S2 roadmap -> decomposition with pipeline_mark_decomposition_complete verify-on-disk (Phase-4 obligations incl. the census ride the D0 artifact), S3 debate fan-out per leaf to Synthesized, S4 fan-in gauntlet, S5 finalize -> execution -> implementation using only gates that exist today; new gates are delivered, not exercised, here
```
given: sessions/<id>.journey.log and card 21537
when:  phase8_subflow_migration.py --check-journey runs at each transition
then:  exit 0; decomposition present (v6 legal); no skipped phase
assert: D0 adequacy predicate satisfied on disk before Debate opens
```

### TC-12.1: Every process failure is recorded with would_have_used [spine_of: TC-12.0, spine_step_ref: S3]
**Data Strategy: REAL-DATA** — specs/<slug>/process-failures/.
```
given: any gate circumvention or tool gap during the session
when:  the session closes
then:  one note per failure with a would_have_used front-matter line
assert: pipeline_patch_state_backlog lists each
```

### TC-12.2: patch_state tally on card 21537 is zero [spine_of: TC-12.0, spine_step_ref: S5]
**Data Strategy: REAL-DATA** — pipeline_lane_state.patch_state_health.
```
given: the session card at close
when:  lane state is read
then:  patch_state_health shows 0 for card 21537
assert: any non-zero tally is itself a recorded process failure
```

## US-13: Recovery after a rejected proof (M2)

### TC-13.0: A rejection carries everything needed to recover [spine: US-13]
**Data Strategy: SYNTHETIC** — seeded wrong-target rejection (ASP-HARDEN-005 shape).
spine_steps: S1 rejection emitted, S2 worker reads code + explanation + expected vs observed + missing-or-mismatched + next actor + permitted recovery, S3 worker re-runs against the intended target, S4 obligation closes with unrelated completed work intact
```
given: a promotion rejected PROOF_PATH_MISMATCH
when:  the worker reads only the rejection payload
then:  it names test_id, obligation, expected path, observed path, evidence class, next actor, and the permitted recovery (re-run on intended path)
assert: three seeded rejections are each recovered by a worker seat without additional context (KPI recovery usability); other closed obligations on the card are untouched
```

### TC-13.1: Missing evidence is distinguishable from observed mismatch [spine_of: TC-13.0, spine_step_ref: S2]
**Data Strategy: SYNTHETIC** — one record with no observation, one with a wrong observation.
```
given: record A (observation absent), record B (observation present, path differs)
when:  promotion validates
then:  A reports evidence missing (no PROOF_* mismatch code); B reports PROOF_PATH_MISMATCH
assert: absence is never reported as mismatch nor as pass
```

### TC-13.2: Unavailable independent review is reported, never simulated [spine_of: TC-13.0, spine_step_ref: S2]
**Data Strategy: REAL-DATA** — a real unreachable seat (codex CLI absent from PATH on the proof host).
```
given: the cross-vendor reviewer seat is unreachable
when:  review is requested
then:  status "reviewer unavailable" with the seat named; no claude substitute; card stays in Review
assert: no review verdict is recorded
```

## US-14: Reconciliation after interruption (M4)

### TC-14.0: Interrupted custody operation is reconciled before dependent work [spine: US-14]
**Data Strategy: REAL-DATA** — a real worktree left behind by killing the creating process mid-turn.
spine_steps: S1 interruption leaves a surviving workspace, S2 next session start lists unresolved rows and surviving exempt-class workspaces, S3 operator dispositions each, S4 dependent work unblocks
```
given: a tool-turn workspace whose turn was interrupted (SIGKILL) before cleanup
when:  the next session starts
then:  the workspace is listed as unreconciled (exemption void because its lifecycle did not end in the turn)
assert: dependent work is blocked until a disposition row exists; interruption never implies completion
```

### TC-14.1: Interrupted run does not imply a pass [spine_of: TC-14.0, spine_step_ref: S2]
**Data Strategy: REAL-DATA** — runner killed mid-execution.
```
given: a promotion run interrupted before the receipt is written
when:  the session resumes
then:  the obligation shows no evidence (not fail, not pass); a re-run is required
assert: partial artifacts are retrievable but carry no result
```

## US-15: Integration ownership (M1)

### TC-15.0: Every shared contract names one owner and its consumers' validation scope [spine: US-15]
**Data Strategy: REAL-DATA** — the keystone header, Fizzy validator, and skill emitter as they exist.
spine_steps: S1 ownership table in the spec (keystone → Brainquarters; plan/metadata validation → Fizzy; TMR execution logic → skill/runner), S2 each consumer's validation scope stated, S3 a contract change follows the owner-first order
```
given: the ownership table
when:  the target_binding keystone change lands
then:  order is keystone → machine schema → sha re-pin → mirrors; Fizzy validates plan/metadata contracts only (OQ-4)
assert: no consumer duplicates another's validation; a mismatch is a typed reject at the consumer, never silent
```

### TC-15.1: Validate and load classify within the declared shared contract [spine_of: TC-15.0, spine_step_ref: S2]
**Data Strategy: REAL-DATA** — live fizzy-pipeline-mcp validate and load dry classification.
```
given: the strict-int discriminator corpus (int 2, int 3, "2", true, 3.0, absent, malformed)
when:  pipeline_validate_plan and pipeline_load classify each
then:  identical classifications
assert: any divergence is VALIDATE_LOAD_CLASSIFICATION_DIVERGENCE (golden case added, TC-10.2)
```

## US-16: Downstream adoption (M7)

### TC-16.0: prediction-prime adopts on a v6 session with zero burden on unaffected work [spine: US-16]
**Data Strategy: REAL-DATA** — a real subsequent v6 session in prediction-prime.
spine_steps: S1 adoption guide followed, S2 readiness command ready, S3 one triggered test bound and promoted through the delivered gates, S4 one CTRL-002-class change passes with a single rationale line
```
given: prediction-prime at pipeline_version 6 after this reform ships
when:  the first session runs
then:  the triggered test round-trips through binding → observation → close; the untriggered change records triggered:false only
assert: no new model launches for the untriggered change; every delivered gate is exercised at least once (KPI released-workflow proof)
```

### TC-16.1: v5 to v6 migration path is explicit [spine_of: TC-16.0, spine_step_ref: S1]
**Data Strategy: REAL-DATA** — an in-flight v5 card and a new v6 card on the same board.
```
given: one in-flight v5 session card and one new v6 card
when:  both run promotion with an unbound triggered test
then:  v5 warns and proceeds; v6 rejects
assert: the v5 card is never rejected retroactively; RB-1 is resolved before any v6 card created before enforcement is rejected
```
