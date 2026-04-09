# Phase 4: Target Architecture — Spec Draft v1

## Overview

This document specifies the rewritten Phase 4 (Target Architecture) of the adversarial-spec workflow. Phase 4 is the architecture decision phase — it runs after spec debate converges and before the gauntlet stress test. It produces a `target-architecture.md` document, architectural invariants, and a Decision Journal.

The rewrite addresses five critical gaps in the current Phase 4:

1. **No cross-cutting concerns.** The current phase treats architecture as "pick some dimensions, draft a doc, debate it" without systematically addressing middleware chains, error handling, validation boundaries, source-of-truth enforcement, observability, caching, or configuration management.

2. **No context branching.** The same 8 steps apply whether you're building from scratch, adding a feature to an existing codebase, or diagnosing an architectural failure. These are fundamentally different workflows with different inputs, scopes, and outputs.

3. **Vague dimensions.** "Auth" and "Data freshness" are listed for web apps, but there's no guidance on what decisions to make within each dimension, what questions to ask, or what deliverables to produce.

4. **No architectural invariants.** The phase produces a document but doesn't force explicit, testable assertions that can be checked by `/mapcodebase` or `/diagnosecodebase`.

5. **Data-flow-only dry-run.** The current dry-run asks "what data is fetched?" and "what happens on error?" but never asks about middleware ordering, validation duplication, SoT conflicts, or observability gaps.

## Evidence: BracketBattleAI Failures

All traceable to missing Phase 4 guidance:

- **CON-001**: 13 of 52 API routes skip rate limiting. 45+ routes repeat auth/rate-limit boilerplate. A middleware chain decision would have prevented this.
- **CON-002**: Two bracket generation pipelines (one dead, one production) writing to different stores. A SoT declaration would have prevented this.
- **GAP-01 through GAP-04**: Three model registries with conflicting data. No SoT enforcement.
- **GAP-05**: Dual pipelines with different transport selection. No integration contract.
- **GAP-09**: Three leaderboard read paths. No caching/read-path architecture decision.

---

## 1. Phase Structure

### 1.1 TodoWrite (Entry Point)

```
TodoWrite([
  {content: "Scale check — assess if architecture phase needed [GATE]", status: "in_progress", activeForm: "Assessing architecture phase need"},
  {content: "Detect context mode (greenfield / brownfield-feature / brownfield-debug)", status: "pending", activeForm: "Detecting architecture context mode"},
  {content: "Categorize application and select dimensions", status: "pending", activeForm: "Categorizing application"},
  {content: "Assess cross-cutting concerns (7 mandatory categories)", status: "pending", activeForm: "Assessing cross-cutting concerns"},
  {content: "Research best practices for each dimension + concern", status: "pending", activeForm: "Researching best practices"},
  {content: "Draft target-architecture.md", status: "pending", activeForm: "Drafting target architecture"},
  {content: "Define architectural invariants", status: "pending", activeForm: "Defining architectural invariants"},
  {content: "Debate architecture until convergence", status: "pending", activeForm: "Debating architecture"},
  {content: "Dry-run verification (expanded questions) [GATE]", status: "pending", activeForm: "Running dry-run verification"},
  {content: "Record decisions in Decision Journal", status: "pending", activeForm: "Recording architecture decisions"},
])
```

### 1.2 Prerequisites

- Spec debate (Phase 3) has converged
- Roadmap with user stories exists

### 1.3 Inputs

- Converged spec draft
- Roadmap / user stories
- `.architecture/manifest.json` concerns[] (optional — from `/mapcodebase`)
- `.architecture/manifest.json` patterns[] (optional — from `/mapcodebase`)
- Framework documentation (via Context7 / web)
- gemini-bundle findings (optional)

---

## 2. Step 1: Scale Check (Gate)

Not every project needs formal architecture. Assess:

```
Scale Assessment
───────────────────────────────────────
Spec scope: [user story count]
Codebase: [greenfield / existing with N files]
Stack complexity: [single runtime / multi-service]

Recommended: [Full architecture | Lightweight | Skip]
```

**Skip criteria:** <3 user stories AND single-file scope, or pure library with no app layer.

**Lightweight criteria:** 3-5 user stories, single runtime, no external integrations. Use the greenfield flow but skip the architecture debate round — the dry-run alone is sufficient.

If skip: log Decision Journal entry with `decision: "skip"`, transition directly to gauntlet.

