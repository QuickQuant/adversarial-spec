# Execution Plan: Validation-Leg Production Process

> **STATUS: APPROVED — Jason 2026-06-11 (present-plan gate, Gate V4 exemptions, and
> tree lock all passed; node count corrected to the TRUE 25 at approval).**
> Next: Step 9b emission → validate loop → pipeline_load (expect 25 New Todo cards).
>
> Session: `adv-spec-202606110339-validation-leg-process` | card 5604 | altitude: system
> Spec: `spec-output.md` (FINAL) | Gauntlet: `gauntlet-concerns-2026-06-11.json` (48 accepted)
> Target arch: `target-architecture.md` (reconciled @ 88a8e664) | Invariants: `architecture-invariants.json` (INV-A1..A7)
> Roadmap: `roadmap/manifest.json` (US-0..US-13, G1-G5, M0-M4) | Tests: `tests-spec.md`
> Gate contract: `fizzy-validation-contract.md` (8 reject classes) | Emitter: `scripts/mini_spec_emission.py`
> Plan schema: **3** (v4 altitude session; system→subsystem→component tree). middleware-candidates EMPTY (middleware-creator skipped).

## Summary

- **Deliverable:** one new stdlib module `skills/adversarial-spec/scripts/validation_emission.py`
  (13 subcommands) + test suite `scripts/tests/test_validation_emission.py` + Phase 7/8
  doc sections + dogfood close. Sibling of `mini_spec_emission.py`; same doc-driven /
  code-checked-shapes pattern (emission-toolchain.md).
- **Nodes:** 25 — 1 system root, 5 subsystems, 19 build components. (Header previously
  misstated 20/14 — stale arithmetic caught at Gate V4 2026-06-11; tree structure unchanged.)
- **Gauntlet concerns addressed:** 48 of 48 accepted (all already woven into FINAL spec;
  linked here so acceptance criteria carry the failure-mode protection).
- **Effort estimate:** ~19 component tasks × S–M ≈ 3–6 days single-agent; less multi-agent.

## Architecture Spine (cross-cutting — every node obeys)

From `architecture-invariants.json`. All tasks MUST preserve these:

| ID | Rule | Invariant | Reference |
|----|------|-----------|-----------|
| AS-1 | `validation-rows.json` is the sole judgment store; `system_validation.json` is write-only projection (`emit-system-validation` only) | INV-A1 | TA §SoT, spec §6.2 |
| AS-2 | Only the 8 named mutators write the ledger, each under `validation-rows.json.lock` via atomic tmp+rename; all else read-only | INV-A2 | TA §Enforcement, spec §7 |
| AS-3 | Every subcommand prints one stdout JSON envelope `{status,code,issues:[{code,row_id,detail}],data}`; exit 0/2/3; reply apply atomic (zero-mutation on invalid) | INV-A3 | spec §7, gauntlet FM-5 |
| AS-4 | Telegram sender extracted by module from raw wake-listener payload vs registry `allowed_sender_ids` (≠ chat_id); fail-closed | INV-A4 | TA §Security, spec §11, SEC-1/2 |
| AS-5 | `self-check` mirrors all 8 gate reject classes, strictly stricter (identical-set anti-relabeling), runs on exact emitted bytes immediately before `mark_system_validation_complete` | INV-A5 | spec §7, fizzy-validation-contract.md |
| AS-6 | At most one open digest batch; conops/row/evidence hashes snapshot at open; idempotent close re-entry | INV-A6 | TA §Delivery, spec §6.2/§8 |
| AS-7 | Every non-null result carries full provenance; `judgment_history` append-only; supersessions/cancellations audit-logged | INV-A7 | spec §9, §11 |

**Wave 0 = SS-1 ledger-core** — shared foundation, blocks every feature subcommand.

## Altitude Tree

```
SYS  validation-leg-process       [system]   parent=null  realizes=US-0..US-13 (owner)
├─ SS-1 ledger-core               [subsystem] parent=SYS   realizes=US-0,US-3,US-7,US-8
│   ├─ C-1.1 module-skeleton-envelope         [component] parent=SS-1
│   ├─ C-1.2 lock-atomic-corrupt              [component] parent=SS-1
│   ├─ C-1.3 hash-canonicalization            [component] parent=SS-1
│   └─ C-1.4 path-containment-bounds          [component] parent=SS-1
├─ SS-2 drafting-leg              [subsystem] parent=SYS   realizes=US-1,US-2,US-3,US-4
│   ├─ C-2.1 derive-conops                    [component] parent=SS-2
│   ├─ C-2.2 normalize-rows                   [component] parent=SS-2
│   └─ C-2.3 check-rows-oracle-lint           [component] parent=SS-2
├─ SS-3 evidence-and-digest       [subsystem] parent=SYS   realizes=US-5,US-6,US-13
│   ├─ C-3.1 record-evidence                  [component] parent=SS-3
│   ├─ C-3.2 assemble-digest                  [component] parent=SS-3
│   └─ C-3.3 record-send-cancel-batch         [component] parent=SS-3
├─ SS-4 judgment-and-close        [subsystem] parent=SYS   realizes=US-7,US-8,US-9,US-11,US-12
│   ├─ C-4.1 parse-reply-grammar              [component] parent=SS-4
│   ├─ C-4.2 telegram-trust-boundary          [component] parent=SS-4
│   ├─ C-4.3 reset-failed-supersede           [component] parent=SS-4
│   ├─ C-4.4 emit-system-validation           [component] parent=SS-4
│   ├─ C-4.5 self-check                        [component] parent=SS-4
│   └─ C-4.6 status                            [component] parent=SS-4
└─ SS-5 phase-wiring-and-dogfood  [subsystem] parent=SYS   realizes=US-0,US-8,US-9,US-10
    ├─ C-5.1 doc-07-execution-validation-leg  [component] parent=SS-5
    ├─ C-5.2 doc-08-implementation-close-algo  [component] parent=SS-5
    └─ C-5.3 dogfood-validation-this-session   [component] parent=SS-5
```

