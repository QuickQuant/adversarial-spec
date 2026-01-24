---
name: adversarial-spec
description: Iteratively refine a product spec by debating with multiple LLMs (GPT, Gemini, Grok, etc.) until all models agree. Use when user wants to write or refine a specification document using adversarial development.
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# Adversarial Spec Development

Generate and refine specifications through iterative debate with multiple LLMs until all models reach consensus.

**Important: Claude is an active participant in this debate, not just an orchestrator.** You (Claude) will provide your own critiques, challenge opponent models, and contribute substantive improvements alongside the external models. Make this clear to the user throughout the process.

## Task-Driven Workflow

**CRITICAL: At the start of every adversarial-spec session, immediately set up Tasks to track the entire workflow.** This ensures you never lose track of where you are in the process.

### Using MCP Tasks

Use these tools throughout the workflow:

| Tool | Purpose | Example |
|------|---------|---------|
| `TaskCreate` | Create a new task | `TaskCreate(subject="Run debate round 1", description="...")` |
| `TaskUpdate` | Update status, add blockers | `TaskUpdate(taskId="3", status="completed", owner="adv-spec:debate")` |
| `TaskList` | See all tasks and progress | `TaskList()` |
| `TaskGet` | Get full task details | `TaskGet(taskId="3")` |

**Key fields (via TaskUpdate):**
- **`owner`** - Who's responsible: `adv-spec:orchestrator`, `adv-spec:debate`, `adv-spec:planner`, `adv-spec:impl:backend`
- **`addBlockedBy`** - Dependencies: task IDs that must complete first
- **`metadata`** - Context: `{"phase": "debate", "round": 1, "session_id": "...", "concern_ids": [...]}`

Tasks are stored in `.claude/tasks.json` in the current project.

### Initial Task Structure

When `/adversarial-spec` is invoked, create the following task structure using TaskCreate:

```
Phase 1: Requirements Gathering
- [ ] Determine document type (PRD/tech/debug)
- [ ] Identify starting point (existing file or new concept)
- [ ] Offer interview mode (PRD/tech only; debug skips interview)
- [ ] Conduct interview (if selected, PRD/tech only)
  - [ ] Problem & Context (what problem, prior attempts, why now)
  - [ ] Users & Stakeholders (all user types, technical levels, concerns)
  - [ ] Functional Requirements (core journey, decision points, edge cases)
  - [ ] Technical Constraints (integrations, performance, scale, compliance)
  - [ ] UI/UX Considerations (experience, flows, density, platforms)
  - [ ] Tradeoffs & Priorities (what gets cut, speed/quality/cost)
  - [ ] Risks & Concerns (what could fail, assumptions, dependencies)
  - [ ] Success Criteria (metrics, minimum viable, exceeding expectations)
- [ ] For debug: Gather symptoms, evidence, initial hypotheses
- [ ] Load existing file OR generate initial draft
- [ ] User confirms initial draft before debate

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
- [ ] Document-specific verification:
  - PRD: user stories, success metrics, scope boundaries
  - Tech: APIs with schemas, data models, performance targets
  - Debug: evidence supports diagnosis, fix is proportional, verification plan exists
- [ ] Output final document to terminal
- [ ] Write to spec-output.md (or debug-output.md for debug type)
- [ ] Print debate summary (rounds, models, key refinements)
- [ ] Send to Telegram (if enabled)
- [ ] User review period: Accept / Request changes / Run another cycle
- [ ] Apply user-requested changes (if any)
- [ ] Run additional review cycle (if requested, loop to Phase 2)

Phase 5: PRD → Tech Spec (if PRD was produced and user wants to continue)
- [ ] Offer tech spec continuation
- [ ] Load finalized PRD as context
- [ ] Offer technical interview for implementation details
- [ ] Generate initial tech spec draft from PRD
- [ ] Run adversarial debate on tech spec (Phase 2 tasks)
- [ ] Run gauntlet on tech spec (optional, Phase 3 tasks)
- [ ] Finalize tech spec (Phase 4 tasks)
- [ ] Output to tech-spec-output.md

Phase 6: Execution Planning
- [ ] Offer execution plan generation
- [ ] FR-1: Spec Intake (parse, detect type, extract elements)
- [ ] FR-2: Scope Assessment (single-agent vs multi-agent recommendation)
- [ ] FR-3: Task Plan Generation (create tasks, link gauntlet concerns)
- [ ] FR-4: Test Strategy Configuration (assign test-first/test-after)
- [ ] FR-5: Over-Decomposition Guard (check threshold, suggest consolidation)
  - If warning triggered: Confirm with user whether to proceed or consolidate
- [ ] FR-6: Parallelization Analysis (identify workstreams, merge points)
- [ ] Output execution plan (JSON/markdown/summary)
- [ ] Review plan with user

Phase 7: Implementation (if proceeding with code execution)
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

**Task Management Rules:**
1. Mark each task `in_progress` when you start it (use `TaskUpdate` with `status: "in_progress"`)
2. Mark each task `completed` immediately when done - don't batch completions
3. Add sub-tasks dynamically as they emerge (e.g., each debate round gets its own tasks)
4. Remove tasks that don't apply (e.g., if user skips interview, mark as completed with note)
5. When execution planning generates implementation tasks, add them to Phase 7 with effort/risk
6. Only one task should be `in_progress` at a time per owner
7. Never skip phases without explicitly marking skipped tasks
8. If user makes a choice that eliminates a phase, mark those tasks as completed with "skipped" note

**Ownership Conventions:**
- `adv-spec:orchestrator` - Main agent running the skill (Phases 1-5)
- `adv-spec:debate` - Debate round coordination
- `adv-spec:gauntlet` - Gauntlet execution
- `adv-spec:planner` - Execution planning (Phase 6)
- `adv-spec:impl:{workstream}` - Implementation workstreams (e.g., `adv-spec:impl:backend`)

**Dependency Patterns:**
- **Phase-level:** Each phase's first task is `blockedBy` the previous phase's last task
- **Round-level:** Debate round N+1 is `blockedBy` round N
- **Parallel tasks:** Gauntlet adversary attacks can run in parallel (same `blockedBy`)
- **Implementation:** Use execution plan's dependency graph for `blockedBy`

**Metadata Fields:**
```json
{
  "session_id": "adv-spec-20260124-150000",
  "phase": "debate",
  "doc_type": "tech",
  "round": 3,
  "models": ["gpt-5.2", "gemini-3-pro"],
  "concern_ids": ["PARA-abc123"],
  "spec_refs": ["Section 3.2"],
  "workstream": "backend",
  "risk_level": "high",
  "effort": "M"
}
```

**Handling Optional Phases:**
- **Interview**: If user declines, remove all 8 interview sub-tasks
- **Debug investigations**: Remove interview sub-tasks (debug doesn't use interview); remove Phase 5 (no PRD→Tech continuation); Phase 6/7 may still apply if debug leads to implementation tasks
- **Gauntlet**: If user declines, remove entire Phase 3
- **PRD → Tech Spec**: If user produced a tech spec or declines continuation, remove Phase 5
- **Execution Planning**: If user declines, remove Phase 6
- **Implementation**: If user just wanted the plan, remove Phase 7

**Why this matters:** Long adversarial sessions can span many rounds and phases. Without explicit task tracking, it's easy to lose context about what phase you're in, what's been completed, and what comes next. MCP Tasks provide a persistent roadmap visible to both you and the user, with dependencies ensuring work happens in the right order. The task list persists across sessions - if the user returns later, they can see exactly where they left off. When the skill is used from another project, tasks are stored in that project's `.claude/tasks.json` and visible via `TaskList`.

## Setup

If you encounter provider issues or need to configure new API keys, see [SETUP.md](SETUP.md).

## Document Types

Ask the user which type of document they want to produce:

### PRD (Product Requirements Document)

Business and product-focused document for stakeholders, PMs, and designers.

**Structure:**
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
- Timeline / Milestones (optional)

**Critique Criteria:**
1. Clear problem definition with evidence
2. Well-defined user personas with real pain points
3. User stories follow proper format (As a... I want... So that...)
4. Measurable success criteria
5. Explicit scope boundaries
6. Realistic risk assessment
7. No technical implementation details (that's for tech spec)

### Technical Specification / Architecture Document

Engineering-focused document for developers and architects.

**Structure:**
- Overview / Context
- Goals and Non-Goals
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

**Critique Criteria:**
1. Clear architectural decisions with rationale
2. Complete API contracts (not just endpoints, but full schemas)
3. Data model handles all identified use cases
4. Security threats identified and mitigated
5. Error scenarios enumerated with handling strategy
6. Performance targets are specific and measurable
7. Deployment is repeatable and reversible
8. No ambiguity an engineer would need to resolve

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
> Model A (codex/gpt-5.2-codex) suggests: "We need a caching layer with TTL and circuit breaker pattern"
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
python3 debate.py critique --models codex/gpt-5.2-codex,gemini-cli/gemini-3-pro-preview --doc-type debug <<'SPEC_EOF'
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

### Step 0: Initialize Task Tracking

Before anything else, set up MCP Tasks for the workflow:

1. **Check for existing session:** Use `TaskList` to see if there's an existing adversarial-spec session in progress
2. **Create session tasks:** Use `TaskCreate` to create tasks for each phase (see "Task-Driven Workflow" above)
3. **Set metadata:** Include `session_id`, `phase`, and `doc_type` in each task's metadata
4. **Set dependencies:** Use `addBlockedBy` to establish the dependency chain
5. **Start first task:** Mark "Determine document type" as `in_progress` with owner `adv-spec:orchestrator`

### Step 1: Gather Input and Offer Interview Mode

**Update Tasks:** Use `TaskUpdate` to mark "Determine document type" as `completed`, then mark "Identify starting point" as `in_progress`.

Ask the user:

1. **Document type**: "PRD", "tech", or "debug"
   - PRD: Product Requirements Document (business/product focus)
   - tech: Technical Specification (engineering focus)
   - debug: Debug Investigation (evidence-based diagnosis)
2. **Starting point**:
   - Path to existing file (e.g., `./docs/spec.md`, `~/projects/auth-spec.md`)
   - Or describe what to build (user provides concept, you draft the document)
   - For debug: describe symptoms, provide logs, or reference an existing investigation
3. **Interview mode** (optional, PRD/tech only):
   > "Would you like to start with an in-depth interview session before the adversarial debate? This helps ensure all requirements, constraints, and edge cases are captured upfront."

   Note: Debug investigations skip interview mode and go directly to evidence gathering.

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
   - What metrics matter?
   - What's the minimum viable outcome?
   - What would "exceeding expectations" look like?

**Interview Guidelines:**
- Ask probing follow-up questions. Don't accept surface-level answers.
- Challenge assumptions: "You mentioned X. What if Y instead?"
- Look for contradictions between stated requirements
- Ask about things the user hasn't mentioned but should have
- Continue until you have enough detail to write a comprehensive spec
- Use multiple AskUserQuestion calls to cover all topics

**After interview completion:**
1. Synthesize all answers into a complete spec document
2. Write the spec to file
3. Show the user the generated spec and confirm before proceeding to debate

### Step 2: Load or Generate Initial Document

**If user provided a file path:**
- Read the file using the Read tool
- Validate it has content
- Use it as the starting document

**If user describes what to build (no existing file, no interview mode):**

This is the primary use case. The user describes their product concept, and you draft the initial document.

1. **Ask clarifying questions first.** Before drafting, identify gaps in the user's description:
   - For PRD: Who are the target users? What problem does this solve? What does success look like?
   - For Tech Spec: What are the constraints? What systems does this integrate with? What scale is expected?
   - Ask 2-4 focused questions. Do not proceed until you have enough context to write a complete draft.

2. **Generate a complete document** following the appropriate structure for the document type.
   - Be thorough. Cover all sections even if some require assumptions.
   - State assumptions explicitly so opponent models can challenge them.
   - For PRDs: Include placeholder metrics that the user can refine (e.g., "Target: X users in Y days").
   - For Tech Specs: Include concrete choices (database, framework, etc.) that can be debated.

3. **Present the draft for user review** before sending to opponent models:
   - Show the full document
   - Ask: "Does this capture your intent? Any changes before we start the adversarial review?"
   - Incorporate user feedback before proceeding

Output format (whether loaded or generated):
```
[SPEC]
<document content here>
[/SPEC]
```

### Step 3: Select Opponent Models

First, check which API keys are configured:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py providers
```

