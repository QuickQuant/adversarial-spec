# Phase 4: Target Architecture — Spec Draft v3

> Round 2 synthesis: Gemini agreed. GPT-5.4 raised 5 issues: framework profile depth, 2 missing concerns (Identity/AuthZ, Data Access/Boundaries), invariant lifecycle, dry-run archetypes. All accepted. Concern count: 7→9.

## Overview

Phase 4 defines shared architecture rules after spec debate converges and before the gauntlet. It operates in three modes (`skip`, `lightweight`, `full`) with three context types (`greenfield`, `brownfield-feature`, `brownfield-debug`).

**Artifacts by phase_mode:**

| Mode | target-architecture.md | architecture-invariants.json | Debate | Dry-run | tests-pseudo.md |
|------|----------------------|----------------------------|--------|---------|-----------------|
| `skip` | Stub (scale rationale only) | Empty array | No | No | No additions |
| `lightweight` | Abbreviated (in-scope concerns only) | Active invariants | No | Yes (1 per surface) | Invariant tests |
| `full` | Complete | Active invariants | Yes | Yes (read+write per surface) | Invariant tests |

---

## 1. TodoWrite (Entry Point)

```
TodoWrite([
  {content: "Scale check — assess phase_mode [GATE]", status: "in_progress", activeForm: "Assessing architecture need"},
  {content: "Detect context mode (greenfield/brownfield-feature/brownfield-debug)", status: "pending", activeForm: "Detecting context mode"},
  {content: "Declare framework profile and execution surfaces", status: "pending", activeForm: "Declaring framework profile"},
  {content: "Categorize application and select dimensions", status: "pending", activeForm: "Categorizing application"},
  {content: "Assess cross-cutting concerns (9 categories)", status: "pending", activeForm: "Assessing cross-cutting concerns"},
  {content: "Research best practices per dimension + concern", status: "pending", activeForm: "Researching best practices"},
  {content: "Draft target-architecture.md", status: "pending", activeForm: "Drafting target architecture"},
  {content: "Define architectural invariants (markdown + JSON)", status: "pending", activeForm: "Defining invariants"},
  {content: "Append invariant-derived tests to tests-pseudo.md", status: "pending", activeForm: "Adding invariant tests"},
  {content: "Debate architecture (full mode only)", status: "pending", activeForm: "Debating architecture"},
  {content: "Dry-run verification — read+write per surface [GATE]", status: "pending", activeForm: "Running dry-run verification"},
  {content: "Record decisions in Decision Journal", status: "pending", activeForm: "Recording decisions"},
])
```

**Prerequisites:** Spec debate converged. Roadmap with user stories and Goals/Non-Goals exists.

**Inputs:** Converged spec, roadmap, `.architecture/manifest.json` (optional), framework docs, gemini-bundle findings (optional).

---

## 2. Step 1: Scale Check (Gate)

```
Scale Assessment
───────────────────────────────────────
Spec scope: [user story count]
Codebase: [greenfield / existing with N files]
Stack complexity: [single runtime / multi-service]
Cross-cutting touch: [auth, persistence, caching, async,
  config, public API, shared contracts]

Phase mode: [skip | lightweight | full]
```

| Mode | Criteria |
|------|----------|
| `skip` | <3 user stories AND single-file scope AND no cross-cutting concern touched |
| `lightweight` | 3-5 stories, single runtime, ≤1 cross-cutting concern, no external integrations |
| `full` | Multi-runtime, external integrations, 2+ cross-cutting concerns, or failure could cause user-visible inconsistency |

If `skip`: log Decision Journal entry, write stub artifacts, transition to gauntlet.

**[GATE] Mark completed. If skip: mark all remaining items completed.**

---

## 3. Step 2: Context Mode Detection

| Mode | Trigger | Scope |
|------|---------|-------|
| **Greenfield** | No existing codebase or `blast_zone` references only new files | Whole system |
| **Brownfield Feature** | Adding/improving feature in existing codebase | Blast zone + touched concerns |
| **Brownfield Debug** | Fixing a bug or architecture failure | Bug's traversal path |