**[GATE] Mark "Scale check" completed before proceeding. If skip: mark all remaining items completed.**

---

## 3. Step 2: Context Mode Detection

This is the critical branching point. The mode determines which steps apply, what scope of analysis is required, and what deliverables are produced.

### 3.1 Mode Selection

| Mode | Trigger | Scope | Starting Point |
|------|---------|-------|----------------|
| **Greenfield** | No existing codebase | Whole system | Research best practices, define from scratch |
| **Brownfield Feature** | Adding or improving a feature in an existing codebase | Blast zone + touched cross-cutting concerns | Read `.architecture/` docs, assess fitness-for-purpose |
| **Brownfield Debug** | Fixing a bug or architectural problem | Blast zone + the middleware/validation/SoT path the bug traversed | Identify which architectural layer failed |

**Detection heuristic:**
1. If spec has no `blast_zone` or `blast_zone` references only new files → **Greenfield**
2. If spec originated from `/diagnosecodebase` or `/treatcodebase`, or the roadmap milestone is a bug fix → **Brownfield Debug**
3. Otherwise → **Brownfield Feature**

Present detected mode to user for confirmation before proceeding.

### 3.2 Scope Rules

**Greenfield:** The entire system is in scope. All 7 cross-cutting concern categories are mandatory. All dimension categories apply.

**Brownfield Feature:** Scope is the **blast zone from the plan** (files to modify + files they import/export) plus **any cross-cutting concern that the feature touches**. Specifically:
- Load `.architecture/primer.md` for system context
- Load component docs for files in the blast zone
- For each of the 7 concern categories, assess: "Does this feature interact with this concern?" If yes, that concern is in scope.
- Out-of-scope concerns are noted as "not affected" with a one-line rationale, not analyzed in depth.

**Brownfield Debug:** Scope is the **bug's traversal path** — from entry point through middleware, validation, data layer, and back. The goal is to identify which architectural layer failed and whether the fix is local or systemic.

---

## 4. Greenfield Flow (Steps 3-10)

### 4.1 Step 3: Categorize the Application

Classify along dimensions relevant to the project type. The taxonomy adapts to the category — don't force web-app dimensions onto a CLI tool.

**Schema (flexible dimensions array):**
```json
{
  "architecture_taxonomy": {
    "category": "web-app | cli | api-service | library | data-pipeline | mobile | other",
    "dimensions": [
      {
        "name": "rendering",
        "value": "hybrid-ssr-csr",
        "rationale": "SSR for initial load, CSR for interactive editors",
        "source_refs": ["Next.js App Router docs", "spec section 7"]
      }
    ],
    "confirmed_by_user": true,
    "confirmed_at": "ISO8601"
  }
}
```

**Dimension lists by category:**

**Web apps:**
- Rendering strategy (SSR/CSR/SSG/hybrid)
- Navigation (SPA/MPA/hybrid)
- Auth and authorization
- Data freshness (polling/websocket/SSE/stale-while-revalidate)
- State management (server state/client state/URL state)
- Multi-page data sharing
- Middleware chain (request pipeline ordering)
- Error handling strategy (error boundaries/global handler/per-route)
- Validation boundaries (client/API/service/database)
- Caching (CDN/server/client/service worker)
- Observability (structured logging/tracing/metrics)
- Security (CORS/CSP/XSS sanitization/CSRF)
- Testing architecture (unit/integration/e2e split)

**APIs / Backend services:**
- Transport (REST/GraphQL/gRPC/WebSocket)
- Auth and authorization (middleware-based/per-route/API key/OAuth)
- Data layer (ORM/raw SQL/document store/file-based)
- Scaling strategy (horizontal/vertical/auto)
- Middleware chain (ordered pipeline of concerns)
- Error handling pipeline (raw -> logged -> user-facing transform stages)
- Validation boundaries (transport/service/domain/persistence)
- Service composition (monolith/microservices/modular monolith)
- Caching (in-memory/Redis/CDN/application-level)
- Configuration management (env vars/config files/secrets manager/feature flags)
- Security beyond auth (rate limiting/input sanitization/SQL injection prevention)
- Deployment strategy (blue-green/canary/rolling)

**CLIs:**
- Execution model (one-shot/interactive/daemon/watch mode)
- State management (stateless/config file/database/session file)
- Concurrency (single-threaded/async/multiprocess)
- I/O model (stdin-stdout/file/network/mixed)
- Error handling (exit codes/stderr formatting/structured output)
- Configuration management (flags/env vars/config files/precedence rules)
- Observability (verbose mode/debug logging/progress reporting)
- Testing strategy (unit/integration/snapshot/golden file)

