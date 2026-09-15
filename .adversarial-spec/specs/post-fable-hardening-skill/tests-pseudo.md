# Test Pseudocode — Post-Fable Hardening, Skill Slice (G1+G2+G5)

> v8.3 — 2026-07-21 (final TCOV hardening: authorization-set encoding,
> authority-owned snapshot roots, result-family boundaries, inheritance lifecycle,
> and ordered promotion coverage; v8.3, FTCOV-1..9). 103 story TCs + 25
> invariant TCs (TC-INV-001..025) = 128 total / 17 spines. (The v8 count
> "99 TCs" excluded the then-24 TC-INV cases; this header now states both.)
> v8 — 2026-07-20 (R6 sync vs spec-draft-v7: TC-8.2 asserts split by enum
> family (PromotionSequenceResult for never-attempted steps vs
> RemoteOperationResult for invoked failures, sol HIGH-2); TC-8.9 wrong-kind
> mutant replaced with deferred-lacking-successor + assert rewritten to the
> §9 disjunct rule (sol HIGH-1). 84 TCs / 17 spines.)
> v7 — 2026-07-20 (R5 sync vs spec-draft-v6: TC-0.8 local-cutoff-rewrite +
> missing-attestation cases (sol HIGH-1); TC-8.2 rewritten as end-to-end
> local/REMOTE split with non-terminal local evaluation (sol HIGH-2); TC-8.9
> one-at-a-time obligation-identity mutants incl. ordinary-waiver rejection
> (sol CRIT-1); TC-0.4 promoted to REAL-DATA (sol MED, DR-8). 84 TCs /
> 17 spines.)
> v6.1 — 2026-07-19 (R4 guardrail fixes: TC-16.4 prepare-boundary rejection
> test added (TCOV-1); TC-15.5 truncation + stale-snapshot tamper forms
> (TCOV-2); TC-16.1 asserts exact §5.2 RemoteOperationResult tokens (CANON-1).
> 84 TCs / 17 spines.)
> v6 — 2026-07-19 (R4 sync vs spec-draft-v5: authority-negative and
> local-I/O isolation coverage, receipt-aware lifecycle coverage, bridge-
> authoritative nonce replay defense, and DR-8 REAL-DATA promotions).
> v5 — 2026-07-19 (R3 sync vs spec-draft-v4: critic-directed REAL-DATA
> promotions, integrity/authority/score/promotion/press assertion extensions,
> and four new behavior TCs; §14 coverage-map patch listed in the R3 report).
> v4 — 2026-07-19 (R3 prep: 16 TCOV obligations; TCOV-5 already re-centered
> in TC-5.0; TCOV-12 updates TC-16.0).
> v3 — 2026-07-19 (R2 sync vs spec-draft-v3: 11 new TCs from R2 synthesis —
> regime stamping, harness anti-vacuous scoring + baseline identity, stable
> verification-card identity, criticality/maturity sole-writer authority,
> deferred atomic inheritance, typed ConOps predicates, node event-log
> hash-chain, fingerprint lineage, press mechanization, waiver replay
> rejection. §"v3 additions" below; coverage map = spec §14).
> v2 — 2026-07-17 (R1 sync vs spec-draft-v2: 8 induced-liveness reclassifications
> per sol mutation directive, 8 new mutation TCs, canonical classification enum).
> v1 — 2026-07-08. Canonical source of truth for tests; roadmap links here.
> One active `spine: true` per user story (TC-X.0 convention). Failure/branch tests
> cite `spine_of` + `spine_step_ref`. Maturity: all `nl→acceptance` candidates; none concrete yet.
> Data-strategy vocabulary applied to this project's "real data" = real session artifacts,
> real transcripts, real registries from past sessions (card-5715, gateway study, liveness-gate wave).
> Every Data Strategy line carrying a `Technique note` is an `(R3-guardrail: CANON-2)`
> canonicalization: the technique is descriptive and not part of the enum value.

---

## US-0: Toolchain bootstrap (M0)

### TC-0.0: Bootstrap on healthy checkout [spine: US-0] (SCOPE-1 resolved: benchmark clauses moved out, 2026-07-19)
**Data Strategy: REAL-DATA** — runs on the actual repo checkout; no manufactured state.
spine_steps: S1 invoke bootstrap command, S2 toolchain probes run, S3 ready verdict emitted
```
given: fresh clone of skill repo at HEAD with deps installed
when:  the documented bootstrap command runs
then:  gate-check CLI, competence harness, reconciliation CLI each probe OK
assert: exit 0; report lists each tool with version/path; wall time < 5 min
```

### TC-0.1: Registry/manifest writers preserve lock and crash safety (R3-guardrail: TCOV-2)
**Data Strategy: REAL-DATA** — **Technique note: real-process fault-injected concurrent read-modify-write.**
spine_of: TC-0.0, spine_step_ref: S2
```
given: each state-modifying Session registry/manifest writer, a valid old and new state,
       and paired competing read-modify-write processes including inverse-order two-artifact
       transactions
when:  the production writer paths run concurrently, and each write is interrupted at every
       durability boundary
then:  every completed transaction has deterministic lock acquisition order, no deadlock,
       no lost update, and no partial visibility; recovery reads only the complete old or new
       state, never a truncated artifact
assert: a writer protocol that cannot finish emits its named fail-closed result; lock logs
        identify the ordered artifacts and crash recovery never silently authorizes a transition
```

### TC-0.2: Missing harness fixture dir named in error
**Data Strategy: SYNTHETIC** — a healthy checkout always has fixtures; absence must be manufactured (rename dir).
spine_of: TC-0.0, spine_step_ref: S2
```
given: checkout with the harness fixtures directory renamed away
when:  bootstrap runs
then:  probe for competence harness fails
assert: nonzero exit; error names the exact missing path; other tools still reported
```

### TC-0.3: Exit-code tier boundary — advisory vs blocking (v6, R4: gemini 2.2; lineage: v2 TCOV R1)
**Data Strategy: REAL-DATA** — Run the real `hardening_bootstrap.py` on a checkout where the usage router file is modified to return an unhealthy socket (asserts exit code `1`) and a blocking folder (e.g., fixtures) is renamed (asserts exit code `2`).
spine_of: TC-0.0, spine_step_ref: S3
```
given: (a) checkout where ONLY the advisory BOOT-ROUTER probe fails;
       (b) checkout where exactly one blocking check fails; and
       (c) checkout where both an advisory and a blocking check fail in the same run
when:  bootstrap runs on each
then:  (a) exits 1 (degraded) with all blocking checks reported OK;
       (b) exits 2 (broken); (c) exits 2 because blocking takes precedence
assert: advisory-only failure never yields 2; blocking failure never yields 1 or 0;
        advisory+blocking cannot be reduced to degraded; each failure line carries check id +
        tool + path + remediation (TRACE R1 contract)
```

### TC-0.5: Required-artifact envelope rejects every invalid integrity form (v6, R4: codex MED-6 + gemini Data Strategy; lineage: v4 TCOV-1 R3-prep, R3 CANON-3/TCOV-5)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Run each real production artifact validator against real schema-valid envelopes from disposable sessions, then induce one byte/schema/integrity mutation at a time before crossing the actual validator boundary.
spine_of: TC-0.0, spine_step_ref: S2
```
given: valid JCS envelopes for gates.json, node/coverage/context registries, reconciliation
       reports, waiver receipts, ConOps evidence indexes, spine manifests, fizzy creation
       attestations, and promotion-prepare receipts; parameterize
       each with malformed JSON, duplicate object keys, invalid UTF-8/JCS-unrepresentable
       values, missing required envelope field, unsupported schema major, stale/mismatched
       content_hash, rehashed unauthorized write, cross-session substitution, and a
       session-manifest path that is absolute, `..`-escaping, or symlinked; additionally
       parameterize waiver receipts and the pinned release digest with operator-signature
       variants, and creation attestations/promotion-prepare receipts with fizzy-signature,
       wrong-key, unsigned, expiry, and wrong-authority variants
when:  the owning validator consumes each artifact at its blocking transition
then:  every mutated envelope is rejected before its payload is used
assert: validators recompute SHA-256 over RFC 8785 JCS omitting content_hash, generated_at,
        and authority.signature; local rehashed conductor writes are detected by the specified
        hash/chain/binding checks. Operator-signature oracles apply only to waiver receipts and
        the pinned release digest; fizzy-signature oracles apply to creation attestations and
        promotion prepare receipts, while the local lifecycle manifest remains only a mirror.
        A correctly operator-signed pinned digest admits hardened enforcement, while unsigned,
        altered-digest, and wrong-key releases fail validation before any hardened gate is
        enforced. Paths are confined to the session root without following symlinks; every
        failure is fail-closed, names artifact type + integrity defect, and is never an empty
        artifact
```

### TC-0.6: Default bootstrap is hermetic while live-contract preflight is not (v6, R4: codex HIGH-3/MED-6 + gemini Data Strategy; lineage: v4 TCOV-2 R3-prep)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Run the real `hardening_bootstrap.py` and `--live-preflight` entry points in disposable sessions; configure BOOT-ROUTER absent-as-expected, deny socket/DNS to the local blocking path, and induce an unavailable dev capability endpoint only for the remote preflight.
spine_of: TC-0.0, spine_step_ref: S2
```
given: a fresh checkout whose local blocking checks pass, BOOT-ROUTER is absent-as-expected,
       and whose fizzy-owned contract boundary is unreachable; the default blocking path runs
       with socket and DNS access denied
when:  default hardening_bootstrap.py runs, then --live-preflight runs explicitly
then:  default bootstrap completes from checkout-local evidence alone; live preflight reports
       the unavailable consumed contract before a session that will use it
assert: default bootstrap neither probes board reachability nor changes its ready/degraded/
        broken verdict because of it; missing/stale local capability evidence returns
        deferred-for-live-preflight; an unavailable live contract cannot be silently admitted
        once --live-preflight is requested, and the remote failure is named
```

### TC-0.7: BOOT-ROUTER uses the advisory three-state decision table (v4, TCOV-3 R3-prep)
**Data Strategy: SYNTHETIC** — isolate router state while every blocking bootstrap check is green.
spine_of: TC-0.0, spine_step_ref: S3
```
given: router state parameterized as:
       | state                    | expected contribution | expected process exit |
       | absent-as-expected       | 0                     | 0                     |
       | installed-but-unhealthy  | 1                     | 1                     |
       | installed-and-healthy    | 0                     | 0                     |
when:  bootstrap evaluates BOOT-ROUTER in each state
then:  it emits the corresponding advisory verdict
assert: no router state yields exit 2; the unhealthy row is degraded, while absence remains
        an expected non-failure rather than an inferred broken dependency
```

### TC-0.8: Regime stamping is authority-attested and immutable (v6, R4: codex CRIT-2 + Claude F3; lineage: v4 TCOV-4 R3-prep, R3 CANON-3/TCOV-5)
**Data Strategy: REAL-DATA** — **Technique note: induced live-contract exercise.** Create disposable sessions through the real `pipeline_create_session` boundary, validate the signed creation attestation with the real bootstrap, and induce mirror/capability mutations on disk.
spine_of: TC-0.0, spine_step_ref: S2
```
given: (a) a pre-cutoff session with an authority-backed created_at and no local stamp resumed
       after rollout; (b) a post-cutoff session created after rollout with its immutable signed
       attestation; (c) a post-cutoff mirror with its required stamp or attestation absent;
       (d) an already-mirrored manifest whose regime is rewritten from hardened to legacy, or
       whose created_at, rollout id, or decided-at field is edited and rehashed; (e) the
       creation-attestation capability is absent or version-incompatible; (f) a LOCALLY
       rewritten cutoff-policy cache claiming a later cutoff_at that would reclassify a
       post-cutoff session as legacy (v7, R5: sol HIGH-1); and (g) a post-cutoff session
       whose creation attestation is missing while the local mirror and local cutoff cache
       both look internally consistent (v7, R5: sol HIGH-1); (h) the
       hardening-rollout-policy-v1 capability absent; (i) the same capability
       version-incompatible; (j) local policy evidence never cached; and (k) local policy
       evidence present but past its freshness window (v7, R5-guardrail: TCOV-1)
when:  lifecycle initialization or resume validation runs
then:  (a) materializes legacy only from the attested created_at and permits a not-applicable
       registry check; (b) mirrors the immutable hardened tuple and initializes the schema-
       valid empty Session TMR registry; (c) and (d) are rejected against the attestation;
       (e) fails closed with authority-capability-missing; (f) is rejected — regime compares
       the attested created_at only against the validated hardening-rollout-policy-v1
       attestation, never a local cutoff value; (g) is broken regardless of local consistency;
       (h) and (i) return exactly authority-capability-missing — never a silent legacy or
       hardened default; (j) and (k) return exactly deferred-for-live-preflight and no
       regime-sensitive transition advances on that result
assert: the authority-attested creation time versus the authority-signed rollout policy is the
        sole regime decision source; the local session-manifest and local policy cache are only
        mirrors; the hardened→legacy rewrite fails even after local rehash; no registry
        presence, local timestamp, local cutoff rewrite, or conductor-authored attestation can
        change the regime, and no self-attested fallback exists
```

