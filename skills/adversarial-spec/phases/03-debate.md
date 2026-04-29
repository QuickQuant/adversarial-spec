> **FIRST ACTION upon entering this phase:** Create this TodoWrite immediately.
> Do NOT read further until the TodoWrite is active.
> Every `[GATE]` item must be marked completed before proceeding past it.

```
TodoWrite([
  {content: "Verify roadmap exists [GATE]", status: "in_progress", activeForm: "Verifying roadmap exists"},
  {content: "Load roadmap user stories", status: "pending", activeForm: "Loading roadmap user stories"},
  {content: "Load or generate initial document", status: "pending", activeForm: "Loading initial document"},
  {content: "Select opponent models", status: "pending", activeForm: "Selecting opponent models"},
  {content: "Assemble context files (technical/full)", status: "pending", activeForm: "Assembling context files"},
  {content: "Round 1: Run debate + synthesize", status: "pending", activeForm: "Running Round 1 debate"},
  {content: "Round 1: Update tests-pseudo.md to match spec [GATE]", status: "pending", activeForm: "Updating tests-pseudo.md"},
  {content: "Round 1: Run SCOPE + TRACE guardrails [GATE]", status: "pending", activeForm: "Running Round 1 guardrails"},
  {content: "Context Readiness Audit (technical/full) [GATE]", status: "pending", activeForm: "Running context readiness audit"},
  {content: "Round 2: Run debate + synthesize", status: "pending", activeForm: "Running Round 2 debate"},
  {content: "Round 2: Update tests-pseudo.md to match spec [GATE]", status: "pending", activeForm: "Updating tests-pseudo.md"},
  {content: "Round 2: Run CONS + SCOPE + TRACE guardrails [GATE]", status: "pending", activeForm: "Running Round 2 guardrails"},
])
```

Mark each step `completed` as you finish it. Mark the current step `in_progress`. Skip steps marked "technical/full" for product-depth specs.

**Dynamic rounds:** For each round beyond Round 2, add three TodoWrite items before starting the round:
- `{content: "Round N: Run debate + synthesize", status: "pending", activeForm: "Running Round N debate"}`
- `{content: "Round N: Update tests-pseudo.md to match spec [GATE]", status: "pending", activeForm: "Updating tests-pseudo.md"}`
- `{content: "Round N: Run CONS + SCOPE + TRACE guardrails [GATE]", status: "pending", activeForm: "Running Round N guardrails"}`

---

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

**[GATE] TodoWrite: Mark "Verify roadmap exists" completed before proceeding to Step 2.**

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
- `gpt-5.4` - Frontier reasoning

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
- `codex/gpt-5.4` - OpenAI Codex with extended reasoning

**If Gemini CLI is installed, include:**
- `gemini-cli/gemini-3.1-pro-preview` - Google Gemini 3 Pro
- `gemini-cli/gemini-3-flash-preview` - Google Gemini 3 Flash

Use AskUserQuestion like this:
```
question: "Which models should review this spec?"
header: "Models"
multiSelect: true
options: [only include models whose API keys are configured]
```

More models = more perspectives = stricter convergence.

### Step 3.5: Assemble Context Files (REQUIRED for technical/full depth)

**Before the first debate round**, assemble context files so opponent models can critique against the actual codebase, not hallucinated patterns.

Check each context source: architecture docs, source issues, type definitions, existing routes/endpoints. Validate all context files contain substantive content, then build `--context` flags and store in session.

**Build the --context flags:**

```bash
CONTEXT_FLAGS=""

# 1. Architecture docs (almost always relevant)
# WARNING: Do NOT pass INDEX.md as --context. INDEX.md is a navigation page
# containing links that opponent models cannot follow. It provides zero
# substantive content. Pass the files it REFERENCES instead:
if [ -d ".architecture" ]; then
  # Primer is the default small-context architecture payload
  [ -f ".architecture/primer.md" ] && CONTEXT_FLAGS="$CONTEXT_FLAGS --context .architecture/primer.md"

  # Include component docs relevant to the spec's blast zone (2-4 files)
  # Match spec file paths/module names against .architecture/structured/components/
  # e.g., --context .architecture/structured/components/data-service.md

  # Add overview.md only when the round needs the full system narrative
  # e.g. later architecture/design rounds or broad multi-component specs:
  # [ -f ".architecture/overview.md" ] && CONTEXT_FLAGS="$CONTEXT_FLAGS --context .architecture/overview.md"

  # For broad or cross-component specs, flows.md covers data paths across the whole system
  # [ -f ".architecture/structured/flows.md" ] && CONTEXT_FLAGS="$CONTEXT_FLAGS --context .architecture/structured/flows.md"
fi

# 2. Source issues/requirements that motivated the spec
# Check session extended_state for issues_file, or scan issues dir
for f in .adversarial-spec/issues/*.md; do
  [ -f "$f" ] && CONTEXT_FLAGS="$CONTEXT_FLAGS --context $f"
done

# 3. Key type definitions (limit to 3-5 most relevant files)
# e.g., --context src/types.ts --context src/api_models.py
```

