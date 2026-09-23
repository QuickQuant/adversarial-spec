> **FIRST ACTION upon entering this phase:** Restore `todowrite_snapshot` when
> present. Resolve the live pipeline version before creating a fresh checklist.
> Every `[GATE]` must complete before proceeding.

### v6 bounded-pipeline sessions

Read the card's pipeline version and returned `pipeline_lane_state` action with
explicit `board_id`. v6 debate is a leaf fan-out; `begin_debate_round` rejects
whole-spec session-card rounds with `V6_DEBATE_IS_LEAF_FANOUT`. Follow the returned
D0/leaf-plan/leaf-cycle action and the version-aware SKILL.md router. The classic
round recipe below applies only to pre-v6 session cards.

Use this phase's roadmap, context-readiness, test-sync, and guardrail obligations
for the artifacts under review. v6's D0 owns the Phase 4 skip-mode artifact;
retain it for the architecture handoff. Do not substitute a whole-spec round for
leaf qualification or the fan-in barrier.

### Dispatch Rule

Carded session → pipeline tools only. Uncarded work or an intentional, logged
override → `debate.py`; satisfy `enforce_pipeline_card_gate`. Uncarded runs and
intentional overrides require `--pipeline-card IntentionalOverride` plus
`--override-reason '<at least 50 characters>'`. Rejected pipeline calls do not
authorize an override. See [script-commands.md](../reference/script-commands.md)
for CLI invocation; preserve the same context, test-sync, and review obligations.
Every board-scoped call requires explicit `board_id` from `projects.yaml`.

