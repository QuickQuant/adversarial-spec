# Spec: Validation-Leg Production Process (v2)

> Session `adv-spec-202606110339-validation-leg-process` | card 5604 | altitude: system
> Depth: technical | Roadmap: `roadmap/manifest.json` (14 stories US-0..US-13, confirmed)
> Fixed downstream contract: `fizzy-validation-contract.md` (served-code extract)
> v2: R1 synthesis — codex/gpt-5.5 (10 findings) + gemini-3.1-pro (6) + Claude

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

### 6.2 `validation-rows.json` (draft rows — US-3, US-4, US-5)

```json
{
  "kind": "validation-rows-draft",
  "conops_hash": "<sha256 prefix at draft time>",
  "rows": [
    {
      "row_id": "r-US3-1",
      "conops_ref": "US-3",
      "scenario": "<end-to-end, user terms: actor, trigger, action path, endpoint>",
      "oracle": "Jason passes this row iff <observable user outcome> demonstrates <named intent from US-3>.",
      "evidence_type": "agent-walkthrough-transcript | artifact-demo | narrative",
      "evidence_rationale": "<one line: why this type fits this scenario>",
      "test_targets": ["<optional; see INV-11>"],
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
- `system_validation.json` becomes the gate-clean projection containing ONLY
  `conops_ref`, `scenario`, `oracle`, `result`, and optional `test_targets` —
  this file is what `validation_artifact_path` points at (name stays stable
  for fizzy-side docs).
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

**Multi-part rule (R1 codex):** if the digest exceeds the Telegram size limit,
split at row boundaries into parts labeled `(part i/k)`; EVERY part carries
the same `digest-id` and total row count. The parser validates replies against
the full digest-state file (all rows), never against an individual part's
text. Digest state lives at
`specs/<slug>/validation-evidence/digest-<digest-id>.json`.

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

Subcommands (all pure-local, no MCP):
- `derive-conops <manifest> [-o conops.md]` — §6.1; prints sha256 prefix.
- `check-rows <validation-rows.json>` — §6.2 constraints; exit 2 on violation
  with `{code, row_id, detail}` issues (codes mirror gate names where they
  overlap).
- `self-check <system_validation.json> --conops <conops.md> [--verification-ledger <path>]`
  — full mirror of the gate's reject classes: kind, conops_hash prefix-match,
  rows non-empty, per-row required fields, result enum, all-pass,
  anti-relabeling (strict subset per gate, EXTENDED locally to also reject
  identical sets — INV-11), US coverage vs the ConOps regex. Verdict parity
  with the gate is a tested invariant (TC-3.3); the local identical-set
  extension is strictly-stricter, so local-clean ⇒ gate-clean.
- `assemble-digest <validation-rows.json> --evidence-dir <dir>` — §6.5;
  refuses missing/empty/type-mismatched evidence (INV-4); excludes superseded
  rows (INV-10); writes the digest-state file.
- `parse-reply <digest-state> <reply-text>` — §6.5 grammar; emits row
  mutations or `RepromptRequired`; atomic application.

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

## 9. Invariants (machine-extractable)

- INV-1: A `result` value originates ONLY from a parsed Jason reply (or
  terminal AskUserQuestion fallback) — never computed, never defaulted.
- INV-2: `not-applicable` is row-level; story-level removal is a ConOps edit.
- INV-3: Row supersession requires human approval outside the pre-judgment
  window; audit entry mandatory.
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
- OQ-2: Telegram hard message-size limit to encode in `assemble-digest`
  (4096 chars classic; confirm with bridge wrapper).
- OQ-3: Should `derive-conops` run once at Phase 7 AND once at Phase 8 close
  (re-hash) by default, or only on detected roadmap edit? (INV-8 satisfiable
  either way; default-rederive is simpler, slightly noisier.)
- OQ-4 (fizzy handoff, not blocking): (a) confirm empty-set anti-relabeling
  pass is intentional (`pipeline.py` ~:9226 comment says yes); (b) report the
  identical-set loophole — identical validation/verification target sets pass
  the gate's strict-subset check (INV-11 closes it locally).
