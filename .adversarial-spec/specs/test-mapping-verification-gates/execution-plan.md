# Execution Plan: Test Mapping & Verification Gates

Generated: 2026-04-11
Spec: `.adversarial-spec/specs/test-mapping-verification-gates/spec-output.md`
Session: `adv-spec-202604111912-test-mapping-verification-gates`
Fizzy card: 572 (board `03fw5alxw15iqwh6hq15vfdsb`)
Task cards: 891 (TMV1), 892 (TMV2), 893 (TMV3), 895 (TMV4), 896 (TMV5), 897 (TMV6)

> **Note on task IDs:** This document refers to tasks as T1-T6 for readability. The Fizzy `task_id` values are `TMV1`-`TMV6` (session-prefixed) to avoid a board-wide dedup collision with the prior `phase4-architecture-rewrite` session that also used T1-T6. T1↔TMV1, T2↔TMV2, ..., T6↔TMV6.

## Summary

- **Tasks:** 6 (S: 3, M: 3, L: 0)
- **Workstreams:** 1 (single-agent, sequential)
- **Gauntlet concerns addressed:** 125 accepted → resolved via 10 surgical fixes already in spec
- **Estimated effort:** half-day

## Scope

All deliverables are phase documentation changes. The 4 verification gates (V1-V4) are **LLM-enforced via TodoWrite**, not runtime validators. There is no Python code to write, no tests to run against a binary, no migration scripts. The work is editing `07-execution.md` and mirroring it to the deployed skill path.

## Blast Zone

| Path | Role |
|------|------|
| `skills/adversarial-spec/phases/07-execution.md` | Primary edit target (source of truth) |
| `~/.claude/skills/adversarial-spec/phases/07-execution.md` | Deployed copy (Claude Code reads this) |
| `.adversarial-spec/specs/test-mapping-verification-gates/fizzy-plan.json` | Dogfood deliverable (T6) |
| `.adversarial-spec/specs/test-mapping-verification-gates/verification-coverage.json` | Dogfood deliverable (T6) |

## Architecture Context

- adversarial-spec is a skill (markdown phase docs + Python debate/gauntlet orchestration)
- Phase 07 is pure prose — the LLM reads it to drive task decomposition and pipeline load
- Gates are enforced by TodoWrite discipline, the same mechanism Phase 07 already uses for existing gates
- No invariant set / target architecture exists for this session (spec is a process change, not a system build)

## Tasks

### T1: Schema Reference Section in 07-execution.md

- **Effort:** M
- **Strategy:** test-after
- **Spec refs:** Schema Changes (lines 33-149)
- **Dependencies:** None
- **Verification:**
  - `behavior_change`: false (documentation-only)
  - `verification_mode`: artifact-sync
  - `verification_scope`: static
  - `exemption_reason`: "Phase doc prose — no runtime validation"
  - `test_refs`: []
  - `test_files`: []
  - `verify_commands`: []

**Description:** Insert a new "Verification Schema (v2)" subsection in `07-execution.md` before Step 3 (Task Decomposition). Content must include:
- `plan_schema_version: 2` root marker and its meaning
- Task-level field table (`behavior_change`, `verification_mode`, `test_refs`, `test_files`, `verify_commands`, `verification_scope`, `verification_notes`, `exemption_reason`)
- `verification_mode` enum table (8 modes)
- `verification_scope` enum table (4 scopes)
- Mode-to-scope compatibility matrix (8x4)
- Path and command validation rules (repo-relative, no `..`, no template interpolation, no whitespace-only strings)
- Typed validation error codes (10 codes)
- Behavior-change classification criteria (what makes a task `behavior_change: true` vs `false`)

**Acceptance:**
- [ ] All 8 verification modes documented with required fields
- [ ] Mode-to-scope matrix present
- [ ] All 10 typed error codes listed
- [ ] Path validation rules stated
- [ ] Behavior-change criteria included
- [ ] Section length reasonable (target ~80-120 lines)

---

### T2: Insert Gates V1-V4 in 07-execution.md

- **Effort:** M
- **Strategy:** test-after
- **Spec refs:** Process Changes to Phase 07 (lines 150-309)
- **Dependencies:** T1 (gates reference schema fields from T1)
- **Verification:**
  - `behavior_change`: false (documentation-only)
  - `verification_mode`: artifact-sync
  - `verification_scope`: static
  - `exemption_reason`: "Phase doc prose — LLM-enforced gates are markdown"
  - `test_refs`: []
  - `test_files`: []
  - `verify_commands`: []

