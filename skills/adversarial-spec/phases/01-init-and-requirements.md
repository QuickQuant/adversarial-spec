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

## Task-Driven Workflow

**CRITICAL: At the start of every adversarial-spec session, set up tracking at two levels.** This ensures you never lose track of where you are in the process.

### Tracking System

Adversarial-spec uses three complementary stores:

| Level | Mechanism | What it tracks | Persists across sessions? |
|-------|-----------|----------------|--------------------------|
| **Pipeline** | Fizzy card | Lane, board-visible gates, claims, review/test lifecycle | Yes — visible on the board |
| **Phase checklist** | `todowrite_snapshot` | In-progress and completed phase steps | Yes — checkpointed in session detail and restored |
| **Decisions** | `requirements_summary` | Accepted requirements, boundaries, and Slice North Star | Yes — durable semantic record |

**Fizzy pipeline** (session-level):
- Every session gets a card via `pipeline_create_session` on the project's Fizzy board.
- The card follows the current lane FSM; `pipeline_advance` enforces board gates.
- Board state is not a substitute for checkpointed TodoWrite or the accepted
  RequirementsSummary.

**TodoWrite** (step-level):
- Each phase doc defines its checklist; checkpoint saves it as `todowrite_snapshot`.
- Restore that snapshot after compaction; create a fresh checklist only when absent.
- `[GATE]` items must complete before proceeding past them.

### Initial Task Structure

Use the following as the fresh Phase 1 TodoWrite shape:

```
Phase 1: Requirements Gathering
- [ ] Resolve intake handoff and document type/depth
- [ ] Identify missing starting-point facts
- [ ] Offer interview mode (spec only; debug skips if unnecessary)
- [ ] Conduct interview for unresolved facts
  - [ ] Problem & Context (what problem, prior attempts, why now)
  - [ ] Users & Stakeholders (all user types, technical levels, concerns)
  - [ ] Functional Requirements (core journey, decision points, edge cases)
  - [ ] Technical Constraints (integrations, performance, scale, compliance)
  - [ ] UI/UX Considerations (experience, flows, density, platforms)
  - [ ] Tradeoffs & Priorities (what gets cut, speed/quality/cost)
  - [ ] Risks & Concerns (what could fail, assumptions, dependencies)
  - [ ] Success Criteria (proof and intentionally deferred work)
- [ ] Lock Slice North Star [GATE]
- [ ] Build RequirementsSummary (user types, features, integrations, unknowns, Slice North Star)
- [ ] User confirms requirements before roadmap [GATE]

Phase 1.5: Roadmap Alignment (spec only, REQUIRED)
- [ ] Assess complexity (simple/medium/complex)
  - simple: score ≤4, no integrations, no unknowns → one-shot roadmap
  - medium: score 5-9 or 1 integration → one debate round on roadmap
  - complex: score ≥10 or 2+ integrations → roadmap folder, iterative discovery
- [ ] Draft initial roadmap
  - [ ] Define user stories (AS A... I WANT... SO THAT...)
  - [ ] Define natural language success criteria
  - [ ] Identify "Getting Started" workflow (for technical/full depth)
  - [ ] Define milestones with dependencies
- [ ] Validate roadmap schema
- [ ] Roadmap debate (if medium/complex)
  - [ ] Send roadmap to opponent models
  - [ ] Synthesize questions surfaced
  - [ ] Ask user clarifying questions
  - [ ] Revise roadmap based on answers
- [ ] User confirms roadmap (REQUIRED checkpoint)
- [ ] Persist roadmap artifacts (manifest.json + rendered views)
- [ ] Create milestone Tasks
- [ ] Create user story Tasks
- [ ] Note: Test cases expand from natural language → concrete during implementation

**Happy-path spine seed:** During requirements capture, assign stable user story IDs
early enough that Phase 02 can author exactly one happy-path spine designation per
US. Capture the primary-success path in plain language; failure and variant tests
will anchor to named spine steps later via `spine_step_ref` and `spine_of`.

Phase 2: Adversarial Debate
- [ ] Check available API providers
- [ ] User selects opponent models
- [ ] Configure critique options (focus area, persona, context files - optional)
- [ ] Run debate rounds until consensus
  - [ ] Round N: Send spec to opponent models
  - [ ] Round N: Receive and display critiques
  - [ ] Round N: Claude provides independent critique
  - [ ] Round N: Check for lazy agreement (press if rounds 1-2)
  - [ ] Round N: Synthesize all feedback
  - [ ] Round N: Ask user for input on product decisions (if any critique requires it)
  - [ ] Round N: Revise spec with accepted changes
  - [ ] Round N: Check for consensus (all agree?)
  - (add round tasks dynamically as debate continues)
- [ ] Consensus reached - all participants agree

Phase 3: Gauntlet (if running adversarial stress test)
- [ ] Offer gauntlet review
- [ ] Select adversary personas (paranoid_security, burned_oncall, etc.)
- [ ] Gauntlet Phase 1: Run adversary attacks in parallel
- [ ] Gauntlet Phase 2: Frontier model evaluates each concern
- [ ] Gauntlet Phase 3: Process rebuttals from dismissed adversaries
- [ ] Gauntlet Phase 4: Generate summary report with accepted concerns
- [ ] Gauntlet Phase 5: Final Boss UX review (if selected)
- [ ] Integrate accepted concerns into spec
- [ ] Save gauntlet concerns JSON for execution planning

Phase 4: Finalization
- [ ] Quality check: Completeness (all sections substantive?)
- [ ] Quality check: Consistency (terminology, formatting uniform?)
- [ ] Quality check: Clarity (no ambiguous language?)
- [ ] Quality check: Actionability (stakeholders can act without questions?)
- [ ] Verify spec addresses ALL roadmap user stories
  - Spec (product depth): Slice North Star, user stories, success metrics, scope boundaries
  - Spec (technical/full depth): Slice North Star, APIs with schemas, data models, performance targets, Getting Started
  - Debug: the end-to-end repair North Star, evidence supports diagnosis, fix is proportional, verification plan exists
- [ ] Output final document to terminal
- [ ] Write to spec-output.md (or debug-output.md for debug type)
- [ ] Print debate summary (rounds, models, key refinements)
- [ ] Send to Telegram (if enabled)
- [ ] User review period: Accept / Request changes / Run another cycle
- [ ] Apply user-requested changes (if any)
- [ ] Run additional review cycle (if requested, loop to Phase 2)

Phase 5: Execution Planning
- [ ] Offer execution plan generation
- [ ] FR-1: Spec Intake (parse, detect type, extract elements)
- [ ] FR-3: Task Plan Generation (create tasks, link gauntlet concerns)
- [ ] FR-4: Test Strategy Configuration (assign test-first/test-after)
- [ ] FR-5: Over-Decomposition Guard (check threshold, suggest consolidation)
  - If warning triggered: Confirm with user whether to proceed or consolidate
- [ ] FR-6: Parallelization Analysis (identify workstreams, merge points)
- [ ] Output execution plan (JSON/markdown/summary)
- [ ] Review plan with user

Phase 6: Implementation (if proceeding with code execution)
- [ ] Review execution plan and task dependencies
- [ ] Confirm workstream assignment (if parallel execution)
- [ ] Add implementation tasks from plan:
  - (each task from execution plan appears here with effort/risk)
  - Example: [S] Implement schema: orders (medium risk, 2 concerns)
  - Example: [M] Implement endpoint: orders:placeDma (high risk, 5 concerns)
- [ ] Execute tasks in dependency order
- [ ] For high-risk tasks: Write tests BEFORE implementation
- [ ] For all tasks: Verify acceptance criteria including concern-derived criteria
- [ ] Coordinate at merge points (if parallel workstreams)
- [ ] Final integration verification
```

