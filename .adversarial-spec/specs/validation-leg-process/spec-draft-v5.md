# Spec: Validation-Leg Production Process (v5)

> Session `adv-spec-202606110339-validation-leg-process` | card 5604 | altitude: system
> Depth: technical | Roadmap: `roadmap/manifest.json` (14 stories US-0..US-13, confirmed)
> Fixed downstream contract: `fizzy-validation-contract.md` (served-code extract,
> fizzy working tree 2026-06-11 — re-extract protocol in §13 if fizzy changes)
> v5: gauntlet synthesis (669 concerns → 62 themes, 48 accepted; report:
> `gauntlet-concerns-2026-06-11.json`). Headlines: sender identity read from raw
> listener payload (not conductor-typed); digest batch delivery tracking before
> bulk verdicts; per-story evidence hashes (no global invalidation); single gate
> artifact (OQ-1 provisionally resolved); supersession legal from any state;
> natural-language bulk-pass aliases (Jason ruling — no reply passwords);
> subcommand set expanded (normalize-rows, record-evidence, record-send,
> reset-failed, supersede-row, status); deterministic close algorithm; explicit
> threat model.
> v4: R3 synthesis — hash canonicalization, sender verification, lock/exit-code
> semantics, batch lifecycle, N/A close rule unified, close idempotency.
> Findings: R1 codex 10 + gemini 6; R2 codex 8 + gemini 4; R3 codex 10 + gemini 5;
> + Claude all rounds; gauntlet 7 adversaries × codex+gemini.

**Enforcement legend (used on MUST statements):** `[module]` = enforced in
`validation_emission.py` code; `[self-check]` = enforced by the self-check
mirror; `[conductor]` = documented conductor procedure (LLM follows phase doc);
`[human]` = Jason's judgment. A MUST without machine enforcement is labeled
honestly — this spec does not pretend procedure is code.

## 1. Overview / Context

Fizzy pipeline v5 arms an independent system-validation obligation for
system-altitude sessions: `_node_is_v_complete` requires
`system_validation_complete` separately from `system_verification_complete`,
and the Finalization→Completed advance refuses to close a session whose ConOps
user stories lack passing validation rows. The gate's artifact contract is
pinned by served-code extract (`fizzy-validation-contract.md`; tool
`mark_system_validation_complete`) — MCP transport behavior, card-metadata
reads, and remediation-card creation use the existing fizzy MCP toolset and are
named where consumed (§8). The skill has no process that produces the gate's
inputs. This spec defines that production line: ConOps derivation,
validation-row drafting, scenario execution and evidence capture, the human
judgment gate, artifact emission, the MCP close call, and the remediation loop.

**Verification vs validation (one line):** verification asks "did we build it
right?" (against the spec); validation asks "did we build the right thing?"
(against operational intent). The gate enforces that the second question is
answered by a human from intent-anchored scenarios, never by re-pointing at
the test suite.

**Threat model (scope honesty, gauntlet ACK-6):** this process defends against
honest mistakes and message-attribution confusion — a conductor LLM applying
the wrong Telegram message as a judgment, stale replies, half-applied state,
relabeled verification, forgotten steps. It does NOT defend against a malicious
agent with write access to this workspace: such an agent can rewrite the ledger,
the module, or the phase docs directly, and no local script can prevent that.
Multiple agents share this branch; the working rule is single-writer — only the
conductor session touches validation artifacts `[conductor]`.

## 2. Goals and Non-Goals

Goals G1–G5 and Non-Goals NG1–NG5 are normative as stated in
`roadmap/manifest.json`. Summarized: (G1) system-altitude sessions can V-close
via documented process; (G2) validation judges intent — structural
anti-relabeling checks plus human semantic layers (the "by construction" claim
is retired per gauntlet; machine checks catch declared-target reuse, humans
catch disguised intent); (G3) Jason is the sole oracle at one-batched-digest
cost (one digest *batch*, possibly multi-part — G3 means one review sitting,
not one Telegram packet); (G4) ConOps is derived late and hash-bound; (G5)
scenario refresh only through an auditable anti-hindsight rule. Non-goals: no
fizzy-side changes (NG1), no sub-system-altitude obligations or v4 retrofit
(NG2), no automated judgment (NG3), no new servers/lanes/tools (NG4), no
verification-success oracles (NG5).

## 3. Getting Started (bootstrap — US-0)

Entry point for a conductor at Phase 7 of a system-altitude session:

1. Read `phases/07-execution.md` §"Validation leg (system altitude)" — added by
   this spec. It links the three artifacts and their order:
   `conops.md` → `validation-rows.json` (draft) → (Phase 8) evidence +
   `system_validation.json`.
2. Run `validation_emission.py derive-conops` against the session's
   `roadmap/manifest.json`. Output:
   `.adversarial-spec/specs/<slug>/roadmap/conops.md` + recorded full sha256
   (12-hex prefix used only where the gate artifact needs it).
3. Draft rows (conductor prose), then `validation_emission.py normalize-rows`
   (stamps canonical hashes — the conductor never computes hex by hand), then
   `validation_emission.py check-rows` until clean.

   **Minimal valid draft row standard** (the row-drafting bar — R1 codex):
   - `conops_ref`: exactly one active US id, matching `^US-\d+$` `[module]`
     (exact-token rule; packed refs like "US-1, US-2" rejected — gauntlet CB-10).
   - `scenario`: a user workflow with actor, trigger, action path, and
     expected operational endpoint.
   - `oracle` in the canonical form:
     `Jason passes this row iff <observable user outcome> demonstrates <named intent from US-n>.`
   - `evidence_type` + non-empty `evidence_rationale`.
   - `test_targets` omitted unless the row genuinely needs references; a row
     whose scenario or oracle cites test files MUST declare them `[module]`
     (lint); never identical to, a subset of, OR overlapping verification
     targets without rationale (INV-11, gauntlet SEC-7).
   - scenario + oracle + digest furniture ≤ 3000 UTF-8 bytes per row `[module]`
     (a row that cannot fit a digest part is a drafting error, never a
     runtime delivery failure — gauntlet FM-9).
   - `row_id` format `r-US<n>-<k>`, globally unique across active AND
     superseded rows, prefix story number matching `conops_ref` `[module]`.

   The Phase 7 doc MUST include one good row example and one rejected row
   example (with the reject reason) `[conductor]`.
4. At Phase 8 close: follow the close algorithm (§8) — execute scenarios,
   `record-evidence`, `assemble-digest`, `record-send`, collect judgments via
   `parse-reply`, `emit-system-validation`, `self-check`, then
   `mark_system_validation_complete`. Every gate reject code's response: §10;
   every local error code's response: §10 (local table).

Time budget: a fresh conductor reaches a self-check-clean draft in <30 min —
this is a dogfood acceptance metric measured during TC-4.1, not a pytest
assertion (gauntlet OP-10). All commands run from the project root; no fizzy
source reading is required to OPERATE the process (US-0); implementers verify
ASSUMPTION-1/2 against served code once, during implementation (§13).

## 4. User Journey (R1: convergent codex + gemini finding)

Roles: **conductor** (drafts, executes, mechanizes), **implementation agents**
(build; fix remediation cards), **Jason** (sole validator).

1. **Phase 7 — drafting.** Conductor derives `conops.md` from the roadmap
   (full hash recorded) and drafts ≥1 intent-anchored row per `US-n`
   (`normalize-rows` then `check-rows` clean). Jason may preemptively veto or
   adjust drafted scenarios but is not required to act; pre-commit edits are
   ordinary drafting, post-commit changes go through `supersede-row` with an
   `approval_ref` (gauntlet DD-10).
