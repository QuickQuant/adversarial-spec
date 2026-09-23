## Implementation (Phase 8)

```text
TodoWrite([
  {content: "Resolve the active Session, agent identity, and explicit board ID", status: "in_progress", activeForm: "Resolving implementation identity"},
  {content: "Load the approved plan, spec, and targeted architecture context [GATE]", status: "pending", activeForm: "Loading implementation context"},
  {content: "Run required pseudo-to-real promotion preflight", status: "pending", activeForm: "Checking promotion obligations"},
  {content: "Inspect, claim, and act on the pipeline-returned action", status: "pending", activeForm: "Processing pipeline work"},
  {content: "Preserve scoped evidence and independent review [GATE]", status: "pending", activeForm: "Recording implementation evidence"},
  {content: "Resolve operator-owned work without agent self-attestation [GATE]", status: "pending", activeForm: "Resolving operator work"},
  {content: "Close system-altitude validation when obligated [GATE]", status: "pending", activeForm: "Closing system validation"},
  {content: "Enter the Phase 8 verification subflow", status: "pending", activeForm: "Entering final verification"},
])
```

Phase 8 starts only after the approved execution plan has passed
`pipeline_validate_plan` and its Task Cards have been created by `pipeline_load`.
Do not ask for a second implementation approval. Missing cards or an unapproved
plan return control to Phase 7.

### Pseudo-to-real promotion pass

For every active TMR row whose data strategy is `REAL-DATA` or
`REAL-DATA + PROPERTY` and which is a happy-path spine or critical seam:

1. Use `phase8_promotion.build_promotion_requests` to emit a typed request with
   the TMR/test/story identity, bound accessors, owner-repo command, cwd, repo,
   commit, and `negative_oracle_required: true`.
2. The owner repo authors and binds the test. Do not trust an owner-authored
   pass/fail claim.
3. The skill runner executes the declared command and captures trusted
   `run_evidence`, including result, environment, artifact URI/hash, and the
   live-or-induced technique when required.
4. Reject unbound accessors, missing negative oracles, exempt/spike critical
   rows, non-green or untrusted evidence, and boundary-mock violations according
   to the deterministic report.

`evaluate_phase8_close` has three cutover modes; state the selected mode in the
close report:

| Mode | Actual behavior |
|---|---|
| `legacy` (default) | Reads record-level `run_evidence`; required missing evidence is a blocking `run_evidence_missing` issue. |
| `warn` | Evaluates target-observation comparison context, but its identity/freshness/terminal gaps are warnings. Core accessor, negative-oracle, exempt-mode, and supplied-evidence checks keep their own severities. |
| `reject` | The same target-observation gaps are halts. Core checks still apply. |

Do not claim that null evidence fails identically in every cutover mode. At
`warn`, a target-observation gap is transitional warning behavior; record it
rather than describing it as enforced rejection.

For altitude-aware work, append close-time `altitude_fit` provenance. Only
`altitude_fit: right` is a correct fit; `too_low` and `too_high` remain precision
failures even if the code is stable.

### Identity and setup

Use a stable pipeline agent alias on every call so independent-review checks can
distinguish implementer and reviewer. Agent aliases are not model transport
names. See `skills/adversarial-spec/reference/current-models.md` for the current
seat/transport mapping.

Before pickup:

- Resolve `session_id` from the invocation or active session pointer. Stop if no
  active Session exists.
- Resolve `board_id` from project/session configuration and pass it explicitly
  on every board-scoped call. Never rely on a server default.
- Confirm the expected Task Cards with
  `pipeline_lane_state(pipeline="task", session_id=SESSION_ID, board_id=BOARD_ID)`.
- Read the project instruction file, approved spec, approved execution plan,
  `.architecture/INDEX.md`, `.architecture/primer.md`, relevant codebase
  Concerns, and only the component/flow docs referenced by the current card.

Read enough of the spec/plan to understand the current card's purpose and
constraints. The card carries the bounded work; the artifact chain supplies the
why.

### Inspect → claim → act

Use a read-only inspection before deciding to work or reporting status:

```text
pipeline_next_actions(session_id=SESSION_ID, agent=AGENT, board_id=BOARD_ID)
# or
pipeline_lane_state(pipeline="task", session_id=SESSION_ID, agent=AGENT, board_id=BOARD_ID)
```

If `attention.session_context.kind` is `session_card_missing`, stop. Task Cards
have lost their parent Session Card; do not claim, sweep, or archive until the
board relationship is repaired.

Only when ready to perform whatever the scheduler returns, claim through:

```text
pipeline_do_next_task(
  session_id=SESSION_ID,
  pipeline="task",
  agent=AGENT,
  board_id=BOARD_ID,
)
```

Act on the returned action. The MCP owns claim CAS, leases, assignment display,
lane priority, rework reservations, and self-review rejection. Do not reproduce
or bypass those mechanics; use the tool for each situation:

| Situation | Tool (always with explicit `board_id`) |
|---|---|
| Long work on a claimed card | `pipeline_heartbeat(agent, event="beat", board_id, card_id)` keeps the lease; `event="idle"` clears presence. |
| Claimed but cannot begin | `pipeline_release_claim(session_id, card_id, agent, reason, board_id)` |
| A specific worker should take it next | `pipeline_handoff_claim(session_id, card_id, agent, to_agent, reason, board_id)` — atomic, no pickup gap |
| Blocked by something outside the card | `pipeline_block_task(session_id, card_id, agent, reason, board_id, blocker_type, evidence)`; `blocker_type` ∈ `known_red_baseline`, `external_dependency`, `environment`, `human_decision`, `human_execution`, `pipeline_bug`, `other` |
| Blocker resolved | `pipeline_unblock_task(session_id, card_id, agent, reason, board_id)` |

Follow `SKILL.md` § Fizzy Card Comment Convention for operator-visible updates.
Keep structured payloads and attestations in metadata/tool results.

#### `implement` or `fix`

1. Read the card description, acceptance steps, declared refs, and review notes
   for a fix.
2. Modify only the card's declared scope and preserve the Architecture Spine.
3. Execute its declared verification commands plus required adjacent checks.
4. Stage explicit paths only. Never sweep unrelated dirty-worktree changes into
   the card commit.
5. Commit with the task identity, then call `pipeline_complete_task` with the
   exact commit and explicit `board_id`.
6. Record only material landing decisions. See `SKILL.md` § Decisions Log.

Evidence precedes completion claims. A passing command that collected zero
tests is not evidence.

#### `review`

The reviewer must differ from the implementer. Read the exact commit and select
a proportional recipe:

| Diff size | Review |
|---|---|
| up to 30 changed lines | Inspect the full diff, acceptance criteria, and declared tests. |
| 31–200 | Add failure-path and new-file checks. |
| 201–800 | Also check the relevant spec section, coverage, adjacent integrations, and structural conformance. |
| above 800 | Request decomposition unless the card explicitly authorizes generated/vendor-scale output and supplies a file-by-file walkthrough. |

Submit `pipeline_review(session_id, card_id, agent, verdict, board_id, notes)` with
`verdict` ∈ `approved` | `changes_requested`; `changes_requested` requires
actionable notes. Do not approve from a summary or self-review your own card.

#### `test`

Run the declared commands against the committed implementation and submit
`pipeline_test(session_id, card_id, agent, result, summary, board_id, ...)` with
`result` ∈ `pass` | `fail`. Behavior-changing automated cards also require
`executed_verify_commands` and `verification_evidence_summary`. Keep the summary
bounded but include the commands, counts, and relevant failure.

When inspection reports a human attestation, do not claim or test it. Surface
the evidence and requested decision; the operator records it through
`pipeline_attest_task`.

#### Human decisions

A `human_decision` block is an operator question. Its card must contain a short
`HUMAN BRIEF:` explaining the product decision and choices without making the
operator decode internal IDs. Preserve the rigorous machine reason separately.
Surface it under the notification rule in `SKILL.md`; a board-only question is a
silent stall. If the operator defers, update the blocker to the true external
dependency and name its unblocking artifact.

#### Human execution

For `blocker.kind: human_execution`:

- Never claim or implement the card.
- Present its exact `HUMAN ACTION:`, procedure, stop conditions, and evidence
  destination.
- Resolve only through `pipeline_complete_human_task`, with literal evidence for
  every acceptance step. Never invent, summarize as firsthand, or self-attest
  operator evidence.
- Respect scope: `global` stops all workers; `dependency` leaves unrelated safe
  work claimable.

Do not substitute `pipeline_attest_task`, `pipeline_test`, or a manual card move.

#### `idle`

Read `attention.next_actions`, `attention.human_actions`, and
`attention.blocked`. Report the named next actor and blocker, then stop. Do not
poll by repeatedly calling the claiming tool.

### Structural and scope conformance

The approved plan's file structure and boundaries are a contract. Do not create,
rename, split, or move implementation files outside it merely because a local
shape feels cleaner.

If new implementation work is needed, amend the execution plan and
`fizzy-plan.json`, obtain required approval, run `pipeline_validate_plan`, and
then `pipeline_load`. A Card comment may record an investigation; it does not
authorize unplanned delivery. Never raw-create a Task Card for an active Session.

See `SKILL.md` § Journey Log for durable workflow events and § Phase Transition
Protocol for checkpoint/transition ownership.

### Validation strategy

For test-first work, write the card's acceptance tests before implementation.
Keep expected-red tests out of the suite-wide default collection until the
implementing card makes them green. Use a quarantined path invoked only by the
card's command, or the framework's explicit todo/skip marker with an unblocking
Card reference. Remove the quarantine when the implementation lands.

For test-after work, implement the bounded behavior and then add tests covering
all acceptance criteria and Concern failure modes.