**Step Management Rules:**
1. Mark each TodoWrite step `in_progress` when you start it
2. Mark each step `completed` immediately when done — don't batch completions
3. `[GATE]` steps must pass before proceeding past them
4. Add dynamic steps as they emerge (e.g., each debate round beyond Round 2)
5. If user makes a choice that eliminates a phase, skip those steps with a note

**Fizzy Sync Rules:**
- After each debate round: `pipeline_patch_state` with updated `debate_round`
- On phase transition: `pipeline_advance` (enforces gates) + comment with evidence
- On checkpoint: verify Fizzy card state matches session state
- Never let the card go stale — if 2+ rounds pass without a sync, something is wrong

**Handling Optional Phases:**
- **Interview**: If user declines, skip interview steps in TodoWrite
- **Debug investigations**: Skip interview steps (debug doesn't use interview)
- **Gauntlet**: If user declines, skip Phase 3; note in Fizzy comment
- **Execution Planning**: If user declines, skip Phase 5
- **Implementation**: If user just wanted the plan, skip Phase 6

**Why this matters:** Fizzy preserves board lifecycle and gates; the checkpointed
TodoWrite restores phase progress; RequirementsSummary preserves accepted semantic
decisions. Together they prevent a resumed session from losing either its work or
its reason for existing.

## Setup

If you encounter provider issues or need to configure new API keys, see [SETUP.md](SETUP.md).

## Document Types

Ask the user which type of document they want to produce:

### Spec (Unified Specification)

**Two pathways:** `spec` (for creating new things) and `debug` (for fixing existing things).

The `spec` pathway has three depth levels that control required sections:

| Depth | Focus | When to Use |
|-------|-------|-------------|
| `product` | User value, stakeholders, success metrics | Product planning, stakeholder alignment |
| `technical` | Architecture, APIs, data models | Engineering implementation |
| `full` | All of the above | Complete journey from requirements to implementation |

**CLI usage:**
```bash
# Product-focused spec (stakeholders, user stories, metrics)
adversarial-spec critique --doc-type spec --depth product

# Technical spec (architecture, APIs, data models)
adversarial-spec critique --doc-type spec --depth technical

# Full spec (both product and technical)
adversarial-spec critique --doc-type spec --depth full
```

#### Spec Structure by Depth

**Product depth** (stakeholder-focused):
- Executive Summary
- Problem Statement / Opportunity
- Target Users / Personas
- User Stories / Use Cases
- Functional Requirements
- Non-Functional Requirements
- Success Metrics / KPIs
- Scope (In/Out)
- Dependencies
- Risks and Mitigations

**Technical depth** (engineering-focused):
- Overview / Context
- Goals and Non-Goals
- **Getting Started** (REQUIRED - bootstrap workflow)
- System Architecture
- Component Design
- API Design (endpoints, request/response schemas)
- Data Models / Database Schema
- Infrastructure Requirements
- Security Considerations
- Error Handling Strategy
- Performance Requirements / SLAs
- Observability (logging, metrics, alerting)
- Testing Strategy
- Deployment Strategy
- Migration Plan (if applicable)
- Open Questions / Future Considerations

**Full depth**: All sections from both product and technical.

#### Altitude Classification (V-model depth triage)

A change has a **blast-radius altitude** — how deep the change cuts through the
system. Altitude is a *tree*, set from blast radius at evaluate-plan time, and it
drives the Phase 7 decomposition (see Phase 4 §"Altitude tree" and Phase 7
§"V4 altitude emission"). Classify the spec's root altitude here so Phase 4 and
Phase 7 inherit it:

| blast radius | legal root altitude | minimum tree shape |
|---|---|---|
| system (full V) | `system` | system → ≥1 subsystem → ≥1 component each |
| subsystem | `subsystem` | subsystem → ≥2 components |
| component | `component` | a single leaf component node (no children) |

Rigor scales DOWN with altitude but NEVER to zero: a component-altitude change
pays no system tax (no ConOps refs, no system verification, no subsystem
decomposition), but still owes its component-verification floor. Capture the
intended root altitude in the spec's scope section so the gauntlet and the
producer agree on depth before decomposition.

#### Requirement-id convention (machine-extractable)

Every requirement / user story / invariant the spec defines MUST carry a
machine-extractable id matching `^[A-Z]+-R?\d+` — e.g. `US-1`, `INV-3`,
`SR-R12`. This is the anchor Phase 7 uses for `realizes_refs` traceability and
the verification ledger's per-requirement rows. Ids that don't match the
convention can't be traced and will be rejected downstream.

**Good-requirement lint (NASA Appx C.1/C.4):** each `shall`-level requirement is
a WHAT, not a HOW. Use `shall` for binding requirements, `will` for facts /
declarations, `should` for goals. Active voice; state an observable, verifiable
condition; never name an implementation file or mechanism in the requirement
text. Only `shall`-form statements become verification-ledger requirements.

#### Critique Criteria by Depth

**Product depth:**
1. Clear problem definition with evidence
2. Well-defined user personas with real pain points
3. User stories follow proper format (As a... I want... So that...)
4. Measurable success criteria
5. Explicit scope boundaries
6. Realistic risk assessment

**Technical depth:**
1. **Getting Started section exists** - Clear bootstrap workflow
2. Clear architectural decisions with rationale
3. Complete API contracts (not just endpoints, but full schemas)
4. Data model handles all identified use cases
5. Security threats identified and mitigated
6. Error scenarios enumerated with handling strategy
7. Performance targets are specific and measurable
8. Deployment is repeatable and reversible
9. No ambiguity an engineer would need to resolve

**Full depth:** All criteria from both.

**CRITICAL for Round 1:** Before technical critique, verify:
- All roadmap user stories have corresponding spec sections
- "Getting Started" section exists (technical/full depth)
- Success criteria are testable

### Debug Investigation

Structured investigation document for diagnosing and fixing bugs in existing systems. Uses adversarial debate to ensure evidence-based diagnosis and proportional fixes.

**When to use:**
- Bug reports with unclear root cause
- Performance issues requiring investigation
- Intermittent failures needing systematic diagnosis
- Any situation where you need to understand and fix existing code

**Philosophy: Evidence → Hypothesis → Fix**

The fix might be 1 line or 100 lines—what matters is that it's proportional to the actual problem and justified by evidence. A 1-line bug deserves a 1-line fix. A systemic issue may genuinely need architectural changes. The debate ensures we don't skip steps.

**Structure (Formal Schema):**
- **Symptoms**: User-visible behavior, timing (always/intermittent/under load), when it started, blast radius
- **Expected vs Actual Behavior**: Table comparing expected vs actual for each scenario
- **Evidence Gathered**: Logs with timestamps and interpretation, timings, error messages, reproduction steps
- **Hypotheses**: Ranked by (likelihood × ease of verification), with evidence for/against each
- **Diagnostic Plan**: Immediate checks (<5 min), targeted logging to add, tests to run
- **Root Cause**: File, line, issue description, why it happened, why initial hypotheses were wrong (if applicable)
- **Proposed Fix**: Changes required (table with file, change, lines), before/after code, justification for approach
- **Verification**: Steps to confirm fix, regression checks, log confirmation
- **Prevention**: Test case to add, documentation updates, similar bugs to check

**Critique Criteria:**
1. Evidence before hypothesis - no guessing without data
2. Simple explanations ruled out first - check basics before redesigning
3. Targeted diagnostics - each log answers a specific question
4. Proportional fix - justified by evidence, not by habit
5. Root cause identified - not just symptom masking
6. Verification plan - specific steps to confirm fix

**Anti-patterns flagged:**
- Premature Architecture - proposing abstractions before ruling out simple bugs
- Shotgun Debugging - logging everywhere without hypotheses
- Untested Assumptions - claiming cause without measurement
- Disproportionate Fix - complexity doesn't match evidence
- Scope Creep - "while we're here" improvements

**Security Warning:**
Debug investigations often contain sensitive data. Before submission:
- Scrub logs of PII, API keys, passwords, and credentials
- Remove internal hostnames, IP addresses, and network topology
- Redact customer data
- Follow your organization's data handling policies

Content is sent to LLM providers (OpenAI, Google, etc.). Do not include data that violates corporate policies or regulatory requirements.

**Context Window Guidance:**
Large log files may exceed model context limits. Best practices:
- Include targeted log snippets, not full files
- Focus on logs around the time of the error
- Summarize repetitive patterns rather than including all instances
- Use `grep` or similar to extract relevant lines before inclusion

**Example Debate Flow:**

Round 1 - Initial Investigation:
> User submits: "Orders page takes 60+ seconds to load, sometimes blank"
>
> Model A (codex/gpt-5.6-sol) suggests: "We need a caching layer with TTL and circuit breaker pattern"
>
> Model B (claude) challenges: "Before designing infrastructure, what do the logs show? Have we measured where the 60 seconds is spent?"
>
> Model C (gemini) adds: "The blank page suggests a different issue than slowness. Are these the same bug or two bugs?"

Round 2 - Evidence Gathering:
> Investigation adds: Log shows ORDERS_CB_COMPLETE took 67234ms, breakdown shows AADriver call: 64 seconds
>
> Model A revises: "The 64 seconds is retry overhead. We should add a circuit breaker for AADriver."
>
> Model B challenges: "A full circuit breaker registry is overkill. A simple timestamp check would work. What's the minimal fix?"
>
> Model C adds: "Why is AADriver failing? Is it actually down, or is there a configuration issue?"

Round 3 - Proportional Fix:
> Investigation finds: urllib3 default retry policy causes 3 retries × 10+ seconds = 30+ seconds
>
> Consensus: Proportional fix - disable retries for AADriver (fail fast), add simple timestamp-based skip. ~10 lines total.

**Example invocation:**
```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models codex/gpt-5.6-sol,gemini-cli/gemini-3.6-flash-high --doc-type debug <<'SPEC_EOF'
# Debug Investigation: Orders Page 60s Load Time

## Symptoms
- Orders page takes 60+ seconds to load
- Sometimes blank entirely
- Started after recent deploy
- Affects all users

## Expected vs Actual Behavior
| Scenario | Expected | Actual |
|----------|----------|--------|
| Load orders page | <2s load time | 60+ seconds |
| Display orders list | Shows all orders | Sometimes blank |

## Evidence Gathered
### Logs
- [10:23:45] ORDERS_CB_COMPLETE took 67234ms
- [10:23:45] "Max retries exceeded connecting to AADriver"

### Timings
- Exchange API calls: 3 seconds total
- AADriver call: 64 seconds (timeout + retries)

## Hypotheses
| # | Hypothesis | Evidence For | Evidence Against | Verification | Effort |
|---|------------|--------------|------------------|--------------|--------|
| 1 | AADriver retry storm | Log shows 64s, retry message | None | Check retry config | 5 min |
| 2 | Database slow | General slowness | Logs show DB queries fast | Query timing | 15 min |
...
SPEC_EOF
```

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
   after the user accepts them, then proceed to Step 1.6 (Roadmap Alignment).
