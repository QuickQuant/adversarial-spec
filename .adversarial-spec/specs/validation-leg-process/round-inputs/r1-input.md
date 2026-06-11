# Spec: Validation-Leg Production Process (v1)

> Session `adv-spec-202606110339-validation-leg-process` | card 5604 | altitude: system
> Depth: technical | Roadmap: `roadmap/manifest.json` (14 stories US-0..US-13, confirmed)
> Fixed downstream contract: `fizzy-validation-contract.md` (served-code extract)

## 1. Overview / Context

Fizzy pipeline v5 arms an independent system-validation obligation for
system-altitude sessions: `_node_is_v_complete` requires
`system_validation_complete` separately from `system_verification_complete`,
and the Finalization→Completed advance refuses to close a session whose ConOps
user stories lack passing validation rows. The gate's contract is fully pinned
(tool `mark_system_validation_complete`; see contract extract) but the skill
has no process that produces its inputs. This spec defines that production
line: ConOps derivation, validation-row drafting, scenario execution and
evidence capture, the human judgment gate, artifact emission, the MCP close
call, and the remediation loop.

**Verification vs validation (one line):** verification asks "did we build it
right?" (against the spec); validation asks "did we build the right thing?"
(against operational intent). The gate enforces that the second question is
answered by a human from intent-anchored scenarios, never by re-pointing at
the test suite.

## 2. Goals and Non-Goals

Goals G1–G5 and Non-Goals NG1–NG5 are normative as stated in
`roadmap/manifest.json`. Summarized: (G1) system-altitude sessions can V-close
via documented process; (G2) validation judges intent, passing anti-relabeling
by construction; (G3) Jason is the sole oracle at one-batched-digest cost;
(G4) ConOps is derived late and hash-bound; (G5) scenario refresh only through
an auditable anti-hindsight rule. Non-goals: no fizzy-side changes (NG1), no
sub-system-altitude obligations or v4 retrofit (NG2), no automated judgment
(NG3), no new servers/lanes/tools (NG4), no verification-success oracles (NG5).

## 3. Getting Started (bootstrap — US-0)

Entry point for a conductor at Phase 7 of a system-altitude session:

1. Read `phases/07-execution.md` §"Validation leg (system altitude)" — added by
   this spec. It links the three artifacts and their order:
   `conops.md` → `validation-rows.json` (draft) → (Phase 8) evidence +
   `system_validation.json`.
2. Run `validation_emission.py derive-conops` against the session's
   `roadmap/manifest.json`. Output: `specs/<slug>/roadmap/conops.md` + recorded
   sha256 prefix.
3. Draft rows (conductor prose, module-validated):
   `validation_emission.py check-rows specs/<slug>/validation-rows.json`.
4. At Phase 8 close: execute scenarios, assemble digest, collect judgments,
   `validation_emission.py self-check`, then call
   `mark_system_validation_complete`. Every reject code's response: §10.

Time budget: a fresh conductor reaches a self-check-clean draft in <30 min
(TC-0.1). All commands run from the project root; no fizzy source reading
required (US-0).

## 4. System Architecture

```
roadmap/manifest.json ──derive-conops──► roadmap/conops.md ──sha256──┐
        │                                                            │
        └──(Phase 7) draft rows──► validation-rows.json (draft)      │
                                        │                            │
 (Phase 8, post-implementation)         ▼                            │
 execute scenarios ──► validation-evidence/<row-id>/ ──► digest ──► Jason
                                        │                  (Telegram, batched)
                              reply grammar parse                    │
                                        ▼                            │
                          system_validation.json ◄── conops_hash ────┘
                                        │
                       self-check (mirror of gate rejects)
                                        ▼
                       mark_system_validation_complete (card 5604-style close)
                                        ▼
                       Finalization → Completed (coverage gate)
```

One new module owns every machine-checkable shape:
`skills/adversarial-spec/scripts/validation_emission.py` (mirrors the
`mini_spec_emission.py` pattern — doc-driven process, code-checked shapes).
Phase docs 07 and 08 gain a "Validation leg" section each; 02 already emits
US-n ids.

## 5. Artifact Contracts (data models)