### TC-0.9: Atomic registry write survives terminal interruption (v5, R3 sync)
**Data Strategy: REAL-DATA** — **Technique note: fault injection.** Write a real session registry with the production write-then-swap path, then inject `kill -9` before swap and at each durability boundary.
spine_of: TC-0.0, spine_step_ref: S2
```
given: a valid on-disk Session TMR registry at version N and a valid version N+1 replacement
when:  the real writer is interrupted with kill -9 during temporary write, file fsync,
       atomic swap, or directory fsync
then:  recovery reads either the complete N registry or the complete N+1 registry
assert: the target file is never truncated or partially serialized; any prepared/uncertain
        transaction is named and blocks rather than authorizing a transition
```

---

## US-1: Gate inventory complete + classified (M1)

### TC-1.0: Inventory covers phases 01–09, no unclassified gate [spine: US-1]
**Data Strategy: REAL-DATA** — the real phase-doc corpus is the input.
spine_steps: S1 extract MUST/gate statements, S2 classify each (a/b/c), S3 emit inventory artifact
```
given: the current phases/01..09 corpus
when:  the gate-inventory extraction runs
then:  every MUST/[GATE] statement appears in the inventory artifact
assert: each row has classification ∈ {code_enforced, mechanized, judgment}  # canonical enum, spec §5.1
assert: a re-run on unchanged docs is idempotent (same artifact hash)
```

### TC-1.2: Doc gate added without inventory row is detected
**Data Strategy: SYNTHETIC** — inject a new MUST line into a scratch copy of a phase doc.
spine_of: TC-1.0, spine_step_ref: S1
```
given: a phase doc copy with one new "MUST" gate not present in the inventory
when:  the inventory freshness check runs (doclint family)
then:  it reports the unclassified gate with file:line
assert: nonzero exit; CI-consumable output
```

---

## US-2: Mechanizable gates fire in code (M1)

### TC-2.0: Violated mechanized gate blocks with named error [spine: US-2]
**Data Strategy: REAL-DATA** — induced: run the REAL enforcement boundary (actual lint/hook/gate binary) against a violating state constructed per the gate's `violation_modes[]`; the check path itself is live, only the violation is induced (v2 reclass, sol mutation directive).
spine_steps: S1 construct violation, S2 run the gate's check, S3 block with named error
```
given: a session state violating one class-(b) gate (parameterized across all mechanized gates)
when:  the corresponding check runs (lint / hook / fizzy gate)
then:  the action is blocked
assert: error names the gate id from the inventory; exit nonzero / tool rejection
```

### TC-2.2: Passing state proceeds without friction
**Data Strategy: REAL-DATA** — replay a known-good session state from the liveness-gate wave.
spine_of: TC-2.0, spine_step_ref: S2
```
given: a real historical session state that satisfied the gate
when:  the check runs
then:  it passes silently
assert: exit 0; no spurious block (guards against over-eager mechanization)
```

### TC-2.3: Every local blocking check is network-hermetic (v6, R4: codex HIGH-3)
**Data Strategy: REAL-DATA** — **Technique note: inventory-wide induced live exercise.** Enumerate the real local blocking checks from `gates.json`, run each production entry point with socket creation/connect and DNS resolution denied, and supply real local artifacts with fresh, stale, and missing verified capability attestations.
spine_of: TC-2.0, spine_step_ref: S2
```
given: every inventory row whose enforcement boundary is a local blocking check, executed
       under a harness that fails any socket, DNS, HTTP, model, Telegram, or fizzy access;
       local evidence is parameterized as sufficient, missing, and stale
when:  each real local check runs to its verdict
then:  sufficient evidence yields the check's named local pass/block verdict; missing or stale
       remote evidence yields exactly deferred-for-live-preflight
assert: every inventory row executes; no check opens or resolves a network endpoint, hangs,
        calls a remote adapter, or converts missing remote evidence into success; bootstrap-
        scoped TC-0.6 remains independently green
```

---

## US-3: Judgment gates get rubric + fixture (M1)

### TC-3.0: Judgment-gate fixture scores known-bad transcript as fail [spine: US-3]
**Data Strategy: REAL-DATA** — known process-failure transcripts exist (six process-failure reports).
spine_steps: S1 load rubric + fixture pair, S2 judge fixture against rubric, S3 emit verdict
```
given: a class-(c) gate's rubric and a fixture built from a real past process failure
when:  the golden-eval judge runs
then:  the known-bad case scores fail, the paired known-good case scores pass
assert: verdicts match fixture labels for every (c)-gate fixture pair
```

### TC-3.2: Rubric without any fixture is rejected at authoring
**Data Strategy: STATIC** — pure artifact-shape check.
spine_of: TC-3.0, spine_step_ref: S1
```
given: an inventory row classified judgment with no fixture file
when:  inventory lint runs
then:  row is flagged incomplete
assert: nonzero exit naming the gate id
```

---

## US-4: Phase spine decomposed, loads exactly what's needed (M2)

### TC-4.0: Spine↔reference pointer closure [spine: US-4]
**Data Strategy: REAL-DATA** — the restructured doc corpus itself.
spine_steps: S1 parse spine units, S2 resolve all pointers, S3 sweep reference units for orphans
```
given: the decomposed phase-doc corpus
when:  doclint pointer-closure check runs
then:  every spine pointer resolves; every reference unit has EXACTLY ONE owning spine step
assert: zero dangling pointers; zero orphans; zero multi-owner units (≥2 owners fails — CANON R1 fix); exit 0
```

### TC-4.2: Deleted-not-moved content is caught
**Data Strategy: SYNTHETIC** — remove a reference unit from a scratch corpus copy without a decision-log entry.
spine_of: TC-4.0, spine_step_ref: S3
```
given: corpus copy missing one reference unit that a spine still points to, AND no
       decisions-log entry recording the removal
when:  pointer-closure check runs
then:  the dangling pointer is reported with source spine unit + missing target
assert: nonzero exit; the missing decisions-log entry is separately flagged (move ≠ delete rule, TCOV R1)
```

---

## US-5: Worker context stays lean (M2)

### TC-5.0: Resolver-mediated context loads are step-named units [spine: US-5] (v4 re-centered, TCOV-5 R3-prep; supersedes v3 TC-5.0 "all doc reads" premise — driver: sol R2 HIGH §6.2 narrowing)
**Data Strategy: REAL-DATA** — audit a real post-restructure session's resolver-written context-load-manifests.
spine_steps: S1 run a phase step with the new corpus, S2 collect the per-step context-load-manifest written by the shared architecture_refs resolver, S3 compare each resolved unit against the step's named units
```
given: a completed phase execution after M2 lands, with per-step context-load-manifests
       written by the sole mechanized loader (the architecture_refs resolver)
when:  the manifest audit compares each manifest's resolved units against the
       executed step's named units
then:  every resolver-mediated load is a unit named by the executed steps
assert: zero monolith units and zero unrelated-phase units in any manifest;
        unmediated workspace reads are OUTSIDE this evidence boundary (spec §6.2) —
        covered only by supplementary transcript spot-audit (judgment rubric,
        not spine evidence, never representable as proof of the "only" rule)
```
<!-- tombstoned: v3 TC-5.0 spine premise "every doc read [from transcript] is step-named"
     asserted the superseded all-reads claim; re-centered per morph-reconciliation
     (fate: Re-centered). TC-5.2 (S3) and TC-5.3 (S2) re-anchor cleanly. -->

### TC-5.2: Spine unit contains no rationale prose
**Data Strategy: STATIC** — content-class lint on spine units.
spine_of: TC-5.0, spine_step_ref: S3
```
given: any spine unit
when:  content-class lint runs (heuristic: origin-story/rationale markers)
then:  rationale content flagged for relocation to reference
assert: spine units pass; violations name section headers
```

---

### TC-5.3: Context-load-manifest generated and validated (v2, TCOV R1; relocated from US-0 section — CONS-5 R2)
**Data Strategy: SYNTHETIC** — run a step with known named units; corrupt the manifest.
spine_of: TC-5.0, spine_step_ref: S2
```
given: a phase step executed with its named units; then a manifest entry hand-edited
       to claim a unit the step did not name
when:  the manifest audit runs
then:  the intact manifest passes; the edited manifest is flagged with the offending unit
assert: manifest is the enforcement evidence (transcript audit supplementary);
        schema-invalid or missing manifest = audit fail, not skip
```

---

## US-6: Competence harness measures candidate conductors (M3)

### TC-6.0: Harness scores candidate across all fixtures [spine: US-6]
**Data Strategy: REAL-DATA + PROPERTY** — fixtures derived from real session states; assert report properties, not exact scores.
spine_steps: S1 load fixture set, S2 run candidate model per fixture, S3 emit scored report
```
given: the full fixture set and a named candidate model (e.g. sonnet)
when:  the harness runs
then:  a scored report is emitted
assert: every fixture has a verdict; report includes per-phase breakdown; per-phase score ∈ [0,100]
        computed as 100 × passed/total (CANON R1 fix); report names candidate model id,
        harness version, fixture-set hash, run timestamp
assert: fixture coverage includes ≥1 entry, ≥1 gate, ≥1 failure-recovery decision per phase
assert: a known phase partition with exactly 2 passing and 2 failing fixtures scores exactly
        50, not merely a value in the valid range
```

### TC-6.1: Transient fixture transport retries are bounded and fail closed (v6, R4: codex MED-6 + gemini Data Strategy; lineage: R3-guardrail TCOV-1)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Route the real harness transport stack to a local loopback HTTP server that returns controlled 429, 5xx, delayed-timeout, and success responses; capture real retry timing with seeded jitter configuration.
spine_of: TC-6.0, spine_step_ref: S2
```
given: the loopback server is parameterized with 429, 5xx, delayed-timeout, and success on
       attempts 1–4 or four consecutive transient failures; the production transport and
       retry scheduler are configured with seeded jitter
when:  the harness dispatches the fixture
then:  success uses at most three retries with observed exponential 1 s backoff plus jitter;
       four consecutive transient failures produce one named failed-fixture verdict and a
       complete report
assert: no retry budget produces an empty, implicit, or passing fixture; the report records
        transport class, attempts, each observed backoff+jitter delay, and the fail-closed
        result; no mock transport adapter participates
```

### TC-6.3: Regression-threshold and coverage-manifest boundaries (v2, TCOV R1)
**Data Strategy: SYNTHETIC** — constructed reports/manifests at the boundaries.
spine_of: TC-6.0, spine_step_ref: S3
```
given: (a) reports with a phase score 9, 10, and 11 points below baseline;
       (b) a coverage manifest with exactly one phase entry/gate/recovery mapping removed;
       (c) a known four-fixture phase partition with two passes and two failures; and
       (d) candidate responses containing an extra, forbidden, or duplicate action, or a
       duplicate or wrong gate citation
when:  the pre-session gate evaluates each
then:  9 and 10 pass the regression rule, 11 fails; the manifest with one missing
       mapping fails BOOT-HARNESS validation; each invalid response fails its fixture
assert: boundary behavior explicit (≤ threshold passes); zero-vs-one mutation detected;
        (c) scores exactly 50 within its own phase (no cross-phase counting), and strict
        action-set/citation equality rejects every extra, forbidden, duplicate, and wrong value
```

### TC-6.2: Known-wrong next-action fixture scores fail
**Data Strategy: SYNTHETIC** — stub model retained. `technical_constraint`: deterministic induction of a specific invalid answer cannot be guaranteed from live providers (v2, sol amendment H).
spine_of: TC-6.0, spine_step_ref: S2
```
given: a stub candidate that always answers "run debate.py critique directly"
when:  harness runs the pipeline-card-fence fixture
then:  that fixture scores fail
assert: fail verdict with the violated rule named (falsifies judge leniency)
```

### TC-6.6: Critical fixture validity and admission both fail closed (v4, TCOV-6 R3-prep)
**Data Strategy: SYNTHETIC** — mutate otherwise-valid critical fixtures and scored reports at their independent validation boundaries.
spine_of: TC-6.0, spine_step_ref: S3
```
given: critical fixtures parameterized with (a) empty or absent required_next_actions,
       (b) extra, forbidden, or duplicate actions, (c) duplicate or wrong citations,
       (d) a required action outside allowed_next_actions, (e) malformed expected.json,
       and (f) a per-phase 2-pass/2-fail partition; plus a complete schema-valid report where
       every non-critical fixture and phase baseline passes but one critical fixture fails
when:  BOOT-HARNESS validates the fixture set and the pre-session gate evaluates the report
then:  every invalid critical fixture is rejected before dispatch; the report with one failed
       critical fixture is denied admission despite its otherwise-green score
assert: every critical fixture declares ≥1 required action; only a complete, schema-valid
        report with every critical fixture passed may satisfy the pre-session gate; score
        arithmetic is exactly 50 for (f) within its phase, and no action/citation mutation is
        admitted by set collapse or cross-phase aggregation
```

---

## US-7: Verification cards derived from TMR registry (M4)

### TC-7.0: Unsatisfied critical-seam TMRs yield exactly matching card set [spine: US-7] (v6, R4: codex HIGH-4)
**Data Strategy: REAL-DATA** — use the liveness-gate session's real tmr-registry.json as base.
spine_steps: S1 build validated authorization_snapshot from registry + verified receipts, S2 select TMRs via select_for_verification(tmr, authorization_snapshot) ≡ critical_seam != false AND NOT is_obligation_satisfied(tmr, authorization_snapshot) (named §8.1/§9 predicates), S3 emit card set (v8.3, FTCOV-7)
```
given: a real registry with exactly 3 qualifying critical-seam TMRs
when:  verification-card derivation runs
then:  exactly 3 cards emitted
assert: each card carries seam name, tmr_uid, `criticality_source: CriticalitySource` backed by
        `CRITICALITY_SOURCES` (R3-guardrail: CANON-4),
        required evidence class; is_concrete uses exact enum equality (maturity == "concrete");
        derivation is code (no LLM call in path)
```

