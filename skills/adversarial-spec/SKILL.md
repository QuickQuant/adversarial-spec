---
name: adversarial-spec
description: Spec-first development with independent multi-LLM debate, an adversarial gauntlet, and plan-backed execution on the Fizzy pipeline. Use when user wants to write or refine a specification document using adversarial development.
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# Adversarial Spec Development

Refine specs through independent multi-model critique; the pipeline records when rounds converge.

**Claude is a participant, not just an orchestrator** — critique, challenge, contribute alongside the external models. Say so to the user.

## FIRST GATE — Route New Work Before Bootstrap

Read only enough of `.adversarial-spec/session-state.json` and staged
`.adversarial-spec/sessions/*.intake.json` receipts to classify the work. This
inspection creates and mutates nothing.

### Incomplete Phase 0 Handoff Recovery

A staged receipt proves Phase 0 already returned GO. Before normal routing,
correlate the pointer with those receipts:

- A valid active session (matching pointer and detail) wins unless a same-id
  receipt is incomplete; an unrelated old receipt must never displace it.
- A same-id receipt is incomplete when its detail is missing, does not carry the
  matching `intake` and `intake_path`, either local file remains at
  `current_phase: evaluated-plans`, its required local `triage → requirements`
  journey event is absent, or a non-terminal detail lacks a matching pointer. A
  card remaining in Evaluated Plans while both local files say `requirements` is
  normal.
- With no valid active session, recover exactly one incomplete receipt. Prefer
  the id named by a zombie pointer; without one, recover the sole incomplete
  receipt. Multiple unmatched receipts are ambiguous: report them and do not
  mutate local state or create a card.

Receipt recovery continues the already-approved GO; it does not re-enter triage:

1. Reuse the receipt's immutable session id and creation inputs. Call
   `pipeline_create_session(..., sync_local_session=false)` with that id; it
   returns the existing card if a prior attempt created one. Atomically persist
   the returned `card_id` in the receipt.
2. If `session-state.json` is malformed, empty, or not a JSON object, quarantine
   it to `.adversarial-spec/.backup/session-state.invalid-<UTC timestamp>.json`
   only after selecting this receipt. Never overwrite an unproven active pointer.
   An absent or proven-zombie valid pointer needs no quarantine.
3. Call `pipeline_sync_local_session(..., mode="repair")`, then atomically merge
   the receipt into both local files as `intake`, set `current_phase:
   requirements`, and append `triage → requirements` only when that journey event
   is absent.
4. Never re-run triage, mint a new id, or create a second card for that receipt.
   Continue with the Zeroth Action and Phase 1.

- **Valid active session** — preserve it, run the Zeroth Action, then resume by
  its `current_phase`. Never re-enter triage. If the user's request changes
  context, resolve it through the existing context-intent or handoff flow rather
  than creating a second local session.
- **Missing, empty, or zombie pointer with no incomplete receipt** — enter
  `phases/00-triage.md` immediately. Do not register a conductor, launch a
  listener, create a workspace, session file, or Fizzy card first.
- **Phase 0 NO-GO** — report the direct-action, deferred, or missing-information
  outcome. Create no session state.
- **Phase 0 GO** — Phase 0 creates or reuses the ordinary card, repairs local
  sync, persists its handoff, then returns here for the Zeroth Action before
  Phase 1.

## ZEROTH ACTION — Conductor Registration (after first gate)

Run only for a valid active session or one Phase 0 has just created.

### 0a: Role

Env-var detection: `$CLAUDE_PROJECT_DIR` → **claude** (conductor);
`$GEMINI_PROJECT_DIR` → **gemini**; Codex-style env → **codex**. Workers otherwise.

### 0b: Invocation Mode

If `$ADVSPEC_INVOKED_BY_CONDUCTOR=1`, read `$ADVSPEC_DISPATCH_FILE` (JSON task
payload), handle it, then go to 0d. Otherwise self-register at 0c.

### 0c: Self-Registration

