# Adversarial-Spec Process Failure Report

**Session:** Targeted Documentation Lookup Protocol
**Date:** 2026-01-27
**Rounds Completed:** 3
**Critical Gap Identified:** User stories and use cases were never defined

---

## Executive Summary

The adversarial-spec session for the Targeted Documentation Lookup Protocol ran 3 full debate rounds with two frontier models (Gemini 3 Pro, GPT-5.2 Codex) without ever establishing clear user stories or validating requirements with the user. The resulting spec is technically detailed but missed fundamental workflow questions until the user explicitly asked: "Is there a defined sequence of steps for how we will bootstrap the initial indexing?"

This represents a systemic failure in the adversarial-spec process itself.

---

## What Went Wrong

### 1. No User Stories Before Debate

The spec jumped directly into technical architecture without defining WHO would use this system and WHAT they're trying to accomplish. The following user stories should have been defined BEFORE Round 1:

**Missing User Stories:**

```
US-1: Developer Bootstrapping New API
  AS A developer starting a new project against an API (e.g., Kalshi)
  I WANT TO quickly set up documentation lookup for that API
  SO THAT I can get targeted, token-efficient answers about API endpoints

US-2: LLM Agent Using Documentation
  AS AN LLM agent (Claude Code) working on code
  I WANT TO query API documentation with minimal token overhead
  SO THAT I can implement features without wasting context on bulk docs

US-3: Adversarial-Spec Using Documentation
  AS THE adversarial-spec skill validating external API interfaces
  I WANT TO fetch and verify API documentation during spec development
  SO THAT specs don't contain invented/incorrect API contracts

US-4: Developer Refreshing Stale Documentation
  AS A developer whose local docs are outdated
  I WANT TO refresh documentation from upstream
  SO THAT I'm working against current API contracts

US-5: Developer Switching Projects
  AS A developer switching between projects (Kalshi → Polymarket → unrelated)
  I WANT TO enable/disable documentation sources per project
  SO THAT I don't pay token overhead for irrelevant docs
```

### 2. No User Q&A After Round 1

Round 1 should have included a checkpoint asking the user:

- "What's your primary use case for this tool?"
- "How do you expect to bootstrap documentation initially?"
- "What's your workflow when starting a new API integration?"
- "Do you need this to work without Context7 available?"

Instead, Round 1 went straight into technical critiques about:
- Data model insufficiency (TypeSchema)
- Markdown parsing strategies
- Search ranking algorithms
- CLI output optimization

These are valid concerns, but they're implementation details disconnected from user goals.

### 3. Bootstrap Workflow Was an Afterthought

The bootstrap workflow—arguably the most important user-facing feature—was:
- Not mentioned in the original spec
- Not raised by either opponent model in 3 rounds
- Only addressed when the user explicitly asked

**Timeline:**
| Round | Focus | Bootstrap Mentioned? |
|-------|-------|---------------------|
| 1 | Data models, parsing strategies | No |
| 2 | Registry patterns, ID generation | No |
| 3 | Search algorithms, token pre-calc | No |
| Post-debate | User asks | Finally addressed |

### 4. Debate Optimized for Technical Correctness, Not User Value

Both opponent models (Gemini, Codex) critiqued:
- O(N) search algorithms
- Runtime token estimation overhead
- Dynamic import security risks
- ID collision handling

These are valid technical concerns. But neither asked:
- "How does a user actually get documentation into this system?"
- "What happens if Context7 isn't available?"
- "What's the happy path for a new user?"

The models were debating HOW to build a system without establishing WHAT the system should accomplish for users.

---

## Impact

### Spec Quality Issues

1. **Bootstrap workflow undefined for 3 rounds** - Added only after user intervention
2. **No acceptance criteria** - How do we know the spec is "done"?
3. **No user journey mapping** - Spec describes components, not experiences
4. **Technical debt in spec itself** - Rework required to add fundamental features