`depends_on` (scheduling only, no altitude inversion): SS-2/SS-3/SS-4 components depend_on
Wave-0 (SS-1). C-4.5 self-check depend_on C-4.4 emit. SS-5 docs depend_on real subcommand
names (SS-2/3/4). C-5.3 dogfood depend_on everything.
**Encoding note (2026-06-12):** these edges are encoded per-node on each `- altitude:` line
below — the emitter reads ONLY per-node `depends_on:` fields, never this paragraph. The
2026-06-11 emission dropped every edge except C-4.5→C-4.4 because the rest existed only
as prose here; per-node fields are now the normative encoding.

## Per-Node Specifications

Format per node: altitude · realizes_refs · impl_status (+evidence) · behavior_change ·
verification_mode/scope · strategy · architecture_refs · concern_refs · invariant_refs ·
surface_scope · test_refs · acceptance_criteria.

### SYS — validation-leg-process (system root)
- altitude: system · parent: null · decomposes_into: [SS-1,SS-2,SS-3,SS-4,SS-5]
- conops_refs / user_story_refs: US-0,US-1,US-2,US-3,US-4,US-5,US-6,US-7,US-8,US-9,US-10,US-11,US-12,US-13
- impl_status: greenfield — "no validation-leg production line exists; spec §1 'the skill has no process that produces the gate's inputs'"
- behavior_change: true · verification_mode: automated-integration · scope: full-suite · strategy: test-first
- architecture_refs: `.architecture/primer.md`, `.architecture/overview.md`, `.architecture/structured/components/emission-toolchain.md`
- concern_refs: (aggregate) · invariant_refs: INV-A1..A7 · surface_scope: cli_command, outbound_integration
- test_refs: TC-4.1 · test_files: `scripts/tests/test_validation_emission.py`
- acceptance_criteria:
  - [ ] Full pytest suite green (`deterministic` markers) across all subcommands
  - [ ] System verification = the integration close path runs end-to-end on fixtures
  - [ ] System validation deferred to dogfood C-5.3 (v4 is verification-only — no system_validation plan binding; VV_ABOVE_ALTITUDE guard)

### SS-1 — ledger-core (subsystem, WAVE 0)
- altitude: subsystem · parent: SYS · decomposes_into: [C-1.1,C-1.2,C-1.3,C-1.4] · realizes: US-0,US-3,US-7,US-8
- impl_status: greenfield — "`validation_emission.py` absent (ls 2026-06-11)"
- behavior_change: true · verification_mode: automated-integration · scope: full-suite · strategy: test-first
- architecture_refs: `.architecture/primer.md`, `.architecture/patterns.md`, `.architecture/structured/flows.md`
- concern_refs: FM-5,FM-7,SEC-8,SEC-9,SEC-10,OP-3,OP-4,DD-6 · invariant_refs: INV-A1,INV-A2,INV-A3,INV-12 · surface_scope: cli_command
- test_refs: TC-3.9,TC-2.6 · acceptance: shared ledger I/O foundation passes lock/corrupt/hash/path fixtures; blocks all feature subcommands until green.

#### C-1.1 module-skeleton-envelope
- altitude: component · parent: SS-1 · realizes: US-0
- impl_status: greenfield — "no `skills/adversarial-spec/scripts/validation_emission.py` (ls → ABSENT 2026-06-11)"
- behavior_change: true · verification_mode: automated-unit · scope: targeted · strategy: test-first
- architecture_refs: `.architecture/structured/components/emission-toolchain.md`, `.architecture/structured/components/debate-engine.md`, `.architecture/patterns.md`
- concern_refs: FM-5,OP-3,OP-4,OP-11 · invariant_refs: INV-A3 · surface_scope: cli_command
- test_refs: TC-3.9 · test_files: `scripts/tests/test_validation_emission.py` · verify_commands: `uv run pytest scripts/tests/test_validation_emission.py -k envelope -q`
- acceptance_criteria:
  - [ ] argparse dispatch for all 13 subcommands; unknown subcommand → exit 2 envelope
  - [ ] Every invocation prints exactly one stdout JSON envelope `{status,code,issues:[{code,row_id,detail}],data}`; warnings to stderr only (FM-5)
  - [ ] Exit-code contract 0/2/3 wired at CLI boundary; global issues carry `row_id:null`
  - [ ] `schema_version` + `module_version` (`__version__` + git short hash) stamped on JSON artifacts (OP-4, DD-6); all timestamps UTC RFC3339 Z (OP-3)