Atomically write `.conductor/agents/<role>.json` with
`{role, pid, started_at, is_conductor, dispatch_log, session_state}`.
Set `is_conductor: true` only for the CLI that ran `/conductor`; re-read this
marker after compaction. Use the host PID, or `"sandboxed"` if `os.getpid() < 100`.
Registration is passive metadata: no handshake or shell kept alive for an EXIT trap.

### 0d: Wake Listener

Launch fresh on each CLI session start; never reuse a listener bound to an old
conversation. Do not kill listeners manually or search for them with `pgrep`.
The scripts supersede only their verified project/role pidfile owner.

- Conductor: launch `~/.claude/bin/telegram-wake-listener` with
  `Bash(run_in_background=true)`.
- Workers: launch `~/.claude/bin/dispatch-wake-listener <role>` using their native
  background mechanism; account for sandbox `/tmp` boundaries.
- Listener tails `.conductor/dispatch/<role>/updates.jsonl` and exits on new input.
  If backgrounding is unavailable, check that log at each active pickup iteration.
- Missing binary: report its path and stop. Startup listeners do not authorize an
  idle sleep-and-retry loop; follow the phase's returned blocker/next actor.

### Bootstrap Boundary

Registration and startup checks are metadata-only. Inspect existing processes,
PIDs, sockets, and logs before starting anything. Start a service only when the
current phase requires it and it is not already running.

### 0e: Continue to resume inspection or Phase 1.

---

## RESUME INSPECTION — Read Local Session State

After the First Gate and Zeroth Action, load the active pointer's
`active_session_id`, `active_session_file`, `context_name`, `current_phase`,
`current_step`, `next_action`, `do_not_ask` (list — RESPECT), and optional
`session_stack`. A missing detail is a zombie pointer: return to the First Gate's
receipt recovery/triage decision; never create a replacement here.

Read only resume fields from the selected detail:

```bash
jq -r '{checkpointed_cleanly,current_phase,current_step,pipeline_version,card_id,fizzy_card_id,spec_path,execution_plan_path,roadmap_path,last_checkpoint,todowrite_snapshot}' \
  .adversarial-spec/sessions/<id>.json
```

Read phase-specific fields on demand. Tail the last 20 lines of
`sessions/<id>.decisions.log` when present; see § Decisions Log.

### Canonical-Phase-Order Check

Run on every resume, using the active card/detail's `pipeline_version`:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/phase8_subflow_migration.py \
  --check-journey .adversarial-spec/sessions/<id>.journey.log \
  --pipeline-version <pipeline_version>