### TC-7.2: All-concrete registry yields empty set + recorded no-op (R3-guardrail: CANON-1, CONS-1, TCOV-3)
**Data Strategy: REAL-DATA** — induced: run the REAL derivation binary against a registry whose entries are promoted to concrete/live (promotion induced; derivation path live) (v2 reclass).
spine_of: TC-7.0, spine_step_ref: S2
```
given: Session TMR registry (at session-manifest tmr_registry_path) where every
       critical-seam TMR satisfies the named `is_promotion_ready(tmr, authorization_snapshot)`
       predicate with all six §9 conditions (v8.2, CONS-R1): is_concrete; schema-valid
       live_or_induced matching required class; schema-valid passing run_evidence at required
       env/tier; evidence bound to tmr_uid/card/hash; current obligation_revision +
       obligation_policy_version with an active, unsuperseded verification card; and (critical
       seams) non-conductor §11.1 provenance class OR a matching provenance-exception receipt
       in the authorization snapshot — "concrete with live evidence" alone is NOT sufficient
when:  derivation runs
then:  zero cards; an explicit no-op record written (not silent absence)
assert: no-op record names tmr_registry_path + tmr_registry_hash (CANON-3 R2) +
        predicate version + zero selected UIDs
```

### TC-7.3: Selection-predicate mutation coverage (v2, sol amendment H)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Use disposable dev sessions, real binaries, a dev operator principal, and real contract probes; induce each `critical_seam` ∈ {true,false,null} × maturity × evidence combination in the real Session TMR registry.
spine_of: TC-7.0, spine_step_ref: S2
```
given: registry fixtures covering every criticality/maturity/evidence combination
when:  derivation runs on each
then:  exactly the intended tmr_uids are selected per combination
assert: critical_seam=null selects (unresolved blocks promotion); false with valid
        criticality_source never selects; lexical maturity comparison would fail this test
```

### TC-7.6: Maturity authority writes evidence and promotion atomically (v4, TCOV-7 R3-prep)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise with fault injection.** Use disposable dev sessions, real binaries, a dev operator principal, and real contract probes; inject faults around the real sole-authorized write transaction for a qualifying completed card.
spine_of: TC-7.0, spine_step_ref: S3
```
given: a valid completed verification card and TMR; parameterize (a) a direct maturity write
       by any component except record_verification_evidence.py, (b) a transaction fault after
       evidence validation but before commit, and (c) a successful authorized write
when:  each path attempts to record promotion-eligible evidence
then:  (a) is rejected; (b) leaves neither run evidence nor a concrete maturity transition;
       (c) commits the bound evidence and nl|acceptance → concrete transition together
assert: registry audit names record_verification_evidence.py as the sole maturity writer;
        no durable state contains exactly one of the evidence write and maturity transition
```

### TC-7.7: Session TMR registry wins a conflicting dual-registry input (v4, TCOV-8 R3-prep)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Use disposable dev sessions, real binaries, a dev operator principal, and real contract probes; induce a disagreement between the manifest-selected Session TMR registry and `.architecture/tests/registry.json` for the same TMR.
spine_of: TC-7.0, spine_step_ref: S1
```
given: session-manifest.json.tmr_registry_path selects registry A, while fizzy's node-keyed
       `.architecture/tests/registry.json` presents conflicting criticality/evidence for the
       same TMR uid
when:  verification-card derivation and promotion evaluation run
then:  both consume registry A only; the conflicting fizzy rollup has no effect on selected
       cards or the promotion verdict
assert: each derivation/report records registry A's path + hash; treating the fizzy rollup as
        either a fallback or a second promotion input is rejected
```

### TC-7.8: Obligation revision supersedes deterministically under write-back races (v4, TCOV-9 R3-prep)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise with fault injection.** Use disposable dev sessions, real binaries, a dev operator principal, and real contract probes; emit revision N, supersede it with N+1, and race stale and current evidence write-backs.
spine_of: TC-7.0, spine_step_ref: S3
```
given: an emitted card keyed by (session_id, tmr_uid, obligation_revision=N, obligation_policy_version),
       then a changed obligation revision N+1; concurrently submit evidence through the stale
       N card and the current N+1 card against the same registry version, including evidence
       valid for N that is submitted after N+1 is emitted
when:  emission supersedes obsolete cards and evidence write-back uses optimistic concurrency
then:  N is explicitly superseded, exactly one N+1 card exists, and only the winning current
       write updates the registry; the stale/conflicted write is rejected and leaves no bind
assert: registry_hash remains provenance rather than card identity; no duplicate card or stale
        evidence can become promotion-eligible after the race; N evidence cannot satisfy the
        current obligation_revision/obligation_policy_version or become promotion-ready for N+1
```

---

## US-8: Promotion gate blocks declared-only evidence (M5)

### TC-8.0: Declared-only critical-seam TMR blocks completion [spine: US-8]
**Data Strategy: REAL-DATA** — induced: drive the REAL `pipeline_advance` path on a dev board with a registry holding one declared-only critical TMR (state induced; gate boundary live) (v2 reclass; enforcement point moved to completion transition per sol CRIT-3).
spine_steps: S1 attempt completion advance, S2 gate derives verdict from run_evidence, S3 advance rejected naming TMR
```
given: session at the final completion transition with one critical-seam TMR whose run_evidence is null (evidence "declared" only in owner prose — canonical states are null or a typed receipt)
when:  pipeline advance to complete is attempted
then:  the gate blocks
assert: rejection names the tmr_uid and required evidence class; owner-written prose does NOT satisfy it
```

### TC-8.2: Run-evidence landing unblocks the same session through the full local/REMOTE split (v7, R5: sol HIGH-2)
**Data Strategy: REAL-DATA** — induced: same live dev-board session; evidence recorded via the REAL `record_verification_evidence.py` write path; the real promotion-prepare-v1 and promotion-commit-v1 dev boundaries exercised end-to-end (v2 reclass; v7 split assertion).
spine_of: TC-8.0, spine_step_ref: S2
```
given: the TC-8.0 session after run evidence lands via record_verification_evidence.py;
       parameterize (a) the full happy path, (b) prepare omitted, (c) commit omitted, and
       (d) commit failing after a successful prepare
when:  the completion advance is retried through local evaluation → REMOTE prepare → REMOTE commit
then:  (a) local evaluation passes NON-terminally, constructs the bound JCS intent, prepare
       issues the receipt, commit consumes it, and only promotion-committed exposes terminal
       completion; (b), (c), and (d) each leave the session non-terminal — local evaluation
       alone never exposes any terminal state
assert: gate verdict logged and derived from the registry, not attestation; no durable state
        shows completion before promotion-committed; (a) journals exactly
        promotion-evaluation-passed BEFORE REMOTE prepare is invoked (never a
        RemoteOperationResult token for the local step — v8.1, R6-guardrail TCOV-A);
        (b) journals exactly promotion-prepare-not-attempted and (c) exactly promotion-commit-not-attempted
        (§5.2 PromotionSequenceResult — local, never a remote success); (d) journals the
        exact applicable RemoteOperationResult token; invoked-operation failures and
        never-attempted gaps are distinguishable by enum family (v8, R6: sol HIGH-2)
```

### TC-8.3: Gateway-study replay is caught
**Data Strategy: REAL-DATA** — the 2026-06-18 gateway study's actual end-state artifacts.
spine_of: TC-8.0, spine_step_ref: S3
```
given: the gateway session's registry state reconstructed at its (premature) completion point
when:  replayed against the promotion gate
then:  completion is blocked
assert: blocked TMR set intersects the gateway 25-bug ledger's seam list
```

### TC-8.4: Green-looking but wrong-binding evidence cannot pass (v2, sol amendment H; R3-guardrail: CANON-1, TCOV-3)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Use disposable dev sessions, real binaries, a dev operator principal, and real contract probes; induce one invalid binding element at a time on otherwise-valid evidence.
spine_of: TC-8.0, spine_step_ref: S2
```
given: evidence with result:pass but ONE of {wrong result-tier, wrong env, wrong evidence
       class, wrong tmr_uid binding, wrong verification-card binding, wrong/absent artifact
       hash, non-concrete TMR maturity, schema-invalid live_or_induced, schema-invalid
       run_evidence, result:fail variant, binding to a nonexistent tmr_uid, stale
       obligation_revision, stale obligation_policy_version, inactive/superseded verification card,
       critical-seam evidence with conductor-generated §11.1 provenance class and no
       provenance-exception receipt in the authorization snapshot}
       (parameterized — named six-condition predicate, TCOV R1; arity + count + provenance
       mutant v8.2, CONS-R2)
when:  the named `is_promotion_ready(tmr, authorization_snapshot)` predicate evaluates
then:  every mutant is rejected
assert: rejection names the failing binding element; evidence bound to a nonexistent tmr_uid
        blocks completion; each stale-revision, stale-policy-version, and superseded-card
        mutant blocks completion; zero mutants pass
```

### TC-8.5: Malformed registry or invalid deferred waiver blocks completion (v2)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Use disposable dev sessions, real binaries, a dev operator principal, and real contract probes; truncate/mis-schema the real registry or induce an invalid waiver.
spine_of: TC-8.0, spine_step_ref: S1
```
given: (a) missing/malformed/unsupported-schema registry; (b) deferred TMR whose waiver
       receipt fails validation (§5.4 rejection set); (c) parameterized over the other
       required blocking artifacts (node registry at dispatch, receipt store at gate
       re-check, reconciliation report at convergence) — fail-closed is global (§1, TCOV R1)
when:  completion advance is attempted
then:  both cases block (fail closed — absence never means "empty")
assert: block names the artifact defect or the receipt rejection reason
```

### TC-8.7: Finalize validates and plans; completion requires a satisfied obligation (v6, R4: codex CRIT-1/HIGH-4; lineage: v4 TCOV-10 R3-prep; v8.3, FTCOV-7)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Use disposable dev sessions, real binaries, a dev operator principal, and real contract probes; exercise one valid registry with declared-only critical evidence and one invalid registry at both transitions.
spine_of: TC-8.0, spine_step_ref: S1
```
given: (a) a schema-valid Session TMR registry with a critical seam whose validated
       authorization_snapshot does not satisfy is_obligation_satisfied(tmr, authorization_snapshot);
       (b) a malformed required registry; and
       (c) a fizzy-signed promotion-prepare-v1 receipt issued for a valid JCS intent snapshot,
       followed by a TMR/evidence/card/receipt mutation before the real completion commit
when:  each session attempts finalize, then the final completion transition
then:  (a) finalizes and creates/validates its verification plan without run evidence, but
       completion blocks on the named TMR; (b) fails finalize on registry validity; (c) rejects
       the stale intent and requires fresh evaluation
assert: finalize never demands evidence that post-Phase-8 verification must produce, while
        completion still fails closed unless every critical seam satisfies the named receipt-
        aware predicate; no mutation between promotion prepare and commit can authorize terminal
        state
```

### TC-8.16: Predicate inputs reject raw receipt collections before semantic evaluation (v8.3, FTCOV-7)
**Data Strategy: REAL-DATA** — invoke the production predicate boundary with a caller-curated raw receipt collection and with the equivalent AuthorizationSetBuilder-produced snapshot.
spine_of: TC-8.0, spine_step_ref: S1
```
given: a raw or caller-curated receipt collection that would change a TMR's apparent
       eligibility, and a validated authorization_snapshot produced by AuthorizationSetBuilder
       from the same verified authority state
when:  select_for_verification, is_promotion_ready, and is_obligation_satisfied are invoked
then:  each raw collection is rejected as a type error BEFORE semantic evaluation or predicate
       journaling; the validated authorization_snapshot follows the normal predicate path
assert: predicates accept only ValidatedAuthorizationSet; no coercion, filtering, or
        caller-selected receipt subset can reach semantic evaluation
```

### TC-8.8: Deferred inheritance recovers atomically as one transaction (v4, TCOV-11 R3-prep; title CONS-7 R3; v8.3, FTCOV-6)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise with fault injection.** Use disposable dev sessions, real binaries, a dev operator principal, and real contract probes; inject failure at each coordinator-journal boundary while issuing a deferred waiver to an existing hardened successor.
spine_of: TC-8.0, spine_step_ref: S3
```
given: a parent critical TMR, an existing hardened successor, a valid tmr-deferred receipt,
       and an authorization_snapshot whose provisional transfer plan includes that obligation;
       inject failure before/after waiver issuance, during intent construction, at authority CAS
       commit, and during post-commit parent/successor mirror materialization
when:  parent PRE-commit evaluation, authority commit, and recovery run after each injection
then:  issuance creates no transfer authority and no successor obligation record; PRE-commit
       accepts only the valid receipt + named existing successor + provisional-plan inclusion,
       and its intent copies that plan byte-identically into successor_transfer_set; authority
       CAS atomically records parent-complete + successor inherited obligation; post-commit
       mirror failure is local-mirror-stale until rematerialization succeeds
assert: a committed successor record is impossible before the parent commit; no prepared or
        local record authorizes transfer; repeated recovery materializes only the one
        authority-committed pair, bound to parent, waiver, TMR, and commit certificate
```

