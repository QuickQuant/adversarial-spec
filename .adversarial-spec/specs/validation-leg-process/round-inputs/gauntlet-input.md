# ADVERSARY BRIEFING — Gauntlet: Validation-Leg Production Process

> This briefing contains codebase context extracted for your review.
> Use it to validate the spec's claims against what actually exists.
> Extraction: 2026-06-11T14:51:28Z | Git: f198887 | Branch: main
> Session altitude: SYSTEM (full intensity). Spec under attack: spec-draft-v4
> (debate-converged after 4 rounds: codex + gemini + claude).
>
> ADVERSARY ROUTING — read your lens's emphasis first:
> - paranoid_security (PARA): §"Security and Trust Boundaries" concern in the
>   Target Architecture below; the sender-allowlist trust boundary (INV-A4,
>   spec INV-15); Telegram inbound reply path; terminal-source assertion.
> - burned_oncall (BURN): lock/crash semantics (INV-A1/A2/A3), idempotent
>   close (INV-A6), remediation loop (spec §8, S4/S6), the Test Pseudocode
>   section (boundary/error cases), error-code playbook (spec §10).
> - pedantic_nitpicker (PEDA): hash canonicalization (spec §6.2), reply
>   grammar (spec §6.5), JSON shapes (§6.2/§6.4), the FULL Test Pseudocode
>   section, the fixed fizzy contract extract (exact field names/enums).
> - asshole_loner (ASSH): row state machine (spec §8), mutation ownership,
>   the §6.4 ASSUMPTION-1 dual-file protocol, abstraction/contract seams
>   between module, conductor LLM, and gate.
> - assumption_auditor (AUDT): the fizzy contract extract below is the ONLY
>   verified external contract — every other claim about fizzy gate behavior,
>   Telegram bridge behavior, and wake-listener behavior is an assumption to
>   audit. Spec OQ-1/OQ-3/OQ-4 are known-open assumptions.
> - information_flow_auditor (FLOW): the §5 system architecture flow diagram;
>   artifact handoffs (manifest → conops → rows → evidence → digest → reply →
>   gate artifact → MCP call); what each step consumes/produces; where data
>   can be lost or duplicated across the Phase 7 → Phase 8 time gap.
> - architect (ARCH): the FULL Target Architecture document below (framework
>   profile, surfaces, concern×surface matrix, INV-A1..A7, altitude tree);
>   module boundary of validation_emission.py vs phase docs vs fizzy.

## Base Context (all adversaries)

**System being extended:** adversarial-spec — a Claude Code skill for
iterative spec development through multi-model debate. Python 3.14+, uv,
pytest, filelock 3.16.1 (pinned). CLI-driven, no daemon. Key existing
patterns this spec builds on:
- `mini_spec_emission.py` pattern: doc-driven process, code-checked shapes.
- Skill-wide atomic JSON writes (tmp+rename) and filelock TASK_LOCK pattern.
- Phase docs (`phases/02-roadmap.md`, `07-execution.md`, `08-implementation.md`)
  drive conductor behavior; scripts enforce machine-checkable shapes.
- Telegram bridge: `~/.claude/bin/telegram-send <project> "<msg>"` outbound;
  inbound replies land via a wake-listener that tails per-project update
  files scoped to the project bot's chat. The bridge wrapper does NO message
  splitting (raw Telegram 4096-char limit applies).
- Fizzy pipeline MCP is the task/board system; the validation gate contract
  is FIXED on the fizzy side (extract below) — this spec is skill-side only.

**Blast zone (files this spec touches):**
- `skills/adversarial-spec/scripts/validation_emission.py` — NEW module (all
  machine-checkable shapes; subcommands in spec §7)
- `skills/adversarial-spec/scripts/tests/test_validation_emission.py` — NEW
- `skills/adversarial-spec/phases/07-execution.md` — new "Validation leg" section
- `skills/adversarial-spec/phases/08-implementation.md` — new close section
- `skills/adversarial-spec/phases/02-roadmap.md` — already emits US-n ids (done)

**Recent git activity in blast zone (last 5):**
- a3c0d1d refactor: remove mcp_tasks package — the retired Tasks MCP server
- 55071ba refactor: delete task_manager.py — retired Tasks MCP client
- 66b45f4 refactor(debate): delete task_manager glue — Tasks MCP retirement
- da512d0 docs(execution): depth-triage Stage 1 shipped — retire fallback notes
- cf4d495 fix(execution): emit acceptance_criteria array per task