### 5.1 `roadmap/conops.md` (US-1, US-2)

Markdown, ≥50 bytes (gate constraint). Structure:

```markdown
# ConOps: <session title>
## Operational narrative
<how the delivered system is used, in user terms — 1-3 paragraphs>
## User stories (intent register)
### US-0: <title>
AS A <persona> I WANT <action> SO THAT <benefit>
<one paragraph of operational meaning — what "working" looks like in use>
### US-1: ...
```

Derivation rules: every `US-\d+` id in the manifest MUST appear as a `### US-n`
heading (the close gate regexes `\bUS-\d+\b` over this file — a dropped id is
an UNVALIDATED_USER_STORY at close). Narrative paragraphs come from the
manifest story text plus the milestone context; the deriver never invents new
stories. Re-derivation overwrites the file and reports the new sha256 prefix.

### 5.2 `validation-rows.json` (draft rows — US-3, US-4, US-5)

```json
{
  "kind": "validation-rows-draft",
  "conops_hash": "<sha256 prefix at draft time>",
  "rows": [
    {
      "row_id": "r-US3-1",
      "conops_ref": "US-3",
      "scenario": "<end-to-end, user terms>",
      "oracle": "<observable user-level outcome Jason judges from intent>",
      "evidence_type": "agent-walkthrough-transcript | artifact-demo | narrative",
      "evidence_rationale": "<one line: why this type fits this scenario>",
      "test_targets": ["<optional; never a strict subset of verification targets>"],
      "result": null
    }
  ],
  "superseded": [
    {
      "row_id": "r-US3-1",
      "reason": "approved story change | removed story | replaced workflow | duplicate coverage",
      "approver": "jason",
      "approved_at": "<ISO8601>",
      "replacement_row_id": "r-US3-2"
    }
  ]
}
```

Constraints (module-enforced at `check-rows`):
- Every ConOps `US-n` covered by ≥1 active row (INV-7).
- `row_id` format `r-US<n>-<k>` — the N/A grammar operates on row ids.
- Oracle quality lint (US-4): reject oracles matching the banned class —
  "tests pass", "code merged", "gate passed", "CI green", or any phrasing
  whose subject is the test suite rather than user-observable behavior.
- `evidence_type` from the taxonomy with non-empty rationale (US-5):
  - `agent-walkthrough-transcript` — the agent executes the scenario
    end-to-end for real and attaches the transcript. Minimum bar: real
    commands/tool calls with real outputs; no mocked steps.
  - `artifact-demo` — pointers to built artifacts (commits, files, rendered
    output) mapped step-by-step to the scenario. Minimum bar: every scenario
    step maps to a concrete artifact reference.
  - `narrative` — written does-it-meet-intent argument citing implementation.
    Minimum bar: permitted only where execution is impossible or destructive;
    rationale must say why the stronger two types don't apply.
- Refresh rule (US-12): a row may be superseded only BEFORE Jason's final
  judgment, or after a HUMAN-APPROVED remediation/scope decision. Allowed
  reasons are the enum above; anything else (implementation failed, evidence
  missing, inconvenient, prior fail) is rejected by `check-rows`. Superseded
  rows are retained in `superseded` with full audit fields.

### 5.3 Evidence artifacts (US-13)

`specs/<slug>/validation-evidence/<row_id>/evidence.md` — produced at Phase 8
by EXECUTING the scenario per its `evidence_type` (transcript, artifact map,
or justified narrative). Digest assembly refuses any row whose evidence file
is missing or empty (INV-4, TC-3.7).

### 5.4 `system_validation.json` (gate input — US-8)

Exactly the gate's required shape plus our audit extras:

```json
{
  "kind": "system-validation",
  "conops_hash": "<fresh sha256 prefix of conops.md>",
  "rows": [
    {
      "conops_ref": "US-3",
      "scenario": "...",
      "oracle": "...",
      "result": "pass | fail | not-applicable",
      "row_id": "r-US3-1",
      "evidence_type": "...",
      "evidence_ref": "validation-evidence/r-US3-1/evidence.md",
      "judged_by": "jason",
      "judged_at": "<ISO8601>",
      "test_targets": ["..."]
    }
  ]
}
```

