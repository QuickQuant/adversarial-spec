> **FIRST ACTION upon entering this phase:** Create this TodoWrite immediately.
> Do NOT read further until the TodoWrite is active.
> Every `[GATE]` item must be marked completed before proceeding past it.

```
TodoWrite([
  {content: "Load finalized spec and gauntlet concerns", status: "in_progress", activeForm: "Loading finalized spec and gauntlet concerns"},
  {content: "Scope assessment — present to user", status: "pending", activeForm: "Assessing execution scope"},
  {content: "Load codebase architecture docs [GATE] — read primer.md + matched components before any exploration", status: "pending", activeForm: "Loading codebase architecture docs"},
  {content: "Load target architecture and build Architecture Spine (if exists)", status: "pending", activeForm: "Building architecture spine"},
  {content: "Decompose into tasks with gauntlet concern linkage", status: "pending", activeForm: "Decomposing spec into tasks"},
  {content: "Classify behavior_change and verification_mode for every task [GATE]", status: "pending", activeForm: "Classifying verification modes"},
  {content: "Assign test strategies (test-first/test-after)", status: "pending", activeForm: "Assigning test strategies"},
  {content: "Attach test_refs, test_files, or exemption_reason for every task [GATE]", status: "pending", activeForm: "Completing verification mapping"},
  {content: "Over-decomposition guard check", status: "pending", activeForm: "Checking for over-decomposition"},
  {content: "Present plan to user for approval [GATE]", status: "pending", activeForm: "Presenting execution plan for approval"},
  {content: "Review verification coverage report before pipeline_load [GATE]", status: "pending", activeForm: "Reviewing verification coverage"},
  {content: "Review every exemption with the user [GATE]", status: "pending", activeForm: "Reviewing verification exemptions"},
  {content: "Write execution plan to disk [GATE]", status: "pending", activeForm: "Writing execution plan to disk"},
  {content: "Verify plan file exists and update session state", status: "pending", activeForm: "Verifying plan persistence"},
  {content: "Generate fizzy-plan.json and load into pipeline [GATE]", status: "pending", activeForm: "Loading execution plan into Fizzy pipeline"},
  {content: "Add concern context comments to all cards [GATE]", status: "pending", activeForm: "Adding concern context comments to Fizzy cards"},
])
```

Mark each step `completed` as you finish it. Mark the current step `in_progress`.

---

## Execution Planning (Phase 7)

After the spec is finalized and the gauntlet has been run, offer to generate an execution plan.

**Skipping the gauntlet is highly discouraged.** Anything that needs an execution plan should also need the thoroughness of a gauntlet review — the gauntlet generates the concrete failure-mode concerns that become acceptance criteria in the execution plan. Without it, acceptance criteria are vague and implementation bugs slip through to code review (or worse, production). At minimum, run a limited gauntlet if context is running short.

> "Spec is finalized. Would you like me to generate an execution plan for implementation?"

**Update Tasks:** Use `TaskUpdate` to mark Phase 6 tasks as `in_progress`/`completed` as you progress. Set owner to `adv-spec:planner`.

---

### Step 1: Load Inputs

You (Claude) create the execution plan directly from the spec and gauntlet output. No external pipeline needed.

**Load the finalized spec:**
- Read the spec file from the session's `spec_path` or the most recent `[SPEC]...[/SPEC]` output

**Load gauntlet concerns (if gauntlet was run):**
```bash
# Find the most recent gauntlet concerns JSON
ls -t .adversarial-spec/specs/*/gauntlet-concerns-*.json 2>/dev/null | head -1
```

If found, read the JSON. Each concern has:
- `adversary`: Which adversary raised it
- `severity`: critical / high / medium / low
- `section_refs`: Which spec sections it targets
- `failure_mode`: What could go wrong
- `detection`: How to detect the failure
- `blast_radius`: Impact scope

---

### Step 2: Scope Assessment

Read through the spec and assess scope before decomposing:

**Guidelines:**
- **Small** (< 5 expected tasks): Single agent, sequential execution. No workstreams needed.
- **Medium** (5-15 tasks): Single agent with logical workstreams. Group by component/layer.
- **Large** (15+ tasks): Consider multi-agent execution. Identify independent workstreams that can run in parallel.

Present the assessment:
```
Scope Assessment
───────────────────────────────────────
Spec sections: N
Gauntlet concerns: M (X critical, Y high)
Estimated tasks: ~Z
Recommendation: [single-agent | single-agent with workstreams | multi-agent]

Proceed with task decomposition? [Y/n]
```

---

### Step 2.5: Load Codebase Architecture (REQUIRED before decomposition)

