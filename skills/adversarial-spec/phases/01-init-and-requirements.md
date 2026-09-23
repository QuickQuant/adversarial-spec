> **FIRST ACTION upon entering this phase:** Restore `todowrite_snapshot` when it
> exists; otherwise create this TodoWrite immediately. Do NOT replace a restored
> snapshot with a fresh checklist. Every `[GATE]` item must be completed before
> proceeding past it.

```
TodoWrite([
  {content: "Resolve intake handoff and document type", status: "in_progress", activeForm: "Resolving intake handoff"},
  {content: "Identify missing starting-point facts", status: "pending", activeForm: "Identifying missing starting-point facts"},
  {content: "Offer interview mode (spec only)", status: "pending", activeForm: "Offering interview mode"},
  {content: "Conduct interview for unresolved facts", status: "pending", activeForm: "Conducting requirements interview"},
  {content: "Lock Slice North Star [GATE]", status: "pending", activeForm: "Locking Slice North Star"},
  {content: "Build RequirementsSummary (user_types, features, integrations, unknowns, slice_north_star)", status: "pending", activeForm: "Building requirements summary"},
  {content: "User confirms requirements before roadmap [GATE]", status: "pending", activeForm: "Awaiting user requirements confirmation"},
])
```

Mark each step `completed` as you finish it. For debug investigations, mark only
the optional interview steps complete when they are not needed; the Slice North Star
gate still applies.

### Treatment-Originated Session Shortcut

If the active session has `"origin": "treatcodebase"` in its session detail file:

1. Read the pre-plan. If it contains a valid `slice_north_star`, restore the
   snapshot and mark only the already-satisfied Phase 1 items completed.
2. If it lacks one, keep the normal Slice North Star gate active. Do not bypass it
   merely because diagnosis or a pre-plan exists.
3. On **"Review roadmap"**: transition to Phase 02 only after both the North Star
   and requirements confirmation gates are complete.
4. On **"Show pre-plan"**: print the Diagnosis Summary and Top 3 Concerns, then
   return to the unresolved Phase 1 item.
5. On **"Start fresh"**: clear `origin` and `pre_plan_path` from session detail.
   The pre-plan remains on disk for reference.

---

## Tracking

| Store | Owns |
|-------|------|
| Fizzy session card | Lane, board-visible gates, claims, review/test lifecycle |
| `todowrite_snapshot` | Phase checklist; restore on resume, create only when absent |
| `requirements_summary` | Accepted requirements, boundaries, and Slice North Star |

Complete human gates only after the user accepts their outputs. Use pipeline tools
with explicit `board_id`; tool results and card state own board progress.

**Happy-path spine seed:** Assign stable user story IDs during requirements capture
so Phase 2 can author exactly one happy-path spine designation per US. Capture the
primary-success path in plain language; branch/failure tests later anchor to named
steps through `spine_step_ref` and `spine_of`.

## Setup and Document Contract

For provider configuration, see [SETUP.md](../SETUP.md).
For document type/depth, required sections, and evidence-led debug investigation,
see [document-types.md](../reference/document-types.md).
Derive and record root altitude using [altitude.md](../reference/altitude.md).
Use machine-extractable requirement IDs and observable, WHAT-not-HOW `shall`
statements; see the `REQUIREMENT_ID_RE` and `lint_requirement_text` contract in
[mini_spec_emission.py](../scripts/mini_spec_emission.py).

