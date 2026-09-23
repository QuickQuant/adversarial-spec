> **FIRST ACTION upon entering this phase:** Restore `todowrite_snapshot` when
> present; otherwise create this TodoWrite. Complete every `[GATE]` before proceeding.

```
TodoWrite([
  {content: "Load approved RequirementsSummary and choose roadmap_mode", status: "in_progress", activeForm: "Choosing roadmap mode"},
  {content: "Draft roadmap with user stories and milestones", status: "pending", activeForm: "Drafting roadmap"},
  {content: "Validate Slice North Star milestone [GATE]", status: "pending", activeForm: "Validating Slice North Star milestone"},
  {content: "Generate test pseudocode for user stories", status: "pending", activeForm: "Generating test pseudocode"},
  {content: "Architecture-impact assessment (component map, middleware, new vars) [GATE]", status: "pending", activeForm: "Assessing architecture impact"},
  {content: "Goal alignment check (human guardrail) [GATE]", status: "pending", activeForm: "Checking goal alignment"},
  {content: "User confirms roadmap [GATE]", status: "pending", activeForm: "Awaiting user roadmap confirmation"},
  {content: "Persist roadmap artifacts and paths in active session", status: "pending", activeForm: "Persisting roadmap artifacts"},
  {content: "Verify artifacts exist on disk [GATE]", status: "pending", activeForm: "Verifying roadmap artifacts on disk"},
])
```

Mark items completed as evidence lands. Roadmap review runs through Phase 3.

### Approved Pre-Plan Artifacts

Phase 1 owns treatment-origin detection and requirements confirmation. When its
approved handoff includes `pre_plan_path`, reuse the RequirementsSummary, Proposed
Roadmap, and `tests_pseudo_path` artifacts that exist and match the accepted Slice
North Star. Complete only satisfied checklist items; run all Phase 2 gates below.
Missing or outdated artifacts require normal authoring.

### Test Pseudocode Generation (All Sessions)

**After Step 3 (Draft Roadmap) completes — for ALL sessions, not just treatment-originated:**

Generate `tests-pseudo.md` alongside the roadmap:
- For each user story in the roadmap, write ≥1 happy-path and ≥1 error-case pseudocode test
- Use `given/when/then/assert` structure
- Reference schema fields from `.architecture/` component docs when available
- Include `Schema refs:` line linking to actual data model fields when the test touches data boundaries
- Apply the **Test Design Methodology** (see below) from initial generation
- Write to `.adversarial-spec/specs/<slug>/tests-pseudo.md`
- Set `tests_pseudo_path` in session detail file

**`tests-pseudo.md` is the roadmap authoring source until TMR compile;
`tmr-registry.json` is authoritative afterward.** The manifest links to the test
artifact without duplicating its content. After compile, update records through
the TMR contract and regenerate the prose view.

#### Happy-Path Spine Authoring Model

Every roadmap user story MUST have exactly one happy-path spine designation.
This is the primary-success test for the user story, not every test that touches
the story. Author it as the `TC-X.0` spine where possible and give it named
`spine_steps` such as `S1`, `S2`, and `S3`.

Authoring rules:
- Exactly one active `spine: true` record per roadmap user story is allowed.
  Authoring lint consumes `SpineCoverageChecker` with phase `authoring` to reject
  zero-spine and duplicate-spine cases.
- One spine designation can have many concrete tests. Secondary, branch, and
  failure tests use `spine_of: <spine test_id>` to point at the spine they
  elaborate.
- Every failure or branch test that uses `spine_of` MUST cite a named
  `spine_step_ref`. A failure test with no `spine_step_ref` is rejected at
  authoring because reviewers cannot tell which happy-path obligation it
  falsifies.
- `also_covers` never creates a spine designation. Only the scalar `user_story`
  field on an active `spine: true` record counts for the one-spine-per-US rule.

Maturity ladder:
- `nl -> acceptance -> concrete` is the only promotion path.
- `nl` records are natural-language intent. They can be promoted only when they
  name at least one accessor (`>=1 named accessor`); empty `accessors` means
  `BLOCK`, not automatic promotion.
- acceptance has executable meaning without the facade: it states observable
  inputs, actions, outputs, and failure conditions that can be checked without
  pretending a UI/API facade already exists.