**Do NOT decompose into tasks, launch Explore agents, or glob/grep the codebase until you have read the architecture docs.** The architecture docs tell you what components exist, what contracts matter, and what gotchas to avoid. Without them, you will invent file structures that conflict with the existing codebase.

**Load project architecture docs:**
```bash
# Check for architecture docs
[ -f .architecture/manifest.json ] && echo "exists" || echo "missing"
```

If `.architecture/manifest.json` exists:
1. Read `.architecture/INDEX.md` — for YOUR navigation only (component table, key files)
2. Read `.architecture/primer.md` — system summary, components, contracts, gotchas
3. Match the spec's scope against the INDEX component table:
   - Which components does the spec touch?
   - Which key files will need modification?
4. Read 2-4 matched component docs from `.architecture/structured/components/`
5. If the spec crosses component boundaries: read `.architecture/structured/flows.md`
6. If the spec touches known debt: read `.architecture/concerns.md`

If `.architecture/` does NOT exist:
- Warn the user: "No architecture docs found. Consider running `/mapcodebase` first."
- If proceeding without: use targeted file reads (not broad Explore agents) to understand the blast zone

**Then load target architecture (from Phase 4, if it exists):**
```bash
# Check for target architecture from Phase 4
ls .adversarial-spec/specs/*/target-architecture.md 2>/dev/null | head -1
```

**Staleness check (REQUIRED when target architecture exists):**

Phase 4 records a `phase_artifacts` block in the session detail file with `spec_fingerprint` (SHA256 of the spec file at the time Phase 4 published) and `architecture_fingerprint`. Before consuming the target architecture, Phase 7 MUST verify that the spec has not drifted:

1. Read `phase_artifacts.spec_fingerprint` from the session detail file
2. Compute the current spec's SHA256 and compare
3. **If fingerprints match:** target architecture is fresh — proceed with consumption
4. **If fingerprints do NOT match:** target architecture is stale
   - Block with a clear message: "Spec has changed since Phase 4 published target architecture (old fingerprint `<hash>`, current `<hash>`). Rerun Phase 4 to refresh target-architecture.md, middleware-candidates.json, and invariant set, or explicitly acknowledge the drift to continue."
   - If the user explicitly acknowledges the drift (interactive confirmation or equivalent session-level override), log the acknowledgement to the session journey and proceed with a warning banner in the execution plan noting the known drift. No CLI flag for this is defined in v17 — the acknowledgement path is ad-hoc until a formal override is specified.
5. Normative source for the fingerprint contract: [`04-target-architecture.md` §7 (Required Headers)](./04-target-architecture.md) and [`04-target-architecture.md` §15 (Session Mutation Contract)](./04-target-architecture.md). Phase 7 MUST NOT mutate `architecture_fingerprint` or `spec_fingerprint` — those are set by Phase 4 and read-only here.

**Consume middleware candidates (when present — advisory only in v17):**

If Phase 4 identified shared middleware (cross-cutting code surfaces that multiple tasks would otherwise duplicate), it publishes `middleware-candidates.json` alongside the target architecture:

```bash
ls .adversarial-spec/specs/*/middleware-candidates.json 2>/dev/null | head -1
```

**Important:** [`04-target-architecture.md` §0](./04-target-architecture.md) declares that until the `middleware-creator` phase is registered in SKILL.md's router and authored, `middleware-candidates.json` is a **passive artifact with no active consumer**. The normative consumer is the middleware-creator phase, not Phase 7. In v17, Phase 7's role is strictly advisory:

- **Every tier (simple, medium, complex):** Surface the candidates in the plan's "Uncovered Concerns / Advisory" section so the user can see what Phase 4 identified. Do NOT auto-create Wave 0 tasks from `middleware-candidates.json` — that materialization is reserved for the middleware-creator phase once it is registered and authored.
- If the user explicitly asks Phase 7 to promote a candidate into a Wave 0 task, record it as a user-initiated decision in the session journey. The default remains "surface only".

If `middleware-candidates.json` is missing entirely (Phase 4 found no shared surfaces), skip this step — not every project needs middleware.

If found, extract cross-cutting patterns and add an Architecture Spine section to the execution plan:

```markdown
## Architecture Spine
Cross-cutting patterns from the Target Architecture. All tasks must follow.

### [Pattern Name]
- **Pattern:** [one-line description]
- **Rule:** [what implementers must / must not do]
- **Reference:** Target Architecture §[N], Task W0-[N]
```

**Wave 0: Architecture Foundation**

Create tasks establishing shared infrastructure BEFORE feature tasks:
- One task per pattern in the Target Architecture
- Wave 0 tasks block all feature tasks depending on the pattern
- Typical: 4-8 tasks, S-M effort

