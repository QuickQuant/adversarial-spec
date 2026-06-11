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
