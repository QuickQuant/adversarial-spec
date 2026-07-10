# Test Pseudocode — Post-Fable Hardening, Skill Slice (G1+G2+G5)

> v1 — 2026-07-08. Canonical source of truth for tests; roadmap links here.
> One active `spine: true` per user story (TC-X.0 convention). Failure/branch tests
> cite `spine_of` + `spine_step_ref`. Maturity: all `nl→acceptance` candidates; none concrete yet.
> Data-strategy vocabulary applied to this project's "real data" = real session artifacts,
> real transcripts, real registries from past sessions (card-5715, gateway study, liveness-gate wave).

---

## US-0: Toolchain bootstrap (M0)

### TC-0.0: Bootstrap on healthy checkout [spine: US-0]
**Data Strategy: REAL-DATA** — runs on the actual repo checkout; no manufactured state.
spine_steps: S1 invoke bootstrap command, S2 toolchain probes run, S3 ready verdict emitted
```
given: fresh clone of skill repo at HEAD with deps installed
when:  the documented bootstrap command runs
then:  gate-check CLI, competence harness, reconciliation CLI each probe OK
assert: exit 0; report lists each tool with version/path; wall time < 5 min
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

---

## US-1: Gate inventory complete + classified (M1)

### TC-1.0: Inventory covers phases 01–09, no unclassified gate [spine: US-1]
**Data Strategy: REAL-DATA** — the real phase-doc corpus is the input.
spine_steps: S1 extract MUST/gate statements, S2 classify each (a/b/c), S3 emit inventory artifact
```
given: the current phases/01..09 corpus
when:  the gate-inventory extraction runs
then:  every MUST/[GATE] statement appears in the inventory artifact
assert: each row has classification ∈ {code-enforced, mechanizable, judgment-rubric}
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
**Data Strategy: SYNTHETIC** — deliberately construct a violating session state per gate under test.
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
given: an inventory row classified judgment-rubric with no fixture file
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
then:  every spine pointer resolves; every reference unit is pointed to by ≥1 spine
assert: zero dangling pointers; zero orphaned reference units; exit 0
```

### TC-4.2: Deleted-not-moved content is caught
**Data Strategy: SYNTHETIC** — remove a reference unit from a scratch corpus copy without a decision-log entry.
spine_of: TC-4.0, spine_step_ref: S3
```
given: corpus copy missing one reference unit that a spine still points to
when:  pointer-closure check runs
then:  the dangling pointer is reported with source spine unit + missing target
assert: nonzero exit
```

---

## US-5: Worker context stays lean (M2)

### TC-5.0: Phase execution touches only step-named units [spine: US-5]
**Data Strategy: REAL-DATA** — audit a real post-restructure session transcript.
spine_steps: S1 run a phase with the new corpus, S2 extract file-reads from transcript, S3 compare against step's named units
```
given: a completed phase execution transcript after M2 lands
when:  the transcript audit (competence-harness family) extracts doc reads
then:  every doc read is a unit named by the executed steps
assert: zero monolith reads; zero unrelated-phase unit reads
```

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

## US-6: Competence harness measures candidate conductors (M3)

### TC-6.0: Harness scores candidate across all fixtures [spine: US-6]
**Data Strategy: REAL-DATA + PROPERTY** — fixtures derived from real session states; assert report properties, not exact scores.
spine_steps: S1 load fixture set, S2 run candidate model per fixture, S3 emit scored report
```
given: the full fixture set and a named candidate model (e.g. sonnet)
when:  the harness runs
then:  a scored report is emitted
assert: every fixture has a verdict; report includes per-phase breakdown; score ∈ [0,1]
assert: fixture coverage includes ≥1 entry, ≥1 gate, ≥1 failure-recovery decision per phase
```

### TC-6.2: Known-wrong next-action fixture scores fail
**Data Strategy: SYNTHETIC** — fixture with a deliberately wrong expected-action answer given by a stub model.
spine_of: TC-6.0, spine_step_ref: S2
```
given: a stub candidate that always answers "run debate.py critique directly"
when:  harness runs the pipeline-card-fence fixture
then:  that fixture scores fail
assert: fail verdict with the violated rule named (falsifies judge leniency)
```

---

## US-7: Verification cards derived from TMR registry (M4)

### TC-7.0: Sub-concrete critical-seam TMRs yield exactly matching card set [spine: US-7]
**Data Strategy: REAL-DATA** — use the liveness-gate session's real tmr-registry.json as base.
spine_steps: S1 read registry, S2 select TMRs (maturity<concrete OR missing live_or_induced on critical seam), S3 emit card set
```
given: a real registry with exactly 3 qualifying critical-seam TMRs
when:  verification-card derivation runs
then:  exactly 3 cards emitted
assert: each card carries seam, tmr_uid, required evidence class; derivation is code (no LLM call in path)
```

### TC-7.2: All-concrete registry yields empty set + recorded no-op
**Data Strategy: SYNTHETIC** — promote all entries of a registry copy to concrete/live.
spine_of: TC-7.0, spine_step_ref: S2
```
given: registry where every critical-seam TMR is concrete with live evidence
when:  derivation runs
then:  zero cards; an explicit no-op record written (not silent absence)
assert: no-op record names registry hash + selection criteria
```

---

## US-8: Promotion gate blocks declared-only evidence (M5)

### TC-8.0: Declared-only critical-seam TMR blocks finalize [spine: US-8]
**Data Strategy: SYNTHETIC** — construct a session whose registry holds one declared-only critical TMR.
spine_steps: S1 attempt finalize advance, S2 gate derives verdict from run_evidence, S3 advance rejected naming TMR
```
given: session at finalize with one critical-seam TMR whose run_evidence is declared-only
when:  pipeline advance toward complete is attempted
then:  the gate blocks
assert: rejection names the tmr_uid and required evidence class; owner-written prose does NOT satisfy it
```

### TC-8.2: Run-evidence landing unblocks the same session
**Data Strategy: SYNTHETIC** — same constructed session, evidence appended.
spine_of: TC-8.0, spine_step_ref: S2
```
given: the TC-8.0 session after real run evidence recorded on the TMR
when:  advance is retried
then:  gate passes
assert: advance succeeds with gate verdict logged (proves gate reads registry, not attestation)
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

