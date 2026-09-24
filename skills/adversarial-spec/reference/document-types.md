## Document Types

### Active `debate.py` types

`debate.py --doc-type` accepts exactly these values:

| Type | Purpose | Additional control |
|---|---|---|
| `spec` | Define a product or technical change. | `--depth product|technical|full`; default `technical`. |
| `debug` | Diagnose an existing failure from evidence and propose a proportional fix. | `--depth` is ignored. |
| `architecture` | Define shared target patterns, boundaries, and flows. | `--depth` is ignored. |

Select models and seats from `reference/current-models.md`. See
`reference/script-commands.md` for executable syntax.

The lower-level standalone gauntlet CLI has its own compatibility parser:
`--doc-type prd|tech|debug` with default `tech`. `prd` and `tech` are
standalone-gauntlet-only values; they are not accepted by `debate.py`.

### Spec (Unified Specification)

| Depth | Focus | Use for |
|---|---|---|
| `product` | User value, stakeholders, success metrics | Product planning and stakeholder alignment |
| `technical` | Architecture, APIs, data models | Engineering implementation |
| `full` | Product and technical requirements | A complete requirements-to-implementation handoff |

#### Structure by depth

**Product depth:**

- Executive Summary
- Problem Statement / Opportunity
- Target Users / Personas
- User Stories / Use Cases
- Functional and Non-Functional Requirements
- Success Metrics / KPIs
- Scope (In/Out)
- Dependencies
- Risks and Mitigations

**Technical depth:**

- Overview / Context
- Goals and Non-Goals
- **Getting Started** — required bootstrap workflow
- System Architecture and Component Design
- API Design, including complete request/response schemas
- Data Models / Database Schema
- Infrastructure and Security Requirements
- Error Handling Strategy
- Performance Requirements / SLAs
- Observability
- Testing and Deployment Strategy
- Migration Plan, when applicable
- Open Questions / Future Considerations

**Full depth:** all product and technical sections.

#### Happy-Path Spine and Maturity Ladder

Spec documents that produce roadmap artifacts preserve the Happy-Path Spine
model through implementation:

- Each user story has exactly one happy-path spine designation. The shared
  `SpineCoverageChecker` rejects zero or duplicate designations.
- The happy-path spine record names `spine_steps`. Each branch or failure test
  uses `spine_of` plus `spine_step_ref`; a missing `spine_step_ref` leaves the
  test unanchored to a happy-path obligation.
- The maturity ladder is `nl -> acceptance -> concrete`.
- `acceptance has executable meaning without the facade`: inputs, actions,
  expected observations, and failure conditions are concrete enough to test
  before the final UI or API exists.
- An `nl` test promotes only with `>=1 named accessor`. Empty `accessors` block
  promotion until the seam, function, route, actor, or artifact is named.

`tests-pseudo.md` rows are authoring prose for the extended TMR row. Compilation
must be able to emit `tmr_uid`, `test_id`, `title`, `user_story`, `maturity`,
`data_strategy`, `live_or_induced`, `spine`, `spine_steps`, `spine_of`,
`spine_step_ref`, `accessors`, `binding_status`, `run_evidence`,
`critical_seam`, `criticality_source`, `verification_mode`,
`verification_scope`, `altitude`, `tested_by`, `status`, `source_spec`,
`also_covers`, `supersedes`, and tombstone/technical-constraint fields when
applicable. Markdown is a view; `tmr-registry.json` is authoritative after
compile.

#### Critique criteria by depth

**Product:**

1. Clear problem definition with evidence
2. Defined personas with real pain points
3. User stories with value and testable outcomes
4. Measurable success criteria
5. Explicit scope boundaries
6. Realistic risks and mitigations

**Technical:**

1. **Getting Started** exists and gives a usable bootstrap workflow
2. Architectural decisions include rationale
3. API contracts include complete schemas
4. The data model covers identified use cases
5. Security threats and mitigations are explicit
6. Error scenarios and handling are enumerated
7. Performance targets are measurable
8. Deployment is repeatable and reversible
9. No implementation-blocking ambiguity remains

**Full:** all product and technical criteria.

**Round 1 checks:** map every roadmap user story to a spec section, require
Getting Started for technical/full depth, and make every success criterion
testable before proceeding.

### Target Architecture

Use `architecture` for the shared patterns every implementation task must
follow: component boundaries, data flow, authentication, state, caching,
failure handling, and cross-cutting constraints. Include explicit decisions,
their rationale, affected requirements, and a dry-run user flow.

Critique it for:

1. Fit to the application's category and scale
2. Missing framework-native capabilities or required patterns
3. Composition across routes, pages, and features
4. Gaps in the dry-run flow
5. Decisions that merely restate defaults without evaluation
6. Consistency with the product requirements

### Debug Investigation

A Debug Investigation diagnoses and fixes an existing system from evidence.
Use it for unclear bugs, performance problems, intermittent failures, and any
case where the cause must be established before choosing a fix.

**Contract: Evidence → Hypothesis → Fix.** Fix size must be proportional to the
demonstrated cause.

Required fields:

- **Symptoms:** user-visible behavior, timing, start point, and blast radius
- **Expected vs Actual Behavior:** a comparison for each scenario
- **Evidence Gathered:** timestamped logs, timings, errors, and reproduction
- **Hypotheses:** ranked by likelihood × ease of verification, with evidence for and against
- **Diagnostic Plan:** immediate checks, targeted instrumentation, and tests
- **Root Cause:** file/location, mechanism, and why competing hypotheses failed
- **Proposed Fix:** files, changes, before/after behavior, and justification
- **Verification:** confirmation steps, regression checks, and expected evidence
- **Prevention:** a retained test, documentation update, and similar-risk search

Critique criteria:

1. Evidence precedes hypotheses.
2. Simple explanations are ruled out before redesign.
3. Each diagnostic answers a named question.
4. The fix is proportional and causally tied to the evidence.
5. Root cause is identified rather than symptoms masked.
6. Verification is specific and reproducible.

Flag premature architecture, shotgun debugging, untested assumptions,
disproportionate fixes, and unrelated scope expansion.

Before submission, remove credentials, PII, customer data, internal network
details, and any material barred by organizational policy. Prefer targeted log
windows and summarized repetition over full log files.