- `concrete` records are bound to actual commands, artifacts, or code-level
  verification evidence.

**Phase 4 Invariant Tests — Upsert Protocol (CRITICAL):**

Phase 4 (target-architecture) injects invariant-derived test cases into `tests-pseudo.md` via a marker-delimited upsert block:

```
<!-- P4_INVARIANT_TESTS_START -->
... invariant test cases, regenerated each Phase 4 run ...
<!-- P4_INVARIANT_TESTS_END -->
```

**Rules:**
- When Phase 4 runs (or reruns), the entire block between `<!-- P4_INVARIANT_TESTS_START -->` and `<!-- P4_INVARIANT_TESTS_END -->` is **replaced atomically**, not appended. Reruns MUST NOT produce duplicate or stacking invariant test entries.
- Content outside the marker block (the user-story tests authored in this phase) is **never touched** by Phase 4.
- If the markers are missing, Phase 4 appends a new block at the end of the file — but on the *next* run it will use the marker boundaries for replacement.
- Roadmap authors SHOULD leave the markers in place once they appear; deleting them forces Phase 4 to re-append.
- The **normative source** for the marker protocol and upsert semantics is [`04-target-architecture.md` §8.3](./04-target-architecture.md). Do not redefine the contract here.

---

### Roadmap Alignment (Spec Only, REQUIRED)

Define user stories and testable milestones before technical debate.

#### 1. Load RequirementsSummary

Use the Phase 1 user-approved summary. Resolve omissions with the user; preserve
the accepted goals, boundaries, and Slice North Star:

```json
{
  "user_types": ["developer", "admin", "end-user"],
  "feature_groups": ["authentication", "data export", "reporting"],
  "external_integrations": ["Kalshi API", "Polymarket API"],
  "unknowns": ["rate limit behavior under load"],
  "bootstrap_steps": ["Install CLI", "Configure API keys", "Run first query"],
  "slice_north_star": {
    "kind": "ui-target | process-output | end-to-end-repair",
    "actor_or_trigger": "who or what starts the slice",
    "outcome": "one observable worthwhile result",
    "thin_path": "entry -> decisive action/process -> useful end state",
    "proof": "demonstration, observation, or measurement",
    "not_this_slice": ["deliberately deferred adjacent work"]
  }
}
```

**Validation:**
- `user_types` must have at least 1 entry
- `feature_groups` must have at least 1 entry
- For technical/full depth, `bootstrap_steps` must be non-empty only when setup is a
  declared prerequisite. Otherwise set `bootstrap_steps: []` and say in the roadmap
  why no Getting Started milestone is required.

- `slice_north_star` must contain all six fields and exactly one outcome.
- `not_this_slice` must not be empty for a retained thin slice or repair.

#### 2. Choose Roadmap Mode

Persist one agent-recorded `roadmap_mode` in the active detail file. Choose by the
open questions that need review; this decision does not set altitude or bypass
Phase 3's critic/round floors.

| `roadmap_mode` | Choose when | Artifacts and review |
|----------------|-------------|----------------------|
| `inline` | No roadmap questions need a separate review pass | Inline roadmap and `user_stories` in active detail |
| `reviewed` | Bounded roadmap questions need a review round | `roadmap/manifest.json` plus readable view; include questions in Phase 3 |
| `iterative` | Discovery needs repeated review and user clarification | Same disk artifacts; refine through Phase 3 rounds and reconfirm changed scope |

Record the mode, rationale, and open questions with the roadmap. The user may
change the mode at confirmation; it is a planning choice, not an automated score.

#### 3. Draft Roadmap

Generate roadmap with user stories and milestones. The roadmap MUST include the
Goals, Non-Goals, and confirmed Slice North Star from RequirementsSummary so that
subsequent reviewers can judge both broad alignment and the first useful outcome.

