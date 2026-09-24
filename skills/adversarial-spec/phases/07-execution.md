> Phase 7 is context-heavy and requires active supervision. Recommend a fresh
> context window before planning. Do not run it unattended unless the user
> explicitly requests that mode.

```text
TodoWrite([
  {content: "Load the finalized artifact chain and targeted architecture context", status: "in_progress", activeForm: "Loading planning inputs"},
  {content: "Resolve and reconcile the active target architecture [GATE]", status: "pending", activeForm: "Reconciling target architecture"},
  {content: "Decompose by readiness and blast radius with concern traceability", status: "pending", activeForm: "Decomposing implementation work"},
  {content: "Classify verification and human-execution obligations [GATE]", status: "pending", activeForm: "Classifying verification obligations"},
  {content: "Persist the checkpoint-safe plan draft [GATE]", status: "pending", activeForm: "Persisting the plan draft"},
  {content: "Prove draft dependency semantics [GATE]", status: "pending", activeForm: "Checking dependency semantics"},
  {content: "Obtain plan, coverage, and exception approval [GATE]", status: "pending", activeForm: "Obtaining plan approval"},
  {content: "Emit, validate, and load the approved Fizzy plan [GATE]", status: "pending", activeForm: "Loading the approved plan"},
  {content: "Verify the card handoff and transition to implementation", status: "pending", activeForm: "Verifying the implementation handoff"},
])
```

## Execution Planning (Phase 7)

Turn the finalized spec, test intent, target architecture, and accepted Concerns
into an approved, dependency-safe execution plan and plan-backed Task Cards.
Draft the plan directly; no extra debate or model pipeline is required. The Fizzy
board pipeline is still required to validate the wire plan and materialize cards.

Never create session work with raw `add_card`. A later scope change is a plan
amendment: update the approved artifacts, run `pipeline_validate_plan`, then
`pipeline_load` again.

### 1. Load the active artifact chain

Resolve the active detail file from `.adversarial-spec/session-state.json`. Read
paths from that detail file rather than selecting the first filename match:

- finalized spec from `spec_path`;
- roadmap/manifest from `roadmap_path` or `manifest_path`;
- tests from the session's `tests-spec.md` path;
- accepted Concern artifact from `gauntlet_concerns_path`;
- execution/decomposition artifacts already recorded for this Session;
- `phase_artifacts.target_architecture_path`, with legacy
  `target_architecture_path` as a compatibility fallback.

Stop on a missing required path. Do not substitute an artifact from another
Session or context.

#### Targeted architecture reads

When `.architecture/manifest.json` exists:

1. Read `.architecture/INDEX.md`, then `.architecture/primer.md`.
2. Use the declared file scope and cross-component flows to select the smallest
   useful set of component/flow documents. Two to four matched component docs is
   typical, not a quota.
3. Read `.architecture/concerns.md` only when the scope intersects recorded
   codebase Concerns.
4. Attach repo-relative `architecture_refs` only when the referenced content
   actually describes the task's files, contracts, or flows. Never infer a ref
   from a similar filename.

If architecture docs are absent, tell the user that `/mapcodebase` is the normal
grounding path. If the user proceeds, inspect the exact code paths in scope and
record the architecture-ref exemption in the plan review.

For each proposed task, ground implementation status in current source and
history:

| Status | Planning action |
|---|---|
| `greenfield` | Build; cite the searched scope and absence of an implementer. |
| `partial` | Complete the existing path; cite the stub, TODO, or incomplete symbol. |
| `already-built` | Verify or port against the approved acceptance criteria; do not describe a new build. |

Record `implementation_status` and concise `implementation_evidence` in the
human plan. Prefer `path:symbol` and commit anchors over brittle source line
numbers.

### 2. Reconcile the active target architecture

Read the target architecture from the active detail's artifact path. Never use a
repository-wide `target-architecture.md` glob or first-match lookup.

Run exactly one named comparison: **`Phase4FingerprintComparison`**. Use the
algorithm and inputs in `04-target-architecture.md` § Fingerprints; do not invent
another hash meaning:

```text
input_fingerprint = sha256(
  stripped_spec_bytes + NUL + roadmap_bytes + NUL +
  canonical_json({phase_mode, context_mode})
)

architecture_fingerprint = sha256(
  input_fingerprint + NUL + canonical_json(framework_profile) + NUL +
  canonical_json(execution_surfaces) + NUL +
  canonical_json(active_invariants) + NUL +
  canonical_json(research_findings)
)
```