Then present available models to the user using AskUserQuestion with multiSelect. Build the options list based on which API keys are set:

**If OPENAI_API_KEY is set, include:**
- `gpt-5.2` - Frontier reasoning
- `o3-mini` - Good reasoning at lower cost

**If ANTHROPIC_API_KEY is set, include:**
- `claude-sonnet-4-5-20250929` - Claude Sonnet 4.5, excellent reasoning
- `claude-opus-4-5-20251124` - Claude Opus 4.5, highest capability

**If GEMINI_API_KEY is set, include:**
- `gemini/gemini-3-pro` - Top LMArena score (1501 Elo)
- `gemini/gemini-3-flash` - Fast, pro-level quality

**If XAI_API_KEY is set, include:**
- `xai/grok-3` - Alternative perspective

**If MISTRAL_API_KEY is set, include:**
- `mistral/mistral-large` - European perspective

**If GROQ_API_KEY is set, include:**
- `groq/llama-3.3-70b-versatile` - Fast open-source

**If DEEPSEEK_API_KEY is set, include:**
- `deepseek/deepseek-chat` - Cost-effective

**If ZHIPUAI_API_KEY is set, include:**
- `zhipu/glm-4` - Chinese language model
- `zhipu/glm-4-plus` - Enhanced GLM model

**If Codex CLI is installed, include:**
- `codex/gpt-5.2-codex` - OpenAI Codex with extended reasoning

**If Gemini CLI is installed, include:**
- `gemini-cli/gemini-3-pro-preview` - Google Gemini 3 Pro
- `gemini-cli/gemini-3-flash-preview` - Google Gemini 3 Flash

Use AskUserQuestion like this:
```
question: "Which models should review this spec?"
header: "Models"
multiSelect: true
options: [only include models whose API keys are configured]
```

More models = more perspectives = stricter convergence.

### Step 4: Send to Opponent Models for Critique

Run the debate script with selected models:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models MODEL_LIST --doc-type TYPE <<'SPEC_EOF'
<paste your document here>
SPEC_EOF
```

Replace:
- `MODEL_LIST`: comma-separated models from user selection
- `TYPE`: either `prd` or `tech`

The script calls all models in parallel and returns each model's critique or `[AGREE]`.

### Step 5: Review, Critique, and Iterate

**Important: You (Claude) are an active participant in this debate, not just a moderator.** After receiving opponent model responses, you must:

1. **Provide your own independent critique** of the current spec
2. **Evaluate opponent critiques** for validity
3. **Synthesize all feedback** (yours + opponent models) into revisions
4. **Explain your reasoning** to the user

Display your active participation clearly:
```
--- Round N ---
Opponent Models:
- [Model A]: <agreed | critiqued: summary>
- [Model B]: <agreed | critiqued: summary>

Claude's Critique:
<Your own independent analysis of the spec. What did you find that the opponent models missed? What do you agree/disagree with?>