### TC-8.9: Valid skip and deferred inheritance satisfy the parent lifecycle (v6, R4: codex HIGH-4; v8.3, FTCOV-6; v8.3, FTCOV-7)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Use disposable parent/successor sessions, real verification-card derivation and completion binaries, real dev authority receipts, and the production inherited-obligation transaction; induce valid skip, committed deferral, and pointer-only/prepared deferral states.
spine_of: TC-8.0, spine_step_ref: S1
```
given: the same otherwise-unready critical TMR is parameterized with (a) no receipt, (b) an
       exact valid tmr-skip receipt in authorization_snapshot, (c) a valid tmr-deferred
       receipt, named existing successor, and matching provisional transfer-plan inclusion in
       authorization_snapshot before parent commit, followed by the matching authority-committed
       inherited-obligation record after parent commit, (d) a missing successor or missing plan
       pre-commit, or an absent/prepared/mismatched record post-commit, and (e) one-at-a-time
       obligation/kind mutants: different tmr_uid, prior revision or policy version, stale
       tmr_record_hash, unknown authorization_kind, or ordinary gate/ConOps waiver
when:  verification-card selection and the parent lifecycle evaluate
       is_obligation_satisfied(tmr, authorization_snapshot) before and after authority commit
then:  (a), (d), and every (e) mutant select the TMR and block; (b) selects no parent card
       and permits the receipt-bound skip; (c) permits PRE-commit intent/commit only with the
       provisional plan, then permits POST-commit parent reads only with the committed record
assert: deferred satisfaction is parent-scoped: the successor record proves obligation inclusion,
        never satisfaction; the parent's consumed receipt is excluded from the successor snapshot,
        and the successor remains blocked until promotion-ready or a new valid receipt
```

---

## US-9: ConOps walkthrough before close (M6)

### TC-9.0: Completed walkthrough writes evidence, session closes [spine: US-9]
**Data Strategy: REAL-DATA** — walkthrough executed against this project's own live pipeline (dogfood).
spine_steps: S1 load walkthrough script, S2 operator executes steps + observations captured, S3 evidence artifact written, S4 close proceeds
```
given: a session at close with a defined walkthrough script for its happy-path spine
when:  the operator completes the walkthrough
then:  evidence artifact (steps, observations, timestamps, operator id) written
assert: session close proceeds; artifact survives close (durable)
```

### TC-9.1: Promotion sequence cannot outrun ConOps evidence (v8.3, FTCOV-8)
**Data Strategy: REAL-DATA** — run the production close coordinator against a session with absent, exact-waived, and complete ConOps evidence.
spine_of: TC-9.0, spine_step_ref: S4
```
given: an otherwise promotion-ready session with (a) missing ConOps evidence, (b) an exact
       receipt-bound ConOps waiver, and (c) completed valid ConOps walkthrough evidence
when:  the close coordinator advances the session
then:  (a) emits NO promotion-evaluation-passed journal event and dispatches neither snapshot
       registration nor prepare; (b) and (c) journal exactly system-verification → ConOps
       walkthrough (or exact receipt-bound waiver) → local promotion evaluation → snapshot
       registration → prepare → commit
assert: the evidence/waiver binding is complete before promotion evaluation; the ordered journal
        sequence is required, with no skipped or reordered dispatch
```

### TC-9.2: Missing walkthrough evidence blocks close
**Data Strategy: REAL-DATA** — induced: drive the REAL close verifier on a dev session with the evidence artifact withheld (state induced; verifier live) (v2 reclass).
spine_of: TC-9.0, spine_step_ref: S4
```
given: session at close, no walkthrough evidence, no operator waiver
when:  close is attempted
then:  blocked with actionable message (script path, waiver mechanism)
assert: explicit operator waiver receipt (§5.4) is the only bypass, and it is logged
```

### TC-9.3: Swapped, stale, or wrong-row evidence rejected (v2, sol amendment H)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Use disposable dev sessions, real binaries, a dev operator principal, and real contract probes; induce row permutations and stale script hashes through the real close verifier.
spine_of: TC-9.0, spine_step_ref: S3
```
given: evidence items with (a) row_id swapped between two rows, (b) script hash from a
       prior walkthrough version, (c) observation not matching the row's contract,
       (d) missing/wrong operator identity, (e) timestamp preceding the walkthrough,
       (f) artifact hash not matching the stored artifact (TCOV R1: full binding set)
when:  the close verifier validates evidence bindings
then:  all six cases (a)–(f) rejected (CONS-R-2 R2)
assert: rejection names row_id + defect class; "worked fine" prose attestation also rejected
```

### TC-9.5: Walkthrough preserves Phase-7 linkage and enforces the predicate matrix (v4, TCOV-13 R3-prep)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Use disposable dev sessions, real binaries, a dev operator principal, and real contract probes; generate a walkthrough from a hashed Phase-7 ConOps artifact, then induce linkage and typed-observation mutations through the real close verifier.
spine_of: TC-9.0, spine_step_ref: S3
```
given: a deterministic, hashed roadmap/conops.md with source rows for API, CLI, GUI, and
       human-judgment observations; its generated walkthrough carries hash-linked mappings
       to those source rows; parameterize (a) mismapped source row, (b) changed source hash,
       (c) API status/JSON-path mismatch, (d) CLI exit-code/token mismatch, (e) GUI missing
       named element/value, and (f) a human-judgment row without its named rubric + fixture
when:  the close verifier validates the walkthrough and submitted evidence
then:  every linkage or typed-predicate mutation is rejected; the human row routes to its
       judgment gate rather than receiving a machine semantic-match verdict
assert: the walkthrough extends, never replaces, Phase 7 ConOps; both artifact hashes and
        each source-row mapping must validate before close can proceed
```

### TC-9.6: ConOps waivers bind exactly one unevidenced row and script (v4, TCOV-14 R3-prep)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Use disposable dev sessions, real binaries, a dev operator principal, and real contract probes; issue a valid waiver challenge for one missing-evidence row and replay it across row and script scopes.
spine_of: TC-9.0, spine_step_ref: S4
```
given: a close block for unevidenced row A under script hash H, plus receipts parameterized as
       exact (A,H), wrong row B with H, A with prior hash H-1, and a receipt lacking either
       row_id or script_hash; retain a second unevidenced row B where applicable
when:  the close verifier evaluates each receipt
then:  only the exact (A,H) receipt waives row A; every scope mutation is rejected and any
       remaining unevidenced row continues to block close
assert: a ConOps waiver cannot become a script-wide or row-wide bypass; rejection names the
        missing or mismatched row/script binding
```

---

## US-10: Durable spine artifacts (M6)

### TC-10.0: Next session's bootstrap consumes prior spine artifacts [spine: US-10]
**Data Strategy: REAL-DATA** — two chained real sessions (dogfood: this session then its successor).
spine_steps: S1 session A closes writing node-registry/spine artifacts, S2 session B bootstrap locates them, S3 B references spine without transcript access
```
given: session A closed with spine artifacts on disk
when:  session B bootstraps in the same project
then:  B's bootstrap surfaces A's spine artifacts
assert: B can name the executable spine entry points with zero reads of A's transcript
```

### TC-10.2: Corrupt spine artifact detected at bootstrap
**Data Strategy: SYNTHETIC** — truncate the artifact file.
spine_of: TC-10.0, spine_step_ref: S2
```
given: spine artifact truncated mid-JSON
when:  session B bootstrap validates it (BOOT-SPINE)
then:  integrity failure reported, artifact quarantined, bootstrap exits BROKEN (2)
assert: exit 2, not degraded — BOOT-SPINE corruption is blocking (CANON R1 fix); the
        original corrupt artifact is preserved in place, a named quarantine status is recorded,
        and defect + path + remediation are named (no move, overwrite, or deletion)
```

---

## US-11: Frozen sections excluded from re-critique (M7)

### TC-11.0: Frozen section absent from round N+1 dispatch [spine: US-11]
**Data Strategy: REAL-DATA** — Use the real `debate.py` and a copy of `SKILL.md`. Mark specific nodes as settled in `debate-nodes.json`, run payload assembly, and verify the payload excludes the frozen content. Edit the frozen spec bytes directly, run assembly, and assert that it blocks.
spine_steps: S1 mark section frozen in node registry, S2 assemble round N+1 dispatch payload, S3 dispatch excludes frozen content
```
given: spec with section X frozen after round N convergence
when:  round N+1 payload is assembled
then:  section X content absent (a one-line frozen stub may remain)
assert: payload diff proves exclusion; token count drops accordingly
```

### TC-11.2: New concern naming frozen section reopens exactly it
**Data Strategy: REAL-DATA** — Use the real `debate.py` and a copy of `SKILL.md`. Mark specific nodes as settled in `debate-nodes.json`, run payload assembly, and verify the payload excludes the frozen content. Edit the frozen spec bytes directly, run assembly, and assert that it blocks.
spine_of: TC-11.0, spine_step_ref: S1
```
given: frozen section X and a new concern that names X
when:  the reopen check runs
then:  X unfreezes; registry logs the unfreeze event with the naming concern id
assert: only X reopens (no blanket thaw); event has concern id + round
```

### TC-11.3: Frozen-bytes mutation without reopen blocks dispatch (v2, sol amendment H)
**Data Strategy: REAL-DATA** — Use the real `debate.py` and a copy of `SKILL.md`. Mark specific nodes as settled in `debate-nodes.json`, run payload assembly, and verify the payload excludes the frozen content. Edit the frozen spec bytes directly, run assembly, and assert that it blocks.
spine_of: TC-11.0, spine_step_ref: S2
```
given: frozen node X whose spec-file content is edited (hash no longer matches registry), and
       a conductor-adjacent rehash/rewrite of its node snapshot that preserves envelope shape
       but conflicts with the append-only event chain
when:  round N+1 payload assembly runs
then:  dispatch blocked naming node X and the hash mismatch
assert: block persists until a named concern reopens X; the chain detects the rehashed but
        unauthorized rewrite as tamper evidence — detection, not prevention, is asserted
```

### TC-11.4: Freeze eligibility follows the required-reviewer decision table (v6, R4: codex MED-6 + gemini Data Strategy; lineage: v4 TCOV-15 R3-prep)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Feed induced leaf-heading spec fragments and reviewer/finding records through the real `debate.py` parser and freeze-eligibility boundary, one decision-table row at a time.
spine_of: TC-11.0, spine_step_ref: S1
```
given: real parser output for induced spec fragments, with freeze requests parameterized as:
       | required reviewer verdicts | node-bound finding state                    | expected |
       | all valid                  | none unresolved                             | freeze   |
       | one missing or invalid     | none unresolved                             | block    |
       | all valid                  | unresolved HIGH/MED/LOW finding             | block    |
       | all valid                  | LOW finding resolved-as-noted                | freeze   |
       | all valid                  | concern without node_id or resolvable anchor | block    |
when:  the freeze gate evaluates each request
then:  only eligible rows create a hash-pinned frozen node
assert: any-severity unresolved finding and every unresolvable concern block freeze; a
        resolved-as-noted LOW finding is not treated as unresolved
```

---

## US-12: Debate node registry persists (M7)

### TC-12.0: Registry survives checkpoint/resume with settled state intact [spine: US-12]
**Data Strategy: REAL-DATA** — real checkpoint/resume cycle in a dogfooded debate.
spine_steps: S1 registry written during round, S2 checkpoint, S3 resume in fresh conversation, S4 round N+1 reads settled/volatile split
```
given: debate with 4 settled, 2 volatile, 3 derived nodes registered
when:  checkpoint then resume occurs
then:  resumed session's round N+1 dispatch reflects the same split
assert: no settled node re-enters volatile without a logged unfreeze event
```

### TC-12.2: Registry/spec version mismatch detected on resume (R3-guardrail: CONS-5, TCOV-9)
**Data Strategy: REAL-DATA** — use a valid node registry whose envelope records an older spec version than the current spec.
spine_of: TC-12.0, spine_step_ref: S3
```
given: a valid canonical snapshot and event chain at spec v(N), while the current spec is v(N+1)
when:  resume validation runs
then:  mismatch blocks round dispatch, points to reconciliation (US-13 flow)
assert: nonzero/blocked with both versions named
```

---

## US-13: Deterministic derived-artifact reconciliation (M8)

### TC-13.0: Spec bump triggers mechanical re-diff before next round [spine: US-13]
**Data Strategy: REAL-DATA** — replay card-5715's real spec v8→v9 bump with its real tests-pseudo.
spine_steps: S1 spec version bumps, S2 reconciliation diffs each derived artifact, S3 clean → round proceeds / dirty → blocked
```
given: card-5715's v9 spec and its (drifted) tests-pseudo as inputs
when:  reconciliation runs
then:  the drift that caused R8/R11 rework is reported mechanically
assert: dirty verdict names artifact + drifted sections; no LLM call in the diff path
```

### TC-13.2: Clean artifacts pass without false positives
**Data Strategy: REAL-DATA** — a version bump from a session known to be drift-free.
spine_of: TC-13.0, spine_step_ref: S3
```
given: spec bump where derived artifacts were correctly regenerated
when:  reconciliation runs
then:  clean verdict; round dispatch unblocked
assert: exit 0 (guards against a gate that cries wolf and gets bypassed)
```