2. **Implementation.** Agents build; verification obligations discharge
   through the normal V&V leg. Validation rows sit untouched (anti-hindsight);
   changes to stories require Jason-approved scope decisions → US-12 refresh.
   The committed Phase 7 ledger hash is the drift baseline (§8 preflight).
3. **Phase 8 — execution.** After all task cards pass review and verification
   is discharged, the conductor EXECUTES every active row's scenario per its
   `evidence_type` and records per-row evidence via `record-evidence` (US-13),
   including a conductor-written `evidence_summary` (mobile-sufficient — §6.5).
4. **Digest.** Conductor runs `assemble-digest` (one batch, possibly labeled
   multi-part, §6.5), sends each part via `telegram-send`, and records send
   results via `record-send`. Superseded rows never appear (INV-10). Bulk
   verdicts are honored only after every part is recorded sent (INV-16).
5. **Judgment.** Jason replies in Telegram — per-row verdicts, `pass all`,
   `pass rest`, or a natural bulk-pass phrase ("those all look good" — fixed
   alias list, §6.5); multi-line justifications supported. Terminal
   AskUserQuestion is the fallback when he's at the keyboard or the bridge is
   down.
6. **Parse.** The conductor passes the RAW wake-listener update file to
   `parse-reply --update-file`; the module itself extracts sender id, message
   id, and reply text (INV-15 — the conductor never transcribes identity).
   A fully-valid reply applies atomically or the module re-prompts quoting the
   offending text (truncated, framed as untrusted) with ZERO mutations.
   After applying, the conductor sends Jason a one-line confirmation of what
   was recorded (gauntlet OP-2).
7. **Fail path.** Any `fail` (justification required, like `na`) stops the
   close: if the batch is only partially judged, the conductor `cancel-batch`s
   the remainder (gauntlet CB-8); remediation cards are created by the
   CONDUCTOR via the existing fizzy MCP, carrying `{row_id, conops_ref,
   scenario, oracle, evidence_ref, fail justification, digest_id}`
   `[conductor]`; implementation agents fix; the conductor verifies card
   resolution via MCP, runs `reset-failed`, re-executes the scenario,
   `record-evidence` fresh, and re-digests (delta digest for re-judged rows
   only).
8. **N/A path.** `parse-reply` warns immediately when an `na` leaves a story
   with zero pass rows (gauntlet FM-11). A sole-row N/A blocks close until a
   replacement row passes or Jason approves removing the story — which is a
   MANIFEST edit first, then re-derive (ConOps never diverges from the
   manifest — gauntlet DD-7).
9. **Close.** Every active row judged (`pass`, or row-level `na` with every
   story still holding ≥1 pass — the single N/A rule, §6.4) →
   `emit-system-validation` → `self-check` (always, including on re-entry —
   INV-5 wins over re-entry shortcuts, gauntlet CB-5) →
   `mark_system_validation_complete` → post-call metadata read-back →
   Finalization→Completed advance. The close algorithm (§8) is the single
   normative ordering, idempotent at every step.

## 5. System Architecture

```
roadmap/manifest.json ──derive-conops [CLI]──► roadmap/conops.md ──sha256──┐
        │                                                                  │
        └─(Phase 7) conductor drafts rows [LLM prose]                      │
              └─► normalize-rows + check-rows [CLI] ─► validation-rows.json│
                                        │              (draft, hash-stamped)
 (Phase 8, post-implementation)         ▼                                  │
 execute scenarios [conductor] ─► record-evidence [CLI]                    │
        ─► validation-evidence/<row-id>/                                   │
                  │                                                        │
        assemble-digest [CLI] ─► validation-digests/ part files            │
                  │                                                        │
        telegram-send loop [conductor] ─► record-send [CLI] ─► Jason       │
                  │                                          (Telegram)    │
        wake-listener update file ─► parse-reply --update-file [CLI]       │
                                        ▼                                  │
                          emit-system-validation [CLI] ◄── conops_hash ────┘
                                        ▼
                       self-check [CLI] (mirror of gate rejects)
                                        ▼
                       mark_system_validation_complete [MCP, conductor]
                                        ▼
                       Finalization → Completed (coverage gate) [fizzy]
```

Arrow mechanisms labeled: [CLI] = `validation_emission.py` subcommand;
[LLM prose] / [conductor] = conductor procedure; [MCP] = existing fizzy tool;
[Telegram] = bridge. The conductor drafts prose and operates the sequence; the
module owns every machine-checkable shape (producer/consumer per subcommand:
§7). One new module: `skills/adversarial-spec/scripts/validation_emission.py`
(doc-driven process, code-checked shapes — the `mini_spec_emission.py` lineage
is the *pattern*, not a shared API; §7 defines this module's full contract).
Phase docs 07 and 08 gain a "Validation leg" section each; 02 already emits
US-n ids.

## 6. Artifact Contracts (data models)

All artifact paths live under `.adversarial-spec/specs/<slug>/` (canonical:
`roadmap/conops.md`, `validation-rows.json`, `validation-evidence/<row_id>/`,
`validation-digests/`, `system_validation.json`). Subcommands resolve paths
under the spec root via realpath; symlinks and escapes rejected `[module]`
(gauntlet SEC-9). All timestamps are UTC RFC3339 with `Z` `[module]`. All JSON
artifacts carry `schema_version` `[module]`. Input bounds `[module]`: reply
16KB, justification 2KB, ledger 5MB, ConOps 1MB — breach is a structured
exit-2 issue.

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

Derivation rules `[module]`:
- Inputs consumed (exact): manifest story `id`, `title`, `story` text, and the
  owning milestone's `title` + context paragraph. Nothing else. Narrative is
  assembled from these by template — the deriver is deterministic given the
  same manifest and never invents stories or free-generates prose (gauntlet
  DD-7).
- Every `US-\d+` id in the manifest MUST appear exactly as a `### US-n`
  heading (the close gate regexes `\bUS-\d+\b` over this file; the heading
  form is OUR stricter shape, TC-1.1).
- **Stray-id lint:** every `\bUS-\d+\b` token in the OUTPUT must correspond to
  a manifest story heading; a stray mention (e.g. "replaces US-2" where US-2
  is gone) is a derivation error — it would mint a phantom coverage
  obligation at the gate (gauntlet CB-11).
- Duplicate story ids in the manifest → exit 2 (gauntlet SEC-9).
- **Per-story hashes:** derive-conops records, alongside the full-file
  `conops_hash`, a `story_hashes` map — sha256 over each `### US-n` section's
  bytes (heading through next heading). Evidence binds to its story's hash, so
  editing one story invalidates only that story's evidence (gauntlet FM-3,
  Jason-approved).
- Re-derivation reports prior and new hashes, and refuses without `--force`
  when an existing ledger references the prior hash (overwrite safety —
  gauntlet DD-7); story REMOVAL requires the manifest edit first.

### 6.2 `validation-rows.json` — the single stateful LEDGER (US-3, US-4, US-5)

**One file owns row state through the entire lifecycle** (R2 convergent
CRITICAL: a separate digest-state file split-brains against the draft).
Mutated ONLY by the eight owning subcommands (§7: `normalize-rows`,
`record-evidence`, `parse-reply`, `assemble-digest`, `record-send`,
`cancel-batch`, `reset-failed`, `supersede-row`) under
`validation-rows.json.lock`; projected
to the gate artifact by `emit-system-validation` — judgments are never
hand-transcribed by an LLM `[module]`. ("Read-only" elsewhere in this spec
means *ledger-bytes-unchanged*; e.g. `emit-system-validation` writes the gate
artifact but never the ledger.)

