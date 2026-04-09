# Phase 4: Target Architecture — Spec Draft v4

> Round 3 synthesis: Gemini agreed (3rd round). GPT-5.4: surface consistency fix, framework subprofiles, triggered concerns (Security/Trust + Integration Delivery), accurate framework guardrails.

## Overview

Phase 4 defines shared architecture rules after spec debate converges and before the gauntlet. Three `phase_mode`s (`skip`, `lightweight`, `full`) and three `context_mode`s (`greenfield`, `brownfield-feature`, `brownfield-debug`).

**Artifacts by phase_mode:**

| Mode | target-architecture.md | architecture-invariants.json | Debate | Dry-run | tests-pseudo.md |
|------|----------------------|----------------------------|--------|---------|-----------------|
| `skip` | Stub (scale rationale) | Empty array | No | No | No additions |
| `lightweight` | In-scope concerns only | Active invariants | No | 1 archetype per applicable surface | Invariant tests |
| `full` | Complete | Active invariants | Yes | Read+write per applicable surface | Invariant tests |

---

## 1. TodoWrite (Entry Point)

```
TodoWrite([
  {content: "Scale check — assess phase_mode [GATE]", status: "in_progress", activeForm: "Assessing architecture need"},
  {content: "Detect context mode", status: "pending", activeForm: "Detecting context mode"},
  {content: "Declare framework profile and execution surface map", status: "pending", activeForm: "Declaring framework profile"},
  {content: "Categorize application and select dimensions", status: "pending", activeForm: "Categorizing application"},
  {content: "Assess base concerns + triggered concerns", status: "pending", activeForm: "Assessing concerns"},
  {content: "Research framework-native primitives", status: "pending", activeForm: "Researching best practices"},
  {content: "Draft target-architecture.md", status: "pending", activeForm: "Drafting target architecture"},
  {content: "Define architectural invariants (markdown + JSON)", status: "pending", activeForm: "Defining invariants"},
  {content: "Append invariant-derived tests to tests-pseudo.md", status: "pending", activeForm: "Adding invariant tests"},
  {content: "Debate architecture (full mode only)", status: "pending", activeForm: "Debating architecture"},
  {content: "Dry-run every applicable surface [GATE]", status: "pending", activeForm: "Running dry-run verification"},
  {content: "Record decisions in Decision Journal", status: "pending", activeForm: "Recording decisions"},
])
```

**Prerequisites:** Spec debate converged. Roadmap with goals, non-goals, user stories exists.

**Inputs:** Converged spec, roadmap, `.architecture/manifest.json` (optional), framework docs, gemini-bundle findings (optional).

---

## 2. Scale Check (Gate)

| Mode | Criteria |
|------|----------|
| `skip` | <3 user stories AND single-file scope AND no cross-cutting concern touched |
| `lightweight` | 3-5 stories, single runtime, ≤1 concern, no external integrations |
| `full` | Multi-runtime, external integrations, 2+ concerns, or user-visible inconsistency risk |

**Brownfield exception:** Even a small brownfield-debug may require `full` if the bug crosses multiple surfaces, touches 2+ concerns, or indicates a systemic invariant failure.

If `skip`: stub artifacts, Decision Journal entry, transition to gauntlet.

**[GATE]**

---

## 3. Context Mode Detection

| Mode | Trigger | Scope |
|------|---------|-------|
| **Greenfield** | No existing codebase or only new files | Whole system |
| **Brownfield Feature** | Adding/improving feature in existing codebase | Blast zone + touched surfaces + touched concerns |
| **Brownfield Debug** | Fixing a bug or architecture failure | Failing traversal path + one sibling path |

Record detected mode and proceed. User can override.

**Brownfield Feature scope:** Blast zone (files to modify + imports/exports) + any of the 9+ concerns the feature touches. Trace entrypoints for **every affected surface**, not only request paths. Concerns not touched: "not affected" with one-line rationale.

**Existing debt rule:** If a concern is in scope AND has a `now` severity in `manifest.json`, flag whether the feature makes the debt worse. Must not reinforce known anti-patterns.