Apply Phase 4's volatile-metadata stripping and canonical JSON rules exactly.
The comparison is fresh only when the recomputed input fingerprint matches
`phase_artifacts.spec_fingerprint` and the recomputed architecture fingerprint
matches `phase4_bootstrap.architecture_fingerprint` plus the published artifact
headers. In `phase_mode: skip`, the architecture fingerprint is intentionally
null and the stub remains the consumed artifact.

If the comparison is stale:

1. Reconcile in place when finalization changed requirements but not component
   boundaries: patch the target architecture, active invariants, middleware
   candidates, framework profile, and dry-run evidence; then rerun the one named
   comparison.
2. Rerun Phase 4 only when boundaries, surfaces, or the invariant set changed;
   obtain user approval first.
3. Proceed with acknowledged drift only as a last resort. Put the warning in the
   execution plan and record the human decision.

Write the reconciled artifact set with Phase 4's same-directory staging and
atomic-renames protocol. Record the prior values and reason in the bootstrap
reconciliation block. See `SKILL.md` § Decisions Log and § Journey Log for the
durable records.

When the active architecture directory contains `middleware-candidates.json`,
surface every retained candidate and map it to exactly one source task plus an
executable test-suite path. Phase 7 prepares that substrate; the optional
middleware-creator phase owns fanout.

Extract cross-cutting decisions into an **Architecture Spine** in the plan:

```markdown
## Architecture Spine

### <decision or pattern>
- Constraint: <what every affected task must preserve>
- Owner task: <task_id>
- Reference: <target-architecture section or architecture ref>
```

Foundation work must precede consumers through real `depends_on` edges, not a
prose-only wave label.

### 3. Shape the plan by blast radius

Use `skills/adversarial-spec/reference/altitude.md` as the altitude authority.

- Lock one Slice North Star outcome.
- The highest-blast item sets the root altitude.
- An irreversible external consequence or process/repository boundary forces a
  `system` root.
- Group work by how far a mistake propagates: component work under subsystem
  work under the single system root where those altitudes exist.
- Explain each node's altitude in plain language.

Apply the proportional verification ladder:

| Altitude | Verification floor |
|---|---|
| component | Unit or component verification; never zero. |
| subsystem | Integration verification plus contract conformance for consumers. |
| system | End-to-end verification, consequence-safety controls, and a manual go-live gate where consequences require one. |

Use safe environments only where the approved plan permits them. A live
money-path acceptance condition requires authorized live evidence; a stand-in is
not a substitute.

#### Split at readiness boundaries

Split work when its earliest safe start differs from its production-integration
gate. A contract-bound adapter may start before the later live integration that
consumes it. Keep a dependency when safety or evidence truly requires it.

Merge proposed cards that cannot be distinguished by owner, dependency,
acceptance evidence, or review boundary. Do not use task-count or spec-page
thresholds as a decomposition rule.

Every accepted gauntlet Concern must be resolved by a task, explicitly deferred
with an owner, or listed as uncovered for user decision. Put `concern_refs` on
the task; the loader carries them into card metadata.

Map target-architecture invariants through acceptance criteria and the dependency
sidecar's `safety_implements` / `safety_consumes` fields. Do not claim
`invariant_refs` or `surface_scope` as Fizzy wire fields without a live consumer.

### 4. Task and verification contract

Each task needs the following plan data:

| Data | Obligation |
|---|---|
| Identity | `task_id`, title, description, effort, and optional workstream. |
| Traceability | spec refs, `concern_refs`, and content-grounded `architecture_refs`. |
| Acceptance | At least one testable `acceptance_criteria` entry. |
| Order | `depends_on` edges whose reasons exist in the dependency sidecar. |
| Scheduling | `strategy`: `test-first`, `test-after`, `spike`, or `refactor`. Never emit `skip`. |
| Tester | `tested_by`: `llm`, `user`, or `both`; this does not assign implementation ownership. |
| Verification | `behavior_change`, `verification_mode`, `verification_scope`, and conditional evidence. |
| Existing state | `implementation_status` plus human-readable `implementation_evidence`. |

Fizzy's `_validate_plan`, `_validate_v2_task`, architecture-ref validation,
semantic-report gate, and altitude validators own machine enforcement. They
validate structure, enums, conditional evidence, reference/path shapes,
dependencies, and altitude shape. Phase 7 owns semantic judgment: correct task
boundaries, meaningful acceptance criteria, accurate refs, Concern/invariant
coverage, evidence adequacy, exceptions, and human approval.

#### Gate V1: Verification classification