**Context File Validation (REQUIRED before passing --context):**

Before passing any file via `--context`, verify it contains substantive content:

1. **Does the file contain actual architecture/code information?** Navigation pages, tables of contents, and link-only documents are useless to opponent models — they can't follow links.
2. **Can the recipient model use the content without following links?** If the file is mostly `[link text](url)` references, pass the linked files instead.
3. **Is the file relevant to the spec being critiqued?** Don't pass every architecture doc — select files that cover the spec's blast zone.

**Do NOT pass as --context:**
- `INDEX.md` or any file that's primarily navigation/links
- Files over 500 lines without trimming to relevant sections
- Files unrelated to the spec's scope

**4. Test pseudocode (when available — ALWAYS include if it exists)**
```bash
# Include tests-pseudo.md so opponents can critique test coverage.
# This is not optional — opponents must see tests to catch spec/test drift.
if [ -n "$TESTS_PSEUDO_PATH" ] && [ -f ".adversarial-spec/$TESTS_PSEUDO_PATH" ]; then
  CONTEXT_FLAGS="$CONTEXT_FLAGS --context .adversarial-spec/$TESTS_PSEUDO_PATH"
fi
```
When tests-pseudo.md is included as context, opponents will naturally critique misaligned assertions.
If an opponent flags a test/spec mismatch, that is a valid critique — address it in the Test-Spec Sync gate.