## Known Gaps

- No production metrics or monitoring exist — this is a single-operator local
  CLI skill; "operability" means conductor-LLM-followable playbooks.
- Context Readiness Audit inventory was not persisted from debate; this
  briefing was assembled fresh (lightweight re-extraction at HEAD f198887).
- Pre-gauntlet COMP pass skipped: the spec introduces no new external SDKs.
  The two external surfaces are the existing Telegram bridge (behavior pinned
  in spec Appendix references + OQ-2 resolved) and the fizzy gate (served-code
  extract included below — treat THAT as ground truth, not training data).
- Architecture corpus (.architecture/) is stale at 9ca3ccd vs HEAD f198887
  (52 commits drift; it still documents the deleted mcp_tasks package). The
  Target Architecture doc below was produced fresh at Phase 4 and is current.
- Dynamic scope-aware adversary prompts not used this run (static personas +
  this briefing). Scope classification for your calibration:
  exposure=local-only, domain=cli-tool, risk_signals=external-integrations
  (Telegram inbound replies cross a trust boundary; no auth/PII/payments).

---

# TARGET ARCHITECTURE (Phase 4, published, fingerprint 48a3ed59fb64)

<!-- target-architecture.md inlined below -->
---
schema_version: "1.0"
spec_slug: "validation-leg-process"
phase_mode: "lightweight"
context_mode: "brownfield_feature"
framework: "Claude Code skill — Python 3.14 scripts (uv) + markdown phase docs"
framework_version: "Python 3.14 / uv / filelock 3.16.1"
surfaces: ["cli_command", "outbound_integration"]
roadmap_path: ".adversarial-spec/specs/validation-leg-process/roadmap/manifest.json"
tests_pseudo_path: ".adversarial-spec/specs/validation-leg-process/tests-pseudo.md"
architecture_fingerprint: "48a3ed59fb6478c66ec760b924ab04fdde305de53ad3cd58d75c808536806857"
---

# Target Architecture: Validation-Leg Production Process

> Phase 4, lightweight mode (roadmap `architecture_impact.verdict: extends_existing`).
> Spec input: `spec-draft-v4.md` (debate-converged R4). Context: brownfield_feature.
> Blast zone: `skills/adversarial-spec/scripts/` (new `validation_emission.py`),
> phase docs `02-roadmap.md` (US-id emission, already done), `07-execution.md`,
> `08-implementation.md`, plus `scripts/tests/test_validation_emission.py`.

## Overview

The spec adds a validation production line to the skill: ConOps derivation →
validation-row drafting (Phase 7) → scenario execution + evidence (Phase 8) →
batched Telegram judgment → gate artifact emission → `mark_system_validation_complete`.
Architecturally this **extends the existing scripts layer** with one new module
following the `mini_spec_emission.py` pattern (doc-driven process, code-checked
shapes). No new layer, no new middleware, no fizzy-side changes (NG1, NG4).

The load-bearing architectural decisions were converged in debate and are
restated here as enforceable commitments rather than re-litigated: single
stateful ledger (no split-brain digest state), strict mutation ownership under
filelock, deterministic hash canonicalization, sender-allowlist trust boundary,
and an idempotent close path.

## Goals and Non-Goals (architecture view)

- G1 (V-closeable process) → the architecture must make the close path
  *mechanical*: every machine-checkable shape lives in `validation_emission.py`;
  the conductor LLM contributes prose only.
- G2/NG3/NG5 (intent judgment, human-only) → the module never generates
  prose and never judges; oracles are linted structurally, judged semantically
  by humans (two-layer enforcement).
- G3 (one-digest cost) → batching, multi-part splitting, and delta digests are
  module responsibilities, not conductor improvisation.
- G4/G5 (hash-bound freshness, auditable refresh) → hash chain (`conops_hash`
  → `row_hash` → evidence headers) is the freshness mechanism end-to-end.
- NG1/NG4 → no new MCP tools, lanes, or servers; the agent makes the existing
  MCP call; the module is pure-local.

## Framework Profile