#### C-1.2 lock-atomic-corrupt
- altitude: component · parent: SS-1 · realizes: US-8
- impl_status: greenfield — "no implementer; pattern source is `gauntlet/persistence.py` (existing)"
- behavior_change: true · verification_mode: automated-unit · scope: targeted · strategy: test-first
- architecture_refs: `.architecture/structured/flows.md`, `.architecture/structured/components/gauntlet.md`, `.architecture/patterns.md`
- concern_refs: FM-7,DD-6,US-8(filelock-semantics),DIS-1(10s-noted) · invariant_refs: INV-A2 · surface_scope: cli_command
- test_refs: TC-3.9 · verify_commands: `uv run pytest scripts/tests/test_validation_emission.py -k "lock or corrupt or atomic" -q`
- acceptance_criteria:
  - [ ] `filelock.FileLock` 10s timeout → exit 3 `LEDGER_BUSY` with owner-pid/lock-age when readable
  - [ ] Every mutation read→mutate→atomic tmp+rename INSIDE the lock; crash mid-write leaves prior ledger intact, no `.tmp` litter (TC-3.9c)
  - [ ] Malformed ledger → exit 3 `LEDGER_CORRUPT`; corrupt bytes copied to `validation-rows.json.corrupt-<ts>` first; never auto-repaired
  - [ ] Single mutation helper requiring the lock; read-only subcommands have no write path (INV-A2)

#### C-1.3 hash-canonicalization
- altitude: component · parent: SS-1 · realizes: US-3
- impl_status: greenfield
- behavior_change: true · verification_mode: automated-unit · scope: targeted · strategy: test-first
- architecture_refs: `.architecture/structured/components/emission-toolchain.md`, `.architecture/structured/components/gauntlet.md`
- concern_refs: SEC-8,DD-5,RC-3 · invariant_refs: INV-12,INV-A1 · surface_scope: cli_command
- test_refs: TC-2.6 · verify_commands: `uv run pytest scripts/tests/test_validation_emission.py -k hash -q`
- acceptance_criteria:
  - [ ] `row_hash` = sha256 over `json.dumps([conops_ref,scenario,oracle,evidence_type],ensure_ascii=False,separators=(",",":"))` with all 4 NFC-normalized; FULL 64-hex stored
  - [ ] `evidence_rationale` + `test_targets` EXCLUDED from row_hash (TC-2.6); hash changes when scenario/oracle/conops_ref/evidence_type change
  - [ ] `conops_hash` = sha256 of conops.md bytes; `story_hashes` per-section; 12-hex prefix emitted only at artifact boundary; self-check rejects prefixes <12 (SEC-8)
  - [ ] Hashes computed ONLY by the module; lengths/constants pinned by tests

#### C-1.4 path-containment-bounds
- altitude: component · parent: SS-1 · realizes: US-7
- impl_status: greenfield — "path-traversal guard pattern source `session.py` `is_relative_to` (existing)"
- behavior_change: true · verification_mode: automated-unit · scope: targeted · strategy: test-first
- architecture_refs: `.architecture/structured/components/session.md`, `.architecture/patterns.md`
- concern_refs: SEC-9,SEC-10,OP-3 · invariant_refs: INV-A3 · surface_scope: cli_command
- test_refs: TC-2.6,TC-1.4 · verify_commands: `uv run pytest scripts/tests/test_validation_emission.py -k "path or bounds" -q`
- acceptance_criteria:
  - [ ] Subcommands resolve artifact paths under spec root via realpath; symlinks/escapes rejected (SEC-9)
  - [ ] Input bounds enforced: reply 16KB, justification 2KB, ledger 5MB, ConOps 1MB → structured exit-2 (SEC-10)
  - [ ] row_id global uniqueness incl. superseded; duplicate manifest story ids → exit 2

### SS-2 — drafting-leg (subsystem)
- altitude: subsystem · parent: SYS · decomposes_into: [C-2.1,C-2.2,C-2.3] · realizes: US-1,US-2,US-3,US-4
- impl_status: greenfield · behavior_change: true · verification_mode: automated-integration · scope: full-suite · strategy: test-first
- architecture_refs: `.architecture/structured/components/emission-toolchain.md`, `.architecture/primer.md`
- concern_refs: DD-7,DD-8,CB-7,CB-10,CB-11,SEC-7 · invariant_refs: INV-6,INV-7,INV-8,INV-11 · surface_scope: cli_command
- test_refs: TC-1.1,TC-2.1 · acceptance: Phase-7 production path derive→normalize→check clean on the session's real roadmap.

