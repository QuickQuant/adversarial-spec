# Phase 4: Target Architecture — Spec Draft v2

> Round 1 synthesis: Incorporates GPT-5.4 (execution surfaces, framework profiles, machine-readable invariants, non-request dry-run), Gemini (background processing, routing, i18n, DB migrations, concurrency control), and Claude (concern interactions, mode-aware dry-run, lightweight mode definition, Phase 2 test integration).

## Overview

Phase 4 defines shared architecture rules after spec debate converges and before the gauntlet. It produces:
- `specs/<slug>/target-architecture.md` (human-readable)
- `specs/<slug>/architecture-invariants.json` (machine-readable)
- Decision Journal entries in session detail file
- Additive test cases in `tests-pseudo.md`

---

## 1. Phase Structure

### 1.1 TodoWrite (Entry Point)

```
TodoWrite([
  {content: "Scale check — assess if architecture phase needed [GATE]", status: "in_progress", activeForm: "Assessing architecture phase need"},
  {content: "Detect context mode (greenfield / brownfield-feature / brownfield-debug)", status: "pending", activeForm: "Detecting architecture context mode"},
  {content: "Declare framework profile and execution surfaces", status: "pending", activeForm: "Declaring framework profile"},
  {content: "Categorize application and select dimensions", status: "pending", activeForm: "Categorizing application"},
  {content: "Assess cross-cutting concerns (7 mandatory categories)", status: "pending", activeForm: "Assessing cross-cutting concerns"},
  {content: "Research best practices for each dimension + concern", status: "pending", activeForm: "Researching best practices"},
  {content: "Draft target-architecture.md", status: "pending", activeForm: "Drafting target architecture"},
  {content: "Define architectural invariants (markdown + JSON)", status: "pending", activeForm: "Defining architectural invariants"},
  {content: "Append invariant-derived tests to tests-pseudo.md", status: "pending", activeForm: "Adding invariant tests"},
  {content: "Debate architecture until convergence", status: "pending", activeForm: "Debating architecture"},
  {content: "Dry-run verification — one per execution surface [GATE]", status: "pending", activeForm: "Running dry-run verification"},
  {content: "Record decisions in Decision Journal", status: "pending", activeForm: "Recording architecture decisions"},
])
```

### 1.2 Prerequisites

- Spec debate (Phase 3) has converged
- Roadmap with user stories and Goals/Non-Goals exists

### 1.3 Inputs

- Converged spec draft
- Roadmap / user stories / Goals / Non-Goals
- `.architecture/manifest.json` concerns[] and patterns[] (optional — from `/mapcodebase`)
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
Cross-cutting touch: [does the change touch auth, persistence,
  caching, async jobs, config, public API, or shared contracts?]

