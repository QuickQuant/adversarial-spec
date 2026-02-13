### Step 1: Verify Roadmap Exists (GATE)

**BLOCKING CHECK:** Before ANY debate work, verify that roadmap artifacts from Phase 2 exist.

```bash
# Check for roadmap artifacts
ROADMAP_EXISTS=false

# Check 1: roadmap folder with manifest.json (medium/complex projects)
if [ -f "roadmap/manifest.json" ]; then
  echo "✓ Found roadmap/manifest.json"
  ROADMAP_EXISTS=true
fi

# Check 2: inline roadmap in session file (simple projects)
if [ -f ".adversarial-spec/session-state.json" ]; then
  if grep -q '"user_stories"' .adversarial-spec/sessions/*.json 2>/dev/null; then
    US_COUNT=$(cat .adversarial-spec/sessions/*.json | grep -o 'US-[0-9]*' | sort -u | wc -l)
    if [ "$US_COUNT" -gt 0 ]; then
      echo "✓ Found $US_COUNT user stories in session file"
      ROADMAP_EXISTS=true
    fi
  fi
fi

if [ "$ROADMAP_EXISTS" = false ]; then
  echo "✗ NO ROADMAP ARTIFACTS FOUND"
  echo ""
  echo "You must complete Phase 2 (Roadmap) before entering debate."
  echo "Run: Read ~/.claude/skills/adversarial-spec/phases/02-roadmap.md"
fi
```

**If no roadmap artifacts exist:**
> ⛔ **STOP.** Do not proceed to debate.
>
> The roadmap phase (02-roadmap.md) must be completed first, including:
> - User stories (US-0, US-1, etc.) defined and validated
> - Roadmap artifacts persisted (Step 6 of 02-roadmap.md)
> - User confirmation checkpoint passed
>
> **Action:** Return to `02-roadmap.md` and complete all steps including artifact persistence.

**Only proceed to Step 2 if roadmap verification passes.**

---

### Step 2: Load Roadmap User Stories (REQUIRED)

**CRITICAL:** Before generating any spec draft, load and use the user stories from Phase 1.5/2.

**Load roadmap artifacts:**
```bash
# Load from roadmap folder (medium/complex)
if [ -f "roadmap/manifest.json" ]; then
  cat roadmap/manifest.json
fi

# Or load from session file (simple)
cat .adversarial-spec/sessions/*.json | jq '.roadmap // .user_stories'
```

**Extract user stories:**
- Parse all `US-X` entries from the roadmap
- Note their associated milestones
- Identify the "Getting Started" user story (US-0) if present
- Collect success criteria for each story

**Create a User Story Reference Table** for use during spec generation:

```markdown
## Roadmap User Stories (from Phase 2)

| ID | Story | Milestone | Success Criteria |
|----|-------|-----------|------------------|
| US-0 | As a new user, I want to set up... | M0: Bootstrap | Setup < 5 min, clear errors |
| US-1 | As a developer, I want to... | M1: Core | Can query docs, < 500 tokens |
| US-2 | ... | M1: Core | ... |
```

**If no roadmap exists:** This is an error. Return to Phase 1.5/2 (02-roadmap.md) to create one. Do NOT proceed to generate a spec without user stories.

### Step 2.5: Load or Generate Initial Document

**If user provided a file path:**
- Read the file using the Read tool
- Validate it has content
- **Map existing sections to user stories** - identify which US-X each section addresses
- Flag any user stories without corresponding sections
- Use it as the starting document

**If generating from scratch (no existing file):**

Build the spec draft **anchored to roadmap user stories**:

1. **Review user stories first.** For each US-X, determine:
   - Which spec section(s) will address this story
   - What details are needed beyond what the roadmap specifies
   - What assumptions need to be validated

2. **Ask targeted clarifying questions** only for gaps NOT covered by the roadmap:
   - Don't ask "Who are the target users?" if US-X already defines them
   - Do ask implementation details: "For US-2 (data export), what formats are needed?"
   - Ask 2-4 focused questions. Reference specific user stories in your questions.

3. **Generate a complete document** that explicitly addresses each user story:
   - **For each US-X, create corresponding spec sections**
   - Use comments like `<!-- Addresses US-1, US-2 -->` to maintain traceability
   - Cover all sections even if some require assumptions
   - State assumptions explicitly so opponent models can challenge them
   - For product depth: Include placeholder metrics that the user can refine
   - For technical/full depth: Include concrete choices that can be debated

   **REQUIRED for technical/full depth:** The spec MUST include a "Getting Started" section addressing US-0 from the roadmap. This section must answer:
   - What does a new user need before they can use this? (prerequisites)
   - What's the step-by-step first-run experience? (setup workflow)
   - What happens if prerequisites aren't met? (error handling)
   - How long until a user can perform their first real task? (time to value)

   **If US-0 is missing from the roadmap**, return to Phase 2 (02-roadmap.md) to add it before generating the spec.