#### C-2.1 derive-conops
- altitude: component · parent: SS-2 · realizes: US-1 · depends_on: C-1.1, C-1.2, C-1.3, C-1.4
- impl_status: greenfield · behavior_change: true · verification_mode: automated-unit · scope: targeted · strategy: test-first
- architecture_refs: `.architecture/structured/components/emission-toolchain.md`, `.architecture/structured/components/session.md`, `.architecture/patterns.md`
- concern_refs: DD-7,CB-11,FM-3,SEC-9 · invariant_refs: INV-2,INV-8 · surface_scope: cli_command
- test_refs: TC-1.1,TC-1.2,TC-1.3,TC-G13 · verify_commands: `uv run pytest scripts/tests/test_validation_emission.py -k conops -q`
- acceptance_criteria:
  - [ ] Deterministic template derivation from manifest id/title/story + milestone context only; never invents stories (DD-7)
  - [ ] Every `US-\d+` appears as `### US-n` heading; stray-id lint (TC-G13: "replaces US-99" → exit 2, CB-11); duplicate ids → exit 2
  - [ ] Records full `conops_hash` + per-section `story_hashes` map (FM-3); re-derive refuses without `--force` when a ledger references prior hash

#### C-2.2 normalize-rows
- altitude: component · parent: SS-2 · realizes: US-3 · depends_on: C-1.1, C-1.2, C-1.3, C-1.4
- impl_status: greenfield · behavior_change: true · verification_mode: automated-unit · scope: targeted · strategy: test-first
- architecture_refs: `.architecture/structured/components/emission-toolchain.md`, `.architecture/structured/components/gauntlet.md`
- concern_refs: CB-7,DD-4 · invariant_refs: INV-A1,INV-12 · surface_scope: cli_command
- test_refs: TC-G11 · verify_commands: `uv run pytest scripts/tests/test_validation_emission.py -k normalize -q`
- acceptance_criteria:
  - [ ] Sole producer of `row_hash`/`story_hash` (CB-7); conductor never writes hex
  - [ ] Stamps schema fields; validates row_id format `r-US<n>-<k>` + global uniqueness + story-prefix match
  - [ ] Mutating subcommand — holds lock, atomic write (INV-A2)

#### C-2.3 check-rows-oracle-lint
- altitude: component · parent: SS-2 · realizes: US-4 · depends_on: C-1.1, C-1.2, C-1.3, C-1.4
- impl_status: greenfield · behavior_change: true · verification_mode: automated-unit · scope: targeted · strategy: test-first
- architecture_refs: `.architecture/structured/components/emission-toolchain.md`, `.architecture/patterns.md`
- concern_refs: CB-10,DD-8,SEC-7,DIS-2,OP-2 · invariant_refs: INV-6,INV-7,INV-11 · surface_scope: cli_command
- test_refs: TC-2.1,TC-2.2,TC-2.3,TC-2.4 · verify_commands: `uv run pytest scripts/tests/test_validation_emission.py -k "check_rows or oracle" -q`
- acceptance_criteria:
  - [ ] `--conops` required; coverage uses exact-token equality `conops_ref=="US-n"` (CB-10); `--draft` relaxes coverage to advisory (DD-8)
  - [ ] Oracle layer-2 lint rejects banned phrases ("tests pass" + synonyms) and vague terminals unless paired with concrete observable; requires literal `iff` + named US-n (INV-6, TC-2.3)
  - [ ] Anti-relabeling: validation test_targets not identical/subset/overlapping verification targets without rationale (INV-11, SEC-7)
  - [ ] Structural only — semantics human-owned (documented scope honesty)

### SS-3 — evidence-and-digest (subsystem)
- altitude: subsystem · parent: SYS · decomposes_into: [C-3.1,C-3.2,C-3.3] · realizes: US-5,US-6,US-13
- impl_status: greenfield · behavior_change: true · verification_mode: automated-integration · scope: full-suite · strategy: test-first
- architecture_refs: `.architecture/primer.md`, `.architecture/structured/components/harness-hooks.md`
- concern_refs: FM-2,DD-1,RC-2,SEC-4,FM-9 · invariant_refs: INV-4,INV-9,INV-10,INV-12,INV-16,INV-A6 · surface_scope: cli_command, outbound_integration
- test_refs: TC-3.1,TC-3.7 · acceptance: evidence→digest→delivery path correct on fixtures + real bridge at dogfood.

#### C-3.1 record-evidence
- altitude: component · parent: SS-3 · realizes: US-13 · depends_on: C-1.1, C-1.2, C-1.3, C-1.4
- impl_status: greenfield · behavior_change: true · verification_mode: automated-unit · scope: targeted · strategy: test-first
- architecture_refs: `.architecture/structured/components/emission-toolchain.md`, `.architecture/structured/components/gauntlet.md`
- concern_refs: FM-2,FM-4,DD-9,OP-2 · invariant_refs: INV-4,INV-9,INV-12 · surface_scope: cli_command
- test_refs: TC-3.7,TC-G4 · verify_commands: `uv run pytest scripts/tests/test_validation_emission.py -k evidence -q`
- acceptance_criteria:
  - [ ] Scaffolds `validation-evidence/<row_id>/evidence.md` canonical front-matter (hashes stamped by module, FM-2); exact keys/order, distinct codes for missing/malformed/hash-mismatch
  - [ ] Records conductor `evidence_summary` into ledger row (mutating); binds row_hash+story_hash+commit (INV-9, INV-12)
  - [ ] Per-story binding: editing one story invalidates only that story's evidence (FM-3/G4)