```json
{
  "profile_type": "single",
  "category": "cli",
  "framework": "Claude Code skill: Python scripts under skills/adversarial-spec/scripts/",
  "framework_version": "Python 3.14+, uv-run, filelock 3.16.1 (pinned skill-wide)",
  "runtime": "python",
  "deployment_target": "serverful",
  "enabled_features": ["filelock TASK_LOCK pattern", "atomic tmp+rename writes", "structured exit codes"],
  "subprofiles": {
    "rendering_model": "N/A",
    "data_access_model": "direct file I/O — JSON ledger + markdown artifacts under .adversarial-spec/specs/<slug>/",
    "mutation_model": "lock-guarded read→mutate→atomic-rename, owned by 3 named subcommands",
    "cache_model": "N/A — no caching; freshness via content hashes",
    "error_model": "exit 0/2/3 with structured {code, row_id, detail} issues on stdout (exit 2)"
  },
  "enforcement_model": "cli_command: module-enforced shape validation (check-rows/self-check) mirroring the fizzy gate; outbound_integration: sender-id allowlist on inbound replies, content discipline on outbound digests"
}
```

## Applicable Execution Surfaces

| surface_id | What it is here |
|---|---|
| `cli_command` | `validation_emission.py` subcommands: `derive-conops`, `check-rows`, `self-check`, `assemble-digest`, `cancel-batch`, `parse-reply`, `emit-system-validation`. All pure-local, no MCP. |
| `outbound_integration` | Telegram digest send (`telegram-send` loop over part files) and inbound reply ingestion (wake listener → `parse-reply`); the agent-side `mark_system_validation_complete` MCP call (fizzy contract is fixed, NG1). |

Category-native rule satisfied: `cli` category ⇒ `cli_command` surface present.
No web surfaces apply — there is no server, no request path, no client runtime.

## Altitude Tree (V-model input for Phase 7)

Root altitude: **system** (set at triage, card 5604).

| node | altitude | parent | decomposes_into | left-arm definition artifact | right-arm obligations |
|---|---|---|---|---|---|
| validation-leg-process (root) | system | — | emission-toolchain, phase-wiring | spec-draft-v4.md (finalized) | component + subsystem + system verification; system validation via THIS process (US-10 dogfood) |
| emission-toolchain | subsystem | root | validation_emission.py, test suite | §6–§7 artifact contracts + component design | component + subsystem verification |
| validation_emission.py | component | emission-toolchain | — | §7 subcommand contracts | component verification (pytest: TC-1.x, TC-2.x, TC-3.2/3.3/3.5/3.6) |
| test_validation_emission.py | component | emission-toolchain | — | §12 testing strategy | component verification |
| phase-wiring (07/08 docs) | component | root | — | §8 phase wiring | component verification (doc review: validation-leg sections present, good/rejected row examples included) |

`depends_on` (scheduling only): phase-wiring depends_on validation_emission.py
(docs reference real subcommand names/flags); dogfood close (US-10) depends_on
everything. No altitude inversion: all edges point strictly downward.

## Concern Assessments (in-scope only — lightweight)

### Concern: Source of Truth and Concurrency
**Decision:** `validation-rows.json` is the single stateful ledger for all row
state through the entire lifecycle; `system_validation.json` is a write-only
projection (`emit-system-validation`), never hand-edited, never read back as
state.
**Surfaces:** cli_command
**Goals/NFRs:** G1, G2 | **User stories:** US-3, US-8
**Framework primitive:** `filelock.FileLock` (10s timeout, exit 3 `LEDGER_BUSY`)
+ atomic tmp+rename inside the lock — the skill's established TASK_LOCK pattern.
**Default status:** accepted (pattern already proven in this codebase)
**Why sufficient:** single-user machine, advisory locks released by OS on
process death; no partial writes possible because mutation is read→mutate→rename
inside the lock. A malformed ledger is never auto-repaired (exit 3
`LEDGER_CORRUPT`, restore from git).
**Alternative considered:** separate digest-state file — rejected in debate
(R2 convergent CRITICAL: split-brain).
**Failure mode prevented:** judgments half-applied or duplicated across files;
crash mid-write corrupting the ledger.
**Invariant refs:** INV-A1, INV-A2 | **Test hook:** TC-INV-A1, TC-INV-A2