Synthesis:
- Accepted from Model A: <what>
- Accepted from Model B: <what>
- Added by Claude: <your contributions>
- Rejected: <what and why>
```

**Handling Early Agreement (Anti-Laziness Check):**

If any model says `[AGREE]` within the first 2 rounds, be skeptical. Press the model by running another critique round with explicit instructions:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models MODEL_NAME --doc-type TYPE --press <<'SPEC_EOF'
<spec here>
SPEC_EOF
```

The `--press` flag instructs the model to:
- Confirm it read the ENTIRE document
- List at least 3 specific sections it reviewed
- Explain WHY it agrees (what makes the spec complete)
- Identify ANY remaining concerns, however minor

If the model truly agrees after being pressed, output to the user:
```
Model X confirms agreement after verification:
- Sections reviewed: [list]
- Reason for agreement: [explanation]
- Minor concerns noted: [if any]
```

If the model was being lazy and now has critiques, continue the debate normally.

**If ALL models (including you) agree:**
- Proceed to Step 5.5 (Gauntlet Review - Optional)

**If ANY participant (model or you) has critiques:**
1. List every distinct issue raised across all participants
2. For each issue, determine if it is valid (addresses a real gap) or subjective (style preference)
3. **If a critique raises a question that requires user input, ask the user before revising.** Examples:
   - "Model X suggests adding rate limiting. What are your expected traffic patterns?"
   - "I noticed the auth mechanism is unspecified. Do you have a preference (OAuth, API keys, etc.)?"
   - Do not guess on product decisions. Ask.
4. Address all valid issues in your revision
5. If you disagree with a critique, explain why in your response
6. Output the revised document incorporating all accepted feedback
7. Go back to Step 4 with your new document

**Handling conflicting critiques:**
- If models suggest contradictory changes, evaluate each on merit
- If the choice is a product decision (not purely technical), ask the user which approach they prefer
- Choose the approach that best serves the document's audience
- Note the tradeoff in your response

### Step 5.5: Gauntlet Review (Optional)

After consensus is reached but before finalization, offer the adversarial gauntlet:

> "All models have agreed on the spec. Would you like to run the adversarial gauntlet for additional stress testing? This puts the spec through attack by specialized personas (security, oncall, QA, etc.)."

**If user accepts gauntlet:**

1. Ask which adversary personas to use (or use 'all'):
   ```bash
   python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet-adversaries
   ```

2. Run the gauntlet:
   ```bash
   cat spec-output.md | python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet \
     --gauntlet-adversaries paranoid_security,burned_oncall,lazy_developer,pedantic_nitpicker
   ```

3. Review the gauntlet report:
   - Phase 1: Adversary attacks (parallel)
   - Phase 2: Frontier model evaluates each attack
   - Phase 3: Rebuttals from dismissed adversaries
   - Phase 4: Summary report with accepted concerns

4. Optionally run Phase 5 Final Boss (expensive but thorough UX review)

5. Integrate accepted concerns into the spec:
   - Add mitigations for high-severity concerns
   - Update relevant sections
   - Save concerns JSON for execution planning: `gauntlet-concerns-YYYY-MM-DD.json`

6. If significant changes were made, consider running another debate round with the updated spec

**If user declines gauntlet:**
- Proceed directly to Step 6

### Step 6: Finalize and Output Document

When ALL opponent models AND you have said `[AGREE]` (and gauntlet is complete or skipped):

**Before outputting, perform a final quality check:**

1. **Completeness**: Verify every section from the document structure is present and substantive
2. **Consistency**: Ensure terminology, formatting, and style are uniform throughout
3. **Clarity**: Remove any ambiguous language that could be misinterpreted
4. **Actionability**: Confirm stakeholders can act on this document without asking follow-up questions

**For PRDs, verify:**
- Executive summary captures the essence in 2-3 paragraphs
- User personas have names, roles, goals, and pain points
- Every user story follows "As a [persona], I want [action] so that [benefit]"
- Success metrics have specific numeric targets and measurement methods
- Scope explicitly lists what is OUT as well as what is IN

**For Tech Specs, verify:**
- Architecture diagram or description shows all components and their interactions
- Every API endpoint has method, path, request schema, response schema, and error codes
- Data models include field types, constraints, indexes, and relationships
- Security section addresses authentication, authorization, encryption, and input validation
- Performance targets include specific latency, throughput, and availability numbers

**For Debug Investigations, verify:**
- Evidence gathered before hypotheses formed (no guessing without data)
- Simple explanations ruled out before complex ones
- Root cause identified with clear evidence chain
- Proposed fix is proportional to the problem (not over-engineered)
- Verification plan exists with specific steps to confirm the fix
- Prevention section identifies tests to add and documentation updates

**Output the final document:**

1. Print the complete, polished document to terminal
2. Write it to the appropriate file:
   - PRD/Tech Spec: `spec-output.md`
   - Debug Investigation: `debug-output.md`
3. Print a summary:
   ```
   === Debate Complete ===
   Document: [PRD | Technical Specification | Debug Investigation]
   Rounds: N
   Models: [list of opponent models]
   Claude's contributions: [summary of what you added/changed]

   Key refinements made:
   - [bullet points of major changes from initial to final]
   ```