**Brownfield Debug scope:** Bug's full traversal path across all surfaces it touches (entry through enforcement, validation, data layer, response/side-effect).

---

## 4. Framework Profile and Execution Surface Map

### 4.1 Framework Capability Profile

```json
{
  "framework_profile": {
    "category": "web-app | api-service | cli | library | data-pipeline | mobile | other",
    "framework": "Next.js App Router | FastAPI | Express 5 | Django | Rails | ...",
    "framework_version": "exact major/minor or constraint",
    "runtime": "node | edge | python | ruby | jvm | mixed",
    "deployment_target": "serverful | serverless | edge | mixed",
    "enabled_features": ["cacheComponents", "serverActions", "ppr", "..."],
    "subprofiles": {
      "rendering_model": "SSR | SSG | RSC+streaming | SPA | hybrid | N/A",
      "data_access_model": "DAL/repository | direct ORM | BFF | service layer | N/A",
      "mutation_model": "server actions | route handlers | RPC | REST | forms | queue | N/A",
      "cache_model": "framework native + invalidation primitives, or N/A",
      "error_model": "native exception/boundary model"
    },
    "enforcement_model": "how auth/validation/logging/rate-limit are enforced per surface"
  }
}
```

**Rule:** `default accepted` is only valid when the profile explains why the default is sufficient for THIS project at THIS version. Stating "default accepted" without justification is a debate target.

### 4.2 Execution Surfaces

| Surface | Examples |
|---------|---------|
| Request/Response | HTTP handlers, API endpoints, GraphQL resolvers |
| Mutation entrypoints | Server Actions, form actions, RPC calls |
| Background jobs | Queue workers, async consumers |
| Scheduled work | Cron, periodic tasks |
| Startup/Build/Migration | Boot, schema migration, initialization |
| Client runtime | Browser JS, React components, native mobile |
| Webhooks | Incoming signed callbacks |
| Outbound integrations | Third-party API/service calls |

Every concern must declare which surfaces it applies to.

### 4.3 Framework-Specific Guardrails

These are known pitfalls that Phase 4 must check when the given framework is in use.

**Next.js App Router:**
- Route Handlers and Server Actions are separate surfaces — each needs its own auth/validation
- Auth belongs close to the data source (DAL/DTO pattern), not just in `middleware.ts` or layouts
- Layouts do NOT re-render on every navigation — do not rely on layout-level auth as the sole gate
- `middleware.ts` is for optimistic filtering (redirects, route protection), not for auth enforcement
- Cache model differs between Cache Components and previous model — document which is in use
- Distinguish `revalidateTag`, `revalidatePath`, and cache opt-out strategies

**FastAPI:**
- Dependencies/sub-dependencies for auth, authz, and request-scoped validation
- Middleware for request/response cross-cutting (CORS, tracing, timing, headers)
- Background tasks bypass request dependencies — document the enforcement gap
- Exception handlers must be explicitly registered

**Express 5:**
- Central router + ordered middleware stack + terminal error-handling middleware
- Promise-aware error propagation (Express 5 auto-forwards rejected async)
- Middleware position matters — document the required order

**Django:**
- `MIDDLEWARE` setting — class-based, ordered
- `@login_required` / permission mixins for view-level auth
- ORM-level validation vs form-level validation — document boundary

**Rails:**
- `before_action` callbacks with controller inheritance
- Strong parameters for mass-assignment protection
- ActiveRecord validations vs controller-level validation — document boundary

---

## 5. Categorize Application

Classify along dimensions relevant to the project type. Each decision links to roadmap goals, user stories, and NFRs.

**Web apps:** rendering/streaming model, route/layout composition, server/client component boundaries, mutation model, cache/revalidation model, state strategy (URL/server/client), background processing, i18n, DB migrations, testing architecture.

**APIs:** transport, contract/versioning, service composition, data layer, idempotency/retry policy, background processing, caching, deployment.

**CLIs:** execution model, config precedence, error model, concurrency, I/O, observability, testing.

**Libraries:** API surface, extension points, error model, observability hooks, config points, compatibility policy, testing support.

**Data pipelines:** orchestration, schema evolution, idempotency, backfill, monitoring.