Recommended: [Full architecture | Lightweight | Skip]
```

**Skip criteria:** <3 user stories AND single-file scope AND no cross-cutting concern touched, or pure library with no app layer.

**Lightweight criteria:** 3-5 user stories, single runtime, no external integrations, touches at most 1 cross-cutting concern. Use the greenfield flow but skip the architecture debate round — the dry-run alone is sufficient.

**Full architecture criteria:** Any of: multi-runtime, external integrations, 2+ cross-cutting concerns touched, or failure could create user-visible inconsistency.

If skip: log Decision Journal entry with `decision: "skip"`, transition directly to gauntlet.

**[GATE] Mark "Scale check" completed before proceeding. If skip: mark all remaining items completed.**

---

## 3. Step 2: Context Mode Detection

### 3.1 Mode Selection

| Mode | Trigger | Scope | Starting Point |
|------|---------|-------|----------------|
| **Greenfield** | No existing codebase | Whole system | Research best practices, define from scratch |
| **Brownfield Feature** | Adding or improving a feature in an existing codebase | Blast zone + touched cross-cutting concerns | Read `.architecture/` docs, assess fitness-for-purpose |
| **Brownfield Debug** | Fixing a bug or architectural problem | Blast zone + the bug's traversal path | Identify which architectural layer failed |

**Detection heuristic:**
1. If spec has no `blast_zone` or `blast_zone` references only new files → **Greenfield**
2. If spec originated from `/diagnosecodebase` or `/treatcodebase`, or the roadmap milestone is a bug fix → **Brownfield Debug**
3. Otherwise → **Brownfield Feature**

Present detected mode to user for confirmation.

### 3.2 Scope Rules

**Greenfield:** The entire system is in scope. All 7 cross-cutting concern categories are mandatory.

**Brownfield Feature:** Scope is the **blast zone** (files to modify + files they import/export) plus **any cross-cutting concern the feature touches**. Additionally:
- Load `.architecture/primer.md` and relevant component docs
- For each of the 7 concerns: "Does this feature interact with this concern?" → in scope if yes
- **Existing debt rule:** If a concern is in scope AND has a `now` severity concern in `manifest.json`, note it. The architecture assessment should avoid making existing debt worse. The brownfield assessment does NOT require fixing existing debt, but MUST flag if the new feature would reinforce a known anti-pattern.
- Out-of-scope concerns: noted as "not affected" with one-line rationale.

**Brownfield Debug:** Scope is the bug's traversal path — entry point through enforcement points, validation, data layer, and response. Goal: identify which layer failed and whether the fix is local or systemic.

---

## 4. Step 3: Framework Profile and Execution Surfaces

**This step is NEW.** Before assessing concerns, declare the framework and its native enforcement model. This prevents reinventing what the framework already provides.

### 4.1 Framework Profile

```json
{
  "framework_profile": {
    "category": "web-app | api-service | cli | library | data-pipeline | mobile | other",
    "framework": "Next.js App Router | FastAPI | Express 5 | Django | Rails | etc.",
    "enforcement_model": "description of how the framework enforces cross-cutting concerns"
  }
}
```

**Why this matters:** The same concern ("ensure every request is authenticated") is enforced differently in different frameworks:
- **Express:** `app.use(authMiddleware)` before route handlers — linear middleware chain
- **FastAPI:** `Depends(get_current_user)` in route signatures — dependency injection
- **Next.js App Router:** `middleware.ts` with path matcher — separate from route handlers
- **Django:** `MIDDLEWARE` list in settings — class-based middleware chain
- **Rails:** `before_action` in controllers — callback chain

The Phase 4 concern assessment must use the framework's native enforcement mechanism, not a generic "middleware chain."

### 4.2 Execution Surfaces

Identify which execution surfaces the project uses. Each concern applies to specific surfaces.

| Surface | Examples |
|---------|---------|
| **Request/Response** | HTTP handlers, API endpoints, GraphQL resolvers |
| **Mutation entrypoints** | Server actions, form handlers, RPC calls |
| **Background jobs** | Queue workers, async tasks, Celery/SQS/Sidekiq |
| **Scheduled work** | Cron jobs, periodic tasks, scheduled functions |
| **Startup/Build/Migration** | DB migrations, build scripts, initialization |
| **Client runtime** | Browser JS, React components, Stimulus controllers |
| **Webhooks** | Incoming webhook handlers, event processors |

Every concern assessed in Step 5 must declare which surfaces it applies to.

---

## 5. Step 4: Categorize the Application

Classify along dimensions relevant to the project type.

**Schema:**
```json
{
  "architecture_taxonomy": {
    "category": "web-app | cli | api-service | library | data-pipeline | mobile | other",
    "framework_profile": "see Step 3",
    "dimensions": [
      {
        "name": "rendering",
        "value": "hybrid-ssr-csr",
        "rationale": "SSR for initial load, CSR for interactive editors",
        "source_refs": ["Next.js App Router docs", "spec §7"]
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
- Routing strategy (file-based/programmatic, data-fetching boundaries, nested layouts)
- Navigation (SPA/MPA/hybrid)
- Auth and authorization
- Data freshness (polling/websocket/SSE/stale-while-revalidate)
- State management (server state/client state/URL state)
- Multi-page data sharing
- Background processing (in-process/external queue/serverless function)
- Enforcement points (framework middleware, route guards, component boundaries)
- Error handling strategy (error boundaries/global handler/per-route/framework-native)
- Validation boundaries (client/API/service/database)
- Caching (CDN/server/client/service worker/framework-native)
- Observability (structured logging/tracing/metrics)
- Security (CORS/CSP/XSS sanitization/CSRF/rate limiting)
- Internationalization (build-time/run-time/routing integration/bundle strategy)
- Database migrations (tooling/zero-downtime patterns)
- Testing architecture (unit/integration/e2e split)

**APIs / Backend services:**
- Transport (REST/GraphQL/gRPC/WebSocket)
- Auth and authorization (enforcement mechanism/API key/OAuth/JWT)
- Data layer (ORM/raw SQL/document store/file-based)
- Database migration strategy (tooling, expand/contract for zero-downtime)
- Scaling strategy (horizontal/vertical/auto)
- Background processing (queue system/retry semantics/dead-lettering/idempotency)
- Enforcement points (middleware chain/dependency injection/decorator pattern)
- Error handling pipeline (raw->logged->user-facing, framework-native error model)
- Validation boundaries (transport/service/domain/persistence)
- Service composition (monolith/microservices/modular monolith)
- Caching (in-memory/Redis/CDN/application-level/framework-native)
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
- Internationalization (bundle vs dynamic loading)

Present classification to user for confirmation.

---

## 6. Step 5: Cross-Cutting Concerns Assessment

**MANDATORY for all projects above the scale threshold.** For each concern:
1. State the decision for this project
2. Declare which execution surfaces it applies to
3. Note the framework-native primitive (if any) and whether it's sufficient
4. Provide rationale with source references
5. Note the alternative considered
6. Provide an implementation sketch

### Concern 1: Enforcement Points

> Renamed from "Middleware Chain" — not all frameworks use linear middleware.

Define how cross-cutting concerns (auth, rate-limiting, logging, validation) are enforced across all execution surfaces.

**Questions to answer:**
- What is the framework's native enforcement mechanism? (middleware, dependencies, callbacks, decorators)
- What enforcement runs on each execution surface? (request handling may differ from background jobs)
- Can a developer add a new endpoint/handler and accidentally skip enforcement?
- Is enforcement framework-level (automatic) or convention (manual)?
- What enforcement bypass rules exist? (health checks, metrics endpoints)

**Framework-specific guidance:**
- **Express/Django:** Ordered middleware list — document the order, note that middleware position matters
- **FastAPI:** Dependency injection — document shared dependencies, note that background tasks bypass request dependencies
- **Next.js App Router:** `middleware.ts` (path-matched, request-only) + `instrumentation.ts` (lifecycle hooks) + Server Component boundaries — document which surface uses which mechanism
- **Rails:** `before_action` callbacks — document controller inheritance chain

### Concern 2: Error Handling Pipeline

Define a multi-stage error transform: raw error -> logged error -> user-facing error. Require framework error model decisions BEFORE custom pipelines.

**Questions to answer:**
- What is the framework's native error model? (e.g., Next.js `error.js`/`global-error.js`, Express terminal error middleware, FastAPI exception handlers)
- Is the framework's default sufficient, or does it need extension?
- Where are errors caught? (per-handler, enforcement layer, global)
- What gets logged vs what the user sees?
- Are correlation IDs attached at the catch site or propagated?
- What's the error response format? (JSON envelope, HTTP status codes, error codes)
- How do errors in background jobs surface? (dead letter queue, alert, retry-then-alert)

### Concern 3: Validation Boundaries

Define what each layer validates, preventing both gaps and duplication.

**Questions to answer:**
- What does the transport layer validate? (request shape, auth token presence)
- What does the service layer validate? (business rules, authorization)
- What does the domain layer validate? (invariants, entity constraints)
- What does the persistence layer validate? (schema constraints, referential integrity)
- Where is validation duplicated, and is that intentional?

### Concern 4: Source of Truth (SoT) and Concurrency

Declare the single authoritative writer for each data entity, staleness SLA for read copies, and concurrent write resolution.

**Questions to answer:**
- For each data entity: who writes it? (one answer only)
- Are there read copies? What's the max acceptable staleness?
- If two components both write to the same entity, which one is authoritative?
- How are concurrent writes to the same entity resolved? (optimistic locking with version/ETag, pessimistic locking, atomic operations, CRDTs, last-write-wins with awareness)
- How are SoT violations detected? (consistency checks, monitoring)

**The "13 routes" anti-pattern:** If you find yourself writing "add the same 3 lines to every handler" or "each service maintains its own copy", you have a SoT problem.

### Concern 5: Observability

Define structured logging fields, trace propagation, and metrics for SLOs.

**Questions to answer:**
- What fields are in every log line? (timestamp, correlation ID, service, level, message)
- How are traces propagated across service boundaries?
- What SLOs exist, and what metrics track them?
- If this fails at 2am, how do we know? What alerts fire?
- Are background job failures observable? (queue depth, failure rate, dead letter count)

### Concern 6: Caching

Define what's cached, where, TTL, and invalidation strategy. Evaluate framework-native cache controls first.

**Questions to answer:**
- What does the framework provide natively? (e.g., Next.js `revalidatePath`/`revalidateTag`, Django cache framework, Rails fragment caching)
- Is the framework default sufficient, or does it need extension?
- What data is cached beyond framework defaults? (computed values, session data, third-party responses)
- Where is the cache? (in-memory, Redis, CDN, browser, service worker)
- What's the TTL for each cached item?
- How is the cache invalidated? (TTL expiry, event-driven, on-demand via framework API)
- What happens if the cache and source disagree?

### Concern 7: Configuration Management

Define what's externalized, how secrets are managed, and feature flag strategy.

**Questions to answer:**
- What configuration is externalized vs hardcoded?
- How are secrets managed? (env vars, secrets manager, vault)
- Is there a feature flag system? What toggles exist?
- What's the configuration precedence? (env > config file > default)
- Are configuration changes hot-reloadable or do they require restart?

### Concern Interactions Checklist

After assessing all 7 concerns individually, verify these known interaction points:

| Interaction | Check |
|-------------|-------|
| Enforcement + Validation | Does enforcement (auth) run before or after input validation? Document the order. |
| Caching + SoT | Can a stale cache temporarily violate SoT? What's the max inconsistency window? |
| Error handling + Observability | Are caught-and-handled errors logged? Or do they disappear silently? |
| Enforcement + Background jobs | Do background jobs have the same enforcement as request handlers? (Often they don't — document the gap.) |
| Validation + Error handling | When validation fails, does the error pipeline produce a useful response? |
| Config + Caching | Do config changes invalidate caches? (Feature flag toggle → cache still serving old behavior?) |

---

## 7. Steps 6-7: Research and Draft

### 7.1 Step 6: Research Best Practices

For each dimension AND each in-scope concern:
1. Check the framework's native primitive FIRST
2. Note: `default accepted`, `default overridden`, or `custom pattern added`
3. Minimum 2 sources (official docs + community/template)
4. Use Context7 if available for exact API signatures

### 7.2 Step 7: Draft Target Architecture Document

Produce `specs/<slug>/target-architecture.md`:

```markdown
### [Pattern/Concern Name]
**Decision:** [pattern chosen]
**Surfaces:** [request/response, background jobs, etc.]
**Serves goals:** [which roadmap Goals this serves]
**User stories:** [which US-X this applies to]
**Framework primitive:** [native mechanism used, or "custom"]
**Rationale:** [why, with source references]
**Alternative considered:** [what else was evaluated]
**Failure mode prevented:** [what goes wrong without this]
**Implementation sketch:** [code snippets or file structure]
**Concern category:** [enforcement | error-handling | validation | sot | observability | caching | config | dimension]
**Test hook:** [test to add in tests-pseudo.md]
```

If `concerns[]` available from mapcodebase: each `now` concern is addressed or declared out of scope.
If `patterns[]` available: each `warning`/`error` pattern gets a section.

---

## 8. Step 8: Define Architectural Invariants

### 8.1 Human-Readable (in target-architecture.md)

```markdown
### Architectural Invariants

INV-001: [category:enforcement] Every API route passes through [auth, rate-limit, logging] enforcement
INV-002: [category:sot] Every data entity has exactly one authoritative writer
INV-003: [category:error-handling] Every error is caught, logged with correlation ID, and transformed before reaching the user
INV-004: [category:validation] No service accesses another service's database directly
INV-005: [category:config] All configuration is externalized — no secrets in source code
```

### 8.2 Machine-Readable (architecture-invariants.json)

```json
[
  {
    "id": "INV-001",
    "category": "enforcement",
    "scope": "all API routes",
    "surface": ["request/response"],
    "rule": "Every API route passes through auth, rate-limit, and logging enforcement",
    "enforcement": "Framework middleware stack — all routes registered through central router",
    "exceptions": ["GET /health", "GET /metrics"],
    "verification": "Grep for route registrations not using the central router; check middleware stack completeness",
    "linked_user_stories": ["US-1", "US-3"],
    "linked_tests": ["TC-INV-001"]
  }
]
```

**Rules:**
- Each invariant must reference a concern category
- Each invariant must be verifiable against source code (not subjective)
- Minimum 1 invariant per in-scope concern category
- Invariants are append-only during the session — to remove one, add a "reversed" Decision Journal entry
- Each invariant must declare which execution surfaces it applies to

### 8.3 Invariant-Derived Tests

For each invariant, append at least one test to `tests-pseudo.md`:

```markdown
## Invariant Tests (Phase 4)

### TC-INV-001: All API routes have enforcement
given: list of all registered routes
when: checking each route's enforcement chain
then: every route (except /health, /metrics) has [auth, rate-limit, logging]
assert: no route bypasses enforcement without being in the exception list
Schema refs: route registration, middleware config
```

This is a direct append to the canonical `tests-pseudo.md` from Phase 2, not a separate file.

---

## 9. Step 9: Debate the Architecture

Run architecture-specific critique rounds:

```bash
cat specs/<slug>/target-architecture.md | \
  uv run python ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --models MODEL_LIST --doc-type architecture --round N \
  --context specs/<slug>/spec-draft-latest.md \
  $CONTEXT_FLAGS
```

**Debate focus areas:**
- Are all cross-cutting concerns addressed for each execution surface?
- Do invariants cover the most critical architectural boundaries?
- Are enforcement points complete and framework-appropriate?
- Are validation boundaries clear and non-overlapping?
- Is the SoT declaration consistent (no entity with two writers)?
- Do concern interactions have documented resolution?

Continue until convergence.

---

## 10. Step 10: Dry-Run Verification (Gate)

**Run at least one dry-run per relevant execution surface**, not just one user flow.

### 10.1 Request/Response Dry-Run

Walk the most complex request flow:
- Which component handles the request?
- What enforcement points does it pass through? In what order?
- What data is fetched, by whom, via what mechanism?
- What state is created?
- Where does validation happen? Duplicated?
- Is there exactly one SoT for each data entity?
- If two users hit this endpoint simultaneously, what happens?
- What happens on error? Does the error pipeline produce a useful response?
- Can we trace this request from entry to response?
- Does this flow violate any invariant?

### 10.2 Background/Async Dry-Run (if applicable)

Walk a background job flow:
- How is the job enqueued? What triggers it?
- What enforcement applies? (often less than request handlers — document the gap)
- What happens if the job fails? Retry? Dead letter? Alert?
- Is the job idempotent? What happens on duplicate execution?
- Can we observe job progress and failures?

### 10.3 Startup/Migration Dry-Run (if applicable)

Walk the startup or migration flow:
- What happens on first deploy?
- What happens on schema migration? (zero-downtime?)
- What configuration is required before the app starts?
- What happens if config is missing?

### 10.4 Mode-Aware Dry-Run Scoping

**Greenfield:** Run all applicable surface dry-runs.
**Brownfield Feature:** Run dry-runs for surfaces the feature touches. Focus on the delta — how does the new feature change the existing flow?
**Brownfield Debug:** Run dry-run for the bug's traversal path only. Focus on: "does the fix close the gap? Could the bug recur on a different path?"

**The dry-run is the proof the architecture is complete.** If gaps found: revise architecture, re-debate the change.

**[GATE] Mark "Dry-run verification" completed before proceeding to Decision Journal.**

---

## 11. Step 11: Record Decisions

Log all architecture decisions to the Decision Journal in the session detail file.

**Decision Journal schema:**
```json
{
  "decision_journal": [
    {
      "entry_id": "dj-YYYYMMDD-<6 char random>",
      "time": "ISO8601",
      "phase": "target-architecture",
      "topic": "enforcement-pattern",
      "decision": "adopt",
      "choice": "FastAPI dependency injection for auth enforcement",
      "rationale": "Framework-native, prevents bypass, testable",
      "surfaces": ["request/response"],
      "alternatives_considered": ["custom middleware stack", "decorator pattern"],
      "revisit_trigger": "If background jobs need the same enforcement",
      "reverses_entry_id": null
    }
  ]
}
```

**Decision types:** `adopt`, `reject`, `defer`, `skip`, `reversed`
**Rules:** Append-only. `reversed` entries must set `reverses_entry_id`.

---

## 12. Brownfield Feature Flow

Replaces greenfield Steps 4-8 with blast-zone-scoped versions. Steps 1-3 (scale, mode, framework profile) and Steps 9-11 (debate, dry-run, journal) are shared.

### 12.1 Read Blast Zone Architecture

1. Load `.architecture/primer.md` for system context
2. Load component docs for blast zone files
3. List `now`/`next` concerns from `manifest.json`
4. List `warning`/`error` patterns from `manifest.json`

### 12.2 Trace Request Paths

For each affected entry point:
1. Map the enforcement chain from entry to handler to response
2. Identify which concerns are touched
3. Note where the feature adds new steps

### 12.3 Assess Cross-Cutting Fitness

| Concern | Assessment |
|---------|-----------|
| Enforcement points | adequate / needs extension / missing / conflicts |
| Error handling | adequate / needs extension / missing / conflicts |
| Validation boundaries | adequate / needs extension / missing / conflicts |
| Source of truth | adequate / new entity needed / conflicts |
| Observability | adequate / needs extension / missing |
| Caching | adequate / new cache needed / invalidation change needed |
| Configuration | adequate / new config needed / externalization needed |

Only concerns NOT marked "adequate" proceed to Step 12.4.

**Existing debt flag:** If a concern is adequate for THIS feature but has a `now` severity concern in `manifest.json`, note: "adequate for this feature, but existing CON-XXX affects this area. This feature does not make it worse / does make it worse because [reason]."

### 12.4 Draft Architecture Additions

Additions ONLY for in-scope concerns. Must be compatible with existing architecture — conflicts surfaced in debate.

### 12.5 Update Invariants

Add invariants for new boundaries. Check existing invariants still hold.

---

## 13. Brownfield Debug Flow

Replaces greenfield Steps 4-8 with diagnosis-focused versions.

### 13.1 Identify the Failed Layer

| Symptom | Failed Concern |
|---------|---------------|
| "Auth bug in 13 routes" | Enforcement gap (not centralized) |
| "Invalid data in database" | Validation boundary gap |
| "Two systems disagree on state" | SoT violation |
| "Can't debug production issue" | Observability gap |
| "Stale data shown to users" | Caching / invalidation failure |
| "Config works in dev, fails in prod" | Configuration management gap |
| "Error swallowed silently" | Error handling pipeline gap |
| "Race condition / lost updates" | Concurrency control gap |

### 13.2 Local Fix vs Systemic Fix Decision

1. **Count affected instances.** 1 → likely local. 4+ → likely systemic.
2. **"New developer" test.** Could a new dev hit the same bug? Yes → systemic.
3. **"3 lines" test.** Is the fix "add the same 3 lines everywhere"? Yes → centralize.

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

### 13.3 Design or Verify

**Systemic fix:** Design the architectural change for affected concern(s).
**Local fix:** Verify existing architecture is sound — bug is in application code, not architecture.

### 13.4 Check Invariant Coverage

- **Invariant exists but violated:** Add enforcement mechanism.
- **No invariant exists:** Add one that would catch this class of bug.

---

## 14. Outputs

All modes produce:
- `specs/<slug>/target-architecture.md` (human-readable, concern-category tagged)
- `specs/<slug>/architecture-invariants.json` (machine-readable)
- Decision Journal entries in session detail file
- Architecture taxonomy in session detail file
- Additive test cases in `tests-pseudo.md`

### Completion Criteria

- All in-scope dimensions decided with rationale
- All in-scope cross-cutting concerns assessed with decision and surface declaration
- Concern interactions checklist completed
- At least one dry-run per relevant execution surface completed without gaps
- Architecture debated through at least one converged round
- Invariants defined in both markdown and JSON formats
- Invariant-derived tests appended to tests-pseudo.md
- Decision Journal records each decision with surfaces and alternatives

### Phase Transition

**Detail file** (`sessions/<id>.json`):
- Set `current_phase: "gauntlet"`
- Set `target_architecture_path` to architecture doc path
- Append journey event

**Pointer file** (`session-state.json`):
- Update `current_phase`, `current_step`, `next_action`, `updated_at`

---

## 15. Interaction with Other Phases

### Phase 2 (Roadmap)

Phase 4 invariant-derived tests are appended DIRECTLY to the canonical `tests-pseudo.md`. This is not a suggestion — it is a required step (TodoWrite item "Append invariant-derived tests").

### Phase 5 (Gauntlet)

Gauntlet adversaries receive the invariant list + framework profile as context:
- **BURN:** Challenge observability invariants — "if INV-005 fails, how do I know?"
- **PARA:** Challenge enforcement invariants — "can INV-001 be bypassed? What about background jobs?"
- **LAZY:** Challenge enforcement mechanism — "can I accidentally skip INV-001?"
- **COMP:** Challenge SoT invariants — "does INV-002 conflict with existing patterns?"

### Phase 7 (Execution)

Execution plan tasks reference invariants:
- Each task notes which invariants it must satisfy
- High-risk tasks (touching 3+ invariants) get `test-first` strategy
- Architecture Spine (Wave 0) derives from invariant enforcement tasks

### Downstream Tools

**`/mapcodebase`:** Consumes `architecture-invariants.json` to verify against source. Violations surface as concerns.
**`/diagnosecodebase`:** Checks invariants during diagnosis. Missing enforcement becomes a finding.

These integrations are FUTURE work — this spec defines the format for downstream consumption.