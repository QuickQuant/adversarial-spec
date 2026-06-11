# Spec: Validation-Leg Production Process (v3)

> Session `adv-spec-202606110339-validation-leg-process` | card 5604 | altitude: system
> Depth: technical | Roadmap: `roadmap/manifest.json` (14 stories US-0..US-13, confirmed)
> Fixed downstream contract: `fizzy-validation-contract.md` (served-code extract)
> v3: R2 synthesis — single-ledger model (digest-state eliminated), row state
> machine, artifact hash chain, provenance fields. R1: codex 10 + gemini 6;
> R2: codex 8 + gemini 4; + Claude both rounds.

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

   **Minimal valid draft row standard** (the row-drafting bar — R1 codex):
   - `conops_ref`: one active `US-n` from ConOps.
   - `scenario`: a user workflow with actor, trigger, action path, and
     expected operational endpoint.
   - `oracle` in the canonical form:
     `Jason passes this row iff <observable user outcome> demonstrates <named intent from US-n>.`
   - `evidence_type` + non-empty `evidence_rationale`.
   - `test_targets` omitted unless the row genuinely needs references; never
     identical to or a subset of verification targets (INV-11).

   The Phase 7 doc MUST include one good row example and one rejected row
   example (with the reject reason).
4. At Phase 8 close: execute scenarios, assemble digest, collect judgments,
   `validation_emission.py self-check`, then call
   `mark_system_validation_complete`. Every reject code's response: §10.

Time budget: a fresh conductor reaches a self-check-clean draft in <30 min
(TC-0.1). All commands run from the project root; no fizzy source reading
required (US-0).

## 4. User Journey (R1: convergent codex + gemini finding)

Roles: **conductor** (drafts, executes, mechanizes), **implementation agents**
(build; fix remediation cards), **Jason** (sole validator).

1. **Phase 7 — drafting.** Conductor derives `conops.md` from the roadmap
   (hash recorded) and drafts ≥1 intent-anchored row per `US-n`
   (`check-rows` clean). Jason may preemptively veto or adjust drafted
   scenarios but is not required to act.
2. **Implementation.** Agents build; verification obligations discharge
   through the normal V&V leg. Validation rows sit untouched (anti-hindsight);
   changes to stories require Jason-approved scope decisions → US-12 refresh.
3. **Phase 8 — execution.** After all task cards pass review and verification
   is discharged, the conductor EXECUTES every active row's scenario per its
   `evidence_type` and writes per-row evidence artifacts (US-13).
4. **Digest.** Conductor assembles one batched Telegram digest (or labeled
   multi-part, §6.5) — every active row with scenario, oracle, and evidence
   summary. Superseded rows never appear (INV-10).
5. **Judgment.** Jason replies in Telegram with the verdict grammar (§6.5) —
   per-row pass/fail/na, `pass all`, or `pass rest`; multi-line justifications
   supported. Terminal AskUserQuestion is the fallback when he's at the
   keyboard or the bridge is down.
6. **Parse.** The parser applies a fully-valid reply atomically or re-prompts
   quoting the offending text with ZERO mutations — judgments can't be
   half-applied.
7. **Fail path.** Any `fail` stops the close: remediation cards are created
   naming the failing `conops_ref`s; implementation agents fix; the conductor
   re-executes the scenario, regenerates evidence, and re-digests (delta
   digest for re-judged rows only).
8. **N/A path.** A sole-row N/A blocks close until a replacement row passes
   or Jason approves removing the story from ConOps (edit + re-hash).
9. **Close.** All rows pass → `system_validation.json` emitted → `self-check`
   passes → `mark_system_validation_complete` → Finalization→Completed
   advance (coverage gate).

## 5. System Architecture

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
                       mark_system_validation_complete
                                        ▼
                       Finalization → Completed (coverage gate)
```

One new module owns every machine-checkable shape:
`skills/adversarial-spec/scripts/validation_emission.py` (mirrors the
`mini_spec_emission.py` pattern — doc-driven process, code-checked shapes).
Phase docs 07 and 08 gain a "Validation leg" section each; 02 already emits
US-n ids.

## 6. Artifact Contracts (data models)

### 6.1 `roadmap/conops.md` (US-1, US-2)

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

Derivation rules: every `US-\d+` id in the manifest MUST appear exactly as a
`### US-n` heading (the close gate regexes `\bUS-\d+\b` over this file — a
dropped id is an UNVALIDATED_USER_STORY at close; the heading form is OUR
stricter shape so the file reads as an intent register, TC-1.1). Narrative
paragraphs come from the manifest story text plus milestone context; the
deriver never invents new stories. Re-derivation overwrites the file and
reports the new sha256 prefix.