### Concern: Enforcement Points
**Decision:** exactly three subcommands may mutate the ledger (`parse-reply`,
`assemble-digest`, `cancel-batch`); everything else is read-only. The gate's
reject classes are mirrored locally by `self-check`, which is strictly stricter
(identical-set anti-relabeling extension) so local-clean ⇒ gate-clean, and MUST
pass on the exact file passed to the MCP call.
**Surfaces:** cli_command, outbound_integration
**Goals/NFRs:** G1 | **User stories:** US-7, US-8, US-11
**Framework primitive:** subcommand dispatch in one module; no shared mutable
state outside the ledger file.
**Default status:** custom pattern (mirrors fizzy gate semantics by design)
**Why sufficient:** a developer (or LLM) cannot "add an endpoint and skip
enforcement" — there is no API surface other than the module's argparse
dispatch, and the close step is documented to run `self-check` immediately
before the MCP call (INV-5 of the spec).
**Bypass risk:** conductor hand-writing `system_validation.json` — explicitly
forbidden; `emit-system-validation` is the only producer.
**Alternative considered:** enforcing via fizzy-side checks — rejected (NG1).
**Failure mode prevented:** gate-reject discoveries at close time; relabeled
verification slipping through.
**Invariant refs:** INV-A2, INV-A5 | **Test hook:** TC-INV-A2, TC-INV-A5

### Concern: Error Handling Pipeline
**Decision:** uniform exit-code contract across all subcommands: 0 ok / 2
validation issues (structured `{code, row_id, detail}` on stdout) / 3
environment-IO-lock-corrupt. Reply-parse failures raise `RepromptRequired`
with ZERO ledger mutations — replies apply atomically or not at all.
**Surfaces:** cli_command
**Goals/NFRs:** G1, G3 | **User stories:** US-7, US-0
**Framework primitive:** Python exceptions mapped to exit codes at the CLI
boundary; issue codes mirror gate names where they overlap.
**Default status:** accepted (skill-wide convention)
**Why sufficient:** the conductor is an LLM following the error-code playbook
(spec §10) — structured machine-readable issues are what make the playbook
mechanical.
**Alternative considered:** free-text errors — rejected; playbook mapping
requires stable codes.
**Failure mode prevented:** half-applied judgments; conductor improvising on
ambiguous failure output.
**Invariant refs:** INV-A3 | **Test hook:** TC-INV-A3

### Concern: Validation Boundaries
**Decision:** two-layer oracle quality enforcement — Layer 1: drafting-time
canonical `iff` form in the Phase 7 doc (LLM constraint); Layer 2: structural
lint in `check-rows` (banned phrases, vague terminals, literal `iff`, named
US-n). `check-rows` validates syntax/structure ONLY; semantic intent is judged
by humans (conductor review + Jason). This scope honesty is documented, not
papered over.
**Surfaces:** cli_command
**Goals/NFRs:** G2 | **User stories:** US-4, US-3
**Framework primitive:** regex/string lint + JSON schema-shape checks in the module.
**Default status:** custom pattern
**Why sufficient:** the gate itself only checks shapes; our structural layer is
already stricter, and the human layers own semantics by design (NG3).
**Alternative considered:** LLM-judged oracle quality — rejected (R1 gemini
realism; non-deterministic enforcement is no enforcement).
**Failure mode prevented:** checkbox-prose oracles ("tests pass") reaching the
digest.
**Invariant refs:** INV-A5 | **Test hook:** TC-INV-A5 (negative cases)

### Concern: Security and Trust Boundaries
**Decision:** inbound trust boundary at `parse-reply`: `--source telegram`
requires `--sender-id` checked against the project's configured Telegram
allowlist (from the telegram registry — never hardcoded); non-allowlisted
replies are DISCARDED with a logged warning (no re-prompt, no mutation).
Outbound: digest text carries scenarios/oracles/evidence summaries only —
no secrets, no tokens; evidence files stay local, referenced by path.
**Surfaces:** outbound_integration
**Goals/NFRs:** G3 | **User stories:** US-6, US-7
**Framework primitive:** wake-listener already scopes updates to the project
bot's chat; allowlist is defense-in-depth on top.
**Default status:** default overridden (listener scoping alone was the default;
debate added the explicit allowlist — R3 convergent CRITICAL)
**Why insufficient default:** the listener scopes by chat, not by sender;
group-chat or forwarded-message edge cases could inject judgments.
**Alternative considered:** trusting the bridge wrapper — rejected R3.
**Failure mode prevented:** a non-Jason sender minting validation judgments
(INV-1/INV-15 of the spec).
**Invariant refs:** INV-A4 | **Test hook:** TC-INV-A4