Example:
```
Wave 0 Tasks
───────────────────────────────────────
W0-1  Establish data fetching pattern     S   Blocks: Tasks 3, 5, 8
W0-2  Implement auth middleware           M   Blocks: Tasks 4, 6, 7
W0-3  Set up shared error handling        S   Blocks: All feature tasks
W0-4  Create component boundary template  S   Blocks: Tasks 3, 4, 5
```

**If no target architecture exists:** Skip Architecture Spine and Wave 0. Proceed directly to Task Decomposition.

---

### Verification Schema (v2) — Reference

**This section defines the verification contract every task in `fizzy-plan.json` must satisfy.** It is read once before decomposition (Step 3) and referenced by Gates V1-V4 and Step 9. The schema is LLM-enforced via TodoWrite gates, not runtime-validated by fizzy-pipeline-mcp; the gates work by structuring the LLM's workflow, not by programmatic enforcement.

**Plan-level version marker** — add to the root of `fizzy-plan.json`:

```json
{
  "plan_schema_version": 2,
  "session_id": "adv-spec-...",
  "tasks": [...]
}
```

- Version 2: requires the verification block below per task.
- Version 1 (legacy): loads with warnings during the migration window. Missing fields are flagged per-task but do not block `pipeline_load`.

**Per-task verification block** — add these fields to each task object:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `behavior_change` | boolean | always | Whether this task modifies runtime behavior. Determines gate enforcement strictness. |
| `verification_mode` | string enum | always | How this task will be verified. Determines which other fields are required. |
| `verification_scope` | string enum | always | Whether verification targets this task specifically or runs the full suite. |
| `test_refs` | string[] | conditional | Test case IDs from `tests-spec.md` or roadmap. Required when `verification_mode` starts with `automated-`. |
| `test_files` | string[] | conditional | Repo-relative test file paths expected to cover this task. Required for `automated-*` and `test-producer`. |
| `verify_commands` | string[] | conditional | Shell command strings the tester runs. Required for `automated-*` and `test-producer`. |
| `verification_notes` | string\|null | optional | Free-text notes about constraints, edge cases, or special considerations. |
| `exemption_reason` | string\|null | conditional | Why this task does not require automated test evidence. Required for `artifact-sync`, `static-check`, `manual-ux`. |

**`verification_mode` enum values:**

| Mode | Meaning | Required fields (beyond always-required) |
|------|---------|------------------------------------------|
| `automated-unit` | Verified by unit tests | `test_refs`, `test_files`, `verify_commands` |
| `automated-integration` | Verified by integration tests | `test_refs`, `test_files`, `verify_commands` |
| `automated-contract` | Verified by API contract tests | `test_refs`, `test_files`, `verify_commands` |
| `automated-component` | Verified by component tests (render, interaction) | `test_refs`, `test_files`, `verify_commands` |
| `static-check` | Verified by linter, type checker, or static analysis | `exemption_reason` (`verify_commands` optional if a validator exists) |
| `manual-ux` | Requires human visual/UX verification | `exemption_reason` |
| `artifact-sync` | Docs, manifests, config sync — no behavioral change | `exemption_reason` |
| `test-producer` | This task writes/expands the test suite itself | `test_files`, `verify_commands` (NOT exempt) |

**Important:** `test-producer` is NOT exempt. A task whose job is "write the tests" still requires concrete `test_files` and `verify_commands` proving the produced suite runs. It never gets an `exemption_reason`.

**`verification_scope` enum values:**

| Scope | Meaning |
|-------|---------|
| `targeted` | Run only the tests declared in `verify_commands` for this task |
| `full-suite` | Run the entire test suite (e.g., `uv run pytest`) |
| `static` | No runtime tests — static analysis or manual review |
| `manual` | Human verification only |

**Mode-to-scope compatibility matrix:**

| `verification_mode` | Valid `verification_scope` values |
|---------------------|----------------------------------|
| `automated-unit` | `targeted`, `full-suite` |
| `automated-integration` | `targeted`, `full-suite` |
| `automated-contract` | `targeted`, `full-suite` |
| `automated-component` | `targeted`, `full-suite` |
| `static-check` | `static` |
| `manual-ux` | `manual` |
| `artifact-sync` | `static` |
| `test-producer` | `targeted`, `full-suite` |

Invalid combinations (e.g., `automated-unit` + `manual`, or `static-check` + `targeted`) are rejected at Gate V2.

**Path and command validation rules:**

- `test_files` must be repo-relative paths rooted at the git repository root. No absolute paths, no `..` traversal. Example: `tests/test_api.py`, not `/home/user/project/tests/test_api.py`.
- `verify_commands` are shell command strings (`string[]`). Each entry is a single command to be executed in a shell. They must be literal — no template interpolation (`${VAR}`), no environment variable expansion. Phase 07 stores commands; Phase 08-09 execute them.
- Empty strings and whitespace-only strings are invalid for all required fields. `test_refs: [""]` or `exemption_reason: "  "` fail validation.

