# Phase 0 — Triage (the front door)

**This runs before new session machinery.** The First Gate's read-only pointer
and staged-receipt probe is the sole exception: it establishes whether an active
session must resume or an accepted GO needs recovery, but creates and mutates
nothing. Receipt recovery continues a prior GO; it is never a fresh triage action.
For new work, triage has no conductor registration, Fizzy card, wake listener,
workspace, or `session-state.json`. Only *after* a GO do you create state and let
the rest of the pipeline bootstrap.

> If triage needs a Fizzy card or a listener to run, it has failed its purpose.
> The whole point is to answer "is this worth a retained session, and what is the
> smallest useful outcome?" before committing state.

**Read with this:** `reference/altitude.md` is the model. This doc applies it.

## Inputs

Just the change description (what the user wants built or fixed). Optionally the
plan file if one exists. Nothing else.

## Outputs (produce all five, in this order)

### 1. Intent, route, and candidate Slice North Star

Choose exactly one route:

- **`repair`** — restore a broken end-to-end path.
- **`bounded-investigation`** — produce a decision receipt; no retained feature
  or implementation card unless a later decision promotes it.
- **`retained-thin-slice`** — prove one useful, end-to-end slice before broader
  hardening or expansion.
- **`full-feature`** — plan the complete approved feature.
- **`stop-defer`** — no session now; name the prerequisite or reason.

For every route except `stop-defer`, capture a **candidate Slice North Star**:

- **Kind:** `ui-target` | `process-output` | `end-to-end-repair`
- **Actor or trigger:** who starts the slice, or what input/event starts it
- **Outcome:** the one observable result that makes this slice worthwhile
- **Thin path:** entry → decisive action/process → useful end state
- **Proof:** what will demonstrate that outcome
- **Not this slice:** adjacent work deliberately deferred

This is an outcome anchor, never a feature inventory. A dashboard, endpoint, or
component name alone is not a North Star. Phase 1 tests and locks the candidate
into the durable `requirements_summary`.

### 2. Complexity tier — `simple` | `medium` | `complex`

Key off **two signals only: integrations + unknowns.** (Reversibility/consequence
is NOT complexity — it is altitude. Don't double-count it.)

- **simple** — few/no new integrations, no real open questions. One agent, a handful of tasks.
- **medium** — a routing/contract decision or a few open questions, or several integrations.
- **complex** — many external SDKs/services to wire AND several genuinely open design questions.

There is no numeric score. Complexity decides **execution shape only** (single agent
vs. workstreams) — it does not change rigor. A high-blast change can be *simple* to
execute and still earn *system* rigor.

### 3. Root altitude — `component` | `subsystem` | `system`

Apply the **forcing rule** (`reference/altitude.md` §2):

> **Pick the highest-blast item in the change. That item's altitude is the root.**
> Any system-altitude node ⇒ the root must be `system`.

- **component** — the whole change is one leaf with a local failure surface.
- **subsystem** — a cohesive unit several components depend on; contract expensive to reverse.
- **system** — *any* node crosses a process/repo boundary OR has **irreversible
  external consequences a code revert can't undo** (prod data loss, destructive
  ops, irreversible outbound effects; moving money is one instance, not the
  definition).

State, in one line, *which item* is the highest-blast item and *why* it sets the root.

**Altitude is DERIVED, never asked.** Do not prompt the user to pick or confirm the
altitude (immutability is a reason to derive carefully, not to ask). If the blast
radius is genuinely unknowable, that is a NO-GO *underspecified* — ask for the
missing facts, not for the altitude.

### 4. Tree sketch

One block: nodes with their altitudes, honoring the minimum tree shape for the root
(`reference/altitude.md` §2) and the strict parent>child altitude rule. Keep it to
the real decomposition — don't invent nodes to look thorough.

### 5. Go / no-go

- **GO** — worth the pipeline. State the rigor it earns per tier (the verification
  ladder, `reference/altitude.md` §4) and the gauntlet roster weight (§6).
- **NO-GO** — and say which:
  - *Too small* — a trivial, reversible, component-only change with no open
    questions. Recommend doing it directly (plan-mode edit), not spinning up a
    session. Proportional rigor cuts *down to direct action*, not just down a tier.
  - *Underspecified* — you cannot pick a root because the blast radius is unknown.
    Say exactly what's missing and ask for it before proceeding.

## On GO — create or reuse one card, preserve the handoff, then bootstrap

1. If `.adversarial-spec/` does not exist, create the standard workspace now — never
   before GO. If this route will touch code, create the dedicated session branch now,
   before any code work.
2. Generate the immutable session id and atomically write
   `.adversarial-spec/sessions/<id>.intake.json`. It contains the selected route,
   problem, goal, non-goal, evidence, unknowns, candidate Slice North Star, next
   durable artifact (`requirements_summary`), creation time, and replay-safe
   card-creation inputs: `session_id`, `title`, `plan_path`, `board_id`, and
   `session_altitude`. This sidecar is the recovery receipt; preserve it after the
   handoff completes.
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

> v3/v2 (pre-altitude) sessions are grandfathered: they never declare an altitude
> and the `_pipeline_version >= 4` fences leave them exactly as before.

## Worked example (this front door's own triage)

> **Change:** add a discoverable triage front door to the adversarial-spec skill —
> `phases/00-triage.md`, `reference/altitude.md`, a router entry, a plan template.

1. **Route: retained-thin-slice.** Candidate North Star: an operator can start a
   new request, see the selected route and handoff, and resume the same Phase 1
   session after interruption. Proof: cold-start and resume walkthroughs. Not this
   slice: changing downstream debate or board-lane semantics.
2. **Complexity: medium.** Integrations: low (skill docs + one router edit, no new
   service). Unknowns: a few (wire the router without breaking in-flight sessions;
   rubric numeric-vs-numberless). → not simple, not complex.
3. **Root altitude: subsystem.** Highest-blast item = the **router edit**: it changes
   a phase-routing contract every project's sessions consume, so a bad edit breaks
   routing broadly. That is subsystem (several consumers depend on it) — *not*
   system: it moves nothing irreversible and a bad edit is caught at session-start
   and reverted with one commit. No system node ⇒ root is not forced to system.
4. **Tree:**
   ```
   SS  triage front door                              [subsystem]
   ├─ C  reference/altitude.md (single page)          [component]
   ├─ C  phases/00-triage.md (this front door)        [component]
   ├─ C  plan template                                [component]
   └─ SS router wiring (additive, grandfathering)     [subsystem]  ← highest blast
   ```
5. **GO.** Component docs earn a cold-read comprehension test. The router edit
   earns a cold-start and in-flight-resume walkthrough. Light gauntlet roster.

## Output template

```
## Triage

Route: <repair|bounded-investigation|retained-thin-slice|full-feature|stop-defer>
Candidate Slice North Star:
  Kind: <ui-target|process-output|end-to-end-repair>
  Actor or trigger: <…>
  Outcome: <…>
  Thin path: <…>
  Proof: <…>
  Not this slice: <…>
Complexity: <tier>  — signals: integrations=<…>, unknowns=<…>
Root altitude: <level>  — highest-blast item: <item>, because <why>
Tree:
  <node>  [<altitude>]
  └─ …
Go / no-go: <GO|NO-GO>  — <rigor per tier, or the reason + what's needed>
```