### Concern: Integration Boundaries and Delivery Semantics
**Decision:** digest batches are the delivery unit: exactly one open batch at a
time; batches snapshot row hashes at open; stale replies (non-active digest-id
or changed row hash) are rejected; multi-part splitting at 3500 chars/part at
row boundaries, every part labeled with digest-id and total count. The Phase 8
close is idempotent end-to-end: re-entry skips completed steps
(`NOTHING_TO_DIGEST` → existing clean emission → card-metadata check before the
MCP call). Telegram down → terminal AskUserQuestion fallback, same grammar,
same provenance requirements.
**Surfaces:** outbound_integration, cli_command
**Goals/NFRs:** G3, G1 | **User stories:** US-6, US-7, US-8, US-9, US-13
**Framework primitive:** `telegram-send` looped over module-written part files;
ledger-recorded `digest_batches[]` (no separate digest-state file).
**Default status:** custom pattern
**Why sufficient:** at-least-once human messaging with replay protection at the
parse layer gives effectively exactly-once judgment application; idempotent
close makes crash recovery a non-event.
**Alternative considered:** bridge-side splitting — rejected (OQ-2 resolved:
wrapper does no size handling).
**Failure mode prevented:** replayed/stale replies mutating current rows;
double-close; lost judgments on crash between emission and MCP call.
**Invariant refs:** INV-A6 | **Test hook:** TC-INV-A6

### Concern: Observability
**Decision:** the audit trail IS the ledger: `judgment` provenance block
required on every non-null result (INV-1), `judgment_history` append-only,
supersessions carry `approval_ref` + timestamp + replacement id, batch
cancellations audit-logged. Session-level events land in the existing
decisions log / journey log. No new observability infra.
**Surfaces:** cli_command
**Goals/NFRs:** G5 | **User stories:** US-12
**Framework primitive:** existing decisions.log + journey.log conventions;
ledger-internal history fields.
**Default status:** accepted
**Why sufficient:** single-user, low-volume; the question "who judged what,
when, from which digest" is answerable from the ledger alone (2am test:
read the ledger).
**Failure mode prevented:** hindsight rewriting of judgments or scenarios
without trace.
**Invariant refs:** INV-A7 | **Test hook:** TC-INV-A7

### Concern: Configuration Management
**Decision:** all external identifiers come from existing config surfaces:
Telegram allowlist/chat-id from the project telegram registry (projects.yaml
ecosystem), board/card ids from session state. Constants that pin contract
behavior (hash prefix lengths 12, part budget 3500, lock timeout 10s) are
module constants pinned by tests, not config — they encode the fixed fizzy
contract and Telegram limit, and varying them per-project would break parity.
**Surfaces:** cli_command, outbound_integration
**Goals/NFRs:** G1 | **User stories:** US-0
**Default status:** accepted
**Failure mode prevented:** hardcoded chat ids; config drift breaking gate
parity.
**Invariant refs:** INV-A4 (allowlist sourcing) | **Test hook:** TC-INV-A4

## Concern x Surface Matrix (lightweight — compact)

| Concern | cli_command | outbound_integration |
|---|---|---|
| SoT/Concurrency | ledger + filelock + atomic rename; owner: module (INV-A1) | N/A — no remote state |
| Enforcement | 3 mutating subcommands only; self-check before MCP (INV-A2, INV-A5) | gate contract conformance only (NG1) |
| Error handling | exit 0/2/3, structured issues; zero-mutation re-prompt (INV-A3) | telegram-send failure → log + terminal fallback |
| Validation | check-rows structural lint; human semantic layers (INV-A5) | N/A |
| Security | terminal source asserts local operator | sender allowlist, discard non-allowlisted (INV-A4); no secrets in digests |
| Delivery | batch lifecycle in ledger | one open batch; stale-reply rejection; idempotent close (INV-A6) |
| Observability | provenance blocks, append-only history (INV-A7) | reply_ref ties judgment to message id |
| Config | pinned contract constants | registry-sourced allowlist (INV-A4) |