**Libraries / SDKs:**
- API surface (function-based/class-based/builder pattern)
- Error handling (exceptions/result types/error codes)
- Extensibility (plugins/hooks/middleware/events)
- Observability hooks (logging integration/metrics/tracing propagation)
- Configuration points (constructor args/builder/env vars)
- Testing support (test helpers/mocks/fakes/fixtures provided)

**Data pipelines:**
- Orchestration (DAG scheduler/event-driven/cron/manual)
- Schema evolution (versioned schemas/schema registry/backward compatibility)
- Idempotency (exactly-once/at-least-once/deduplication strategy)
- Backfill strategy (full reprocessing/incremental/checkpoint-based)
- Monitoring (pipeline health/data quality/SLA tracking)

**Mobile:**
- Offline-first (local DB/sync queue/conflict resolution)
- Sync strategy (pull/push/bidirectional/CRDT)
- Push notifications (FCM/APNs/in-app)
- Deep linking (universal links/app links/deferred)
- App lifecycle (background tasks/state restoration/migration)

Present classification to user for confirmation.

### 4.2 Step 4: Cross-Cutting Concerns Assessment

**This step is NEW and MANDATORY for all projects above the scale threshold.** It is the primary addition to Phase 4.

For each of the 7 concern categories below, the LLM must:
1. State the decision for this project
2. Provide rationale with source references
3. Note the alternative considered
4. Provide an implementation sketch (code snippet or file structure)

#### Concern 1: Middleware Chain

Define the ordered list of concerns that every request passes through, with framework-specific implementation.

**Questions to answer:**
- What middleware runs, in what order?
- What happens if a middleware rejects the request?
- Can a developer add a route and accidentally skip middleware?
- How is the middleware chain enforced (framework-level vs convention)?

**Example output:**
```markdown
### Middleware Chain
**Decision:** Framework-enforced middleware stack (not convention)
**Order:** [CORS, rate-limit, auth, request-logging, validation, handler, error-transform, response-logging]
**Enforcement:** All routes register through a central router that applies the full stack. No per-handler middleware application.
**Framework mechanism:** [e.g., Express app.use() in order, Django MIDDLEWARE setting, FastAPI middleware stack]
**Bypass rules:** Health check and metrics endpoints bypass auth but not rate-limit or logging.
```

#### Concern 2: Error Handling Pipeline

Define a multi-stage error transform: raw error -> logged error -> user-facing error.

**Questions to answer:**
- Where are errors caught? (per-handler, middleware, global)
- What gets logged vs what the user sees?
- Are correlation IDs attached at the catch site or propagated?
- What's the error response format? (JSON envelope, HTTP status codes, error codes)

#### Concern 3: Validation Boundaries

Define what each layer validates, preventing both gaps and duplication.

**Questions to answer:**
- What does the transport layer validate? (request shape, auth token presence)
- What does the service layer validate? (business rules, authorization)
- What does the domain layer validate? (invariants, entity constraints)
- What does the persistence layer validate? (schema constraints, referential integrity)
- Where is validation duplicated, and is that intentional?

#### Concern 4: Source of Truth (SoT) Enforcement

Declare the single authoritative writer for each data entity and the staleness SLA for read copies.

**Questions to answer:**
- For each data entity: who writes it? (one answer only)
- Are there read copies? What's the max acceptable staleness?
- If two components both write to the same entity, which one is authoritative?
- How are SoT violations detected? (consistency checks, monitoring)

**The "13 routes" anti-pattern:** If you find yourself writing "add the same 3 lines to every handler" or "each service maintains its own copy", you have a SoT problem. Centralize the writer.

#### Concern 5: Observability

Define structured logging fields, trace propagation, and metrics for SLOs.

**Questions to answer:**
- What fields are in every log line? (timestamp, correlation ID, service, level, message)
- How are traces propagated across service boundaries?
- What SLOs exist, and what metrics track them?
- If this fails at 2am, how do we know? What alerts fire?

#### Concern 6: Caching

Define what's cached, where, TTL, and invalidation strategy.

**Questions to answer:**
- What data is cached? (responses, computed values, session data)
- Where is the cache? (in-memory, Redis, CDN, browser, service worker)
- What's the TTL for each cached item?
- How is the cache invalidated? (TTL expiry, event-driven, manual)
- What happens if the cache and source disagree?