**Mobile:** offline model, sync strategy, push notifications, deep linking, lifecycle, i18n.

---

## 6. Cross-Cutting Concerns Assessment

### 6.1 Base Concerns (always evaluate when in scope)

For each in-scope concern, produce:
- Decision + surfaces
- Framework primitive + `default accepted | default overridden | custom pattern`
- Why default IS or IS NOT sufficient
- Rationale with official docs
- Alternative considered
- Failure mode prevented
- Implementation sketch
- Invariant refs + test hook

**Concern 1: Identity, Session, and Authorization**
- Authn mechanism (session cookies, JWT, API keys, OAuth)
- Session strategy (stateless, server-side, hybrid)
- Authorization model (RBAC, ABAC, per-resource)
- Identity propagation across surfaces (how do background jobs/webhooks get identity?)
- Auth failure behavior (redirect, 401, 403)

**Concern 2: Data Access, State, and Component Boundaries**
- Where reads happen (server components, API, direct DB, cache)
- Where mutations happen (server actions, API endpoints, queue consumers)
- Who owns invalidation after mutation
- Server/client component boundaries
- State management (server, URL, client, shared)
- Cross-route data sharing rules

**Concern 3: Enforcement Points**
- Framework's native enforcement mechanism per surface
- Can a developer add an endpoint and skip enforcement?
- Automatic (framework-level) vs manual (convention)?
- Bypass rules with explicit exception list

**Concern 4: Error Handling Pipeline**
- Framework's native error model (check FIRST)
- Multi-stage: raw → logged → user-facing
- Per-surface catch points
- Background/scheduled failure surfacing
- Error response format

**Concern 5: Validation Boundaries**
- Transport → service → domain → persistence
- Intentional duplication documented
- Gaps identified

**Concern 6: Source of Truth and Concurrency**
- Authoritative writer per entity (one answer)
- Read-copy staleness SLA
- Concurrent write resolution (optimistic/pessimistic/atomic/CRDT)
- SoT violation detection

**Concern 7: Observability**
- Required log fields
- Trace propagation across boundaries
- SLOs and metrics
- Background job visibility
- 2am failure detection path

**Concern 8: Caching**
- Framework-native cache behavior FIRST
- Cache locations, TTL, invalidation triggers
- Read-your-own-writes guarantee
- Cache-source disagreement handling

**Concern 9: Configuration Management**
- Externalization policy
- Secrets management
- Feature flags
- Config precedence
- Hot-reload vs restart

### 6.2 Triggered Concerns

These are mandatory when their trigger condition is met.

**Concern 10: Security and Trust Boundaries**
*Triggered for:* `web-app`, `api-service`, `mobile`

- CSRF/CORS/CSP (or platform equivalent)
- Input/output sanitization
- Upload/download rules
- Host/origin trust
- Secret exposure prevention
- Public vs private route/endpoint boundaries
- Client-side auth gating does NOT replace server-side authorization

**Concern 11: Integration Boundaries and Delivery Semantics**
*Triggered when:* `background`, `scheduled`, `webhooks`, or `outbound integrations` surfaces are in scope

- Webhook signature verification
- Idempotency keys and deduplication
- Retry policy with backoff
- Timeout budgets per integration
- Circuit breaking / fallback strategy
- Poison message handling
- Exactly-once vs at-least-once assumptions documented

### 6.3 Concern Interactions Checklist

| Interaction | Check |
|-------------|-------|
| Identity + Enforcement | Auth enforcement order relative to validation |
| Mutation + Cache | Mutation triggers invalidation? Path documented? |
| Cache + SoT | Stale cache window vs SoT SLA |
| Error + Observability | Caught errors logged or silent? |
| Enforcement + Background | Same enforcement as requests? Gap documented? |
| Config + Cache | Feature flag change invalidates caches? |
| Validation + Error | Validation failure → useful error response? |
| Identity + Background | Background jobs have identity? How? |
| Security + Validation | Unsafe input blocked before side effects? |
| Webhook + Delivery | Replay/idempotency path documented? |
| Outbound + Error | Timeout/retry/circuit-break policy? |
| Client + Auth | UI gating does not replace server auth? |
| Cache + Auth | User-specific data not shared via cache? |