**Typed validation error codes** (used in Gate V2 and coverage report):

| Error code | Meaning |
|------------|---------|
| `missing_verification_mode` | Task has no `verification_mode` |
| `missing_verification_scope` | Task has no `verification_scope` |
| `missing_behavior_change` | Task has no `behavior_change` classification |
| `missing_required_test_refs` | `automated-*` task with empty `test_refs` |
| `missing_required_test_files` | `automated-*` or `test-producer` task with empty `test_files` |
| `missing_required_verify_commands` | `automated-*` or `test-producer` task with empty `verify_commands` |
| `missing_exemption_reason` | Exempt mode with no `exemption_reason` |
| `invalid_scope_for_mode` | `verification_scope` not in the valid set for `verification_mode` |
| `invalid_test_file_path` | Path is absolute or contains `..` traversal |
| `empty_or_whitespace_value` | A required field contains an empty or whitespace-only string |

Each error identifies the affected `task_id`.

**Behavior-change classification criteria:**

A task is `behavior_change: true` if it modifies any of:
- Runtime logic or control flow
- Public interfaces, APIs, or contracts
- Data persistence semantics or migrations
- Validation or authorization behavior
- Rendering behavior or user-visible state
- Test-enforced behavior (changes that would break existing tests)

A task is `behavior_change: false` only for:
- Documentation-only changes (README, inline comments, `docs/`)
- Manifest or config-file sync with no runtime effect
- Formatting-only changes (whitespace, linting fixes)
- Pure metadata maintenance (labels, descriptions)

This classification is a best-effort LLM judgment. Edge cases (config with conditional runtime effects, refactors that preserve behavior) are inherently subjective. **Gate V4 (Exception Review) is the explicit human correction point** where the user can override any classification the LLM got wrong.

**Contract with fizzy-pipeline-mcp:** fizzy consumes these fields with a `declared_` prefix to distinguish plan-time declarations from execution-time evidence. `test_refs` and `test_files` stay distinct in the plan, but fizzy may persist them as one declared target bundle. Field mapping:

| adversarial-spec field | fizzy metadata field |
|------------------------|----------------------|
| `behavior_change` | `behavior_change` |
| `verification_mode` | `verification_mode` |
| `test_refs`, `test_files` | `declared_test_targets` |
| `verify_commands` | `declared_verify_commands` |
| `exemption_reason` | `declared_exemption_reason` |
| `verification_scope` | `verification_scope` |

---

### Step 3: Task Decomposition

Create implementation tasks from the spec. For each major spec section or feature:

**Decomposition guidelines:**
- Target **1-4 hours of work per task**
- Each task should be independently testable
- Group related work (e.g., all error codes in one task, not 20 separate tasks)
- Include setup/infrastructure tasks (project scaffold, dependencies, config)

**For each task, specify:**
- **Title**: Short, action-oriented (e.g., "Implement order placement endpoint")
- **Description**: What to build, referencing specific spec sections
- **Spec references**: Which sections this task implements
- **Acceptance criteria**: Derived from spec requirements AND gauntlet concerns
- **Test strategy**: test-first or test-after (see Step 4)
- **Dependencies**: Which tasks must complete before this one
- **Effort estimate**: S (< 1hr), M (1-4hr), L (4-8hr)

**Link gauntlet concerns to tasks:**
For each concern in the gauntlet JSON, match its `section_refs` to your tasks. When a concern maps to a task:
- Add the concern's `failure_mode` as an acceptance criterion
- Add the concern's `detection` strategy as a test case
- Note the concern severity - critical/high concerns make the task higher risk

**Link target-architecture invariants and surfaces to tasks (when Phase 4 ran):**

Each task's metadata MUST reference the invariant IDs and surface scope it touches. Read [`04-target-architecture.md` §8 (invariants)](./04-target-architecture.md) and §6 (concern x surface matrix), then for every task add:
- `invariant_refs`: list of invariant IDs (e.g. `INV-7`, `INV-12`) whose protection the task's code paths must preserve. An invariant applies to a task when any of its enforcing surfaces, data flows, or guarded modules intersect the task's declared file scope.
- `surface_scope`: list of surface IDs from §6 canonical enums (`cli_command`, `public_api`, `data_stream`, etc.) that the task exposes or mutates.

Surface the linkage in the task entry so reviewers can audit coverage:
```markdown
- **Invariants touched:** INV-3, INV-7, INV-12
- **Surfaces:** public_api, data_stream
```

**Invariant coverage check:** After decomposition, every invariant listed in §8 MUST be referenced by at least one task. If an invariant has no task, either it is out of scope (document why in the "Uncovered Concerns" section) or you missed a task — revisit decomposition.