#### Concern 7: Configuration Management

Define what's externalized, how secrets are managed, and feature flag strategy.

**Questions to answer:**
- What configuration is externalized vs hardcoded?
- How are secrets managed? (env vars, secrets manager, vault)
- Is there a feature flag system? What toggles exist?
- What's the configuration precedence? (env > config file > default)
- Are configuration changes hot-reloadable or do they require restart?

### 4.3 Step 5: Research Best Practices

For each dimension AND each in-scope concern:
1. Look up the established pattern for the chosen stack
2. Minimum 2 sources (official docs + community/template)
3. Use Context7 if available for exact API signatures
4. Note where the framework provides built-in solutions vs where custom implementation is needed

### 4.4 Step 6: Draft Target Architecture Document

Produce `specs/<slug>/target-architecture.md`:

```markdown
### [Pattern/Concern Name]
**Decision:** [pattern chosen]
**Rationale:** [why, with source references]
**Alternative considered:** [what else was evaluated]
**Implementation sketch:** [code snippets or file structure]
**Applies to:** [which user stories / features]
**Concern category:** [middleware | error-handling | validation | sot | observability | caching | config | dimension]
```

If `concerns[]` available from mapcodebase: each `now` concern should either be addressed explicitly by the target architecture or explicitly declared out of scope with rationale.

If `patterns[]` available from mapcodebase: each `warning`/`error` pattern gets a corresponding section explaining how it's addressed.

### 4.5 Step 7: Define Architectural Invariants

**This step is NEW.** Produce a section in `target-architecture.md` titled "Architectural Invariants."

Invariants are explicit, testable assertions about the system. They become:
- Input to `/mapcodebase` pattern detection (can verify invariants against source)
- Input to `/diagnosecodebase` concern detection (violations become concerns)
- Checklist for code review (does this PR violate an invariant?)

**Format:**
```markdown
### Architectural Invariants

INV-001: [category:middleware] Every API route passes through [auth, rate-limit, logging] middleware
INV-002: [category:sot] Every data entity has exactly one authoritative writer
INV-003: [category:error-handling] Every error is caught, logged with correlation ID, and transformed before reaching the user
INV-004: [category:validation] No service accesses another service's database directly
INV-005: [category:config] All configuration is externalized — no secrets in source code
```

**Rules:**
- Each invariant must reference a concern category
- Each invariant must be verifiable against source code (not subjective)
- Minimum 1 invariant per in-scope concern category
- Invariants are append-only during the session — to remove one, add a "reversed" Decision Journal entry

### 4.6 Step 8: Debate the Architecture

Run architecture-specific critique rounds:

```bash
cat specs/<slug>/target-architecture.md | \
  uv run python ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --models MODEL_LIST --doc-type architecture --round N \
  --context specs/<slug>/spec-draft-latest.md \
  $CONTEXT_FLAGS
```

**Debate focus areas:**
- Are all cross-cutting concerns addressed for the chosen category?
- Do the invariants cover the most critical architectural boundaries?
- Is the middleware chain complete and correctly ordered?
- Are validation boundaries clear and non-overlapping?
- Is the SoT declaration consistent (no entity with two writers)?

If debate reveals spec gaps: revise spec -> run spec debate round -> resume architecture debate.

Continue until convergence.

### 4.7 Step 9: Dry-Run Verification (Gate)

Walk the most complex user flow through the architecture step-by-step. The expanded dry-run covers ALL concern categories, not just data flow.

**Data flow questions (existing):**
- Which component renders / handles the request?
- What data is fetched, by whom, via what mechanism?
- What state is created, where, what happens on navigation?
- What happens on error?

**Middleware questions (NEW):**
- What middleware runs before this handler? In what order?
- Can a new developer add a route and accidentally skip auth/validation/logging?
- If middleware rejects the request, what response does the user see?

**Validation questions (NEW):**
- Where does validation happen for this flow? Is it duplicated across layers?
- What happens if invalid data bypasses the transport layer validation?

**SoT questions (NEW):**
- Is there exactly one source of truth for each data entity in this flow?
- If this flow writes data, is the writer the declared authoritative source?

**Observability questions (NEW):**
- If this fails at 2am, how do we know? What's observable?
- Can we trace a single request from entry to response?

