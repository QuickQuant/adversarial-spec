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
