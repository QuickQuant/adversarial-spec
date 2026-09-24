# Phase 0 — Triage (the front door)

Decide, before creating any state, whether this request earns a retained session
and what its smallest useful outcome is. Triage creates no workspace, Fizzy card,
listener, or session file; only a GO does. The First Gate in `SKILL.md` runs first
and owns resume and interrupted-handoff recovery.

**Input:** the change description, plus a plan file if one exists.
**Model:** `reference/altitude.md`.

## Outputs

### 1. Decision

Choose exactly one: the smallest outcome that delivers the request safely. High
blast radius raises the depth of tests and review; on its own it is never a
reason to choose a GO route.

A handoff, plan, or conductor note that names a route ("open a session", "follow
the full pipeline") is input, not the decision. Triage decides. When you choose a
smaller route than the input names, say so and why in the triage output.

GO routes:

- **`repair`** — restore a broken end-to-end path.
- **`bounded-investigation`** — produce a decision receipt; no retained feature
  or implementation card unless a later decision promotes it.
- **`retained-thin-slice`** — prove one useful, end-to-end slice before broader
  hardening or expansion.
- **`full-feature`** — plan the complete approved feature.

NO-GO outcomes (create no state):

- **`direct-action`** — trivial, reversible, component-only, no open questions.
  Do it directly instead of opening a session.
- **`focused-fix`** — a known defect or bounded change in one repository, at any
  blast radius. Its open questions are design choices the operator can rule on in
  one ask round, not research or cross-model debate. Open no session and no card.
  Required instead:
  1. a handoff mini-spec (`handoff-via-spec`): goal, non-goals, acceptance;
  2. test-first, with paired negative oracles and captured failing-first runs;
  3. one independent, read-only code review, with dispositions recorded;
  4. the operator's landing approval, plus a supervised canary when the change
     guards model dispatch or other shared tooling.

  Choose `focused-fix` over a GO route when the risk lives in the code itself, not
  in an unsettled product question: roadmap debate, decomposition, and competing
  implementations cannot find bugs that tests and review would miss.
- **`underspecified`** — the outcome or blast radius is unknown. Name the missing
  facts and ask for them.
- **`stop-defer`** — not now; name the prerequisite or reason.

### 2. Candidate Slice North Star (GO only)

- **Kind:** `ui-target` | `process-output` | `end-to-end-repair`
- **Actor or trigger:** who starts the slice, or what input/event starts it
- **Outcome:** the one observable result that makes this slice worthwhile
- **Thin path:** entry → decisive action/process → useful end state
- **Proof:** what will demonstrate that outcome
- **Not this slice:** adjacent work deliberately deferred

This is an outcome anchor, never a feature inventory. A dashboard, endpoint, or
component name alone is not a North Star. Write `unknown` rather than inventing a
field; Phase 1 resolves unknowns and locks the result into `requirements_summary`.

### 3. Root altitude (GO only) — `component` | `subsystem` | `system`

> **The highest-blast item in the change sets the root.** Any system-altitude item
> forces a `system` root.

- **component** — the whole change is one leaf with a local failure surface.
- **subsystem** — a cohesive unit several components depend on; its contract is
  expensive to reverse.
- **system** — a mistake escapes a code revert: irreversible external
  consequences (prod data loss, destructive ops, irreversible outbound effects),
  or a contract that other repositories or processes consume and that cannot be
  changed in one coordinated release. Launching a subprocess, or being used by
  several repositories, does not by itself make a change `system`.

Name the highest-blast item and why in one line. Derive altitude; never ask the user
to pick it. If the blast radius is unknowable, the decision is `underspecified`.

## On GO — create or reuse one card, preserve the handoff, then bootstrap

1. If `.adversarial-spec/` does not exist, create the standard workspace now — never
   before GO. If this route will touch code, create the dedicated session branch now,
   before any code work.
   The default branch is protected: session work never lands on it directly, and
   merging is a deliberate operator act. If a repo is already on another session's
   branch with a dirty worktree, branch from there and **commit only your own
   files** — never sweep another session's uncommitted work into your commits.
2. Generate the immutable session id and atomically write
   `.adversarial-spec/sessions/<id>.intake.json`. It contains the selected route,
   problem, goal, non-goal, evidence, unknowns, candidate Slice North Star, altitude
   rationale, next durable artifact (`requirements_summary`), creation time, and
   replay-safe card-creation inputs: `session_id`, `title`, `plan_path`,
   `board_id`, and `session_altitude`. This sidecar is the recovery receipt;
   preserve it after the handoff completes.
3. Create or reuse the ordinary session card without local sync:

   ```
   pipeline_create_session(
       session_id=<from receipt>,
       title=<from receipt>,
       plan_path=<from receipt>,
       board_id=<from receipt>,
       sync_local_session=false,
       session_altitude=<from receipt>,
   )
   ```

   Creation is idempotent by session id. Passing `session_altitude` preserves
   `session_altitude_source: "declared"` for later phase rigor. Atomically add the
   returned `card_id` and optional `short_url` to the receipt before writing local
   session state.
4. If `session-state.json` is malformed, empty, or not a JSON object, then — and
   only then — ensure `.adversarial-spec/.backup/` exists, quarantine the pointer to
   `session-state.invalid-<UTC timestamp>.json`, and record that path in the receipt.
   Do not overwrite a syntactically valid pointer until the First Gate has proved it
   absent or zombie. Next repair local state:

   ```
   pipeline_sync_local_session(
       session_id=<from receipt>,
       card_id=<from receipt>,
       board_id=<from receipt>,
       mode="repair",
   )
   ```

   Repair safely replaces an absent or proven-zombie valid pointer without creating
   another card.
5. Follow `SKILL.md`'s local-only `triage → requirements` exception: merge the
   staged receipt into the returned detail as `intake`, retain `intake_path`, set
   both local files to `current_phase: requirements`, set the next action to
   validate the Slice North Star, and append the journey event only if absent.
   Preserve the card identifiers returned by sync. Do **not** call
   `pipeline_advance` or move the card.
6. If interrupted, the First Gate recovers this same receipt: rerun the idempotent
   card creation with its session id, persist the returned card id, repair local
   sync, then merge the receipt. Never re-run triage, mint a new id, or create a
   second card for that receipt.
7. Return to `SKILL.md` for conductor/listener bootstrap, then enter Phase 1.

## Output template

```
## Triage

Decision: <repair|bounded-investigation|retained-thin-slice|full-feature|direct-action|focused-fix|underspecified|stop-defer>
Route input: <route named by the handoff/plan, or none> — <kept | narrowed: why>
Candidate Slice North Star:            (GO only)
  Kind: <ui-target|process-output|end-to-end-repair>
  Actor or trigger: <…>
  Outcome: <…>
  Thin path: <…>
  Proof: <…>
  Not this slice: <…>
Root altitude: <level> — highest-blast item: <item>, because <why>   (GO only)
NO-GO detail: <direct action | focused fix: repo + review seat + landing gate | missing facts | prerequisite>   (NO-GO only)
```

Example:

```
## Triage

Decision: retained-thin-slice
Candidate Slice North Star:
  Kind: process-output
  Actor or trigger: operator starts /adversarial-spec with a new request
  Outcome: the request lands in Phase 1 with its route and handoff preserved
  Thin path: request → triage decision → one card + local session → Phase 1
  Proof: cold-start and interrupted-resume walkthroughs reach the same session
  Not this slice: downstream debate and board-lane semantics
Root altitude: subsystem — highest-blast item: the router edit, because every
  project's sessions consume it, yet a bad edit is caught at session start and
  reverted with one commit
```