```markdown
## Roadmap: [Feature Name]

### Goals
- [Goal 1 from requirements interview]
- [Goal 2 ...]

### Non-Goals
- [Non-goal 1 from requirements interview]
- [Non-goal 2 ...]

### Slice North Star
- **Kind:** <ui-target | process-output | end-to-end-repair>
- **Actor or trigger:** <…>
- **Outcome:** <one observable result>
- **Thin path:** <entry → decisive action/process → useful end state>
- **Proof:** <…>
- **Not this slice:** <…>

### Milestone 1: [First Useful Outcome]
**North Star Milestone:** yes
**User Stories:**
- US-1: As a [persona], I want [action] so that [benefit]
- US-2: ...

**Success Criteria (Natural Language):**
- [ ] The Slice North Star outcome occurs through the declared thin path
- [ ] The declared proof is observable
- [ ] Error case [Z] is handled

**Test Cases (expand during implementation):**
- TC-1.1: [Description] (stage: nl)
- TC-1.2: [Description] (stage: nl)

**Dependencies:** None | M0

### Milestone 2: [Later approved work]
**North Star Milestone:** no
...
```

Exactly one milestone MUST be marked `North Star Milestone: yes`. It may follow a
technical/full-depth Getting Started prerequisite; bootstrap is not automatically
the useful outcome. Every story in that milestone must directly enable, deliver, or
prove the declared thin path. A dashboard, endpoint, or component added without that
link belongs in later work or an explicit non-goal.

**For technical/full depth, require a "Getting Started" milestone when setup is a
real prerequisite:**
```markdown
### Milestone 0: Getting Started (Bootstrap)
**North Star Milestone:** no
**User Stories:**
- US-0: As a new user, I want to set up the tool so that I can start using it

**Success Criteria:**
- [ ] Setup takes < 5 minutes
- [ ] Clear error messages if prerequisites are missing
- [ ] Can verify setup worked before proceeding
```

#### 3.4. Architecture-Impact Assessment (REQUIRED)

**This is a GATE — do not proceed until the architecture-impact block is written into the roadmap.**

**Update Tasks:** Mark "Architecture-impact assessment" as `in_progress`.

Record architecture impact before debate so critics receive the component and
middleware boundaries. Phase 4 still owes an artifact, including for `skip` mode.

**Procedure:**

1. Read `.architecture/INDEX.md`, then `.architecture/primer.md` and the relevant component docs (if present). For greenfield sessions with no `.architecture/` corpus, treat the planned component map as the reference.
2. For each milestone in the draft roadmap, ask:
   - Does any user story introduce a **new component class** (new layer, new service, new background worker class)?
   - Does any user story require **new shared middleware** (cross-cutting concern that multiple endpoints/jobs will consume)?
   - Does any user story add **new variables, schemas, or contracts** that will flow through existing middleware?
3. Produce the `architecture_impact` block (see schema below). Even "no change" must be explicit — a one-line verdict with rationale.

**`architecture_impact` block schema** (manifest, or active detail for `inline`):

```json
{
  "architecture_impact": {
    "verdict": "no_change | extends_existing | new_components | new_middleware",
    "rationale": "1-3 sentences explaining the verdict",
    "new_components": [
      {"name": "string", "kind": "route | model | worker | cli | migration | ...", "extends": "<existing component class or 'new layer'>"}
    ],
    "new_middleware": [
      {"name": "string", "purpose": "string", "consumed_by": ["<surface or endpoint>", ...]}
    ],
    "new_vars_into_existing_middleware": [
      {"variable": "string", "target_middleware": "string", "purpose": "string"}
    ],
    "assessed_at": "ISO8601",
    "assessed_against": "<git_hash of .architecture/ at time of assessment, or 'greenfield'>"
  }
}
```

**Verdict criteria:**
- `no_change`: roadmap touches only existing components, no new shared middleware, no new contracts flowing through middleware. Phase 4 will run in `skip` mode.
- `extends_existing`: roadmap adds new modules WITHIN existing component classes (e.g., a new route in an existing routes layer, a new model in an existing model layer). No new layers, no new middleware. Phase 4 will run in `lightweight` mode.
- `new_components`: roadmap introduces a new component class or layer. Phase 4 will run in `full` mode.
- `new_middleware`: roadmap requires shared middleware (auth, logging, validation, retry, etc.) that crosses surfaces. Phase 4 will run in `full` mode AND middleware-creator may activate post-execution.

**Example — "no change" verdict:**

```json
{
  "architecture_impact": {
    "verdict": "no_change",
    "rationale": "Adds two GET endpoints to existing api/routes layer. Returns data already produced by existing analyzer module. No new components or shared concerns.",
    "new_components": [],
    "new_middleware": [],
    "new_vars_into_existing_middleware": [],
    "assessed_at": "2026-05-17T18:30:00Z",
    "assessed_against": "9b0d437"
  }
}
```