See SKILL.md § [Phase Transition Protocol](../SKILL.md#phase-transition-protocol).
See SKILL.md § [Decisions Log](../SKILL.md#decisions-log).

## Process

### Phase 1 Entry

The First Gate and Phase 0 own context detection and session creation. Do not create
a workspace, session, branch, or Fizzy card here.
1. Read the active detail file's `intake` and its `intake_path` sidecar when present.
2. Restore `todowrite_snapshot`; otherwise use this phase's fresh checklist.
3. Treat a missing `intake` as a legacy session: perform normal discovery and create
   a Slice North Star here. Never restart Phase 0 or discard the active session.
4. Intake facts prefill Phase 1. Ask only for unknown, ambiguous, or contradicted
   facts; do not repeat settled route, problem, evidence, or boundary questions.

### Step 1: Resolve Intake and Missing Facts

Use the handoff to establish document type/depth, starting point, and whether a
full interview is useful. Resolve only absent or uncertain fields:

1. **Document type/depth** — `spec` / `debug`; for specs, product, technical, or full.
2. **Starting point** — an existing file, evidence source, or the change description.
3. **Interview mode** — optional for specs; use it when material requirements remain
   unknown. Debug investigations may proceed directly to evidence gathering.

Do not treat a candidate route as permission to skip requirements confirmation.
`bounded-investigation` still needs a decision-output North Star; `repair` still
needs the repaired end-to-end path.

### Step 1.25: Lock Slice North Star [GATE]

Before building RequirementsSummary, turn the intake candidate into exactly one
confirmed Slice North Star:

```markdown
## Slice North Star

Kind: ui-target | process-output | end-to-end-repair
Actor or trigger: <who starts the slice, or what starts it>
Outcome: <one observable result that makes the slice worthwhile>
Thin path: <entry → decisive action/process → useful end state>
Proof: <demonstration, observation, or measurement>
Not this slice: <adjacent work deliberately deferred>
```

Rules:

- It is an outcome anchor, never a feature inventory. A dashboard, endpoint, or
  component name alone fails the gate.
- A `ui-target` names the primary surface and decisive user action.
- A `process-output` names the input, produced output, and usable quality bar.
- An `end-to-end-repair` names the former failing trigger and the repaired successful
  completion.
- Keep one North Star. Additional valuable behavior belongs in later work or an
  explicit non-goal.

Store the confirmed block as `requirements_summary.slice_north_star`. Complete this
gate only when the user accepts the block.


### Step 1.5: Interview Mode (If Selected)

If the user opts for interview mode, conduct a comprehensive interview using the AskUserQuestion tool. This is NOT a quick Q&A; it's a thorough requirements gathering session.

**If an existing spec file was provided:**
- Read the file first
- Use it as the basis for probing questions
- Identify gaps, ambiguities, and unstated assumptions

**Interview Topics (cover ALL of these in depth):**

1. **Problem & Context**
   - What specific problem are we solving? What happens if we don't solve it?
   - Who experiences this pain most acutely? How do they currently cope?
   - What prior attempts have been made? Why did they fail or fall short?

2. **Users & Stakeholders**
   - Who are all the user types (not just primary)?
   - What are their technical sophistication levels?
   - What are their privacy/security concerns?
   - What devices/environments do they use?

3. **Functional Requirements**
   - Walk through the core user journey step by step
   - What happens at each decision point?
   - What are the error cases and edge cases?
   - What data needs to flow where?

4. **Technical Constraints**
   - What systems must this integrate with?
   - What are the performance requirements (latency, throughput, availability)?
   - What scale are we designing for (now and in 2 years)?
   - Are there regulatory or compliance requirements?

5. **UI/UX Considerations**
   - What is the desired user experience?
   - What are the critical user flows?
   - What information density is appropriate?
   - Mobile vs desktop priorities?

6. **Tradeoffs & Priorities**
   - If we can't have everything, what gets cut first?
   - Speed vs quality vs cost priorities?
   - Build vs buy decisions?
   - What are the non-negotiables?

7. **Risks & Concerns**
   - What keeps you up at night about this project?
   - What could cause this to fail?
   - What assumptions are we making that might be wrong?
   - What external dependencies are risky?

8. **Success Criteria**
   - How will we know this succeeded?
   - What proof satisfies the Slice North Star?
   - What metrics matter?
   - What intentionally valuable work is deferred from this slice?

**Interview Guidelines:**
- Ask probing follow-up questions. Don't accept surface-level answers.
- Challenge assumptions: "You mentioned X. What if Y instead?"
- Look for contradictions between stated requirements
- Ask about things the user hasn't mentioned but should have
- Continue until you have enough detail to write a comprehensive spec
- Use multiple AskUserQuestion calls to cover all topics

**After interview completion or gap resolution:**
1. Synthesize intake and new evidence into a RequirementsSummary, including
   `slice_north_star`.
2. Present the RequirementsSummary and confirmed Slice North Star together.
3. Mark both the Slice North Star and requirements-confirmation gates complete only
   after the user accepts them, then enter [Phase 2: Roadmap](02-roadmap.md).