### TC-13.3: Semantic rename/move detected despite surviving anchors (v6, R4: codex MED-6 + gemini Data Strategy; lineage: v2 sol amendment H)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Create a temporary git workspace with real spec/derived artifacts, induce a bound-entity rename/move while preserving a same-named anchor, and run the real `reconcile_derived.py` adapters.
spine_of: TC-13.0, spine_step_ref: S2
```
given: for each adapter, an artifact where a bound entity moved/renamed but a
       superficially identical anchor still exists (e.g. TC id reused for different
       behavior; TMR user_story re-pointed; architecture component renamed with alias)
when:  reconciliation runs
then:  each adapter reports dirty with the semantic-binding change named
assert: anchor-existence-only checking would pass these; the adapters must not
```

### TC-13.4: Unavailable required adapter blocks fail-closed (v6, R4: codex MED-6 + gemini Data Strategy; lineage: v2 TCOV R1)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** In a temporary git workspace containing real spec/derived artifacts, invoke the real `reconcile_derived.py` with one required production adapter made unloadable through its normal configuration/import boundary.
spine_of: TC-13.0, spine_step_ref: S2
```
given: reconciliation run with one required adapter unloadable (missing module / crash), and a
       conductor-adjacent rehash/rewrite of a reconciliation report that preserves its local
       envelope but conflicts with its provenance chain
when:  reconciliation runs
then:  verdict is NOT clean; dispatch and convergence both blocked
assert: block names the unavailable adapter; absence never degrades to "clean"; the report
        rewrite is detected through the chain as tamper evidence, not prevented as an OS write
```

### TC-13.6: Non-derivable fingerprints route to a judgment gate (v6, R4: codex MED-6 + gemini Data Strategy; lineage: v4 TCOV-17 R3-prep)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** In a temporary git workspace, run the real `reconcile_derived.py` over real artifacts whose induced asserted contract field lacks a machine-comparable derivation alongside a normally derivable fingerprint.
spine_of: TC-13.0, spine_step_ref: S2
```
given: a reconciliation adapter whose one mapped field has no deterministic fingerprint
       derivation, and a proposed classification of either mechanical clean or judgment with
       a named rubric and golden fixture
when:  reconciliation configuration and reporting run
then:  the non-derivable mechanical claim is rejected; the judgment classification is accepted
       only with its rubric + fixture and is reported as judgment rather than clean
assert: no absent fingerprint is replaced by prose/LLM inference or an implicit clean verdict;
        derivable fields remain mechanically compared under their normal adapter contract
```

---

## US-14: False-convergence guard (M8)

### TC-14.0: Quorum-AGREE with dirty derived diff rejected [spine: US-14]
**Data Strategy: REAL-DATA** — induced: run the REAL convergence evaluator with live reconciliation output; the AGREE quorum is induced, the guard path is live (v2 reclass).
spine_steps: S1 collect round verdicts, S2 run anti-bare-AGREE press, S3 require clean derived diff, S4 convergence verdict
```
given: round where all opponents return AGREE but tests-pseudo diff is dirty
when:  convergence evaluation runs
then:  convergence rejected as false
assert: rejection cites the dirty artifact; debate continues rather than advancing
```

### TC-14.2: Card-5715 R3/R7 replay flags both false convergences
**Data Strategy: REAL-DATA** — the actual R3 and R7 round artifacts from card-5715.
spine_of: TC-14.0, spine_step_ref: S4
```
given: card-5715 R3 and R7 round outputs replayed through the guard
when:  convergence evaluation runs on each
then:  both are flagged false
assert: R3 and R7 each rejected; the eventual true convergence round passes
```

### TC-14.3: Clean report for a DIFFERENT spec hash rejected (v6, R4: codex MED-6 + gemini Data Strategy; lineage: v2 TCOV R1)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Run the real convergence evaluator on induced on-disk round files: a production reconciliation report bound to real spec hash H1 and a quorum verdict file bound to real spec hash H2.
spine_of: TC-14.0, spine_step_ref: S3
```
given: quorum AGREE on spec hash H2, with a clean reconciliation report bound to H1 ≠ H2
when:  convergence evaluation runs
then:  convergence rejected — the clean report must bind the EXACT agreed spec hash
assert: rejection names both hashes; re-running reconciliation on H2 is the required remedy
```

### TC-14.5: Anti-bare-AGREE press parameterizes every failure mode (v6, R4: codex MED-6 + gemini Data Strategy; lineage: v4 TCOV-16 R3-prep, R3 TCOV-6)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Run the real convergence evaluator on induced first-two-round verdict/press files written in the production schema, independently varying one press failure mode per file set.
spine_of: TC-14.0, spine_step_ref: S2
```
given: an AGREE-ing critic in round 1 or 2; `MIN_PRESS_JUSTIFICATION_CHARS=280` measured
       after NFC normalization and trim; parameterize press output as a valid sustain citing a
       volatile node_id, 279/280-character sustains, padded/NFC variants, stale/frozen/unknown
       node citations, valid/invalid revise findings, malformed JSON/output, and transport failure
when:  convergence evaluates quorum for each result
then:  only valid threshold-satisfying sustain preserves that critic's AGREE for quorum;
       every other result records press-failed and excludes the AGREE this round
assert: a sustain must cite at least one current volatile node; a revise needs a source-bound
        finding; 280 is accepted only after NFC+trim measurement; stale/frozen/unknown citations,
        malformed output, and transport failure fail closed identically to sub-threshold sustain;
        no fallback treats a missing structured verdict as an unpressed AGREE, and the configured
        threshold/version is bound to the convergence record
```

### TC-14.6: Critic stdout contract rejects artifact-only returns (v5, R3 sync; R3-guardrail: TCOV-6)
**Data Strategy: REAL-DATA** — this round's gemini return is the real fixture.
spine_of: TC-14.0, spine_step_ref: S1
```
given: one valid critic return on stdout in `[AGREE]` xor critique-plus-`[SPEC]` form, and this
       round's gemini artifact-file-only return
when:  the dispatch layer evaluates debate_return_quality
then:  the valid stdout return is accepted; the artifact-only return is marked invalid
assert: documented salvage copies the artifact into the round workspace, registers its true
        findings_count, and writes a decisions-log salvage entry; salvaged evidence does not
        transform the raw artifact-only return into a successful dispatch
```

---

## US-15: Authorized waiver mechanism (M1, R1 revision)

### TC-15.0: Waived gate proceeds with durable receipt [spine: US-15]
**Data Strategy: REAL-DATA** — induced: block a REAL gate on dev infrastructure; the grant flows through the REAL operator channel (Telegram message on the dev bot → listener feed) (v2 reclass).
spine_steps: S1 gate blocks, S2 operator grant lands in channel log, S3 receipt validates + action proceeds, S4 receipt surfaces in close report
```
given: a session blocked at a mechanized gate with a valid exceptional reason
when:  the operator grant lands in the channel log and the receipt is minted
then:  the blocked action proceeds; receipt persists with gate id + block_id + artifact hashes
assert: close report lists the receipt; audit trail readable post-session
```

### TC-15.2: Bypass attempt without receipt blocked and logged
**Data Strategy: REAL-DATA** — induced: retry the blocked action against the REAL enforcement boundary with no receipt (v2 reclass).
spine_of: TC-15.0, spine_step_ref: S2
```
given: same blocked state, no waiver receipt
when:  the conductor retries the blocked action
then:  still blocked; the attempt itself is logged
assert: no conductor-side action (including raw waivers.log edits) substitutes for a receipt
```

### TC-15.3: Forged/stale/misbound receipts fail (v6, R4: gemini 2.1; lineage: v2 sol amendment H)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Use disposable dev sessions, real binaries, a dev operator principal, and real contract probes; induce each §5.4 rejection form against the real receipt validator.
spine_of: TC-15.0, spine_step_ref: S3
```
given: receipts that are (a) proof-less, (b) edited post-mint, (c) issued pre-block,
       (d) wrong-session, (e) wrong-gate, (f) expired, (g) malformed, or (h) signed only over
       the legacy `(session_id, gate_id, block_id, nonce)` tuple while the full JCS challenge's
       affected-artifact hashes or justification hash differ (parameterized)
when:  receipt validation runs
then:  every forgery class rejected
assert: rejection names the violated binding; only a signature over the entire RFC 8785 JCS
        waiver_challenge envelope is accepted, and conductor-minted receipts are impossible by
        construction
```

### TC-15.5: Bridge-authoritative nonce consumption survives listener and cache loss (v6, R4: codex HIGH-5; lineage: v5 R3 sync)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Consume a grant through the real Telegram bridge authority, capture its signed consumption receipt, restart the real listener, then delete or replace the local nonce audit cache before replay.
spine_of: TC-15.0, spine_step_ref: S2
```
given: a real dev-operator grant whose challenge nonce was consumed in the bridge authority
       domain and returned a signed consumption receipt
when:  the listener restarts and the local `.adversarial-spec/nonces.jsonl` cache is
       parameterized one-at-a-time as: deleted, replaced with a pre-consumption copy,
       truncated mid-record (corrupted), and rolled back to a stale post-consumption
       snapshot; then the same receipt/proof nonce is presented again in each condition
then:  bridge-side authoritative state rejects replay in every local-cache condition,
       including the corruption path (a truncated/unreadable cache is never treated as
       "no record found, allow") (v6.1, R4-guardrail: TCOV-2)
assert: the rejection names the consumed nonce and validates the bridge-signed consumption
        receipt; neither in-memory listener state nor local nonce-cache presence/content can
        authorize issuance or acceptance, and the original waiver remains bound to its block
```

### TC-15.6: Authority scoping rejects a conductor rewrite and detects journal tampering (v5, R3 sync)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Use a real operator-signed dev receipt and a real conductor-adjacent journal, then induce a conductor-side rewrite with recomputed hashes.
spine_of: TC-15.0, spine_step_ref: S3
```
given: an operator-signed receipt and a hash-chained conductor-adjacent journal; the conductor
       rewrites the receipt and recomputes envelope hashes, then rewrites a journal entry
when:  receipt validation and journal-chain validation run
then:  signature validation rejects the rewritten receipt; the chain detects the journal rewrite
assert: receipt authority is prevention by the operator-held key, while journal integrity is
        detection-not-prevention; both outcomes are named rather than inferred from local hashes
```

---

## US-16: G3 contract-boundary guardrail (M4, R1 revision)

### TC-16.0: Contract-boundary artifact is a complete v3 substrate oracle, zero fizzy-repo scope leaks [spine: US-16] (v4, TCOV-12 R3-prep; R3-guardrail: CANON-2)
**Data Strategy: REAL-DATA** — **Technique note: synthetic mutation over real artifacts.** Lint the real execution plan and contract artifact, then remove or mutate one required v3 binding at a time.
spine_steps: S1 enumerate fizzy deltas referenced by M4/M5, S2 emit contract-boundary artifact, S3 lint execution plan file scopes
```
given: the slice's execution plan and contract-boundary artifact, including per consumed
       delta contract_id, compatible version range, capability probe, evidence schema, exact
       protected skill transition, and G3 tracking pointer; parameterize omission/mutation of
       each required substrate binding: liveness-gate-test-ladder-fizzy spec-draft-v4, DD-3
       no-new-lanes/existing-lane-FSM, DD-5 immutable load-time capability, liveness-v4 §7.5
       composed gate stack, Session-TMR-registry-only input, and challenge-bound override
when:  the boundary lint runs
then:  the complete artifact passes; every missing, altered, or conflicting binding fails with
       its affected transition named; zero tasks scope fizzy-repo files
assert: the canonical card-derivation/promotion input is only the Session TMR registry at
        session-manifest.json.tmr_registry_path (with consumed path + hash recorded), never
        `.architecture/tests/registry.json`; no skill-side lane or override fallback exists
```

### TC-16.1: promotion-commit-v1 consumes each fizzy prepare receipt exactly once (v6, R4: codex CRIT-1 + Claude F3; lineage: R3-guardrail TCOV-4)
**Data Strategy: REAL-DATA** — **Technique note: induced live-contract exercise.**
spine_of: TC-16.0, spine_step_ref: S2
```
given: a valid fizzy-issued promotion-prepare-v1 receipt bound to the JCS intent hash, session
       id, registry hash/version, active-card set, applicable receipt ids, ConOps evidence hash,
       expiry, and expected transition version; plus one variant per §5.2 reason code —
       conductor-generated, unsigned, wrong-key, expired, replayed (already consumed),
       stale-cas, state-stale after prepare, and intent-mismatch — plus a transport fault
       (expected result: promotion-transport-unavailable); and a missing or
       version-incompatible promotion authority capability
when:  the valid prepare receipt is committed once, replayed, and every failing variant is
       submitted through the real promotion-commit-v1 boundary
then:  the valid submission creates exactly one terminal commit; replay and every invalid/
       stale variant fail closed without another transition; missing/incompatible authority
       returns authority-capability-missing
assert: commit verifies fizzy signature + key, expiry, single use, and CAS version, then
        revalidates authoritative state before terminal visibility; no receipt failing any
        §5.2 reason-code check authorizes completion, and each rejected variant carries its
        exact matching reason code (v7, R5-guardrail: CANON-1); every
        response is exactly one §5.2 RemoteOperationResult token — promotion-committed,
        promotion-commit-rejected (with its named reason code, incl. reason=replayed),
        promotion-transport-unavailable, or authority-capability-missing — and no locally
        signed or unsigned fallback exists (v6.1, R4-guardrail: CANON-1)
```

### TC-16.2: Execution-plan task scoping a fizzy path is flagged (v6, R4: codex MED-6 + gemini Data Strategy)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Copy the real execution plan into a temporary workspace, induce one fizzy-repo file scope, and run the real contract-boundary linter.
spine_of: TC-16.0, spine_step_ref: S3
```
given: plan copy with one task whose file scope includes the fizzy repo
when:  boundary lint runs
then:  the task is flagged with its offending path
assert: nonzero exit naming task_id
```