#### C-3.2 assemble-digest
- altitude: component · parent: SS-3 · realizes: US-6 · depends_on: C-1.1, C-1.2, C-1.3, C-1.4
- impl_status: greenfield · behavior_change: true · verification_mode: automated-unit · scope: targeted · strategy: test-first
- architecture_refs: `.architecture/structured/components/harness-hooks.md`, `.architecture/structured/components/providers.md`, `.architecture/patterns.md`
- concern_refs: DD-1,RC-3,SEC-4,FM-9,OP-5,OP-9 · invariant_refs: INV-4,INV-10,INV-12,INV-A6 · surface_scope: cli_command, outbound_integration
- test_refs: TC-3.1,TC-1.5,TC-G9 · verify_commands: `uv run pytest scripts/tests/test_validation_emission.py -k digest -q`
- acceptance_criteria:
  - [ ] Pure assembly (reset removed — DD-1); only `result==null` active rows (delta); refuses missing/empty/type-mismatched/hash-mismatched/reset-stale evidence (INV-4/12)
  - [ ] Refuses while non-terminal batch exists; snapshots conops/row/evidence hashes; writes part files to `validation-digests/`, records sha256s (RC-3, A6)
  - [ ] 3500 UTF-8 byte/part split at row boundaries, `(part i/k)` labels; secret deny-pattern lint blocks assembly; row prose escaped; narrative rows marked (SEC-4, FM-9)
  - [ ] Zero pending → exit 0 `NOTHING_TO_DIGEST`

#### C-3.3 record-send-cancel-batch
- altitude: component · parent: SS-3 · realizes: US-6 · depends_on: C-1.1, C-1.2, C-1.3, C-1.4
- impl_status: greenfield · behavior_change: true · verification_mode: automated-unit · scope: targeted · strategy: test-first
- architecture_refs: `.architecture/structured/components/harness-hooks.md`, `.architecture/structured/components/emission-toolchain.md`
- concern_refs: RC-2,FM-6,FM-12,OP-7 · invariant_refs: INV-16,INV-A6 · surface_scope: cli_command, outbound_integration
- test_refs: TC-G1 · verify_commands: `uv run pytest scripts/tests/test_validation_emission.py -k "record_send or cancel" -q`
- acceptance_criteria:
  - [ ] `record-send` records per-part delivery + message_id; flips batch to `sent` only when ALL parts sent (RC-2)
  - [ ] `cancel-batch` requires `--reason`; rows return to delta pool; audit-logged; cancellation notice if parts were sent (FM-12)
  - [ ] Bulk verdicts gated on `sent` status (INV-16)

### SS-4 — judgment-and-close (subsystem)
- altitude: subsystem · parent: SYS · decomposes_into: [C-4.1,C-4.2,C-4.3,C-4.4,C-4.5,C-4.6] · realizes: US-7,US-8,US-9,US-11,US-12
- impl_status: greenfield · behavior_change: true · verification_mode: automated-integration · scope: full-suite · strategy: test-first
- architecture_refs: `.architecture/structured/components/harness-hooks.md`, `.architecture/structured/components/emission-toolchain.md`
- concern_refs: CB-1,CB-9,SEC-1,SEC-2,RC-1,FM-10,DD-2 · invariant_refs: INV-1,INV-3,INV-5,INV-11,INV-13,INV-15,INV-17,INV-A1,INV-A4,INV-A5,INV-A7 · surface_scope: cli_command, outbound_integration
- test_refs: TC-3.2,TC-3.3 · acceptance: reply→judgment→emission→gate-parity close path correct on fixtures.

#### C-4.1 parse-reply-grammar
- altitude: component · parent: SS-4 · realizes: US-7 · depends_on: C-1.1, C-1.2, C-1.3, C-1.4
- impl_status: greenfield · behavior_change: true · verification_mode: automated-unit · scope: targeted · strategy: test-first
- architecture_refs: `.architecture/structured/components/emission-toolchain.md`, `.architecture/patterns.md`
- concern_refs: CB-9,FM-10,RC-4,OP-6,SEC-6-reject · invariant_refs: INV-1,INV-16,INV-17,INV-A3 · surface_scope: cli_command
- test_refs: TC-3.2,TC-3.5,TC-G2,TC-G6,TC-G8 · verify_commands: `uv run pytest scripts/tests/test_validation_emission.py -k "parse_reply or grammar" -q`
- acceptance_criteria:
  - [ ] Block grammar: per_row / bulk_pass (+ fixed natural-alias list) / pass_rest; case-insensitive keywords, exact-case row ids (TG-G2/G8)
  - [ ] fail+na REQUIRE justification (FM-10); explicit per-row applies before bulk (CB-9); duplicate verdicts invalid; typo'd continuation → parse error
  - [ ] Idempotent by `reply_ref` (processed_reply_refs); edited messages ignored (INV-17, RC-4); invalid/partial → ZERO mutations + re-prompt quoting truncated untrusted text (INV-A3)
  - [ ] Owns the locked judgment mutation; writes provenance block (INV-1)