Before scheduling tests, every task must have a deliberate `behavior_change`,
`verification_mode`, and compatible `verification_scope`. Surface uncertainty;
do not choose a fallback merely to complete the table.

#### Verification modes

| Mode | Scope | Conditional evidence |
|---|---|---|
| `automated-unit` | `targeted` or `full-suite` | accepted test-target alias plus `verify_commands` |
| `automated-integration` | `targeted` or `full-suite` | accepted test-target alias plus `verify_commands` |
| `automated-contract` | `targeted` or `full-suite` | accepted test-target alias plus `verify_commands` |
| `automated-component` | `targeted` or `full-suite` | accepted test-target alias plus `verify_commands` |
| `test-producer` | `targeted` or `full-suite` | `test_files` plus `verify_commands`; never exempt |
| `static-check` | `static` | `exemption_reason`; command when a validator exists |
| `artifact-sync` | `static` | `exemption_reason` |
| `manual-ux` | `manual` | `exemption_reason` |
| `system-validation` | `end-to-end` | the ConOps-bound validation leg, not relabeled test evidence |

The accepted test-target aliases are `test_targets`, `test_refs`, and
`test_files`; the validator normalizes them. Do not require a literal
`test_refs` key. Paths are repo-relative, non-empty, and cannot traverse `..`.
Verification commands are literal, runnable shell commands with the correct
working directory and test path.

The evidence rule is conditional:

- `behavior_change: true`: missing required automated targets/commands or an
  exempt mode without a reason is a validation error.
- `behavior_change: false`: the same missing evidence is a validator warning,
  not a hard failure. Phase 7 still reviews the warning and may require evidence.

Use the structured `issues` and `warnings` from `pipeline_validate_plan` as the
error authority. Do not maintain a copied error-code table here.

#### Gate V2: Mapping completeness

Before dependency analysis, confirm every task has its required evidence or
exemption, content-grounded architecture refs, implementation status/evidence,
and a valid human-execution block when applicable. This is the semantic review
that precedes the authoritative validator; it does not replace that validator.

#### Pure human execution

Use `human_execution` only when an operator must perform the work itself. It is
different from `tested_by: user`, which only says who verifies agent work.

```json
{
  "strategy": "spike",
  "behavior_change": false,
  "verification_mode": "manual-ux",
  "verification_scope": "manual",
  "tested_by": "user",
  "human_execution": {
    "scope": "dependency",
    "reason": "Why an operator must perform this action.",
    "procedure": "Ordered action, safe stop condition, and no-secret rule.",
    "evidence_destination": "Where literal outcome evidence is recorded."
  }
}
```

Choose `global` scope only when all work must stop; otherwise use `dependency`.
Start the card description with a plain-language `HUMAN ACTION:` brief covering
the action, reason, evidence, completion condition, and forbidden disclosures.

#### Test scheduling

Use test-first for risky business rules, security boundaries, external
integrations, high-severity Concerns, or architecture-safety owners. Use
test-after for bounded low-risk implementation. Use `spike` only where the plan
commits to no automated test; its independent verification mode still applies.

A REAL-DATA happy-path spine or critical seam may not use `spike` or an exempt
verification mode. Bind its accessors, owner-repo command, and negative oracle so
Phase 8 can produce trusted `run_evidence`.

### 5. Persist one checkpoint-safe plan

Use one persistence model. Atomically write the first complete decomposition to:

```text
.adversarial-spec/specs/<slug>/execution-plan.md
```

Start it with:

```markdown
> STATUS: DRAFT — pending Phase 7 plan, coverage, and exception approval.
> Not emitted to fizzy-plan.json and not loaded.
```

Record `execution_plan_path` in the active detail and pointer with atomic
detail-then-pointer writes. After approval, atomically replace the same file with
the approved content and an `APPROVED` status. Version control records the delta;
do not claim that a separate draft/final pair exists.

The plan must include the Slice North Star, root altitude and tree, Architecture
Spine, tasks, verification ladder, dependency graph, dependency semantics
summary, Concern coverage, exceptions, and uncovered obligations.

### 6. Prove dependency semantics

Keep graph semantics in sidecars, not in undocumented Fizzy task fields. Before
approval, write `dependency-semantics-draft.json` with the proposed task objects
and semantic block, then run the repository-owned analyzer:

```bash
uv run python skills/adversarial-spec/scripts/dependency_semantics.py \
  --plan .adversarial-spec/specs/<slug>/dependency-semantics-draft.json
```

It must prove the reviewed edge reasons, fanout readiness, active/deferred
scope, safety owners/consumers, and evidence receipts needed by the active
decomposition. Present that result with the plan.