Record the detected mode and proceed. User can override if incorrect.

**Brownfield Feature scope:** Blast zone (files to modify + imports/exports) + any of the 9 concerns the feature touches. Concerns not touched are noted "not affected" with one-line rationale.

**Existing debt rule (brownfield only):** If a concern is in scope AND has a `now` severity concern in `manifest.json`, flag whether the new feature makes the debt worse or not. The assessment does NOT require fixing existing debt, but MUST flag reinforcement of known anti-patterns.

**Brownfield Debug scope:** Bug's traversal path from entry through enforcement, validation, data layer, and response.

---

## 4. Step 3: Framework Profile and Execution Surfaces

### 4.1 Framework Capability Profile

```json
{
  "framework_profile": {
    "category": "web-app | api-service | cli | library | data-pipeline | mobile | other",
    "framework": "Next.js App Router | FastAPI | Express 5 | Django | Rails | ...",
    "framework_version": "15.x | 0.115+ | 5.x | 5.2 | 8.x | ...",
    "runtime": "node | edge | python | ruby | jvm | mixed",
    "deployment_target": "serverful | serverless | edge | mobile-store | cli-local | mixed",
    "feature_flags": ["cacheComponents", "serverActions", "ppr", "..."],
    "enforcement_model": "summary of how the framework enforces cross-cutting concerns"
  }
}
```