See SKILL.md § [Decisions Log](../SKILL.md#decisions-log).

### Classic Round Checklist

```
TodoWrite([
  {content: "Verify roadmap and load user stories [GATE]", status: "in_progress", activeForm: "Verifying roadmap"},
  {content: "Load or generate initial document and confirm coverage", status: "pending", activeForm: "Preparing initial document"},
  {content: "Select opponent seats for altitude quorum", status: "pending", activeForm: "Selecting opponent seats"},
  {content: "Assemble context (technical/full)", status: "pending", activeForm: "Assembling context"},
  {content: "Round 1: Run debate + synthesize", status: "pending", activeForm: "Running Round 1 debate"},
  {content: "Round 1: Update tests-pseudo.md to match spec [GATE]", status: "pending", activeForm: "Updating test intent"},
  {content: "Round 1: Run SCOPE + TRACE + CANON + TCOV guardrails [GATE]", status: "pending", activeForm: "Running Round 1 guardrails"},
  {content: "Context Readiness Audit (technical/full) [GATE]", status: "pending", activeForm: "Auditing context readiness"},
  {content: "Record round; finalize only at convergence and altitude floor [GATE]", status: "pending", activeForm: "Closing debate round"},
])
```

Complete items as evidence lands. Skip technical/full-only items for product-depth
specs. For each additional round, add debate/synthesis, Test-Spec Sync, all five
guardrails, and round closure items before starting it. Restore completed gates;
do not force a second round when the altitude floor and recorded basis allow exit.

---

### Step 1: Verify Roadmap Exists (GATE)

Read only the active session's selected roadmap:
Resolve stored relative artifact paths against their documented workspace root
before reading them; the example below uses repository-relative paths.

```bash
SESSION_ID=$(jq -er '.active_session_id | select(type == "string" and length > 0)' .adversarial-spec/session-state.json) || exit 1
SESSION_DETAIL=".adversarial-spec/sessions/$SESSION_ID.json"
ROADMAP_PATH=$(jq -er '.roadmap_path | select(type == "string" and length > 0)' "$SESSION_DETAIL") || exit 1
if [ "$ROADMAP_PATH" = "inline" ]; then
  jq -e '{roadmap, user_stories, requirements_summary, architecture_impact}' "$SESSION_DETAIL"
else
  jq -e '{user_stories, milestones, slice_north_star, architecture_impact}' "$ROADMAP_PATH"
fi
```

Require the selected manifest (normally `roadmap/manifest.json`) or
active inline roadmap to contain approved, non-empty user stories and milestones.
Verify the Phase 2 user confirmation and referenced test artifact. Missing or
unreadable inputs block debate: return to [Phase 2](02-roadmap.md), never borrow
stories from another session.

**[GATE] TodoWrite: Complete "Verify roadmap and load user stories" only after this check.**

### Step 2: Load Roadmap User Stories (REQUIRED)

Use the Phase 2 stories selected above before generating a draft.

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

   **For technical/full depth with a declared setup prerequisite:** Include a "Getting Started" section addressing the roadmap's bootstrap story. Answer:
   - What does a new user need before they can use this? (prerequisites)
   - What's the step-by-step first-run experience? (setup workflow)
   - What happens if prerequisites aren't met? (error handling)
   - How long until a user can perform their first real task? (time to value)

   **If setup is required but its story is missing**, return to Phase 2 to add it. Otherwise retain the roadmap's explicit no-bootstrap rationale.

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

Before finalizing a technical spec, audit every architecture arrow. Name the
mechanism (poll, push, webhook, queue), verify what the source supports using
authoritative docs, and check the chosen mechanism against the latency requirement.
Do not assume polling is the only option.

```markdown
## Information Flows

| Flow | Source | Destination | Mechanism | Latency | Source Capabilities | Justification |
|------|--------|-------------|-----------|---------|---------------------|---------------|
| Fill notification | Exchange | Worker | WebSocket | <50ms | Verified stream and REST endpoints | Required latency rules out slow polling |
```

### Step 2.7: External API Interface Verification (For Technical/Full Depth Specs)

Do not guess external field names, types, or response shapes. Check in order:

1. Official SDK type definitions for the version in use; verify their API version.
2. Local API documentation, checking freshness/version.
3. Official documentation through the project's documentation tools.
4. Ask the user for an authoritative source if none is available.

Cite the file/document, version, and verification date alongside the interface.
Mark unresolved shapes `UNVERIFIED`, name the missing evidence, and stop treating
them as implementation-ready until verified. Model agreement is not API evidence.

### Step 3: Select Opponent Models

Choose seats with the user from [current-models.md](../reference/current-models.md)
and use labels accepted by `agents.validate_debate_model`. That reference owns
model, effort, transport, and reviewer-independence policy. Passing a link does not
change runner defaults; select seats explicitly.

Read `session_altitude` from the card with explicit `board_id` before dispatch.
For classic rounds, `ALTITUDE_DEBATE_QUORUM` freezes these minimums into round state;
see [altitude.md §6](../reference/altitude.md#6-rigor-that-scales--the-consumption-tables).

| session_altitude | min counting critics | min distinct families | min rounds |
|---|---|---|---|
| component | 1 | 1 | 1 |
| subsystem | 2 | 2 | 1 |
| system | 2 | 2 | 2 |

Undeclared/grandfathered sessions retain the pipeline's legacy 2-critic/2-family
quorum and one-round floor. Use registry families; same-family seats do not add
family diversity.

### Step 3.5: Assemble Context Files (REQUIRED for technical/full depth)

Before the first round, assemble substantive context for the spec's blast zone.
Use [context-addition-protocol.md](../reference/context-addition-protocol.md) for
selection, extraction, size budget, appendix format, and freshness checks. Persist
the selected paths in `extended_state.context_files`.

**Transport:** Pipeline rounds pass the actual context text (excerpts, test intent,
lookup resolutions, and directives) as `domain_context` to
`pipeline_begin_debate_round`; the pipeline writes it into the isolated critic
workspace. Uncarded/override CLI rounds attach files with `--context`. A list of
paths or navigation links alone does not deliver their contents.

Include `tests-pseudo.md` whenever present (and the authoritative TMR records if
compiled). Critics must review assertions, causality, UI/display contracts, and
stale assumptions as well as story coverage. Address corrections in Test-Spec Sync.
Include active, unprocessed visualizer feedback; after incorporation, mark each
included file `processed-in-round-<N>` so it is not attached again.

**MOCK falsification directive (REQUIRED in every debate round's prompt preamble).** When `tests-pseudo.md` is in context, append this sentence to the debate prompt so both debaters (and Claude) attack weak mock justifications:

> *"For any **critical-seam** test on a non-REAL `Data Strategy` (MOCK / MOCK-EXTERNAL / SYNTHETIC / STATIC / FRONTEND — the rule keys on real-ness, not the label, DR-8), challenge its justification. If you can name one plausible live reproduction path against dev infrastructure or small real money (e.g., fund a dev account, rapid-fire real orders, submit malformed inputs, cancel a nonexistent order), report it as a correction — the test should be promoted to REAL-DATA. A justified MOCK must cite a concrete `technical_constraint` (DD-3); scale / cost / time excuses ('too slow', 'rate-limited', '2^31 items') are inducible, not impossibility, and also promote."*

**Test adequacy directive (REQUIRED in every debate round's prompt preamble when tests are in context):**

> *"Attack the tests as well as the spec. Field existence, HTTP 200, non-null, and range checks are not adequate for semantic contracts. For every user-facing parameter, emitted metric, UI label/tooltip, state transition, and formula, ask whether the tests would fail if the implementation had the wrong causality or displayed the wrong meaning."*

### Step 4: Dispatch Critics via Pipeline Tools (Classic Rounds)

**CRITICAL: Always pass the COMPLETE spec document from disk. NEVER summarize, condense, or rewrite it from memory.** The spec file on disk is the source of truth. Opponent models must see the exact same document the user approved.

**Before EVERY debate round:**

0. **Lookup Sweep [GATE].** Maintain
   `.adversarial-spec/specs/<slug>/lookup-log.md`. Sweep OQ/ASSUMPTION entries and
   hedges (`TBD`, `unverified`, `assumed`) for questions answerable by source,
   official docs, config, or a short user clarification. Resolve lookup-answerable
   entries before dispatch and record `RESOLVED <date> via <method>: <answer>`.
   Keep only judgment or implementation-verification questions open, with reasons.
   Include this log in the context payload so critics see the evidence.

1. Write the current spec to `.adversarial-spec/specs/<slug>/spec-draft-vN.md`
2. Verify the file exists and has expected content: `wc -l .adversarial-spec/specs/<slug>/spec-draft-vN.md`
3. Read the spec content from disk — the file IS the source of truth, never memory

**4a. Begin the round:**
```
begin_result = pipeline_begin_debate_round(
    session_id=SESSION_ID,
    card_id=FIZZY_CARD_ID,
    round_number=N,
    models=SELECTED_REGISTRY_MODELS,
    board_id=BOARD_ID,
    orchestrator_agent=AGENT,
    domain_context=ASSEMBLED_CONTEXT_TEXT,
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
    model=MODEL,
    spec_path=SPEC_DRAFT_PATH,  # complete current draft under this worktree
    board_id=BOARD_ID
)
```
The tool launches the critic subprocess with full isolation (MCP disabled, workspace-only instruction file) and returns when the critic finishes.

**Ambiguous MCP timeout recovery (fire-and-poll):** If the wrapper times out while
the critic may still run, do not retry the launch. Inspect the returned
`results_dir` (or workspace path recorded in pipeline state), under
`<model-with-slashes-replaced-by-dashes>/`, for `parsed.json`, `raw.txt`, and
`stderr.txt`. Check at the established 90-second recovery cadence without
exponential backoff; keep the user informed while waiting.

A completed `parsed.json` supplies status, agreement, and findings count; preserve
`raw.txt` as review evidence. Recover the dispatch ID from pipeline state and
register the return. If no ID can be recovered, record the artifact path on the
card using explicit `board_id`, write a process-failure note, and surface the
blocker. Treat failure as terminal only after the critic timeout and absence of a
terminal artifact. Never fabricate a return or duplicate a still-running critic.

**4c. Register each model's return:**
After each dispatch returns:
```
pipeline_register_debate_agent_return(
    session_id=SESSION_ID,
    card_id=FIZZY_CARD_ID,
    round_instance_id=begin_result["round_instance_id"],
    dispatch_id=result["dispatch_id"],
    model=MODEL,
    status=result["status"],
    findings_count=result["findings_count"],
    agreed=result["agreed"],
    artifact_relpath=result["artifact_relpath"],
    board_id=BOARD_ID
)
```

**4d. Finish the round after synthesis and gates.** Complete Step 5, Test-Spec
Sync, and Checkpoint Guardrails, then run [Round Closure](#round-closure-classic-pipeline).
An actual skipped/failed critic stays recorded as such; it cannot supply missing
quorum evidence.

**Rejected calls:** Inspect the live card and returned blocker. Resume an existing
round with `active_round_policy="resume"` when appropriate; reconcile incomplete
returns/checklists through the owning tools. Do not invent sequence numbers,
claim skipped work completed, or use `pipeline_patch_state` to skip a fence.
Unrecoverable state requires a process-failure note and operator resolution.

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

2. **Confirm Getting Started Exists:** For technical/full depth when setup is a declared prerequisite:
   - A "Getting Started" or "Bootstrap" section should already exist (addressing US-0)
   - The bootstrap workflow from the roadmap should be documented
   - New users can understand how to set up the system
   - **If required but missing:** Return to Step 2.5 to add it; otherwise retain the no-bootstrap rationale

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

   Do NOT proceed to another round or phase handoff until the user confirms direction.

---

### Context Readiness Audit (GATE — technical/full depth)

Run after Round 1 and before Round 2, or before finalizing a one-round debate.
On resume, a missing inventory requires this audit before continuing. For v6,
complete it before architecture-focused leaf review. Phase 3 owns the inventory;
Phase 5 consumes and revalidates it before arming adversaries.

1. Identify the blast zone from the spec's files, modules, types, tables, functions,
   and external services.
2. Check the sources below and classify each as `AVAILABLE`, `PARTIAL`,
   `NOT_AVAILABLE`, or `NOT_APPLICABLE`.

   | Context source | Evidence to inspect |
   |----------------|---------------------|
   | Architecture | Manifest freshness, primer, relevant component docs |
   | Schemas/types | Definitions referenced by the blast zone |
   | Tests and coverage | Existing tests, coverage config/report, test intent |
   | Dependencies | `pyproject.toml` / `package.json` |
   | Recent changes | Git history and working-tree changes in the blast zone |
   | Build/test health | Latest applicable run evidence; gaps stated explicitly |
   | Operations | Monitoring/SLIs, error/retry handling, auth/authz patterns |
   | External APIs | Versioned SDK/docs and verified interface excerpts |
   | Prior art | Legacy/archive code, similar features, ADRs/design rationale |

3. Present available sources, actionable gaps, and design gaps to the user. Offer
   to obtain missing evidence; record any accepted omissions. Do not create raw
   task cards for context work: use the approved plan-backed path if needed.
4. Persist the agent-maintained `ContextInventoryV1` in
   `extended_state.context_inventory`. This is a manual guidance record; no
   runtime schema validator is implemented.

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
     "gaps_noted": ["missing evidence or design gaps"]
   }
   ```

Persist only available/partial sources with actionable path/task data. Summarize
unavailable, inapplicable, or non-actionable entries in `gaps_noted` when relevant.
This entry pruning never deletes the inventory at debate exit.

**Retain and revalidate:** Keep the inventory and selected context paths through
the architecture handoff and gauntlet. Before reuse, check HEAD, working-tree
changes, source existence, and blast-zone changes; refresh affected excerpts and
update timestamps/statuses. Unchanged HEAD alone does not prove fresh context.
Use [context-addition-protocol.md](../reference/context-addition-protocol.md) for
extraction and transport; update the payload before the next dispatch.

**[GATE] TodoWrite: Complete "Context Readiness Audit (technical/full)" only after
inventory persistence and gap review.**

---

**Round 2 Architecture & Design (For Spec documents):**

**PRE-CHECK (technical/full depth):** Verify the Context Readiness Audit was completed. If `extended_state.context_inventory` is missing from the session state, STOP and run the audit above before proceeding.

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

**Handling Early Agreement:** `[AGREE]` is a response marker, not proof of
convergence. If early agreement lacks evidence, ask the next round's critics to
name at least three reviewed sections, explain agreement, and identify remaining
issues. Add these instructions to the context payload using the selected dispatch
mode; do not bypass the pipeline for a separate press run.

**Incorporate critiques:**
1. List distinct issues, including your independent critique; accept valid gaps
   and explain rejected suggestions.
2. Ask the user about product decisions or conflicting priorities before revising.
3. Write the revised complete draft to disk as `spec-draft-v{N+1}.md` and verify it.
4. Run Test-Spec Sync and Checkpoint Guardrails below, including on an unchanged
   draft before claiming a clean round.
5. Record the round through Round Closure. The pipeline's recorded convergence
   basis plus altitude round floor decides whether to finalize or run another
   round. Changes needing independent review go into the next round.

### Test-Spec Sync (GATE — after each round incorporation)

> **This is a GATE, not advisory.** Tests that drift from the spec produce false confidence —
> downstream phases consume this test intent. Before compile, edit `tests-pseudo.md`;
> after compile, update authoritative `tmr-registry.json` records and regenerate the
> prose view per the [TMR contract](../reference/document-types.md#happy-path-spine-and-maturity-ladder).

After writing the current spec to disk and BEFORE running checkpoint guardrails:

**0. Morph gate-in (REQUIRED — [morph-reconciliation.md](../reference/morph-reconciliation.md)).** Before diffing tests,
scan this round's accepted critiques for a **morph verb** (`delete`/`relocate`/`externalize`/
`absorb`/`merge`/`split`/`reframe`) applied to a named capability. If any fired, a **user-story
morph** may have occurred: a US whose center of gravity moved, leaving its spine test pointing
at deleted behavior (grep-clean but semantically rotten). Run the morph-reconciliation procedure
(migration ledger → fate classification → artifact reconcile → lineage record → `orphaned_spine`
verify) for each affected capability before proceeding. Run the reference's `orphaned_spine` check as the standing backstop.

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
- **Data Strategy annotation** — every test must have a `Data Strategy:` line (REAL-DATA, SYNTHETIC, MOCK, etc.). Default to REAL-DATA. Only use SYNTHETIC when the condition genuinely cannot occur in real data.
- **BVA** — scan spec changes for new/modified numeric boundaries. Add at-boundary and just-outside tests marked `[BVA]`.
- **State transitions** — if this round changed state machine behavior (new states, new transitions), update the state transition table and add tests for new transitions.
- **Decision tables** — if this round changed combinatorial logic, update the decision table and add tests for new rows.
- **Semantic contracts and causality** — for every user-facing parameter, output field, chart/table label, tooltip, and derived metric touched by the change, classify it as `active_formula`, `active_gate`, `threshold`, `telemetry_only`, `legacy_display`, or `display_contract`. Add perturbation tests proving what changes and what must NOT change.

**5. Verify completeness:**
- Every user story still has ≥1 test in tests-pseudo.md
- Every numeric boundary has BVA tests
- Every state transition has a test (cross-reference table)
- Every decision table row has a test
- Every canonical formula, parameter-causality claim, payload meaning, and user-visible display claim has at least one falsifying test or an explicit deferral with rationale
- Field-presence, HTTP 200, non-null, and range tests are counted as smoke tests only; they do not satisfy semantic contract coverage by themselves
- Tests that verify behaviors NOT in any user story = scope drift (flag via SCOPE guardrail)
- No test asserts behavior that contradicts the current spec draft

**6. Persist updated test intent.** Write `tests-pseudo.md` at `session.tests_pseudo_path`; after compile, apply the TMR contract and regenerate this view.

**[GATE] TodoWrite: Mark "Round N: Update tests-pseudo.md to match spec" completed before proceeding to guardrails.**

---

### Checkpoint Guardrails (after each round incorporation)

After Test-Spec Sync, run checkpoint guardrails before the next debate round. These catch editorial regressions early — contradictions, scope drift, and orphaned requirements compound across rounds.

**Five guardrail adversaries** (defined in `adversaries.py` → `GUARDRAILS` dict):

| Guardrail | Prefix | What it checks |
|-----------|--------|----------------|
| `consistency_auditor` | CONS | Cross-section contradictions, duplicate numbering, arithmetic consistency |
| `scope_creep_detector` | SCOPE | New scope additions not in original requirements, including unlinked cross-project/authority work |
| `requirements_tracer` | TRACE | User stories/acceptance criteria that lost coverage |
| `canonical_type_auditor` | CANON | Canonical contract drift: named types/enums, formulas, parameter causality, payload meanings, UI/display claims, and active-vs-legacy classifications. |
| `test_coverage_auditor` | TCOV | Test adequacy: tests-pseudo/tests-spec would actually fail for contract, causality, UI, formula, state, BVA, and negative-path violations; rejects field-presence-only false confidence. |

**First-draft exemption:** CONS cannot run on the first draft (it compares sections against each other — only meaningful after revision introduces cross-section drift). **SCOPE, TRACE, CANON, and TCOV CAN run on the first draft** because they compare the spec/tests against external inputs (requirements, roadmap, codebase/contracts), which exist before the first draft. TCOV requires tests-pseudo.md or tests-spec.md; if no test artifact exists yet, emit a blocking setup warning rather than silently passing.

**Invocation contract — guardrail orchestration:**

1. Run the five guardrails as **five separate parallel subagents**: CONS, SCOPE, TRACE, CANON, and TCOV. Never collapse them into one combined prompt or one shared model call.
2. Each subagent receives a self-contained payload:
   - persona prompt from `adversaries.py`
   - identical orchestrator-passed content bundle (current spec, roadmap/user stories, tests-pseudo/tests-spec when present, canonical contract index, relevant architecture/code excerpts)
   - **SESSION BOUNDARY CONTEXT for SCOPE**: subject project/repository and allowed write roots; authoritative session/card; named external dependencies; linked sibling sessions/cards; and every newly proposed or performed out-of-boundary action since the prior round. A phrase such as "pipeline recovery" or "necessary infrastructure" is not an approval record. If this context is missing, SCOPE must return `SCOPE INPUT GAP` rather than a clean result.
   - this round's text diff
   - TMR semantic-delta with stable join keys (`tmr_uid`, `test_id`, `user_story`) even when the key text is outside the changed hunk
   - **ownership matrices, when present** (`specs/<slug>/ownership-baseline.md` written by mapcodebase, ≤40 rows; `specs/<slug>/ownership-live.md` amended each round): before dispatch, amend ownership-live.md with a provenance note for every entity (table, endpoint, store, config key) whose home this round's spec version introduces or moves, then compute the deterministic baseline↔live A/B diff and include it in the CONS payload. Two homes for one entity, or a home contradicting the baseline without a provenance note, is a CONS finding. See `docs/proposals/ownership-matrices-cons.md`. Mid-debate these stay warning severity (fix next round); the finalize pass runs `action="finalize"` where any unresolved CONS finding blocks (06-finalize.md).
3. Each subagent returns a structured result set: `{guardrail, findings[]}`. Every finding MUST carry a key to a `test_id`, `user_story`, `tmr_uid`, section id, or `ORCH` target. Persist the per-guardrail result sets and the aggregate for the round.
4. Transient transport failures (`429`, timeout, retryable CLI/API failure) are retried with bounded backoff before any orchestration error is synthesized. A dead or exhausted subagent yields a synthetic `ORCH` finding: `blocking` on gauntlet, `warning` on critique. Four passing guardrails plus one ORCH is not green for gauntlet.
5. Join keys are journaled only for findings that mutate a TMR/node field. Spec/contract-only findings are recorded in the round aggregate, but they do not create conflict-disposition entries unless they identify a concrete TMR/node field transition.

**Session file dependency:** SCOPE, TRACE, CANON, and TCOV all require external input beyond the spec. SCOPE requires both `requirements_summary` and SESSION BOUNDARY CONTEXT; if either is missing, do not call it clean — surface an input gap and stop the next-round transition until the operator supplies or explicitly waives it. If the roadmap manifest (TRACE/TCOV), canonical contract index (CANON/TCOV), or tests-pseudo/tests-spec (TCOV) is missing or empty, warn the user and skip only the affected guardrail rather than running it without the external input. CANON with an empty contract index degrades to repeated-inline-union and repeated-formula detection only; it cannot audit parameter causality or display-contract drift without owner excerpts.

**SCOPE authority-boundary addendum:** A current-project session may discover that a dependency or pipeline mechanism is defective. That makes the current project **blocked**; it does not authorize repair work in the dependency's repository. Before the next round, create or link the owning sibling session/card, record the dependency in this session, and let that owner perform the repair. SCOPE flags an unlinked external repair even if no spec paragraph mentions it and even if it was presented as a purely operational or architectural necessity.

**Depth limit (FM-2):** If CONS finds issues, fix them and re-run CONS. If the re-run finds NEW contradictions introduced by the fix, defer to the user after 2 attempts — do not loop indefinitely.

**Workflow after guardrails:** Persist the aggregate report, show its actionable
results to the user, and resolve each category:

1. Fix CONS findings before proceeding
2. Present SCOPE additions for user approval or removal
3. Restore TRACE-flagged coverage or explicitly descope with user approval
4. Apply CANON fixes (replace inline unions with named types; align formulas, parameter causality, payload meanings, UI/display claims, and active-vs-legacy classifications with canonical contracts)
5. Apply TCOV fixes before the next round: add or strengthen tests-pseudo/tests-spec so each accepted semantic claim has a falsifying oracle; classify field-presence, HTTP 200, non-null, and range-only tests as smoke coverage only
6. Only after guardrails pass (or user explicitly overrides): proceed to the next round

**[GATE] TodoWrite: Mark "Round N: Run CONS + SCOPE + TRACE + CANON + TCOV guardrails" (or "SCOPE + TRACE + CANON + TCOV" for Round 1) completed before proceeding to the next round.**

### Round Closure (Classic Pipeline)

After every critic return is registered and synthesis, test sync, and guardrails
have produced their artifacts, record the round:

```
round_result = pipeline_advance_debate_round(
    session_id=SESSION_ID,
    card_id=FIZZY_CARD_ID,
    agent=AGENT,
    round_number=N,
    models_used=SELECTED_REGISTRY_MODELS,
    findings_count=FINDINGS_COUNT,
    findings_summary=ROUND_SYNTHESIS,
    current_spec_draft_path=CURRENT_SPEC_DRAFT_PATH,
    guardrail_report_path=GUARDRAIL_REPORT_PATH,
    board_id=BOARD_ID,
)
```

Omit `convergence` so the pipeline derives it from registered outcomes. Inspect
`ok` and the recorded `convergence_basis`; completed counting critics, family
quorum, and absence of blocking returns determine convergence. An unavailable
reviewer is unavailable, never a fabricated agreement. A rejected call blocks
closure. Preserve returned archive paths for critic evidence.

When the recorded round converged, the altitude round floor is satisfied, and no
revision still needs review, close the debate without inventing another round:

```
pipeline_finalize_debate_round(
    session_id=SESSION_ID,
    card_id=FIZZY_CARD_ID,
    agent=AGENT,
    board_id=BOARD_ID,
)
```

Require success before handoff. If the basis or floor fails, run another round;
never patch a convergence flag. Pipeline tools own round state and routine card
comments.

See SKILL.md § [Fizzy Card Comment Convention](../SKILL.md#fizzy-card-comment-convention).
See SKILL.md § [Phase Transition Protocol](../SKILL.md#phase-transition-protocol) for Telegram/milestone notifications and human interrupt handling.
See SKILL.md § [Journey Log](../SKILL.md#journey-log).

### Target-Architecture / Decomposition Handoff

Hand off the reviewed spec path, roadmap, current test intent, guardrail report,
lookup log, and retained `extended_state.context_inventory` to
[Phase 4](04-target-architecture.md). Classic sessions enter target architecture;
v6 validates the Phase 4 artifact carried by D0 decomposition and follows the
router's fan-in handoff. Missing architecture artifacts block further progression,
even when the selected architecture mode is `skip`.

See SKILL.md § [Phase Transition Protocol](../SKILL.md#phase-transition-protocol).