---

### Gate V1: Verification Classification

**Position:** After Step 3 (Task Decomposition), before Step 4 (Test Strategy Assignment).

**TodoWrite item:**
```
{content: "Classify behavior_change and verification_mode for every task [GATE]", status: "pending", activeForm: "Classifying verification modes"}
```

**Rule:** Do not proceed until every task in your decomposition has:
- `behavior_change` (boolean, per the classification criteria in the Verification Schema reference)
- `verification_mode` (one of the 8 enum values)
- `verification_scope` (must be valid for the chosen mode per the compatibility matrix)

Assign these **during decomposition**, not as a deferred second pass. If you cannot confidently classify a task, surface it explicitly rather than picking a fallback mode.

**Nature of this gate:** This is an LLM-enforced process gate that structures your workflow. It is not a runtime validator — no code checks the output. The enforcement mechanism is the TodoWrite checklist: mark V1 `completed` only when every task in your internal list has all three fields assigned. Gate V4 is the human correction point for any classification that turns out to be wrong.

**[GATE] TodoWrite: Mark "Classify behavior_change and verification_mode for every task" completed before proceeding to Step 4.**

---

### Step 4: Test Strategy Assignment

Assign test-first or test-after to each task based on risk:

**Use test-first when:**
- Task has 3+ gauntlet concerns linked to it
- Any linked concern is critical or high severity
- **Task has 3+ `invariant_refs` from `04-target-architecture.md` §8** — high-invariant-density tasks are inherently high-risk and MUST be test-first regardless of concern count
- Task involves security-sensitive logic
- Task implements complex business rules
- Task has external API integrations
- Task is large effort (L/XL) regardless of concern count — larger tasks have more surface area for bugs
- Acceptance criteria contain vague terms ("good performance", "fast", "better UX") — vagueness needs test anchoring

**Use test-after when:**
- Task is low-risk (0-2 low/medium concerns)
- Task is primarily CRUD or boilerplate
- Task is infrastructure/setup

**Skip tests (no strategy) when:**
- Task is pure documentation (README, docs, comments)
- Task is configuration-only (env vars, deploy config, CI setup)
- Task is a rename/move with no logic changes

Present as a table:
```
Test Strategy
───────────────────────────────────────
Task                          | Strategy    | Reason
Implement auth middleware     | test-first  | 3 concerns (1 critical)
Create DB schema             | test-after  | 0 concerns, standard CRUD
Implement order placement    | test-first  | 5 concerns (2 high)
Add error response codes     | test-after  | 1 low concern
```

---

### Gate V2: Mapping Completeness

**Position:** After Step 4 (Test Strategy Assignment), before Step 5 (Over-Decomposition Guard).

**TodoWrite item:**
```
{content: "Attach test_refs, test_files, or exemption_reason for every task [GATE]", status: "pending", activeForm: "Completing verification mapping"}
```

**Rules** (must all hold for every task):

- If `verification_mode` starts with `automated-`: require non-empty `test_refs`, non-empty `test_files`, and non-empty `verify_commands`.
- If `verification_mode` is `test-producer`: require non-empty `test_files` and non-empty `verify_commands`. (`test-producer` is NOT exempt.)
- If `verification_mode` is `artifact-sync`, `static-check`, or `manual-ux`: require non-empty `exemption_reason`.
- Mode-to-scope compatibility must hold per the Verification Schema matrix.
- `test_files` paths must be repo-relative (no absolute paths, no `..` traversal).
- `verify_commands` must be literal shell strings (no template interpolation).
- No required field may be empty or whitespace-only. Array entries such as `test_refs: ["  "]` still fail this gate.

**Typed validation errors** (surface these by `task_id` when they fire):

Refer to the "Typed validation error codes" table in the Verification Schema reference. The 10 codes are:
`missing_verification_mode`, `missing_verification_scope`, `missing_behavior_change`, `missing_required_test_refs`, `missing_required_test_files`, `missing_required_verify_commands`, `missing_exemption_reason`, `invalid_scope_for_mode`, `invalid_test_file_path`, `empty_or_whitespace_value`.

**Nature of this gate:** LLM-enforced process gate. Mark V2 `completed` only when every task satisfies all rules above. If any task fails a rule, either fix the task's verification block or surface the failure explicitly and loop back to Step 3/4 to reclassify.

**[GATE] TodoWrite: Mark "Attach test_refs, test_files, or exemption_reason for every task" completed before proceeding to Step 5.**

---

### Step 5: Over-Decomposition Guard

Before presenting the plan, check for over-decomposition:

**Warning thresholds:**
- If task count > **2x the number of spec sections**, you may be over-decomposing
- If task count > **15 for a simple spec** (< 3 pages), consolidate
- If multiple tasks target the **same spec section** with S effort, merge them

**If threshold exceeded:**
```
⚠️ Over-Decomposition Warning
───────────────────────────────────────
Tasks: 28 (threshold: ~16 based on 8 spec sections)

Suggested consolidations:
• "Create User model" + "Add User validation" + "Add User serialization"
  → "Implement User model with validation"
• "Add GET /users" + "Add POST /users" + "Add DELETE /users"
  → "Implement /users CRUD endpoints"

Apply consolidations? [Y/n/customize]
```

---

### Step 6: Parallelization Analysis

For medium/large plans, identify independent workstreams:

**Guidelines:**
- Tasks with no dependency relationship can run in parallel
- Group into workstreams by component (backend, frontend, infra)
- Identify merge points where workstreams must synchronize
- Order merge sequence by risk (merge highest-risk stream first for early feedback)

**Present workstreams:**
```
Parallelization Plan
───────────────────────────────────────
Stream A (Backend): Tasks 1, 3, 5, 7
Stream B (Frontend): Tasks 2, 4, 6
Stream C (Infra): Tasks 8, 9

Merge points:
• After Task 5 + Task 9: Backend needs infra (medium risk)
• After Task 7 + Task 6: Integration testing (high risk)

Branch pattern: feature/<stream>-<task> → develop → main
```

---

### Step 7: Present Final Plan

Output the execution plan in this format:

```markdown
# Execution Plan: [Project Name]

## Summary
- Tasks: N (S: X, M: Y, L: Z)
- Workstreams: W
- Gauntlet concerns addressed: C of T
- Estimated effort: [range]

## Tasks

### [Workstream A]

#### Task 1: [Title]
- **Effort:** M
- **Strategy:** test-first
- **Spec refs:** Section 3.1, 3.2
- **Concerns:** PARA-abc (critical), BURN-def (high)
- **Acceptance criteria:**
  - [ ] [From spec: requirement]
  - [ ] [From concern PARA-abc: failure mode addressed]
- **Dependencies:** None
- **Test cases:**
  - [From concern detection strategy]

#### Task 2: [Title]
...

## Dependency Graph
Task 1 → Task 3 → Task 5
Task 2 → Task 4
Task 8 → Task 5 (merge point)

## Uncovered Concerns
[List any gauntlet concerns that don't map to tasks - these need attention]
```

**After presenting:**
> "Execution plan ready with N tasks across W workstreams. M gauntlet concerns linked.
> Any concerns not covered? Want to adjust task granularity or workstream assignments?"

Wait for user approval before proceeding to Step 8.

**[GATE] TodoWrite: Mark "Present plan to user for approval" completed before proceeding to Gate V3.**

---

### Gate V3: Coverage Report

**Position:** After Step 7 (Present Final Plan), before Step 8 (Persist Execution Plan). The user must see coverage before approving the plan for persistence.

**TodoWrite item:**
```
{content: "Review verification coverage report before pipeline_load [GATE]", status: "pending", activeForm: "Reviewing verification coverage"}
```

**Rule:** Emit both a human-readable summary AND a machine-readable JSON block. Write the JSON to `.adversarial-spec/specs/<slug>/verification-coverage.json` alongside the execution plan.

**Human-readable format:**

```
Verification Coverage Report
───────────────────────────────────────
Total tasks:              38
Behavior-changing:        23
Non-behavior-changing:    15

By mode:
  automated-unit:          8
  automated-integration:   5
  automated-contract:      4
  automated-component:     3
  static-check:            2
  artifact-sync:           6
  test-producer:           3
  manual-ux:               4
  UNMAPPED:                3  ← BLOCKING

Unmapped behavior-changing tasks:
  T12: "Update config loader" — has AC mentioning tests
  T15: "Add retry logic" — behavior-changing, no verification
  T22: "Frontend polish" — needs at least manual-ux classification
```

**Machine-readable JSON** (persist to `.adversarial-spec/specs/<slug>/verification-coverage.json`):

```json
{
  "report_schema_version": 1,
  "total_tasks": 38,
  "behavior_changing_count": 23,
  "non_behavior_changing_count": 15,
  "counts_by_mode": {
    "automated-unit": 8,
    "automated-integration": 5,
    "automated-contract": 4,
    "automated-component": 3,
    "static-check": 2,
    "artifact-sync": 6,
    "test-producer": 3,
    "manual-ux": 4
  },
  "exempt_tasks": [
    {"task_id": "T5", "mode": "artifact-sync", "reason": "Roadmap/manifest sync"},
    {"task_id": "T9", "mode": "static-check", "reason": "Config schema validated by ruff"}
  ],
  "unmapped_behavior_tasks": ["T12", "T15", "T22"],
  "unmapped_non_behavior_tasks": [],
  "validation_errors": []
}
```

