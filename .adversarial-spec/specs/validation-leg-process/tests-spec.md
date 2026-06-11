# Acceptance Tests (tests-spec): Validation-Leg Production Process

> Promoted from `tests-pseudo.md` at finalize (2026-06-11). Stage: acceptance,
> ready for concretization in `scripts/tests/test_validation_emission.py`.
> Synced to the FINAL spec (v5 lineage). Roadmap: `roadmap/manifest.json`.
> Fixed gate contract: `fizzy-validation-contract.md` (all 8 reject codes in
> TC-0.2 verified present in the contract extract). Schema refs validated
> against spec §6.2 (ledger), §6.3 (evidence front matter), §6.4 (gate
> artifact), §6.5 (digest/reply grammar).
>
> Promotion corrections vs tests-pseudo (audit trail — pseudo file unchanged):
> 1. TC-2.6: `len == 12` → full sha256 (64 hex) stored; 12-hex prefix only at
>    artifact emission (spec §6.2 hash canonicalization, gauntlet SEC-8).
> 2. TC-3.8: `assemble-digest --reset-failed` → standalone `reset-failed`
>    subcommand (spec §7, gauntlet DD-1; matches TC-INV-A7).
> 3. TC-1.4: OQ-2 deferral resolved — digest part budget is 3500 UTF-8 bytes
>    (spec §6.5); BVA pair added inline.
>
> Coverage map: every US-0..US-13 has ≥1 TC (US-0: TC-0.1/0.2; US-1/2:
> TC-1.1..1.4, TC-G13; US-3: TC-2.1; US-4: TC-2.3; US-5: TC-2.4; US-6:
> TC-3.1, TC-G1/G9; US-7: TC-3.2, TC-G2/G6/G8; US-8: TC-3.3, TC-INV-A1/A5,
> TC-G10; US-9: TC-3.4/3.8, TC-G10; US-10: TC-4.1; US-11: TC-3.3, TC-INV-A5;
> US-12: TC-2.5, TC-G4/G5; US-13: TC-3.7). No orphan tests: every TC names
> its US/concern source.

## M0 — Getting Started

### TC-0.1: Cold-read bootstrap produces valid artifacts
**Data Strategy: REAL-DATA** — exercised on this session's own roadmap (the dogfood corpus is real data for this project).
```
given: a fresh agent with only the phase docs (incl. the §3 minimal row
       standard + good/rejected row examples) and this session's roadmap/manifest.json
when:  it follows the documented Phase 7 validation-leg entry point
then:  it produces conops.md + draft rows that pass check-rows (draft-stage
       validator; self-check applies later to system_validation.json — R3 fix)
assert: check_rows(rows, conops).valid == true
assert: elapsed <= 30 minutes
```

### TC-0.2: Docs enumerate all gate error codes with responses
**Data Strategy: STATIC** — doc-content check, no runtime.
```
given: the validation-leg phase docs
when:  scanned for fizzy's six reject codes (SESSION_MISMATCH, VV_NOT_OBLIGATED_AT_ALTITUDE,
       VALIDATION_ARTIFACTS_INCOMPLETE, VALIDATION_KIND_MISMATCH, VV_LEDGER_HAS_FAILURES,
       VALIDATION_IS_RELABELED_VERIFICATION) plus the two advance-time codes
       (SYSTEM_VALIDATION_MISSING, UNVALIDATED_USER_STORY)
then:  each code appears with a documented conductor response
assert: all 8 codes present with non-empty response text
```

## M1 — ConOps Derivation

### TC-1.1: Derivation includes every US id as a `### US-n` heading
**Data Strategy: REAL-DATA** — run against this session's actual roadmap manifest (14 stories US-0..US-13).
```
given: roadmap/manifest.json with user_stories US-0..US-13 (14 stories)
when:  conops derivation runs
then:  conops.md contains every id formatted strictly as a "### US-<n>" heading
       (not merely present anywhere — an id dumped outside a heading fails)
assert: for every id in manifest_story_ids: regex "^### US-<n>:" matches conops_md
assert: len(conops_md) >= 50 bytes and suffix == ".md"
```

