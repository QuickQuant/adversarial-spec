# Phase 4: Target Architecture — Spec Draft v6

> Round 5 synthesis: Both models critiqued (Gemini broke 4-round agreement streak). Accepted: Goals/Non-Goals, Getting Started prerequisites, schema-versioned JSON artifacts, blocking error list, deployment strategy, migration plan, testing strategy, observability guidance. All sections scoped to actual deployment target (skill files → `~/.claude/skills/adversarial-spec/`).

## Overview

Phase 4 defines shared architecture rules after spec debate converges and before the gauntlet. It is mode-aware across `phase_mode` (`skip | lightweight | full`) and `context_mode` (`greenfield | brownfield-feature | brownfield-debug`).

**Artifacts by phase_mode:**

| Mode | target-architecture.md | architecture-invariants.json | Debate | Dry-run | tests-pseudo.md |
|------|----------------------|----------------------------|--------|---------|-----------------|
| `skip` | Stub (scale rationale) | `{"schema_version":"1.0","invariants":[]}` | No | No | No additions |
| `lightweight` | In-scope concerns only | Active invariants | No | 1 highest-risk archetype per applicable surface | Invariant tests |
| `full` | Complete with concern x surface matrix | Active invariants | Yes | Read+write per applicable surface | Invariant tests |

## Goals and Non-Goals

**Goals:**
- Produce deterministic architecture artifacts (`target-architecture.md`, `architecture-invariants.json`, decision journal entries, invariant-derived tests) before implementation begins.
- Force explicit coverage of every in-scope concern across every applicable execution surface — no implicit assumptions.
- Support bounded effort through `phase_mode` and `context_mode` so small changes don't require full architecture review.
- Give Phase 5 (Gauntlet) and Phase 7 (Execution) verifiable architecture inputs without requiring code.
- Prevent the failure pattern where implementation begins without explicit decisions on enforcement, data access, error handling, or caching.

**Non-goals:**
- Phase 4 does NOT produce implementation code — only architectural constraints, decisions, and pseudo-tests.
- Phase 4 does NOT replace the Gauntlet (Phase 5) — it establishes the rules the Gauntlet will stress-test.
- Phase 4 does NOT infer missing product goals or user stories — those must exist from the Roadmap (Phase 2).
- Traceability references the target product roadmap, NOT the roadmap of the Phase 4 rewrite itself.

---

## 0. Getting Started and Bootstrap

### Prerequisites

Before entering Phase 4, these must exist:
- **Converged spec** from Phase 3 debate (`specs/<slug>/spec-draft-latest.md`)
- **Roadmap manifest** with goals, non-goals, milestones, and user stories
- **`tests-pseudo.md` path** declared in roadmap or session state
- **For brownfield work:** `.architecture/manifest.json` and `.architecture/primer.md`
- **For `lightweight` and `full`:** declared framework name and version

If any prerequisite is missing, Phase 4 cannot start — see Blocking Errors (Section 15).

### First-Run Orientation

Phase 4 is an AI-agent-driven process. The agent (Claude) executes the steps below using the TodoWrite checklist as its task tracker. The user's role is:
1. Confirm `phase_mode` after the scale check (Step 2)
2. Override `context_mode` if the auto-detection is wrong (Step 3)
3. Review the draft `target-architecture.md` before debate (Step 9)
4. Approve the final architecture before transitioning to gauntlet

**Time to first artifact:**
- Bootstrap record + skeleton `target-architecture.md`: first few minutes
- `skip` completion: under 5 minutes
- `lightweight` draft: under 30 minutes
- `full` draft (excluding debate latency): under 60 minutes

### Bootstrap Contract

Before proceeding past the scale check, record these in the session detail file as `phase4_bootstrap`:

- Spec slug and artifact paths
- `phase_mode` (determined in Step 2)
- `context_mode` (determined in Step 3)
- Framework capability profile (Step 4)
- Applicable execution surfaces (Step 4)
- Roadmap goals, non-goals, user stories
- Canonical `tests-pseudo.md` path