ASSUMPTION-1 (verify at implementation): the gate ignores unknown row fields
(`row_id`, `evidence_ref`, `judged_by`, ...). If it rejects extras, emit a
gate-clean projection and keep the audit copy as
`system_validation.audit.json`.

### 5.5 Digest + reply grammar (US-6, US-7)

Digest: one Telegram message via `telegram-send`, formatted:

```
🥊📜 VALIDATION DIGEST <session> (<N> rows)
[1] r-US3-1 (US-3)
  scenario: <one line>
  oracle: <one line>
  evidence: <type> — <one-line summary> (full: <path>)
...
Reply: "pass all" | "fail r-US3-1: <reason>" | "na r-US3-1: <justification>"
(lines combine; unlisted rows inherit "pass" only if reply starts "pass rest")
```

If the digest exceeds Telegram's message limit, split at row boundaries into
parts labeled `(part i/k)`; judgments reference row ids so parts don't need
ordered replies.

Reply grammar (deterministic, line-oriented):

```
reply      := line+
line       := "pass all" | "pass rest" | verdict
verdict    := ("fail" | "na") SP row_id ":" SP text
row_id     := "r-US" digits "-" digits
```

Parse rules: `fail`/`na` lines mutate exactly their row; `pass all` sets every
unjudged active row to pass; `pass rest` sets remaining unjudged rows to pass
after explicit verdicts; `na` requires non-empty justification text (else
re-prompt, TC-3.5); any unparseable line → re-prompt with the offending line
quoted, zero mutations applied (TC-3.2). N/A is row-level only: if a story's
ONLY active row goes N/A, close is blocked pre-MCP with the two documented
resolutions — draft a replacement row or remove the story from ConOps (edit +
re-hash + re-digest delta) (TC-3.6).

## 6. Component Design — `validation_emission.py`

Subcommands (all pure-local, no MCP):
- `derive-conops <manifest> [-o conops.md]` — §5.1; prints sha256 prefix.
- `check-rows <validation-rows.json>` — §5.2 constraints; exit 2 on violation
  with `{code, row_id, detail}` issues (codes mirror gate names where they
  overlap).
- `self-check <system_validation.json> --conops <conops.md> [--verification-ledger <path>]`
  — full mirror of the gate's reject classes: kind, conops_hash prefix-match,
  rows non-empty, per-row required fields, result enum, all-pass, anti-
  relabeling strict-subset (with the served-code empty-set semantics: empty
  validation target set PASSES), US coverage vs the ConOps regex. Verdict
  parity with the gate is a tested invariant (TC-3.3).
- `assemble-digest <validation-rows.json> --evidence-dir <dir>` — §5.5;
  refuses missing evidence (INV-4).
- `parse-reply <digest-state> <reply-text>` — §5.5 grammar; emits row
  mutations or `RepromptRequired`.

The conductor (LLM) writes scenario/oracle prose; the module never generates
prose and never judges — it validates shapes and mechanizes the close (NG3).

## 7. Phase Wiring

- **Phase 7 (07-execution.md)**: after the execution plan is written and
  before `pipeline_load`, IF `session_altitude == "system"`: run
  `derive-conops`, draft rows, run `check-rows` until clean. Artifacts commit
  with the execution plan. (Rows precede implementation — anti-hindsight.)
- **Phase 8 (08-implementation.md)**: new close section "Validation leg
  (system altitude)" — after all task cards pass review and verification
  obligations are discharged: execute scenarios → evidence artifacts →
  `assemble-digest` → Telegram → parse replies (loop on re-prompt) → write
  `system_validation.json` → `self-check` → `mark_system_validation_complete`
  → proceed to Finalization advance. On any `fail` row: STOP, create
  remediation cards naming the failing `conops_ref`s, and re-enter after fix +
  re-execution + regenerated evidence (US-9; the gate hard-rejects fail rows,
  so the close step never calls the MCP with a fail present).
- **Refresh interplay (US-12)**: ConOps/story changes during implementation
  require Jason's approval (human-approved scope decision); after approval,
  re-derive ConOps (new hash), supersede affected rows with audit entries, and
  regenerate downstream artifacts.