```json
{
  "schema_version": "1.0",
  "kind": "validation-rows-ledger",
  "module_version": "<validation_emission __version__ + git short hash>",
  "conops_hash": "<full sha256 at draft time>",
  "story_hashes": {"US-3": "<full sha256 of the US-3 section>"},
  "drafted_baseline_hash": "<sha256 of the ledger as committed at Phase 7>",
  "digest_batches": [
    {
      "digest_id": "d-1",
      "status": "assembled | sent | closed | cancelled",
      "opened_at": "<RFC3339Z>", "closed_at": null, "cancelled_at": null,
      "cancel_reason": null,
      "conops_hash_snapshot": "<full sha256 at batch open>",
      "row_hash_snapshot": {"r-US3-1": "<row_hash at batch open>"},
      "evidence_hash_snapshot": {"r-US3-1": "<sha256 of evidence.md bytes>"},
      "parts": [
        {"i": 1, "path": "validation-digests/digest-d-1-part-1.txt",
         "sha256": "<part bytes>", "sent_at": null, "message_id": null,
         "send_result": "pending | sent | failed"}
      ],
      "row_ids": ["r-US3-1"],
      "processed_reply_refs": ["telegram:<chat>:<msg_id>"]
    }
  ],
  "rows": [
    {
      "row_id": "r-US3-1",
      "row_hash": "<full sha256 — canonicalization below>",
      "conops_ref": "US-3",
      "story_hash": "<story_hashes[US-3] at draft/refresh time>",
      "scenario": "<end-to-end, user terms: actor, trigger, action path, endpoint>",
      "oracle": "Jason passes this row iff <observable user outcome> demonstrates <named intent from US-3>.",
      "evidence_type": "agent-walkthrough-transcript",
      "evidence_rationale": "<one line: why this type fits this scenario>",
      "evidence_summary": "<conductor-written, mobile-sufficient, validated non-empty at digest time>",
      "test_targets": [],
      "result": null,
      "judgment": null,
      "judgment_history": [
        {"result": "fail", "digest_id": "d-1", "source": "telegram",
         "reply_ref": "telegram:<chat>:<msg_id>", "judged_at": "<RFC3339Z>",
         "justification": "<text>", "row_hash": "<at judgment>",
         "conops_hash": "<at judgment>"}
      ]
    }
  ],
  "superseded": [
    {
      "row_snapshot": {"row_id": "r-US3-1", "...": "FULL row object as retired"},
      "reason": "approved story change | removed story | replaced workflow | duplicate coverage | post-judgment retirement",
      "approver": "jason",
      "approval_ref": "telegram:<chat>:<msg_id> | transcript:<session>:<turn> | decision:<RFC3339Z>",
      "approved_at": "<RFC3339Z>",
      "replacement_row_id": "r-US3-2"
    }
  ],
  "security_events": [
    {"at": "<RFC3339Z>", "code": "SENDER_NOT_ALLOWLISTED",
     "sender_hash": "<sha256 of sender id — raw id never stored>",
     "digest_id": "d-1"}
  ]
}
```

Schema notes (gauntlet CB-2/CB-3/DD-4/DD-5/RC-3/RC-4/SEC-5/OP-1):
`result == null ⟺ judgment == null` `[module]`; `judgment_history` entries
carry the hash context they were judged under; batches snapshot conops, row,
AND evidence hashes at open; per-part send results + message ids recorded by
`record-send`; `processed_reply_refs` makes reply application idempotent
(duplicate delivery rejected); superseded entries retain the FULL row
snapshot; security events (discarded non-allowlisted replies, cancellations)
are durable in the ledger with sender ids hashed. **Active row predicate
(formal):** a row is active iff it appears in `rows[]` and its `row_id`
appears in no `superseded[].row_snapshot.row_id`. **Canonical ordering:**
ledger array order; `emit-system-validation` preserves it.

**Hash canonicalization (R3 convergent CRITICAL — deterministic or it doesn't
exist):**
- `row_hash` = sha256 over the UTF-8 encoding of
  `json.dumps([conops_ref, scenario, oracle, evidence_type], ensure_ascii=False, separators=(",", ":"))`
  with all four strings NFC-normalized first. FULL hash stored; 12-hex prefix
  emitted only where an artifact needs it; `self-check` rejects prefixes
  shorter than 12 `[module]` (gauntlet SEC-8). `evidence_rationale` and
  `test_targets` are EXCLUDED from `row_hash` (bookkeeping must not orphan
  evidence) — but both are snapshotted per batch, so they cannot drift while a
  digest is open (gauntlet RC-3 family).
- `conops_hash` = sha256 over the raw file bytes of `conops.md` (full,
  locally); `story_hashes` per §6.1. The gate prefix-matches bidirectionally;
  12 hex chars satisfy it at the artifact boundary.
- Hashes are computed ONLY by the module (`normalize-rows`, `record-evidence`)
  — the conductor never writes hex by hand (gauntlet CB-7).
- Lengths and constants are module constants pinned by tests.

**Digest batch lifecycle (R3 codex + gauntlet RC-2):** `assemble-digest`
creates a batch in status `assembled` (only `result == null` active rows) and
writes part files; the conductor sends each part and records the outcome via
`record-send`; when ALL parts record `sent`, the batch is `sent`. Bulk
verdicts (`pass all`/aliases/`pass rest`) are rejected unless the batch is
`sent` (INV-16) — Jason cannot bulk-approve rows that were never delivered.
`parse-reply` closes the batch (`closed`) when every snapshot row is judged.
EXACTLY ONE batch may be non-terminal (`assembled`/`sent`); `assemble-digest`
refuses while one exists. `cancel-batch --digest-id d-N --reason <text>`
cancels (audit-logged; rows return to the delta pool; if parts were already
sent, the conductor sends a cancellation notice through the same channel —
gauntlet FM-12). A reply verdict is rejected if the row's hash changed after
batch open (stale-row protection) or if the batch's `conops_hash_snapshot` no
longer matches (gauntlet RC-3). Digest ids are strictly monotonic per ledger
(max existing + 1, including cancelled), allocated under lock.

Constraints (module-enforced at `check-rows`; `--draft` mode checks structure
only and reports coverage as advisory, so incremental drafting isn't noisy —
INV-7 binds at draft-complete and at emission, gauntlet DD-8):
- Every ConOps `US-n` covered by ≥1 active row (INV-7); coverage uses
  exact-token equality (`conops_ref == "US-n"`), strictly stricter than the
  gate's substring match (gauntlet CB-10).
- `row_id` rules per §3 (format, global uniqueness incl. superseded, story
  prefix match).
- **Oracle quality (US-4) — two-layer enforcement (R1 gemini realism):**
  - Layer 1 (primary): the conductor LLM drafts oracles against the canonical
    `iff` form (§3) — drafting-time constraint in the Phase 7 doc `[conductor]`.
  - Layer 2 (fallback lint in `check-rows`) `[module]`: reject oracles
    containing the banned class — "tests pass", "code merged", "gate passed",
    "CI green", plus synonym classes ("suite succeeds", "pipeline healthy",
    "checks satisfied") — or vague terminals ("works", "looks good",
    "acceptable", "done", "successful") unless paired with a concrete
    observable outcome **defined as: the same sentence names an artifact,
    output, or user-visible behavior** (deterministic rule, gauntlet
    dismissal DIS-2 boundary); require the literal `iff` form and a named
    US-n intent reference. Scope honesty: lint is structural; semantics are
    human-owned (NG3).
