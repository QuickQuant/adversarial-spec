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