This is a named contract because downstream phases and tools need a deterministic starting state. Bootstrap fields are set progressively — `phase_mode` and `context_mode` are filled first, then profile and surfaces. Fields are written as they become known; the bootstrap is complete when all fields are set.

---

## 1. TodoWrite (Entry Point)

```
TodoWrite([
  {content: "Scale check — assess phase_mode [GATE]", status: "in_progress", activeForm: "Assessing architecture need"},
  {content: "Detect context mode", status: "pending", activeForm: "Detecting context mode"},
  {content: "Bootstrap architecture context", status: "pending", activeForm: "Recording bootstrap context"},
  {content: "Declare framework profile and execution surface map", status: "pending", activeForm: "Declaring framework profile"},
  {content: "Categorize application and select dimensions", status: "pending", activeForm: "Categorizing application"},
  {content: "Assess base concerns + triggered concerns", status: "pending", activeForm: "Assessing concerns"},
  {content: "Emit concern x surface matrix", status: "pending", activeForm: "Building concern-surface matrix"},
  {content: "Research framework-native primitives", status: "pending", activeForm: "Researching best practices"},
  {content: "Draft target-architecture.md", status: "pending", activeForm: "Drafting target architecture"},
  {content: "Define architectural invariants (markdown + JSON)", status: "pending", activeForm: "Defining invariants"},
  {content: "Append invariant-derived tests to tests-pseudo.md", status: "pending", activeForm: "Adding invariant tests"},
  {content: "Debate architecture (full mode only)", status: "pending", activeForm: "Debating architecture"},
  {content: "Dry-run per phase_mode scope [GATE]", status: "pending", activeForm: "Running dry-run verification"},
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

**Risk triggers override story-count heuristics:** trust boundary introduced, irreversible side effects, external write integration, multi-tenant or regulated data, realtime/streaming surface.

**Brownfield exception:** Even a small brownfield-debug may require `full` if the bug crosses multiple surfaces, touches 2+ concerns, or indicates a systemic invariant failure.

If `skip`: stub artifacts, Decision Journal entry with `decision: "skip"`, transition to gauntlet.

**[GATE]**

---

## 3. Context Mode Detection

| Mode | Trigger | Scope |
|------|---------|-------|
| **Greenfield** | No existing codebase or only new files | Whole system |
| **Brownfield Feature** | Adding/improving feature in existing codebase | Blast zone + touched surfaces + touched concerns |
| **Brownfield Debug** | Fixing a bug or architecture failure | Failing traversal path + one sibling path |

Record detected mode in Bootstrap and in the final architecture document header. User can override.

**Brownfield Feature scope:** Blast zone (files to modify + imports/exports) + any concerns the feature touches. Trace entrypoints for **every affected surface**, not only request paths.

**Existing debt rule:** If a concern is in scope AND has a `now` severity in `manifest.json`, flag whether the feature makes the debt worse. Must not reinforce known anti-patterns.

**Brownfield Debug scope:** Bug's full traversal path across all surfaces it touches.

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
      "cache_model": "framework native model + invalidation primitives | N/A",
      "error_model": "native exception/boundary model"
    },
    "enforcement_model": "per-surface enforcement mechanism summary"
  }
}
```

**Rule:** `default accepted` is only valid when the profile explains why the default is sufficient for THIS project at THIS version.

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
| Realtime/Streaming | WebSockets, SSE, streaming responses, subscriptions |

Every concern must declare which surfaces it applies to.

### 4.3 Framework-Specific Guardrails

Known pitfalls that Phase 4 must check when the given framework is in use. Use version-aware language — framework APIs change across major versions.