For `spike`, commit no promised automated suite, but still discharge the
declared exempt/manual verification and reason. A live-spine owner cannot be a
spike or exempt task.

### System-altitude validation leg

Run this leg only when card metadata, read with explicit `board_id`, shows that
the system node owes the pipeline-v5+ system-validation obligation. Component
and subsystem nodes skip it.

Phase 7 drafted the ConOps-bound ledger. Phase 8 executes scenarios, obtains the
operator's judgments, emits the close artifact, and closes the distinct
validation gate. The scripts mechanize shape and hashes; they do not write the
scenario prose or make the human judgment.

The close target is the single **system-altitude Task Card**, not the Session
Card. Confirm `card_type: task`, `altitude: system`, and
`parent_session_id == SESSION_ID` before calling:

```text
pipeline_mark_system_validation_complete(
  card_id=SYSTEM_NODE_CARD_ID,
  session_id=SESSION_ID,
  board_id=BOARD_ID,
  validation_artifact_path="<slug>/system_validation.json",
  conops_path="<slug>/roadmap/conops.md",
)
```

Use this re-entrant ordering:

1. Resolve the system node from the board; read metadata. If already complete,
   jump to readback. Verify the worktree and Phase 7 artifacts, re-derive ConOps,
   compare hashes, and surface unexplained baseline drift.
2. Confirm verification obligations and reviews are discharged.
3. Execute every active unjudged scenario and attach commit-bound evidence with
   `record-evidence`.
4. Run `assemble-digest`. If no rows remain but failures exist, remediate; if no
   failures exist, proceed to emission.
5. Route the digest for correlated operator judgment using the notification rule
   in `SKILL.md`. Parse and apply replies; an uncorrelated message cannot approve
   a gate.
6. On failure, cancel any open remainder, create plan-backed remediation work,
   resolve it, `reset-failed`, and re-execute the scenario.
7. Run `emit-system-validation`, then `self-check` on the exact file.
8. Recheck the artifact hash, call the MCP close tool, and resolve a lost response
   by reading metadata rather than blindly re-emitting.
9. Confirm `system_validation_complete: true` by metadata readback, then commit
   the evidence artifacts.

Every re-entry starts at step 1. `NOTHING_TO_DIGEST` is a branch, not proof of
success. `self-check` and the hash guard run before every close attempt.

#### System-validation error-class playbook

Keep these eight served-code responses current. Do not force or patch around any
reject.

| Gate reject | Required response |
|---|---|
| `SESSION_MISMATCH` | Confirm the target is the system Task Card and belongs to this Session; never retarget another Session's card. |
| `VV_NOT_OBLIGATED_AT_ALTITUDE` | Stop and reconcile altitude/triage; do not force validation onto a lower node. |
| `VALIDATION_KIND_MISMATCH` | Regenerate with `emit-system-validation`; do not hand-edit the artifact kind. |
| `VALIDATION_ARTIFACTS_INCOMPLETE` | Run `self-check`, repair every reported artifact/coverage issue, and re-emit. |
| `VV_LEDGER_HAS_FAILURES` | Return to the remediation loop; a failed row cannot close. |
| `VALIDATION_IS_RELABELED_VERIFICATION` | Redraft from ConOps intent and remove verification-only oracles/targets. |
| `SYSTEM_VALIDATION_MISSING` | Run this close leg for the obligated system node before final advance. |
| `UNVALIDATED_USER_STORY` | Add or repair a passing row for every uncovered ConOps story, then rerun close. |

Local script routing:

| Code family | Response |
|---|---|
| `LEDGER_BUSY` | Check the active owner; bounded retry only. Follow file-lock stale handling when proven stale. |
| `LEDGER_CORRUPT` | Restore from committed bytes and replay quarantined evidence; never overwrite the corrupt copy silently. |
| `NOTHING_TO_DIGEST` | Failures present → remediation; otherwise → emission. |
| sender/allowlist/reply errors | Repair correlation/configuration and re-feed the exact operator response. |
| stale digest/row/ConOps | Regenerate the digest from current bytes and identify the superseded digest. |
| evidence missing/malformed/hash/stale | Re-execute the named scenario and record fresh evidence. |
| `SELF_CHECK_FAILED` | Fix issues and re-emit; do not call the MCP close tool. |
| `ARTIFACT_SHA_MISMATCH` | Re-emit and self-check the fresh artifact before retrying. |
| `ANTI_RELABELING_UNCHECKED` | Supply the verification ledger when verification artifacts exist. |

### Enter the verification subflow

When the scheduler returns `action: sweep`, implementation cards have reached
the sweep boundary; they are not complete yet. Do not sweep from this loop.

Set `current_phase: implementation` and `current_step: verification` in the
active detail and pointer using the transition protocol, then follow
`09-verification.md`. Verification performs the whole-change judgment and calls
either `pipeline_sweep` or `pipeline_sweep_fail`.

Stop the pickup loop while verification owns the flow. Do not use
`pipeline_patch_state` to bypass verification or a human fence.