4. **Present the draft with user story mapping** before sending to opponent models:
   - Show the full document
   - Show which user stories each section addresses
   - Flag any user stories without clear coverage
   - Ask: "Does this capture your intent? Any user stories need better coverage?"
   - Incorporate user feedback before proceeding

Output format (whether loaded or generated):
```
[SPEC]
<document content here>
[/SPEC]
```

### Step 2.6: Information Flow Audit (For Technical/Full Depth Specs)

**CRITICAL**: Before finalizing any technical spec with architecture diagrams, audit every information flow.

Every arrow in an architecture diagram represents a mechanism decision. If you don't make that decision explicitly, you'll default to familiar patterns that may not fit the requirements.

**Example Failure:** A spec showed `Worker -> Exchange (order)` and `Exchange -> Worker (result)`. Everyone assumed "result" meant polling. Reality: the exchange provided real-time WebSocket push. The spec required 200ms latency; polling would have 5000ms. 62 adversary concerns were raised about error handling for the polling implementation - all of which would have been avoided with WebSocket.

**For each arrow/flow in your architecture:**

1. **What mechanism?** REST poll? WebSocket push? Webhook callback? Queue?

2. **What does the source system support?** Before assuming, check:
   - If Context7 MCP tools are available, query the external system's documentation
   - Look for: WebSocket channels, webhook endpoints, streaming APIs
   - Don't assume polling is the only option

3. **Does it meet latency requirements?** If a requirement says "<500ms", polling at 5s intervals won't work.

**Add an Information Flow table to technical specs:**

```markdown
## Information Flows

| Flow | Source | Destination | Mechanism | Latency | Source Capabilities | Justification |
|------|--------|-------------|-----------|---------|---------------------|---------------|
| Order submission | Worker | Exchange | REST POST | ~100ms | REST only | N/A |
| Fill notification | Exchange | Worker | WebSocket | <50ms | WebSocket USER_CHANNEL, REST poll | Real-time needed for 200ms requirement |
```

This prevents the gauntlet from flagging unspecified flows after you've already designed around the wrong mechanism.

### Step 2.7: External API Interface Verification (For Technical/Full Depth Specs)

**CRITICAL**: When defining TypeScript/Python interfaces for external API responses, DO NOT GUESS.

AI models pattern-match what they think an API "probably" looks like based on training data. This leads to specs with wrong field names, missing fields, and invented fields that don't exist.

**Example Failure (Real Bug):**
```typescript
// WHAT 3 FRONTIER MODELS AGREED ON (WRONG):
interface KalshiOrderResponse {
  filled_count: number;        // ❌ WRONG - API uses "fill_count"
  average_fill_price?: number; // ❌ DOESN'T EXIST in API
}
```

Three frontier models agreed on this interface. None checked. The implementation failed at runtime.

**Before defining ANY external API interface, check these sources IN ORDER:**

1. **SDK TYPE DEFINITIONS (Best Source)**
   If an official SDK exists, its `.d.ts` files are authoritative:
   ```bash
   # Find exact field names:
   grep -A 50 "export interface Order" node_modules/kalshi-typescript/dist/models/order.d.ts

   # Search for specific field:
   grep -rn "fill_count" node_modules/kalshi-typescript/dist/
   ```
   SDK types are auto-generated from OpenAPI specs - always correct, always up to date.

2. **LOCAL API DOCUMENTATION**
   Check `api_documentation/` or `api-reference/` folders for cached docs.

3. **CONTEXT7 (If SDK unavailable)**
   Use MCP tools: `mcp__context7__resolve-library-id` → `mcp__context7__query-docs`

4. **ASK THE USER**
   If no SDK and no docs found, ask for a documentation link. DO NOT proceed with guesses.

**In the spec, cite the source:**
```typescript
// Source: node_modules/kalshi-typescript/dist/models/order.d.ts
// Verified: 2026-01-27
interface KalshiOrder {
  fill_count: number;  // NOT "filled_count"
  // ... copy exact fields from SDK
}
```

**If no authoritative source exists:**
Mark as `UNVERIFIED` and flag for user:
```typescript
// ⚠️ UNVERIFIED - No SDK or docs found
// TODO: Verify against actual API before implementation
interface SomeApiResponse { ... }
```

