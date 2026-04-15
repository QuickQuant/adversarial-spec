# Spec: Per-Card Verification Mapping in Phase 07

## Problem

Phase 07 (Execution Planning) produces `fizzy-plan.json` files where the majority of tasks lack structured verification intent. In ETB's 38-task plan, 25 tasks had neither `test_refs` nor `test_cases` — including cards explicitly marked `test-first` and cards whose acceptance criteria mention tests.

The current Phase 07 text (line 438) says tasks without `test_refs` "should be flagged for user review." This is too weak: the flag is advisory, easily skipped, and produces plans that look valid while being under-specified for downstream enforcement.

The downstream consumer (`fizzy-pipeline-mcp`) is separately adding strict enforcement at `pipeline_load`, `pipeline_test`, and `pipeline_sweep` transitions. But it can only enforce what the plan declares. If the plan omits verification intent, the pipeline has nothing to gate on.

## Goal

Every task in `fizzy-plan.json` must declare explicit verification intent before `pipeline_load`. No task leaves Phase 07 in an ambiguous verification state.

## Non-Goals

- Changing `fizzy-pipeline-mcp` behavior (separate proposal)
- Changing Phase 08 (Implementation) or Phase 09 (Verification) workflows
- Adding runtime test execution to Phase 07 (Phase 07 plans; Phases 08-09 execute)
- Mandating specific test frameworks or tooling

## User Journey

The updated Phase 07 flow adds 4 interactive gates. Here is what the user experiences:

1. **Automated decomposition (Gates V1-V2):** The LLM decomposes tasks and assigns `behavior_change`, `verification_mode`, test mappings, and exemption reasons automatically. No user interaction required at V1/V2 unless the LLM cannot classify a task.
2. **Coverage review (Gate V3):** User sees a coverage report showing counts by mode, exempt tasks, and any unmapped behavior-changing tasks. If unmapped tasks exist, the pipeline blocks until they are resolved.
3. **Exemption review (Gate V4):** User sees all exempt tasks with their reasons. They can acknowledge (`Y`), reject (`n` to reclassify), or modify individual exemptions.
4. **Pipeline load:** Once V3-V4 pass, the plan is persisted and loaded normally.

A user producing their first v2 plan should complete all gates in a single Phase 07 run with no additional tooling.

## Schema Changes

### Plan-level version marker

Add `plan_schema_version` to the root of `fizzy-plan.json`:

```json
{
  "plan_schema_version": 2,
  "session_id": "adv-spec-...",
  "tasks": [...]
}
```

- Version 2: requires the verification block defined below.
- Version 1 (legacy): loads with warnings during migration window. Missing fields are flagged per-task but do not block `pipeline_load`.

### New fields per task in `fizzy-plan.json`

Add these fields to each task object alongside the existing `test_refs` and `strategy`:

```json
{
  "task_id": "G2-1",
  "title": "Implement trade telemetry API",
  "description": "...",
  "wave": 1,
  "effort": "M",
  "strategy": "test-after",
  "depends_on": ["W0-2"],
  "concern_refs": ["BURN-003"],

  "behavior_change": true,
  "verification_mode": "automated-contract",
  "test_refs": ["TC-5.2", "TC-5.4"],
  "test_files": ["tests/test_t5_api_contracts.py"],
  "verify_commands": ["uv run pytest tests/test_t5_api_contracts.py -q"],
  "verification_scope": "targeted",
  "verification_notes": "Trade telemetry keys must remain optional for older payloads.",
  "exemption_reason": null
}
```

### Field definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `behavior_change` | boolean | always | Whether this task modifies runtime behavior. Determines gate enforcement strictness. |
| `verification_mode` | string enum | always | How this task will be verified. Determines which other fields are required. |
| `test_refs` | string[] | conditional | References to test case IDs from `tests-spec.md` or roadmap test cases. Required when `verification_mode` starts with `automated-`. |
| `test_files` | string[] | conditional | Repo-relative test file paths expected to cover this task. Required for `automated-*` and `test-producer` modes. |
| `verify_commands` | string[] | conditional | Shell commands the tester should run. Required for `automated-*` and `test-producer` modes. |
| `verification_scope` | string enum | always | Whether verification targets this task specifically or runs the full suite. |
| `verification_notes` | string\|null | optional | Free-text notes about verification constraints, edge cases, or special considerations. |
| `exemption_reason` | string\|null | conditional | Why this task does not require automated test evidence. Required when `verification_mode` is `artifact-sync`, `static-check`, or `manual-ux`. |

### Behavior-change classification