**Next.js App Router:**
- Route Handlers and Server Actions are separate surfaces — each needs its own auth/validation
- Auth belongs close to the data source (DAL/DTO pattern), not just in proxy/middleware
- Layouts do NOT re-render on every navigation — layout auth is not the sole gate
- Proxy/middleware (naming varies by version: `middleware.ts` pre-16, `proxy.ts` 16+) is for optimistic filtering, not authoritative enforcement
- Cache model: explicitly choose among `updateTag` (read-your-own-writes for mutations), `revalidateTag`, `revalidatePath`, cache opt-out, and `use cache` / Cache Components when enabled
- If Server Actions are used, define when `updateTag` is needed for immediate consistency

**FastAPI:**
- Dependencies/sub-dependencies for request-time auth, authz, and validation
- Middleware for request/response cross-cutting (CORS, tracing, timing, headers)
- Background task bodies do NOT automatically inherit request-time enforcement — document this gap
- WebSocket endpoints are a distinct surface requiring their own auth/error/lifecycle rules
- Exception handlers must be explicitly registered

**Express 5:**
- Central router + ordered middleware stack + terminal error-handling middleware
- Promise-aware error propagation (auto-forwards rejected async in v5)
- Middleware position matters — document required order

**Django:**
- `MIDDLEWARE` setting — class-based, ordered
- Auth boundary separate from validation boundary — document both
- Channels for WebSocket/realtime — distinct surface with own auth model

**Rails:**
- `before_action` callbacks with controller inheritance
- Strong parameters for mass-assignment protection
- ActionCable for WebSocket — separate auth/channel model

---

## 5. Categorize Application

Classify along dimensions relevant to the project type. Each decision links to roadmap goals, user stories, and NFRs.

**Web apps:** rendering/streaming model, route/layout composition, server/client boundaries, mutation model, cache/revalidation model, state strategy (URL/server/client), background processing, i18n, DB migrations, testing architecture.

**APIs:** transport, contract/versioning, service composition, data layer, idempotency/retry, background processing, caching, deployment.

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
- Why default IS or IS NOT sufficient for this project/version
- Rationale with official docs
- Alternative considered
- Failure mode prevented
- Implementation sketch
- Invariant refs + test hook

**Concern 1: Identity, Session, and Authorization**
- Authn mechanism, session strategy, authorization model
- Identity propagation across all surfaces (background jobs, webhooks, realtime)
- Auth failure behavior per surface

**Concern 2: Data Access, State, and Component Boundaries**
- Where reads and mutations happen
- Invalidation/revalidation ownership after mutation
- Server/client component boundaries
- State management strategy
- Cross-route data sharing rules

**Concern 3: Enforcement Points**
- Framework's enforcement mechanism per surface
- Can a developer add an endpoint and skip enforcement?
- Automatic vs manual enforcement
- Bypass rules with explicit exception list

**Concern 4: Error Handling Pipeline**
- Framework's native error model (check FIRST)
- Multi-stage: raw → logged → user-facing
- Per-surface catch points
- Background/scheduled/realtime failure surfacing
- Error response format

**Concern 5: Validation Boundaries**
- Transport → service → domain → persistence
- Intentional duplication documented
- Gaps identified

**Concern 6: Source of Truth and Concurrency**
- Authoritative writer per entity
- Read-copy staleness SLA
- Concurrent write resolution
- SoT violation detection

**Concern 7: Observability**
- Required log fields, trace propagation
- SLOs and metrics
- Background job and realtime connection visibility
- 2am failure detection path

**Concern 8: Caching**
- Framework-native cache behavior FIRST
- Immediate consistency path (e.g., `updateTag` after Server Action)
- Stale-while-revalidate path
- Invalidation owner per mutation
- User-specific cache isolation
- Read-your-own-writes rule
- Cache-source disagreement handling

**Concern 9: Configuration Management**
- Externalization, secrets, feature flags
- Config precedence, hot-reload policy

### 6.2 Triggered Concerns

**Concern 10: Security and Trust Boundaries**
*Triggered for:* `web-app`, `api-service`, `mobile`