**Example — "extends_existing" verdict with var-into-middleware mapping:**

```json
{
  "architecture_impact": {
    "verdict": "extends_existing",
    "rationale": "Adds an annotation BFF route and Annotation discriminated-union model. Pushes two new fields through existing event-stream and singleflight middleware.",
    "new_components": [
      {"name": "me_annotations route", "kind": "route", "extends": "app/routes/"},
      {"name": "Annotation model", "kind": "model", "extends": "app/models/"}
    ],
    "new_middleware": [],
    "new_vars_into_existing_middleware": [
      {"variable": "MAX_RECORD_SIZE = 64KB", "target_middleware": "jsonl_event_stream.py", "purpose": "Cap record size to prevent OOM"},
      {"variable": "schema_version in cache key", "target_middleware": "evaluation_context_store.py", "purpose": "Bust cache on schema migrations"}
    ],
    "assessed_at": "2026-05-17T18:30:00Z",
    "assessed_against": "9b0d437"
  }
}
```

**Treatment-session shortcut:** If `pre_plan_path` is set and the pre-plan contains an `## Architecture Impact` section, extract the block from that source rather than re-deriving it. Confirm it still matches the approved scope and current architecture before reuse.

**[GATE] TodoWrite: Mark "Architecture-impact assessment" completed only after the block is written into the draft roadmap manifest (or active session detail for `inline`).**

---

#### 3.5. Goal and Slice North Star Alignment Check (Human Guardrail)

**This is a GATE — do not proceed to Phase 3 review until alignment is confirmed.**

**Update Tasks:** Mark "Validate Slice North Star milestone [GATE]" and
"Goal alignment check (human guardrail)" as `in_progress`.

Review the roadmap against both Goals/Non-Goals and the confirmed Slice North Star:

1. The roadmap has exactly one marked North Star Milestone, with at least one user
   story and a success criterion that proves the declared outcome.
2. Every story in that milestone directly enables, delivers, or proves the thin
   path. A story that merely adds a dashboard panel, endpoint, or component fails
   unless it has that direct link.
3. Stories outside the North Star Milestone either support a declared prerequisite
   or are marked later; they cannot silently expand the first useful slice.
4. Each story still serves a stated goal and does not implement a non-goal.
5. If the roadmap lacks Goals, Non-Goals, or Slice North Star, flag the gap and
   repair it before debate.

When a contradiction appears, revise the North Star, stories, or boundaries until
the user confirms alignment. Complete both TodoWrite gates only after confirmation.

#### 4. Carry Open Questions into Phase 3

For `reviewed` or `iterative`, persist the questions needing critique alongside the
roadmap. Phase 3 reviews them through the pipeline once the card is eligible.
Resolve product decisions with the user and reconfirm changed goals, boundaries,
or North Star milestones before continuing.

#### 5. User Confirmation (REQUIRED)

**CRITICAL CHECKPOINT:** Before accepting the roadmap artifacts, present them to the user:

> "Here's the roadmap I've drafted:
>
> **Roadmap mode:** [inline | reviewed | iterative] — [open questions/reason]
> **Milestones:** [list]
> **User Stories:** [count]
> **Getting Started:** [present/missing]
>
> Do you want to:
> 1. Accept this roadmap
> 2. Make changes
> 3. Accept for Phase 3 review with recorded open questions"

**Do NOT proceed to adversarial debate until user confirms roadmap.**

**[GATE] TodoWrite: Mark "User confirms roadmap" completed before proceeding to Step 6.**

#### 6. Persist Roadmap Artifacts

- `inline`: store the roadmap and non-empty `user_stories` array in the active
  `.adversarial-spec/sessions/<id>.json`; set `roadmap_path: "inline"`.
- `reviewed` / `iterative`: write `roadmap/manifest.json` as the roadmap source and
  `roadmap/overview.md` as its readable view; set `roadmap_path` to the manifest.
- Persist `roadmap_mode`, its rationale, open review questions, architecture impact,
  and `tests_pseudo_path`. Keep the accepted North Star and milestone mapping.

**Artifact assertion [GATE]:** Read back the active detail's selected roadmap
(inline or manifest). It must contain the approved stories, milestones, North Star,
and architecture impact; the referenced test artifact must exist and cover each
story. Missing, empty, or unreadable artifacts block entry to Phase 3.