**Caching questions (NEW):**
- What's cached in this flow? What happens if the cache and source disagree?
- Is the TTL appropriate for the freshness requirement?

**Invariant questions (NEW):**
- Does this flow violate any declared architectural invariant?
- Are there invariants that should exist but don't?

**The dry-run is the proof the architecture is complete.** If gaps found: revise architecture, re-debate the change.

**[GATE] Mark "Dry-run verification" completed before proceeding to Decision Journal.**

### 4.8 Step 10: Record Decisions

Log all architecture decisions to the Decision Journal in the session detail file. Schema unchanged from current Phase 4.

---

## 5. Brownfield Feature Flow

This flow replaces the greenfield Steps 3-7 with blast-zone-scoped versions. Steps 1 (scale check), 2 (context detection), 8 (debate), 9 (dry-run), and 10 (decision journal) are shared.

### 5.1 Step 3-BF: Read Blast Zone Architecture

1. Load `.architecture/primer.md` for system context
2. Load component docs for files in the blast zone (from `.architecture/structured/components/`)
3. List `now`/`next` concerns from `manifest.json` `concerns[]`
4. List `warning`/`error` patterns from `manifest.json` `patterns[]`
5. Load gemini-bundle findings if available

### 5.2 Step 4-BF: Trace Request Paths

For each entry point affected by the feature:
1. Map the middleware chain the request passes through (from entry to handler to response)
2. Identify which cross-cutting concerns are touched
3. Note where the feature adds new steps to the chain

### 5.3 Step 5-BF: Assess Cross-Cutting Fitness

For each of the 7 concern categories, assess fitness-for-purpose:

| Concern | Assessment |
|---------|-----------|
| Middleware chain | adequate / needs extension / missing / conflicts |
| Error handling | adequate / needs extension / missing / conflicts |
| Validation boundaries | adequate / needs extension / missing / conflicts |
| Source of truth | adequate / new entity needed / conflicts |
| Observability | adequate / needs extension / missing |
| Caching | adequate / new cache needed / invalidation change needed |
| Configuration | adequate / new config needed / externalization needed |

**Only concerns marked "needs extension", "missing", "conflicts", or "new X needed" proceed to Step 6.** Concerns marked "adequate" are logged with a one-line rationale and skipped.

### 5.4 Step 6-BF: Draft Architecture Additions

Produce architecture additions ONLY for in-scope concerns. Use the same format as greenfield (decision/rationale/alternative/sketch/applies-to/concern-category).

**Critical constraint:** Architecture additions must be compatible with the existing architecture. If a proposed addition conflicts with an existing pattern, the conflict must be surfaced in the debate round.

### 5.5 Step 7-BF: Update Invariants

If the feature introduces new architectural boundaries, add invariants. If existing invariants are affected, note whether they still hold.

---

## 6. Brownfield Debug Flow

This flow replaces the greenfield Steps 3-7 with diagnosis-focused versions. Steps 1 (scale check), 2 (context detection), 8 (debate), 9 (dry-run), and 10 (decision journal) are shared.

### 6.1 Step 3-DBG: Identify the Failed Layer

Which cross-cutting concern broke? Use the diagnostic heuristic:

| Symptom | Failed Concern |
|---------|---------------|
| "Auth bug in 13 routes" | Middleware gap (auth not centralized) |
| "Invalid data in database" | Validation boundary gap |
| "Two systems disagree on state" | SoT violation |
| "Can't debug production issue" | Observability gap |
| "Stale data shown to users" | Caching / invalidation failure |
| "Config works in dev, fails in prod" | Configuration management gap |
| "Error swallowed silently" | Error handling pipeline gap |

### 6.2 Step 4-DBG: Local Fix vs Systemic Fix Decision

Apply the decision tree:

1. **Count affected instances.** How many routes/handlers/components exhibit this bug?
   - 1 instance → likely local fix
   - 4+ instances → likely systemic (middleware/architecture) fix

2. **The "new developer" test.** Could a new developer adding a route/handler hit the same bug?
   - Yes → systemic fix (the architecture allowed this to happen)
   - No → local fix (one-off mistake)

3. **The "3 lines" test.** Is the fix "add the same 3 lines to every handler"?
   - Yes → middleware fix (centralize the concern)
   - No → may be a local fix

**Present the decision to the user:**
```
Debug Fix Assessment
───────────────────────────────────────
Symptom: [description]
Failed concern: [concern category]
Affected instances: [count]
New developer risk: [yes/no]
Recommended: [local fix | systemic fix]

[Proceed with recommendation] [Override to local] [Override to systemic]
```