### TC-1.2: Dropped story fails self-check (error case)
**Data Strategy: SYNTHETIC** — a manifest/conops mismatch must be manufactured; derivation by construction includes all stories.
```
given: conops.md hand-edited to remove US-3
when:  local self-check runs coverage against the manifest
then:  failure names US-3 and the UNVALIDATED_USER_STORY consequence
assert: self_check.valid == false
assert: "US-3" in self_check.issues[0].detail
```

### TC-1.3: Re-derivation after roadmap edit refreshes content + hash
**Data Strategy: REAL-DATA + PROPERTY** — edit-then-rederive on the real corpus; assert hash relationship, not exact values.
```
given: an emitted conops.md and its recorded sha256 prefix H1
when:  a roadmap story is edited and derivation re-runs producing hash H2
then:  conops.md reflects the edit and H2 != H1
assert: new story text in conops.md
assert: H2 != H1
```

### TC-1.4: ConOps byte-floor boundary [BVA]
**Data Strategy: SYNTHETIC** — exact byte counts require manufactured content; cannot land on 49/50 bytes with real derivation.
```
given: conops files of exactly 49 and exactly 50 bytes
when:  local self-check runs the gate's _require_readable_file mirror
then:  49 bytes fails (gate would reject VALIDATION_ARTIFACTS_INCOMPLETE);
       50 bytes passes the size check (inclusive boundary, per served code)
assert: self_check(conops_49B).valid == false
assert: size check passes for conops_50B
```
### TC-1.5: Digest part byte-budget boundary [BVA] (promoted — OQ-2 resolved)
**Data Strategy: SYNTHETIC** — exact byte counts manufactured.
```
given: assembled digest parts of exactly 3500 and 3501 UTF-8 bytes of content
when:  assemble-digest splits at row boundaries
then:  3500-byte part is emitted as one part; 3501 forces a split (or summary
       truncation per §6.5 — scenario and oracle never truncated)
assert: every emitted part file <= 3500 UTF-8 bytes
assert: a single row whose scenario+oracle+furniture > 3000 bytes was already
        rejected at check-rows (ROW_OVER_BUDGET — TC-G9 cross-ref)
```

## M2 — Row Drafting