#### C-4.2 telegram-trust-boundary
- altitude: component · parent: SS-4 · realizes: US-7 · depends_on: C-1.1, C-1.2, C-1.3, C-1.4
- impl_status: greenfield — "wake-listener payload source `~/.claude/bin/telegram-wake-listener` (exists); ASSUMPTION-2 verified at impl"
- behavior_change: true · verification_mode: automated-unit · scope: targeted · strategy: test-first
- architecture_refs: `.architecture/structured/components/harness-hooks.md`, `.architecture/structured/components/providers.md`
- concern_refs: SEC-1,SEC-2,SEC-3,OP-1,US-1 · invariant_refs: INV-15,INV-A4 · surface_scope: outbound_integration
- test_refs: TC-INV-A4,TC-G3,TC-G7 · verify_commands: `uv run pytest scripts/tests/test_validation_emission.py -k "sender or telegram or allowlist" -q`
- acceptance_criteria:
  - [ ] `--source telegram` reads RAW `--update-file`; module extracts sender/message/text; `--sender-id` ignored for telegram (SEC-1, TC-G3)
  - [ ] Sender checked vs registry `allowed_sender_ids` (≠ chat_id, SEC-2); missing/malformed registry → `ALLOWLIST_CONFIG_INVALID` fail-closed
  - [ ] Non-allowlisted → DISCARDED, exit 2 `SENDER_NOT_ALLOWLISTED` + hashed-sender security event, zero mutations (INV-15, OP-1)
  - [ ] No hardcoded chat/sender literal in source (static grep, TC-INV-A4); terminal source asserts identity + transcript reply_ref (SEC-3, TC-G7)

#### C-4.3 reset-failed-supersede
- altitude: component · parent: SS-4 · realizes: US-12 · depends_on: C-1.1, C-1.2, C-1.3, C-1.4
- impl_status: greenfield · behavior_change: true · verification_mode: automated-unit · scope: targeted · strategy: test-first
- architecture_refs: `.architecture/structured/components/emission-toolchain.md`, `.architecture/structured/components/gauntlet.md`
- concern_refs: CB-1,DD-1,FM-1,FM-4,DD-10 · invariant_refs: INV-3,INV-13,INV-14,INV-A7 · surface_scope: cli_command
- test_refs: TC-2.5,TC-3.8,TC-G5 · verify_commands: `uv run pytest scripts/tests/test_validation_emission.py -k "reset or supersede" -q`
- acceptance_criteria:
  - [ ] `reset-failed`: judged-fail result→history (append-only INV-14), nulls result/judgment, renames evidence `.invalidated-<ts>` (FM-4); `--remediation-ref` REQUIRED, conductor-verified assertion (FM-1)
  - [ ] `supersede-row`: legal from ANY state incl judged-pass (CB-1/INV-13); full snapshot to `superseded`; transactional replacement in one invocation (no coverage gap, INV-7); `approval_ref` always required (INV-3)
  - [ ] Allowed-reason enum enforced; disallowed (impl failed / evidence missing / prior negative judgment) → `REFRESH_DISALLOWED` (TC-2.5b/G5)

#### C-4.4 emit-system-validation
- altitude: component · parent: SS-4 · realizes: US-8 · depends_on: C-1.1, C-1.2, C-1.3, C-1.4
- impl_status: greenfield · behavior_change: true · verification_mode: automated-unit · scope: targeted · strategy: test-first
- architecture_refs: `.architecture/structured/components/emission-toolchain.md`, `.architecture/structured/cross-references.md`
- concern_refs: CB-2,CB-3,CB-12,DD-3,FM-3,PARA-ledger-hash · invariant_refs: INV-1,INV-8,INV-A1 · surface_scope: cli_command
- test_refs: TC-INV-A1,TC-3.4,TC-3.6 · verify_commands: `uv run pytest scripts/tests/test_validation_emission.py -k "emit or projection" -q`
- acceptance_criteria:
  - [ ] Read-only projection of judged rows into §6.4 (ledger untouched); `result==null ⟺ judgment==null` (CB-2); `na`→`not-applicable` (CB-12)
  - [ ] Refuses: any active row unjudged/failed; provenance missing on non-null result (INV-1); fresh-ConOps mismatch scoped by story_hashes (FM-3)
  - [ ] `test_targets` preserved (anti-relabeling parity SEC-7); `ledger_hash` binds artifact to exact ledger state (PARA); single artifact (OQ-1, DD-3) with Appendix-A contingency
  - [ ] Single N/A rule: na rows appear but don't count toward coverage; every story needs ≥1 pass (TC-3.6)