- `evidence_type` from the taxonomy with non-empty rationale (US-5):
  - `agent-walkthrough-transcript` — the agent executes the scenario
    end-to-end for real and attaches the transcript. Minimum bar: real
    commands/tool calls with real outputs and timestamps; no mocked steps.
    (Async: the agent walks, Jason reviews the transcript — never synchronous.)
  - `artifact-demo` — pointers to built artifacts (commits, files, rendered
    output) mapped step-by-step to the scenario. Minimum bar: every scenario
    step maps to a concrete artifact reference.
  - `narrative` — written does-it-meet-intent argument citing implementation.
    Minimum bar: permitted only where execution is impossible or destructive;
    rationale must cite the concrete impossibility/destructive condition (not
    just assert it), and narrative rows are flagged in the digest so Jason
    sees the weaker evidence class (gauntlet AUDT-118939dc).
- Refresh rule (US-12): a row may be superseded at ANY lifecycle point —
  including judged-pass — always with human approval and full audit
  (`supersede-row` is the only path; resolves the v4 S7/INV-13 contradiction,
  gauntlet CB-1, Jason-approved). Decision rule: remediation that re-executes
  an unchanged scenario = `reset-failed` (S6); remediation or scope change
  that alters the scenario/oracle = `supersede-row` + replacement row.
  Allowed reasons are the enum in the schema; anything else (implementation
  failed, evidence missing, inconvenient) is rejected `[module]`. Supersession
  + replacement happen in ONE `supersede-row` invocation (transactional — no
  coverage gap, gauntlet DD-8). Superseded rows are strictly excluded from
  digests and reply parsing (INV-10).

### 6.3 Evidence artifacts (US-13)

`validation-evidence/<row_id>/evidence.md` — produced at Phase 8 by EXECUTING
the scenario per its `evidence_type`, via `record-evidence` `[module]`, which
scaffolds the file with a canonical front-matter block so the conductor never
formats hashes by hand (gauntlet FM-2):

```yaml
---
row_id: r-US3-1
row_hash: <full sha256>
story_hash: <full sha256 of the row's US section>
conops_hash: <full sha256>
evidence_type: agent-walkthrough-transcript
produced_at: <RFC3339Z>
commit: <implementation git short hash>
worktree_clean: true
---
```

Exact keys, exact order, one block, duplicates rejected; distinct error codes
for missing vs malformed vs hash-mismatched front matter `[module]`.

Digest assembly refuses any row whose evidence file is missing, empty,
type-mismatched, or hash-mismatched (INV-4, TC-3.7). **Hash chain (INV-12,
revised for per-story binding — gauntlet FM-3):** evidence binds to
`row_hash` + `story_hash` (+ `conops_hash` recorded for audit). A row edit
orphans that row's evidence; a ConOps edit orphans evidence only for rows
whose STORY section changed. `reset-failed` renames the old file to
`evidence.md.invalidated-<ts>` — stale evidence cannot be silently re-accepted
(gauntlet FM-4); `assemble-digest` rejects evidence whose `produced_at`
predates the row's last reset. Evidence content hash is snapshotted per batch
(§6.2), so post-judgment evidence edits are detectable. Provenance minimums
for `agent-walkthrough-transcript`: real command/tool invocations with outputs
and timestamps embedded. The module verifies front matter, structure, and
hashes; it CANNOT prove execution authenticity — that integrity claim is
enforced by conductor discipline and checked at dogfood/spot-review (R2
honesty fix; threat model §1).

### 6.4 `system_validation.json` (gate input — US-8)

**Single artifact (OQ-1 provisionally resolved, gauntlet DD-3,
Jason-approved):** the served-code extract reads required dict fields and
lists no unknown-field rejection, so the gate is treated as TOLERATING extras.
One file: the gate's required shape plus our audit extras. The FIRST
implementation test (parity test against served code) confirms this; only if
it falsifies does the contingency in Appendix A (clean + audit sidecar)
activate.

```json
{
  "schema_version": "1.0",
  "kind": "system-validation",
  "module_version": "<as ledger>",
  "conops_hash": "<12-hex prefix of fresh sha256 of conops.md>",
  "ledger_hash": "<full sha256 of validation-rows.json at emission>",
  "rows": [
    {
      "conops_ref": "US-3",
      "scenario": "...",
      "oracle": "...",
      "result": "pass",
      "row_id": "r-US3-1",
      "evidence_type": "agent-walkthrough-transcript",
      "evidence_ref": "validation-evidence/r-US3-1/evidence.md",
      "evidence_hash": "<full sha256 of evidence bytes>",
      "judged_by": "jason",
      "judged_at": "<RFC3339Z>",
      "test_targets": []
    }
  ]
}
```

Result enum (ledger and artifact): `pass | fail | not-applicable` — the reply
token `na` maps to `not-applicable` at parse time `[module]` (gauntlet CB-12).
`judged_by` is derived: allowlisted Telegram sender → `jason`; terminal source
→ `jason` (asserted, §11). `test_targets` are ALWAYS preserved in projection
when present (anti-relabeling parity — gauntlet SEC-7). `ledger_hash` binds
the artifact to the exact ledger state it projects (gauntlet PARA-f2a004bc).
Row ordering = ledger order.

**The single N/A rule (R3 codex — resolves §4/§6.5 conflict):** `na` rows DO
appear in `system_validation.json` (the gate's result enum accepts
`not-applicable`; only `fail` hard-rejects) and do NOT count toward story
coverage — every story needs ≥1 `pass` row regardless. Close proceeds when
every active row is judged `pass` or `na` AND coverage holds.

### 6.5 Digest + reply grammar (US-6, US-7)

Digest: one digest BATCH per review sitting (G3), delivered as one or more
Telegram parts via `telegram-send`, formatted:

```
🥊📜 VALIDATION DIGEST <session> <digest-id> (<N> rows, part i/k)
[1] r-US3-1 (US-3)
  scenario: <one line>
  oracle: <one line>
  evidence: <type> — <evidence_summary> (file: <repo-relative path>)
  [prior: failed d-1 — <one-line reason>]        # delta digests only
...
Reply per row ("pass r-US3-1", "fail r-US3-1: <reason>", "na r-US3-1: <why>")
or pass everything ("pass all" / "those all look good"). "pass rest" passes
whatever you didn't explicitly judge.
```

(Project emoji framing kept per ecosystem convention — Jason ruling on
gauntlet OP-9.)