### TC-2.1: Every story covered by ≥1 structurally-valid row (module scope)
**Data Strategy: REAL-DATA** — drafted against this session's conops.
```
given: conops.md with N story ids
when:  row drafting completes and check-rows runs
then:  every id appears in >=1 active row's conops_ref; every row passes the
       STRUCTURAL checks (id format, row_hash present, iff-form oracle,
       evidence_type + rationale)
assert: uncovered_stories(rows, conops) == []
assert: every row has non-empty conops_ref, scenario, oracle (iff-form), evidence_type
```
NOTE (R2 — module honesty): wrong-story SEMANTIC mismatch (scenario serving
US-5 under conops_ref US-3) is NOT detectable by check-rows (a deterministic
script cannot judge intent). That defect is caught by the human layers —
conductor drafting review and Jason's judgment — and spot-checked at dogfood
(TC-4.1's intent-level acceptance). Explicit deferral, not a coverage gap.

### TC-2.2: Relabeled verification caught locally — subset AND identical sets (error case)
**Data Strategy: SYNTHETIC** — requires constructing target-set relationships precisely.
```
given: a verification ledger with test_targets {a,b,c} and draft rows whose
       extracted targets are (case 1) {a,b} — strict subset; (case 2) {a,b,c}
       — identical (passes the GATE's strict-subset check; INV-11 closes it locally)
when:  local self-check runs the anti-relabeling mirror
then:  BOTH cases fail with the local twin of VALIDATION_IS_RELABELED_VERIFICATION
assert: self_check.valid == false in both cases
assert: issue.code == "VALIDATION_IS_RELABELED_VERIFICATION"
```

### TC-2.3: Oracle quality lint rejects test-restatement and vague oracles (error case)
**Data Strategy: SYNTHETIC** — bad oracles are manufactured counterexamples for the lint.
```
given: rows with oracles "all integration tests pass", "works as expected",
       and "Jason passes this row iff the digest renders" (no intent reference)
when:  oracle quality lint (layer-2 fallback) runs
then:  each row is rejected with guidance: iff-form + observable outcome +
       named US-n intent required
assert: lint.valid == false for all three; "observable" in lint.message
```

### TC-2.4: Missing evidence_type fails self-check (error case)
**Data Strategy: SYNTHETIC** — manufactured omission.
```
given: a row lacking evidence_type (or lacking its selection rationale)
when:  self-check runs
then:  failure names the row's conops_ref and the missing field
assert: self_check.valid == false
```

### TC-2.5: Scenario refresh rule — allowed path audited, disallowed path rejected
**Data Strategy: SYNTHETIC** — refresh scenarios (approved story change vs. post-failure rewrite) must be manufactured to hit both branches precisely.
```
given: a draft row R1 for US-4 and (a) a HUMAN-APPROVED story-change decision,
       (b) a prior fail judgment on R1 with no approved decision
when:  refresh is requested in each case
then:  (a) R1 moves to the superseded audit section with reason/approver/
       timestamp/replacement-id and replacement row R1' is drafted;
       (b) refresh is rejected citing the disallowed-reason list
assert: case-a audit entry complete and US-4 still covered by an active row
assert: case-b raises RefreshDisallowed naming "prior negative judgment"
```

## M3 — Gate & Close

### TC-3.1: Digest assembly — delta semantics, part files, faithful summaries
**Data Strategy: REAL-DATA** — assembled from this session's real rows; sent over the real bridge during dogfood.
```
given: a ledger with unjudged rows (result null), 1 judged-pass row,
       1 superseded row, all with executed evidence
when:  assemble-digest runs
then:  the digest contains ONLY result-null active rows (delta semantics —
       judged-pass and superseded rows absent); evidence summaries are
       TRACEABLE to evidence file content; each part <= 3500 UTF-8 bytes, written as
       a discrete digest-<id>-part-<i>.txt file with paths printed; the batch
       (digest_id, parts, row_ids) is recorded in the ledger
assert: only result-null rows present; pass + superseded rows absent
assert: each evidence summary maps to content in its evidence.md
assert: every part file <= 3500 UTF-8 bytes; batch recorded in digest_batches
```

### TC-3.2: Reply grammar round-trip — all forms, multi-line, duplicates, malformed
**Data Strategy: SYNTHETIC** — parser unit tests over the full grammar; exact strings need precise control.
```
given: replies "pass all", "pass r-US3-1", "pass rest",
       "fail r-US3-1: scenario shows wrong lane\nsecond line of reasoning",
       "na r-US7-1: deferred by decision D2",
       duplicate conflicting verdicts for r-US3-1 in one reply,
       a verdict naming unknown row id "r-US99-1",
       a verdict naming a superseded row id,
       bare-story target "fail US-3: nope", and malformed "US-3 nope"
when:  the reply parser runs against the digest-state file
then:  well-formed blocks mutate exactly the intended rows atomically;
       multi-line justification captured; every invalid case produces
       RepromptRequired with ZERO mutations
assert: parse("pass all") -> all unjudged ACTIVE rows result=pass
assert: parse("pass rest") after explicit verdicts -> remaining unjudged pass
assert: fail/na/pass row forms -> exactly one row mutated
assert: duplicates(conflicting) / unknown id / superseded id / bare US-n /
        malformed -> RepromptRequired, zero mutations
assert: reply with non-active digest_id -> rejected as stale, zero mutations
assert: verdict on a row whose row_hash changed after batch open -> rejected
assert: telegram reply with non-allowlisted sender-id -> DISCARDED with
        warning (no re-prompt, no mutation — INV-15)
assert: applied verdicts carry full provenance (digest_id, source, reply_ref,
        judged_at) in the ledger row's judgment block
```

### TC-2.6: Hash canonicalization is deterministic and scoped [pins constants]
**Data Strategy: SYNTHETIC** — canonicalization edge inputs (unicode forms, whitespace) must be manufactured.
```
given: a row whose scenario contains NFD-vs-NFC unicode and trailing spaces,
       and a second copy with evidence_rationale and test_targets edited
when:  row_hash is computed for both
then:  hash is identical across unicode normal forms after NFC; identical
       under rationale/test_targets edits (excluded fields); CHANGES when
       scenario, oracle, conops_ref, or evidence_type change; FULL sha256
       stored (64 hex); 12-hex prefix emitted only at artifact boundary
assert: hash(NFD variant) == hash(NFC variant)
assert: hash(rationale-edited) == hash(original)
assert: hash(oracle-edited) != hash(original); len == 64 in ledger
assert: emitted artifact prefix len == 12; self-check rejects prefixes < 12
```

### TC-3.3: Self-check ≡ gate, with single-defect causality
**Data Strategy: SYNTHETIC** — one manufactured artifact per reject class.
```
given: a known-good system_validation.json and single-defect variants:
       bad kind, stale conops_hash, empty rows, missing row field, bad result
       enum, fail row present, relabeled targets (subset), relabeled targets
       (identical — local-only reject)
when:  local self-check evaluates each
then:  good passes; each variant fails with the code the gate would emit
       (identical-set variant fails locally by design); AND repairing ONLY the
       named defect makes that variant pass — proving the defect named is the
       defect detected
assert: verdict parity with fizzy-validation-contract.md per class
assert: for each variant: self_check(repair(variant)).valid == true
```

### TC-3.4: Fail row spawns remediation path
**Data Strategy: REAL-DATA** — exercised on the dogfood board with a deliberately failed judgment.
```
given: a judged row set containing one result=fail
when:  the close step runs
then:  no MCP mark call is made; remediation task cards are created referencing
       the failing conops_ref; session cannot advance to Completed
assert: mark_call_attempted == false
assert: remediation card exists naming the failed US id
```

### TC-3.5: N/A without justification rejected (error case)
**Data Strategy: SYNTHETIC** — manufactured reply.
```
given: reply "na r-US5-1:" (empty justification)
when:  reply parser runs
then:  rejected with re-prompt requiring justification text
assert: row r-US5-1 unchanged; RepromptRequired raised
```

### TC-3.6: N/A on a story's sole row blocks close (coverage-gate constraint)
**Data Strategy: SYNTHETIC** — sole-row N/A must be manufactured.
```
given: US-9 covered by exactly one active row, judged "na r-US9-1: deferred by D4"
when:  the close step runs coverage pre-check
then:  close is blocked BEFORE any MCP call with guidance: either draft a
       replacement row for US-9 or remove US-9 from ConOps (edit + re-hash)
assert: mark_call_attempted == false
assert: blocker names US-9 and offers both documented resolutions
```

### TC-3.7: Scenario execution produces type-matched evidence before digest
**Data Strategy: REAL-DATA** — executed on this session's own scenarios during dogfood; the error branches are cheap synthetic twins.
```
given: judged-ready draft rows after implementation completes
when:  the Phase 8 close step runs
then:  each row's scenario is EXECUTED per its evidence_type and a per-row
       evidence artifact exists BEFORE digest assembly; a row with missing
       evidence OR evidence not matching its declared type (e.g. narrative
       file for an agent-walkthrough-transcript row) blocks digest assembly
       with a named row
assert: every digest row references a non-empty, type-matched evidence artifact
assert: digest_assembly(rows_with_missing_evidence) raises EvidenceMissing
assert: digest_assembly(rows_with_type_mismatch) raises EvidenceTypeMismatch
assert: evidence with stale embedded row_hash (row edited after capture) is
        rejected the same as missing evidence (INV-12 hash chain)
```

### TC-3.8: Remediation delta cycle — fail reset with history, pass immutability
**Data Strategy: SYNTHETIC** — the fail→reset→re-judge cycle and the protected-pass case need manufactured judgment states.
```
given: a ledger with row A judged-fail (remediation card resolved), row B
       judged-pass, row C judged-fail (remediation card NOT resolved)
when:  reset-failed --row A --remediation-ref <cardA> runs (succeeds), then
       reset-failed --row C --remediation-ref <cardC> runs (refused), then
       assemble-digest runs
then:  A's fail moves to judgment_history (append-only) and A re-enters the
       delta digest; C's reset is REFUSED (unresolved remediation); B is
       untouched and absent from the new digest (INV-13); a second
       assemble-digest while the new batch is open is REFUSED (one open
       batch); cancel-batch returns its rows to the delta pool with audit
assert: A.judgment_history[-1].result == "fail"; A.result == null; A in new digest
assert: reset(C) raises RemediationUnresolved
assert: B.result == "pass" unchanged; B not in new digest
assert: emit-system-validation refuses while any active row is unjudged/failed
```

### TC-3.9: Lock and failure semantics — busy, corrupt, crash-safe
**Data Strategy: SYNTHETIC** — held locks and corrupt ledgers must be manufactured (same class as the retired task-store lock tests).
```
given: (a) a held validation-rows.json.lock, (b) a ledger of invalid JSON,
       (c) a simulated crash (os.replace raises) mid-mutation
when:  parse-reply / assemble-digest run in each case
then:  (a) exit 3 LEDGER_BUSY after 10s timeout; (b) exit 3 LEDGER_CORRUPT,
       no auto-repair; (c) original ledger bytes intact (atomic tmp+rename),
       no .tmp litter
assert: exit codes 3 with named errors; ledger unchanged in (c)
```

### TC-3.10: Close-step idempotent re-entry
**Data Strategy: SYNTHETIC** — partial-failure states (post-emit crash, already-complete card) must be staged.
```
given: (a) all rows judged, no system_validation.json yet;
       (b) self-check-clean system_validation.json exists, MCP call crashed;
       (c) card metadata already shows system_validation_complete true
when:  the Phase 8 close step re-enters in each state
then:  (a) assemble-digest exits NOTHING_TO_DIGEST -> straight to emission;
       (b) skip to MCP call, no re-judging, no new digest;
       (c) MCP call skipped entirely -> Finalization advance
assert: no row judgment mutated in any re-entry; no duplicate digest batches
assert: (c) issues zero mark_system_validation_complete calls
```

## M4 — Dogfood

### TC-4.1: This session V-closes end-to-end — gate acceptance AND intent-level acceptance
**Data Strategy: REAL-DATA** — the entire point: real session, real card 5604, real judgments, real MCP call.
```
given: this session at end of Phase 8 with implemented process + artifacts
when:  the documented close runs (execute scenarios -> evidence -> digest ->
       Jason judges -> system_validation.json -> mark_system_validation_complete
       -> Finalization advance)
then:  the real gate accepts on first call (self-check parity held); the
       coverage gate passes with all US ids covered; AND Jason's judgment
       includes intent-level acceptance of the process itself — bootstrap
       usable without fizzy source, digest sufficient to judge from mobile,
       reply/re-prompt unambiguous, remediation guidance actionable
assert: card 5604 meta.system_validation_complete == true
assert: session advance to Completed succeeds
assert: dogfood rows covering US-0/US-6/US-7/US-9 carry Jason's pass with
        intent-level oracles (not "the gate accepted")
```

<!-- P4_INVARIANT_TESTS_START -->
## Invariant Tests (Phase 4)

### TC-INV-A1: Ledger is sole SoT; gate artifact is pure projection (stage: acceptance) [SYNTHETIC]
given: a ledger with judged rows (pass/na with provenance) and a hand-built system_validation.json that disagrees with the ledger
when: emit-system-validation runs against the ledger; self-check runs against the hand-built file
then: emitted projection matches ledger judged rows exactly (ids, results, ordering); hand-built file with a result the ledger lacks fails (provenance/coverage checks)
assert (negative): editing the projection file does NOT change any subsequent module read — no subcommand reads system_validation.json as state

### TC-INV-A2: Mutation ownership + lock discipline (stage: acceptance) [SYNTHETIC]
given: a valid ledger fixture
when: every read-only subcommand (derive-conops, check-rows, self-check, emit-system-validation) runs against it
then: ledger file bytes are byte-identical after each run
assert (negative): parse-reply/assemble-digest/cancel-batch invoked while validation-rows.json.lock is held by another process exit 3 LEDGER_BUSY within ~10s and leave the ledger unchanged

### TC-INV-A3: Atomic reply application; structured exit codes (stage: acceptance) [SYNTHETIC]
given: a digested batch and a reply containing one valid verdict block and one invalid block (unknown row id)
when: parse-reply processes the reply
then: exit 2 with RepromptRequired quoting the offending text; ledger bytes unchanged (zero mutations — TC-3.2 overlap)
assert (positive): the same reply with the invalid block removed applies BOTH verdicts atomically with full provenance
assert (negative): corrupt ledger JSON → exit 3 LEDGER_CORRUPT, file untouched, no auto-repair

### TC-INV-A4: Sender allowlist trust boundary (stage: acceptance) [SYNTHETIC]
given: a digested batch and a grammatically valid "pass all" reply
when: parse-reply runs with --source telegram --update-file <raw listener payload whose sender is non-allowlisted> (v5: module extracts sender itself — conductor-typed --sender-id is ignored for telegram; see TC-G3)
then: reply DISCARDED with structured code + hashed-sender security event; ledger judgments unchanged; no re-prompt
assert (positive): identical payload with allowlisted sender applies normally
assert (counterfactual): module source contains no hardcoded chat/sender id literal (allowlist resolved from telegram registry config at runtime)

### TC-INV-A5: self-check is a strictly-stricter gate mirror (stage: acceptance) [REAL-DATA + PROPERTY]
given: per gate reject class in fizzy-validation-contract.md, a fixture artifact the gate would reject (wrong kind, stale conops_hash, empty rows, missing field, bad result enum, fail row, strict-subset test_targets, uncovered US id)
when: self-check runs on each fixture
then: each is rejected with the mirrored code (verdict parity, TC-3.3)
assert (stricter): identical-set test_targets fixture passes the gate's strict-subset rule but is REJECTED locally (INV-11 extension)
assert (positive): a fully clean artifact passes both self-check and (at dogfood) the real gate first-call

### TC-INV-A6: Single open batch; staleness rejection; idempotent close (stage: acceptance) [SYNTHETIC]
given: a ledger with an open digest batch
when: assemble-digest is invoked again
then: refused while the batch is open
assert: reply with non-active digest-id rejected as stale; reply targeting a row whose row_hash changed after batch open rejected
assert (idempotency): running the full close sequence twice (digest → judge → emit → self-check) yields NOTHING_TO_DIGEST on re-entry and an identical system_validation.json; no row is re-judged
assert (negative): cancel-batch without --reason refused; with reason, rows return to delta pool and the cancellation is audit-logged

### TC-INV-A7: Provenance required; history append-only (stage: acceptance) [SYNTHETIC]
given: a ledger where one row has result "pass" but judgment: null
when: emit-system-validation runs
then: refusal naming the provenance-less row (INV-1 enforceable form)
assert: reset-failed (standalone subcommand as of v5) moves the prior fail judgment into judgment_history (original entry intact, byte-compared) and requires a paired --remediation-ref
assert (negative): a superseded entry missing approval_ref is rejected by check-rows
Schema refs: validation-rows.json ledger (§6.2), system_validation.json (§6.4), fizzy-validation-contract.md
<!-- P4_INVARIANT_TESTS_END -->

<!-- GAUNTLET_TESTS_BEGIN source: gauntlet-2026-06-11 (concern report gauntlet-concerns-2026-06-11.json) -->
## Gauntlet Tests (post-gauntlet v5 additions)

### TC-G1: Bulk verdicts require delivered batch (stage: acceptance) [SYNTHETIC]
Source: RC-2 (ARCH/FLOW/PARA/BURN convergent)
given: a batch in status "assembled" with 2 of 3 parts recorded sent
when: parse-reply receives "pass all" (or any natural alias)
then: rejected (INV-16); explicit per-row verdicts for delivered rows still apply
assert (positive): after record-send marks part 3 sent (batch status "sent"), the same bulk verdict applies to all snapshot rows
assert: record-send flips batch status only when ALL parts are sent

### TC-G2: Natural-language bulk-pass aliases (stage: acceptance) [SYNTHETIC]
Source: SEC-6 (Jason ruling — no reply passwords)
given: a sent batch with unjudged rows
when: parse-reply receives "those all look good" / "all good" / "LGTM" (case-insensitive)
then: applied exactly as "pass all"
assert (negative): a phrase NOT on the fixed alias list ("ship it") → re-prompt, zero mutations
assert (deterministic): alias matching is string comparison against the module constant — test pins the list

### TC-G3: Sender identity extracted from raw listener payload (stage: acceptance) [SYNTHETIC]
Source: SEC-1 (5-adversary convergent; Jason-ruled right-sizing)
given: a raw wake-listener update file whose payload sender is non-allowlisted, with reply text "pass all"
when: parse-reply --source telegram --update-file <path> runs (no --sender-id flag honored)
then: reply discarded, exit 2 SENDER_NOT_ALLOWLISTED, security event appended with HASHED sender id, zero mutations
assert (positive): same payload with allowlisted sender applies; judgment provenance reply_ref = payload message id
assert (config): missing/malformed registry allowlist → ALLOWLIST_CONFIG_INVALID, telegram parsing blocked
assert (counterfactual): a conductor-supplied --sender-id flag contradicting the payload is ignored for telegram source

### TC-G4: Per-story evidence binding (stage: acceptance) [SYNTHETIC]
Source: FM-3 (Jason-approved per-story hashes)
given: a ledger with passing evidence for US-3 and US-7 rows, all hash-bound
when: the US-7 section of conops.md is edited and re-derived (manifest-first)
then: US-7 rows' evidence is invalidated (story_hash mismatch); US-3 rows' evidence remains VALID
assert: emit-system-validation refusal names only US-7 rows; close does not force global re-execution

### TC-G5: Supersession legal from any state, transactional replacement (stage: acceptance) [SYNTHETIC]
Source: CB-1 (S7/INV-13 contradiction resolved)
given: a judged-pass row whose story was legitimately re-scoped
when: supersede-row runs with --reason "approved story change" --approval-ref telegram:<chat>:<id> --replacement-file new-row.json
then: full row snapshot moves to superseded[]; replacement row installed in the SAME invocation; coverage never gaps (INV-7 holds at exit)
assert (negative): missing approval_ref → REFRESH_DISALLOWED; reason outside enum → REFRESH_DISALLOWED
assert: superseded row's id rejected by later parse-reply with a replacement-row notice

### TC-G6: Reply idempotency and edited messages (stage: acceptance) [SYNTHETIC]
Source: RC-4
given: a reply applied from update payload with reply_ref R
when: the same payload is fed to parse-reply again (duplicate delivery)
then: acknowledged, zero new mutations (processed_reply_refs)
assert: an edited-message payload with the same message id is ignored (first capture wins)

### TC-G7: Terminal-source provenance and abuse surface (stage: acceptance) [SYNTHETIC]
Source: SEC-3
given: parse-reply --source terminal without a transcript-style --reply-ref
then: rejected (terminal judgments must cite the AskUserQuestion transcript)
assert (documented boundary): test asserts the weaker-trust framing exists — terminal judgments record source "terminal", never "telegram"

### TC-G8: Grammar tightenings (stage: acceptance) [SYNTHETIC]
Source: CB-9, FM-10
given: a sent batch
when/then matrix:
- "fail r-US3-1" (no justification) → re-prompt (fail requires reason, like na)
- "fail rest" / "na all" → invalid, zero mutations
- "pass r-US3-1" twice in one reply → invalid (all duplicates rejected)
- "pas r-US3-1" on a continuation line → parse error, NOT swallowed as justification
- explicit "fail r-US3-1: x" + "pass rest" in either textual order → fail applies first, rest passes remainder
- "PASS ALL" → applies (case-insensitive keywords); "pass R-us3-1" → invalid (row ids exact-case)

### TC-G9: Digest hygiene lints (stage: acceptance) [SYNTHETIC]
Source: SEC-4, FM-9
given: a row whose evidence_summary contains a token matching the secret deny-pattern set
when: assemble-digest runs
then: assembly BLOCKED naming the offending span
assert: a drafted row with scenario+oracle > 3000 UTF-8 bytes → check-rows ROW_OVER_BUDGET (drafting error, never delivery failure)
assert: digest part files land in validation-digests/ and their sha256s are recorded in the batch

### TC-G10: Close algorithm re-entry routing (stage: acceptance) [SYNTHETIC]
Source: CB-5
given: a ledger with one judged-fail row and all others judged pass
when: the close algorithm re-enters (NOTHING_TO_DIGEST condition)
then: routed to remediation (step 6), NEVER to emission
assert: re-entry with an existing clean system_validation.json still re-runs self-check before the MCP call (INV-5); artifact sha256 verified unchanged at call time (TOCTOU)

### TC-G11: normalize-rows is the only hash producer (stage: acceptance) [SYNTHETIC]
Source: CB-7
given: conductor-drafted rows with NO row_hash fields
when: normalize-rows runs
then: canonical hashes stamped (full sha256; NFC; pinned canonicalization)
assert: check-rows on hand-written (wrong) hashes → structured issue; conductor workflow never computes hex (doc assertion: Phase 7 doc shows normalize-rows in the drafting sequence)

### TC-G12: Status command (stage: acceptance) [SYNTHETIC]
Source: FM-5
given: a ledger mid-close (sent batch, 2 unjudged rows, 1 failed row)
when: status runs
then: read-only report names active batch + age, per-part send state, unjudged row ids, the failed row, coverage state, and the next close-algorithm step
assert: ledger bytes unchanged (read-only contract)

### TC-G13: derive-conops lints — stray ids, duplicates, overwrite safety, story hashes (stage: acceptance) [SYNTHETIC]
Source: CB-11, DD-7, FM-3
given: a manifest whose story text mentions "replaces US-99" (no US-99 story exists)
when: derive-conops runs
then: exit 2 naming the stray US-99 token (phantom coverage obligation prevented)
assert: duplicate story ids in the manifest -> exit 2
assert: re-derivation over an existing conops.md referenced by a ledger -> refused without the explicit override flag; with it, prior and new hashes both reported
assert: output includes the story_hashes map; editing one story section changes only that story's hash (TC-G4 dependency)
<!-- GAUNTLET_TESTS_END -->