### 6.2 `validation-rows.json` — the single stateful LEDGER (US-3, US-4, US-5)

**One file owns row state through the entire lifecycle** (R2 convergent
CRITICAL: a separate digest-state file split-brains against the draft).
Drafted at Phase 7, mutated only by `parse-reply` and `assemble-digest` under
a lock file (`validation-rows.json.lock`), projected to the gate artifact by
`emit-system-validation` — judgments are never hand-transcribed by an LLM.

```json
{
  "kind": "validation-rows-ledger",
  "conops_hash": "<sha256 prefix at draft time>",
  "digest_batches": [
    {"digest_id": "d-1", "parts": 2, "sent_at": "<ISO8601>", "row_ids": ["r-US3-1"]}
  ],
  "rows": [
    {
      "row_id": "r-US3-1",
      "row_hash": "<sha256 prefix of scenario+oracle+evidence_type>",
      "conops_ref": "US-3",
      "scenario": "<end-to-end, user terms: actor, trigger, action path, endpoint>",
      "oracle": "Jason passes this row iff <observable user outcome> demonstrates <named intent from US-3>.",
      "evidence_type": "agent-walkthrough-transcript | artifact-demo | narrative",
      "evidence_rationale": "<one line: why this type fits this scenario>",
      "test_targets": ["<optional; see INV-11>"],
      "result": null,
      "judgment": {"digest_id": "d-1", "source": "telegram | terminal", "reply_ref": "<message id or transcript ref>", "judged_at": "<ISO8601>", "justification": "<text|null>"},
      "judgment_history": [
        {"result": "fail", "digest_id": "d-1", "source": "telegram", "reply_ref": "<id>", "judged_at": "<ISO8601>", "justification": "<text>"}
      ]
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
- `row_id` format `r-US<n>-<k>` — verdict grammar operates on row ids ONLY,
  never bare `US-n` (R1 codex: prevents grammar/roadmap drift).
- **Oracle quality (US-4) — two-layer enforcement (R1 gemini realism):**
  - Layer 1 (primary): the conductor LLM drafts oracles against the canonical
    `iff` form (§3) — drafting-time constraint in the Phase 7 doc.
  - Layer 2 (fallback lint in `check-rows`): reject oracles containing the
    banned class — "tests pass", "code merged", "gate passed", "CI green" —
    or vague terminals ("works", "looks good", "acceptable", "done",
    "successful") unless paired with a concrete observable outcome; require
    the literal `iff` form and a named US-n intent reference.
- `evidence_type` from the taxonomy with non-empty rationale (US-5):
  - `agent-walkthrough-transcript` — the agent executes the scenario
    end-to-end for real and attaches the transcript. Minimum bar: real
    commands/tool calls with real outputs; no mocked steps. (Async: the agent
    walks, Jason reviews the transcript — never synchronous.)
  - `artifact-demo` — pointers to built artifacts (commits, files, rendered
    output) mapped step-by-step to the scenario. Minimum bar: every scenario
    step maps to a concrete artifact reference.
  - `narrative` — written does-it-meet-intent argument citing implementation.
    Minimum bar: permitted only where execution is impossible or destructive;
    rationale must say why the stronger two types don't apply.
- Refresh rule (US-12): a row may be superseded only BEFORE Jason's final
  judgment, or after a HUMAN-APPROVED remediation/scope decision (an agent
  never approves its own scope reduction). Allowed reasons are the enum above;
  anything else (implementation failed, evidence missing, inconvenient, prior
  fail) is rejected by `check-rows`. Superseded rows are retained in
  `superseded` with full audit fields and are strictly excluded from digests
  and reply parsing (INV-10).

### 6.3 Evidence artifacts (US-13)

`specs/<slug>/validation-evidence/<row_id>/evidence.md` — produced at Phase 8
by EXECUTING the scenario per its `evidence_type` (transcript, artifact map,
or justified narrative). Digest assembly refuses any row whose evidence file
is missing, empty, or mismatched with its declared `evidence_type` (INV-4,
TC-3.7). Evidence provenance is row-bound and hash-bound (INV-9): produced
after implementation, before digest assembly, under the current `conops_hash`;
ConOps edits or row supersession invalidate prior evidence for that row.

**Hash chain (INV-12, R2 codex):** every evidence.md MUST embed the
`row_hash` and `conops_hash` it was produced under (header lines). A row edit
changes `row_hash` and orphans the old evidence — `assemble-digest` rejects
hash-mismatched evidence the same as missing evidence. **Provenance minimums**
for `agent-walkthrough-transcript`: real command/tool invocations with their
outputs and timestamps embedded. The module verifies embedded hashes and
structure; it CANNOT prove execution authenticity — that integrity claim is
enforced by conductor discipline and checked at dogfood/spot-review, and is
documented as such rather than promised as a deterministic guarantee (R2
honesty fix, codex + gemini convergent).

### 6.4 `system_validation.json` (gate input — US-8)

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

**ASSUMPTION-1 resolution protocol (R1 codex + gemini):** whether the gate
tolerates unknown row fields MUST be verified during implementation (first
self-check parity test against served code). If unknown fields are rejected:
- `system_validation.json` becomes the gate-clean projection: top-level
  `kind` + `conops_hash` (ALWAYS present — the gate requires both), and rows
  containing ONLY `conops_ref`, `scenario`, `oracle`, `result`, and optional
  `test_targets`. This file is what `validation_artifact_path` points at
  (name stays stable for fizzy-side docs).
- `system_validation.audit.json` carries all audit fields and is the skill's
  rich record.
- The two files are hash-linked: identical `conops_hash` and identical row
  ordering; `self-check` runs on the EXACT file passed to the MCP call.

### 6.5 Digest + reply grammar (US-6, US-7)

Digest: one Telegram message via `telegram-send`, formatted:

```
🥊📜 VALIDATION DIGEST <session> <digest-id> (<N> rows)
[1] r-US3-1 (US-3)
  scenario: <one line>
  oracle: <one line>
  evidence: <type> — <one-line summary> (full: <path>)