Bypass risks: hand-edited `system_validation.json` (caught: emit-only producer +
self-check on exact file); conductor skipping self-check (caught: Phase 8 doc
close sequence + TC-3.3 parity test); direct ledger edits outside the module
(residual — single-user discipline, flagged in dogfood spot-review per R2
honesty fix).

## Architectural Invariants

INV-A1: [category:sot] `validation-rows.json` is the sole authoritative store of
row state; `system_validation.json` is a write-only projection produced
exclusively by `emit-system-validation`; no other artifact or process stores or
transcribes judgments.

INV-A2: [category:enforcement] Only `parse-reply`, `assemble-digest`, and
`cancel-batch` mutate the ledger; each acquires `validation-rows.json.lock` for
the full read-modify-write and writes via atomic tmp+rename; all other
subcommands are read-only.

INV-A3: [category:error_handling] Every subcommand terminates with exit 0, 2
(structured `{code,row_id,detail}` issues), or 3; an invalid or partially valid
reply produces ZERO ledger mutations and a re-prompt quoting the offending text.

INV-A4: [category:security] A Telegram-sourced judgment is applied only when its
sender id matches the project's registry-configured allowlist; the allowlist is
never hardcoded; non-allowlisted replies are discarded and logged, never parsed
into the ledger.

INV-A5: [category:validation] `self-check` mirrors every gate reject class,
is strictly stricter than the gate (identical-set anti-relabeling), and passes
on the exact bytes passed to `mark_system_validation_complete` immediately
before every call; gate/local verdict parity is a pinned test.

INV-A6: [category:integration] At most one digest batch is open at any time;
batches snapshot row hashes at open; replies referencing a non-active digest-id
or a changed row hash are rejected; the Phase 8 close sequence is idempotent —
re-entry at any step skips already-completed work without re-judging.

INV-A7: [category:observability] Every non-null `result` carries a full
provenance block; `judgment_history` is append-only; supersessions and batch
cancellations carry audit fields including `approval_ref`/reason; no history is
ever rewritten.

(Spec-level INV-1..INV-15 in `spec-draft-v4.md` §9 remain normative; INV-A*
are the architecture-level commitments that make them enforceable.)

## Middleware Candidates

None. The roadmap's `architecture_impact` declares `new_middleware: []` and NG4
forbids new shared middleware; `validation_emission.py` is a project-local
script (single consumer, single surface owner), not reusable middleware. See
`middleware-candidates.json` (empty, advisory).

## Dry-run Summary

Lightweight scope: 1 highest-risk archetype per applicable surface.
- `cli_command`: trace the `parse-reply` mutation path (reply text → grammar →
  sender allowlist → batch/hash staleness checks → lock → atomic apply →
  provenance write) against INV-A2/A3/A4/A6.
- `outbound_integration`: trace the digest batch lifecycle (assemble → part
  files → telegram-send loop → reply → close/cancel → delta re-entry) against
  INV-A6 and the idempotent-close claims.

Results recorded in `dry-run-results.json` after draft review.

## Open Questions

- OQ-P4-1: none architecture-blocking. Spec OQ-1 (gate tolerance of unknown row
  fields) and OQ-3 (re-derive cadence) are implementation-time questions with
  resolution protocols already specified in the spec; OQ-4 is a fizzy handoff.

---

# FIXED DOWNSTREAM CONTRACT (served-code extract — ground truth)

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

---

# TEST PSEUDOCODE (canonical, Data-Strategy-annotated) — primary lens: PEDA, BURN

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
       scenario, oracle, conops_ref, or evidence_type change; 12 hex chars
