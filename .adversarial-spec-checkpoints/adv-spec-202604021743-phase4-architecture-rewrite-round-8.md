# Phase 4: Target Architecture — Spec Draft v8

> Round 7 synthesis: Gemini agreed. GPT-5.4: 6 issues — canonical surface IDs, run_fingerprint + idempotency_key for rerun dedup, session mutation contract, deployment/runtime separation (REL_* vs P4_*), lightweight roadmap alignment gate, stale lock handling. All accepted (partially for run input schema and alignment artifact — scoped to what's useful without over-formalizing an agent-driven process).

## Overview

Phase 4 is a file-based, AI-agent-driven state machine that runs after spec debate convergence (Phase 3) and before the gauntlet (Phase 5). It converts a converged product spec into deterministic architecture artifacts. There is no external HTTP API — the normative interfaces are the artifacts and session-state mutations this phase produces.

It is mode-aware across `phase_mode` (`skip | lightweight | full`) and `context_mode` (`greenfield | brownfield_feature | brownfield_debug`).

### Canonical Enums

These enums are normative. All artifacts, schemas, and references must use these exact values.

**`phase_mode`:** `skip | lightweight | full`

**`context_mode`:** `greenfield | brownfield_feature | brownfield_debug`

**`surface_id`:** `request_response | mutation_entrypoint | background_job | scheduled_work | startup_migration | client_runtime | webhook | outbound_integration | realtime_streaming`

**`concern_category`:** `enforcement | sot | error_handling | validation | config | caching | observability | security | integration`

**`bootstrap_status`:** `bootstrapping | drafting | debating | dry_run | blocked | completed`

**`decision_type`:** `adopt | reject | defer | skip | migrate`

**`verification_kind`:** `static | dynamic | manual`

**Artifacts by phase_mode:**

| Mode | target-architecture.md | architecture-invariants.json | Debate | Dry-run | tests-pseudo.md |
|------|----------------------|----------------------------|--------|---------|-----------------|
| `skip` | Stub (scale rationale) | `{"schema_version":"1.0","invariants":[]}` | No | No | No additions |
| `lightweight` | In-scope concerns only | Active invariants | No | 1 highest-risk archetype per applicable surface | Invariant tests (upsert) |
| `full` | Complete with concern x surface matrix | Active invariants | Yes | Read+write per applicable surface | Invariant tests (upsert) |

## Goals and Non-Goals

**Goals:**
- Produce deterministic architecture artifacts (`target-architecture.md`, `architecture-invariants.json`, `dry_run_results`, decision journal entries, invariant-derived tests) before implementation begins.
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
- **For brownfield work:** `.architecture/manifest.json` (schema 2.0) and `.architecture/primer.md`
- **For `lightweight` and `full`:** declared framework name and version
- **Runtime:** Python 3.14+, `uv`, file locking support, git

If any prerequisite is missing, Phase 4 cannot start — see Blocking Errors (Section 15).

### Concurrency Rule

Exactly one Phase 4 writer may mutate a given session at a time. Before writing any artifact or session field, acquire `<session-detail-path>.lock`. Release on completion or error.

**Stale lock handling:** If the lock file exists but the holding process is no longer running (check PID if recorded, or age > 30 minutes), the agent may force-break the lock with a warning logged to the journey. The warning must include the stale lock's age and the action taken.

### First-Run Orientation

Phase 4 is an AI-agent-driven process. The agent (Claude) executes the steps below using the TodoWrite checklist as its task tracker. The user's role is:
1. Confirm `phase_mode` after the scale check (Step 2)
2. Confirm or override `context_mode` after auto-detection (Step 3) — **[GATE]**
3. Review the draft `target-architecture.md` before debate (Step 9)
4. Approve the final architecture before transitioning to gauntlet

**Time to first artifact (p95 targets, excluding external model/doc-fetch latency):**
- Bootstrap record + skeleton `target-architecture.md`: ≤10 seconds
- `skip` completion: ≤5 minutes
- `lightweight` draft: ≤30 minutes
- `full` draft: ≤60 minutes

### Bootstrap Contract (`phase4_bootstrap`)

The bootstrap is a progressively-filled record in the session detail file. It is the deterministic starting state that downstream phases and tools depend on.

**Normative schema:**

```json
{
  "schema_version": "1.0",
  "status": "bootstrapping | drafting | debating | dry_run | blocked | completed",
  "session_id": "string (required)",
  "spec_slug": "string (required)",
  "run_fingerprint": "sha256 (required, see below)",
  "phase_mode": "skip | lightweight | full (required, set at Step 2)",
  "context_mode": "greenfield | brownfield_feature | brownfield_debug (required, set at Step 3)",
  "artifact_paths": {
    "target_architecture": "specs/<slug>/target-architecture.md (required)",
    "invariants": "specs/<slug>/architecture-invariants.json (required)",
    "tests_pseudo": "string (required, from roadmap)",
    "dry_run_results": "specs/<slug>/dry-run-results.json (required for non-skip)"
  },
  "framework_profile": "{} (required for non-skip, set at Step 4)",
  "execution_surfaces": "[] (required for non-skip, set at Step 4)",
  "roadmap_ref": {
    "goals": "[] (required)",
    "non_goals": "[] (required)",
    "user_stories": "[] (required)"
  },
  "current_gate": "string | null (name of current gate step)",
  "blocking_error": "null | BlockingError object (see Section 15)",
  "started_at": "ISO8601 (required)",
  "updated_at": "ISO8601 (required, updated on every write)",
  "completed_at": "ISO8601 | null (set when status=completed)"
}
```

**Status state machine:**

```
bootstrapping → drafting → debating → dry_run → completed
     ↓              ↓          ↓         ↓
   blocked       blocked    blocked   blocked
```

- `bootstrapping`: Steps 0-3 (prerequisites, scale check, context mode, bootstrap fields)
- `drafting`: Steps 4-8 (framework profile, categorize, concerns, research, draft)
- `debating`: Step 9 (debate, full mode only — skip this state for lightweight/skip)
- `dry_run`: Step 10 (dry-run verification)
- `completed`: All gates passed, artifacts written
- `blocked`: Any blocking error — `blocking_error` field contains the details

**Write timing:** Fields are set progressively as steps complete. `status` advances only when the previous state's work is done. `updated_at` is set on every mutation. All writes use temp-file + atomic rename.

**Run fingerprint:** `run_fingerprint = sha256(spec_bytes + roadmap_bytes + phase_mode + context_mode + framework_profile_json)`. Computed at bootstrap, stored in `phase4_bootstrap`. Used by idempotency rules (Section 11, 20) to suppress duplicate entries on rerun.

**Resume behavior:** On re-entry, read `phase4_bootstrap.status` and `current_gate` to determine where to resume. Do not re-run completed steps. Merge new field values by key (existing values preserved unless explicitly overridden). If `run_fingerprint` matches the previous run, idempotency rules apply — duplicate journal entries and journey events are suppressed.

**Roadmap alignment check (prerequisite):** Before proceeding past bootstrap, verify the roadmap is internally consistent:
- Every user story maps to ≥1 goal
- No user story conflicts with a declared non-goal
- If either check fails, raise `P4_UNALIGNED_STORY` (see Section 15)

---

## 1. TodoWrite (Entry Point)

```
TodoWrite([
  {content: "Scale check — assess phase_mode [GATE]", status: "in_progress", activeForm: "Assessing architecture need"},
  {content: "Detect context mode and confirm with user [GATE]", status: "pending", activeForm: "Detecting context mode"},
  {content: "Bootstrap architecture context", status: "pending", activeForm: "Recording bootstrap context"},
  {content: "Declare framework profile and execution surface map", status: "pending", activeForm: "Declaring framework profile"},
  {content: "Categorize application and select dimensions", status: "pending", activeForm: "Categorizing application"},
  {content: "Assess base concerns + triggered concerns", status: "pending", activeForm: "Assessing concerns"},
  {content: "Emit concern x surface matrix", status: "pending", activeForm: "Building concern-surface matrix"},
  {content: "Research framework-native primitives", status: "pending", activeForm: "Researching best practices"},
  {content: "Draft target-architecture.md", status: "pending", activeForm: "Drafting target architecture"},
  {content: "Define architectural invariants (markdown + JSON)", status: "pending", activeForm: "Defining invariants"},
  {content: "Upsert invariant-derived tests to tests-pseudo.md", status: "pending", activeForm: "Upserting invariant tests"},
  {content: "Debate architecture (full mode only)", status: "pending", activeForm: "Debating architecture"},
  {content: "Dry-run per phase_mode scope [GATE]", status: "pending", activeForm: "Running dry-run verification"},
  {content: "Record decisions and dry-run results in session", status: "pending", activeForm: "Recording decisions"},
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

**Brownfield exception:** Even a small brownfield_debug may require `full` if the bug crosses multiple surfaces, touches 2+ concerns, or indicates a systemic invariant failure.

If `skip`: stub artifacts, Decision Journal entry with `decision: "skip"`, transition to gauntlet.

**[GATE]** — Present result to user for confirmation before proceeding.

---

## 3. Context Mode Detection

| Mode | Trigger | Scope |
|------|---------|-------|
| **Greenfield** | No existing codebase or only new files | Whole system |
| **Brownfield Feature** | Adding/improving feature in existing codebase | Blast zone + touched surfaces + touched concerns |
| **Brownfield Debug** | Fixing a bug or architecture failure | Failing traversal path + one sibling path |

**[GATE]** — Present detected mode to user for confirmation or override before proceeding. Record confirmed mode in Bootstrap and in the final architecture document header.

**Brownfield Feature scope:** Blast zone (files to modify + imports/exports) + any concerns the feature touches. Trace entrypoints for **every affected surface**, not only request paths.

**Existing debt rule:** If a concern is in scope AND has a `now` severity in `manifest.json`, flag whether the feature makes the debt worse. Must not reinforce known anti-patterns.

**Brownfield Debug scope:** Bug's full traversal path across all surfaces it touches.

---

## 4. Framework Profile and Execution Surface Map

### 4.1 Framework Capability Profile

Populate the `framework_profile` key in `phase4_bootstrap`. All fields required for `lightweight` and `full`:

```json
{
  "category": "web-app | api-service | cli | library | data-pipeline | mobile | other",
  "framework": "Next.js App Router | FastAPI | Express 5 | Django | Rails | ...",
  "framework_version": "exact major/minor or constraint",
  "runtime": "node | edge | python | ruby | jvm | mixed",
  "deployment_target": "serverful | serverless | edge | mixed",
  "enabled_features": ["cacheComponents", "serverActions", "ppr"],
  "subprofiles": {
    "rendering_model": "SSR | SSG | RSC+streaming | SPA | hybrid | N/A",
    "data_access_model": "DAL/repository | direct ORM | BFF | service layer | N/A",
    "mutation_model": "server actions | route handlers | RPC | REST | forms | queue | N/A",
    "cache_model": "framework native model + invalidation primitives | N/A",
    "error_model": "native exception/boundary model"
  },
  "enforcement_model": "per-surface enforcement mechanism summary"
}
```

**Rule:** `default accepted` is only valid when the profile explains why the default is sufficient for THIS project at THIS version.

### 4.2 Execution Surfaces

| `surface_id` | Human Name | Examples |
|--------------|-----------|---------|
| `request_response` | Request/Response | HTTP handlers, API endpoints, GraphQL resolvers |
| `mutation_entrypoint` | Mutation Entrypoints | Server Actions, form actions, RPC calls |
| `background_job` | Background Jobs | Queue workers, async consumers |
| `scheduled_work` | Scheduled Work | Cron, periodic tasks |
| `startup_migration` | Startup/Build/Migration | Boot, schema migration, initialization |
| `client_runtime` | Client Runtime | Browser JS, React components, native mobile |
| `webhook` | Webhooks | Incoming signed callbacks |
| `outbound_integration` | Outbound Integrations | Third-party API/service calls |
| `realtime_streaming` | Realtime/Streaming | WebSockets, SSE, streaming responses, subscriptions |

Every concern must declare which `surface_id`s it applies to. All JSON schemas, matrix cells, and artifact references must use the `surface_id` enum value, not the human name.

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

Classify along dimensions relevant to the project type. Each decision links to roadmap goals, user stories, and NFRs. Record in the session detail file as `architecture_taxonomy`:

```json
{
  "schema_version": "1.0",
  "category": "web-app | cli | api-service | library | data-pipeline | mobile | other",
  "dimensions": [
    {
      "name": "string (required)",
      "value": "string (required)",
      "rationale": "string (required)",
      "source_refs": ["string"]
    }
  ]
}
```

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
| Concern | request_response | mutation_entrypoint | background_job | scheduled_work | startup_migration | client_runtime | webhook | outbound_integration | realtime_streaming |
|---------|-----------------|-------------------|---------------|---------------|------------------|---------------|---------|--------------------|--------------------|
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

### Required Headers for `target-architecture.md`

```yaml
schema_version: "1.0"
spec_slug: "<slug>"
phase_mode: "full"
context_mode: "greenfield"
framework: "FastAPI"
framework_version: "0.115.x"
surfaces: ["request_response", "background_jobs"]
roadmap_path: "<path>"
tests_pseudo_path: "<path>"
```

Required sections: Overview, Goals and Non-Goals, Framework Profile, Applicable Execution Surfaces, Concern Assessments, Concern x Surface Matrix (full/recommended for lightweight), Architectural Invariants, Dry-run Summary, Open Questions.

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

### 8.2 Machine-Readable (`architecture-invariants.json`)

**Normative schema — all fields required unless marked optional:**

```json
{
  "schema_version": "1.0",
  "spec_slug": "string",
  "phase_mode": "skip | lightweight | full",
  "generated_at": "ISO8601",
  "invariants": [
    {
      "id": "INV-NNN (required)",
      "status": "active | reversed (required)",
      "category": "concern_category enum (required)",
      "scope": "string (required)",
      "surfaces": ["surface_id enum (required, ≥1)"],
      "rule": "string (required)",
      "enforcement": "string (required)",
      "exceptions": ["string (optional, default [])"],
      "verification_kind": "static | dynamic | manual (required)",
      "verification": "string (required)",
      "linked_user_stories": ["US-X (required, ≥1)"],
      "linked_goals": ["G-X (required, ≥1)"],
      "linked_tests": ["TC-INV-NNN (required, ≥1)"],
      "supersedes": "INV-NNN | null (optional)",
      "superseded_by": "INV-NNN | null (optional)"
    }
  ]
}
```

**Rules:**
- Minimum 1 active invariant per in-scope concern (`lightweight` and `full`)
- `skip`: `{"schema_version": "1.0", "spec_slug": "<slug>", "phase_mode": "skip", "generated_at": "ISO8601", "invariants": []}`
- Each invariant: verifiable (`static` | `dynamic` | `manual`), names ≥1 surface
- Reversed: `status: "reversed"`, `superseded_by` set to replacement
- Downstream tools consume only `status: "active"`
- Legacy bare-array format (no wrapper) must be accepted by readers; new writers always emit schema `1.0`

### 8.3 Invariant-Derived Tests

**Upsert** the `## Invariant Tests (Phase 4)` heading block in canonical `tests-pseudo.md`. If the heading already exists, replace the entire block (from heading to next `##` or EOF). Never blindly append — reruns must be idempotent.

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

Debate rounds default to a maximum of 3. At round 5, the agent must require explicit user approval to continue.

Set `phase4_bootstrap.status = "debating"` before the first debate round. Update `updated_at` after each round.

---

## 10. Dry-Run Verification (Gate)

### 10.1 Mode-Aware Scope

| Mode | Dry-run scope |
|------|--------------|
| `skip` | None |
| `lightweight` | 1 highest-risk archetype per applicable surface |
| `full` | Read AND write archetypes per applicable surface |

**Highest-risk selection criteria:** trust boundary crossed, irreversible side effect, async delivery, concurrency exposure, user-visible inconsistency potential. When multiple surfaces qualify, pick the one with the most concern interactions.

Set `phase4_bootstrap.status = "dry_run"` before starting. Record results to `dry_run_results` artifact.

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

### 10.3 Dry-Run Results Schema (`dry-run-results.json`)

**Normative schema:**

```json
{
  "schema_version": "1.0",
  "spec_slug": "string",
  "phase_mode": "lightweight | full",
  "context_mode": "greenfield | brownfield_feature | brownfield_debug",
  "run_at": "ISO8601",
  "archetypes": [
    {
      "surface": "surface_id enum (required)",
      "operation": "read | write (required)",
      "status": "pass | fail (required)",
      "checks_run": ["string (required, ≥1, e.g. 'enforcement_order', 'auth_check')"],
      "failed_checks": ["string (empty if pass)"],
      "invariant_ids": ["INV-NNN (invariants verified in this archetype)"],
      "evidence": "string (required, description of what was verified)",
      "notes": "string | null (optional, failure details or edge cases found)"
    }
  ],
  "summary": {
    "total_archetypes": "integer",
    "passed": "integer",
    "failed": "integer"
  }
}
```

### 10.4 Context-Aware Scoping

- **Greenfield (full):** All applicable surface archetypes.
- **Brownfield Feature:** Archetypes for surfaces the feature touches. Focus on delta.
- **Brownfield Debug:** Failing path + one sibling-path verification.

**[GATE]** — All required archetypes must pass. Any failure is a blocking error.

---

## 11. Record Decisions

Decision Journal entries are append-only in the session detail file under `decision_journal[]`.

**Normative schema — required fields unless marked optional:**

```json
{
  "entry_id": "dj-YYYYMMDD-<6 char> (required)",
  "idempotency_key": "sha256(run_fingerprint + topic + choice) (required)",
  "time": "ISO8601 (required)",
  "phase": "target-architecture (required)",
  "phase_mode": "skip | lightweight | full (required)",
  "context_mode": "greenfield | brownfield_feature | brownfield_debug (required)",
  "topic": "string (required, e.g. 'enforcement-pattern')",
  "decision": "decision_type enum (required)",
  "choice": "string (required)",
  "surfaces": ["surface_id enum (required, ≥1)"],
  "rationale": "string (required)",
  "alternatives_considered": ["string (optional)"],
  "revisit_trigger": "string | null (optional)",
  "reverses_entry_id": "dj-* | null (optional, for reversals)"
}
```

**Idempotency rule:** On rerun (same `run_fingerprint`), if a journal entry with the same `idempotency_key` already exists, skip the write. This prevents duplicate entries when Phase 4 resumes after a blocking error.

**Reversal rule:** To reverse a prior decision, create a new entry with `decision: "reject"` and `reverses_entry_id` pointing to the original. Never delete or modify existing entries.

---

## 12. Brownfield Feature Flow

Replaces greenfield Steps 5-8 with blast-zone-scoped versions. Steps 1-4 and 9-11 are shared.

1. **Read blast zone architecture** — primer.md, component docs, concerns, patterns
2. **Trace entrypoints per affected surface** — map enforcement chain for each surface touched
3. **Assess concern fitness** per base + triggered concern: `adequate | needs_extension | missing | conflicts`
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
- `specs/<slug>/dry-run-results.json` (non-skip only)
- Decision journal entries in session detail file
- Architecture taxonomy in session detail file
- `phase4_bootstrap` in session detail file

### Completion Criteria by Mode

**`skip`:**
- Scale rationale recorded
- Stub target-architecture.md created
- Empty architecture-invariants.json created (with schema_version)
- Decision Journal entry with `decision: "skip"`
- `phase4_bootstrap.status = "completed"`

**`lightweight`:**
- In-scope concerns decided with rationale
- Active invariants defined and verifiable
- 1 highest-risk archetype per applicable surface passed
- Invariant tests upserted in tests-pseudo.md
- Dry-run results recorded
- Decisions recorded with surfaces
- `phase4_bootstrap.status = "completed"`

**`full`:**
- All in-scope dimensions decided with rationale
- All in-scope base + triggered concerns assessed
- Concern x surface matrix complete
- Concern interactions checklist completed
- Read+write dry-run per applicable surface passed
- Debate converged
- Active invariants defined, verifiable, in JSON + markdown
- Invariant tests upserted in tests-pseudo.md
- Dry-run results recorded
- Decisions recorded with surfaces, phase_mode, context_mode
- `phase4_bootstrap.status = "completed"`

---

## 15. Session Mutation Contract

Phase 4 may only mutate these session detail file keys:

| Key | Mutation Rule |
|-----|--------------|
| `phase4_bootstrap` | Upsert by key; always update `updated_at` |
| `architecture_taxonomy` | Replace atomically |
| `decision_journal[]` | Append only; suppress duplicate `idempotency_key` |
| `journey[]` | Append only; suppress duplicate `event_id` |
| `phase_artifacts.target_architecture_path` | Set once at draft completion |
| `current_phase` | Set on phase transition (via SKILL.md protocol) |
| `current_step` | Update at each gate |
| `updated_at` | Update on every mutation |

Phase 4 must NOT mutate: `requirements_summary`, `roadmap_path`, `debate_state`, `completed_work`, `trello_card_id`, or any key not listed above.

**File artifacts** (written to `specs/<slug>/`, not session state):

| Artifact | Mutation Rule |
|----------|--------------|
| `target-architecture.md` | Replace atomically |
| `architecture-invariants.json` | Replace atomically |
| `dry-run-results.json` | Replace atomically |
| `tests-pseudo.md` | Upsert only the `## Invariant Tests (Phase 4)` heading block |

All file writes use temp-file + atomic rename. No in-place mutation.

---

## 16. Blocking Errors

Phase 4 session runs and skill releases use separate error code namespaces. A skill release failure must NOT mutate `phase4_bootstrap`.

### Session Run Errors (`P4_*`)

Set `phase4_bootstrap.status = "blocked"` and populate the `blocking_error` field.

**Blocking error schema:**

```json
{
  "code": "string (required, P4_* from table below)",
  "severity": "blocking (always)",
  "message": "string (required, human-readable description)",
  "resolution": "string (required, what the user/agent should do)",
  "detected_at": "ISO8601 (required)",
  "artifact_state": "string (required, summary of what was written before the error)"
}
```

**Error codes:**

| Code | Condition | Resolution |
|------|-----------|------------|
| `P4_MISSING_ROADMAP` | No roadmap manifest with goals, non-goals, user stories | Return to Phase 2 |
| `P4_MISSING_TESTS_PATH` | `tests_pseudo_path` not set in roadmap or session | Set in roadmap manifest |
| `P4_MISSING_ARCH_DOCS` | Brownfield work without usable `.architecture/manifest.json` | Run `/mapcodebase` first |
| `P4_UNRESOLVED_FRAMEWORK` | `lightweight` or `full` without declared framework name and version | Resolve before continuing |
| `P4_UNALIGNED_STORY` | User story maps to 0 goals or conflicts with a non-goal | Fix roadmap before continuing |
| `P4_INVALID_BOOTSTRAP` | `phase4_bootstrap` fails schema validation | Fix malformed fields |
| `P4_CONCURRENT_WRITER` | Lock file already held by an active writer | Wait or investigate |
| `P4_STALE_LOCK` | Lock file exists but holding process is gone (age > 30 min or PID dead) | Force-break with warning, log to journey |
| `P4_UNCOVERED_CONCERN` | In-scope concern has zero applicable surface decisions | Add surface decisions |
| `P4_UNVERIFIABLE_INVARIANT` | Invariant has no verification method | Fix or remove with rationale |
| `P4_DRY_RUN_FAILED` | Any required archetype fails verification | Fix architecture decisions |
| `P4_ARTIFACT_WRITE_FAILED` | Atomic write to any artifact path failed | Check filesystem permissions |

### Skill Release Errors (`REL_*`)

These apply to deploying skill files to `~/.claude/skills/`. They do NOT touch `phase4_bootstrap` or any session state.

| Code | Condition | Resolution |
|------|-----------|------------|
| `REL_VALIDATION_FAILED` | Schema/example inconsistency in spec | Fix spec before deploying |
| `REL_SMOKE_FAILED` | Greenfield or brownfield smoke-run failed | Fix spec or phase doc |
| `REL_BACKUP_FAILED` | Could not create backup of current deployed files | Check permissions on `~/.claude/skills/` |
| `REL_DEPLOY_FAILED` | Atomic rename or checksum verification failed | Rollback from backup |
| `REL_ROLLBACK_FAILED` | Could not restore from backup | Manual intervention required |

**Rules (both namespaces):**
- No silent fallback from a blocking error to `skip`
- Every blocking error must be surfaced to the user before halting
- Prior artifacts are preserved — a blocked run does not delete completed work
- Reruns after fixing a blocking error must be idempotent (bootstrap fields merge by key, journal entries deduplicated by `idempotency_key`)

---

## 17. Security Considerations

Phase 4's own operational security (not the target system being architected):

- **Path validation:** Validate `spec_slug` and all artifact-relative paths against a strict allowlist pattern (`^[a-z0-9][a-z0-9-]*$` for slugs, no `..`, no absolute paths). Reject path traversal attempts.
- **Subprocess safety:** `debate.py` is invoked as a subprocess. Pass structured arguments — never interpolate user-controlled strings into shell evaluation boundaries.
- **Secret redaction:** Never write API keys, tokens, or raw config dumps to session files, decision journal entries, prompts, or deployed artifacts.
- **Untrusted input:** Treat framework docs, roadmap text, and opponent-model output as untrusted input. Do not let them define file paths, commands, or session field values without validation.
- **Deploy-time permissions:** Deployed files in `~/.claude/skills/` must be user-readable only (no world-writable).

---

## 17. Testing Strategy

### Schema Validation Tests
- **Each artifact schema:** Verify `architecture-invariants.json`, `phase4_bootstrap`, `architecture_taxonomy`, `dry-run-results.json`, and decision journal entries conform to their declared schemas. Reject malformed output.
- **Enum enforcement:** Verify `status`, `phase_mode`, `context_mode`, `verification_kind`, `decision` only accept declared values.

### Unit-Level Validation
- **Scale check logic:** Verify mode selection for edge cases (exactly 3 stories, single concern at boundary, risk trigger override)
- **Context mode detection:** Verify greenfield/brownfield_feature/brownfield_debug classification against known project shapes
- **Invariant lifecycle:** Verify `active` → `reversed` with `superseded_by` set, downstream consumers ignore `reversed`
- **Path validation:** Verify slug validation rejects traversal, accepts valid slugs

### Integration Tests
- **Greenfield end-to-end:** From scale check through dry-run for a small greenfield spec (3 user stories, 2 surfaces, 2 concerns) — verify all artifacts produced and conform to schemas
- **Brownfield feature:** Inject existing `.architecture/` docs, verify blast-zone scoping respects existing architecture, concern fitness assessment runs, debt flags raised
- **Brownfield debug:** Inject a failing traversal path, verify local-vs-systemic decision logic, invariant gap classification

### Idempotency Tests
- **Rerun Phase 4 on same inputs:** Verify bootstrap merges by key without duplication, invariant tests are upserted (not doubled), decision journal entries are not duplicated, artifact content is identical

### Failure Tests
- **Each blocking error code:** Verify Phase 4 halts (not degrades) and `phase4_bootstrap.status = "blocked"` with correct error code
- **Concurrent writer:** Verify lock prevents simultaneous writes

### Golden Tests
- **Artifact shape:** Verify `target-architecture.md` has all required headers and sections
- **Concern x surface matrix:** Verify every in-scope concern has at least one surface decision

### Deployment Tests
- **Backup creation, atomic replace, checksum verification, rollback by release_id**

---

## 18. Deployment Strategy

Phase 4 deploys as a markdown phase document plus supporting schema definitions. The deployment target is `~/.claude/skills/adversarial-spec/`.

### Deployment Steps
1. **Validate:** All schemas and examples in the spec are internally consistent
2. **Smoke-run:** Execute one greenfield and one brownfield scenario against the new phase doc
3. **Update cross-references:** Verify `02-roadmap.md`, `05-gauntlet.md`, and `07-execution.md` reference the correct section numbers and artifact names
4. **Generate release_id:** `p4-YYYYMMDD-<short-hash>`
5. **Backup:** Copy current deployed files to `~/.claude/skills/adversarial-spec/.backup/<release_id>/`
6. **Deploy:** Write candidate files to temp paths in deploy target, then atomically rename into place
7. **Verify:** Checksum deployed files against source — must match
8. **Record:** Log deployment event with `release_id` to journey

### Rollback
- Restore from the backup for a specific `release_id`: copy from `.backup/<release_id>/` → deploy target, atomically rename, verify checksums
- Record rollback event with `release_id` to journey
- Git history is evidence and provenance, not the rollback mechanism

---

## 19. Migration Plan

### Legacy Session Compatibility
- Sessions created before this Phase 4 version will not have `phase4_bootstrap` in their session detail file
- On first Phase 4 entry: if `phase4_bootstrap` is absent, create it with `status: "bootstrapping"` — do not error
- Legacy `architecture-invariants.json` may be a bare array (no `schema_version` wrapper) — readers must accept both formats; new writers always emit schema `1.0`

### Artifact Path Normalization
- If an existing session stores an obsolete artifact root or roadmap path, normalize into canonical paths in the bootstrap record
- Preserve the old value in the decision journal as a `migrate` entry

### Invariant Test Section
- If `tests-pseudo.md` already contains an old `## Invariant Tests (Phase 4)` block, the upsert replaces it. No duplicated sections on re-entry.

### Cross-Reference Updates
- Phase 5 (`05-gauntlet.md`): Update adversary briefing inputs to reference concern x surface matrix and triggered concerns
- Phase 7 (`07-execution.md`): Update task generation to reference invariant IDs and surface scope
- Phase 2 (`02-roadmap.md`): Update tests-pseudo integration to reference invariant-derived tests section

---

## 20. Observability

Phase 4 is an AI-agent-driven process, not a running service. Observability means producing enough evidence for a fresh agent (or human) to understand what happened and resume.

### Required Evidence per Run
- `phase4_bootstrap` record in session detail file (progressive state machine — `status` shows how far the run progressed)
- Decision journal entries (append-only, shows every architectural choice with rationale)
- Journey log entries for phase transitions and gate completions
- Dry-run results artifact (pass/fail per archetype with failure details and evidence)
- `blocking_error` field if halted (shows exact error code, message, and artifact state at time of failure)

### Required Journey Events
- `phase4_started`, `scale_check_complete`, `context_detected`, `bootstrap_complete`, `draft_written`, `debate_round_complete` (per round), `dry_run_complete`, `phase4_blocked`, `phase4_completed`, `deployment_complete`, `rollback_complete`

### Debugging a Failed Run
1. Read `phase4_bootstrap.status` and `current_gate` — shows how far the run progressed
2. If `blocked`: read `blocking_error` for exact condition and resolution
3. Read decision journal — shows which concerns were assessed before failure
4. Read dry-run results — shows which archetypes passed/failed
5. A failed Phase 4 run must leave enough session state for a fresh agent to resume without re-reading source files or re-running completed steps

---

## 21. Phase Interactions

**Phase 2 (Roadmap):** Invariant tests upserted in canonical `tests-pseudo.md`. Architecture traces to roadmap goals, user stories, and existing tests.

**Phase 5 (Gauntlet):** Adversaries receive framework profile, surface map, concern x surface matrix, invariant set, and triggered concerns. BURN→observability+realtime, PARA→enforcement/auth/security/trust, LAZY→enforcement bypass, COMP→SoT/brownfield compatibility.

**Phase 7 (Execution):** Tasks reference invariants. High-risk (3+ invariants) → test-first. Architecture Spine (Wave 0) derives from invariant enforcement tasks. Multi-surface tasks flagged for extra review.

**Downstream:** `/mapcodebase` and `/diagnosecodebase` consume `architecture-invariants.json` (active only + surface scope). Future work.

---

## Open Questions / Future Considerations

- Publish formal JSON Schema files (`.json-schema`) for all Phase 4 artifacts, referenced from this spec.
- Decide whether `dry_run_results` should remain a separate artifact file or be embedded in the session detail file.
- Define schema-version bump rules when Phase 5 or Phase 7 adds new invariant-consumer requirements.
- Should framework-specific guardrails move into versioned adapters (separate files per framework) instead of being embedded in this phase doc?