### 6.3 Step 5-DBG: Design or Verify

**If systemic fix:** Design the architectural change (add middleware, fix validation boundary, declare SoT, etc.). Use the same format as greenfield concern assessment for the affected concern(s) only.

**If local fix:** Verify the existing architecture is sound — the bug is in application code, not architecture. Document why the architecture correctly handles this concern in general, and why this specific instance was a deviation.

### 6.4 Step 6-DBG: Check Invariant Coverage

Does an invariant exist that should have prevented this bug?
- **If yes and violated:** The invariant exists but wasn't enforced. Add enforcement mechanism to the architecture.
- **If no:** Add a new invariant that would catch this class of bug.

---

## 7. Outputs

All modes produce:
- `specs/<slug>/target-architecture.md` (with concern-category tags on each section)
- Decision Journal entries in session detail file
- Architecture taxonomy in session detail file

Additionally:
- **Greenfield:** Full invariant set (minimum 1 per concern category)
- **Brownfield Feature:** Invariant additions/updates for affected concerns
- **Brownfield Debug:** Invariant that would have prevented the bug + enforcement mechanism

### Completion Criteria

- All in-scope taxonomy dimensions decided with rationale
- All in-scope cross-cutting concerns assessed with decision
- At least one dry-run completed without gaps (expanded questions)
- Architecture debated through at least one converged round
- Architectural invariants defined for all in-scope concerns
- Decision Journal records categorization + each pattern/concern decision

### Phase Transition

**Detail file** (`sessions/<id>.json`):
- Set `current_phase: "gauntlet"`
- Set `target_architecture_path` to the architecture doc path
- Append journey event

**Pointer file** (`session-state.json`):
- Update `current_phase`, `current_step`, `next_action`, `updated_at`

---

## 8. Interaction with Other Phases

### Phase 2 (Roadmap)

Phase 2 generates `tests-pseudo.md`. Phase 4 invariants may suggest additional test cases:
- Each invariant implies at least one test: "verify INV-001 by checking that route X passes through auth middleware"
- These tests should be appended to `tests-pseudo.md` or flagged as additions during the gauntlet.

### Phase 5 (Gauntlet)

Gauntlet adversaries should receive the invariant list as context. Key adversaries:
- **BURN (burned oncall):** Challenge observability invariants — "if INV-005 fails, how do I know?"
- **PARA (paranoid security):** Challenge auth/validation invariants — "can INV-001 be bypassed?"
- **LAZY (lazy developer):** Challenge middleware enforcement — "can I accidentally skip INV-001?"
- **COMP (compatibility):** Challenge SoT invariants — "does INV-002 conflict with existing patterns?"

### Phase 7 (Execution)

Execution plan tasks should reference invariants:
- Each implementation task notes which invariants it must satisfy
- High-risk tasks (those touching 3+ invariants) get `test-first` strategy
- Invariant enforcement is a verification criterion for task completion

### Downstream Tools

**`/mapcodebase`:** Can consume invariants from `target-architecture.md` to verify against source code. Violations surface as concerns.

**`/diagnosecodebase`:** Can check invariants during diagnosis. Missing enforcement becomes a finding.

These integrations are FUTURE work — this spec defines the invariant format so downstream tools can consume it when ready.

---

## 9. Debate Focus Areas

When this spec goes through adversarial debate, focus on:

1. **Cross-cutting concern taxonomy completeness.** Are 7 categories sufficient? Is anything mis-categorized? Should "security" be its own concern category separate from auth?

2. **Brownfield scoping.** Is "blast zone + touched cross-cutting concerns" the right scope? Too narrow risks missing architectural side effects. Too broad wastes context on irrelevant concerns.

3. **Invariant enforcement format.** How should invariants be structured for downstream tool consumption? Is `[category:X]` tagging sufficient? Should there be a machine-readable invariant schema (JSON)?

4. **The debug decision tree.** Is the "count instances + new developer test + 3 lines test" heuristic practical? What edge cases break it? Should the thresholds (1 vs 4+) be configurable?

5. **Scale check for brownfield.** Should brownfield features have a different scale check than greenfield? A 2-route feature addition might still need middleware assessment.

6. **Test interaction.** Should Phase 4 produce its own test assertions (invariant tests) or just flag additions to `tests-pseudo.md`?