assert: hash(NFD variant) == hash(NFC variant)
assert: hash(rationale-edited) == hash(original)
assert: hash(oracle-edited) != hash(original); len == 12
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
when:  assemble-digest --reset-failed A --remediation-ref <cardA> --reset-failed C
       --remediation-ref <cardC> runs, then a new digest is assembled
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
when: parse-reply runs with --source telegram --sender-id <non-allowlisted>
then: reply DISCARDED with logged warning; ledger unchanged; no re-prompt
assert (positive): identical reply with allowlisted sender-id applies normally
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
assert: --reset-failed moves the prior fail judgment into judgment_history (original entry intact, byte-compared) and requires a paired --remediation-ref
assert (negative): a superseded entry missing approval_ref is rejected by check-rows
Schema refs: validation-rows.json ledger (§6.2), system_validation.json (§6.4), fizzy-validation-contract.md
<!-- P4_INVARIANT_TESTS_END -->

---

# SPECIFICATION TO REVIEW

# Spec: Validation-Leg Production Process (v4)

> Session `adv-spec-202606110339-validation-leg-process` | card 5604 | altitude: system
> Depth: technical | Roadmap: `roadmap/manifest.json` (14 stories US-0..US-13, confirmed)
> Fixed downstream contract: `fizzy-validation-contract.md` (served-code extract)
> v4: R3 synthesis — hash canonicalization, sender verification, lock/exit-code
> semantics, batch lifecycle, N/A close rule unified, close idempotency.
> Findings: R1 codex 10 + gemini 6; R2 codex 8 + gemini 4; R3 codex 10 +
> gemini 5; + Claude all rounds.

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
9. **Close.** Every active row judged (`pass`, or row-level `na` with every
   story still holding ≥1 pass — the single N/A rule, §6.4) →
   `system_validation.json` emitted → `self-check` passes →
   `mark_system_validation_complete` → Finalization→Completed advance
   (coverage gate). The close step is idempotent (§8).

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
      "row_hash": "<canonical row hash — see Hash Canonicalization below>",
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
      "approval_ref": "<Telegram message id | decisions.log line | transcript ref — REQUIRED (INV-3)>",
      "approved_at": "<ISO8601>",
      "replacement_row_id": "r-US3-2"
    }
  ]
}
```

**Hash canonicalization (R3 convergent CRITICAL — deterministic or it doesn't
exist):**
- `row_hash` = first 12 hex chars of sha256 over the UTF-8 encoding of
  `json.dumps([conops_ref, scenario, oracle, evidence_type], ensure_ascii=False, separators=(",", ":"))`
  with all four strings NFC-normalized first. `evidence_rationale` and
  `test_targets` are deliberately EXCLUDED (editing rationale or target
  bookkeeping must not orphan evidence).
- `conops_hash` = first 12 hex chars of sha256 over the raw file bytes of
  `conops.md` (mirrors fizzy's `_sha256_prefix`; the gate prefix-matches
  bidirectionally, so 12 hex chars satisfy it).
- Both lengths are constants in `validation_emission.py`; tests pin them.

**Digest batch lifecycle (R3 codex):** a batch is `open` from assembly until
every row in it is judged (then `closed`) or it is explicitly cancelled
(`cancel-batch --digest-id d-N --reason <text>` — audit-logged; rows return to
the delta pool). EXACTLY ONE batch may be open; `assemble-digest` refuses
while one is open. Each batch snapshots its rows' `row_hash`es; a reply
verdict is rejected if the row's hash changed after batch open (stale-row
protection). `pass all` / `pass rest` scope to the OPEN batch's rows only.

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

**The single N/A rule (R3 codex — resolves §4/§6.5 conflict):** `na` rows DO
appear in `system_validation.json` (the gate's result enum accepts
`not-applicable`; only `fail` hard-rejects) and do NOT count toward story
coverage — every story needs ≥1 `pass` row regardless. Close proceeds when
every active row is judged `pass` or `na` AND coverage holds.

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
`parse-reply`, `assemble-digest`, and `cancel-batch` mutate the ledger; each
takes `validation-rows.json.lock` for the full read-modify-write; everything
else is read-only.

**Lock + failure semantics (R3 convergent):** `filelock.FileLock` with a 10s
timeout (the skill's established TASK_LOCK pattern); timeout → exit 3
`LEDGER_BUSY`, never blocking forever. Crash recovery is structural: the OS
releases advisory locks on process death, and every mutation is
read→mutate→atomic-tmp+rename INSIDE the lock, so a crash mid-mutation leaves
the previous ledger intact (no partial writes possible). A malformed/unparseable
ledger → exit 3 `LEDGER_CORRUPT`, never auto-repaired — restore from git.
**Exit codes (all subcommands):** 0 = ok; 2 = validation issues (structured
`{code, row_id, detail}` on stdout); 3 = environment/IO/lock/corrupt.

- `derive-conops <manifest> [-o conops.md]` — §6.1; prints sha256 prefix.
- `check-rows <validation-rows.json> --conops <conops.md>` — §6.2 STRUCTURAL
  constraints; `--conops` is REQUIRED (R3 codex: INV-7 coverage is
  uncheckable without it); exit 2 on violation with `{code, row_id, detail}`
  issues (codes mirror gate names where they overlap). Scope honesty (R2
  gemini CRITICAL): `check-rows` validates syntax and structure ONLY — id
  formats, iff-form, banned-phrase lint, coverage, target sets, hash
  presence/recomputation. It cannot and does not judge semantic intent;
  wrong-story scenarios are caught by the human layers (conductor drafting
  review, Jason's judgment).
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
  excludes superseded rows (INV-10); records the digest batch in the ledger
  (snapshotting row hashes); refuses while another batch is open; writes
  discrete part files and prints their paths. Resets resolved-fail rows
  (fail → history, result → null) only via paired args
  `--reset-failed <row_id> --remediation-ref <card_id>` (repeatable; one
  remediation reference REQUIRED per reset row — R3 codex). If zero rows have
  `result == null` and none need reset, exits 0 with `NOTHING_TO_DIGEST` —
  the close step then skips straight to emission (idempotent re-entry).
- `cancel-batch <validation-rows.json> --digest-id <d-N> --reason <text>` —
  NEW (R3): closes an open batch without judgments (audit-logged); its rows
  return to the delta pool.
- `parse-reply <validation-rows.json> <reply-text> --digest-id <d-N> --source telegram|terminal --reply-ref <id> --sender-id <id>`
  — §6.5 grammar; OWNS the locked ledger mutation: applies a fully-valid reply
  atomically (result + judgment provenance fields + history append) or raises
  `RepromptRequired` with zero mutations. Stale/non-active `digest-id` →
  rejected; verdict on a row whose hash changed since batch open → rejected.
  **Sender verification (R3 convergent CRITICAL):** for `--source telegram`,
  `--sender-id` is REQUIRED and checked against the project's Telegram
  allowlist (the configured chat id from the telegram registry — never
  hardcoded); a non-allowlisted sender → reply DISCARDED with a warning (no
  re-prompt, no mutation — INV-15). `--source terminal` asserts the local
  operator is Jason (single-user machine assumption, documented). There is no
  intermediate judgment store — judgments live in the ledger from the moment
  of parse.
- `emit-system-validation <validation-rows.json> --conops <conops.md> [-o system_validation.json]`
  — NEW (R2 gemini): machine projection of the ledger's judged rows into the
  gate artifact shape (§6.4) — top-level `kind`, fresh `conops_hash`, rows
  with the gate's required fields (+ extras per ASSUMPTION-1 state). The
  conductor never hand-writes the gate artifact. Refuses if any active row is
  unjudged or failed, AND recomputes the fresh ConOps hash — mismatch with the
  ledger's `conops_hash` → refusal (R3 gemini: blocks the stale-hash race at
  the projection layer; the fix is re-derive → re-draft affected rows →
  re-judge, per US-12).

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

**Close-step idempotency (R3 convergent HIGH):** the Phase 8 close is
re-entrant at every step. Re-entering when: all rows already judged →
`assemble-digest` exits `NOTHING_TO_DIGEST`, skip to emission; emission
already produced a self-check-clean `system_validation.json` → skip to the
MCP call; the card already has `system_validation_complete: true` (check
`get_card_metadata` FIRST on re-entry) → skip the MCP call entirely and
proceed to the Finalization advance. A crash between emission and the MCP
call therefore re-enters cleanly with no re-judging and no duplicate state.

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
- INV-15: A Telegram-sourced judgment is applied only when the sender id
  matches the project's configured allowlist; non-allowlisted replies are
  discarded (logged), never parsed into the ledger.

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
- Reply authenticity: sender-id allowlist check in `parse-reply` (INV-15);
  the wake-listener pipeline already scopes updates to the project bot's chat,
  and the allowlist is defense-in-depth on top.
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