Digest content rules `[module]` (gauntlet SEC-4/OP-2):
- `evidence_summary` is conductor-written at evidence time, validated
  non-empty and length-bounded at digest assembly; it MUST be sufficient to
  judge from mobile — file paths are audit pointers, not reading material
  (TC-4.1's mobile-sufficiency criterion). The module never generates prose;
  it validates the conductor's summary exists (resolves the v4 "magic
  summary" gap, gauntlet ASSH-055e42e7).
- Secret lint: deny-pattern scan (key/token/bearer/password/env-var shapes)
  over the full digest text; a match BLOCKS assembly with the offending span
  indicated. Defense-in-depth on top of `[conductor]` content discipline.
- Row prose is escaped so it cannot imitate digest furniture (row labels,
  reply instructions).
- Narrative-evidence rows carry a `(narrative)` marker.
- Delta digests show a one-line prior-fail context per reset row.

**Multi-part rule (R1 codex, R2 mechanics, gauntlet RC-2):** budget is
**3500 UTF-8 bytes** per part (Telegram's raw limit is 4096 chars; byte
budget absorbs encoding — gauntlet OP-9). Split at row boundaries into parts
labeled `(part i/k)`; EVERY part carries the same `digest-id` and total row
count. Row-size lint at draft time (§3) guarantees no single row exceeds the
budget, so truncation is limited to evidence summaries (head + `…` + path
pointer); scenario and oracle are never truncated. `assemble-digest` writes
parts to `validation-digests/digest-<id>-part-<i>.txt` (NOT the evidence dir —
gauntlet OP-5), records their hashes in the batch, and prints the paths; the
conductor loops `telegram-send` over them — via stdin/`-` (the wrapper
supports it; never shell-interpolated message bodies — gauntlet
AUDT-109ec728) — with bounded retry (3 attempts, backoff) per part, recording
each outcome via `record-send`. Partial-send failure → `cancel-batch` + either
retry as a fresh batch or terminal fallback for the WHOLE batch — channels are
never mixed within one batch (gauntlet FM-6). Replies are validated against
the ledger's active batch; a reply referencing a non-active `digest-id` is
rejected as stale (replay protection, R2 codex). The batch records per-part
`message_id`s; a Telegram reply to ANY part binds to the batch (gauntlet US-5).

Reply grammar (deterministic, block-oriented — R1 gemini; revised per
gauntlet CB-9 + Jason's no-passwords ruling):

```
reply       := block+
block       := verdict (newline continuation)*
verdict     := per_row | bulk_pass | pass_rest
per_row     := ("pass" | "fail" | "na") SP row_id [":" SP text]
bulk_pass   := "pass all" | natural_alias
natural_alias := "those all look good" | "all look good" | "all good"
               | "looks good" | "lgtm"           # fixed list, module constant
pass_rest   := "pass rest"
row_id      := "r-US" digits "-" digits
```

Parse rules `[module]`:
- Verdict keywords and aliases are case-insensitive with whitespace
  normalized; row ids are exact-case. Aliases are matched as whole-line
  tokens from the fixed list above — the module matches strings; no LLM
  interprets the reply. (Alias list extension is a one-line module change +
  test.)
- `fail` and `na` REQUIRE non-empty justification (else re-prompt) — fail
  text seeds the remediation card (gauntlet FM-10). `pass` justification is
  optional; if present it is stored.
- Explicit per-row verdicts always apply BEFORE `pass all`/aliases/`pass rest`
  regardless of their textual order in the reply (gauntlet CB-9).
  `fail all`/`na all`/`fail rest`/`na rest` are invalid.
- Bulk verdicts scope to the OPEN batch's snapshot rows and require batch
  status `sent` (INV-16).
- ANY duplicate verdict for the same row in one reply is invalid (the v4
  "unless identical" loophole is removed).
- A continuation line that begins with a verdict keyword or row id is a parse
  error, not a justification — a typo'd verdict cannot be silently swallowed
  (gauntlet FM-12/CB-9).
- Unknown row ids, superseded row ids, and bare `US-n` targets are invalid.
  Replies to superseded rows get a rejection notice naming the replacement
  row (gauntlet BURN-f702791c).
- Partial replies are allowed with explicit row verdicts; unlisted rows
  remain unjudged and the batch stays open for further replies (one inbound
  message per `parse-reply` invocation; the conductor never aggregates
  messages — gauntlet US-5).
- `na` is accepted only from Jason and is row-level; a story's sole active
  row going N/A triggers an immediate warning (TC-3.5/3.6).
- Any unparseable or invalid block → ZERO mutations and a re-prompt quoting
  the offending text (truncated to 200 chars, framed as untrusted content —
  gauntlet SEC-4) (TC-3.2). Replies apply atomically or not at all.
- Idempotency: a reply whose `reply_ref` is already in the batch's
  `processed_reply_refs` is acknowledged but not re-applied; edited Telegram
  messages are ignored (first capture wins) (gauntlet RC-4).
- After a successful apply, the conductor sends a one-line confirmation of
  recorded judgments through the same channel `[conductor]` (gauntlet OP-2).

## 7. Component Design — `validation_emission.py`

Subcommands (all pure-local, no MCP — remote reads/writes are conductor
actions, named in §8). **Mutation ownership (R2 codex, expanded per gauntlet
CB-6/DD-1):** exactly eight subcommands mutate the ledger — `normalize-rows`,
`record-evidence` (writes the row's `evidence_summary`), `parse-reply`,
`assemble-digest`, `record-send`, `cancel-batch`, `reset-failed`,
`supersede-row`; each takes `validation-rows.json.lock` for the full
read-modify-write; everything else leaves ledger bytes unchanged.

**Lock + failure semantics (R3 convergent):** `filelock.FileLock` with a 10s
timeout (the skill's established TASK_LOCK pattern — same usage as
`gauntlet/persistence.py`, incl. its stale-lock handling); timeout → exit 3
`LEDGER_BUSY` with owner-pid/lock-age detail when readable. Crash recovery is
structural: the OS releases advisory locks on process death, and every
mutation is read→mutate→atomic-tmp+rename INSIDE the lock (crash-mid-mutation
leaves the previous LEDGER intact; crash safety is scoped to process death —
fsync durability against power loss is NOT claimed — gauntlet AUDT-1b597582;
side-effect files like digest parts may need regeneration after a crash, which
re-running the same subcommand does). A malformed/unparseable ledger → exit 3
`LEDGER_CORRUPT`, never auto-repaired — the corrupt bytes are copied aside to
`validation-rows.json.corrupt-<ts>` FIRST (forensics), then restore from git
(commit cadence below makes this lossless to the last batch close).
**Commit cadence `[conductor]`:** commit the ledger after every batch close
and before the MCP call.
**Exit codes (all subcommands):** 0 = ok; 2 = validation issues; 3 =
environment/IO/lock/corrupt. **Stdout envelope (exact, gauntlet FM-5):**
always one JSON object `{"status": "<ok|issues|reprompt|error>", "code":
"<stable code|null>", "issues": [{"code": "...", "row_id": "<id|null>",
"detail": "..."}], "data": {...}}`; human-readable warnings go to stderr only.
Global issues carry `row_id: null`.

- `derive-conops <manifest> [-o conops.md] [--force]` — §6.1; prints full +
  12-hex hashes and the `story_hashes` map.
- `normalize-rows <validation-rows.json> --conops <conops.md>` — NEW
  (gauntlet CB-7): stamps `row_hash`/`story_hash` for drafted rows, assigns
  schema fields, validates id format/uniqueness. The drafting bridge between
  conductor prose and the hashed ledger (mutating).
- `check-rows <validation-rows.json> --conops <conops.md> [--draft]` — §6.2
  STRUCTURAL constraints; `--conops` REQUIRED (INV-7 coverage); `--draft`
  relaxes coverage to advisory. Exit 2 with structured issues (codes mirror
  gate names where they overlap). Scope honesty (R2 gemini CRITICAL):
  validates syntax and structure ONLY; semantic intent is human-owned.
- `record-evidence <validation-rows.json> --row <row_id> --type <evidence_type> [--commit <hash>]`
  — NEW (gauntlet FM-2): scaffolds `validation-evidence/<row_id>/evidence.md`
  with the canonical front-matter block (hashes stamped by the module), then
  validates the completed file's structure on re-invocation. Records the
  conductor's `evidence_summary` into the ledger row (mutating — in the
  owner list above).
- `self-check <system_validation.json> --conops <conops.md> [--verification-ledger <path>]`
  — full mirror of the gate's reject classes: kind, conops_hash prefix-match
  (rejecting prefixes <12 hex), rows non-empty, per-row required fields,
  result enum, all-pass, anti-relabeling (strict subset per gate, EXTENDED
  locally to reject identical sets AND unjustified overlaps — INV-11), US
  coverage vs the ConOps regex (whole-file `\bUS-\d+\b`, exactly like the
  gate — the §6.1 heading rule is a derivation constraint, not the coverage
  rule). `--verification-ledger` is REQUIRED when verification artifacts
  exist for the session; absent input → `ANTI_RELABELING_UNCHECKED` warning
  status, never a silent pass (gauntlet SEC-7). Verdict parity with the gate
  is a tested invariant (TC-3.3); local extensions are strictly-stricter, so
  local-clean ⇒ gate-clean.
- `assemble-digest <validation-rows.json> --evidence-dir <dir>` — §6.5; PURE
  assembly (reset moved out — gauntlet DD-1); includes only `result == null`
  active rows (delta digest); refuses missing/empty/type-mismatched/
  hash-mismatched/reset-stale evidence (INV-4, INV-12); refuses while a
  non-terminal batch exists; snapshots conops/row/evidence hashes; writes
  part files + hashes; prints paths. Zero rows pending → exit 0,
  `{"status":"ok","code":"NOTHING_TO_DIGEST"}`.
- `record-send <validation-rows.json> --digest-id <d-N> --part <i> --result sent|failed [--message-id <id>]`
  — NEW (gauntlet RC-2): records per-part delivery; flips batch to `sent`
  when all parts sent.
- `cancel-batch <validation-rows.json> --digest-id <d-N> --reason <text>` —
  closes a non-terminal batch without judgments (audit-logged; rows return to
  the delta pool).
- `reset-failed <validation-rows.json> --row <row_id> --remediation-ref <card_id>`
  — NEW as standalone (gauntlet DD-1): moves a judged-fail row's judgment to
  history (append-only), nulls result/judgment, invalidates evidence
  (rename), repeatable per row. `--remediation-ref` REQUIRED; resolution of
  the card is verified by the CONDUCTOR via MCP before invoking — the module
  records the ref as a conductor-verified assertion (honest boundary,
  gauntlet FM-1).
- `supersede-row <validation-rows.json> --row <row_id> --reason <enum> --approver jason --approval-ref <ref> [--replacement-file <row.json>]`
  — NEW (gauntlet CB-6/CB-1): retires a row (full snapshot to `superseded`)
  and atomically installs the replacement row when provided (transactional
  refresh, no coverage gap). Legal from ANY row state; always requires
  `approval_ref`.
- `parse-reply <validation-rows.json> (--update-file <path> | --reply-file <path> | <reply-text>) --digest-id <d-N> --source telegram|terminal --reply-ref <ref> [--sender-id <id>]`
  — §6.5 grammar; OWNS the locked judgment mutation. **Telegram source
  (gauntlet SEC-1, Jason-ruled):** `--update-file` points at the RAW
  wake-listener update payload; the module extracts sender id, message id,
  and reply text itself — `--sender-id` is ignored for telegram (the
  conductor never transcribes identity). Sender checked against the
  registry's `allowed_sender_ids` (distinct from the chat id — gauntlet
  SEC-2; exact config: the project's telegram registry entry in the
  projects.yaml ecosystem, field names pinned at implementation against the
  real registry file); missing/malformed registry → telegram replies
  rejected with `ALLOWLIST_CONFIG_INVALID` (fail-closed config handling, no
  ceremony). Non-allowlisted sender → reply DISCARDED: exit 2
  `SENDER_NOT_ALLOWLISTED` + ledger security event (sender hashed) — never
  parsed, never mutating (INV-15). **Terminal source:** `--sender-id`
  optional (asserted identity); `reply_ref` must reference the
  AskUserQuestion transcript (§11). Stale/non-active digest, changed row
  hash, changed conops snapshot, duplicate `reply_ref` → rejected.
  `--reply-file`/stdin are the text-input paths (positional reply-text is
  test-only — multiline shell quoting is a footgun, gauntlet OP-6).
- `emit-system-validation <validation-rows.json> --conops <conops.md> [-o system_validation.json]`
  — machine projection of judged rows into §6.4 (single artifact; ledger
  untouched). Refuses: any active row unjudged or failed; provenance missing
  on any non-null result (INV-1); fresh-ConOps hash mismatch vs ledger →
  refusal scoped by story_hashes — only rows whose story section changed are
  invalidated (re-derive → supersede/re-draft affected rows → re-judge,
  per US-12; gauntlet FM-3); superseded/foreign/duplicate row ids rejected.
- `status <validation-rows.json>` — NEW (gauntlet FM-5): read-only; reports
  active batch + age (>48h flagged with cancel/reissue guidance), per-part
  send state, unjudged rows, judged summary, coverage state, blockers, and
  the next close-algorithm step.

The conductor (LLM) writes scenario/oracle/summary prose; the module never
generates prose and never judges — it validates shapes and mechanizes the
close (NG3).

## 8. Phase Wiring

- **Phase 7 (07-execution.md)**: after the execution plan is written and
  before `pipeline_load`, IF the card's `session_altitude == "system"` (read
  from card metadata via MCP, not only local session state — gauntlet US-2):
  run `derive-conops`, draft rows (per the §3 standard, with the
  good/rejected examples), `normalize-rows`, `check-rows` until clean.
  Artifacts commit with the execution plan; the committed ledger hash is
  recorded as `drafted_baseline_hash`. (Rows precede implementation —
  anti-hindsight; exposure of rows to implementation agents is an accepted
  tradeoff, ACK-7.)
