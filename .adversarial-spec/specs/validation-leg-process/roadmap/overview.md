# Roadmap: Validation-Leg Production Process

> Session `adv-spec-202606110339-validation-leg-process` (card 5604, system
> altitude). Source of truth: `manifest.json`. Tests: `../tests-pseudo.md`.
> Fixed downstream contract: `../fizzy-validation-contract.md`.

### Goals

- G1: A v5 system-altitude session can V-close — every precondition of fizzy's
  `mark_system_validation_complete` and the Finalization→Completed coverage
  gate is satisfiable by documented, repeatable skill process.
- G2: Validation judges INTENT (ConOps-anchored scenarios), not re-run tests —
  passes the anti-relabeling check by construction, not by luck.
- G3: Jason is the sole validation oracle; the process keeps his cost to one
  batched Telegram digest per session (terminal fallback when present).
- G4: ConOps stays fresh — derived late (Phase 7) from the post-debate roadmap
  and hash-bound at mark time, so validation never binds stale intent.
- G5: Scenario refresh is possible only through an auditable anti-hindsight
  rule (added R1, codex).

### Non-Goals

- NG1: No fizzy-side changes. The gate contract is fixed; we conform to it.
- NG2: No validation obligations for subsystem/component altitudes (the v5
  gate is system-only) and no retrofit of v4/grandfathered sessions.
- NG3: No automated pass/fail judgment — `result` values are human judgments,
  never computed by an agent or test runner.
- NG4: No new MCP server, board lane, or fizzy tool; skill docs + one local
  emission/self-check module only.
- NG5: No validation row may use verification-test success ("tests pass",
  "gate passed", "code merged") as its oracle (added R1, codex).

---

### Milestone 0: Getting Started (Bootstrap)

**User Stories:**
- US-0: As a conductor agent entering Phase 7 of a system-altitude session, I
  want a single documented entry point (which doc to read, which artifacts
  exist, in what order) so that I can run the validation leg end-to-end
  without reading fizzy source code.

**Success Criteria (Natural Language):**
- [ ] A fresh conductor can produce a valid `conops.md` + draft rows from docs
      alone in under 30 minutes.
- [ ] The docs state every fizzy reject code and the documented response to it.
- [ ] A malformed artifact is caught by the local self-check BEFORE any MCP
      call (clear error message naming the failing field).

**Test Cases (expand during implementation):**
- TC-0.1: Cold-read bootstrap — fresh agent follows docs to valid artifacts (stage: nl)
- TC-0.2: Docs cover all six gate error codes with responses (stage: nl)

**Dependencies:** None

### Milestone 1: ConOps Derivation & Emission

**User Stories:**
- US-1: As a conductor at Phase 7, I want to derive `roadmap/conops.md` from
  the roadmap manifest (user stories + operational narrative) so that
  validation binds to refreshed, post-debate intent.
- US-2: As the validator, I want the ConOps to read as operational intent
  (AS A / I WANT / SO THAT plus a narrative of how the system is used), not as
  a test inventory, so that my pass/fail judgments anchor on what was wanted.

**Success Criteria (Natural Language):**
- [ ] Emitted conops.md contains every `US-n` id present in the roadmap
      manifest (the close gate regexes these; a dropped id = UNVALIDATED_USER_STORY).
- [ ] File satisfies gate constraints: ≥50 bytes, `.md`, readable.
- [ ] Emission records the sha256 prefix that `system_validation.json` must declare.
- [ ] Re-running emission after a roadmap edit refreshes both content and hash
      (drift defense G4).

**Test Cases:**
- TC-1.1: Derivation includes all US ids from manifest (stage: nl)
- TC-1.2: Dropped-story detection — manifest story missing from conops fails self-check (stage: nl)
- TC-1.3: Hash refresh on re-derivation after edit (stage: nl)

**Dependencies:** M0

### Milestone 2: Validation-Row Drafting (Phase 7)

**User Stories:**
- US-3: As a conductor at Phase 7 (pre-implementation), I want to draft ≥1
  validation row per user story — `conops_ref`, `scenario` (end-to-end, user
  terms), `oracle`, and an `evidence_type` — so that the gate's row schema is
  satisfiable and scenarios are written before hindsight can shape them.
- US-4: As the validator, I want every `oracle` to state how I judge pass/fail
  FROM INTENT (an observable user-level outcome, never "tests pass") so that
  rows cannot degrade into checkbox prose (validation-theater defense).
- US-5: As a conductor, I want an evidence-type taxonomy
  (agent-walkthrough-transcript / artifact-demo / narrative) with a per-type
  minimum bar and a required selection rationale per row, so that evidence
  matches what each scenario is actually of without requiring synchronous
  human participation (R1b: renamed from "live-walkthrough" — the agent walks,
  Jason reviews the transcript async).