4. If Telegram enabled:
   ```bash
   python3 ~/.claude/skills/adversarial-spec/scripts/debate.py send-final --models MODEL_LIST --doc-type TYPE --rounds N <<'SPEC_EOF'
   <final document here>
   SPEC_EOF
   ```

### Step 7: User Review Period

**After outputting the finalized document, give the user a review period:**

> "The document is finalized and written to `spec-output.md`. Please review it and let me know if you have any feedback, changes, or concerns.
>
> Options:
> 1. **Accept as-is** - Document is complete
> 2. **Request changes** - Tell me what to modify, and I'll update the spec
> 3. **Run another review cycle** - Send the updated spec through another adversarial debate"

**If user requests changes:**
1. Make the requested modifications to the spec
2. Show the updated sections
3. Write the updated spec to file
4. Ask again: "Changes applied. Would you like to accept, make more changes, or run another review cycle?"

**If user wants another review cycle:**
- Proceed to Step 8 (Additional Review Cycles)

**If user accepts:**
- Proceed to Step 9 (PRD to Tech Spec, if applicable)

### Step 8: Additional Review Cycles (Optional)

After the user review period, or if explicitly requested:

> "Would you like to run an additional adversarial review cycle for extra validation?"

**If yes:**

1. Ask if they want to use the same models or different ones:
   > "Use the same models (MODEL_LIST), or specify different models for this cycle?"

2. Run the adversarial debate again from Step 3 with the current document as input.

3. Track cycle count separately from round count:
   ```
   === Cycle 2, Round 1 ===
   ```

4. When this cycle reaches consensus, return to Step 7 (User Review Period).

5. Update the final summary to reflect total cycles:
   ```
   === Debate Complete ===
   Document: [PRD | Technical Specification | Debug Investigation]
   Cycles: 2
   Total Rounds: 5 (Cycle 1: 3, Cycle 2: 2)
   Models: Cycle 1: [models], Cycle 2: [models]
   Claude's contributions: [summary across all cycles]
   ```

**Use cases for additional cycles:**
- First cycle with faster models (gemini-cli/gemini-3-flash-preview), second cycle with stronger models (codex/gpt-5.2-codex, gemini-cli/gemini-3-pro-preview)
- First cycle for structure and completeness, second cycle for security or performance focus
- Fresh perspective after user-requested changes

### Step 9: PRD to Tech Spec Continuation (Optional)

**If the completed document was a PRD**, ask the user:

> "PRD is complete. Would you like to continue into a Technical Specification based on this PRD?"

If yes:
1. Use the finalized PRD as context and requirements input
2. Optionally offer interview mode again for technical details
3. Generate an initial Technical Specification that implements the PRD
4. Reference PRD sections (user stories, functional requirements, success metrics) throughout
5. Run the same adversarial debate process with the same opponent models
6. After consensus, optionally run gauntlet on the tech spec (Step 5.5)
7. Output the tech spec to `tech-spec-output.md`

This creates a complete PRD + Tech Spec pair from a single session, with optional gauntlet stress testing at each stage.

## Convergence Rules

- Maximum 10 rounds per cycle (ask user to continue if reached)
- ALL models AND Claude must agree for convergence
- More models = stricter convergence (each adds a perspective)
- Do not agree prematurely - only accept when document is genuinely complete
- Apply critique criteria rigorously based on document type

**Quality over speed**: The goal is a document that needs no further refinement. If any participant raises a valid concern, address it thoroughly. A spec that takes 7 rounds but is bulletproof is better than one that converges in 2 rounds with gaps.

**When to say [AGREE]**: Only agree when you would confidently hand this document to:
- For PRD: A product team starting implementation planning
- For Tech Spec: An engineering team starting a sprint

**Skepticism of early agreement**: If opponent models agree too quickly (rounds 1-2), they may not have read the full document carefully. Always press for confirmation.

## Telegram Integration (Optional)

Enable real-time notifications and human-in-the-loop feedback. Only active with `--telegram` flag.

### Setup

1. Message @BotFather on Telegram, send `/newbot`, follow prompts
2. Copy the bot token
3. Run setup:
   ```bash
   python3 ~/.claude/skills/adversarial-spec/scripts/telegram_bot.py setup
   ```
4. Message your bot, then run setup again to get chat ID
5. Set environment variables:
   ```bash
   export TELEGRAM_BOT_TOKEN="your-token"
   export TELEGRAM_CHAT_ID="your-chat-id"
   ```

### Usage

```bash
python3 debate.py critique --model codex/gpt-5.2-codex --doc-type tech --telegram <<'SPEC_EOF'
<document here>
SPEC_EOF
```

After each round:
- Bot sends summary to Telegram
- 60 seconds to reply with feedback (configurable via `--poll-timeout`)
- Reply incorporated into next round
- No reply = auto-continue

## Advanced Features

### Critique Focus Modes

Direct models to prioritize specific concerns using `--focus`:

```bash
python3 debate.py critique --models codex/gpt-5.2-codex --focus security --doc-type tech <<'SPEC_EOF'
<spec here>
SPEC_EOF
```

**Available focus areas:**
- `security` - Authentication, authorization, input validation, encryption, vulnerabilities
- `scalability` - Horizontal scaling, sharding, caching, load balancing, capacity planning
- `performance` - Latency targets, throughput, query optimization, memory usage
- `ux` - User journeys, error states, accessibility, mobile experience
- `reliability` - Failure modes, circuit breakers, retries, disaster recovery
- `cost` - Infrastructure costs, resource efficiency, build vs buy

