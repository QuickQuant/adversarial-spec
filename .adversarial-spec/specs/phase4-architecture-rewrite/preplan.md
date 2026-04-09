# Pre-Plan: Phase 4 (Target Architecture) Rewrite

## Problem Statement

Phase 4 of the adversarial-spec workflow is the architecture decision phase. It currently has 8 steps in 225 lines and treats architecture as "pick some dimensions, draft a doc, debate it." This is inadequate:

1. **Missing cross-cutting concerns.** Middleware chain, error handling pipeline, validation boundaries, source-of-truth enforcement, observability, caching, and configuration management are not mentioned. These are the exact concerns whose absence caused BracketBattleAI's architecture failures (dual pipelines, triple SoT, 45+ routes with duplicated auth boilerplate).

2. **No context branching.** The same 8 steps apply whether you're building a system from scratch, adding a feature to an existing codebase, or debugging a production issue. These are fundamentally different workflows.

3. **Dimensions are vague.** "Auth" and "Data freshness" are listed as dimensions for web apps, but there's no guidance on what decisions to make within each dimension, what questions to ask, or what deliverables to produce.

4. **No architectural invariants.** The phase produces a document but doesn't force explicit invariants that can be checked later by `/mapcodebase` or `/diagnosecodebase`.

5. **The dry-run is data-flow only.** It asks "what data is fetched?" and "what happens on error?" but never asks about middleware ordering, validation duplication, SoT conflicts, or observability gaps.

## Evidence: BracketBattleAI Failures

All traceable to missing Phase 4 guidance:

- **CON-001**: 13 of 52 API routes skip rate limiting. 45+ routes repeat auth/rate-limit boilerplate. A middleware chain decision would have prevented this.
- **CON-002**: Two bracket generation pipelines (one dead, one production) writing to different stores. A SoT declaration would have prevented this.
- **GAP-01 through GAP-04**: Three model registries with conflicting data. No SoT enforcement.
- **GAP-05**: Dual pipelines with different transport selection. No integration contract.
- **GAP-09**: Three leaderboard read paths. No caching/read-path architecture decision.

## Proposed Structure

### Three Modes (Context-Aware)

| Mode | Trigger | Scope | Starting Point |
|------|---------|-------|----------------|
| **Greenfield** | No existing codebase | Whole system | Research best practices, define from scratch |
| **Brownfield feature** | Adding/improving feature in existing codebase | Blast zone + touched cross-cutting concerns | Read `.architecture/` docs, assess fitness-for-purpose |
| **Brownfield debug/fix** | Fixing a bug or architectural problem | Blast zone + the middleware/validation/SoT path the bug traversed | Identify which architectural layer failed |

### Greenfield Steps (Expanded)

1. Scale check (existing — keep as gate)
2. Categorize application (existing — expand dimension lists)
3. **Define cross-cutting concerns** (NEW — mandatory for all projects above scale threshold):
   - Middleware chain: ordered list of concerns with framework-specific implementation
   - Error handling pipeline: 3-stage transform (raw → logged → user-facing)
   - Validation boundaries: what each layer validates (API, service, domain, DB)
   - Source of truth: single writer per data entity, staleness SLA for read copies
   - Observability: structured logging fields, trace propagation, metrics for SLOs
   - Caching: what/where/TTL/invalidation strategy
   - Configuration: what's externalized, how secrets are managed, feature flag strategy
4. Research best practices per dimension (existing — but now includes cross-cutting)
5. Draft target architecture document (existing — expanded template)
6. **Define architectural invariants** (NEW):
   - Explicit, testable assertions about the system
   - E.g., "Every API route passes through the auth middleware"
   - E.g., "Every data entity has exactly one authoritative writer"
   - Becomes input to `/mapcodebase` concern detection
7. Debate architecture (existing)
8. Dry-run verification (existing — expanded questions)
9. Record decisions in Decision Journal (existing)

### Brownfield Feature Steps

1. Scale check (keep — may skip architecture for trivial features)
2. **Read blast zone architecture** — load `.architecture/` component docs for affected area
3. **Trace request path** — for each affected entry point, map the middleware chain the request passes through
4. **Assess cross-cutting fitness** — for each concern:
   - Middleware chain: adequate / needs extension / missing / conflicts with change
   - Error handling: does the existing pipeline handle this feature's error cases?
   - Validation: does validation exist at the right layers for the new data?
   - SoT: does this feature introduce a new data entity? Who writes it?
   - Observability: can you trace the new feature's requests?
   - Caching: does the feature interact with existing caches? New cache needed?
5. **Draft architecture additions** — ONLY for concerns marked "needs extension" or "missing"
6. **Debate additions against existing constraints** — opponents check for conflicts with existing architecture
7. **Dry-run the feature** through existing + proposed architecture
8. **Update invariants** if new ones are introduced
9. Record decisions

### Brownfield Debug/Fix Steps

1. Scale check (almost always skip — fixes are scoped)
2. **Identify the failed layer** — which cross-cutting concern broke?
   - "Auth bug in 13 routes" → middleware gap
   - "Invalid data in DB" → validation boundary gap
   - "Two systems disagree" → SoT violation
   - "Can't debug production issue" → observability gap