### Process Issues

1. **User forced to intervene** - User shouldn't need to ask "wait, how does setup work?"
2. **Wasted debate rounds** - 3 rounds on implementation before validating requirements
3. **False sense of completeness** - Spec appeared thorough but missed core workflows

---

## Root Cause Analysis

### Process Gap: Missing Requirements Phase

The adversarial-spec skill instructions include:

```
Phase 1: Requirements Gathering
- [ ] Determine document type (PRD/tech/debug)
- [ ] Identify starting point (existing file or new concept)
- [ ] Offer interview mode (PRD/tech only; debug skips interview)
- [ ] Conduct interview (if selected, PRD/tech only)
```

**However:**
- Interview mode was not offered
- User stories were not gathered
- The "interview topics" (Problem & Context, Users & Stakeholders, Functional Requirements) were skipped
- Debate started immediately after generating an initial draft

### Why This Happened

1. **Onboarding docs provided context** - The skill saw existing architecture docs and assumed requirements were known
2. **Tech spec bias** - Tech specs often skip user stories (incorrectly)
3. **Model behavior** - Opponent models critique what's in front of them, not what's missing
4. **No explicit checkpoint** - Process doesn't require user validation after Round 1

---

## Recommendations for Adversarial-Spec Process

### 1. MANDATORY User Stories Before Debate

Add to Phase 1 (before any debate rounds):

```markdown
## Phase 1.5: User Story Definition (REQUIRED)

Before generating the initial spec draft, define 3-5 user stories:

1. **Primary User Story**: The main use case this system serves
2. **Setup/Bootstrap Story**: How a new user gets started
3. **Daily Usage Story**: The common workflow after setup
4. **Edge Case Story**: What happens when things go wrong

Format:
  AS A [user type]
  I WANT TO [action]
  SO THAT [benefit]

These user stories become ACCEPTANCE CRITERIA for the spec.
Do not proceed to debate until user confirms these stories.
```

### 2. Round 1 Must Include User Validation

After Round 1 critiques, BEFORE applying changes:

```markdown
## Round 1 Checkpoint (REQUIRED)

Before synthesizing Round 1 feedback, ask the user:

1. "Based on opponent critiques, here are the main technical concerns: [list]
   Do any of these conflict with your priorities?"

2. "The spec currently assumes [X workflow]. Is this how you expect to use it?"

3. "Are there any user scenarios we haven't addressed?"

Do not proceed to Round 2 until user confirms direction.
```

### 3. Bootstrap/Setup Must Be Explicit Section

For any tool/system spec, require:

```markdown
## Getting Started (REQUIRED SECTION)

Every tech spec must include a "Getting Started" section that answers:

1. What does a new user need before they can use this?
2. What's the step-by-step first-run experience?
3. What happens if prerequisites aren't met?
4. How long until a user can perform their first real task?

This section should be written BEFORE implementation details.
```

### 4. Opponent Model Prompt Enhancement

Add to the critique prompt sent to opponent models:

```markdown
## Critique Requirements

In addition to technical review, you MUST address:

1. **User Journey**: Is there a clear path from "new user" to "productive user"?
2. **Setup/Bootstrap**: How does a user get started? Is this defined?
3. **Error Recovery**: What happens when things go wrong?
4. **Missing Use Cases**: What user scenarios are NOT addressed?

If the spec lacks user stories or a clear setup workflow, this is a CRITICAL gap
that must be raised before any implementation details are discussed.
```

### 5. Debate Round Focus Progression

Structure rounds with explicit focus:

```markdown
## Debate Round Structure

Round 1: REQUIREMENTS VALIDATION
- Are user stories complete?
- Is the setup/bootstrap workflow defined?
- Are acceptance criteria clear?
- USER CHECKPOINT before proceeding

Round 2: ARCHITECTURE & DESIGN
- Component design
- Data models
- API contracts

Round 3: IMPLEMENTATION DETAILS
- Algorithms
- Performance
- Security
- Error handling

Round 4+: REFINEMENT
- Edge cases
- Polish
```