## 8. Invariants (machine-extractable)

- INV-1: A `result` value originates ONLY from a parsed Jason reply (or
  terminal AskUserQuestion fallback) — never computed, never defaulted.
- INV-2: `not-applicable` is row-level; story-level removal is a ConOps edit.
- INV-3: Row supersession requires human approval outside the pre-judgment
  window; audit entry mandatory.
- INV-4: No digest row without a non-empty executed-evidence artifact.
- INV-5: `self-check` MUST pass immediately before every
  `mark_system_validation_complete` call.
- INV-6: No oracle may reference test-suite success (NG5).
- INV-7: Every active ConOps US id has ≥1 active row at all times after
  drafting; `check-rows` enforces.
- INV-8: ConOps hash recorded in `system_validation.json` is computed AFTER
  the last ConOps edit (stale-hash submissions are a self-check failure, not a
  gate discovery).

## 9. Error-Code Playbook (gate → documented response) (US-0, US-8)

| Gate reject | Conductor response |
|---|---|
| `SESSION_MISMATCH` | Verify card/session ids; never re-point at another session's card. |
| `VV_NOT_OBLIGATED_AT_ALTITUDE` | Card isn't system-altitude: validation leg doesn't apply — investigate why it ran (triage/altitude drift); do not force. |
| `VALIDATION_KIND_MISMATCH` | Artifact `kind` wrong — regenerate via module (hand-edited artifact suspected). |
| `VALIDATION_ARTIFACTS_INCOMPLETE` | Run `self-check`; fix the named field; if hash mismatch, re-derive ConOps and re-hash (INV-8 violated). |
| `VV_LEDGER_HAS_FAILURES` | Should be unreachable (close step blocks on fail rows); if hit, the remediation loop was bypassed — process failure note + remediate. |
| `VALIDATION_IS_RELABELED_VERIFICATION` | Rows re-point at verification fixtures — redraft scenarios from ConOps intent; check `test_targets` sets. |
| `SYSTEM_VALIDATION_MISSING` (at advance) | `mark_system_validation_complete` was never called for a system node — run the Phase 8 close section. |
| `UNVALIDATED_USER_STORY` (at advance) | A ConOps US id lacks a passing row — self-check coverage should have caught it; re-run close with coverage fix. |

## 10. Security / Operability

- Digest content goes through Telegram (external service): scenarios and
  evidence summaries only — no secrets, tokens, or proprietary payloads in
  digest text; evidence files stay local, referenced by path.
- Telegram unavailable → terminal AskUserQuestion fallback (same grammar,
  same INV-1 provenance); judgments are never deferred to an agent because the
  bridge is down.
- All JSON writes atomic (tmp+rename), consistent with skill-wide rule.

## 11. Testing Strategy

`tests-pseudo.md` is canonical (19 TCs, Data-Strategy-annotated). Concrete
tests land in `scripts/tests/test_validation_emission.py`. Verification =
pytest over the module (TC-1.x, TC-2.x, TC-3.2/3.3/3.5/3.6). Validation of
THIS session = running the process on itself (TC-0.1, TC-3.1, TC-3.4/3.7,
TC-4.1) — disjoint evidence surfaces by construction (T2).

## 12. Open Questions

- OQ-1: ASSUMPTION-1 (§5.4) — does the gate tolerate unknown row fields?
  Verify against served code at implementation; fallback specified.
- OQ-2: Telegram hard message-size limit to encode in `assemble-digest`
  (4096 chars classic; confirm with bridge wrapper).
- OQ-3: Should `derive-conops` run once at Phase 7 AND once at Phase 8 close
  (re-hash) by default, or only on detected roadmap edit? (INV-8 satisfiable
  either way; default-rederive is simpler, slightly noisier.)
- OQ-4 (fizzy handoff, not blocking): confirm empty-set anti-relabeling pass
  is intentional and stable (`pipeline.py` ~:9226 comment says yes).


---

# CONTEXT APPENDIX (for critics — not part of the spec under debate)

## A. Fixed downstream gate contract (served-code extract)

# Fizzy System-Validation Gate — Served-Code Contract Extract