**Description:** Insert Gates V1-V4 at the correct positions in `07-execution.md`:
- **Gate V1 (Verification Classification)**: after Step 3 (Task Decomposition), before Step 4 (Test Strategy Assignment)
- **Gate V2 (Mapping Completeness)**: after Step 4, before Step 5 (Over-Decomposition Guard)
- **Gate V3 (Coverage Report)**: after Step 7 (Present Final Plan), before Step 8 (Persist Execution Plan)
- **Gate V4 (Exception Review)**: after V3, before Step 8

Each gate must include: TodoWrite item syntax, position note, rule text, blocking behavior, and (for V3) both the human-readable and machine-readable coverage report templates.

**Acceptance:**
- [ ] All 4 gates inserted at correct positions
- [ ] V1 rule: every task has `behavior_change` + `verification_mode` + `verification_scope`
- [ ] V2 rules: conditional-required field checks, mode-to-scope matrix, path validation
- [ ] V3 emits human-readable summary AND `report_schema_version: 1` JSON to `.adversarial-spec/specs/<slug>/verification-coverage.json`
- [ ] V3 blocking rule: refuse `pipeline_load` if `unmapped_behavior_tasks` is non-empty
- [ ] V4 lists exempt tasks (artifact-sync, static-check, manual-ux) and requires user acknowledgement
- [ ] V4 explicitly notes that `test-producer` tasks are NOT exempt
- [ ] Note in each gate clarifying "LLM-enforced process gate, not runtime validator"

---

### T3: Update Phase 07 TodoWrite Template

- **Effort:** S
- **Strategy:** test-after
- **Spec refs:** Updated TodoWrite for Phase 07 (lines 366-389)
- **Dependencies:** T2 (TodoWrite references gate names)
- **Verification:**
  - `behavior_change`: false
  - `verification_mode`: artifact-sync
  - `verification_scope`: static
  - `exemption_reason`: "Phase doc prose — TodoWrite template is markdown"

**Description:** Replace the existing TodoWrite template at the top of `07-execution.md` (lines 5-20) with the 16-item version from spec lines 370-388. New items:
- `Classify behavior_change and verification_mode for every task [GATE]` (after decomposition)
- `Attach test_refs, test_files, or exemption_reason for every task [GATE]` (after strategy assignment)
- `Review verification coverage report before pipeline_load [GATE]` (after plan approval)
- `Review every exemption with the user [GATE]` (after coverage review)

**Acceptance:**
- [ ] TodoWrite has all 4 new `[GATE]` items
- [ ] Items are in correct order relative to existing steps
- [ ] Existing gates (Load architecture, Present plan, Write to disk, Load pipeline, Add comments) preserved
- [ ] Template still parses as valid pseudo-code

---

### T4: Update Step 9 to Emit v2 Schema + Coverage Report

- **Effort:** M
- **Strategy:** test-after
- **Spec refs:** Schema Changes, Acceptance Criteria #4 and #6
- **Dependencies:** T1 (uses schema from T1)
- **Verification:**
  - `behavior_change`: false
  - `verification_mode`: artifact-sync
  - `verification_scope`: static
  - `exemption_reason`: "Phase doc prose — JSON template is in markdown fence"