A task is `behavior_change: true` if it modifies:
- Runtime logic or control flow
- Public interfaces, APIs, or contracts
- Data persistence semantics or migrations
- Validation or authorization behavior
- Rendering behavior or user-visible state
- Test-enforced behavior (changes that would break existing tests)

A task is `behavior_change: false` only for:
- Documentation-only changes (README, inline comments, docs/)
- Manifest or config-file sync with no runtime effect
- Formatting-only changes (whitespace, linting fixes)
- Pure metadata maintenance (labels, descriptions)

The LLM classifies `behavior_change` during task decomposition (Step 3) as a best-effort judgment. This classification is inherently subjective — reasonable engineers may disagree on edge cases like config changes with conditional runtime effects or refactors that preserve behavior. Gate V4 (Exception Review) is the explicit human correction point where the user can override any classification. The gates are LLM-enforced process guidance, not runtime enforcement — they work by structuring the LLM's workflow, not by programmatic validation.

### `verification_mode` enum values

| Mode | Meaning | Required fields |
|------|---------|-----------------|
| `automated-unit` | Verified by unit tests | `test_refs`, `test_files`, `verify_commands` |
| `automated-integration` | Verified by integration tests | `test_refs`, `test_files`, `verify_commands` |
| `automated-contract` | Verified by API contract tests | `test_refs`, `test_files`, `verify_commands` |
| `automated-component` | Verified by component tests (render, interaction) | `test_refs`, `test_files`, `verify_commands` |
| `static-check` | Verified by linter, type checker, or static analysis | `verify_commands` (optional), `exemption_reason` |
| `manual-ux` | Requires human visual/UX verification | `exemption_reason` |
| `artifact-sync` | Docs, manifests, config sync — no behavioral change | `exemption_reason` |
| `test-producer` | This task writes/expands the test suite itself | `test_files`, `verify_commands` |

### Mode-to-scope compatibility matrix

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

Invalid combinations (e.g., `automated-unit` + `manual`) are rejected at Gate V2.

### `verification_scope` enum values

| Scope | Meaning |
|-------|---------|
| `targeted` | Run only the tests declared in `verify_commands` for this task |
| `full-suite` | Run the entire test suite (e.g., `uv run pytest`) |
| `static` | No runtime tests — static analysis or manual review |
| `manual` | Human verification only |

### Path and command validation rules

- `test_files` must be repo-relative paths rooted at the git repository root (no absolute paths, no `..` traversal). Example: `tests/test_api.py`, not `/home/user/project/tests/test_api.py`.
- `verify_commands` are shell command strings (`string[]`). Each entry is a single command to be executed in a shell. They must be literal — no template interpolation (`${VAR}`), no environment variable expansion. Phase 07 stores commands; it does not execute them. Execution happens in Phase 08-09.
- Empty strings and whitespace-only strings are invalid for all required fields. `test_refs: [""]` or `exemption_reason: "  "` fail validation.

## Process Changes to Phase 07

### Soft planning rules (LLM guidance)

These rules guide the LLM during task decomposition, before any hard gate fires. They are advisory — the gates below are the enforcement layer.

1. `test-first` tasks should default to `automated-*` verification modes.
2. API, service, middleware, migration, and data-contract tasks should never be emitted without `test_refs` plus at least one `verify_commands` entry.
3. Frontend visualization cards should use a mixed model:
   - `automated-component` for data shape, render, and interaction checks
   - `manual-ux` only for the visual quality slice that cannot be asserted cheaply
4. Docs-only or manifest-sync cards should use `artifact-sync` or `static-check` with an explicit `exemption_reason`.
5. Cards whose purpose is "write the tests" should use `test-producer`, not blank `test_refs`.
6. A card with acceptance criteria that mention tests must never be emitted with an empty verification block.

### Hard gates (TodoWrite items)

Four new TodoWrite gates are inserted into the Phase 07 flow between existing steps. These gates are LLM-enforced process gates — they structure the LLM's workflow by requiring each step to complete before the next begins. They are not programmatic runtime validators. The enforcement mechanism is the TodoWrite checklist: the LLM must mark each `[GATE]` item complete (with evidence) before proceeding. Gate V4 provides the human correction point for any classification the LLM got wrong.

#### Gate V1: Verification Classification

**Position:** After Step 3 (Task Decomposition), before Step 4 (Test Strategy Assignment).

TodoWrite item:
```
{content: "Classify behavior_change and verification_mode for every task [GATE]", status: "pending", activeForm: "Classifying verification modes"}
```

**Rule:** Do not proceed until every task has `behavior_change`, `verification_mode`, and `verification_scope` assigned. The mode-to-scope compatibility matrix must be satisfied. The LLM must assign these during decomposition, not defer them.

#### Gate V2: Mapping Completeness