**MOCK falsification directive (REQUIRED in every debate round's prompt preamble).** When `tests-pseudo.md` is in context, append this sentence to the debate prompt so both debaters (and Claude) attack weak mock justifications:

> *"For any test with `Strategy: MOCK*`, challenge the `why_impossible_to_reproduce_live` claim. If you can name one plausible live reproduction path against dev infrastructure or small real money (e.g., fund a dev account, rapid-fire real orders, submit malformed inputs, cancel a nonexistent order), report it as a correction — the test should be promoted to REAL-DATA."*

This adds zero new adversary launches. Both debaters already see `tests-pseudo.md`; this directive just tells them what to attack in it.

**Store assembled context list in session state** (`extended_state.context_files`) for reuse across rounds.

**Do NOT run `debate.py critique` without --context for technical/full specs that reference an existing codebase.** Product-depth specs about new greenfield projects may not need context.

### Step 4: Dispatch Critics via Pipeline Tools

**CRITICAL: Use pipeline tools to run the debate. Do NOT call debate.py directly.**

The pipeline tools handle workspace creation, MCP isolation, subprocess launching, and per-model tracking. This ensures every debate round is tracked on the Fizzy card.

**CRITICAL: Always pass the COMPLETE spec document from disk. NEVER summarize, condense, or rewrite it from memory.** The spec file on disk is the source of truth. Opponent models must see the exact same document the user approved.

**Before EVERY debate round:**

1. Write the current spec to `.adversarial-spec/specs/<slug>/spec-draft-vN.md`
2. Verify the file exists and has expected content: `wc -l .adversarial-spec/specs/<slug>/spec-draft-vN.md`
3. Read the spec content from disk — the file IS the source of truth, never memory

**4a. Begin the round:**
```
pipeline_begin_debate_round(
    session_id=SESSION_ID,
    card_id=FIZZY_CARD_ID,
    round_number=N,
    models=["codex/gpt-5.4", "gemini-cli/gemini-3.1-pro-preview"],
    board_id=BOARD_ID,
    domain_context="Optional project-specific context"
)
```
This creates the isolated workspace, writes critic AGENTS.md, creates per-model checklist items on the card.

**4b. Dispatch each model individually:**
For each model, call:
```
result = pipeline_dispatch_single_agent_debate(
    session_id=SESSION_ID,
    card_id=FIZZY_CARD_ID,
    round_number=N,
    round_instance_id=begin_result["round_instance_id"],
    model="codex/gpt-5.4",
    spec_content=spec_text,  # full spec read from disk
    board_id=BOARD_ID
)
```
The tool launches the critic subprocess with full isolation (MCP disabled, workspace-only instruction file) and returns when the critic finishes.

**4c. Register each model's return:**
After each dispatch returns:
```
pipeline_register_debate_agent_return(
    session_id=SESSION_ID,
    card_id=FIZZY_CARD_ID,
    round_instance_id=begin_result["round_instance_id"],
    dispatch_id=result["dispatch_id"],
    model="codex/gpt-5.4",
    status=result["status"],
    findings_count=result["findings_count"],
    agreed=result["agreed"],
    artifact_relpath=result["artifact_relpath"],
    board_id=BOARD_ID
)
```

**4d. The conductor can skip models or stop early.**
If a model is hanging or you have enough critiques, register remaining models as `status="skipped"` and proceed.

**No fallback.** If `pipeline_begin_debate_round` rejects the round (sequence mismatch, checklist missing, active round conflict), STOP. Do not dispatch standalone `debate.py critique` — there is no "pipeline unavailable" condition in a Fizzy-enabled project; either the card is in a debate-eligible lane or it isn't, and standalone bypass is exactly how tests-pseudo.md drifted across v2→v7 without a single staleness warning. Options when the pipeline rejects:

1. **Sequence mismatch on a mid-session card** — prior rounds ran before pipeline adoption. Treat the current spec version as pipeline-R1 (fresh pipeline-tracked start on the consolidated spec); prior rounds live on disk as historical artifacts. Dispatch from R1 forward via pipeline tools only.
2. **Active round conflict** — a prior round on this card never advanced. Register the missing model returns with `status="skipped"` and advance, then begin the next round.
3. **Checklist missing** — the `pipeline_begin_debate_round` call failed partway. Retry with `active_round_policy="reuse"` or `"replace"`.

If none of those resolve it, write a process-failure note (≥200 bytes, describe what broke, which gate was circumvented, what permanent fix is planned) and use `pipeline_patch_state` with `process_failure_path` to move forward. Do not fall back to `debate.py` with a Fizzy card present — the script now enforces `--pipeline-card` and will exit 2.

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

**Use TodoWrite** to track each validation item — mark completed or flag blocked:

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

**Context Readiness Audit (GATE — between Round 1 and Round 2, REQUIRED for technical/full depth):**

> **STOP.** Do NOT proceed to Round 2 without completing this audit.
> This is a GATE, not advisory. The audit produces the `ContextInventoryV1` that:
> - Builds the `--context` flags for Round 2+ debate invocations
> - Feeds the Arm Adversaries step before the gauntlet (see 04-gauntlet.md)
> - Prevents the failure pattern where models critique architecture without seeing the actual codebase
>
> **If this audit was skipped** (e.g., resumed session), run it NOW before proceeding.

After Round 1 validates requirements and before Round 2 debates architecture, audit what codebase context is available to inform the remaining debate and the eventual gauntlet.

**Why here:** Round 1 is about user value (no codebase context needed). Round 2 is about architecture (codebase context critical). Gaps discovered now have time to be addressed — tasks can complete while debate proceeds.

**Use TodoWrite** to track each context source check from the table below — mark each as completed with its status (AVAILABLE/PARTIAL/NOT_AVAILABLE/NOT_APPLICABLE).

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
   | Test pseudocode | Check `tests_pseudo_path` in session, verify file exists | PEDA, COMP, BURN |

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
     "schema_version": "1.1",
     "audit_timestamp": "ISO-8601",
     "git_hash": "short hash",
     "blast_zone": ["file1.py", "file2.py"],
     "sources": {
       "source_id": {
         "status": "available|partial",
         "path": "string or null",
         "summary": "one-line description",
         "est_tokens": 1200,
         "task_id": null
       }
     },
     "total_available_tokens": 8500,
     "gaps_noted": ["description of design gaps for later rounds"]
   }
   ```

   **Persistence rule (v1.1):** Only persist sources where `status ∈ {available, partial}` AND they carry actionable path/task data. Drop `not_available`, `not_applicable`, and `actionable:false` entries — they're audit-only noise that bloats every resume. Summarize them in `gaps_noted` if they need to survive.

   **Debate-exit prune:** On phase transition `debate → {gauntlet, finalize}`, delete `extended_state.context_inventory` from the session detail file. It's a debate-round working artifact — adversaries in gauntlet re-derive from the spec. Keep `gaps_noted` if it was promoted into the spec, else discard.

   This inventory is reused by:
   - **Context-addition-protocol** — debate round appendices draw from it instead of re-extracting
   - **Arm Adversaries** — gauntlet briefings are assembled from it (see 04-gauntlet.md)

   **Staleness rule:** If `git rev-parse --short HEAD` differs from `git_hash` in inventory, re-extract only the sources whose files were modified.

**After the audit, update --context flags for Round 2+:**

Build expanded context from the inventory's AVAILABLE sources:
```bash
CONTEXT_FLAGS=""
for source in inventory.sources where status == "available" and path != null:
  CONTEXT_FLAGS="$CONTEXT_FLAGS --context $source.path"