**Description:** Update Step 9 (Load into Fizzy Pipeline) of `07-execution.md` to:
1. Emit `plan_schema_version: 2` at the root of `fizzy-plan.json`
2. Include the full verification block per task in the example (with `behavior_change`, `verification_mode`, `verification_scope`, `test_files`, `verify_commands`, `exemption_reason`)
3. Reference the T1 schema section for field semantics (don't duplicate)
4. Add explicit guidance: the plan output from Gate V3 and Gate V4 must be satisfied before `pipeline_load` is invoked
5. Add a step-within-step to write `verification-coverage.json` alongside `fizzy-plan.json`

**Acceptance:**
- [ ] Root-level `plan_schema_version: 2` shown in JSON example
- [ ] Per-task verification block in example tasks
- [ ] Coverage report JSON shape documented with `report_schema_version: 1`
- [ ] Coverage report path: `.adversarial-spec/specs/<slug>/verification-coverage.json`
- [ ] Gate V3/V4 prerequisites explicitly referenced before `pipeline_load` call

---

### T5: Deploy Updated 07-execution.md

- **Effort:** S
- **Strategy:** skip
- **Spec refs:** N/A (infrastructure task)
- **Dependencies:** T2, T3, T4
- **Verification:**
  - `behavior_change`: false
  - `verification_mode`: artifact-sync
  - `verification_scope`: static
  - `exemption_reason`: "File copy — no logic change"

**Description:** Copy the updated `skills/adversarial-spec/phases/07-execution.md` to `~/.claude/skills/adversarial-spec/phases/07-execution.md` so that the next `/adversarial-spec` invocation picks up the new gates.

**Acceptance:**
- [ ] File copied via `cp`
- [ ] `diff` between source and deployed copy is empty
- [ ] No other phase docs modified during copy

---

### T6: Dogfood — Generate v2 fizzy-plan.json for This Session

- **Effort:** S
- **Strategy:** test-after
- **Spec refs:** Acceptance Criteria #4, #6, #8; User Journey (lines 22-31)
- **Dependencies:** T5 (runs against deployed doc)
- **Verification:**
  - `behavior_change`: true (produces the first v2 plan JSON artifact)
  - `verification_mode`: test-producer
  - `verification_scope`: targeted
  - `test_refs`: []
  - `test_files`: [".adversarial-spec/specs/test-mapping-verification-gates/fizzy-plan.json", ".adversarial-spec/specs/test-mapping-verification-gates/verification-coverage.json"]
  - `verify_commands`: ["python3 -c \"import json; p = json.load(open('.adversarial-spec/specs/test-mapping-verification-gates/fizzy-plan.json')); assert p['plan_schema_version'] == 2; assert all('verification_mode' in t for t in p['tasks'])\""]

**Description:** Walk this execution plan through all 4 gates manually and produce two files:
1. `.adversarial-spec/specs/test-mapping-verification-gates/fizzy-plan.json` — v2 schema with all 6 tasks from this plan, each with verification block
2. `.adversarial-spec/specs/test-mapping-verification-gates/verification-coverage.json` — `report_schema_version: 1` with counts and exempt task list

Classification per task (already determined in the verification blocks above):
- T1-T5: `behavior_change: false`, `artifact-sync` or `skip` mode
- T6: `behavior_change: true`, `test-producer` mode (this very task writes the JSON artifacts)

**Acceptance:**
- [ ] `fizzy-plan.json` exists with `plan_schema_version: 2`
- [ ] All 6 tasks have `behavior_change`, `verification_mode`, `verification_scope`
- [ ] Automated tasks have `test_refs`, `test_files`, `verify_commands`
- [ ] Exempt tasks have non-empty `exemption_reason`
- [ ] `verification-coverage.json` exists with `report_schema_version: 1`
- [ ] Coverage counts match plan contents
- [ ] Python validation command passes (non-zero → gate fails)
- [ ] No typed validation errors fire for any task

---

## Dependency Graph

```
T1 ─┬─→ T2 ─┐
    ├─→ T3 ─┼─→ T5 ─→ T6
    └─→ T4 ─┘
```

- T2, T3, T4 are independent after T1 completes
- T5 waits for T2, T3, T4
- T6 waits for T5 (must run against deployed version)

## Uncovered Concerns

None. The spec's 4 Open Questions are explicit deferrals, not gaps:
- `behavior_change` heuristics vs LLM classification (deferred by design)
- Coverage report for every attempt vs final only (deferred)
- `manual-ux` reviewer identity (deferred to later phase)
- Fizzy migration window trigger (belongs to fizzy-pipeline-test-enforcement proposal)

## Verification Coverage (Dogfood Preview)

```
Total tasks:              6
Behavior-changing:        1  (T6)
Non-behavior-changing:    5  (T1-T5)

By mode:
  artifact-sync:           5
  test-producer:           1
  UNMAPPED:                0  ← NOT BLOCKING

Exempt tasks:
  T1 artifact-sync  "Phase doc prose — no runtime validation"
  T2 artifact-sync  "Phase doc prose — LLM-enforced gates are markdown"
  T3 artifact-sync  "Phase doc prose — TodoWrite template is markdown"
  T4 artifact-sync  "Phase doc prose — JSON template is in markdown fence"
  T5 artifact-sync  "File copy — no logic change"
```

T6 is `test-producer` with its own `verify_commands`, so it passes Gate V2 without an exemption.