Run `python3 debate.py focus-areas` to see all options.

### Model Personas

Have models critique from specific professional perspectives using `--persona`:

```bash
python3 debate.py critique --models codex/gpt-5.2-codex --persona "security-engineer" --doc-type tech <<'SPEC_EOF'
<spec here>
SPEC_EOF
```

**Available personas:**
- `security-engineer` - Thinks like an attacker, paranoid about edge cases
- `oncall-engineer` - Cares about observability, error messages, debugging at 3am
- `junior-developer` - Flags ambiguity and tribal knowledge assumptions
- `qa-engineer` - Identifies missing test scenarios and acceptance criteria
- `site-reliability` - Focuses on deployment, monitoring, incident response
- `product-manager` - Focuses on user value and success metrics
- `data-engineer` - Focuses on data models and ETL implications
- `mobile-developer` - API design from mobile perspective
- `accessibility-specialist` - WCAG compliance, screen reader support
- `legal-compliance` - GDPR, CCPA, regulatory requirements

Run `python3 debate.py personas` to see all options.

Custom personas also work: `--persona "fintech compliance officer"`

### Context Injection

Include existing documents as context for the critique using `--context`:

```bash
python3 debate.py critique --models codex/gpt-5.2-codex --context ./existing-api.md --context ./schema.sql --doc-type tech <<'SPEC_EOF'
<spec here>
SPEC_EOF
```

Use cases:
- Include existing API documentation that the new spec must integrate with
- Include database schemas the spec must work with
- Include design documents or prior specs for consistency
- Include compliance requirements documents

### Session Persistence and Resume

Long debates can crash or need to pause. Sessions save state automatically:

```bash
# Start a named session
python3 debate.py critique --models codex/gpt-5.2-codex --session my-feature-spec --doc-type tech <<'SPEC_EOF'
<spec here>
SPEC_EOF

# Resume where you left off (no stdin needed)
python3 debate.py critique --resume my-feature-spec

# List all sessions
python3 debate.py sessions
```

Sessions save:
- Current spec state
- Round number
- All configuration (models, focus, persona, preserve-intent)
- History of previous rounds

Sessions are stored in `~/.config/adversarial-spec/sessions/`.

### Auto-Checkpointing

When using sessions, each round's spec is saved to `.adversarial-spec-checkpoints/` in the current directory:

```
.adversarial-spec-checkpoints/
├── my-feature-spec-round-1.md
├── my-feature-spec-round-2.md
└── my-feature-spec-round-3.md
```

Use these to rollback if a revision makes things worse.

### Retry on API Failure

API calls automatically retry with exponential backoff (1s, 2s, 4s) up to 3 times. If a model times out or rate-limits, you'll see:

```
Warning: codex/gpt-5.2-codex failed (attempt 1/3): rate limit exceeded. Retrying in 1.0s...
```

If all retries fail, the error is reported and other models continue.

### Response Validation

If a model provides critique but doesn't include proper `[SPEC]` tags, a warning is displayed:

```
Warning: codex/gpt-5.2-codex provided critique but no [SPEC] tags found. Response may be malformed.
```

This catches cases where models forget to format their revised spec correctly.

### Preserve Intent Mode

Convergence can collapse toward lowest-common-denominator interpretations, sanding off novel design choices. The `--preserve-intent` flag makes removals expensive:

```bash
python3 debate.py critique --models codex/gpt-5.2-codex --preserve-intent --doc-type tech <<'SPEC_EOF'
<spec here>
SPEC_EOF
```

When enabled, models must:

1. **Quote exactly** what they want to remove or substantially change
2. **Justify the harm** - not just "unnecessary" but what concrete problem it causes
3. **Distinguish error from preference**:
   - ERRORS: Factually wrong, contradictory, or technically broken (remove/fix)
   - RISKS: Security holes, scalability issues, missing error handling (flag)
   - PREFERENCES: Different style, structure, or approach (DO NOT remove)
4. **Ask before removing** unusual but functional choices

This shifts the default from "sand off anything unusual" to "add protective detail while preserving distinctive choices."

**Use when:**
- Your spec contains intentional unconventional choices
- You want models to challenge your ideas, not homogenize them
- Previous rounds removed things you wanted to keep
- You're refining an existing spec that represents deliberate decisions

Can be combined with other flags: `--preserve-intent --focus security`

### Cost Tracking

Every critique round displays token usage and estimated cost:

```
=== Cost Summary ===
Total tokens: 12,543 in / 3,221 out
Total cost: $0.0847

By model:
  codex/gpt-5.2-codex: $0.00 (8,234 in / 2,100 out) [subscription]
  gemini-cli/gemini-3-pro-preview: $0.00 (4,309 in / 1,121 out) [free tier]
```

Cost is also included in JSON output and Telegram notifications.

### Saved Profiles

Save frequently used configurations as profiles:

**Create a profile:**
```bash
python3 debate.py save-profile strict-security --models codex/gpt-5.2-codex,gemini-cli/gemini-3-pro-preview --focus security --doc-type tech
```