**Blocking rule:** Refuse `pipeline_load` if `unmapped_behavior_tasks` is non-empty. Non-behavior-changing tasks with no mapping produce a warning, not a block. `validation_errors` must be empty or Gate V2 was skipped in error — loop back to V2.

**Nature of this gate:** LLM-enforced process gate. Mark V3 `completed` only after the JSON file exists on disk at the declared path AND the human-readable summary has been shown to the user.

**[GATE] TodoWrite: Mark "Review verification coverage report before pipeline_load" completed before proceeding to Gate V4.**

---

### Gate V4: Exception Review

**Position:** After Gate V3, before Step 8 (Persist Execution Plan). Must happen in the same user-approval flow as V3.

**TodoWrite item:**
```
{content: "Review every exemption with the user [GATE]", status: "pending", activeForm: "Reviewing verification exemptions"}
```

**Rule:** Surface all exempt tasks explicitly to the user. Exempt modes are `artifact-sync`, `static-check`, and `manual-ux`. **`test-producer` tasks are NOT exempt** and do not appear in this review — they require `test_files` and `verify_commands` like automated modes.

**Presentation format:**

```
Exempt Tasks (require user acknowledgement)
───────────────────────────────────────
  T5  artifact-sync   "Roadmap/manifest sync — no behavioral change"
  T9  static-check    "Config schema validated by ruff type check"
  T14 manual-ux       "Visual heatmap quality — cannot assert programmatically"
  T18 artifact-sync   "README update — docs only"

Acknowledge exemptions? [Y/n/modify]
```

**User response handling:**

- `Y` — proceed to Step 8.
- `n` — loop back to Step 3 to reclassify one or more tasks.
- `modify` — for each task the user corrects:
  1. Update the affected task's fields (mode, scope, test_refs, exemption_reason, or `behavior_change`)
  2. Re-validate that single task against Gate V2 rules
  3. Regenerate `verification-coverage.json` (Gate V3)
  4. Re-present only the changed tasks for confirmation

**Nature of this gate:** This is the human correction point for any classification the LLM got wrong at Gate V1 or V2. The gate is LLM-enforced only in the sense that the LLM must ask; the *answer* is a human decision. Record the user's acknowledgement in the session journey.

**[GATE] TodoWrite: Mark "Review every exemption with the user" completed before proceeding to Step 8.**

---

### Step 8: Persist Execution Plan

**This step is REQUIRED before checkpoint or phase transition.** The plan must be on disk, not just in conversation output. A fresh agent (new conversation, Codex, or any other tool) cannot recover inline-only plans.

**Write the execution plan to:**
```
.adversarial-spec/specs/<slug>/execution-plan.md
```

Where `<slug>` is the context name slugified (same as the manifest directory).

**Use atomic write** (temp file + rename) to prevent corruption.

**Update session detail file:**
```json
{
  "execution_plan_path": ".adversarial-spec/specs/<slug>/execution-plan.md"
}
```

**Update pointer file** (`session-state.json`) to include the same `execution_plan_path` for consistency.

**Verify before proceeding:**
- File exists on disk
- File is non-empty
- Path recorded in session detail file

**[GATE] TodoWrite: Mark "Write execution plan to disk" completed before proceeding to Step 9.**

---

### Step 9: Load into Fizzy Pipeline

**This step connects the execution plan to the self-pickup loop.** Without it, cards are just text on disk — no agent can pick them up via `pipeline_do_next_task`.

**Prerequisites:** Gates V3 (Coverage Report) and V4 (Exception Review) must be completed. Do not invoke `pipeline_load` while `unmapped_behavior_tasks` in `verification-coverage.json` is non-empty.

**Generate `fizzy-plan.json`:**

Write a JSON file alongside the execution plan:
```
.adversarial-spec/specs/<slug>/fizzy-plan.json
```

The JSON must follow the v2 pipeline schema. The root includes `plan_schema_version: 2` and every task carries the verification block defined in the Verification Schema (v2) reference:

```json
{
  "plan_schema_version": 2,
  "session_id": "<active_session_id from session-state.json>",
  "tasks": [
    {
      "task_id": "T1",
      "title": "Implement trade telemetry API",
      "description": "Full task description with acceptance criteria",
      "wave": 0,
      "effort": "M",
      "strategy": "test-first",
      "depends_on": [],
      "concern_refs": ["PARA-abc", "BURN-def"],
      "invariant_refs": ["INV-3", "INV-7"],
      "surface_scope": ["public_api", "data_stream"],

      "behavior_change": true,
      "verification_mode": "automated-contract",
      "verification_scope": "targeted",
      "test_refs": ["TC-5.2", "TC-5.4"],
      "test_files": ["tests/test_t5_api_contracts.py"],
      "verify_commands": ["uv run pytest tests/test_t5_api_contracts.py -q"],
      "verification_notes": "Trade telemetry keys must remain optional for older payloads.",
      "exemption_reason": null
    },
    {
      "task_id": "T2",
      "title": "Update roadmap manifest",
      "description": "Sync roadmap.json with Wave 1 task IDs",
      "wave": 1,
      "effort": "S",
      "strategy": "test-after",
      "depends_on": ["T1"],
      "concern_refs": [],
      "invariant_refs": [],
      "surface_scope": [],

      "behavior_change": false,
      "verification_mode": "artifact-sync",
      "verification_scope": "static",
      "test_refs": [],
      "test_files": [],
      "verify_commands": [],
      "verification_notes": null,
      "exemption_reason": "Roadmap/manifest sync — no runtime effect"
    }
  ]
}
```

**Field mapping from execution plan:**

Core fields (unchanged from v1):
- `task_id`: Task numbering from the plan (T1, T2, ... or W0-1, W1-1, etc.)
- `title`: Task title
- `description`: Full description including acceptance criteria
- `wave`: Wave number from the plan
- `effort`: S / M / L
- `strategy`: test-first / test-after / skip
- `depends_on`: List of task_ids this task depends on (from dependency graph)
- `concern_refs`: List of gauntlet concern IDs linked to this task
- `invariant_refs`, `surface_scope`: Populated when Phase 4 ran (see Step 3)

Verification block fields (v2, see Verification Schema reference above for full semantics):
- `behavior_change`, `verification_mode`, `verification_scope`: always required
- `test_refs`, `test_files`, `verify_commands`: required per mode
- `exemption_reason`: required for exempt modes (`artifact-sync`, `static-check`, `manual-ux`)
- `verification_notes`: optional free-text

**Plan-level version marker:** include `plan_schema_version: 2` at the root. fizzy-pipeline-mcp uses this to select the strict validation path at `pipeline_load`. Plans missing this marker (or with version `1`) load with warnings during the migration window.

**Emit verification-coverage.json:** If Gate V3 did not already write it, write the coverage report to `.adversarial-spec/specs/<slug>/verification-coverage.json` now using the `report_schema_version: 1` shape documented in Gate V3.

**Load into pipeline:**
```
pipeline_load(
  plan_path = ".adversarial-spec/specs/<slug>/fizzy-plan.json",
  session_id = "<active_session_id>",
  board_id = BOARD_ID
)
```

This creates cards in the **New Todo** lane with proper state blocks. `pipeline_do_next_task` can now walk these cards, check dependencies, and assign them to agents.

**Verify:**
```
pipeline_lane_state(pipeline="task", board_id=BOARD_ID)
```

Confirm cards appear in New Todo with correct count.

**[GATE] TodoWrite: Mark "Generate fizzy-plan.json and load into pipeline" completed before proceeding to Step 10.**

---

### Step 10: Add Concern Context Comments to Cards

**This step makes each card self-contained for human readers.** Without it, a person opening a single Fizzy card sees acceptance criteria but has no idea WHY the task exists, what production problem it prevents, or which gauntlet findings shaped the approach. They'd have to read the full spec to orient — defeating the purpose of card-level task breakdown.

**For each card created in Step 9, add a comment that includes:**

1. **Which concern(s) it addresses** — e.g., "CON-001: Gateway token refresh has no mutex"
2. **The problem in plain language** — what's broken, what happened (production incidents, data corruption, etc.)
3. **Why the fix takes this shape** — key gauntlet findings that constrained the approach (e.g., "gauntlet FM-2: can't cross-package import because gateway tsconfig restricts rootDir")
4. **How it connects to other cards** — dependencies, fallback relationships (e.g., "if this task's transition fails, T8's stuck detector catches it as the safe fallback")

**Format:**
```
**Context: CON-XXX — [short problem description]**

[1-3 paragraphs: what's broken, what the fix does, which gauntlet findings matter]
```

**Guidelines:**
- Write for a human who will read ONE card, not the full spec
- Include gauntlet concern IDs (e.g., RC-1, FM-2) so they can trace back to the gauntlet findings doc
- For prerequisite/audit tasks (no concern), explain what downstream tasks need from this one
- Keep each comment under 200 words — enough to orient, not a spec restatement

**Efficiency:** All card comments are independent — make all `add_comment` calls in parallel.

**[GATE] TodoWrite: Mark "Add concern context comments to cards" completed before proceeding to Phase 8 (Implementation).**

Only after concern context comments: proceed to Phase 8 (Implementation).