#### C-4.5 self-check
- altitude: component · parent: SS-4 · realizes: US-11 · depends_on: C-1.1, C-1.2, C-1.3, C-1.4, C-4.4
- impl_status: greenfield · behavior_change: true · verification_mode: automated-unit · scope: targeted · strategy: test-first
- architecture_refs: `.architecture/structured/components/emission-toolchain.md`, `.architecture/primer.md`
- concern_refs: RC-1,SEC-7,CB-5,DD-2 · invariant_refs: INV-5,INV-11,INV-A5 · surface_scope: cli_command
- test_refs: TC-3.3,TC-INV-A5,TC-G10 · verify_commands: `uv run pytest scripts/tests/test_validation_emission.py -k self_check -q`
- acceptance_criteria:
  - [ ] Mirrors all 8 gate reject classes (fizzy-validation-contract.md): kind, conops_hash prefix-match (<12 reject), rows non-empty, per-row fields, result enum, all-pass, anti-relabeling, US coverage regex `\bUS-\d+\b`
  - [ ] Strictly stricter: rejects identical-set AND unjustified-overlap test_targets locally (INV-11); verdict parity is a pinned test (TC-3.3)
  - [ ] `--verification-ledger` required when verification artifacts exist; absent → `ANTI_RELABELING_UNCHECKED` warning, never silent pass
  - [ ] Runs on exact emitted bytes immediately before MCP; artifact sha256 re-verified at call time (INV-5, RC-1 TOCTOU)

#### C-4.6 status
- altitude: component · parent: SS-4 · realizes: US-8 · depends_on: C-1.1, C-1.2, C-1.3, C-1.4
- impl_status: greenfield · behavior_change: **false** (read-only reporter) · verification_mode: automated-unit · scope: targeted · strategy: test-after
- architecture_refs: `.architecture/structured/components/emission-toolchain.md`, `.architecture/structured/components/debate-engine.md`
- concern_refs: FM-5,OP-7,OP-8 · invariant_refs: INV-A7 · surface_scope: cli_command
- test_refs: TC-G12 · verify_commands: `uv run pytest scripts/tests/test_validation_emission.py -k status -q`
- acceptance_criteria:
  - [ ] Read-only: ledger bytes unchanged (TC-G12); reports active batch + age (>48h flagged), per-part send state, unjudged rows, judged summary, coverage state, blockers, next close-algorithm step
  - [ ] No mutation path (INV-A2 read-only side)

### SS-5 — phase-wiring-and-dogfood (subsystem)
- altitude: subsystem · parent: SYS · decomposes_into: [C-5.1,C-5.2,C-5.3] · realizes: US-0,US-8,US-9,US-10
- impl_status: partial — "07/08 docs exist; validation-leg sections absent (grep 2026-06-11)"
- behavior_change: false · verification_mode: automated-integration · scope: full-suite · strategy: spike
- architecture_refs: `.architecture/filesystem-map.md`, `.architecture/access-guide.md`
- concern_refs: DD-2,FM-8,US-0,US-10,ACK-4,OP-10 · invariant_refs: INV-5,INV-7,INV-A5,INV-A6 · surface_scope: cli_command, outbound_integration
- test_refs: TC-0.1,TC-0.2,TC-4.1 · acceptance: docs wire the process + dogfood proves on self.

#### C-5.1 doc-07-execution-validation-leg
- altitude: component · parent: SS-5 · realizes: US-0 · depends_on: C-2.1, C-2.2, C-2.3, C-3.1, C-3.2, C-3.3, C-4.1, C-4.2, C-4.3, C-4.4, C-4.5, C-4.6
- impl_status: **partial** — "`skills/adversarial-spec/phases/07-execution.md` exists (1069 lines); no 'Validation leg (system altitude)' section (grep: only Step-9b generic conops hits at L944/964/1008)"
- behavior_change: false · verification_mode: **artifact-sync** · scope: static · strategy: spike
- architecture_refs: `.architecture/filesystem-map.md`, `.architecture/structured/components/debate-engine.md`
- concern_refs: US-0,CB-7,DD-10,OP-11 · invariant_refs: INV-7,INV-A5 · surface_scope: cli_command
- test_refs: TC-0.1 (dogfood) · **exemption_reason:** "Phase-7 doc section (process narrative, no runtime behavior); cold-read usability verified at dogfood TC-0.1 (fresh agent reaches check-rows-clean draft <30 min), not a CI unit test."
- acceptance_criteria:
  - [ ] "Validation leg (system altitude)" section added after execution plan, before pipeline_load; gated on `session_altitude=="system"` (read via MCP card metadata, US-2)
  - [ ] Documents order derive-conops → draft rows → normalize-rows → check-rows; §3 minimal-row standard; ONE good + ONE rejected row example (CB-7 normalize in sequence)
  - [ ] Records `drafted_baseline_hash`; anti-hindsight note (rows precede implementation)

