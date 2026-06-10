# Phase 0 — Triage (the front door)

**This runs BEFORE any session machinery.** No conductor registration, no Fizzy
card, no wake listener, no `session-state.json`. Triage is a cheap go/no-go gate
whose entire cost is reading a change description and thinking. Only *after* a GO do
you create a session and let the rest of the pipeline bootstrap.

> If triage needs a Fizzy card or a listener to run, it has failed its purpose.
> The whole point is to answer "is this even worth the full pipeline, and how
> deep?" before committing any state.

**Read with this:** `reference/altitude.md` is the model. This doc applies it.

## Inputs

Just the change description (what the user wants built or fixed). Optionally the
plan file if one exists. Nothing else.

## Outputs (produce all four, in this order)

### 1. Complexity tier — `simple` | `medium` | `complex`

Key off **two signals only: integrations + unknowns.** (Reversibility/consequence
is NOT complexity — it is altitude. Don't double-count it.)

- **simple** — few/no new integrations, no real open questions. One agent, a handful of tasks.
- **medium** — a routing/contract decision or a few open questions, or several integrations.
- **complex** — many external SDKs/services to wire AND several genuinely open design questions.

There is no numeric score. Complexity decides **execution shape only** (single agent
vs. workstreams) — it does not change rigor. A high-blast change can be *simple* to
execute and still earn *system* rigor.

### 2. Root altitude — `component` | `subsystem` | `system`

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

### 3. Tree sketch

One block: nodes with their altitudes, honoring the minimum tree shape for the root
(`reference/altitude.md` §2) and the strict parent>child altitude rule. Keep it to
the real decomposition — don't invent nodes to look thorough.

### 4. Go / no-go

- **GO** — worth the pipeline. State the rigor it earns per tier (the verification
  ladder, `reference/altitude.md` §4) and the gauntlet roster weight (§6).
- **NO-GO** — and say which:
  - *Too small* — a trivial, reversible, component-only change with no open
    questions. Recommend doing it directly (plan-mode edit), not spinning up a
    session. Proportional rigor cuts *down to direct action*, not just down a tier.
  - *Underspecified* — you cannot pick a root because the blast radius is unknown.
    Say exactly what's missing and ask for it before proceeding.

## On GO — create the session WITH the altitude (the one wiring step)

Triage's output is not advisory paperwork — the root altitude becomes a first-class
session attribute. Create the session passing it explicitly:

```
pipeline_create_session(
    session_id=<new id>,
    title=<change title>,
    plan_path=<plan path>,
    board_id=BOARD_ID,
    session_altitude="<root from step 2>",   # ← carries triage forward
    ...
)
```

This stamps `session_altitude_source: "declared"` and lets Phase 1/4/5/7 inherit the
depth instead of defaulting an undeclared session to `system` (full rigor for
everything). Then route to `phases/01-init-and-requirements.md` and continue.

> v3/v2 (pre-altitude) sessions are grandfathered: they never declare an altitude
> and the `_pipeline_version >= 4` fences leave them exactly as before.

## Worked example (this front door's own triage)

> **Change:** add a discoverable triage front door to the adversarial-spec skill —
> `phases/00-triage.md`, `reference/altitude.md`, a router entry, a plan template.

1. **Complexity: medium.** Integrations: low (skill docs + one router edit, no new
   service). Unknowns: a few (wire the router without breaking in-flight sessions;
   rubric numeric-vs-numberless). → not simple, not complex.
2. **Root altitude: subsystem.** Highest-blast item = the **router edit**: it changes
   a phase-routing contract every project's sessions consume, so a bad edit breaks
   routing broadly. That is subsystem (several consumers depend on it) — *not*
   system: it moves nothing irreversible and a bad edit is caught at session-start
   and reverted with one commit. No system node ⇒ root is not forced to system.
3. **Tree:**
   ```
   SS  triage front door                              [subsystem]
   ├─ C  reference/altitude.md (single page)          [component]
   ├─ C  phases/00-triage.md (this front door)        [component]
   ├─ C  plan template                                [component]
   └─ SS router wiring (additive, grandfathering)     [subsystem]  ← highest blast
   ```
4. **GO.** Component docs earn a cold-read comprehension test (a fresh model on a
   different family must produce a correct tree from the docs alone). The router
   edit (subsystem) earns an integration check: a real session-start proves triage
   runs before machinery AND an in-flight session still routes from its current
   phase. Light gauntlet roster (subsystem, nothing irreversible).

## Output template

```
## Triage

Complexity: <tier>  — signals: integrations=<…>, unknowns=<…>
Root altitude: <level>  — highest-blast item: <item>, because <why>
Tree:
  <node>  [<altitude>]
  └─ …
Go / no-go: <GO|NO-GO>  — <rigor per tier, or the reason + what's needed>
```