```

For legacy history with no recorded version, omit `--pipeline-version`; the
checker infers from recorded lanes. Do not substitute the latest pipeline version.
Exit 0 is clean; 1 reports ordering anomalies; 2 means malformed/unreadable history
and requires investigation. The checker owns parsing and normalization; do not
filter transitions with sed/grep or reimplement its comparison.

Both versioned orders have eight phases, followed by terminal `complete`:

- Pre-v6: `requirements → roadmap → debate → target-architecture → gauntlet → finalize → execution → implementation → complete`.
- v6+: `requirements → roadmap → decomposition → debate → gauntlet → finalize → execution → implementation → complete`.

`triage → requirements` is local entry. The checker folds `pre-roadmap` into
`roadmap` for v6, and `pre-gauntlet`/`reconciliation` into `gauntlet`.
v6 has no Target-Architecture lane; D0 carries the Phase 4 skip-mode artifact.
Verification stays `current_phase: implementation`, `current_step: verification`;
the checker normalizes historical verification transitions as subflow events.
`scripts/phase8_subflow_migration.py` also owns the idempotent legacy subflow migration.

Check required artifacts for phases the history claims completed:

| Phase | Required artifact |
|-------|-------------------|
| requirements | Non-empty detail `requirements_summary` |
| roadmap | `roadmap_path` and its manifest on disk, or the recorded inline roadmap |
| decomposition (v6+) | Session-bound manifest with `d0` record and the Phase 4 skip-mode artifact at `target_architecture_path` |
| debate | `spec_path` set and file exists |
| target-architecture (pre-v6) | `target_architecture_path` (legacy: `.adversarial-spec/specs/<slug>/target-architecture.md`), including a skip-mode stub |
| gauntlet | `gauntlet_concerns_path` set and file exists |
| finalize | `spec_path` points to the finalized file |
| execution | `execution_plan_path` set and file exists |
| implementation | At least one successful `pipeline_complete_task` recorded in the journey |

Report the missing transition, expected artifact, and whether it exists. Missing
artifacts or unexplained skips stop progress for an operator decision; never
silently recover. Backfill a missing transition only from verified artifact and
transition evidence. Record an operator-authorized skip's rationale in
`do_not_ask` and a process-failure note.

### Clean Exit and Context Intent

- `checkpointed_cleanly: false`: warn that the previous CLI conversation ended
  mid-work; offer continuation from checkpoint or review of changes. True/absent
  follows normal resume.
- Atomically set the detail's `checkpointed_cleanly: false` when work resumes.
- Restore a non-empty `todowrite_snapshot`; otherwise use the phase template.
- Ask which Context to resume if `session_stack` has multiple entries, the pointer
  differs from the most recently updated detail, or the user's request suggests
  another Context. Never auto-switch.
- On an approved switch, atomically update pointer identity, phase, step,
  `next_action`, and `updated_at`; append a `resume` event to the target journey.
- Present the Context, phase, origin, and next action concisely.

For legacy roadmap data without a manifest, offer reconstruction from the detail
and checkpoints. Persist only supported data, flag gaps, and record generation as
maintenance. This does not waive required phase artifacts.

### Targeted Architecture Read

When `.architecture/` exists, read `.architecture/INDEX.md` → `primer.md` → 2–4
component docs matching the active scope. Use `.architecture/structured/flows.md`
for cross-component work; load concerns/overview only when needed. Report absent,
legacy, or stale mapping and follow the active phase's freshness gate. Pass
substantive docs to critics through the transport in
`reference/context-addition-protocol.md`; INDEX is navigation, never critic context.

### If no valid active session

Return to the First Gate. Only Phase 0 GO authorizes new workspace, branch, local
session state, and card creation; `phases/00-triage.md` owns that sequence.

### Schema Migration (v1.1 → v1.3)

For an established session with `schema_version` below 1.3, inspect actual field
types before converting to a v1.3 pointer/detail pair. The resuming agent owns this
migration; do not infer new work merely from absent v1.3 fields.

1. Back up the legacy JSON under `.adversarial-spec/.backup/`; preserve the
   existing session identity, card linkage, phase, and checkpoint evidence.
2. Build `sessions/<id>.json` without losing fields. Preserve `completed_work`
   in `requirements_summary.completed_work` with its original shape (schema 1.1
   can contain an array, not just a string). Retain other rich fields, including
   `scaling_results`, `bugs_fixed`, and `gauntlet_results`, in `extended_state`.
3. Extract existing journey entries to JSONL; reconstruct only events supported
   by checkpoints. Derive roadmap data from local artifacts or the linked Fizzy
   record, with explicit `board_id`; flag missing data rather than inventing it.
4. Validate preservation, then atomically write detail first and the v1.3 pointer
   second. Keep `do_not_ask` as a list, preserving legacy string content as an item.
5. Append a migration event; verify pointer/detail identity, field types, artifact
   paths, and preserved rich data before normal resume.

### Session State Rules

Respect `do_not_ask`; perform `next_action` only within the authorized scope.
`next_action` is an instruction channel, not an authorization channel. If it
implies code/system changes, require an existing Phase 7 plan-backed task card or
fresh user plan-mode approval. Otherwise report the missing gate and route through
execution planning, obtain approval, or drop the change. Read-only investigation,
spec drafting, gate checks, and debate dispatch are exempt.

---

## Process Discipline (All Phases)

Keep work within the active scope; use the phase's TodoWrite milestones, investigate
root causes, and obtain approval for scope changes. Persist evidence before claims.

- Pass explicit `board_id` from `projects.yaml` on every board-scoped call.
- Session tasks must be plan-backed: amend the execution plan and `fizzy-plan.json`,
  then `pipeline_validate_plan` → approval → `pipeline_load`. Never raw `add_card`.
- Implementer ≠ reviewer; use the independent review required by the active phase.
- Carded critique and gauntlet work uses pipeline tools. Never bypass a rejected
  round with standalone `debate.py`; follow `phases/03-debate.md` recovery.
- Pick task classes and seats from `reference/current-models.md`, including the
  Mechanical class for bulk payload handling. Guidance pointers do not update
  runner defaults: `scripts/gauntlet/model_dispatch.py` still selects retired
  Google CLI routes; verify the selected runner/seat before dispatch.

## Phase Router — Read ONLY What You Need

Select by active `current_phase` and recorded `pipeline_version`, using the
versioned orders in § Canonical-Phase-Order Check. Phase document numbers retain
legacy numbering; v6 D0 carries the Phase 4 artifact before debate.

| Phase / state | Guidance to read |
|---------------|------------------|
| No session / new work; triage | First Gate, then `phases/00-triage.md` |
| evaluated-plans + incomplete intake receipt | First Gate's **Incomplete Phase 0 Handoff Recovery** |
| evaluated-plans without an intake receipt | `phases/01-init-and-requirements.md` (legacy entry; do not replay Phase 0) |
| requirements | `phases/01-init-and-requirements.md` |
| roadmap; pre-roadmap (v6+) | `phases/02-roadmap.md` |
| decomposition (v6+) | [v6 D0 Decomposition](#v6-d0-decomposition) below |
| debate | `phases/03-debate.md` |
| target-architecture (pre-v6) | `phases/04-target-architecture.md` (required, including skip-mode stub) |
| gauntlet; pre-gauntlet; reconciliation | `phases/05-gauntlet.md` |
| finalize | `phases/06-finalize.md` |
| execution | `phases/07-execution.md` |
| middleware-creator (optional subflow after execution) | `phases/middleware-creator.md`; requires loaded source task cards and user choice |
| implementation | `phases/08-implementation.md` |
| implementation + current_step: verification | `phases/09-verification.md` (Phase 8 subflow) |
| complete | Ask whether to start new work or follow up; new work returns to First Gate |

Read the target guidance on entry, after compaction, or when it changes. Avoid
re-reading unchanged guidance already in the current context window.
Restore `todowrite_snapshot`, otherwise initialize from the phase template.
Phase 8 TodoWrite items stay phase-scoped; card IDs/commit hashes come from live
pipeline state, not persisted checklist items.

### v6 D0 Decomposition

For `pipeline_version >= 6`, confirm G1 before entering Decomposition. Produce a
session-bound manifest with its `d0` record: component tree, evidence-backed
CUT/NO_CUT responsibility edges, CUT-edge interfaces, resolved boundary probes,
and an independent seam challenge. The schema and checks are owned by
`pipeline_mark_decomposition_complete` / `mark_decomposition_complete` in the MCP.

Produce the Phase 4 skip-mode `target-architecture.md` and persist
`target_architecture_path` within this D0 handoff; read
`phases/04-target-architecture.md` for its artifact contract and human gates.
Do not add a Target-Architecture lane or journey phase to the v6 order.

Call `pipeline_mark_decomposition_complete(card_id, session_id, board_id,
manifest_path)` to verify D0 on disk; advance only after it succeeds. Never patch
`d0_closed` or assert adequacy in prose. Unresolved seams require the operator's
`NO_GO_UNRESOLVED_SEAM` backtrack.

**Acceptance obligations:** when a `REAL-DATA`, LIVE test is the sole discharge of
a goal-level requirement, an `acceptance-only` ruling must retain a topology-free
`acceptance_obligations[]` entry: `obligation_id`, `root_goal`, `discharge_test`,
`route_prose`, `missing_evidence_classes[]`, `downstream_owner_phase`. No task edges
or card IDs. `dependency_semantics.py` rejects an `acceptance_oracle` without the
record; Phase 7 Gate D1 closes each obligation by ID through evidence receipts.
Ordinary real-data smoke probes do not trigger this obligation.

After D0, v6 loads leaf cards in Debate for bounded A→S cycles, then joins them
at Pre-Gauntlet for one system gauntlet. Pre-v6 retains its Finalization load path.
Follow the active phase and MCP results for dispatch; preserve G2/G3 approvals.
Consuming-project governing artifacts:
`orchestration/governing/RULESET-bounded-pipeline-v1.md`,
`orchestration/governing/BRAINSTORM-2-lanes-and-flow.md`, and
`orchestration/governing/DECISIONS-brainstorm-2-open.md`.

### User Language → Phase Mapping

| User intent | Target |
|-------------|--------|
| Critique, review, feedback | debate |
| Architecture, patterns | pre-v6 target-architecture; v6 D0 artifact guidance |
| Stress test, attack, gauntlet | gauntlet |
| Finalize, lock the spec | finalize |
| Execution/implementation plan | execution |
| Build, implement | implementation, subject to approval gates |

Debate improves the spec through critic rounds; gauntlet challenges it with
adversary personas. Use the target phase's tools. Gauntlet reviewers stay
read-only; report missing evidence as blocked and carry fixture/claim ceilings.
Mocked logic cannot establish browser, wire, permission, or credential behavior.
See `phases/05-gauntlet.md` and `reference/gauntlet-details.md`.

### Phase Transition Protocol

1. Read target guidance; satisfy its entry gates and persist the outgoing phase's
   deliverables and artifact paths. Preserve G1/G2/G3 evidence, Phase 4 human
   decisions, Phase 6 user review, and Phase 7 plan approval.
2. Atomically write detail (`sessions/<id>.json`) first: `current_phase`,
   `current_step`, `updated_at`, and phase-owned artifact fields. Append the
   transition to the Journey Log. Then atomically write pointer
   (`session-state.json`): `current_phase`, `current_step`, `next_action`,
   `updated_at`. Add missing legacy detail phase fields; never omit either write.
3. Resolve the card from detail `card_id`, legacy `fizzy_card_id`, or pointer
   `pipeline_card_id`. Add a concise comment per § Fizzy Card Comment Convention;
   use `pipeline_advance` with explicit `board_id` for legal board movement.
   Never use `pipeline_patch_state` to transition or skip a fence. On rejection,
   stop and reconcile local/board state through the owning gate.
4. Apply § Major Milestone Notifications (Telegram) when notification is needed.

**Triage exception:** after receipt persistence and
`pipeline_sync_local_session(..., mode="repair")`, atomically merge intake into
returned detail then pointer, set `current_phase: requirements`, and append the
absent `triage → requirements` event. No `pipeline_advance`: the card stays in
Evaluated Plans until the normal requirements-to-roadmap transition.

**Architecture gate:** pre-v6 must visit target-architecture between debate and
gauntlet, even for a stub. v6 must carry that stub from D0; no invented intermediate
phase. Follow Phase 4's artifact/human-gate contract in both cases.

**Completion gates:** after Phase 6 user review, ask whether to generate the Phase
7 execution plan; a decline may close with `execution skipped by user`. Otherwise
validate and obtain approval before loading/implementation; warn on zero actionable
tasks. Offer middleware-creator only for materializable `middleware-candidates.json`
with loaded source cards and test-suite paths. Verification remains inside Phase 8;
follow its sweep gate before closing implemented work. Set `completed_at` on closure.

### Fizzy Card Comment Convention

Every `add_comment` is operator-visible. Use a short outcome heading, one concrete
evidence reference, and the next action/actor; add why it matters only if needed.
Keep normal comments under 180 words. Keep raw JSON, payloads, transcripts, and
checklist dumps in their owning artifacts or pipeline metadata.

### Major Milestone Notifications (Telegram)

Use Telegram for a phase's human-gated review when the user uses that channel;
send routine milestone/status notifications only when requested. Bridge setup and
transport live in `reference/telegram-bridge.md`.

Gate approval must correlate the human reply to the specific gate request and
artifact under review. Uncorrelated same-chat text never approves a gate. If reply
correlation cannot be established, keep the gate pending and seek explicit approval
through the active conversation. `scripts/telegram_bot.py`'s same-chat poller does
not establish that correlation. A timeout, silence, or notification failure never
means approval. Optional notification failure does not block ungated work.

---

## Workspace Bootstrap (Phase 0 GO Only)

During approved Phase 0 GO, create missing `.adversarial-spec/` directories:
`sessions/`, `checkpoints/`, `specs/`, `issues/`, `retrospectives/`, `.backup/`.
Create the pointer through Phase 0's session-sync sequence; never bootstrap for
read-only triage.

## Alignment Prompts

At startup, phase transitions, and checkpoint, offer goal/phase alignment when it
needs confirmation. A refocus updates detail `context.goal` and appends
`goal_history: [{at, from, to, why?}]`; unchanged confirmation creates no log event.

## Decisions Log

Append to `.adversarial-spec/sessions/<id>.decisions.log` after successful
`pipeline_complete_task`, material phase milestones, and user decisions that
foreclose an option. Plain text, one line per decision:

```text
<ISO8601> [<card_id|phase|decision>] <what landed> — <why it matters>
```

Include the commit hash for completed code work. Keep entries concise; put longer
reasoning in retrospectives. Never rewrite the log or substitute a commit message
for the required entry. On resume, read `tail -20` for recent decisions.

## Journey Log

`.adversarial-spec/sessions/<id>.journey.log` is append-only JSONL, one event per
line; it is not an array in the detail JSON. Use a JSON encoder to escape values:

```json
{"time":"ISO8601","event":"Phase transition: <old> → <new>","type":"transition"}
```

Other event types include `artifact`, `create`, `maintenance`, `decision`, and
`resume`. Preserve historical fields and avoid duplicate events on recovery.
For existing records with `idempotency_key`, check that key before appending.
The resume checker reads transition history; load full event bodies only for
investigation/context recovery. For legacy embedded `journey` arrays, use
`scripts/migrate-journey-to-log.py` after reading its invocation and backup rules.

## Checkpoint

Persist deliverables before checkpoint. Follow the `checkpoint-workflow` skill for
checkpoint procedure and the context boundary.

## File Discipline & Orphan Detection

At checkpoint/resume, flag unexpected root Markdown artifacts and suggest their
`.adversarial-spec/` destination. Exclude standard project docs, manifests, and
build/config files. Ask before moving anything; never auto-move.

## Session ID Generation

Format: `adv-spec-YYYYMMDDHHMM-<slug>`. Lowercase the Context name, replace
non-alphanumeric runs with `-`, trim separators, and cap the slug at 32 characters.

## Atomic Writes

All JSON writes use `<path>.tmp` then atomic rename to target. For paired state
updates, detail always precedes pointer; see § Phase Transition Protocol.

## Reference Files (Load On-Demand)

- `reference/current-models.md` — task classes, seats, invocation policy
- `reference/altitude.md` — scope and gate obligations
- `reference/document-types.md` — document types and debug workflow
- `reference/context-addition-protocol.md` — critic context transports
- `reference/advanced-features.md` — focus modes, personas, profiles
- `reference/script-commands.md` — CLI reference
- `reference/gauntlet-details.md` — adversarial gauntlet details
- `reference/convergence-and-telegram.md` — convergence, notification entry points
- `reference/telegram-bridge.md` — Telegram setup and reply transport