- US-12: As a conductor, I want a controlled scenario-refresh rule — refresh
  only BEFORE Jason's final judgment or after a **human-approved**
  remediation/scope decision (an agent may never approve its own scope
  reduction — R1b gemini); allowed reasons: approved story change, removed story, replaced
  workflow serving the same intent, duplicate coverage; disallowed reasons:
  implementation failed, evidence missing, scenario inconvenient, prior
  negative judgment; superseded rows kept in an audit section with
  reason/approver/timestamp/replacement-id — so that legitimately obsolete
  Phase 7 rows are replaceable without hindsight rewriting (T1 resolution).

**Success Criteria (Natural Language):**
- [ ] Every US-n in conops.md is covered by ≥1 draft row.
- [ ] No row's test targets are a subset of the verification ledger's targets
      (anti-relabeling, checked locally before the gate does).
- [ ] Every row passes the oracle quality bar: names an observable outcome and
      the intent it serves; "tests pass"/"code merged" auto-rejected.
- [ ] Every row carries an evidence_type + one-line rationale.

**Test Cases:**
- TC-2.1: Row coverage — all stories get rows (stage: nl)
- TC-2.2: Relabeled-verification rejection caught locally (stage: nl)
- TC-2.3: Oracle quality lint rejects test-restatement oracles (stage: nl)
- TC-2.4: Evidence-type required — row without it fails self-check (stage: nl)

**Dependencies:** M1

### Milestone 3: Phase 8 Gate & Close

**User Stories:**
- US-13: As a conductor at Phase 8 (post-implementation), I want to EXECUTE
  each drafted scenario and compile captured evidence into a per-row evidence
  artifact BEFORE digest assembly, so that the digest is backed by real
  execution data, never mock assumptions (R1b gemini — closes the M2→M3 gap:
  drafting and digesting had no execution step between them).
- US-6: As the validator, I want one batched Telegram digest — every row with
  its scenario, oracle, and assembled evidence summary — so that I can judge
  the whole session from mobile in one interaction.
- US-7: As a conductor, I want a defined digest reply grammar
  (`pass all` | `fail US-n: <reason>` | `na <row-id>: <justification>` |
  mixed lines) parsed deterministically, so that judgments can't be
  misapplied. N/A is accepted only from Jason, requires justification, and is
  **row-level only**: the coverage gate requires every active ConOps story to
  have ≥1 PASSING row, so N/A on a story's sole row blocks close — removing a
  story is a ConOps edit + re-hash, never an N/A (R1 codex contract catch).
- US-8: As a conductor, I want to write `system_validation.json` (kind,
  conops_hash, judged rows) and call `mark_system_validation_complete`,
  with every gate error code mapped to a documented response, so that the
  close is mechanical once judgments exist.
- US-9: As a conductor, I want `fail` results to spawn a remediation loop
  (remediation task cards → fix → re-exercise scenario → regenerate rows →
  re-gate) so that a failed validation blocks completion until resolved.
- US-11: As a conductor, I want a local self-check that mirrors the gate's
  reject codes (kind, hash prefix-match, row fields, result enum, relabeling,
  US coverage) so that artifacts fail fast before any MCP call — the same
  dry-run/load symmetry the v3 plan emitter has.

**Success Criteria (Natural Language):**
- [ ] Digest fits one Telegram message (or documented multi-part rule) and
      contains everything needed to judge without opening a laptop.
- [ ] Reply grammar round-trips: every grammar form parses to the intended
      row mutations; malformed replies produce a re-prompt, never a guess.
- [ ] A clean artifact passes the real gate on first MCP call (self-check ≡ gate).
- [ ] A failed row provably blocks completion and produces remediation cards.

**Test Cases:**
- TC-3.1: Digest assembly from judged rows (stage: nl)
- TC-3.2: Reply grammar parse — all forms + malformed input (stage: nl)
- TC-3.3: Self-check mirrors gate verdict on valid + each invalid artifact class (stage: nl)
- TC-3.4: Fail row → remediation card path (stage: nl)
- TC-3.5: N/A without justification rejected (stage: nl)

**Dependencies:** M1, M2

### Milestone 4: Dogfood Close-Out

**User Stories:**
- US-10: As the project owner, I want THIS session (card 5604) to V-close
  through the new process — its own ConOps, its own rows, my real judgments,
  a real `mark_system_validation_complete` call — so that the process is
  proven on itself before any other session depends on it.

**Success Criteria (Natural Language):**
- [ ] Card 5604 reaches `system_validation_complete: true` via the documented
      process, no overrides, no patch_state bypass.
- [ ] Session advances Finalization→Completed with the coverage gate passing.
- [ ] A retro note records any contract surprises for the fizzy handoff.

**Test Cases:**
- TC-4.1: End-to-end dogfood — this session's own gate passes (stage: nl)

**Dependencies:** M0–M3