- **Phase 8 (08-implementation.md)**: new close section "Validation leg
  (system altitude)" = the close algorithm below, verbatim.
- **Refresh interplay (US-12)**: ConOps/story changes during implementation
  require Jason's approval; after approval: manifest edit → re-derive (new
  hashes) → `supersede-row` affected rows (with replacements) → regenerate
  affected evidence only (per-story binding, INV-12/FM-3).

**Close algorithm (single normative ordering — gauntlet DD-2; every step
idempotent, re-entry starts at step 1):**

1. **Preflight** `[conductor]`: read `board_id` (projects.yaml), `card_id` +
   `session_id` (session detail file); `get_card_metadata` → verify session
   match, `session_altitude == system`, pipeline v5+ obligation; if
   `system_validation_complete` already true → skip to step 9. Verify clean
   worktree; verify `conops.md` and ledger exist; re-derive ConOps and
   compare hashes (OQ-3 RESOLVED: always re-derive at close entry) — story
   mismatch → refresh protocol (§8 above) before proceeding; compare ledger
   vs `drafted_baseline_hash` and surface any unexplained drift.
2. All verification obligations discharged; all task cards through review.
3. Evidence: for each active unjudged row, execute scenario → `record-evidence`
   (front matter incl. commit hash, clean worktree).
4. `assemble-digest`. `NOTHING_TO_DIGEST` + no failed rows → step 7.
   `NOTHING_TO_DIGEST` + failed rows present → remediation loop (step 6) —
   never emission (gauntlet CB-5).
5. Send parts (`telegram-send` via stdin, bounded retry) + `record-send` each;
   all sent → await replies; `parse-reply --update-file` per inbound message;
   apply confirmations; loop until batch closed. Bridge down → `cancel-batch`,
   terminal AskUserQuestion fallback for the whole batch (same grammar;
   detection = telegram-send nonzero exit/timeout — gauntlet US-6).