3. **Decision: local fix or systemic fix?**
   - Apply the "13 routes" rule: 1 route = local fix, 4+ routes = middleware fix
   - "Could a new developer hit the same bug?" → systemic fix
   - "Is the fix 'add the same 3 lines to every handler'?" → middleware fix
4. **If systemic: design the architectural change** (add middleware, fix validation boundary, declare SoT)
5. **If local: verify the existing architecture is sound** — the bug is in application code, not architecture
6. **Dry-run the fix path** through the existing architecture
7. **Check invariant coverage** — does an invariant exist that should have prevented this? If not, add one.
8. Record decisions

### Expanded Dimension Lists

**Web apps** (current + additions):
- Current: Rendering, Navigation, Auth, Data freshness, State management, Multi-page sharing
- Add: Middleware chain, Error handling strategy, Validation boundaries, Caching, Observability, Security (CORS/CSP/sanitization), Testing architecture

**APIs** (current + additions):
- Current: Transport, Auth, Data layer, Scaling
- Add: Middleware chain, Error handling pipeline, Validation boundaries, Service composition, Caching, Config management, Security (beyond auth), Deployment strategy

**CLIs** (current + additions):
- Current: Execution model, State, Concurrency, I/O
- Add: Error handling, Config management, Observability, Testing strategy

**Libraries** (current + additions):
- Current: API surface, Error handling, Extensibility
- Add: Observability hooks, Configuration points, Testing support

**New categories needed:**
- Data pipelines: Orchestration, Schema evolution, Idempotency, Backfill strategy, Monitoring
- Mobile: Offline-first, Sync strategy, Push notifications, Deep linking, App lifecycle

### Expanded Dry-Run Questions

In addition to existing ("What data is fetched? What state is created? What happens on error?"):

- "Where does validation happen for this flow? Is it duplicated across layers?"
- "If this fails at 2am, how do we know? What's observable?"
- "What middleware runs before this handler? In what order?"
- "Is there exactly one source of truth for this data? Who writes it?"
- "What's cached? What happens if the cache and source disagree?"
- "Can a new developer add a route and accidentally skip auth/validation/logging?"
- "Does this flow violate any declared architectural invariant?"

### Architectural Invariants (New Deliverable)

Added to Phase 4 outputs alongside `target-architecture.md`:

```markdown
### Architectural Invariants

INV-001: Every API route passes through [auth, rate-limit, logging] middleware
INV-002: Every data entity has exactly one authoritative writer
INV-003: Every error is caught, logged with correlation ID, and transformed before reaching the user
INV-004: No service accesses another service's database directly
INV-005: All configuration is externalized — no secrets in source code
```

These become:
- Input to `/mapcodebase` pattern detection (can verify invariants against source)
- Input to `/diagnosecodebase` concern detection (violations become concerns)
- Checklist for code review (does this PR violate an invariant?)

## Research Sources

Comprehensive research was conducted across these frameworks:

- **arc42** (Section 8: Cross-cutting Concepts) — mandatory cross-cutting concern categories
- **C4 Model** — 4-level decomposition forcing decisions at each level
- **Architecture Decision Records (MADR)** — structured decision documentation with consequences
- **SEI/CMU Quality Attribute Workshop** — stimulus/response/measure scenarios for quality attributes
- **Richards & Ford "Fundamentals of Software Architecture"** — 30+ architecture characteristics taxonomy
- **Microsoft Azure Cloud Design Patterns** — gateway, integration, reliability patterns
- **Martin Fowler** — distributed monolith detection, strangler fig migration, monolith-first principle
- **Simon Brown "Risk-Storming"** — visual risk identification on architecture diagrams
- **Framework-specific middleware docs** — Rails Rack, Django middleware, Express, FastAPI, NestJS pipeline

## Debate Focus Areas

1. **Cross-cutting concern taxonomy** — is the list complete? Are any concerns mis-categorized?
2. **Brownfield scoping** — is "blast zone + touched cross-cutting concerns" the right scope? Too narrow? Too broad?
3. **Invariant enforcement** — how do invariants flow into downstream tools (`/mapcodebase`, `/diagnosecodebase`)? What format?
4. **The "13 routes" rule and debug decision tree** — is this practical? What edge cases break it?
5. **Scale check thresholds** — should brownfield features have a different scale check than greenfield?
6. **Interaction with Phase 2 (tests-pseudo.md)** — should testability sketches feed into Phase 4, or does Phase 4 produce its own verification artifacts?

## Blast Zone

Files to modify in `adversarial-spec` project:
- `skills/adversarial-spec/phases/04-target-architecture.md` — primary rewrite target
- `skills/adversarial-spec/phases/02-roadmap.md` — may need cross-reference to Phase 4 invariants
- `skills/adversarial-spec/phases/05-gauntlet.md` — adversaries may need updated architecture context
- `skills/adversarial-spec/phases/07-execution.md` — execution plan may reference invariants

Downstream consumers (need compatibility check, not modification):
- `skills/evaluate-plan/SKILL.md` — may add testability sketch gate
- `skills/mapcodebase/` — may consume invariants in future
- `skills/diagnosecodebase/` — may check invariants in future