---

## 7. Research and Draft

### Research Rules
- Official framework docs FIRST, matched to declared version
- `default accepted` requires justification for THIS project
- `default overridden` requires both the default behavior and override reason
- For frameworks with multiple valid primitives, produce a **surface-to-primitive matrix**

### Draft Format

Each section in `specs/<slug>/target-architecture.md`:

```markdown
### [Concern or Dimension]
**Decision:** [pattern chosen]
**Surfaces:** [which surfaces this applies to]
**Goals/NFRs:** [roadmap goals served]
**User stories:** [US-X references]
**Framework primitive:** [native mechanism + version]
**Default status:** [accepted | overridden | custom]
**Why sufficient/insufficient:** [explanation]
**Rationale:** [with official doc sources]
**Alternative considered:** [what else evaluated]
**Failure mode prevented:** [what goes wrong without this]
**Implementation sketch:** [code/structure]
**Invariant refs:** [INV-XXX]
**Test hook:** [test for tests-pseudo.md]
```

---

## 8. Architectural Invariants

### 8.1 Human-Readable (in target-architecture.md)

```markdown
### Architectural Invariants

INV-001: [category:enforcement] Every protected entrypoint passes through auth + audit logging
INV-002: [category:sot] Every data entity has exactly one authoritative writer
INV-003: [category:error-handling] Every error is caught, logged with correlation ID, and transformed
INV-004: [category:validation] No service accesses another service's persistence directly
INV-005: [category:config] All configuration externalized — no secrets in source
```

### 8.2 Machine-Readable (architecture-invariants.json)

```json
[
  {
    "id": "INV-001",
    "status": "active",
    "category": "enforcement",
    "scope": "all protected HTTP entrypoints",
    "surfaces": ["request/response", "mutation entrypoints"],
    "rule": "Protected entrypoints require auth, authorization, and audit logging",
    "enforcement": "Framework dependency injection + central router",
    "exceptions": ["GET /health", "GET /metrics"],
    "verification_kind": "static",
    "verification": "Check all route/action registrations for auth dependency",
    "linked_user_stories": ["US-1", "US-3"],
    "linked_goals": ["G-1"],
    "linked_tests": ["TC-INV-001"],
    "supersedes": null,
    "superseded_by": null
  }
]
```

**Rules:**
- Minimum 1 active invariant per in-scope concern (base + triggered)
- Each invariant verifiable: `static` (source scan), `dynamic` (runtime check), `manual` (review)
- Reversed: set `status: "reversed"`, set `superseded_by` to replacement ID
- Downstream tools consume only `status: "active"`
- Append-only in session — reverse via Decision Journal entry

### 8.3 Invariant-Derived Tests

Append directly to canonical `tests-pseudo.md`:

```markdown
## Invariant Tests (Phase 4)

### TC-INV-001: All protected entrypoints have enforcement
given: list of all registered routes and server actions
when: checking each for auth dependency/middleware
then: every protected entrypoint (except exceptions) has auth + audit
assert: no protected entrypoint bypasses enforcement
Schema refs: route registration, action registry
```

---

## 9. Debate (full mode only)

```bash
cat specs/<slug>/target-architecture.md | \
  uv run python ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --models MODEL_LIST --doc-type architecture --round N \
  --context specs/<slug>/spec-draft-latest.md $CONTEXT_FLAGS
```

Debate checks: framework fit, surface coverage, boundary composition, invariant verifiability, brownfield compatibility, requirement traceability, whether any section merely restates defaults without justification.

---

## 10. Dry-Run Verification (Gate)

**Run read AND write archetypes for every applicable surface.**

| Surface | Read archetype | Write archetype |
|---------|---------------|-----------------|
| Request/Response | GET through enforcement→data→response | POST/PUT through enforcement→validation→mutation→response |
| Mutation entrypoints | UI reads form/state for mutation | Server action: authz→validate→write→invalidate |
| Background jobs | Job reads config/state | Job mutates with retry/idempotency |
| Scheduled work | Scheduled read/report | Scheduled mutation/backfill |
| Startup/Migration | Config load, dependency check | Schema migration, init |
| Client runtime | Page boot, state hydration, auth read | Client event → allowed mutation path |
| Webhooks | Signed webhook parse + verify | Webhook → idempotent side effect |
| Outbound integrations | Read call with timeout/fallback | Write call with retry/backoff/circuit |

