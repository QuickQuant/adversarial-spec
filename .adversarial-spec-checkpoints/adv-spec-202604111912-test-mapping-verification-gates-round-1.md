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

## Schema Changes

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
| `verification_mode` | string enum | always | How this task will be verified. Determines which other fields are required. |
| `test_refs` | string[] | conditional | References to test case IDs from `tests-spec.md` or roadmap test cases. Required when `verification_mode` starts with `automated-`. |
| `test_files` | string[] | conditional | Concrete test file paths expected to cover this task. Required for `automated-*` and `test-producer` modes. |
| `verify_commands` | string[] | conditional | Shell commands the tester should run. Required for `automated-*` and `test-producer` modes. |
| `verification_scope` | string enum | always | Whether verification targets this task specifically or runs the full suite. Values: `targeted`, `full-suite`, `static`, `manual`. |
| `verification_notes` | string | optional | Free-text notes about verification constraints, edge cases, or special considerations. |
| `exemption_reason` | string | conditional | Why this task does not require automated test evidence. Required when `verification_mode` is `artifact-sync`, `static-check`, or `manual-ux`. |

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

### `verification_scope` enum values

| Scope | Meaning |
|-------|---------|
| `targeted` | Run only the tests declared in `verify_commands` for this task |
| `full-suite` | Run the entire test suite (e.g., `uv run pytest`) |
| `static` | No runtime tests — static analysis or manual review |
| `manual` | Human verification only |

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

Four new TodoWrite gates are inserted into the Phase 07 flow between existing steps.

#### Gate V1: Verification Classification

**Position:** After Step 3 (Task Decomposition), before Step 4 (Test Strategy Assignment).

TodoWrite item:
```
{content: "Classify verification_mode for every task [GATE]", status: "pending", activeForm: "Classifying verification modes"}
```

**Rule:** Do not proceed until every task has a `verification_mode` and `verification_scope`. The LLM must assign these during decomposition, not defer them.

#### Gate V2: Mapping Completeness

**Position:** After Step 4 (Test Strategy Assignment), before Step 5 (Over-Decomposition Guard).

TodoWrite item:
```
{content: "Attach test_refs, test_files, or exemption_reason for every task [GATE]", status: "pending", activeForm: "Completing verification mapping"}
```

**Rules:**
- If `verification_mode` starts with `automated-`: require non-empty `test_refs` and non-empty `verify_commands`.
- If `verification_mode` is `automated-*` or `test-producer`: require non-empty `test_files`.
- If `verification_mode` is `artifact-sync`, `static-check`, or `manual-ux`: require non-empty `exemption_reason`.

#### Gate V3: Coverage Report

**Position:** After Step 7 (Present Final Plan), before Step 8 (Persist Execution Plan). User must see coverage before approving the plan.

TodoWrite item:
```
{content: "Review verification coverage report before pipeline_load [GATE]", status: "pending", activeForm: "Reviewing verification coverage"}
```

**Rule:** Emit a machine-readable coverage summary:

```
Verification Coverage Report
───────────────────────────────────────
Total tasks:           38
Automated (unit):       8
Automated (integration): 5
Automated (contract):   4
Automated (component):  3
Static-check:           2
Artifact-sync:          6
Test-producer:          3
Manual-ux:              4
Exempt (with reason):  15
Unmapped:               3  ← BLOCKING

Unmapped tasks:
  T12: "Update config loader" — has acceptance criteria mentioning tests
  T15: "Add retry logic" — behavior-changing, no verification
  T22: "Frontend polish" — needs at least manual-ux classification

Refuse pipeline_load if unmapped > 0 for behavior-changing tasks.
```

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
  T30 test-producer   "Writes the integration test suite for Gate 1"

Acknowledge exemptions? [Y/n/modify]
```

If the user modifies an exemption (e.g., upgrades `manual-ux` to `automated-component`), loop back to Gate V2 for that task only.

## Special Handling by Task Type

### Docs or manifest maintenance

Examples: roadmap sync, manifest update, README changes.

These should NOT be forced into fake pytest mappings. They carry:
- `verification_mode: "artifact-sync"` or `"static-check"`
- `exemption_reason` explaining why no behavioral tests apply
- `verify_commands` if a parser or validator exists (e.g., `python3 -c "import json; json.load(open('manifest.json'))"`)

### Test-writing cards

Examples: "Write Gate 1 integration tests", "Add regression suite for scoring."

These should NOT be treated as unmapped — they ARE the tests. They carry:
- `verification_mode: "test-producer"`
- `test_files` for the new or expanded suite
- `verify_commands` that prove the produced suite runs (e.g., `uv run pytest tests/test_gate1.py -q`)

### Hybrid frontend cards

Examples: heatmap rendering, interactive explorer, chart components.

These should usually split verification:
- `automated-component` for data shape, render contract, and edge-case state
- A separate `manual-ux` card (or verification note) only for subjective visual polish

If a frontend card genuinely cannot be automated at all, it gets `manual-ux` with an `exemption_reason` that explains why.

## Contract with fizzy-pipeline-mcp

This spec produces the fields; fizzy-pipeline-mcp consumes them. The mapping:

| adversarial-spec field | fizzy-pipeline-mcp metadata field |
|------------------------|----------------------------------|
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
  {content: "Classify verification_mode for every task [GATE]", status: "pending"},
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

## Acceptance Criteria

1. Phase 07 cannot emit a behavior-changing task with an empty verification block.
2. Phase 07 cannot call `pipeline_load` while unmapped behavior-changing tasks exist.
3. Exemptions are explicit, typed, and surfaced for user review before plan approval.
4. Generated `fizzy-plan.json` contains all 6 verification fields per task, providing sufficient structure for `fizzy-pipeline-mcp` to enforce `Passed Test` transitions without depending on free-form comments.
5. The updated TodoWrite includes all 4 verification gates in the correct positions.
6. Backward compatibility: existing `fizzy-plan.json` files without the new fields still load (the pipeline handles missing fields as warnings during migration window).