> Extracted 2026-06-11 from /home/jason/PycharmProjects/fizzy-pipeline-mcp
> working tree (branch claim-race-in-progress-status) by an Explore agent.
> This is the FIXED contract the skill-side process must satisfy. Verify line
> numbers before citing in debate; behavior is the load-bearing part.

## Tool: `mark_system_validation_complete` (pipeline.py:9139-9346)

```python
async def mark_system_validation_complete(
    client, *, card_id: str, session_id: str, board_id: str | None = None,
    validation_artifact_path: str,   # path to system_validation.json
    conops_path: str,                # path to ConOps / user-intent artifact
) -> dict
```

Returns `{ok, card_id, kind="system_validation", rows, system_validation_artifacts}`.

## Preconditions (fail-closed, in order)

1. `_task_belongs_to_session` → else `SESSION_MISMATCH` (:9177)
2. `altitude == "system"` → else `VV_NOT_OBLIGATED_AT_ALTITUDE` (:9184)
3. `conops_path` readable, ≥50 bytes, suffix .md/.txt/.json → else
   `VALIDATION_ARTIFACTS_INCOMPLETE`; hashed via `_sha256_prefix` (:9191-9197)
4. `validation_artifact_path` readable .json, dict, `kind == "system-validation"`
   → else `VALIDATION_KIND_MISMATCH` (:9215)
5. Artifact `conops_hash` must prefix-match (either direction) the fresh hash of
   `conops_path` → staleness binding (:9232-9243)
6. `rows`: non-empty list of dicts; EVERY row requires non-empty strings
   `conops_ref` (user-story pointer, NOT a test file), `scenario` (end-to-end,
   user terms), `oracle` (how pass/fail judged from user intent), and
   `result ∈ {pass, fail, not-applicable}` (:9245-9282)
7. Any `result == "fail"` → `VV_LEDGER_HAS_FAILURES` with failing refs (:9284)
8. Anti-relabeling: validation rows' `test_targets` must NOT be a strict subset
   of `system_verification_artifacts`' test targets → else
   `VALIDATION_IS_RELABELED_VERIFICATION` (:9293-9315)

## Stored on card (write-once `system_validation_artifacts`, :9318-9328)

`validation_artifact_path`, `conops_path`, `conops_hash`, `row_count`,
`conops_ref_count`, `completed_at`. No per-row evidence field exists in the
contract — evidence lives skill-side.

## Obligation predicate `_node_owes_system_validation` (:8735-8746)

`pipeline_version >= 5 AND altitude == "system"`. v4 grandfathered.
`system_verification_complete` does NOT satisfy it (independence, "C2").

## V-completeness `_node_is_v_complete` (:8749-8766)

Altitude obligations each checked via `VV_COMPLETE_FLAG`; `system_validation`
appended independently if owed and `system_validation_complete is not True`.

## Session-close coverage gate `_check_system_validation_coverage_sync` (:9447-9572)

Runs at Finalization→Completed advance (v5 only):
- Every v5 system node must have `system_validation_complete == True` → else
  `SYSTEM_VALIDATION_MISSING`.
- Extracts ALL `US-\d+` ids (regex `\bUS-\d+\b`, :9438-9439) from the ConOps
  file; every id must appear in ≥1 row with `result == "pass"` (substring match
  on `conops_ref`) → else `UNVALIDATED_USER_STORY` (fails closed if artifacts
  unreadable).

## Schema-3 plan rule (:5045-5048)

A `system_validation` key in any task's verification binding →
`VV_ABOVE_ALTITUDE` ("system_validation is not part of the v4 contract").
Validation closes CARD-SIDE only, never plan-side.

## Where altitude lives

- Session card `pipeline_metadata`: `session_altitude`, `session_altitude_source`,
  `altitude_at_debate_start` (immutable capture at debate start, :6226-6229).
- Task cards: `altitude`, immutable at plan-load (`_ALTITUDE_IMMUTABLE`, :390).
- `CURRENT_PIPELINE_VERSION = 5` (:93).

## Fizzy-side design-doc anchors