### TC-9.2: Missing walkthrough evidence blocks close
**Data Strategy: SYNTHETIC** — attempt close on a constructed session without the artifact.
spine_of: TC-9.0, spine_step_ref: S4
```
given: session at close, no walkthrough evidence, no operator waiver
when:  close is attempted
then:  blocked with actionable message (script path, waiver mechanism)
assert: explicit operator waiver (named authority) is the only bypass, and it is logged
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
when:  session B bootstrap validates it
then:  integrity failure reported, artifact quarantined, bootstrap continues degraded
assert: degraded state named in bootstrap report (not silent fallback)
```

---

## US-11: Frozen sections excluded from re-critique (M7)

### TC-11.0: Frozen section absent from round N+1 dispatch [spine: US-11]
**Data Strategy: SYNTHETIC** — constructed spec with sections frozen at known round boundaries.
spine_steps: S1 mark section frozen in node registry, S2 assemble round N+1 dispatch payload, S3 dispatch excludes frozen content
```
given: spec with section X frozen after round N convergence
when:  round N+1 payload is assembled
then:  section X content absent (a one-line frozen stub may remain)
assert: payload diff proves exclusion; token count drops accordingly
```

### TC-11.2: New concern naming frozen section reopens exactly it
**Data Strategy: SYNTHETIC** — inject a critique naming section X.
spine_of: TC-11.0, spine_step_ref: S1
```
given: frozen section X and a new concern that names X
when:  the reopen check runs
then:  X unfreezes; registry logs the unfreeze event with the naming concern id
assert: only X reopens (no blanket thaw); event has concern id + round
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

### TC-12.2: Registry/spec version mismatch detected on resume
**Data Strategy: SYNTHETIC** — bump spec version without registry update.
spine_of: TC-12.0, spine_step_ref: S3
```
given: spec at v(N+1), registry stamped v(N)
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

---

## US-14: False-convergence guard (M8)

### TC-14.0: Quorum-AGREE with dirty derived diff rejected [spine: US-14]
**Data Strategy: SYNTHETIC** — constructed round result: all opponents AGREE, reconciliation dirty.
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

---

## US-15: Authorized waiver mechanism (M1, R1 revision)

### TC-15.0: Waived gate proceeds with durable record [spine: US-15]
**Data Strategy: SYNTHETIC** — waivers are exceptional by design; construct the blocked state.
spine_steps: S1 gate blocks, S2 Jason records waiver (authority+justification+gate id), S3 action proceeds, S4 waiver surfaces in close report
```
given: a session blocked at a mechanized gate with a valid exceptional reason
when:  Jason records a waiver with justification
then:  the blocked action proceeds; waiver record persists with gate id + affected artifacts
assert: close report lists the waiver; audit trail readable post-session
```

### TC-15.2: Bypass attempt without waiver blocked and logged
**Data Strategy: SYNTHETIC** — simulate a conductor attempting the blocked action with no waiver.
spine_of: TC-15.0, spine_step_ref: S2
```
given: same blocked state, no waiver recorded
when:  the conductor retries the blocked action
then:  still blocked; the attempt itself is logged
assert: no conductor-side action can substitute for the waiver record
```

---

## US-16: G3 contract-boundary guardrail (M4, R1 revision)

### TC-16.0: Contract-boundary artifact complete, zero fizzy-repo scope leaks [spine: US-16]
**Data Strategy: REAL-DATA** — this slice's real execution plan and contract artifact.
spine_steps: S1 enumerate fizzy deltas referenced by M4/M5, S2 emit contract-boundary artifact, S3 lint execution plan file scopes
```
given: the slice's execution plan and the contract-boundary artifact
when:  the boundary lint runs
then:  every fizzy-side dependency named with a G3 tracking pointer; zero tasks scope fizzy-repo files
assert: lint exit 0; artifact lists lane/gate/schema deltas with version stamps
```

### TC-16.2: Execution-plan task scoping a fizzy path is flagged
**Data Strategy: SYNTHETIC** — inject a fizzy-repo path into a scratch plan copy.
spine_of: TC-16.0, spine_step_ref: S3
```
given: plan copy with one task whose file scope includes the fizzy repo
when:  boundary lint runs
then:  the task is flagged with its offending path
assert: nonzero exit naming task_id
```