### TC-16.3: Incompatible or unavailable fizzy contract blocks advancement (v2, sol amendment H)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Use disposable dev sessions, real binaries, a dev operator principal, and real contract probes; induce an incompatible version or unavailable capability probe for the consumed `contract_id`.
spine_of: TC-16.0, spine_step_ref: S1
```
given: a gates.json entry with owner:fizzy whose capability probe fails or whose
       version range excludes the live fizzy contract
when:  the affected transition is attempted
then:  advancement blocked; no skill-side fallback path permits it
assert: block names contract_id + expected vs live version
```

### TC-16.4: promotion-prepare-v1 rejects invalid intents without minting a receipt (v6.1, R4-guardrail: TCOV-1)
**Data Strategy: REAL-DATA** — **Technique note: induced live-contract exercise.** Use disposable dev sessions and the real fizzy promotion-prepare-v1 boundary; induce each mismatch one at a time against live authoritative state.
spine_of: TC-16.0, spine_step_ref: S2
```
given: JCS promotion intents parameterized one-at-a-time with: a stale active-card set, a
       wrong ConOps-evidence hash, a wrong evidence-index hash, a session not in the required
       pre-prepare state, and a CAS/transition-version mismatch already detectable at prepare
       time; plus one fully valid intent as control
when:  each intent is submitted to the real promotion-prepare-v1 boundary
then:  every mismatched intent returns promotion-prepare-rejected with the matching §5.2
       reason code and NO receipt is minted (nothing later submittable to promotion-commit-v1);
       only the valid control intent yields a signed one-time receipt
assert: prepare-side rejection is distinct from commit-side rejection (result token differs);
        no rejected-prepare path leaves a mintable or replayable receipt artifact in any
        durable state; the control receipt commits exactly once (cross-check TC-16.1)
```

---

## v3 additions (R2 synthesis, 2026-07-19)

### TC-0.4: BOOT-REGISTRY branches on attested regime, never on absence (v7, R5: sol MED promotion; lineage: v6 R4 codex CRIT-2, v3 R2)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise (v7 promotion — isolation was a convenience, not an impossibility; regime branching is a critical seam post-F2).** Create three disposable sessions through the real `pipeline_create_session` boundary (one pre-cutoff for legacy, two post-cutoff), induce the hardened+missing-registry state by removing the registry file on disk, and run the real bootstrap against each.
spine_of: TC-0.0, spine_step_ref: S2
```
given: a validated creation-attestation/mirror pair whose hardening_regime is
       legacy | hardened(valid registry) | hardened(missing registry)
when:  bootstrap runs BOOT-REGISTRY for each
then:  legacy → check not-applicable, exit contribution 0; hardened+valid → pass;
       hardened+missing → broken (exit 2)
assert: verdicts differ ONLY by the validated attested regime; deleting the registry from the
        legacy case does not change its verdict (absence never infers regime), while changing
        only the mirror without a matching attestation fails before branching
```

### TC-6.4: Vacuous empty answer fails critical fixtures (v3, R2)
**Data Strategy: SYNTHETIC** — candidate answer `{"next_actions": [], "gate_citations": [...]}` with correct citations.
spine_of: TC-6.0, spine_step_ref: S3
```
given: a critical fixture with required_next_actions nonempty; answer proposes zero actions
when:  scoring runs
then:  fixture fails (required ⊄ proposed)
assert: failure reason names the missing required action(s)
```

### TC-6.5: Missing or incompatible baseline blocks the pre-session gate (v3, R2)
**Data Strategy: SYNTHETIC** — candidate model id with no baseline for current (harness version, fixture-set hash).
spine_of: TC-6.0, spine_step_ref: S3  <!-- CONS-6 R2: TC-6.0 defines S1-S3 only; baseline lookup happens at the S3 verdict step -->

```
given: no baseline row matches (candidate policy, harness version, fixture-set hash, scoring schema)
when:  the pre-session gate evaluates the candidate
then:  gate blocks; no silent fallback to another model's baseline
assert: block names the missing baseline key tuple
```

### TC-7.4: Verification-card identity survives registry churn (v3, R2)
**Data Strategy: REAL-DATA** — real session TMR registry mutated by an unrelated TMR update between two emissions.
spine_of: TC-7.0, spine_step_ref: S2
```
given: card emitted for tmr_uid X; an unrelated TMR then changes (registry_hash changes)
when:  emission re-runs
then:  card for X is upserted under its stable key (session_id, tmr_uid,
       obligation_revision, obligation_policy_version); zero duplicate cards
assert: board card count for X unchanged; registry_hash recorded as snapshot field
        only; card records tmr_registry_path + tmr_registry_hash (CANON-3 R2)
```

### TC-7.5: Criticality resolution has exactly one writer (v3, R2)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Real registry; attempt criticality write via a non-classifier path.
spine_of: TC-7.0, spine_step_ref: S1
```
given: a TMR with critical_seam=null, including a classifier attempt to set
       critical_seam:false without a decision record linking rule version, source-artifact hash,
       and resolved architecture link
when:  a component other than criticality_classifier.py attempts to set criticality
then:  non-classifier write rejected; unlinked false classification rejected; classifier
       resolution succeeds only with the required decision record and updates criticality_source
assert: registry audit shows exactly one authorized writer for the transition; absent linkage
        preserves null or resolves conservatively true, never false
```

### TC-8.6: Deferred obligation transfers only at the authority commit point (v3, R2; v8.3, FTCOV-6)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Use disposable dev sessions, real binaries, a dev operator principal, and real contract probes; issue a deferred waiver naming (a) a nonexistent successor and (b) an existing hardened successor.
spine_of: TC-8.0, spine_step_ref: S3
```
given: (a) a tmr-deferred receipt naming a nonexistent successor and (b) a valid receipt naming
       an existing hardened successor whose obligation appears in the validated snapshot's
       provisional transfer plan
when:  issuance, parent PRE-commit evaluation, intent construction, and authority CAS commit run
then:  (a) is rejected; (b) issuance creates neither transfer authority nor a successor
       obligation record, PRE-commit accepts the receipt/successor/provisional-plan tuple, and
       the intent copies its plan byte-identically into successor_transfer_set
assert: only the authority CAS commit atomically creates parent-complete plus the successor
        inherited-obligation record; before commit no committed record can exist, and after
        commit the successor record proves inclusion rather than satisfaction
```

### TC-9.4: Typed predicate mismatch rejected; judgment rows route to rubric (v3, R2)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Use disposable dev sessions, real binaries, a dev operator principal, and real contract probes; submit a real API response log that fails its JSON-path assertion and a human-judgment row to the close verifier.
spine_of: TC-9.0, spine_step_ref: S3
```
given: ConOps row with typed predicate (API status+JSON-path); evidence log failing the path
when:  close verifier runs
then:  row rejected mechanically; the human-judgment row is not machine-verdicted —
       it routes to its named judgment gate (rubric + fixture)
assert: rejection cites row_id + failed predicate; judgment row cites its gate_id
```

### TC-12.3: Event-log hash-chain break is detected (v3, R2)
**Data Strategy: REAL-DATA** — Generate a valid node registry log, tampered line N's predecessor hash, and run the real parsing/validation script to verify it detects the break and exits nonzero.
spine_of: TC-12.0, spine_step_ref: S2
```
given: a valid event log whose round finding/reopen metrics are recomputed from events, then
       (a) line N's predecessor-hash no longer matches line N-1 and (b) snapshot counters are
       edited while the validated event chain remains unchanged
when:  registry validation runs (bootstrap or round begin)
then:  chain break detected; registry treated as corrupt (fail closed); unchanged valid events
       retain their recomputed metrics despite edited snapshot counters
assert: error names the first broken line index; finding and reopen metrics come only from the
        validated event chain, never mutable snapshot counters
```

### TC-13.5: Rename without lineage mapping is dirty despite resolving anchor (v3, R2)
**Data Strategy: REAL-DATA** — real tests-pseudo adapter over a spec bump that renames a TC while keeping its anchor text.
spine_of: TC-13.0, spine_step_ref: S2
```
given: spec bump renames/moves an item; old and new fingerprints unlinked by lineage
when:  reconcile_derived.py runs
then:  adapter verdict dirty even though the superficial anchor resolves
assert: report shows fingerprint pair + missing-lineage reason; dispatch blocked
```

### TC-14.4: Failed press excludes AGREE from quorum (v3, R2)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Real round state; induce a sub-threshold sustain justification.
spine_of: TC-14.0, spine_step_ref: S2
```
given: critic AGREEs in round ≤2; press verdict is sustain with justification below threshold
when:  convergence is evaluated
then:  that AGREE does not count toward quorum this round
assert: convergence_basis records press-failed for the critic
```

### TC-15.4: Waiver replay across blocks or nonces is rejected (v3, R2)
**Data Strategy: REAL-DATA** — **Technique note: induced live exercise.** Use disposable dev sessions, real binaries, a dev operator principal, and real contract probes; replay a legitimate grant for block A against block B and reuse its nonce.
spine_of: TC-15.0, spine_step_ref: S2
```
given: a valid challenge-bound receipt for (gate G, block A); a new block B on the same gate;
       and a receipt with a valid block_id + nonce but a signature from an unauthorized key
when:  the receipt (or its proof) is presented for B, its nonce is reused, or the unauthorized
       signature is validated
then:  rejected: challenge mismatch (wrong block_id / artifact set / consumed nonce)
assert: rejection distinguishes wrong-block, reused-nonce, and unauthorized-key signatures;
        block B remains blocked
```


<!-- P4_INVARIANT_TESTS_START -->
## Invariant Tests (Phase 4, v2 — renumbered to architecture-invariants.json v2)

Each test pairs a positive assertion with a counterfactual so a wrong-mechanism
pass is detectable (semantic-oracle rule).

### TC-INV-001: Gate closure with verification_scope and real-boundary negative tests
given: gates.json, the phase-doc corpus, and the named negative-test set
when: gate_inventory.py check --all and lint run
then: every gate carries one classification AND one verification_scope; every mechanized skill-owned gate's negative test executes the REAL CLI/hook boundary and the named gate_id blocks
assert: unclassified row, missing scope, unmapped doc marker, and a tautological negative test (asserts existence, never invokes boundary) each fail
Schema refs: gates.json normalized form, violation_modes[]

### TC-INV-002: Blocking transitions fail closed incl. uncommitted-transaction artifacts
given: a blocking transition and its required-artifact matrix
when: each required artifact is removed, truncated, hash-flipped, major-bumped, or left inside an uncommitted StateTransaction
then: the transition blocks with a named verdict per defect class
assert: no class yields advance; restoring the valid committed artifact unblocks the same transition
Schema refs: envelope, StateTransaction manifest

### TC-INV-003: Sole-writer authority and mirror-never-authority
given: the Session TMR registry, session-manifest mirror, and signed creation attestation
when: a non-owner attempts a criticality/evidence write, and the mirror is rewritten to claim a different hardening_regime
then: rogue writes rejected; both mutation-kind owners persist only through TmrRegistryWriter; regime branching follows only the attested value
assert: rewritten mirror fails validation; a direct registry-file write bypassing TmrRegistryWriter is caught by the sole-path scan; derivation reports carry tmr_registry_path + tmr_registry_hash matching the consumed file
Schema refs: session-manifest.json, creation attestation

### TC-INV-004: Named results, never success-shaped
given: remote-operation invocation points with fault injection
when: transport loss, absent capability, forged receipt, stale CAS, and success are induced
then: each yields exactly one per-operation result token with correct reason code (successful prepare = promotion-prepared carrying the receipt; ready preflight = live-preflight-ready; status lookup = commit-status-resolved); never-invoked steps journal PromotionSequenceResult
assert: an injected handler mapping an exception to a pass-shaped verdict is caught (CON-001-class guard); no non-terminal success token exposes terminal completion
Schema refs: §5.2 enums

### TC-INV-005: Strict codec validates before interpretation
given: valid + mutated artifacts (hash-flip, duplicate member, BOM, NaN, lone surrogate, oversize, unknown major)
when: any consumer loads each artifact
then: mutated artifacts rejected with named verdicts before any payload read
assert: valid artifact round-trips with recomputed content_hash equal to stored; ambiguous numerics encoded as strings survive round-trip
Schema refs: envelope, JCS RFC 8785, codec limits

### TC-INV-006: Exact signature input, external trust roots, safe paths
given: receipts signed correctly, over a tuple subset, with an artifact-embedded key, and paths with ../, absolute, symlink, cross-session targets
when: MW-004 verification and the rooted path layer run
then: only whole-signature_input correct-domain signatures validate; unsafe paths fail closed without opening targets
assert: subset-signature and self-keyed receipts fail even when hashes verify; symlink-to-inside-root still refused (no-follow, fstat-validated)
Schema refs: signature_input contract, trust-root config

### TC-INV-007: Contract closure gates consumed transitions
given: contract-boundary.md entries and probe results compatible/incompatible/absent
when: protected transitions attempt under each state
then: only compatible advances; others block with authority-capability-missing semantics, no skill-side fallback
assert: probe-skipping transition caught by boundary lint; fizzy-repo-scoped plan task fails lint
Schema refs: contract-boundary.md