- `20-vv-and-validation.md:163,179,184-186` — conops_ref points at roadmap
  user-story ids; hash binding rationale.
- `60-cross-repo-contract.md:6-7` — validation migration hooks.
- `NASA-CROSSWALK-SUPPLEMENT.md:53,261,543-544` — Appx S ConOps outline as the
  intended ConOps shape.


## B. Roadmap (confirmed; 14 user stories US-0..US-13)

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


## C. Test pseudocode (canonical test source of truth)

# Test Pseudocode: Validation-Leg Production Process

> Canonical source of truth for tests (stage: nl → acceptance → concrete).
> Roadmap: `roadmap/manifest.json`. Fixed gate contract:
> `fizzy-validation-contract.md` (reject codes referenced below are fizzy's).

## M0 — Getting Started

### TC-0.1: Cold-read bootstrap produces valid artifacts
**Data Strategy: REAL-DATA** — exercised on this session's own roadmap (the dogfood corpus is real data for this project).
```
given: a fresh agent with only the phase docs and this session's roadmap/manifest.json
when:  it follows the documented Phase 7 validation-leg entry point
then:  it produces conops.md + draft rows that pass the local self-check
assert: self_check(artifacts).valid == true
assert: elapsed <= 30 minutes
```

### TC-0.2: Docs enumerate all gate error codes with responses
**Data Strategy: STATIC** — doc-content check, no runtime.
```
given: the validation-leg phase docs
when:  scanned for fizzy's six reject codes (SESSION_MISMATCH, VV_NOT_OBLIGATED_AT_ALTITUDE,
       VALIDATION_ARTIFACTS_INCOMPLETE, VALIDATION_KIND_MISMATCH, VV_LEDGER_HAS_FAILURES,
       VALIDATION_IS_RELABELED_VERIFICATION)
then:  each code appears with a documented conductor response
assert: all 6 codes present with non-empty response text
```

## M1 — ConOps Derivation

### TC-1.1: Derivation includes every US id from the manifest
**Data Strategy: REAL-DATA** — run against this session's actual roadmap manifest (12 stories).
```
given: roadmap/manifest.json with user_stories US-0..US-11
when:  conops derivation runs
then:  conops.md contains every id, extractable by the gate's regex \bUS-\d+\b
assert: set(regex_extract(conops_md)) >= set(manifest_story_ids)
assert: len(conops_md) >= 50 bytes and suffix == ".md"
```

### TC-1.2: Dropped story fails self-check (error case)
**Data Strategy: SYNTHETIC** — a manifest/conops mismatch must be manufactured; derivation by construction includes all stories, so the gap cannot occur in a normal run.
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

## M2 — Row Drafting

### TC-2.1: Every story covered by ≥1 draft row
**Data Strategy: REAL-DATA** — drafted against this session's conops.
```
given: conops.md with N story ids
when:  row drafting completes
then:  every id appears in >=1 row's conops_ref
assert: uncovered_stories(rows, conops) == []
assert: every row has non-empty conops_ref, scenario, oracle, evidence_type
```

### TC-2.2: Relabeled verification caught locally (error case)
**Data Strategy: SYNTHETIC** — requires constructing rows whose test targets exactly subset the verification ledger; correct drafting never produces this.
```
given: a verification ledger with test_targets {a,b,c} and draft rows whose
       extracted test targets are {a,b} (strict subset)
when:  local self-check runs the anti-relabeling mirror
then:  it fails with the local twin of VALIDATION_IS_RELABELED_VERIFICATION
assert: self_check.valid == false
assert: issue.code == "VALIDATION_IS_RELABELED_VERIFICATION"
```

### TC-2.3: Oracle quality lint rejects test-restatement oracles (error case)
**Data Strategy: SYNTHETIC** — bad oracles ("all tests pass", "code merged") are manufactured counterexamples for the lint.
```
given: a row with oracle == "all integration tests pass"
when:  oracle quality lint runs
then:  the row is rejected with guidance to state an observable user-level outcome
assert: lint.valid == false and "observable" in lint.message
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
given: a draft row R1 for US-4 and (a) an approved story-change decision,
       (b) a prior fail judgment on R1 with no approved decision
when:  refresh is requested in each case
then:  (a) R1 moves to the superseded audit section with reason/approver/
       timestamp/replacement-id and replacement row R1' is drafted;
       (b) refresh is rejected citing the disallowed-reason list
assert: case-a audit entry complete and US-4 still covered by an active row
assert: case-b raises RefreshDisallowed naming "prior negative judgment"
```

## M3 — Gate & Close

### TC-3.1: Digest assembly from judged rows
**Data Strategy: REAL-DATA** — assembled from this session's real rows; sent over the real bridge during dogfood.
```
given: N draft rows with assembled evidence summaries
when:  digest assembly runs
then:  one Telegram-ready message contains every row's conops_ref, scenario,
       oracle, and evidence summary, within message-size limits (or the
       documented multi-part rule)
assert: all rows present; size constraint satisfied
```

### TC-3.2: Reply grammar round-trip — all forms + malformed input
**Data Strategy: SYNTHETIC** — parser unit tests over the full grammar; exact strings need precise control.
```
given: replies "pass all", "fail US-3: scenario shows wrong lane", "na US-7: deferred by decision D2",
       and a mixed multi-line reply, and malformed "US-3 nope"
when:  the reply parser runs
then:  each well-formed reply mutates exactly the intended rows; malformed
       input produces a re-prompt, never a guessed mutation
assert: parse("pass all") -> all rows result=pass
assert: parse fail/na forms -> exactly one row mutated, justification captured
assert: parse(malformed) -> RepromptRequired, zero mutations
```

### TC-3.3: Self-check ≡ gate on valid + each invalid artifact class
**Data Strategy: SYNTHETIC** — one manufactured artifact per reject class (bad kind, stale hash, empty rows, missing field, bad enum, fail row, relabeled targets).
```
given: a known-good system_validation.json and 7 single-defect variants
when:  local self-check evaluates each
then:  good passes; each variant fails with the same code the gate would emit
assert: verdict parity with fizzy-validation-contract.md for all 8 cases
```

### TC-3.4: Fail row spawns remediation path
**Data Strategy: REAL-DATA** — exercised on the staging/dogfood board with a deliberately failed judgment.
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
given: reply "na US-5:" (empty justification)
when:  reply parser runs
then:  rejected with re-prompt requiring justification text
assert: row US-5 unchanged; RepromptRequired raised
```

### TC-3.6: N/A on a story's sole row blocks close (coverage-gate constraint)
**Data Strategy: SYNTHETIC** — sole-row N/A must be manufactured; normal drafting plus judgments rarely isolates it.
```
given: US-9 covered by exactly one row, judged "na r-9-1: deferred by D4"
when:  the close step runs coverage pre-check
then:  close is blocked BEFORE any MCP call with guidance: either draft a
       replacement row for US-9 or remove US-9 from ConOps (edit + re-hash)
assert: mark_call_attempted == false
assert: blocker names US-9 and offers both documented resolutions
```

### TC-3.7: Scenario execution produces evidence artifact before digest (error case included)
**Data Strategy: REAL-DATA** — executed on this session's own scenarios during dogfood; the no-evidence error branch is the cheap synthetic twin.
```
given: judged-ready draft rows after implementation completes
when:  the Phase 8 close step runs
then:  each row's scenario is EXECUTED (per its evidence_type) and a per-row
       evidence artifact exists BEFORE digest assembly; a row with no
       execution evidence blocks digest assembly with a named row
assert: every digest row references a non-empty evidence artifact
assert: digest_assembly(rows_with_missing_evidence) raises EvidenceMissing
```

## M4 — Dogfood

### TC-4.1: This session V-closes end-to-end through the real gate
**Data Strategy: REAL-DATA** — the entire point: real session, real card 5604, real judgments, real MCP call.
```
given: this session at end of Phase 8 with implemented process + artifacts
when:  the documented close runs (digest -> Jason judges -> system_validation.json
       -> mark_system_validation_complete -> Finalization advance)
then:  the real gate accepts on first call (self-check parity held) and the
       coverage gate passes with all US ids covered
assert: card 5604 meta.system_validation_complete == true
assert: session advance to Completed succeeds
```