```

Update `extended_state.context_files` in session state with the new list. Use these flags for ALL subsequent `debate.py critique` invocations.

**[GATE] TodoWrite: Mark "Context Readiness Audit (technical/full)" completed before proceeding to Round 2.**

---

**Round 2 Architecture & Design (For Spec documents):**

**PRE-CHECK:** Verify the Context Readiness Audit was completed. If `extended_state.context_inventory` is missing from the session state, STOP and run the audit above before proceeding. Round 2 without codebase context produces hallucinated critiques.

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
cat .adversarial-spec/specs/<slug>/spec-draft-vN.md | \
  python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --models MODEL_NAME --doc-type TYPE --press
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
7. **Write the revised spec to disk** as `spec-draft-v{N+1}.md` (where N is current round):
   ```bash
   # Write revised spec to disk BEFORE next round
   # This is the source of truth for the next debate.py invocation
   ```
   Verify the file was written: `wc -l .adversarial-spec/specs/<slug>/spec-draft-v{N+1}.md`
8. **Update tests-pseudo.md to match the revised spec [GATE]** (see Test-Spec Sync section below)
9. **Run checkpoint guardrails** (see Checkpoint Guardrails section below)
10. Go back to Step 4, piping the NEW file from disk: `cat spec-draft-v{N+1}.md | debate.py ...`

**Handling conflicting critiques:**
- If models suggest contradictory changes, evaluate each on merit
- If the choice is a product decision (not purely technical), ask the user which approach they prefer
- Choose the approach that best serves the document's audience
- Note the tradeoff in your response

---

### Test-Spec Sync (GATE — after each round incorporation)

> **This is a GATE, not advisory.** Tests that drift from the spec produce false confidence —
> the gauntlet and implementation phases trust tests-pseudo.md as ground truth for what the
> spec actually requires. Stale tests mean stale implementation targets.

After writing the revised spec to disk (Step 5 item 7) and BEFORE running checkpoint guardrails:

**1. Diff the spec changes against tests-pseudo.md:**
- For each spec section that changed in this round, check whether the corresponding test cases still assert the correct behavior
- Pay special attention to: field names/schemas, formulas, API contracts, edge case rules, error codes

**2. Update tests-pseudo.md for EVERY spec change that affects observable behavior:**
- **Changed formula** → update the assertion values (e.g., `pnl_variance` → `pnl_stddev`)
- **Changed API contract** → update request/response fields in test setup/assertions
- **New edge case specified** → add a test case
- **Removed behavior** → remove or update the test case
- **Changed semantics** → update the `given/when/then` to match

**3. Add test cases for new behaviors introduced by this round's critiques:**
- Each accepted critique that changes spec behavior should have ≥1 test covering the fixed behavior
- If a critique says "division by zero when X" and the spec now handles it, there must be a test: "given X, when computed, then no error and result is Y"

**4. Apply the Test Design Methodology (02-roadmap.md §9) to all new/changed tests:**
- **Data strategy annotation** — every test must have a `Strategy:` line (REAL-DATA, SYNTHETIC, MOCK, etc.). Default to REAL-DATA. Only use SYNTHETIC when the condition genuinely cannot occur in real data.
- **BVA** — scan spec changes for new/modified numeric boundaries. Add at-boundary and just-outside tests marked `[BVA]`.
- **State transitions** — if this round changed state machine behavior (new states, new transitions), update the state transition table and add tests for new transitions.
- **Decision tables** — if this round changed combinatorial logic, update the decision table and add tests for new rows.

**5. Verify completeness:**
- Every user story still has ≥1 test in tests-pseudo.md
- Every numeric boundary has BVA tests
- Every state transition has a test (cross-reference table)
- Every decision table row has a test
- Tests that verify behaviors NOT in any user story = scope drift (flag via SCOPE guardrail)
- No test asserts behavior that contradicts the current spec draft

**6. Write updated tests-pseudo.md to disk.** The file path is in `session.tests_pseudo_path`.

**[GATE] TodoWrite: Mark "Round N: Update tests-pseudo.md to match spec" completed before proceeding to guardrails.**

---

### Checkpoint Guardrails (after each round incorporation)

After incorporating critiques into a new spec version (Step 5 item 8), run checkpoint guardrails before the next debate round. These catch editorial regressions early — contradictions, scope drift, and orphaned requirements compound across rounds.

**Four guardrail adversaries** (defined in `adversaries.py` → `GUARDRAILS` dict):

| Guardrail | Prefix | What it checks |
|-----------|--------|----------------|
| `consistency_auditor` | CONS | Cross-section contradictions, duplicate numbering, arithmetic consistency |
| `scope_creep_detector` | SCOPE | New scope additions not in original requirements |
| `requirements_tracer` | TRACE | User stories/acceptance criteria that lost coverage |
| `canonical_type_auditor` | CANON | Spec inlines a domain enum as a literal union (`"kalshi"\|"polymarket"`, `"yes"\|"no"`, etc.) when a canonical named type already exists in the codebase — OR repeats the same literal union across multiple spec sections without hoisting. Catches spec/code type drift. |

**First-draft exemption:** CONS cannot run on the first draft (it compares sections against each other — only meaningful after revision introduces cross-section drift). **SCOPE, TRACE, and CANON CAN run on the first draft** because they compare the spec against external inputs (requirements, roadmap, codebase), which exist before the first draft.

**Invocation contract — how Claude assembles guardrail inputs:**

1. Read the guardrail prompt from `adversaries.py` (CONS, SCOPE, TRACE, CANON)
2. Assemble the input payload:
   - **CONS:** prompt + current spec text
   - **SCOPE:** prompt + original requirements (from session file `requirements_summary`) + current spec text
   - **TRACE:** prompt + roadmap manifest (user stories + acceptance criteria) + current spec text
   - **CANON:** prompt + current spec text + **codebase type index** (a short catalog of named domain enums already defined in the project — generate by grepping `src/shared/` + `src/convex/schema.ts` + the architecture primer for `type X = "a"|"b"` / Zod enum schemas / `v.union(v.literal(...))` patterns, or by reading `.architecture/manifest.json` if it enumerates canonical types)
3. Send the assembled input to a model via `debate.py critique --model <model> --system-prompt <guardrail-prompt>` or evaluate inline if the spec fits in Claude's own context

**Session file dependency:** SCOPE, TRACE, and CANON all require external input beyond the spec. If `requirements_summary` (SCOPE), the roadmap manifest (TRACE), or the codebase type index (CANON) is missing or empty, warn the user and skip that guardrail rather than running it without the external input. CANON with an empty codebase index degrades to "repeated-inline-union" detection only (still useful — catches drift WITHIN the spec even if no code type exists yet).

**Depth limit (FM-2):** If CONS finds issues, fix them and re-run CONS. If the re-run finds NEW contradictions introduced by the fix, defer to the user after 2 attempts — do not loop indefinitely.

**Workflow after guardrails:**

```
Guardrail Results (post-Round N incorporation)
═══════════════════════════════════════
CONS (consistency_auditor): 2 findings
  1. §3.2 says "max 5 retries" but §5.1 says "max 3 retries"
  2. §7.3 and §7.4 both numbered as §7.3