### TC-INV-008: StateTransaction crash safety, leases, and roll-forward
given: a coupled multi-file change (registry + journal + index) under crash injection at every protocol step, plus a live writer holding its per-transaction lease while recovery and GC run
when: the process is killed between staging, PREPARED, replacement, and COMMITTED; a concurrent reader attempts the coupled set during replacement; recovery encounters the lease-held transaction
then: recovery either rolls the prepared transaction forward from staged hashes or aborts cleanly; recovery on the lease-held transaction waits within the deadline and re-reads — it never treats an active transaction as crashed
assert: acquisition order lease -> resource locks (canonical path order) holds for writers, recovery, and GC (no deadlock, no recovery race); recovery barrier runs before every coupled access (not just init); abort only before first replacement; post-first-replacement unverifiable state surfaces as transaction-corrupt (never 'aborted cleanly'); an attempted WAIVER of transaction-corrupt is rejected (non-waivable; explicit repair operation required, corrupt bytes preserved in the forensic quarantine directory); READER RACE (R5): a reader whose recovery scan preceded a writer's crash re-detects the PREPARED manifest via the post-lock coordinator-index scan while holding shared locks, releases every resource lock, recovers under lease -> exclusive locks, retries — it never observes A-new/B-old and never acquires a lease while holding resource locks; cross-session deferral coordinates via the repo-scoped .txn/; a committed manifest referenced by a live artifact is NOT pruned — pruning is reachability-aware and referenced transactions retain a compact commit certificate; a live lock sidecar cannot be replaced or unlinked (persistent identity)
Schema refs: PREPARED/COMMITTED manifest, transaction lease, commit certificate

### TC-INV-009: Audit coupling and quarantine-in-place
given: a state mutation with its required event record, plus a corrupted journal line
when: the mutation commits and the chain verifier runs
then: success is visible only after the event record commits in the same transaction; the corrupt line is detected as a chain break with named quarantine status
assert: original corrupt bytes remain in place; identity-less report (missing operation/transaction id, versions, hashes) is schema-invalid
Schema refs: report identity, event chain

### TC-INV-010: Configuration is release/spec-bound
given: a checkout where MAX_PHASE_REGRESSION_POINTS is changed without a spec bump, and a gate path reading an env var
when: reconcile_derived.py and the static env scan run
then: the invariants adapter reports dirty naming the drifted constant; the env read fails the scan
assert: the same change with a spec bump + updated anchor reconciles clean
Schema refs: reconciliation report

### TC-INV-011: Hook isolation and single role policy
given: the .claude/hooks/ import graph, hook registration state, and the shared role helper
when: static import scan, registration doclint, and role-precedence contract tests run
then: no hook imports adversarial_spec.*; an unregistered hook is reported absent; all hooks resolve roles via the one helper; each hook's declared signaling mode matches its event type; at most one slice-owned dispatcher per event; a preventive gate registered on a non-blockable event (e.g. PostToolUse) fails lint
assert: injected runtime import fails the scan; a fourth inline role branch fails the contract test; malformed input to a safety hook produces the blocking form, not allow
Schema refs: hook registration, CON-003

### TC-INV-012: Single-file durability protocol
given: slice modules and crash injection between temp write and replace
when: static scan for raw state writes runs and a registry write is interrupted
then: zero raw write_text/open-w on state paths; after crash the target holds complete old or complete new content; bootstrap feature-detects the platform capability profile; a symlink in a NON-final path component is refused (openat2 RESOLVE_BENEATH / per-component walk, not final-component O_NOFOLLOW)
assert: planted raw write caught; unsupported filesystem returns exactly filesystem-capability-unsupported;
        the legacy hyphenated alias and every other alias are rejected instead of degrading silently (v8.3, FTCOV-9)
Schema refs: single-file protocol

### TC-INV-013: Hash-decided staleness blocks dispatch and convergence
given: a frozen node pin, a renamed TMR without lineage, and evidence predating an obligation_revision bump
when: dispatch assembly, reconciliation, and the promotion predicate run
then: dispatch blocks on hash mismatch; reconciliation dirty; stale evidence fails the predicate
assert: untouched hashes dispatch clean; each dirty verdict names the exact stale artifact and hash pair
Schema refs: node_content_hash, fingerprints

### TC-INV-014: Hermetic local path is an import boundary
given: every blocking check run under denied socket/DNS and an import-graph scan of the bootstrap path
when: checks execute and the scan runs
then: no network syscall; no remote-transport import reachable from the local blocking path; missing remote evidence returns deferred-for-live-preflight
assert: advisory-only failure exits 1; advisory+blocking exits 2; failure output names check id, artifact, expected path, remediation
Schema refs: §3 exit contract

### TC-INV-015: Critic stdout contract with recorded salvage
given: one critic returning [AGREE] on stdout and one writing its critique to an artifact file
when: debate_return_quality evaluates the returns
then: stdout return valid; artifact-file return invalid with documented salvage flow and decisions-log entry
assert: salvage recorded as violation evidence, never a clean raw return; agentic-CLI prompt templates carry the stdout-only demand
Schema refs: §12.3 contract

### TC-INV-016: CLI determinism via the shared boundary
given: a new CLI invoked with an abbreviated long option, an unknown argument, a parse error, and --help
when: each invocation runs
then: abbreviation and unknown arguments are rejected; the parse error emits one structured result envelope (status/code/subject/remediation), not a bare exit; --help succeeds
assert: counterfactual — a CLI bypassing MW-008 (raw argparse defaults) is caught by the boundary conformance test
Schema refs: CliResult schema, exit mapping

### TC-INV-017: Remote completion reconciled by operation identity
given: a promotion commit whose response is lost after remote success, and a retry attempt under a new identity
when: the recovery protocol runs
then: status lookup by operation_id + receipt hash resolves committed-with-matching-intent to promotion-committed; the new-identity retry is rejected as replayed
assert: unestablishable status returns promotion-transport-unavailable and local code exposes no completion; blind retry never occurs
Schema refs: PSF-1 status lookup, §5.2 reason codes

### TC-INV-018: Transitive close binding
given: a prepared promotion intent binding the evidence-index hash, then a post-prepare tamper of the event-log head or spine manifest
when: promotion commit validates authoritative state
then: the DAG (spine-core -> evidence-index -> spine-manifest -> intent) detects the mismatch and commit is rejected; a cycle injection (artifact referencing a hash above it) is rejected at validation
assert: untampered close commits; the rejection names the broken link in the chain
Schema refs: spine-manifest.json, evidence index

### TC-INV-019: Authority-held evidence snapshot (narrowed custody claim)
given: a close-evidence AGGREGATE set registered into the authority domain, then a post-prepare local mutation of the evidence index
when: promotion prepare binds authority-computed hashes and commit revalidates
then: prepare against unregistered artifacts is rejected; the post-prepare mutation is detected by the AUTHORITY's snapshot comparison at commit, not by conductor arithmetic
assert: counterfactual — a prepare path accepting a conductor-supplied hash without a registered snapshot is structurally absent; absent registration capability returns authority-capability-missing (narrowed guarantee, never faked); NO artifact, log line, or result token represents aggregate custody as transitive leaf-blob closure (the narrowed-custody statement is present and machine-checkable)
Schema refs: evidence-snapshot-registration-v1 (PSF-7 expanded), close DAG

### TC-INV-020: Bound authorization state at prepare/commit
given: a promotion intent whose ValidatedAuthorizationSet was built from a successor record and waiver receipt, then a post-evaluation change to the successor record (or receipt revocation) in the authority domain
when: promotion prepare and commit revalidate authorization_set_hash and the successor-transfer set against current Fizzy authority state
then: the changed successor state invalidates prepare/commit (stale authorization_set_hash rejected); with unchanged state, tmr-deferred commit atomically records parent-complete + successor-inherited-obligation in the authority domain and local mirrors materialize from that committed result
assert: a local mirror write path that establishes transfer authority without a committed authority result is structurally absent; the intent binds authorization_set_hash, snapshot root, registry hash/version, active-card set, ConOps evidence root, session id, expected transition version, and successor-transfer set
Schema refs: ValidatedAuthorizationSet (MW-009), promotion intent (PSF-8)

### TC-INV-021: Independent provenance for critical evidence (branches disjoint)
given: a critical-seam obligation whose evidence set consists only of conductor-produced bytes (well-formed, correctly hashed, registered in the snapshot), plus a variant holding a valid TMR waiver
when: promotion evaluation applies the evidence-class provenance policy and the is_obligation_satisfied disjuncts
then: the evidence branch is NOT satisfied — conductor bytes lack an acceptable producer attestation (authority-observed, signed independent worker, or signed operator observation); the waiver variant satisfies ONLY the skip/deferral branch and never produces an independent-evidence verdict
assert: the same evidence WITH a valid independent attestation satisfies the evidence branch; a waiver is never recorded as a producer attestation; conductor-only artifacts remain available as diagnostics; the rejection names the missing provenance class
Schema refs: evidence provenance policy (PSF-9 amended), INV-021

### TC-INV-022: Architecture fingerprint covers the frozen set
given: a published artifact set with a computed architecture_fingerprint, then a post-publication edit to middleware-candidates.json (or the contract boundary, or the architecture doc body)
when: reconciliation recomputes SHA256(JCS({input_fingerprint, framework_profile, execution_surfaces, research_findings, target_architecture_hash, architecture_invariants_hash, middleware_candidates_hash, contract_boundary_hash}))
then: the fingerprint mismatch is detected and named; hashes omit the fingerprint field and volatile timestamps (normalized LF for the Markdown)
assert: an edit to ANY member of the frozen set breaks the fingerprint — no artifact in the set is outside the formula
Schema refs: architecture_fingerprint formula (INV-022)

### TC-INV-023: Canonical authorization-set encoding (v8.3, FTCOV-1)
given: an authorization-fact set presented in shuffled order and with one duplicated member,
       plus an authority response containing opaque snapshot_id and snapshot-root bytes
when: canonical_set() normalizes the facts before authorization_set_hash =
       SHA256(RFC8785_JCS({"domain":"validated-authorization-set-v1","trust_policy":
       {"policy_id","policy_version","policy_hash","keyset_epoch"},"predicate_version":...,
       "facts":canonical_set(...)}))
then: shuffled logical fact sets produce byte-identical authorization_set_hash values; duplicates
       are rejected rather than deduplicated or double-counted; prepare binds the exact returned
       snapshot_id + root bytes, while a locally recomputed or substituted root is intent-mismatch
assert: RFC 8785 never sorts a raw array; derived-hash domain separation is the in-object domain
        field (never a UTF-8 prefix concat); the client never computes snapshot_root, and a
        schema-declared identity tuple overrides byte ordering where declared
Schema refs: canonical_set (PSF-13), INV-023

### TC-INV-025: authorization_set_hash known-answer and mutation resistance (v8.3, FTCOV-2)
given: canonical inputs for the exact validated-authorization-set-v1 object, including trust
       policy_id, policy_version, policy_hash, keyset_epoch, predicate_version, and a canonical
       fact set whose facts each carry TMR identity/revision/policy/hash, authorization kind,
       receipt hash, nonce-consumption-proof hash, successor identity, successor authority
       version, inherited-record hash, and commit-certificate hash
when: an independent known-answer implementation computes SHA256 over RFC 8785 JCS of that
       in-object-domain object, then mutates one scalar, one fact field, or set membership at a time
then: the production digest is byte-identical to the known answer; every mutation changes it
assert: mutations cover policy_id, policy_version, policy_hash, keyset_epoch, predicate_version,
        the domain string, every listed fact field, and insertion/removal of one fact; no UTF-8
        domain-prefix concatenation is accepted for authorization_set_hash
Schema refs: ValidatedAuthorizationSet (MW-009), INV-023

### TC-INV-024: Trust-policy and keyset binding
given: a ValidatedAuthorizationSet built under TrustPolicy P1/keyset epoch E1, then a rotation to P2 (or E2) after local evaluation — and separately after prepare
when: promotion prepare and commit revalidate the trust_policy block inside authorization_set_hash
then: both rotation points yield state-stale requiring fresh evaluation; a receipt signed under a rotated key cannot ride the old authorization_set_hash through commit
assert: obligation_policy_version (TMR) and TrustPolicy.policy_version are distinct fields — a change to one never masquerades as the other; MW-004 returns the verified purpose + trust-policy/keyset identity consumed here
Schema refs: TrustPolicySnapshot (PSF-14), INV-024
<!-- P4_INVARIANT_TESTS_END -->

---

## v8 additions (gauntlet synthesis, 2026-07-20)

> Source: gauntlet-concerns-2026-07-20.json themes (GNT tags). Maturity: nl →
> acceptance; concrete binding lands with the implementing Phase 7 tasks.

### TC-8.10: Snapshot registration precedes prepare (GNT: SEC-3)
**Data Strategy: MOCK-EXTERNAL** — contract fixture for `evidence-snapshot-registration-v1`; the real `promotion_gate.py` sequence code runs.
```
given: a passing local promotion evaluation with (a) a registered, unexpired snapshot
       (fixture returns snapshot_id + authority-computed root), (b) registration never
       invoked, (c) an INVOKED registration the fixture rejects, (d) a registered but
       expired snapshot, (e) a prepare intent hand-built with a conductor-computed root
       differing from the authority root (v8.1, TCOV-3)
when:  the conductor advances toward REMOTE prepare
then:  (a) the prepare intent binds snapshot_id + the authority root; (b) prepare is not
       dispatched, journal records evidence-snapshot-registration-not-attempted; (c) the
       journaled result is evidence-snapshot-rejected and prepare is not dispatched;
       (d) re-registration is required — prepare against the expired snapshot_id is
       rejected by the fixture and journaled; (e) prepare is rejected intent-mismatch
assert: no path lets a conductor-computed root reach a prepare receipt; the §4 canonical
        sequence includes registration between local evaluation and prepare
```