- CSRF/CORS/CSP (or platform equivalent)
- Input/output sanitization
- Upload/download rules, host/origin trust
- SSRF prevention when outbound integrations exist
- Tenant/data-partition boundaries when multi-tenant
- Secret exposure prevention
- Public vs private endpoint boundaries
- Client-side auth gating does NOT replace server-side authorization

**Concern 11: Integration Boundaries and Delivery Semantics**
*Triggered when:* `background`, `scheduled`, `webhooks`, or `outbound integrations` surfaces in scope

- Webhook signature verification
- Idempotency keys and deduplication
- Retry policy with backoff
- Timeout budgets per integration
- Circuit breaking / fallback
- Poison message handling
- Exactly-once vs at-least-once documented

**Concern 12: Realtime and Connection Lifecycle**
*Triggered when:* `realtime/streaming` surface in scope

- Handshake auth/authz
- Per-message or per-event authorization
- Disconnect/reconnect semantics
- Ordering and fan-out model
- Backpressure and rate limits
- Observability for long-lived connections

### 6.3 Concern x Surface Matrix (Required for `full`, recommended for `lightweight`)

After assessing all concerns, produce a matrix in `target-architecture.md`:

```markdown
| Concern | Req/Resp | Mutation | Background | Scheduled | Startup | Client | Webhooks | Outbound | Realtime |
|---------|----------|----------|------------|-----------|---------|--------|----------|----------|----------|
| Identity | JWT middleware | Server Action auth | Job context propagation | Service account | N/A | Token refresh | HMAC verify | API key | WS handshake auth |
| Enforcement | Express middleware | Action guard | Manual check | Manual check | N/A | N/A | Signature verify | N/A | Connection auth |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |
```

Each cell names: primitive, enforcement owner, bypass risk, and invariant IDs.

**Why unconditional:** Even frameworks with a single enforcement model can have surfaces that slip through. The matrix forces explicit coverage declaration.

### 6.4 Concern Interactions Checklist

| Interaction | Check |
|-------------|-------|
| Identity + Enforcement | Auth enforcement order relative to validation |
| Mutation + Cache | Mutation triggers invalidation? Immediate consistency path? |
| Cache + SoT | Stale cache window vs SoT SLA |
| Error + Observability | Caught errors logged or silent? |
| Enforcement + Background | Same enforcement as requests? Gap documented? |
| Config + Cache | Feature flag change invalidates caches? |
| Validation + Error | Validation failure → useful error response? |
| Identity + Background | Background jobs have identity? How propagated? |
| Security + Validation | Unsafe input blocked before side effects? |
| Webhook + Delivery | Replay/idempotency path documented? |
| Outbound + Error | Timeout/retry/circuit-break policy? |
| Client + Auth | UI gating does not replace server auth? |
| Cache + Auth | User-specific data not shared via cache? |
| Realtime + Identity | Long-lived connection re-auth on token expiry? |
| Realtime + Observability | Connection duration, message rate, error rate tracked? |

---

## 7. Research and Draft

### Research Rules
- Official framework docs FIRST, matched to declared version
- `default accepted` requires justification for THIS project
- `default overridden` requires both default behavior and override reason
- For every concern, produce a surface-to-primitive mapping (feeds the matrix)

### Draft Format

Each section in `specs/<slug>/target-architecture.md`:

```markdown
### [Concern or Dimension]
**Decision:** [pattern chosen]
**Surfaces:** [which surfaces]
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
{
  "schema_version": "1.0",
  "spec_slug": "<slug>",
  "phase_mode": "full",
  "generated_at": "ISO8601",
  "invariants": [
    {
      "id": "INV-001",
      "status": "active",
      "category": "enforcement",
      "scope": "all protected entrypoints",
      "surfaces": ["request/response", "mutation entrypoints"],
      "rule": "Protected entrypoints require auth, authorization, and audit logging",
      "enforcement": "Framework enforcement mechanism per profile",
      "exceptions": ["GET /health", "GET /metrics"],
      "verification_kind": "static",
      "verification": "Check all route/action registrations for auth enforcement",
      "linked_user_stories": ["US-1", "US-3"],
      "linked_goals": ["G-1"],
      "linked_tests": ["TC-INV-001"],
      "supersedes": null,
      "superseded_by": null
    }
  ]
}
```