SCOPE (scope_creep_detector): 1 finding
  1. §4.2 adds "webhook notification system" — not in original
     requirements. → SCOPE ADDITION (needs approval)

TRACE (requirements_tracer): 0 findings

CANON (canonical_type_auditor): 1 finding
  1. §5.1 inlines `exchange: "kalshi"|"polymarket"` — canonical
     type `ExchangeCode` exists in src/shared/balances-contract.ts.
     Replace with `ExchangeCode` reference.

[Fix CONS findings] [Approve/remove SCOPE additions] [Replace inline unions with canonical types] [Proceed to next round]
```

1. Fix CONS findings before proceeding
2. Present SCOPE additions for user approval or removal
3. Restore TRACE-flagged coverage or explicitly descope with user approval
4. Apply CANON fixes (replace inline unions with named types; define a spec-level "Canonical Types" section if no code type exists yet and the union is repeated)
5. Only after guardrails pass (or user explicitly overrides): proceed to the next round

**[GATE] TodoWrite: Mark "Round N: Run CONS + SCOPE + TRACE + CANON guardrails" (or "SCOPE + TRACE + CANON" for Round 1) completed before proceeding to the next round.**

### Fizzy Sync (after each round — REQUIRED)

**When using pipeline tools (Step 4):** Per-round sync is handled automatically. `pipeline_begin_debate_round`, `pipeline_register_debate_agent_return`, and `pipeline_advance_debate_round` update the Fizzy card with round state, per-model checklist items, and comments. No manual sync needed.

**Fallback (debate.py without pipeline tools):** If pipeline tools were unavailable and you used standalone `debate.py`, manually sync the Fizzy pipeline card. Read `fizzy_card_id` from the session detail file (`sessions/<id>.json`).

**If `fizzy_card_id` exists:**
1. Use a **haiku subagent** (to keep MCP payload out of main context) to:
   - `pipeline_patch_state(card_id, session_id, {"debate_round": N, "last_agent": "claude-opus-4-6"})` where N is the round just completed
   - `add_comment(card_id, "Round N complete: <1-2 sentence synthesis summary>. Spec version: vN.")`
2. Board is pinned at Fizzy server startup. The `board_id` parameter is optional and validated.

**If `fizzy_card_id` is missing:** Log a warning but do not block. The card may not have been created (legacy session) or the session predates this sync requirement.

**Why this matters:** Without per-round sync, the Fizzy card becomes stale immediately after creation. The board is the only external visibility into session progress — other agents, the conductor, and the user all depend on it. (See process failure: "Trello Board Ignored During Entire Spec Session", 2026-03-26.)

### Telegram Notification (after each round — REQUIRED)

After Fizzy sync, send a Telegram summary and pause for human interruption. See SKILL.md "Major Milestone Notifications" for full protocol.

**After debate round synthesis + guardrails:**
```bash
~/.claude/bin/telegram-send <project> "R<N> complete: <count> findings (<critical> critical, <major> major, <minor> minor) applied. Guardrails: SCOPE <pass/fail>, TRACE <pass/fail>, CONS <pass/fail>."
sleep 120  # 2 min pause for human interruption
```

**After convergence declared:**
```bash
~/.claude/bin/telegram-send <project> "Convergence after <N> rounds. <severity trend summary>. Proceeding to finalize."
sleep 120
```

**Rules:**
- Check telegram config first (`has_telegram_config` or `telegram-registry-lookup`). Skip if no config.
- The 120s pause is mandatory — gives human time to read and Ctrl+C to redirect.
- If `telegram-send` fails, log to stderr and continue.
- This is the human's primary mobile channel for staying oriented during long autonomous runs.

---

### Phase Transition: debate → gauntlet

When consensus is reached and user opts for gauntlet, sync both session files per the Phase Transition Protocol (SKILL.md):

1. **Detail file** (`sessions/<id>.json`): set `current_phase: "gauntlet"`, `current_step: "Consensus reached, running gauntlet"`, append entry to journey log (`sessions/<id>.journey.log`), and **delete `extended_state.context_inventory`** (debate-round working artifact; gauntlet re-derives from spec)
2. **Pointer file** (`session-state.json`): set `current_phase: "gauntlet"`, `current_step`, `next_action`, `updated_at`

If user declines gauntlet and proceeds directly to finalize, set `current_phase: "finalize"` instead.