For each archetype verify: enforcement order, auth/authz, boundary ownership, validation, cache behavior, concurrency, observability, security/trust boundaries, delivery semantics (if applicable), invariant compliance.

### Mode-Aware Scoping

- **Greenfield (full):** All applicable surface archetypes.
- **Brownfield Feature:** Archetypes for surfaces the feature touches. Focus on delta.
- **Brownfield Debug:** Failing path + one sibling-path verification.

**[GATE]**

---

## 11. Record Decisions

Decision Journal entries include `surfaces` field:

```json
{
  "entry_id": "dj-YYYYMMDD-<6 char>",
  "time": "ISO8601",
  "phase": "target-architecture",
  "topic": "enforcement-pattern",
  "decision": "adopt",
  "choice": "FastAPI dependency injection for auth enforcement",
  "surfaces": ["request/response", "mutation entrypoints"],
  "rationale": "Framework-native, prevents bypass",
  "alternatives_considered": ["custom middleware", "decorator"],
  "revisit_trigger": "If background jobs need same enforcement",
  "reverses_entry_id": null
}
```

---

## 12. Brownfield Feature Flow

Replaces greenfield Steps 5-8 with blast-zone-scoped versions. Steps 1-4 and 9-11 are shared.

1. **Read blast zone architecture** — primer.md, component docs, concerns, patterns
2. **Trace entrypoints per affected surface** — map enforcement chain for each surface touched, not only request paths
3. **Assess concern fitness** per base + triggered concern: `adequate | needs extension | missing | conflicts`
   - Only non-adequate proceed to drafting
   - **Existing debt flag:** adequate but has `now` concern? "Does not make worse / makes worse because [reason]"
4. **Draft architecture additions** — in-scope concerns only, compatible with existing architecture
5. **Update invariants** — add for new boundaries, verify existing still hold

---

## 13. Brownfield Debug Flow

1. **Identify failed concern and failed surface** — which concern broke, on which surface
2. **Local vs systemic decision** — count instances, new-developer test, 3-lines test
3. **Design or verify:**
   - Systemic: centralize fix at correct architectural boundary
   - Local: verify architecture is sound, bug is application code
4. **Dry-run failing path + one sibling path** — verify fix works broadly
5. **Add or tighten invariant** for this bug class

---

## 14. Outputs and Completion

**Artifacts:**
- `specs/<slug>/target-architecture.md` (concern-tagged)
- `specs/<slug>/architecture-invariants.json` (machine-readable)
- Decision Journal entries in session detail file
- Architecture taxonomy in session detail file
- Additive tests in `tests-pseudo.md`

**Completion criteria:**
- All in-scope dimensions decided with rationale
- All in-scope base + triggered concerns assessed
- Every applicable surface dry-run completed (read+write)
- Concern interactions checklist completed
- Debate converged (`full` mode)
- Invariants defined, active, verifiable
- Invariant tests appended to tests-pseudo.md
- Decisions recorded with surfaces

---

## 15. Phase Interactions

**Phase 2 (Roadmap):** Invariant tests appended directly to canonical `tests-pseudo.md`. Architecture must trace to roadmap goals, user stories, and existing tests.

**Phase 5 (Gauntlet):** Adversaries receive framework profile, surface map, invariant set, and triggered concerns as context. BURN→observability, PARA→enforcement/auth/security, LAZY→enforcement bypass, COMP→SoT/brownfield compatibility.

**Phase 7 (Execution):** Tasks reference invariants. High-risk (3+ invariants) → test-first. Architecture Spine (Wave 0) derives from invariant enforcement tasks. Multi-surface tasks flagged for extra review.

**Downstream:** `/mapcodebase` and `/diagnosecodebase` consume `architecture-invariants.json` (active only + surface scope). Future work.