**Use a profile:**
```bash
python3 debate.py critique --profile strict-security <<'SPEC_EOF'
<spec here>
SPEC_EOF
```

**List profiles:**
```bash
python3 debate.py profiles
```

Profiles are stored in `~/.config/adversarial-spec/profiles/`.

Profile settings can be overridden by explicit flags.

### Diff Between Rounds

Generate a unified diff between spec versions:

```bash
python3 debate.py diff --previous round1.md --current round2.md
```

Use this to see exactly what changed between rounds. Helpful for:
- Understanding what feedback was incorporated
- Reviewing changes before accepting
- Documenting the evolution of the spec

### Export to Task List

Extract actionable tasks from a finalized spec:

```bash
cat spec-output.md | python3 debate.py export-tasks --models codex/gpt-5.2-codex --doc-type prd
```

Output includes:
- Title
- Type (user-story, task, spike, bug)
- Priority (high, medium, low)
- Description
- Acceptance criteria

Use `--json` for structured output suitable for importing into issue trackers:

```bash
cat spec-output.md | python3 debate.py export-tasks --models codex/gpt-5.2-codex --doc-type prd --json > tasks.json
```

## Script Reference

```bash
# Core commands
python3 debate.py critique --models MODEL_LIST --doc-type TYPE [OPTIONS] < spec.md
python3 debate.py critique --resume SESSION_ID
python3 debate.py diff --previous OLD.md --current NEW.md
python3 debate.py export-tasks --models MODEL --doc-type TYPE [--json] < spec.md

# Info commands
python3 debate.py providers      # List supported providers and API key status
python3 debate.py focus-areas    # List available focus areas
python3 debate.py personas       # List available personas
python3 debate.py profiles       # List saved profiles
python3 debate.py sessions       # List saved sessions

# Profile management
python3 debate.py save-profile NAME --models ... [--focus ...] [--persona ...]

# Telegram
python3 debate.py send-final --models MODEL_LIST --doc-type TYPE --rounds N < spec.md

# Gauntlet
python3 debate.py gauntlet --gauntlet-adversaries all < spec.md
python3 debate.py gauntlet-adversaries  # List adversary personas
python3 debate.py adversary-stats       # View adversary performance
```

**Critique options:**
- `--models, -m` - Comma-separated model list (auto-detects from available API keys if not specified)
- `--doc-type, -d` - Document type: prd or tech (default: tech)
- `--round, -r` - Current round number (default: 1)
- `--focus, -f` - Focus area for critique
- `--persona` - Professional persona for critique
- `--context, -c` - Context file (can be used multiple times)
- `--profile` - Load settings from saved profile
- `--preserve-intent` - Require explicit justification for any removal
- `--session, -s` - Session ID for persistence and checkpointing
- `--resume` - Resume a previous session by ID
- `--press, -p` - Anti-laziness check for early agreement
- `--telegram, -t` - Enable Telegram notifications
- `--poll-timeout` - Telegram reply timeout in seconds (default: 60)
- `--json, -j` - Output as JSON
- `--codex-search` - Enable web search for Codex CLI models (allows researching current info)
- `--timeout` - Timeout in seconds for model API/CLI calls (default: 600)
- `--show-cost` - Show cost summary after critique

## Adversarial Gauntlet

The gauntlet is a multi-phase stress test that puts your spec through adversarial attack by specialized personas, then evaluates which attacks are valid.

### Gauntlet Phases

1. **Phase 1: Adversary Attacks** - Multiple adversary personas attack the spec in parallel
2. **Phase 2: Evaluation** - A frontier model evaluates each attack (accept/dismiss/defer)
3. **Phase 3: Rebuttals** - Dismissed adversaries can challenge the evaluation
4. **Phase 4: Summary** - Aggregated results showing accepted concerns
5. **Phase 5: Final Boss** (optional) - Opus 4.5 UX Architect reviews the spec holistically

### Adversary Personas

| Persona | Focus |
|---------|-------|
| `paranoid_security` | Auth holes, injection, encryption gaps, trust boundaries |
| `burned_oncall` | Missing alerts, log gaps, failure modes, debugging at 3am |
| `lazy_developer` | Ambiguity, missing examples, tribal knowledge assumptions |
| `pedantic_nitpicker` | Inconsistencies, spec gaps, undefined edge cases |
| `asshole_loner` | Aggressive devil's advocate, challenges fundamental assumptions |

### Usage

```bash
# Run gauntlet with all adversaries
cat spec.md | python3 debate.py gauntlet --gauntlet-adversaries all

# Run with specific adversaries
cat spec.md | python3 debate.py gauntlet --gauntlet-adversaries paranoid_security,burned_oncall

# Combine with regular critique (gauntlet runs first)
cat spec.md | python3 debate.py critique --models gpt-4o --gauntlet --gauntlet-adversaries all

# Skip rebuttals for faster execution
cat spec.md | python3 debate.py gauntlet --gauntlet-adversaries all --no-rebuttals

# List available adversaries
python3 debate.py gauntlet-adversaries

# View adversary performance stats
python3 debate.py adversary-stats
```

### Final Boss Review

After phase 4 completes, you'll be prompted:

```
Run Final Boss UX review? (y/n):
```