After approval, preserve the semantic block in `dependency-semantics.json` and
run the analyzer again on the exact emitted plan and sidecar:

```bash
uv run python skills/adversarial-spec/scripts/dependency_semantics.py \
  --plan .adversarial-spec/specs/<slug>/fizzy-plan.json \
  --semantics .adversarial-spec/specs/<slug>/dependency-semantics.json \
  --decomposition .adversarial-spec/specs/<slug>/decomposition/d0-decomposition.json \
  --emit-report .adversarial-spec/specs/<slug>/dependency-semantics-report.json
```

Omit `--decomposition` only when the active route has no D0 artifact. Put these
root fields in the plan:

```json
{
  "semantic_contract_version": 1,
  "semantic_report_path": "dependency-semantics-report.json"
}
```

The final report must be green and bind the exact plan and ledger hashes. Fizzy's
`_check_semantic_report` verifies those hashes and analyzer floor at load. It
also rejects every reported live-spine owner whose mode is exempt/manual or
whose strategy is `spike`. Fix the plan and regenerate the report; never edit a
report to make it green.

### 7. Human approval, coverage, and exceptions

Present the complete plan, dependency summary, uncovered Concerns, and the V3/V4
reviews below. Obtain one explicit user approval only after those reviews and
before emission or load.

#### Gate V3: Coverage report

Write `.adversarial-spec/specs/<slug>/verification-coverage.json` and show its
summary. It must count tasks by behavior flag and mode, list every exemption,
and identify unmapped behavior-changing work. This file is an **agent-owned
safety gate and review artifact**; `pipeline_load` does not consume it.

- Do not load while any behavior-changing task is unmapped.
- Review validator warnings for non-behavior tasks rather than upgrading them to
  an invented machine failure.

#### Gate V4: Exception review

- Present every `artifact-sync`, `static-check`, and `manual-ux` exemption for
  acknowledgement. `test-producer` is not exempt.
- When the user changes a classification, update the task, regenerate coverage
  and dependency artifacts, and re-present the affected decision.

Record approval and exception decisions per `SKILL.md` § Decisions Log. Human
approval is not replaced by a clean validator result.

### 8. System-altitude validation draft

Run this section only when card metadata, read with explicit `board_id`, says the
system node owes the pipeline-v5+ system-validation obligation. Component and
subsystem nodes do not draft this ledger.

Phase 7 defines operational intent before implementation. Phase 8 executes the
scenarios and obtains human judgments. Verification asks whether the system was
built right; validation asks whether the right system was built.

Use `skills/adversarial-spec/scripts/validation_emission.py`. Every command emits
one JSON envelope; the script owns hashes and the planner owns prose.

```bash
uv run python skills/adversarial-spec/scripts/validation_emission.py \
  derive-conops .adversarial-spec/specs/<slug>/roadmap/manifest.json

uv run python skills/adversarial-spec/scripts/validation_emission.py \
  normalize-rows .adversarial-spec/specs/<slug>/validation-rows.json \
  --conops .adversarial-spec/specs/<slug>/roadmap/conops.md

uv run python skills/adversarial-spec/scripts/validation_emission.py \
  check-rows .adversarial-spec/specs/<slug>/validation-rows.json \
  --conops .adversarial-spec/specs/<slug>/roadmap/conops.md
```

Draft at least one active row per ConOps story. Each row needs a unique
`r-US<n>-<k>` ID, one matching `conops_ref`, an actor/trigger/action/outcome
scenario, a human-judged oracle containing both `iff` and the story ID, a valid
evidence type, and an evidence rationale. Test/CI success is not a validation
oracle. Loop normalize/check until the envelope is clean.

Commit `conops.md`, `validation-rows.json`, and the approved execution plan
together. Preserve the script-stamped `drafted_baseline_hash`; Phase 8 uses it to
surface hindsight drift.

### 9. Emit the wire plan

Inspect the active session/card metadata before choosing a schema. The current
MCP source declares:

```text
CURRENT_PIPELINE_VERSION = 6
```

Pipeline version and plan schema are separate. Existing flat schema-1/2 sessions
remain grandfathered; do not migrate or delete that route merely because new
cards use version 6.

#### Flat schema-2 compatibility branch

Retain this branch for classic/legacy flat execution plans:

```json
{
  "plan_schema_version": 2,
  "session_id": "adv-spec-...",
  "semantic_contract_version": 1,
  "semantic_report_path": "dependency-semantics-report.json",
  "tasks": [
    {
      "task_id": "T1",
      "title": "Implement the bounded behavior",
      "description": "Why this task exists and its implementation constraints.",
      "acceptance_criteria": ["The named behavior is proven at its boundary."],
      "effort": "M",
      "strategy": "test-first",
      "tested_by": "llm",
      "depends_on": [],
      "concern_refs": ["CB-1"],
      "architecture_refs": [".architecture/structured/components/example.md"],
      "behavior_change": true,
      "verification_mode": "automated-contract",
      "verification_scope": "targeted",
      "test_targets": ["TC-1"],
      "test_files": ["tests/test_example.py"],
      "verify_commands": ["uv run pytest tests/test_example.py -q"]
    }
  ]
}
```

`plan_schema_version` is always a bare JSON integer.

#### Altitude schema-3 branch

An altitude plan is a single rooted tree. Each node carries `altitude`, `parent`,
`decomposes_into`, definition refs/hashes, and exactly the verification bindings
earned by its altitude:

| Node | Required verification bindings | Shape |
|---|---|---|
| component | component | leaf; non-null parent unless it is the root |
| subsystem | component + subsystem | non-null parent; decomposes into children |
| system | component + subsystem + system | single root; null parent |

```json
{
  "plan_schema_version": 3,
  "session_id": "adv-spec-...",
  "tasks": [
    {
      "task_id": "SYS",
      "altitude": "system",
      "parent": null,
      "decomposes_into": ["SS-1"],
      "system_spec_path": ".adversarial-spec/specs/<slug>/SYS/system-spec.md",
      "spec_refs": {
        "definition_artifact": ".adversarial-spec/specs/<slug>/SYS/system-spec.md",
        "definition_hash": "<sha256 prefix>"
      },
      "verification_binding": {
        "component_verification": {"plan_artifact": "<path>", "plan_hash": "<hash>", "kind": "verification"},
        "subsystem_verification": {"plan_artifact": "<path>", "plan_hash": "<hash>", "kind": "verification"},
        "system_verification": {"plan_artifact": "<path>", "plan_hash": "<hash>", "kind": "verification"}
      }
    }
  ]
}
```

This is an altitude-field excerpt, not a standalone loadable task. Every node
also carries all common task/verification fields from §4, and the omitted child
nodes complete every `decomposes_into` reference. Prefer the emitter over
hand-authoring this shape.

Write each definition and verification-plan artifact before emission; Fizzy
re-derives the hashes from disk. Keep structural `parent` / `decomposes_into`
separate from execution-order `depends_on`. Every reviewed order constraint must
be a real edge so later-wave work cannot become ready early.

Use `mini_spec_emission.py` to emit and self-check schema 3, including requirement
metadata and the component ⊂ subsystem ⊂ system obligation chain. Then run the
live validator; the local self-check is a preflight, not permission to load
against an MCP that rejects the schema.

### 10. Validate, smoke, and load

Run dependency analysis on the exact emitted bytes, then call the authoritative
validator with explicit routing:

```text
result = pipeline_validate_plan(
  plan_path=".adversarial-spec/specs/<slug>/fizzy-plan.json",
  session_id=SESSION_ID,
  board_id=BOARD_ID,
)
```

If invalid, inspect its structured issues, fix the source plan, re-emit, and run
again until clean. Do not copy validator codes into this document and do not use
`pipeline_load` as a speculative validator.

Before load, execute every distinct `verify_commands` shape against a disposable
fixture in the owning test directory. Confirm the runner collected and ran the
named file; exit zero with zero collected tests is failure. Remove the fixture
and record command/count evidence per `SKILL.md` § Decisions Log.

Then load the already-approved plan:

```text
pipeline_load(
  plan_path=".adversarial-spec/specs/<slug>/fizzy-plan.json",
  session_id=SESSION_ID,
  board_id=BOARD_ID,
)
```

Read `pipeline_lane_state(pipeline="task", session_id=SESSION_ID,
board_id=BOARD_ID)` and confirm card count, dependencies, and expected lane.
Never use `pipeline_patch_state` to skip a load or transition fence.

`concern_refs` and architecture context already travel in card metadata and the
dispatch result. Per-card Concern comments are not a load gate. Add a bounded
operator-facing comment only when it provides information metadata cannot, and
follow `SKILL.md` § Fizzy Card Comment Convention.

When the load/readback is correct, enter middleware-creator if the approved plan
requires it; otherwise transition to implementation. See `SKILL.md` § Phase
Transition Protocol. The transition, notification, Decisions Log, and Journey
Log contracts live there and are not restated here.