### Step 3: Select Opponent Models

First, check which API keys are configured:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py providers
```

Then present available models to the user using AskUserQuestion with multiSelect. Build the options list based on which API keys are set:

**If OPENAI_API_KEY is set, include:**
- `gpt-5.3` - Frontier reasoning

**If ANTHROPIC_API_KEY is set, include:**
- `claude-sonnet-4-5-20250929` - Claude Sonnet 4.5, excellent reasoning
- `claude-opus-4-6` - Claude Opus 4.6, highest capability

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
- `codex/gpt-5.3-codex` - OpenAI Codex with extended reasoning

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
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models MODEL_LIST --doc-type spec --depth DEPTH <<'SPEC_EOF'
<paste your document here>
SPEC_EOF
```

Replace:
- `MODEL_LIST`: comma-separated models from user selection
- `DEPTH`: `product`, `technical`, or `full` (based on spec depth from Phase 1)

For debug investigations, use `--doc-type debug` (no --depth needed).

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

**Debate Round Focus Progression:**

Each round has a specific focus. This prevents deep-diving into implementation before requirements are validated.

| Round | Focus | What to Review |
|-------|-------|----------------|
| **Round 1** | REQUIREMENTS VALIDATION | User story coverage, Getting Started section, success criteria clarity |
| **Round 2** | ARCHITECTURE & DESIGN | Component design, data models, API contracts, system boundaries |
| **Round 3** | IMPLEMENTATION DETAILS | Algorithms, performance targets, security, error handling |
| **Round 4+** | REFINEMENT | Edge cases, polish, final consistency checks |

**Important:** Do not accept critiques about Round 3 topics (algorithms, performance) in Round 1 - defer them to the appropriate round. Requirements must be validated before implementation details are debated.

---

**Round 1 Roadmap Validation (REQUIRED for Spec documents):**

In Round 1, BEFORE reviewing technical details, **confirm** the spec addresses all roadmap user stories. Since the spec was generated anchored to user stories (Step 2), this is a verification step, not a discovery step.

1. **Confirm User Story Coverage:** Verify the spec addresses ALL user stories from the roadmap.
   - The spec should already have `<!-- Addresses US-X -->` markers from Step 2.5
   - For each `US-X` in roadmap, confirm the corresponding spec section exists and is substantive
   - **If a user story lacks coverage:** This is a Step 2.5 error. Return to Step 2.5 to address it before continuing debate.

2. **Confirm Getting Started Exists:** For technical/full depth:
   - A "Getting Started" or "Bootstrap" section should already exist (addressing US-0)
   - The bootstrap workflow from the roadmap should be documented
   - New users can understand how to set up the system
   - **If missing:** Return to Step 2.5 to add it

3. **Confirm Success Criteria Are Testable:** For each success criterion:
   - Is it specific enough to write a test for?
   - If not, flag for clarification (this is expected - criteria often need refinement)

4. **USER CHECKPOINT (Round 1 only):**
   After Round 1 synthesis, present findings to the user:
   > "Round 1 confirmed user story coverage:
   > - [list US-X → section mappings]
   >
   > Technical concerns raised:
   > - [list concerns from opponent models and Claude]
   >
   > Success criteria needing clarification:
   > - [list if any]
   >
   > Before Round 2, do any of these conflict with your priorities?"

   Do NOT proceed to Round 2 until user confirms direction.

---

**Context Readiness Audit (between Round 1 and Round 2, REQUIRED for technical/full depth):**

After Round 1 validates requirements and before Round 2 debates architecture, audit what codebase context is available to inform the remaining debate and the eventual gauntlet.

**Why here:** Round 1 is about user value (no codebase context needed). Round 2 is about architecture (codebase context critical). Gaps discovered now have time to be addressed — tasks can complete while debate proceeds.

**Process:**

1. **Identify the blast zone.** Parse the spec for file paths, module names, table names, function names, and external services. These are the files/modules the spec will likely modify.