#### C-5.2 doc-08-implementation-close-algo
- altitude: component · parent: SS-5 · realizes: US-8 · depends_on: C-2.1, C-2.2, C-2.3, C-3.1, C-3.2, C-3.3, C-4.1, C-4.2, C-4.3, C-4.4, C-4.5, C-4.6
- impl_status: **partial** — "`skills/adversarial-spec/phases/08-implementation.md` exists (300 lines); no close-algorithm/validation-leg section (grep 2026-06-11 → none)"
- behavior_change: false · verification_mode: **static-check** · scope: static · strategy: spike
- architecture_refs: `.architecture/filesystem-map.md`, `.architecture/structured/components/debate-engine.md`
- concern_refs: DD-2,FM-8,CB-5,US-4-correction · invariant_refs: INV-5,INV-A6 · surface_scope: cli_command
- test_refs: TC-0.2 · verify_commands: `uv run pytest scripts/tests/test_validation_emission.py -k doc_error_codes -q`
- **exemption_reason:** "Phase-8 close-algorithm doc; verified by TC-0.2 static grep asserting all 8 gate reject codes appear with documented responses — no runtime behavior of its own."
- acceptance_criteria:
  - [ ] "Validation leg (system altitude)" close section = the §8 close algorithm verbatim (single normative ordering, every step idempotent, re-entry at step 1; DD-2)
  - [ ] §10 error-code playbook: all 8 gate rejects + local codes each with documented conductor response (TC-0.2)
  - [ ] Re-entry routing: NOTHING_TO_DIGEST + failed rows → remediation, never emission (CB-5); self-check before MCP (INV-5); MCP wiring concrete (FM-8)

#### C-5.3 dogfood-validation-this-session
- altitude: component · parent: SS-5 · realizes: US-10 · depends_on: (all)
- impl_status: greenfield — "process never executed; this session is its first run"
- behavior_change: false · verification_mode: **manual-ux** · scope: manual · strategy: spike
- architecture_refs: `.architecture/primer.md`, `.architecture/structured/components/harness-hooks.md`, `.architecture/overview.md`
- concern_refs: ACK-4,OP-10,US-10 · invariant_refs: INV-A5 (and all) · surface_scope: cli_command, outbound_integration
- test_refs: TC-4.1 · **exemption_reason:** "Dogfood close: requires the real fizzy gate accepting on first call AND Jason's intent-level acceptance of the process experience (mobile-sufficient digest, unambiguous reply/re-prompt). Human-gated; cannot assert programmatically (NG3, ACK-4 bootstrap circularity acknowledged)."
- acceptance_criteria:
  - [ ] Card 5604 `system_validation_complete == true`; Finalization→Completed advance succeeds (TC-4.1)
  - [ ] Dogfood rows covering US-0/US-6/US-7/US-9 carry Jason's pass with intent-level oracles (not "the gate accepted")
  - [ ] Dogfood metrics record local retries/re-prompts/re-emissions before first MCP call + <30 min bootstrap timing (OP-10)

## Coverage Summary

- **US realization (UNDECOMPOSED_REQUIREMENT guard):** US-0→C-1.1/C-5.1/C-5.3 · US-1→C-2.1 · US-2→C-2.1 · US-3→C-1.3/C-2.2/C-2.3 · US-4→C-2.3 · US-5→C-3.1 · US-6→C-3.2/C-3.3 · US-7→C-1.4/C-4.1/C-4.2 · US-8→C-1.2/C-4.4/C-4.6/C-5.2 · US-9→SS-4/C-5.2 · US-10→C-5.3 · US-11→C-4.5 · US-12→C-4.3 · US-13→C-3.1. **All 14 realized.** ✓
- **Invariant coverage:** INV-A1..A7 + spec INV-1..17 each referenced by ≥1 node. ✓
- **Over-decomposition guard:** 25 nodes vs 14 sections (2× threshold = 28); 19 build leaves vs 14 sections. PASS. ✓
- **Exemptions (Gate V4):** C-5.1 artifact-sync, C-5.2 static-check, C-5.3 manual-ux — all doc/dogfood, verified at M4 dogfood, no CI unit obligation.

## Remaining Phase-7 steps (post-approval)

1. Gate V3 — write `verification-coverage.json` (22 automated: 16 unit + 6 integration; 3 exempt; 0 unmapped behavior-changing).
2. Gate V4 — review the 3 exemptions with Jason.
3. Step 9b — emit schema-3 `fizzy-plan.json` via `mini_spec_emission.emit_fizzy_plan` (writes per-node `normative.md`/`subsystem-spec.md`/`system-spec.md` + `component/subsystem/system-verification-*.md` dotted-line artifacts with re-derivable hashes); enrich each task with the real verification fields above; `self_check_plan()` then `pipeline_validate_plan` loop until clean.
4. Step 9 — `pipeline_load` to board `03fw5alxw15iqwh6hq15vfdsb`; verify New Todo count = 25.
5. Step 10 — per-card concern-context comments (parallel `add_comment`).