**Rules:**
- Minimum 1 active invariant per in-scope concern (`lightweight` and `full`)
- `skip`: `{"schema_version": "1.0", "invariants": []}`
- Each invariant: verifiable (`static` | `dynamic` | `manual`), names surfaces
- Reversed: `status: "reversed"`, `superseded_by` set to replacement
- Downstream tools consume only `status: "active"`

### 8.3 Invariant-Derived Tests

Append directly to canonical `tests-pseudo.md`:

```markdown
## Invariant Tests (Phase 4)

### TC-INV-001: All protected entrypoints have enforcement
given: list of all registered routes, server actions, and webhook handlers
when: checking each for auth enforcement
then: every protected entrypoint (except exceptions) has auth + audit
assert: no protected entrypoint bypasses enforcement
Schema refs: route registration, action registry, webhook handler list
```

---

## 9. Debate (full mode only)

```bash
cat specs/<slug>/target-architecture.md | \
  uv run python ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --models MODEL_LIST --doc-type architecture --round N \
  --context specs/<slug>/spec-draft-latest.md $CONTEXT_FLAGS
```

Debate checks: framework fit (version-accurate), surface completeness (including realtime when applicable), cache consistency semantics, invariant verifiability, brownfield compatibility, requirement traceability, whether any decision merely restates defaults without project-specific justification.

---

## 10. Dry-Run Verification (Gate)

### 10.1 Mode-Aware Scope

| Mode | Dry-run scope |
|------|--------------|
| `skip` | None |
| `lightweight` | 1 highest-risk archetype per applicable surface |
| `full` | Read AND write archetypes per applicable surface |

**Highest-risk selection criteria:** trust boundary crossed, irreversible side effect, async delivery, concurrency exposure, user-visible inconsistency potential. When multiple surfaces qualify, pick the one with the most concern interactions.

### 10.2 Archetypes by Surface

| Surface | Read archetype | Write archetype |
|---------|---------------|-----------------|
| Request/Response | GET through enforcement→data→response | POST/PUT through enforcement→validation→mutation→response |
| Mutation entrypoints | UI/form reads state for mutation | Server action: authz→validate→write→invalidate |
| Background jobs | Job reads config/state | Job mutates with retry/idempotency |
| Scheduled work | Scheduled read/report | Scheduled mutation/backfill |
| Startup/Migration | Config load, dependency check | Schema migration, initialization |
| Client runtime | Page boot, state hydration, auth read | Client event → mutation path |
| Webhooks | Signed webhook parse + verify | Webhook → idempotent side effect |
| Outbound integrations | Read call with timeout/fallback | Write call with retry/backoff/circuit |
| Realtime/Streaming | Connection setup + auth handshake | Message/event → side effect path |

For each archetype verify: enforcement order, auth/authz, boundary ownership, validation, cache behavior (including immediate consistency), concurrency, observability, security/trust boundaries, delivery semantics (if applicable), invariant compliance.

### 10.3 Context-Aware Scoping

- **Greenfield (full):** All applicable surface archetypes.
- **Brownfield Feature:** Archetypes for surfaces the feature touches. Focus on delta.
- **Brownfield Debug:** Failing path + one sibling-path verification.

**[GATE]**

---

## 11. Record Decisions

Decision Journal entries:

```json
{
  "entry_id": "dj-YYYYMMDD-<6 char>",
  "time": "ISO8601",
  "phase": "target-architecture",
  "phase_mode": "full",
  "context_mode": "greenfield",
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
2. **Trace entrypoints per affected surface** — map enforcement chain for each surface touched
3. **Assess concern fitness** per base + triggered concern: `adequate | needs extension | missing | conflicts`
   - Only non-adequate proceed to drafting
   - **Existing debt flag:** adequate but has `now` concern? Flag reinforcement risk.
4. **Produce concern x surface matrix** for blast zone — include existing primitive, adequacy verdict, debt interaction, proposed delta
5. **Draft architecture additions** — in-scope concerns only, compatible with existing
6. **Update invariants** — add for new boundaries, verify existing still hold

---

## 13. Brownfield Debug Flow

1. **Identify failed concern and failed surface**
2. **Local vs systemic decision** — count instances, new-developer test, 3-lines test
3. **Design or verify:**
   - Systemic: centralize fix at correct architectural boundary
   - Local: verify architecture is sound, bug is application code
4. **Dry-run failing path + one sibling path**
5. **Classify invariant gap:** invariant existed but was violated (add enforcement) vs no invariant existed (add one)

---

## 14. Outputs and Completion

**Artifacts (all modes):**
- `specs/<slug>/target-architecture.md`
- `specs/<slug>/architecture-invariants.json`
- Decision Journal entries in session detail file
- Architecture taxonomy in session detail file

### Completion Criteria by Mode

**`skip`:**
- Scale rationale recorded
- Stub target-architecture.md created
- Empty architecture-invariants.json created (with schema_version)
- Decision Journal entry with `decision: "skip"`

**`lightweight`:**
- In-scope concerns decided with rationale
- Active invariants defined and verifiable
- 1 highest-risk archetype per applicable surface completed
- Invariant tests appended to tests-pseudo.md
- Decisions recorded with surfaces

**`full`:**
- All in-scope dimensions decided with rationale
- All in-scope base + triggered concerns assessed
- Concern x surface matrix complete
- Concern interactions checklist completed
- Read+write dry-run per applicable surface completed
- Debate converged
- Active invariants defined, verifiable, in JSON + markdown
- Invariant tests appended to tests-pseudo.md
- Decisions recorded with surfaces, phase_mode, context_mode

---

## 15. Blocking Errors

Phase 4 must halt (not silently degrade to `skip`) when:

| Error | Condition | Resolution |
|-------|-----------|------------|
| Missing roadmap | No roadmap manifest with goals, non-goals, user stories | Return to Phase 2 |
| Missing tests path | `tests_pseudo_path` not set in roadmap or session | Set in roadmap manifest |
| Missing architecture docs (brownfield) | Brownfield work without usable `.architecture/manifest.json` | Run `/mapcodebase` first |
| Unresolved framework (non-skip) | `lightweight` or `full` without declared framework name and version | Resolve before continuing |
| Uncovered concern | In-scope concern has zero applicable surface decisions | Add surface decisions |
| Unverifiable invariant | Invariant has no verification method | Fix or remove with rationale |
| Dry-run failure | Any required archetype fails verification | Fix architecture decisions |

**Rules:**
- No silent fallback from a blocking error to `skip`
- Every blocking error must be surfaced to the user before halting
- Reruns after fixing a blocking error must be idempotent (bootstrap fields merge by key)

---

## 16. Testing Strategy

### Unit-Level Validation
- **Scale check logic:** Verify mode selection for edge cases (exactly 3 stories, single concern at boundary, risk trigger override)
- **Context mode detection:** Verify greenfield/brownfield-feature/brownfield-debug classification against known project shapes
- **Schema validation:** Verify `architecture-invariants.json` and `phase4_bootstrap` conform to their declared schemas — reject malformed output
- **Invariant lifecycle:** Verify `active` → `reversed` with `superseded_by` set, downstream consumers ignore `reversed`

### Integration Tests
- **Greenfield end-to-end:** From scale check through dry-run for a small greenfield spec (3 user stories, 2 surfaces, 2 concerns) — verify all artifacts produced
- **Brownfield feature:** Inject existing `.architecture/` docs, verify blast-zone scoping respects existing architecture, concern fitness assessment runs, debt flags raised
- **Brownfield debug:** Inject a failing traversal path, verify local-vs-systemic decision logic, invariant gap classification

### Failure Tests
- **Each blocking error:** Verify Phase 4 halts (not degrades) when roadmap missing, tests path missing, framework unresolved, etc.
- **Idempotency:** Run Phase 4 twice on same inputs — verify bootstrap merges by key without duplication

### Golden Tests
- **Artifact shape:** Verify `target-architecture.md` has all required headers and `architecture-invariants.json` matches schema
- **Concern x surface matrix:** Verify every in-scope concern has at least one surface decision

---

## 17. Deployment Strategy

Phase 4 deploys as a markdown phase document plus any supporting schema definitions. The deployment target is `~/.claude/skills/adversarial-spec/`.

### Deployment Steps
1. Validate: All schemas and examples in the spec are internally consistent
2. Smoke-run: Execute one greenfield and one brownfield scenario against the new phase doc
3. Copy: `cp skills/adversarial-spec/phases/04-target-architecture.md ~/.claude/skills/adversarial-spec/phases/`
4. Update cross-references: Verify `02-roadmap.md`, `05-gauntlet.md`, and `07-execution.md` reference the correct section numbers and artifact names
5. Verify: Diff deployed files against source to confirm match

### Rollback
- The previous `04-target-architecture.md` is preserved in git history
- Rollback: `git show HEAD~1:skills/adversarial-spec/phases/04-target-architecture.md > ~/.claude/skills/adversarial-spec/phases/04-target-architecture.md`
- No database state, no running services — rollback is a single file restore

---

## 18. Migration Plan

### Legacy Session Compatibility
- Sessions created before this Phase 4 version will not have `phase4_bootstrap` in their session detail file
- On first Phase 4 entry: if `phase4_bootstrap` is absent, create it — do not error
- Legacy `architecture-invariants.json` may be a bare array (no `schema_version` wrapper) — readers must accept both formats; new writers always emit schema `1.0`

### Artifact Path Normalization
- If an existing session stores an obsolete artifact root or roadmap path, normalize into the bootstrap record
- Preserve the old value in the decision journal as a `migration` entry

### Cross-Reference Updates
- Phase 5 (`05-gauntlet.md`): Update adversary briefing inputs to reference concern x surface matrix and triggered concerns
- Phase 7 (`07-execution.md`): Update task generation to reference invariant IDs and surface scope
- Phase 2 (`02-roadmap.md`): Update tests-pseudo integration to reference invariant-derived tests section

---

## 19. Observability

Phase 4 is an AI-agent-driven process, not a running service. Observability means producing enough evidence for a fresh agent (or human) to understand what happened and resume.

### Required Evidence per Run
- `phase4_bootstrap` record in session detail file (progressive, shows what was resolved and when)
- Decision journal entries (append-only, shows every architectural choice with rationale)
- Journey log entries for phase transitions and gate completions
- Dry-run results (pass/fail per archetype with failure details)

### Debugging a Failed Run
- Read `phase4_bootstrap.status` — shows how far the run progressed
- Check blocking errors — any halt is recorded in session state with the error condition
- Read decision journal — shows which concerns were assessed before failure
- A failed Phase 4 run must leave enough session state for a fresh agent to resume without re-reading source files or re-running completed steps

---

## 20. Phase Interactions

**Phase 2 (Roadmap):** Invariant tests appended to canonical `tests-pseudo.md`. Architecture traces to roadmap goals, user stories, and existing tests.

**Phase 5 (Gauntlet):** Adversaries receive framework profile, surface map, concern x surface matrix, invariant set, and triggered concerns. BURN→observability+realtime, PARA→enforcement/auth/security/trust, LAZY→enforcement bypass, COMP→SoT/brownfield compatibility.

**Phase 7 (Execution):** Tasks reference invariants. High-risk (3+ invariants) → test-first. Architecture Spine (Wave 0) derives from invariant enforcement tasks. Multi-surface tasks flagged for extra review.

**Downstream:** `/mapcodebase` and `/diagnosecodebase` consume `architecture-invariants.json` (active only + surface scope). Future work.