...
Reply: "pass all" | "pass r-US3-1" | "fail r-US3-1: <reason>" | "na r-US3-1: <justification>"
```

**Multi-part rule (R1 codex, R2 mechanics):** message budget is **3500 chars**
per part (Telegram's raw limit is 4096 and the bridge wrapper does no
splitting — Appendix D; conservative budget absorbs encoding overhead). Split
at row boundaries into parts labeled `(part i/k)`; EVERY part carries the same
`digest-id` and total row count. If a single row exceeds the budget, its
evidence summary is truncated deterministically (head + `…` + full path
pointer) — scenario and oracle are never truncated. `assemble-digest` writes
each part as a discrete file `validation-evidence/digest-<digest-id>-part-<i>.txt`
and prints the paths; the conductor loops `telegram-send` over them (R2
gemini). The DIGEST BATCH is recorded in the ledger (`digest_batches[]`) —
there is no separate digest-state file; replies are validated against the
ledger's active batch, and a reply referencing a non-active `digest-id` is
rejected as stale (replay protection, R2 codex).

**Delta digest (remediation re-entry, R2 convergent):** `assemble-digest`
includes only rows with `result == null`. Re-assembling after a remediation
requires the failed rows to have been reset: the reset moves the fail judgment
into `judgment_history` (append-only — the original failed judgment is never
erased, R2 codex immutability) and sets `result`/`judgment` to null, gated on
the remediation card(s) for that row being resolved. Already-passed rows are
NEVER re-digested or re-judged unless superseded (INV-13).

Reply grammar (deterministic, block-oriented — R1 gemini):

```
reply      := block+
block      := verdict (newline continuation)*
verdict    := ("pass" | "fail" | "na") SP target [":" SP text]
target     := row_id | "all" | "rest"
row_id     := "r-US" digits "-" digits
```

Parse rules:
- `pass <row_id>` passes exactly one row; `fail`/`na <row_id>` mutate exactly
  their row. Continuation lines append to the preceding verdict's text
  (multi-line justifications).
- `pass all` sets every unjudged ACTIVE row in the digest state to pass —
  across all parts of a multi-part digest. `pass rest` does the same but only
  after explicit verdicts in the same reply are applied. (`fail all` /
  `na all` are invalid.)
- Duplicate verdicts for the same row in one reply are invalid unless
  identical.
- Unknown row ids, superseded row ids, and bare `US-n` targets are invalid.
- Partial replies are allowed only with explicit row verdicts; unlisted rows
  remain unjudged unless `pass all`/`pass rest` appears.
- `na` requires non-empty justification (else re-prompt, TC-3.5); N/A is
  accepted only from Jason and is row-level only — a story's sole active row
  going N/A blocks close with the two documented resolutions (TC-3.6).
- Any unparseable or invalid block → ZERO mutations and a re-prompt quoting
  the offending text (TC-3.2). Replies apply atomically or not at all.

## 7. Component Design — `validation_emission.py`

Subcommands (all pure-local, no MCP). **Mutation ownership (R2 codex):** only
`parse-reply` and `assemble-digest` mutate the ledger; both take
`validation-rows.json.lock` for the full read-modify-write (filelock pattern,
same as the skill's checkpoint discipline); everything else is read-only.

- `derive-conops <manifest> [-o conops.md]` — §6.1; prints sha256 prefix.
- `check-rows <validation-rows.json>` — §6.2 STRUCTURAL constraints; exit 2 on
  violation with `{code, row_id, detail}` issues (codes mirror gate names
  where they overlap). Scope honesty (R2 gemini CRITICAL): `check-rows`
  validates syntax and structure ONLY — id formats, iff-form, banned-phrase
  lint, coverage, target sets, hash presence. It cannot and does not judge
  semantic intent; wrong-story scenarios are caught by the human layers
  (conductor drafting review, Jason's judgment).
- `self-check <system_validation.json> --conops <conops.md> [--verification-ledger <path>]`
  — full mirror of the gate's reject classes: kind, conops_hash prefix-match,
  rows non-empty, per-row required fields, result enum, all-pass,
  anti-relabeling (strict subset per gate, EXTENDED locally to also reject
  identical sets — INV-11), US coverage vs the ConOps regex. Verdict parity
  with the gate is a tested invariant (TC-3.3); the local identical-set
  extension is strictly-stricter, so local-clean ⇒ gate-clean.
- `assemble-digest <validation-rows.json> --evidence-dir <dir>` — §6.5;
  includes only `result == null` rows (delta digest); refuses
  missing/empty/type-mismatched/hash-mismatched evidence (INV-4, INV-12);
  excludes superseded rows (INV-10); records the digest batch in the ledger;
  writes discrete part files and prints their paths. Resets resolved-fail rows
  (fail → history, result → null) only with `--reset-failed <row_id...>` and a
  resolved remediation reference per row.
- `parse-reply <validation-rows.json> <reply-text> --digest-id <d-N> --source telegram|terminal --reply-ref <id>`
  — §6.5 grammar; OWNS the locked ledger mutation: applies a fully-valid reply
  atomically (result + judgment provenance fields + history append) or raises
  `RepromptRequired` with zero mutations. Stale/non-active `digest-id` →
  rejected. There is no intermediate judgment store — judgments live in the
  ledger from the moment of parse (R2: closes the "where do judgments live"
  gap).
- `emit-system-validation <validation-rows.json> --conops <conops.md> [-o system_validation.json]`
  — NEW (R2 gemini): machine projection of the ledger's judged rows into the
  gate artifact shape (§6.4) — top-level `kind`, fresh `conops_hash`, rows
  with the gate's required fields (+ extras per ASSUMPTION-1 state). The
  conductor never hand-writes the gate artifact. Refuses if any active row is
  unjudged or failed.

The conductor (LLM) writes scenario/oracle prose; the module never generates
prose and never judges — it validates shapes and mechanizes the close (NG3).

## 8. Phase Wiring

- **Phase 7 (07-execution.md)**: after the execution plan is written and
  before `pipeline_load`, IF `session_altitude == "system"`: run
  `derive-conops`, draft rows (per the §3 minimal row standard, with the
  good/rejected examples), run `check-rows` until clean. Artifacts commit with
  the execution plan. (Rows precede implementation — anti-hindsight.)
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
  regenerate downstream artifacts (including evidence — INV-9).

**Row state machine (R2 codex — normative):**

| # | From | Event | To | Notes |
|---|------|-------|----|-------|
| S1 | drafted (`result:null`, no evidence) | scenario executed | evidence-attached | evidence embeds row_hash + conops_hash |
| S2 | evidence-attached | `assemble-digest` | digested (batch d-N) | only `result:null` rows; batch recorded in ledger |
| S3 | digested | `parse-reply` pass | judged-pass | TERMINAL unless superseded (INV-13) |
| S4 | digested | `parse-reply` fail | judged-fail | remediation cards created naming conops_ref |
| S5 | digested | `parse-reply` na | judged-na | row-level; sole-row N/A blocks close (TC-3.6) |
| S6 | judged-fail | remediation resolved + `--reset-failed` | drafted (evidence invalidated) | fail moves to judgment_history (append-only) |
| S7 | any pre-judgment | human-approved supersession | superseded | audit entry; excluded from digests/parsing (INV-10) |

No other transitions exist. Judged-pass rows cannot re-enter the cycle except
via S7 supersession; judgment_history is never rewritten.

## 9. Invariants (machine-extractable)

- INV-1: A `result` value originates ONLY from a parsed Jason reply (or
  terminal AskUserQuestion fallback) — never computed, never defaulted.
  ENFORCEABLE FORM (R2 codex): every non-null result carries the `judgment`
  provenance block (`digest_id`, `source`, `reply_ref`, `judged_at`);
  `emit-system-validation` refuses rows with a result but no provenance.
- INV-2: `not-applicable` is row-level; story-level removal is a ConOps edit.
- INV-3: Row supersession requires human approval outside the pre-judgment
  window; audit entry mandatory and MUST carry an `approval_ref` (Telegram
  message id, decision-log line, or transcript ref) — machine-checkable, not
  asserted (R2 codex).
- INV-4: No digest row without a non-empty executed-evidence artifact matching
  its declared `evidence_type`.
- INV-5: `self-check` MUST pass immediately before every
  `mark_system_validation_complete` call, on the exact file passed to it.
- INV-6: No oracle may reference test-suite success (NG5).
- INV-7: Every active ConOps US id has ≥1 active row at all times after
  drafting; `check-rows` enforces.
- INV-8: ConOps hash recorded in `system_validation.json` is computed AFTER
  the last ConOps edit (stale-hash submissions are a self-check failure, not a
  gate discovery).
- INV-9: Evidence provenance is row-bound and hash-bound — produced after
  implementation, before digest assembly, under the current `conops_hash`;
  ConOps changes or row supersession invalidate prior evidence for that row.
- INV-10: Superseded rows are strictly excluded from digest assembly and reply
  parsing.
- INV-11: Local anti-relabeling rejects validation `test_targets` that are a
  strict subset of OR identical to verification targets (stricter than the
  gate, which rejects only strict subsets — the identical-set loophole is
  flagged to fizzy, OQ-4).
- INV-12: Artifact hash chain — evidence embeds the `row_hash` + `conops_hash`
  it was produced under; `assemble-digest` and `emit-system-validation` verify
  the chain end-to-end (row edit ⇒ evidence orphaned ⇒ re-execute).
- INV-13: Judged-pass rows are immutable — never re-digested, re-judged, or
  edited; the only exit is human-approved supersession (S7).
- INV-14: `judgment_history` is append-only; resets move judgments into
  history, never erase them.

## 10. Error-Code Playbook (gate → documented response) (US-0, US-8)

| Gate reject | Conductor response |
|---|---|
| `SESSION_MISMATCH` | Verify card/session ids; never re-point at another session's card. |
| `VV_NOT_OBLIGATED_AT_ALTITUDE` | Card isn't system-altitude: validation leg doesn't apply — investigate why it ran (triage/altitude drift); do not force. |
| `VALIDATION_KIND_MISMATCH` | Artifact `kind` wrong — regenerate via module (hand-edited artifact suspected). |
| `VALIDATION_ARTIFACTS_INCOMPLETE` | Run `self-check`; fix the named field; if hash mismatch, re-derive ConOps and re-hash (INV-8 violated). |
| `VV_LEDGER_HAS_FAILURES` | Should be unreachable (close step blocks on fail rows); if hit, the remediation loop was bypassed — process failure note + remediate. |
| `VALIDATION_IS_RELABELED_VERIFICATION` | Rows re-point at verification fixtures — redraft scenarios from ConOps intent; check `test_targets` sets (INV-11 should have caught locally). |
| `SYSTEM_VALIDATION_MISSING` (at advance) | `mark_system_validation_complete` was never called for a system node — run the Phase 8 close section. |
| `UNVALIDATED_USER_STORY` (at advance) | A ConOps US id lacks a passing row — self-check coverage should have caught it; re-run close with coverage fix. |

## 11. Security / Operability

- Digest content goes through Telegram (external service): scenarios and
  evidence summaries only — no secrets, tokens, or proprietary payloads in
  digest text; evidence files stay local, referenced by path.
- Telegram unavailable → terminal AskUserQuestion fallback (same grammar,
  same INV-1 provenance); judgments are never deferred to an agent because the
  bridge is down.
- All JSON writes atomic (tmp+rename), consistent with skill-wide rule.

## 12. Testing Strategy

`tests-pseudo.md` is canonical (Data-Strategy-annotated). Concrete tests land
in `scripts/tests/test_validation_emission.py`. Verification = pytest over the
module (TC-1.x, TC-2.x, TC-3.2/3.3/3.5/3.6). Validation of THIS session =
running the process on itself (TC-0.1, TC-3.1, TC-3.4/3.7, TC-4.1) — disjoint
evidence surfaces by construction (T2).

**Dogfood validation is NOT satisfied by gate acceptance alone (R1 codex):**
TC-4.1 requires BOTH the real gate accepting on first call AND Jason's
intent-level acceptance of the process experience — that the bootstrap was
usable without reading fizzy source, the digest sufficed to judge from mobile,
reply/re-prompt behavior was unambiguous, and remediation guidance would be
actionable on a fail. Gate acceptance is the mechanical half; the usability
judgment is the validation half.

## 13. Open Questions

- OQ-1: ASSUMPTION-1 (§6.4) — does the gate tolerate unknown row fields?
  Verify against served code at implementation; resolution protocol specified.
- OQ-2: RESOLVED (context audit): bridge wrapper does no size handling;
  Telegram's raw 4096-char limit applies; `assemble-digest` budgets 3500
  chars/part and owns splitting (§6.5).
- OQ-3: Should `derive-conops` run once at Phase 7 AND once at Phase 8 close
  (re-hash) by default, or only on detected roadmap edit? (INV-8 satisfiable
  either way; default-rederive is simpler, slightly noisier.)
- OQ-4 (fizzy handoff, not blocking): (a) confirm empty-set anti-relabeling
  pass is intentional (`pipeline.py` ~:9226 comment says yes); (b) report the
  identical-set loophole — identical validation/verification target sets pass
  the gate's strict-subset check (INV-11 closes it locally).


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


## B. Test pseudocode (canonical, R2-synced)

# Test Pseudocode: Validation-Leg Production Process

> Canonical source of truth for tests (stage: nl → acceptance → concrete).
> Synced to spec-draft-v2.md (R1). Roadmap: `roadmap/manifest.json`. Fixed
> gate contract: `fizzy-validation-contract.md` (reject codes are fizzy's).

## M0 — Getting Started

### TC-0.1: Cold-read bootstrap produces valid artifacts
**Data Strategy: REAL-DATA** — exercised on this session's own roadmap (the dogfood corpus is real data for this project).
```
given: a fresh agent with only the phase docs (incl. the §3 minimal row
       standard + good/rejected row examples) and this session's roadmap/manifest.json
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
(Telegram digest size boundary deferred — OQ-2: limit unconfirmed; add [BVA]
pair when `assemble-digest` encodes the real limit.)

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
       TRACEABLE to evidence file content; each part <= 3500 chars, written as
       a discrete digest-<id>-part-<i>.txt file with paths printed; the batch
       (digest_id, parts, row_ids) is recorded in the ledger
assert: only result-null rows present; pass + superseded rows absent
assert: each evidence summary maps to content in its evidence.md
assert: every part file <= 3500 chars; batch recorded in digest_batches
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
assert: applied verdicts carry full provenance (digest_id, source, reply_ref,
        judged_at) in the ledger row's judgment block
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
when:  assemble-digest --reset-failed A C runs, then a new digest is assembled
then:  A's fail moves to judgment_history (append-only) and A re-enters the
       delta digest; C's reset is REFUSED (unresolved remediation); B is
       untouched and absent from the new digest (INV-13)
assert: A.judgment_history[-1].result == "fail"; A.result == null; A in new digest
assert: reset(C) raises RemediationUnresolved
assert: B.result == "pass" unchanged; B not in new digest
assert: emit-system-validation refuses while any active row is unjudged/failed
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

## C. Bridge fact: telegram-send wrapper does NO size handling; raw 4096-char Telegram limit; assemble-digest budgets 3500/part.