2. **Check context sources against this checklist:**

   | Context Source | Check Method | Who Benefits |
   |---------------|-------------|--------------|
   | Architecture docs | `[ -f .architecture/manifest.json ]` | ALL (base context) |
   | Schema/type definitions | Grep for table/interface names in blast zone | PEDA, COMP |
   | Test coverage | Check for pytest-cov config or recent coverage report | PEDA, COMP |
   | Dependency inventory | Read pyproject.toml / package.json | LAZY, PREV, PARA |
   | Git recent changes | `git log --oneline -10 -- <blast zone files>` | COMP, PREV |
   | Build/test status | `uv run pytest --tb=short` (or equivalent) | COMP |
   | Monitoring/metrics | Check for alerting config, dashboards, SLIs | BURN |
   | Error handling patterns | Grep for try/except, circuit breaker, retry in blast zone | BURN |
   | Auth/authz patterns | Grep for auth, permission, token in blast zone | PARA |
   | External API docs | Check for SDK, cached docs, Context7 availability | AUDT, FLOW |
   | Legacy/archive dirs | `find . -type d -name "_legacy" -o -name "deprecated"` | PREV |
   | Design rationale (ADRs) | Check for decision docs, spec history | ASSH |
   | Existing similar features | Grep for feature keywords across codebase | PREV, LAZY |

3. **Classify each source:** `AVAILABLE`, `PARTIAL`, `NOT_AVAILABLE`, or `NOT_APPLICABLE`.

4. **For PARTIAL sources, determine if gap is actionable:**
   - Can we generate a coverage report now? → Suggest task
   - Can we fetch API docs via Context7? → Suggest task
   - Is this a fundamental gap the spec SHOULD address? → Note for Round 2+

5. **Present to user:**

   ```
   Context Readiness Audit
   ═══════════════════════════════════════
   Blast zone: 5 files, 3 modules

   ✓ AVAILABLE (6)
     Architecture docs, schema definitions, type definitions,
     dependency inventory, git history, build status

   ⚠ GAPS (2)
     Test coverage — no pytest-cov configured
       → Can generate now (spawns 30s task)
     External API docs — spec references FooAPI, no local docs
       → Can fetch via Context7 (spawns task)

   ✗ NOT AVAILABLE (1)
     Monitoring data — no alerting configured
       → This is a design gap. Round 3 should address it.

   ─ NOT APPLICABLE (1)
     Incident reports — not relevant for CLI tool

   [Generate available gaps] [Proceed without] [Choose which]
   ```

6. **Cache inventory in session state** as `ContextInventoryV1`:

   ```json
   {
     "schema_version": "1.0",
     "audit_timestamp": "ISO-8601",
     "git_hash": "short hash",
     "blast_zone": ["file1.py", "file2.py"],
     "sources": {
       "source_id": {
         "status": "available|partial|not_available|not_applicable",
         "path": "string or null",
         "summary": "one-line description",
         "est_tokens": 1200,
         "actionable": false,
         "task_id": null
       }
     },
     "total_available_tokens": 8500,
     "gaps_noted": ["description of design gaps for later rounds"]
   }
   ```

   This inventory is reused by:
   - **Context-addition-protocol** — debate round appendices draw from it instead of re-extracting
   - **Arm Adversaries** — gauntlet briefings are assembled from it (see 04-gauntlet.md)

   **Staleness rule:** If `git rev-parse --short HEAD` differs from `git_hash` in inventory, re-extract only the sources whose files were modified.

**After the audit, proceed to Round 2.**

---

**Round 2 Architecture & Design (For Spec documents):**

After Round 1 confirms requirements, Round 2 focuses on system design:

1. **Component Design:** Are system components well-defined with clear responsibilities?
2. **Data Models:** Do the data models support all user stories?
3. **API Contracts:** Are APIs complete with request/response schemas and error codes?
4. **System Boundaries:** Are integration points with external systems clear?

**Defer implementation details** (algorithms, caching strategies, etc.) to Round 3.

**Round 3 Implementation Details (For Spec documents):**

After architecture is validated, Round 3 focuses on implementation:

1. **Algorithms:** Are the proposed algorithms appropriate for the scale?
2. **Performance:** Are targets specific and measurable?
3. **Security:** Are threats identified with mitigations?
4. **Error Handling:** Are failure modes enumerated with recovery strategies?

**Round 4+ Refinement:**

Final rounds focus on polish:
- Edge cases and boundary conditions
- Consistency across sections
- Clarity of language
- Final verification against user stories

---

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

---

### Phase Transition: debate → gauntlet

When consensus is reached and user opts for gauntlet, sync both session files per the Phase Transition Protocol (SKILL.md):

1. **Detail file** (`sessions/<id>.json`): set `current_phase: "gauntlet"`, `current_step: "Consensus reached, running gauntlet"`, append journey entry
2. **Pointer file** (`session-state.json`): set `current_phase: "gauntlet"`, `current_step`, `next_action`, `updated_at`

If user declines gauntlet and proceeds directly to finalize, set `current_phase: "finalize"` instead.