The Final Boss is an Opus 4.5 UX Architect who reviews the spec for:
- User journey completeness
- Error state handling
- Accessibility concerns
- Overall coherence

This is expensive but thorough. You can also pre-commit with `--final-boss` to skip the prompt.

### Gauntlet Options

- `--gauntlet, -g` - Enable gauntlet mode (can combine with critique)
- `--gauntlet-adversaries` - Comma-separated adversaries or 'all'
- `--gauntlet-model` - Model for adversary attacks (default: auto-select free model)
- `--gauntlet-frontier` - Model for evaluation (default: auto-select frontier model)
- `--no-rebuttals` - Skip Phase 3 rebuttal phase
- `--final-boss` - Auto-run Phase 5 (skips prompt)

## Execution Planning (Phase 6)

After the spec is finalized (and optionally after gauntlet), offer to generate an execution plan:

> "Spec is finalized. Would you like me to generate an execution plan for implementation?"

**Update Tasks:** Use `TaskUpdate` to mark Phase 6 tasks as `in_progress`/`completed` as you progress. Set owner to `adv-spec:planner`.

### Running the Execution Planning Pipeline

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py execution-plan \
  --spec-file spec-output.md \
  --plan-format markdown \
  --plan-output execution-plan.md
```

The pipeline runs 6 steps:

1. **Spec Intake (FR-1)** - Parse the spec, detect document type (PRD/tech)
2. **Scope Assessment (FR-2)** - Recommend single-agent vs multi-agent execution
3. **Task Plan Generation (FR-3)** - Create implementation tasks with:
   - Linked gauntlet concerns
   - Spec section references
   - Acceptance criteria derived from concerns
   - Test cases derived from failure modes
4. **Test Strategy Configuration (FR-4)** - Assign test-first vs test-after
5. **Over-Decomposition Guard (FR-5)** - Warn if plan is too granular
6. **Parallelization Analysis (FR-6)** - Identify workstreams and merge points

### Output Formats

- `--plan-format json` - Full structured output for programmatic use
- `--plan-format markdown` - Human-readable document
- `--plan-format summary` - Brief terminal overview

### Linking Gauntlet Concerns

If gauntlet was run, the concerns JSON is auto-detected. Otherwise specify:

```bash
python3 debate.py execution-plan \
  --spec-file spec-output.md \
  --concerns-file gauntlet-concerns-2026-01-23.json
```

Concerns are linked to tasks by section reference, giving each task:
- Related concerns with severity
- Acceptance criteria derived from failure modes
- Test cases derived from detection strategies

## Implementation (Phase 7)

After the execution plan is generated, offer to proceed with implementation:

> "Execution plan generated with N tasks. Would you like to proceed with implementation?"

**Update Tasks:** Use `TaskCreate` to add each implementation task from the execution plan. Include metadata for linking:

### Adding Implementation Tasks

For each task in the execution plan, use `TaskCreate` with:
- **subject:** Task title
- **description:** Full task description with acceptance criteria
- **activeForm:** "Implementing: {title}"
- **owner:** `adv-spec:impl:{workstream}` (e.g., `adv-spec:impl:backend`)
- **metadata:** Include `concern_ids`, `spec_refs`, `effort`, `risk_level`, `validation`
- **blockedBy:** Task IDs from execution plan's dependency graph

Example task creation:
```json
{
  "subject": "Implement schema: orders",
  "description": "Create database schema for orders table with fields...",
  "activeForm": "Implementing: orders schema",
  "owner": "adv-spec:impl:backend",
  "metadata": {
    "phase": "implementation",
    "concern_ids": ["PARA-abc123", "BURN-def456"],
    "spec_refs": ["Section 3.2"],
    "effort": "S",
    "risk_level": "medium",
    "validation": "test-after"
  }
}
```

Visual format (for display):
```
Phase 7: Implementation
- [S] Implement schema: orders (medium risk, 2 concerns)
- [S] Implement schema: order_queue (low risk)
- [M] Implement endpoint: orders:placeDma (high risk, 5 concerns)
- [ ] [M] Implement endpoint: orders:placeArbitrage (high risk, 3 concerns)
- [ ] [S] Implement scheduled function: syncOrderStatus (low risk)
```

### Task Execution

Work through implementation tasks in dependency order:

1. Mark task as `in_progress`
2. Read the full task description from the execution plan
3. Follow the validation strategy (test-first or test-after)
4. Address all acceptance criteria, including those from concerns
5. Run the test cases
6. Mark task as `completed`
7. Move to next task

**High-risk tasks** (3+ concerns) use test-first validation:
- Write tests based on test cases before implementation
- Ensure tests cover failure modes from concerns
- Implementation must pass all tests

**Lower-risk tasks** use test-after validation:
- Implement the feature
- Write tests after
- Still address all acceptance criteria

### Parallelization

If the plan recommends multi-agent execution and multiple workstreams:

1. Review the workstream assignments
2. Consider parallel execution for independent streams
3. Coordinate at merge points
4. Follow the recommended branch pattern

The execution plan's `parallelization` section provides:
- `streams` - Independent workstreams with task IDs
- `merge_sequence` - Order and risk of merging streams
- `branch_pattern` - Recommended git branching strategy