### TC-8.17: Snapshot registration is idempotent at object and finalize layers (v8.3, FTCOV-3)
**Data Strategy: MOCK-EXTERNAL** — exercise the consumed registration contract with byte-identical uploads and lost finalize responses.
```
given: evidence object bytes B with digest D, registration operation_id O, set S, and a fixture
       that records stored object count/bytes plus signed finalize receipts
when:  B is uploaded twice, then finalize(O, S) loses its response and is retried as finalize(O, S),
       followed by finalize(O, S′) with changed set bytes
then:  both uploads acknowledge D with unchanged object count/bytes and no double storage;
       the identical finalize retry returns the original signed receipt; changed-set retry is
       rejected intent-mismatch
assert: per-object identity is byte digest while finalize identity is operation_id + identical
        registration set; neither layer may mint duplicate storage or a second snapshot receipt
```

### TC-8.11: Non-terminal remote successes are real result tokens (GNT: CB-1)
**Data Strategy: MOCK-EXTERNAL** — result-adapter fixtures across all remote operations.
```
given: fixture authority responses for successful live preflight, snapshot registration,
       prepare, and commit-status lookup
when:  each operation's result is adapted to RemoteOperationResult
then:  live-preflight-ready, evidence-snapshot-registered, promotion-prepared, and
       commit-status-resolved are returned as enum members (never exceptions, side
       effects, or failure-shaped results); none exposes terminal completion
assert: one canonical adapter handles every §5.2 token; promotion-committed remains the
        sole terminal success
```

### TC-8.12: Operation journal distinguishes never-attempted from response-lost (GNT: RC-2)
**Data Strategy: REAL-DATA** — **Technique note: induced crash.** Real journal code + kill-injected subprocess around a fixture authority.
```
given: crashes injected at three boundaries (v8.1, TCOV-4): (a) BEFORE the journal
       record persists (no dispatching record exists), (b) AFTER the fsynced dispatching
       record but BEFORE transport invocation, (c) AFTER transport invocation but before
       the response is recorded; plus (d) a retry of an uncertain operation with
       byte-identical request and (e) a retry with changed bytes under the same
       operation_id
when:  recovery runs
then:  (a) yields the exact step token (e.g. promotion-prepare-not-attempted for an
       unreached prepare); (b) and (c) both yield remote-uncertain — indistinguishable
       locally BY DESIGN — resolved only via the owning contract's status lookup by
       operation_id (commit-status-resolved for prepare/commit); (d) succeeds
       idempotently; (e) is rejected intent-mismatch
assert: the intent-durable record is fsynced before transport; a changed evaluation is a
        new operation_id; never-attempted is decidable exactly when no dispatching
        record exists
```

### TC-8.18: Result families reject cross-family and local-condition tokens (v8.3, FTCOV-4)
**Data Strategy: MOCK-EXTERNAL** — feed every named result token through the three production result adapters and the local recovery surfaces.
```
given: LocalReconciliationResult tokens mirror-materialized, mirror-reconciliation-pending,
       and mirror-reconciliation-corrupt; plus remote-uncertain and local-mirror-stale
when:  each token is offered to LocalReconciliationResult, RemoteOperationResult, and
       PromotionSequenceResult adapters
then:  exactly the three canonical mirror outcomes are accepted by LocalReconciliationResult;
       remote-uncertain and local-mirror-stale are rejected by all three adapters, with the
       former retaining operation-journal status-lookup recovery and the latter blocking
       dependent local work until mirror rematerialization
assert: every adapter-accepted enum token belongs to exactly one declared family; neither local
        condition is recast as a remote result, sequence result, or reconciliation outcome
```

### TC-8.13: Parent completion is never observable without successor-transfer facts (GNT: RC-1)
**Data Strategy: MOCK-EXTERNAL** — authority-contract fixture with CAS semantics; real predicate + reconciliation code.
```
given: a parent with a signature/policy-valid tmr-deferred receipt (not yet satisfying —
       the committed transfer does not exist until authority commit; v8.1, TCOV-6); the
       authority CONTRACT FIXTURE commits completion + successor_transfer_set as one CAS
       record (fixture-level conformance — the production contract's indivisibility is
       proven by the contract's own conformance suite at staging, queried at every CAS
       boundary, and is a recorded §8.2 capability-probe obligation, not this TC's
       oracle); crash injected between authority commit and successor mirror
       materialization
when:  the successor session starts and runs the startup reconciliation gate
then:  the successor derives its inherited obligations from the authority record at the
       required read-version BEFORE TMR compilation or card emission; operating from the
       stale mirror is blocked (local-mirror-stale)
assert: no observable state exposes parent-complete with an unowned obligation; the
        derivation binds the record CAS version + authorization_set_hash
```

### TC-8.14: local-mirror-stale rematerialization (GNT: RC-1/CB-1)
**Data Strategy: MOCK-EXTERNAL** — authority fixture serves the committed record; real StateTransaction mirror code.
```
given: authority-committed completion whose local mirror is missing or stale
when:  the conductor resumes
then:  local work on the affected set is blocked until idempotent rematerialization from
       the authority record succeeds; repeated rematerialization is a no-op
assert: retrying completion and reporting the authority-committed operation AS FAILED are
        both forbidden; surfacing the named local-mirror-stale state is REQUIRED (v8.1,
        TCOV-8); the mirror rebuild is the ONLY exit from local-mirror-stale
```

### TC-8.15: Transfer-record retention, archival, and deletion protection (GNT: RC-1; v8.1, TCOV-7)
**Data Strategy: MOCK-EXTERNAL** — authority-contract fixture with retention semantics; real successor lookup code.
```
given: (a) a committed transfer record with an undischarged successor obligation and an
       attempted authority-side deletion, (b) the same record archived after discharge,
       (c) a status lookup for an operation_id that never existed
when:  a late successor resolves its inherited obligations / the deletion is attempted
then:  (a) deletion is rejected while any transferred obligation is undischarged (the
       record is the GC root); (b) lookup yields record-archived with the resolvable
       transfer facts; (c) lookup yields proof-of-nonexistence, distinct from
       record-archived
assert: a late successor can always resolve a parent deferral or receive an explicit
        nonexistence proof; silent record loss is unrepresentable
```

### TC-1.4: StateTransaction lifecycle under crash and concurrency (GNT: RC-3; v8.3, FTCOV-5)
**Data Strategy: REAL-DATA** — **Technique note: induced crash/contention.** Real coordinator on a real filesystem with kill-injection and concurrent readers.
```
given: a coupled two-file write with crashes injected (a) before the PUBLISHING manifest fsync,
       (b) immediately after the PUBLISHING fsync but before the first replacement, (c) after
       each replacement, (d) with staged files corrupted, plus (e) two concurrent readers and
       a second writer during recovery
when:  recovery and reads run
then:  (a) may abort cleanly; (b) and (c) MUST roll forward from staged files; (d) enters terminal
       transaction-corrupt preserving artifacts in place; (e) exactly one recovery owner
       is lease-elected (readers release shared locks before contending — no inverted
       order), readers scan BOTH PREPARED and PUBLISHING manifests and retry, and no
       reader observes members from two generations (v8.2, CONS-V15/CONS-3/CONS-4)
assert: durable PUBLISHING fsync, not the first replacement, is the roll-forward boundary;
        lock acquisition is bounded with a named timeout result
```

### TC-1.5: Intermediate-symlink traversal is blocked (GNT: US-1)
**Data Strategy: REAL-DATA** — real resolver on a real filesystem with symlink substitution.
```
given: a session-relative path whose INTERMEDIATE directory is replaced by a symlink
       escaping the session root; and a repository on a filesystem failing the lock probe
when:  the resolver opens the path / bootstrap runs
then:  the open fails closed (descriptor-relative walk detects the substitution); the
       unsupported filesystem yields filesystem-capability-unsupported at bootstrap
assert: final-component O_NOFOLLOW alone never passes the suite; every component is
        device/mount-validated
```

### TC-15.7: Waiver issuance is idempotent across lost responses (GNT: SEC-4)
**Data Strategy: MOCK-EXTERNAL** — bridge-contract fixture; real journal + acceptance code.
```
given: an issuance whose response is lost after bridge-side nonce consumption
when:  the conductor retries with the same operation_id + challenge_hash
then:  the bridge returns the ORIGINALLY issued receipt (lookup, not reissue); a DIFFERENT
       challenge against the consumed nonce is rejected reused-nonce (a bridge-contract
       rejection reason, not a §5.2 code — v8.1 CANON-3)
assert: listener outage cannot permanently strand a gate; receipt recovery never mints a
        second receipt
```

### TC-15.8: TrustPolicy purpose scoping rejects wrong-purpose keys (GNT: SEC-1)
**Data Strategy: MOCK** — policy-evaluation fixtures over the real AuthorizationSetBuilder.
```
given: cryptographically valid receipts signed by (a) a key authorized for the exact
       purpose+scope, (b) a key authorized for a different purpose (minor-gate waiver key
       on a critical-seam promotion), (c) a key from a stale keyset epoch, (d) a rotated
       key whose successor gained no new purposes
when:  AuthorizationSetBuilder builds the validated snapshot
then:  only (a) and (d)-within-scope enter the snapshot; (b) and (c) are rejected as
       unauthorized (never as malformed)
assert: predicates cannot consume receipts that bypassed the builder; the snapshot's
        authorization_set_hash changes when policy identity/keyset epoch changes
```

### TC-2.4: Hook dispatcher owns its events (GNT: DD-2)
**Data Strategy: REAL-DATA** — real hook registration on a disposable Claude-hooks config.
```
given: (a) the canonical single-dispatcher registration, (b) a duplicate third-party
       handler registered on the same event, (c) a preventive gate declared with an async
       signaling mode
when:  BOOT-GATES runs and the shared conformance fixture suite executes against both
       skill-runtime and hook-local validators
then:  (a) passes; (b) is detected and fails BOOT-GATES; (c) fails lint; conformance
       verdicts agree across surfaces
assert: typed ALLOW/DENY/DIAGNOSTIC verdicts; divergent hook-vs-runtime validation is a
        bootstrap failure, not a silent drift
```

### TC-10.3: Close-binding DAG rejects reverse edges (GNT: CB-3)
**Data Strategy: SYNTHETIC** — schema validation over constructed artifact triples.
```
given: (a) a valid spine-core → evidence-index → spine-manifest triple, (b) an
       evidence-index referencing the spine manifest, (c) a spine-core referencing the
       evidence index, (d) a manifest whose spine_core_hash mismatches
when:  the close verifier validates the triple
then:  only (a) passes; (b) and (c) are schema violations (cycle prevention); (d) fails
       hash validation
assert: production order is enforced; each hash field names its exact §1 projection
```

### TC-3.3: live-preflight-unavailable is exercised (GNT: US-3)
**Data Strategy: MOCK-EXTERNAL** — transport fixture refusing the preflight endpoint.
```
given: (a) --live-preflight invoked against an unreachable authority (REMOTE case), and
       (b) hermetic bootstrap with a stale local attestation and NO preflight invoked
       (LOCAL case), each with and without a pending regime-sensitive transition (v8.1,
       TCOV-19)
when:  the preflight / bootstrap runs
then:  (a) yields exactly live-preflight-unavailable (an invoked RemoteOperationResult);
       (b) yields the LOCAL state deferred-for-live-preflight — the two tokens are never
       conflated; §3 mapping: deferred + pending regime-sensitive operation → exit 2,
       deferred + none pending → exit 1 with the named next action
assert: both tokens appear in adapter, journal, and operator surface with distinct
        semantics — closing the v7 zero-coverage gap (verified 2026-07-20)
```

### TC-0.10: Epoch-zero provisioning and permanent pre-rollout regime (v8.2, CONS-V15)
**Data Strategy: MOCK-EXTERNAL** — creation-contract fixture with and without an active rollout policy.
```
given: (a) session creation while NO rollout policy exists (fixture returns the signed
       epoch-zero attestation: hardening_regime pre-rollout, hardening_rollout_id null),
       (b) the same session resumed AFTER a policy is later issued, (c) a pre-contract
       session with no creation attestation resolved via historical lookup
when:  bootstrap and regime-sensitive branching run
then:  (a) the session operates pre-rollout with the registry check not-applicable and no
       hardened transition reachable; (b) the attested regime REMAINS pre-rollout
       (immutable for the session's lifetime); (c) legacy is mirror-stamped from the
       authority-backed created_at — the only materialization path without an attestation
assert: no post-hoc reclassification of an attested regime ever occurs; branching uses
        only the §1 canonical enum after mirror validation
```

### TC-13.7: Reconciliation reads one source snapshot (GNT: US-3)
**Data Strategy: REAL-DATA** — real reconcile_derived.py in a temp git workspace with induced mid-run mutation.
```
given: a reconciliation run during which an input artifact is mutated mid-run
when:  adapters execute
then:  the generation change is detected, the run is invalidated and re-executed against
       a consistent snapshot; the report records the source snapshot identity
assert: a clean report never describes a mixed-generation repository; lineage mappings
        load from reconciliation/lineage-map.json and both fingerprints must resolve
```