---

## The User Stories That Should Have Been

Here are the user stories that should have driven this spec from the start:

### US-1: Developer Bootstrapping New API Documentation

```
AS A developer starting work on a Kalshi trading bot
I WANT TO set up targeted documentation lookup for Kalshi's API
SO THAT I can query specific endpoints without loading 400KB of docs

ACCEPTANCE CRITERIA:
- [ ] Can bootstrap from Context7 if available
- [ ] Can bootstrap from URL if Context7 unavailable
- [ ] Can bootstrap manually if neither available
- [ ] Setup takes < 5 minutes
- [ ] Clear error messages if something fails
- [ ] Can verify setup worked before disabling Context7
```

### US-2: LLM Agent Querying Documentation

```
AS Claude Code working on trading bot implementation
I WANT TO query "how to place an order on Kalshi"
SO THAT I get only the relevant endpoint info (~100 tokens) not bulk docs (~10K tokens)

ACCEPTANCE CRITERIA:
- [ ] Query returns < 500 tokens for typical questions
- [ ] Results are ranked by relevance
- [ ] Can request more detail if needed (graduated levels)
- [ ] Zero always-on token overhead (CLI-based)
- [ ] < 200ms latency for queries
```

### US-3: Adversarial-Spec Verifying API Interfaces

```
AS THE adversarial-spec skill writing a tech spec
I WANT TO verify that API interfaces in my spec match actual documentation
SO THAT I don't hallucinate field names or invent endpoints

ACCEPTANCE CRITERIA:
- [ ] Can fetch current documentation during spec development
- [ ] Can query specific endpoints to verify schemas
- [ ] Documentation source is cited in spec
- [ ] Warning if documentation couldn't be verified
```

### US-4: Developer Switching Projects

```
AS A developer who works on multiple trading projects
I WANT TO enable Kalshi docs for Project A, Polymarket for Project B
SO THAT each project only loads relevant documentation

ACCEPTANCE CRITERIA:
- [ ] Per-project MCP configuration
- [ ] Disabled sources have zero overhead
- [ ] Can quickly switch active sources
- [ ] Sources don't interfere with each other
```

### US-5: Developer Refreshing Documentation

```
AS A developer whose Kalshi integration broke after an API update
I WANT TO refresh my local documentation from upstream
SO THAT I'm working against the current API contract

ACCEPTANCE CRITERIA:
- [ ] Single command to refresh: `docmaster fetch kalshi`
- [ ] Automatic re-indexing after fetch
- [ ] Can rollback if new docs break something
- [ ] Notified if docs changed significantly
```

---

## Conclusion

The adversarial-spec process successfully produced a technically sound specification, but it failed to anchor that specification in user needs. Three rounds of debate with frontier models refined data models, search algorithms, and security considerations—but none of that matters if users can't figure out how to get started.

**Key Lesson:** Technical correctness is necessary but not sufficient. User stories and workflows must be defined BEFORE implementation details are debated.

**Recommended Action:** Update the adversarial-spec skill to:
1. Require user stories before debate
2. Add a mandatory user checkpoint after Round 1
3. Require a "Getting Started" section in all tech specs
4. Prompt opponent models to critique missing user journeys

---

## Appendix: Session Statistics

| Metric | Value |
|--------|-------|
| Total Rounds | 3 |
| Opponent Models | gemini-cli/gemini-3-pro-preview, codex/gpt-5.2-codex |
| User Checkpoints | 0 (should have been 1+) |
| User Stories Defined | 0 (should have been 3-5) |
| Bootstrap Workflow Defined | Round 4 (after user asked) |
| Lines of Spec Before Bootstrap Section | ~600 |
| Lines Added for Bootstrap | ~120 |