**Why version matters:** The same framework can have fundamentally different architecture patterns across versions (e.g., Next.js caching model changed between 14 and 15; FastAPI's `Depends` behavior differs from middleware). Prescribing patterns for the wrong version causes bugs.

### 4.2 Execution Surfaces

| Surface | Examples |
|---------|---------|
| Request/Response | HTTP handlers, API endpoints, GraphQL resolvers |
| Mutation entrypoints | Server actions, form handlers, RPC calls |
| Background jobs | Queue workers, Celery/SQS/Sidekiq tasks |
| Scheduled work | Cron jobs, periodic tasks |
| Startup/Build/Migration | DB migrations, build scripts, initialization |
| Client runtime | Browser JS, React components, Stimulus controllers |
| Webhooks | Incoming webhook handlers |
| Outbound integrations | API client calls, third-party service connections |

Every concern assessed in Step 5 must declare which surfaces it applies to.

---

## 5. Step 4: Categorize the Application

Classify along dimensions relevant to the project type.

**Web apps:** Rendering, routing/layout model, navigation, data freshness, state management, multi-page sharing, background processing, i18n, DB migrations, testing architecture.

**APIs:** Transport, service composition, data layer, DB migrations, scaling, background processing, deployment strategy.

**CLIs:** Execution model, state management, concurrency, I/O model, config precedence, testing strategy.

**Libraries:** API surface, error handling, extensibility, observability hooks, config points, testing support.

**Data pipelines:** Orchestration, schema evolution, idempotency, backfill strategy, monitoring.

**Mobile:** Offline-first, sync strategy, push notifications, deep linking, app lifecycle, i18n.

Each dimension decision links to roadmap Goals, relevant user stories, and NFRs where applicable.

---

## 6. Step 5: Cross-Cutting Concerns Assessment

**9 mandatory concern categories.** For each in-scope concern:
1. Decision for this project
2. Execution surfaces it applies to
3. Framework-native primitive (if any) + whether it's sufficient (`default accepted`, `default overridden`, `custom pattern`)
4. Rationale with source references
5. Alternative considered
6. Implementation sketch
7. Failure mode prevented

### Concern 1: Identity, Session, and Authorization

Define the authn mechanism, session/token model, authorization model, and how identity propagates across surfaces (requests, background jobs, webhooks, server-side mutations).

**Questions:**
- What authentication mechanism? (session cookies, JWT, API keys, OAuth)
- What session strategy? (stateless JWT, server-side sessions, hybrid)
- What authorization model? (RBAC, ABAC, per-resource, middleware-enforced)
- How does identity propagate to background jobs and webhooks?
- What happens when auth fails? (redirect, 401, 403)

### Concern 2: Data Access, State, and Component Boundaries

Define where reads happen, where mutations happen, who owns invalidation/revalidation, and the server/client/shared state boundaries.

**Questions:**
- Where do reads happen? (server components, API calls, direct DB, cache)
- Where do mutations happen? (server actions, API endpoints, direct DB)
- Who owns invalidation after a mutation? (framework revalidation, manual cache bust, event-driven)
- What are the server/client component boundaries? (which components can access which data)
- How is state managed? (server state, URL state, client state, shared state)
- What cross-route data sharing rules exist?

### Concern 3: Enforcement Points

Define how cross-cutting concerns (auth, rate-limiting, logging, validation) are enforced. Use the framework's native mechanism.

**Questions:**
- What is the framework's enforcement mechanism? (middleware, dependencies, callbacks, decorators)
- What enforcement runs on each execution surface?
- Can a developer add an endpoint and accidentally skip enforcement?
- Is enforcement automatic (framework-level) or manual (convention)?
- What bypass rules exist? (health checks, metrics)

**Framework guidance:** Express=ordered middleware, FastAPI=dependency injection, Next.js=`middleware.ts`+layouts, Django=MIDDLEWARE setting, Rails=`before_action`.

### Concern 4: Error Handling Pipeline

Define the multi-stage error transform: raw→logged→user-facing. Require framework error model decisions BEFORE custom pipelines.

**Questions:**
- What is the framework's native error model?
- Is the default sufficient or needs extension?
- Where are errors caught? (per-handler, enforcement layer, global)
- What gets logged vs what the user sees?
- Error response format? (JSON envelope, HTTP status, error codes)
- How do background job errors surface? (dead letter, alert, retry-then-alert)

### Concern 5: Validation Boundaries

Define what each layer validates, preventing gaps and unintentional duplication.

**Questions:**
- Transport layer: request shape, auth token presence
- Service layer: business rules, authorization
- Domain layer: invariants, entity constraints
- Persistence layer: schema constraints, referential integrity
- Intentional duplication documented?

### Concern 6: Source of Truth and Concurrency

Declare the single authoritative writer per data entity, staleness SLA, and concurrent write resolution.

**Questions:**
- For each entity: who writes it? (one answer)
- Read copies? Max acceptable staleness?
- Concurrent write resolution? (optimistic locking, pessimistic, atomic, CRDT, last-write-wins)
- How are SoT violations detected?

### Concern 7: Observability

Define structured logging, trace propagation, and SLO metrics.

**Questions:**
- Required log fields? (timestamp, correlation ID, service, level)
- Trace propagation across boundaries?
- SLOs and metrics?
- Background job visibility? (queue depth, failure rate, dead letter count)
- 2am failure detection path?

### Concern 8: Caching

Define cache strategy. Evaluate framework-native cache controls FIRST.

**Questions:**
- Framework-native cache behavior? (sufficient or needs extension)
- Cache locations? (in-memory, Redis, CDN, browser, service worker)
- TTL per cached item?
- Invalidation triggers? (TTL, event-driven, framework API like `revalidatePath`)
- Read-your-own-writes guarantee?
- Cache-source disagreement handling?

### Concern 9: Configuration Management

Define externalization, secrets, and feature flags.

**Questions:**
- What's externalized vs hardcoded?
- Secrets management? (env vars, secrets manager, vault)
- Feature flag system?
- Config precedence? (env > file > default)
- Hot-reloadable or requires restart?

### Concern Interactions Checklist

After assessing all concerns, verify these known interaction points:

| Interaction | Check |
|-------------|-------|
| Identity + Enforcement | Auth enforcement runs before or after input validation? |
| Mutation + Cache | Mutation triggers invalidation/revalidation? Path documented? |
| Cache + SoT | Stale cache temporarily violates SoT? Max inconsistency window? |
| Error handling + Observability | Caught-and-handled errors logged or silent? |
| Enforcement + Background | Background jobs have same enforcement as requests? Gap documented? |
| Config + Cache | Config change (feature flag) invalidates caches? |
| Validation + Error handling | Validation failure produces useful error response? |
| Identity + Background | Background jobs have identity/context? How propagated? |

---

## 7. Steps 6-7: Research and Draft

### Research Rules

- Check framework-native primitive FIRST
- Record: `default accepted`, `default overridden`, or `custom pattern`
- Official docs required. Community/template source only when overriding defaults or docs are silent.
- Research must match declared framework version and runtime.

### Draft Format

Each section in `specs/<slug>/target-architecture.md`:

```markdown
### [Concern or Dimension Name]
**Decision:** [pattern chosen]
**Surfaces:** [request/response, background, etc.]
**Goals/NFRs:** [which roadmap Goals this serves]
**User stories:** [which US-X]
**Framework primitive:** [native mechanism, version, "default accepted/overridden/custom"]
**Rationale:** [with sources]
**Alternative considered:** [what else was evaluated]
**Failure mode prevented:** [what goes wrong without this]
**Implementation sketch:** [code/structure]
**Invariant refs:** [INV-XXX]
**Test hook:** [test to add in tests-pseudo.md]
```

---

## 8. Step 8: Architectural Invariants

### 8.1 Human-Readable (in target-architecture.md)

```markdown
### Architectural Invariants

INV-001: [category:enforcement] Every API route passes through [auth, rate-limit, logging] enforcement
INV-002: [category:sot] Every data entity has exactly one authoritative writer
INV-003: [category:error-handling] Every error is caught, logged with correlation ID, and transformed
INV-004: [category:validation] No service accesses another service's persistence directly
INV-005: [category:config] All configuration is externalized — no secrets in source code
```

### 8.2 Machine-Readable (architecture-invariants.json)

```json
[
  {
    "id": "INV-001",
    "status": "active",
    "category": "enforcement",
    "surfaces": ["request/response"],
    "rule": "Every protected route passes through auth, rate-limit, and logging enforcement",
    "enforcement": "Framework middleware stack — all routes via central router",
    "exceptions": ["GET /health", "GET /metrics"],
    "verification_kind": "static",
    "verification": "Grep for route registrations not using central router",
    "linked_user_stories": ["US-1", "US-3"],
    "linked_goals": ["G-2"],
    "linked_tests": ["TC-INV-001"],
    "supersedes": null,
    "superseded_by": null
  }
]
```

**Rules:**
- Minimum 1 active invariant per in-scope concern
- Each invariant is verifiable (`static` = source grep, `dynamic` = runtime check, `manual` = review)
- Reversed invariants: set `status: "reversed"`, set `superseded_by` to replacement ID
- Downstream tools consume only `status: "active"` invariants
- Append-only during session — to reverse, add Decision Journal entry + new invariant

### 8.3 Invariant-Derived Tests

Append to canonical `tests-pseudo.md`:

```markdown
## Invariant Tests (Phase 4)

### TC-INV-001: All API routes have enforcement
given: list of all registered routes
when: checking each route's enforcement chain
then: every route (except exceptions) has [auth, rate-limit, logging]
assert: no route bypasses enforcement without being in exception list
Schema refs: route registration, middleware config
```

---

## 9. Step 9: Debate (full mode only)

```bash
cat specs/<slug>/target-architecture.md | \
  uv run python ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --models MODEL_LIST --doc-type architecture --round N \
  --context specs/<slug>/spec-draft-latest.md $CONTEXT_FLAGS
```

Debate checks: framework fit, surface coverage, boundary composition, invariant verifiability, brownfield compatibility, requirement traceability.

Continue until convergence.

---

## 10. Step 10: Dry-Run Verification (Gate)

### 10.1 Required Dry-Runs

| Surface | Read archetype | Write archetype |
|---------|---------------|-----------------|
| Request/Response | GET flow through enforcement→data→response | POST/PUT flow through enforcement→validation→mutation→response |
| Background | Job reading state/config | Job writing/mutating state |
| Startup/Migration | Config loading, dependency check | Schema migration, initialization |

For each archetype, check: enforcement order, identity/authz, data ownership, component boundaries, validation, cache invalidation, concurrency, observability, invariant compliance.

### 10.2 Mode-Aware Scoping

- **Greenfield (full):** All applicable surface archetypes.
- **Brownfield Feature:** Archetypes for surfaces the feature touches. Focus on the delta.
- **Brownfield Debug:** Bug's traversal path + **one sibling-path check** (a similar flow that was NOT failing, to verify the systemic fix works broadly).

**[GATE] Mark completed before proceeding to Decision Journal.**

---

## 11. Step 11: Record Decisions

Decision Journal schema (unchanged from current Phase 4 + `surfaces` field):

```json
{
  "entry_id": "dj-YYYYMMDD-<6 char>",
  "time": "ISO8601",
  "phase": "target-architecture",
  "topic": "enforcement-pattern",
  "decision": "adopt",
  "choice": "FastAPI dependency injection for auth",
  "surfaces": ["request/response"],
  "rationale": "Framework-native, prevents bypass",
  "alternatives_considered": ["custom middleware", "decorator"],
  "revisit_trigger": "If background jobs need same enforcement",
  "reverses_entry_id": null
}
```

---

## 12. Brownfield Feature Flow

Replaces greenfield Steps 4-8 with blast-zone-scoped versions. Steps 1-3 and 9-11 are shared.

1. **Read blast zone architecture** — primer.md, component docs, concerns, patterns
2. **Trace request paths** — map enforcement chain per affected entry point
3. **Assess cross-cutting fitness** per concern: `adequate | needs extension | missing | conflicts`
   - Only non-adequate concerns proceed to drafting
   - **Existing debt flag:** adequate for this feature but has `now` concern? Note "does not make worse / makes worse because [reason]"
4. **Draft architecture additions** — in-scope concerns only, must be compatible with existing architecture
5. **Update invariants** — add for new boundaries, verify existing still hold

---

## 13. Brownfield Debug Flow

Replaces greenfield Steps 4-8 with diagnosis-focused versions.

1. **Identify failed layer:**

| Symptom | Failed Concern |
|---------|---------------|
| Auth bug in many routes | Enforcement gap |
| Invalid data in DB | Validation boundary gap |
| Systems disagree on state | SoT violation |
| Can't debug production | Observability gap |
| Stale data shown | Caching failure |
| Config works in dev only | Config management gap |
| Error swallowed | Error handling gap |
| Race condition / lost update | Concurrency gap |

2. **Local vs systemic decision:**
   - Count affected instances (1=local, 4+=systemic)
   - "New developer" test (yes=systemic)
   - "3 lines" test (yes=centralize)

3. **Design or verify:**
   - Systemic: design architectural change for affected concern(s)
   - Local: verify architecture is sound, bug is in application code

4. **Check invariant coverage:**
   - Exists but violated → add enforcement mechanism
   - Doesn't exist → add invariant for this bug class

---

## 14. Outputs and Completion

**Artifacts:**
- `specs/<slug>/target-architecture.md` (concern-tagged sections)
- `specs/<slug>/architecture-invariants.json` (machine-readable)
- Decision Journal entries in session detail file
- Architecture taxonomy in session detail file
- Additive tests in `tests-pseudo.md`

**Completion criteria:**
- All in-scope dimensions decided with rationale
- All in-scope concerns assessed with decision + surface declaration
- Concern interactions checklist completed
- Dry-runs pass (read+write per surface, sibling-path for debug)
- Debate converged (full mode)
- Invariants defined in markdown + JSON with `status: active`
- Invariant tests appended to tests-pseudo.md
- Decision Journal complete

---

## 15. Phase Interactions

**Phase 2 (Roadmap):** Invariant tests appended directly to canonical `tests-pseudo.md`.

**Phase 5 (Gauntlet):** Adversaries receive invariant list + framework profile. BURN→observability, PARA→enforcement/auth, LAZY→enforcement bypass, COMP→SoT/brownfield compatibility.

**Phase 7 (Execution):** Tasks reference invariants. High-risk (3+ invariants) → test-first. Architecture Spine (Wave 0) derives from invariant enforcement.

**Downstream:** `/mapcodebase` consumes `architecture-invariants.json` (future). `/diagnosecodebase` checks invariants (future).