**Position:** After Step 4 (Test Strategy Assignment), before Step 5 (Over-Decomposition Guard).

TodoWrite item:
```
{content: "Attach test_refs, test_files, or exemption_reason for every task [GATE]", status: "pending", activeForm: "Completing verification mapping"}
```

**Rules:**
- If `verification_mode` starts with `automated-`: require non-empty `test_refs`, `test_files`, and `verify_commands`.
- If `verification_mode` is `test-producer`: require non-empty `test_files` and `verify_commands`.
- If `verification_mode` is `artifact-sync`, `static-check`, or `manual-ux`: require non-empty `exemption_reason`.
- Mode-to-scope compatibility must hold (see matrix above).
- `test_files` must be repo-relative (no absolute paths, no `..`).

**Typed validation errors:**

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

#### Gate V3: Coverage Report

**Position:** After Step 7 (Present Final Plan), before Step 8 (Persist Execution Plan). User must see coverage before approving the plan.

TodoWrite item:
```
{content: "Review verification coverage report before pipeline_load [GATE]", status: "pending", activeForm: "Reviewing verification coverage"}
```

**Rule:** Emit both a human-readable summary and a machine-readable JSON block.

Human-readable:
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

Machine-readable (persisted alongside the plan):
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

**Blocking rule:** Refuse `pipeline_load` if `unmapped_behavior_tasks` is non-empty. Non-behavior-changing tasks with no mapping produce a warning, not a block.

The coverage report JSON is written to `.adversarial-spec/specs/<slug>/verification-coverage.json` for auditability.

#### Gate V4: Exception Review

**Position:** After Gate V3, before Step 8. Must happen in the same user-approval flow.

TodoWrite item:
```
{content: "Review every exemption with the user [GATE]", status: "pending", activeForm: "Reviewing verification exemptions"}
```

**Rule:** Surface all exempt tasks explicitly:

```
Exempt Tasks (require user acknowledgement)
───────────────────────────────────────
  T5  artifact-sync   "Roadmap/manifest sync — no behavioral change"
  T9  static-check    "Config schema validated by ruff type check"
  T14 manual-ux       "Visual heatmap quality — cannot assert programmatically"
  T18 artifact-sync   "README update — docs only"

Acknowledge exemptions? [Y/n/modify]
```

Note: `test-producer` tasks are NOT exempt — they require `test_files` and `verify_commands` like automated modes. They do not appear in this exemption review.

If the user modifies an exemption (e.g., upgrades `manual-ux` to `automated-component`, or reclassifies `behavior_change`):
1. Update the affected task's fields
2. Re-validate that single task against Gate V2 rules
3. Regenerate the coverage report (Gate V3)
4. Re-present only the changed tasks for confirmation

## Special Handling by Task Type

### Docs or manifest maintenance

Examples: roadmap sync, manifest update, README changes.

These should NOT be forced into fake pytest mappings. They carry:
- `behavior_change: false`
- `verification_mode: "artifact-sync"` or `"static-check"`
- `exemption_reason` explaining why no behavioral tests apply
- `verify_commands` if a parser or validator exists (e.g., `python3 -c "import json; json.load(open('manifest.json'))"`)

### Test-writing cards

Examples: "Write Gate 1 integration tests", "Add regression suite for scoring."

These should NOT be treated as unmapped — they ARE the tests. They carry:
- `behavior_change: true` (they change test-enforced behavior)
- `verification_mode: "test-producer"`
- `test_files` for the new or expanded suite
- `verify_commands` that prove the produced suite runs (e.g., `uv run pytest tests/test_gate1.py -q`)

### Hybrid frontend cards

Examples: heatmap rendering, interactive explorer, chart components.

These should usually split verification:
- `automated-component` for data shape, render contract, and edge-case state
- A separate `manual-ux` card (or verification note) only for subjective visual polish

If a frontend card genuinely cannot be automated at all, it gets `manual-ux` with an `exemption_reason` that explains why.

## Security Considerations

- `verify_commands` are plan-time strings generated by the LLM, not user-supplied input. They are stored in JSON, not executed during Phase 07.
- Reject absolute paths in `test_files` (must be repo-relative).
- Reject path traversal (`..`) in `test_files`.
- `verify_commands` must be literal strings — no template interpolation, no environment variable expansion, no shell metacharacter injection.
- `exemption_reason` is audit metadata only — it is never evaluated as code.

## Contract with fizzy-pipeline-mcp

This spec produces the fields; fizzy-pipeline-mcp consumes them. The mapping:

| adversarial-spec field | fizzy-pipeline-mcp metadata field |
|------------------------|----------------------------------|
| `behavior_change` | `behavior_change` |
| `verification_mode` | `verification_mode` |
| `test_refs` | `declared_test_refs` |
| `test_files` | `declared_test_files` |
| `verify_commands` | `declared_verify_commands` |
| `exemption_reason` | `declared_exemption_reason` |
| `verification_scope` | `verification_scope` |

The `declared_` prefix in fizzy metadata distinguishes plan-time declarations from execution-time evidence (e.g., `executed_verify_commands`).

## Updated TodoWrite for Phase 07

The full Phase 07 TodoWrite with verification gates inserted:

```
TodoWrite([
  {content: "Load finalized spec and gauntlet concerns", status: "in_progress"},
  {content: "Scope assessment — present to user", status: "pending"},
  {content: "Load codebase architecture docs [GATE]", status: "pending"},
  {content: "Load target architecture and build Architecture Spine (if exists)", status: "pending"},
  {content: "Decompose into tasks with gauntlet concern linkage", status: "pending"},
  {content: "Classify behavior_change and verification_mode for every task [GATE]", status: "pending"},
  {content: "Assign test strategies (test-first/test-after)", status: "pending"},
  {content: "Attach test_refs, test_files, or exemption_reason for every task [GATE]", status: "pending"},
  {content: "Over-decomposition guard check", status: "pending"},
  {content: "Present plan to user for approval [GATE]", status: "pending"},
  {content: "Review verification coverage report before pipeline_load [GATE]", status: "pending"},
  {content: "Review every exemption with the user [GATE]", status: "pending"},
  {content: "Write execution plan to disk [GATE]", status: "pending"},
  {content: "Verify plan file exists and update session state", status: "pending"},
  {content: "Generate fizzy-plan.json and load into pipeline [GATE]", status: "pending"},
  {content: "Add concern context comments to all cards [GATE]", status: "pending"},
])
```

## Migration

- New plans include `plan_schema_version: 2` at the root.
- `pipeline_load` detects schema version:
  - Version 2: full validation of verification block per task.
  - Version 1 (or missing): loads with per-task warnings naming missing fields. Does not block.
- Migration window ends when the fizzy-pipeline-mcp strict mode is enabled (separate proposal's rollout step 4).
- No retroactive backfill of existing plans is required — they remain loadable with warnings.

## Acceptance Criteria

1. Phase 07 cannot emit a `behavior_change: true` task with an empty verification block.
2. Phase 07 cannot call `pipeline_load` while unmapped behavior-changing tasks exist.
3. Exemptions are explicit, typed, and surfaced for user review before plan approval.
4. Generated `fizzy-plan.json` includes `plan_schema_version: 2`. Every task includes `behavior_change`, `verification_mode`, and `verification_scope` (always required), plus the mode-specific fields per the enum table (`test_refs`, `test_files`, `verify_commands`, `exemption_reason`). Optional fields (`verification_notes`) may be omitted or null.
5. The updated TodoWrite includes all 4 verification gates (V1-V4) in the correct positions.
6. A machine-readable coverage report JSON is persisted alongside the plan.
7. Invalid mode-to-scope combinations are rejected at Gate V2 with typed error codes.
8. Backward compatibility: `plan_schema_version: 1` plans load with warnings, not errors.

## Testing Strategy

Tests for validating this spec's own implementation:

1. **Schema validation tests:** For each `verification_mode`, assert that the correct fields are required/optional. Test all 10 typed error codes trigger on invalid input (including `empty_or_whitespace_value`). Test mode-to-scope compatibility matrix rejects invalid combinations.
2. **Behavior-change classification tests:** Provide task descriptions and assert correct `behavior_change` classification. Cover edge cases: refactors that change behavior, config changes with runtime effect, test-only changes.
3. **Coverage report tests:** Generate a `fizzy-plan.json` with mixed modes. Assert the coverage report JSON matches expected counts. Assert blocking rule fires when `unmapped_behavior_tasks` is non-empty.
4. **Gate ordering tests:** Verify V1 blocks before V2, V2 blocks before over-decomposition guard, V3/V4 block before plan persistence.
5. **Migration tests:** Load a `plan_schema_version: 1` plan and assert warnings (not errors). Load a v2 plan with missing fields and assert typed errors.

## Open Questions

- Should `behavior_change` be derived from heuristics or always require explicit LLM classification? (Current: LLM classifies, user can override at Gate V4.)
- Should coverage reports be persisted for every plan generation attempt, or only the final approved version?
- Should `manual-ux` tasks require an attached reviewer identity in later phases?
- When exactly will the fizzy-pipeline-mcp migration window close? (Currently: "when strict mode is enabled" — needs a concrete trigger.)