See SKILL.md § [Journey Log](../SKILL.md#journey-log).
See SKILL.md § [Phase Transition Protocol](../SKILL.md#phase-transition-protocol).

Use the router's version-aware handoff after verification; v6 requires D0
Decomposition before debate. Phase 7 owns execution planning. Any session task
creation requires plan amendment → `pipeline_validate_plan` → `pipeline_load`
with explicit `board_id`; never raw `add_card`. Do not use `pipeline_patch_state`
to bypass a pipeline gate.

Test promotion and binding follow the [TMR/maturity contract](../reference/document-types.md#happy-path-spine-and-maturity-ladder).

#### 9. Test Design Methodology

**Apply from initial `tests-pseudo.md` generation and maintain through every debate round.**

##### 9a. Test Data Strategy Annotations (REQUIRED)

Every test case MUST be annotated with its data strategy. This eliminates "I'll figure out fixtures later" drift during implementation.

| Strategy | When to use | Example |
|----------|-------------|---------|
| `REAL-DATA` | Condition occurs naturally in a normal run of the project's data | Reversals, signal clusters, mixed exit types |
| `REAL-DATA + PROPERTY` | Run real data, assert relationships not exact values | "all scores in [0,1]", "exit counts sum to total" |
| `SYNTHETIC` | Condition **cannot** occur in real data, or requires precise numeric control | Zero-variance market, exact boundary values, flat data |
| `MOCK` | External dependency (network, filesystem, third-party API) | API connection failure, cache lifecycle |
| `FRONTEND` | Component render, interaction, or visual assertion | Heatmap renders, button swaps axes |
| `STATIC` | Read config file, no runtime needed | Proxy port check |

**Classification rule:** Default to REAL-DATA. Only use SYNTHETIC when you can articulate *why* the condition won't appear in a normal run. "I want exact control" is not sufficient — if the condition occurs naturally, use real data and assert properties. SYNTHETIC is for impossible/degenerate conditions (flat market, zero variance) and precise boundary math where you need to land on an exact value.

**Lazy classification is a process failure.** If you stamp SYNTHETIC on "2 positions open, reversal signal fires" — that happens in any volatile trading day. Use REAL-DATA. Reserve SYNTHETIC for conditions that genuinely require manufacturing: fill ordering instrumentation, exact equity math, zero-variance indicators.

Include the annotation as a **Data Strategy:** line immediately after the test case title, with a brief justification:
```markdown
### TC-1.5: Histogram auto-cap zero median — guaranteed floor
**Data Strategy: SYNTHETIC** — Zero histogram median cannot occur in real market data (MARA is volatile).
```

**MOCK falsification requirement (REQUIRED for every `Data Strategy: MOCK*` test).** Any test labeled `MOCK`, `MOCK-EXTERNAL`, or any other `MOCK*` variant MUST carry an additional `why_impossible_to_reproduce_live:` field whose value is a specific technical condition that cannot be forced with dev infrastructure + small real money. A `scope:` descriptor (e.g., *"scope: Kalshi REST response"*) is a topic pointer, not an impossibility claim — it does not satisfy this requirement.

Valid examples:
- *"Kalshi maintenance-mode 503 (controlled outage only; dev account has no mechanism to induce)"*
- *"Network partition between gateway host and exchange (no dev hook to simulate without disabling host networking)"*

Invalid (trivially falsifiable — use REAL-DATA instead):
- *">100 positions required for pagination"* → fund dev, open >100 sub-dollar positions
- *"rate-limit behavior under burst"* → rapid-fire real orders, gain real telemetry
- *"error-code generation"* → malformed orders, invalid tickers, bad credentials
- *"cancel-failure path"* → cancel a nonexistent, already-filled, or malformed order ID

If the `why_impossible_to_reproduce_live:` value is empty, hand-wavy, or names a condition that a reviewer can force live, the classification is a process failure — promote the test to REAL-DATA.

```markdown
### TC-M2.8: Kalshi maintenance-mode 503 retry backoff
**Data Strategy: MOCK-EXTERNAL** — scope: Kalshi REST response
**why_impossible_to_reproduce_live:** Kalshi maintenance 503 is a controlled exchange-side outage; no dev-account mechanism induces it.
```

##### 9b. Boundary Value Analysis (REQUIRED for numeric specs)

Every numeric boundary in the spec MUST have at-boundary and just-outside tests. When writing or updating tests-pseudo.md, scan the spec for:
- Threshold comparisons (`>=`, `>`, `<`, `<=`)
- Range limits (`[0..50]`, `(0..100]`)
- Minimum counts (`< 2 trades`, `< 30 trades`)
- Capacity limits (`max 2 positions`)

For each boundary, add tests marked `[BVA]`:
- **At boundary:** value exactly equals the limit
- **Just outside:** value one unit past the limit
- **Clarify inclusive/exclusive:** If the spec uses `>=`, test at `=` and document it passes

Example:
```markdown
### TC-X.Y: Score exactly at threshold [BVA]
**Data Strategy: SYNTHETIC** — Need precise control to land composite exactly on threshold.
```

##### 9c. State Transition Testing (REQUIRED for stateful components)

If the spec describes a component with mutable state (e.g., strategy engine with positions), create a **State Transition Table** listing:
- All legal states
- All events/signals that cause transitions
- Resulting state and action for each combination
- Which test case covers each transition

Format:
```markdown
### State Transition Table

| # | From | Event | To | Action | Test |
|---|------|-------|----|--------|------|
| T1 | S0 (0 open) | buy signal | S1 (1 open) | open position | TC-X.1 |
| T2 | S1 | buy signal, allowed | S2 (2 open) | open second | TC-X.2 |
```

Every row must have a test. If a transition lacks a test, add one.

##### 9d. Decision Table Testing (REQUIRED for combinatorial logic)

If the spec defines branching logic with multiple conditions (e.g., scoring gate with ADX zone + score comparison), create a **Decision Table** covering all condition combinations:

```markdown
### Scoring Gate Decision Table

| # | Condition A | Condition B | Expected Result | Test |
|---|-------------|-------------|-----------------|------|
| 1 | below_floor | any | rejected | TC-X.1 |
| 2 | soft_zone | passes | scored, true | TC-X.2 |
```

Every row must have a test. Missing rows = missing coverage.

##### 9e. Semantic Contract and Causality Testing (REQUIRED for user-visible behavior)

Every user-facing parameter, output field, chart/table label, tooltip, and derived metric must have a canonical contract classification before tests are considered adequate:

| Classification | Meaning | Minimum Test Shape |
|----------------|---------|--------------------|
| `active_formula` | Changing this input changes the emitted metric/formula value | Perturb input A while holding others fixed; assert metric changes by expected formula |
| `active_gate` | Changing this input changes pass/fail or routing, but not the emitted metric value | Perturb gate; assert pass/fail/routing changes and score/value remains stable if applicable |
| `threshold` | Compared against a computed value | At-boundary and just-outside BVA; assert inclusive/exclusive behavior |
| `telemetry_only` | Emitted for explanation, never changes decisions | Perturb field; assert telemetry changes and decisions/score do not |
| `legacy_display` | Retained for comparison/display but not active behavior | Assert UI labels it legacy/display-only and active metrics remain unchanged |
| `display_contract` | User-visible text explains behavior | Static/frontend test checks label/tooltip/legend matches canonical classification |

Tests must prove both sides of the causal contract:
- **Positive causality:** active inputs change the behavior they claim to control.
- **Negative causality:** telemetry-only and legacy-display inputs do NOT change active decisions or active scores.

Field-presence, non-null, status-code, and range tests are not sufficient for semantic contracts. They may remain as smoke tests, but they do not satisfy this methodology unless paired with a falsifying causality, formula, or display-contract assertion.

Example:
```markdown
### TC-X.Y: ADX center is display-only for active score
**Data Strategy: SYNTHETIC** — Need fixed indicators to isolate parameter causality.
given: identical bars/indicators and two param sets differing only in scoring_adx_center
when: entry scoring runs
then: adx_moderate changes, but entry_score.score and pass/fail are unchanged
assert: detail_a.adx_moderate != detail_b.adx_moderate
assert: detail_a.score == detail_b.score
assert: passed_a == passed_b
```

Bias toward adding contract, causality, invariant, and user-surface tests when in doubt. Avoid padding with duplicate smoke tests that do not increase falsification power.