6. Any `fail`: if batch partially judged → `cancel-batch` remainder. Create
   remediation cards (MCP, payload per §4.7); after fixes: verify card
   resolution (MCP) → `reset-failed` per row → step 3.
7. `emit-system-validation` → `self-check` (ALWAYS, on the exact emitted file
   — including on re-entry; record the artifact's sha256).
8. Re-verify the artifact's sha256 unchanged (TOCTOU guard, gauntlet RC-1),
   then `mark_system_validation_complete` (explicit `board_id`). Transient
   MCP error → bounded retry; lost response → `get_card_metadata` to learn
   the true state (gauntlet FM-8).
9. `get_card_metadata` read-back confirms `system_validation_complete: true`
   → commit artifacts → proceed to Finalization advance. Post-close
   discovery of an erroneous validation: process-failure note + fizzy
   handoff item (write-once artifacts, OQ-4c).

**Row state machine (R2 codex — normative; revised per gauntlet CB-1/CB-4):**

| # | From | Event | To | Notes |
|---|------|-------|----|-------|
| S1 | drafted (`result:null`, no evidence) | scenario executed (`record-evidence`) | evidence-attached | front matter binds row/story/conops hashes + commit |
| S2 | evidence-attached | `assemble-digest` | digested (batch d-N) | only `result:null` active rows; batch snapshots hashes |
| S3 | digested | `parse-reply` pass | judged-pass | exits only via S7 |
| S4 | digested | `parse-reply` fail | judged-fail | justification required; remediation cards |
| S5 | digested | `parse-reply` na | judged-na | row-level; sole-row N/A warned at parse, blocks close (TC-3.6) |
| S6 | judged-fail | card resolved + `reset-failed` | needs-reexecution | fail → history (append-only); evidence invalidated (renamed); distinct from drafted — scenario unchanged, evidence required fresh |
| S6b | needs-reexecution | scenario re-executed (`record-evidence`) | evidence-attached | fresh evidence, fresh hashes |
| S7 | ANY state | `supersede-row` (human-approved) | superseded | full snapshot retained; excluded from digests/parsing (INV-10); transactional replacement allowed |
| S8 | digested | `cancel-batch` | evidence-attached | returns to delta pool; audit on batch |

No other transitions exist. `judgment_history` is never rewritten.

## 9. Invariants (machine-extractable)

- INV-1 `[module]`: a `result` value originates ONLY from a parsed Jason reply
  (or terminal AskUserQuestion fallback) — never computed, never defaulted.
  ENFORCEABLE FORM: `result == null ⟺ judgment == null`; every non-null
  result carries the full provenance block; `emit-system-validation` refuses
  violations.
- INV-2: `not-applicable` is row-level; story-level removal is a MANIFEST
  edit followed by re-derivation (never a ConOps-only edit).
- INV-3 `[module]`: row supersession requires human approval at every
  lifecycle point; audit entry mandatory with durable `approval_ref`
  (telegram:<chat>:<msg_id> | transcript:<session>:<turn> |
  decision:<RFC3339Z> — never a log line number).
- INV-4 `[module]`: no digest row without a non-empty executed-evidence
  artifact matching its declared `evidence_type` and hash chain.
- INV-5 `[conductor]`, checked by TC-3.3: `self-check` MUST pass immediately
  before EVERY `mark_system_validation_complete` call, on the exact file
  passed to it — including re-entries; the artifact hash is re-verified at
  call time (RC-1).
- INV-6 `[module]` lint + `[human]`: no oracle may reference test-suite
  success (NG5), including the synonym classes in §6.2.
- INV-7 `[module]`: every active ConOps US id has ≥1 active row at
  draft-complete and at emission (transitional states during transactional
  refresh are internal to `supersede-row`).
- INV-8 `[module]`: the ConOps hash in `system_validation.json` is computed
  at emission AFTER the close-entry re-derivation (OQ-3 resolved).
- INV-9 `[module]`: evidence provenance is row-bound and STORY-bound —
  produced after implementation, before digest assembly, under the current
  `row_hash` + `story_hash`; story edits or row supersession invalidate that
  story's/row's evidence only.
- INV-10 `[module]`: superseded rows are strictly excluded from digest
  assembly and reply parsing; stale replies referencing them get a
  replacement-row notice.
- INV-11 `[module]`: local anti-relabeling rejects validation `test_targets`
  that are a strict subset of, identical to, OR overlapping verification
  targets without per-row rationale (strictly stricter than the gate's
  strict-subset check — identical-set and superset loopholes closed locally;
  flagged to fizzy, OQ-4). `--verification-ledger` required when
  verification artifacts exist; absence yields a warning status, never a
  silent pass.
- INV-12 `[module]`: artifact hash chain — evidence front matter embeds
  `row_hash` + `story_hash` (+ `conops_hash` audit copy); `assemble-digest`
  verifies the chain and snapshots evidence content hashes;
  `emit-system-validation` re-verifies before projection.
- INV-13 `[module]`: judged-pass rows are immutable in place — never
  re-digested, re-judged, or edited; their ONLY exit is human-approved
  supersession (S7, legal from any state — consistent with the state machine
  as of v5).
- INV-14 `[module]`: `judgment_history` is append-only; resets move judgments
  into history, never erase them.
- INV-15 `[module]`: a Telegram-sourced judgment is applied only when the
  sender id EXTRACTED BY THE MODULE from the raw wake-listener payload
  matches the registry's `allowed_sender_ids`; the allowlist is never
  hardcoded; non-allowlisted replies are discarded with a structured code and
  a hashed-sender security event, never parsed into the ledger.
- INV-16 `[module]` (NEW): bulk verdicts (`pass all`, aliases, `pass rest`)
  apply only to a batch whose every part is recorded `sent` — undelivered
  rows cannot be bulk-approved.
- INV-17 `[module]` (NEW): reply application is idempotent by `reply_ref`;
  edited messages are not re-applied.

## 10. Error-Code Playbook (US-0, US-8)

Gate rejects (unchanged from v4):

| Gate reject | Conductor response |
|---|---|
| `SESSION_MISMATCH` | Should be unreachable post-preflight (close step 1 verifies ids); if hit, re-run preflight; never re-point at another session's card. |
| `VV_NOT_OBLIGATED_AT_ALTITUDE` | Card isn't system-altitude: investigate triage/altitude drift; do not force. |
| `VALIDATION_KIND_MISMATCH` | Artifact `kind` wrong — regenerate via module (hand-edited artifact suspected). |
| `VALIDATION_ARTIFACTS_INCOMPLETE` | Run `self-check`; fix reported issues (the gate may group several failures under this code — rely on local self-check granularity, not the gate's message). |
| `VV_LEDGER_HAS_FAILURES` | Should be unreachable (close algorithm blocks on fail rows); if hit, the remediation loop was bypassed — process failure note + remediate. |
| `VALIDATION_IS_RELABELED_VERIFICATION` | Rows re-point at verification fixtures — redraft scenarios from ConOps intent; check `test_targets` sets (INV-11 should have caught locally). |
| `SYSTEM_VALIDATION_MISSING` (at advance) | `mark_system_validation_complete` was never called for a system node — run the close algorithm. |
| `UNVALIDATED_USER_STORY` (at advance) | A ConOps US id lacks a passing row — self-check coverage should have caught it; re-run close with coverage fix. |

Local codes (NEW — gauntlet FM-5):

| Local code | Meaning | Response |
|---|---|---|
| `LEDGER_BUSY` (exit 3) | Lock held >10s | Check `status`/live processes; retry once after 30s; stale lock → see filelock stale handling. |
| `LEDGER_CORRUPT` (exit 3) | Unparseable ledger | Corrupt bytes auto-copied aside; restore from git (commit cadence bounds loss); replay from quarantine + Telegram transcript if needed. |
| `NOTHING_TO_DIGEST` (exit 0) | No unjudged active rows | Close algorithm step 4 routing: failed rows → remediation; else → emission. |
| `SENDER_NOT_ALLOWLISTED` (exit 2) | Telegram reply from unknown sender | Security event logged; if Jason's real reply was discarded, fix the registry allowlist and re-feed the update file. |
| `ALLOWLIST_CONFIG_INVALID` (exit 2) | Registry missing/malformed | Fix the project telegram registry entry; telegram parsing is blocked until valid. |
| `STALE_DIGEST` / `STALE_ROW_HASH` / `STALE_CONOPS` (exit 2) | Reply references non-active batch or changed content | Re-digest; notify Jason which digest is current. |
| `REPROMPT_REQUIRED` (exit 2) | Invalid/partial reply blocks | Send the module's re-prompt text (quoted offending span) to the same channel. |
| `EVIDENCE_MISSING` / `EVIDENCE_MALFORMED` / `EVIDENCE_HASH_MISMATCH` / `EVIDENCE_STALE` (exit 2) | Evidence chain broken | Re-execute scenario via `record-evidence` for the named row. |
| `REFRESH_DISALLOWED` (exit 2) | Supersession reason not in enum / approval missing | Get the human decision; use the allowed reason enum. |
| `ROW_OVER_BUDGET` (exit 2) | Row exceeds digest byte budget | Redraft the row tighter (drafting error). |
| `ANTI_RELABELING_UNCHECKED` (warning) | No verification ledger supplied | Supply `--verification-ledger`; do not close on a warning when verification artifacts exist. |

## 11. Security / Operability

- Threat model: §1. Single-writer rule for validation artifacts `[conductor]`.
- Inbound trust boundary: INV-15 — the module reads the raw wake-listener
  payload itself; the conductor never types identity flags for telegram
  sources. The registry distinguishes `chat_id` (listener scoping) from
  `allowed_sender_ids` (judgment authority). ASSUMPTION-2 (§13) pins the
  listener payload shape at implementation.
- Terminal fallback: weaker boundary, documented as such — asserted identity
  on a single-user machine; `reply_ref` must cite the AskUserQuestion
  transcript; a negative test covers terminal-source abuse (TC-G7). Bridge
  down → terminal for the WHOLE batch (same grammar, same INV-1 provenance);
  judgments are never deferred to an agent because the bridge is down.
- Digest hygiene `[module]`: secret deny-pattern lint blocks assembly;
  repo-relative paths only; row prose escaped; re-prompts quote untrusted
  text truncated and framed. Digest content goes through Telegram (external
  service): scenarios, oracles, and summaries only — evidence files stay
  local, referenced by path (audit pointers).
- Audit: the ledger is the audit trail — provenance blocks, append-only
  history, full-snapshot supersession, hashed-sender security events,
  per-part send records, batch hash snapshots, `module_version` stamps, and
  `ledger_hash` binding on the emitted artifact. "What did Jason see and
  judge?" is answerable from the ledger alone.
- All JSON writes atomic (tmp+rename) inside the lock, consistent with the
  skill-wide rule; crash-safety scope per §7.

## 12. Testing Strategy

`tests-pseudo.md` is canonical (Data-Strategy-annotated; gauntlet additions
carry `Source: gauntlet-2026-06-11` attribution). Concrete tests land in
`scripts/tests/test_validation_emission.py`. **Markers (gauntlet OP-10):**
`deterministic` (CI-runnable: parser, hashes, lint, state machine, gate-class
mirror, lock/corrupt/crash fixtures) vs `dogfood` (requires Jason, real
Telegram, real MCP — run during this session's own validation leg, recorded
not CI-gated). Verification = pytest over the module (TC-1.x, TC-2.x,
TC-3.2/3.3/3.5/3.6, TC-G*). Validation of THIS session = running the process
on itself (TC-0.1, TC-3.1, TC-3.4/3.7, TC-4.1) — disjoint evidence surfaces
by construction (T2); bootstrap circularity is a named residual risk
(dogfooding the process on itself is supportive, not independent, evidence —
ACK-4).

**Dogfood validation is NOT satisfied by gate acceptance alone (R1 codex):**
TC-4.1 requires BOTH the real gate accepting on first call AND Jason's
intent-level acceptance of the process experience — bootstrap usable without
reading fizzy source, digest sufficient to judge from mobile (summaries
self-contained — §6.5), reply/re-prompt behavior unambiguous, remediation
guidance actionable on a fail. Dogfood metrics also record local retries,
re-prompts, and re-emissions before the first MCP call (a clean "first call"
must not hide local churn — gauntlet OP-10), plus the <30 min bootstrap
timing (§3).

## 13. Open Questions & Assumptions

- OQ-1: PROVISIONALLY RESOLVED (gauntlet DD-3, Jason-approved) — the gate is
  treated as tolerating unknown row fields (served-code extract reads dict
  fields; no unknown-field rejection present). First implementation test
  verifies against served code; falsification activates Appendix A.
- OQ-3: RESOLVED — `derive-conops` re-runs at Phase 8 close entry, always;
  story-level hash comparison scopes any invalidation (close algorithm
  step 1).
- OQ-4 (fizzy handoff, not blocking): (a) confirm empty-set anti-relabeling
  pass is intentional (`pipeline.py` ~:9226 comment says yes); (b) report the
  identical-set/superset loophole — INV-11 closes both locally; (c) NEW:
  write-once `system_validation_artifacts` have no correction path after an
  erroneous close — request guidance (local policy meanwhile: process-failure
  note + handoff item).
- ASSUMPTION-2 (gauntlet SEC-1/US-1): the wake-listener update payload
  exposes sender id and message id per inbound message. Verified during
  implementation by reading the listener source and capturing one real
  payload (~10 min); `parse-reply --update-file` parsing is written against
  the verified shape. (Ordinary implementation task — no blocking ceremony.)
- ASSUMPTION-3: `get_card_metadata` exposes `session_altitude` and
  `system_validation_complete` (used by close steps 1/9) — verified at
  implementation alongside ASSUMPTION-2; both are existing fizzy tools (NG4
  intact).
- Contract drift: the served-code extract is dated 2026-06-11 (fizzy working
  tree). `self-check` parity is pinned to it; if fizzy's gate changes, parity
  tests fail → re-extract the contract and re-pin (documented drift
  protocol; runtime contract-fingerprint checking is NOT claimed).

## Appendix A — Contingency: dual-artifact protocol (inactive)

Activates ONLY if the OQ-1 parity test shows the gate rejecting unknown row
fields. Then: `system_validation.json` becomes the gate-clean projection
(top-level `kind` + `conops_hash`; rows with ONLY `conops_ref`, `scenario`,
`oracle`, `result`, optional `test_targets` — preserved when present), and
`system_validation.audit.json` (same `schema_version` discipline) carries the
full §6.4 shape. Both produced by `emit-system-validation` in one invocation
from the same ledger read; identical `conops_hash`, `ledger_hash`, and row
ordering; `self-check` runs on the EXACT file passed to the MCP call;
`row_id` is the correlation key. While inactive, no audit sidecar exists —
the ledger is the rich record (split-brain avoided, gauntlet DD-3).
