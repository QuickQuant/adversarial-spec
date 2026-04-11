## Verification (Phase 9)

> **FIRST ACTION upon entering this phase:** Create this TodoWrite immediately.
> Do NOT read further until the TodoWrite is active.

```
TaskCreate([
  {subject: "Collect verification inputs (spec, test spec, execution plan, gauntlet concerns, architecture docs, pipeline state)", status: "pending", activeForm: "Collecting verification inputs"},
  {subject: "Run goal coverage check", status: "pending", activeForm: "Checking goal coverage"},
  {subject: "Run non-goal audit", status: "pending", activeForm: "Auditing non-goals"},
  {subject: "Run user story validation", status: "pending", activeForm: "Validating user stories"},
  {subject: "Run concern mitigation audit", status: "pending", activeForm: "Auditing concern mitigations"},
  {subject: "Run structural conformance check", status: "pending", activeForm: "Checking structural conformance"},
  {subject: "Run regression test sweep", status: "pending", activeForm: "Running regression tests"},
  {subject: "Write verification report", status: "pending", activeForm: "Writing verification report"},
  {subject: "Execute pipeline sweep or sweep_fail", status: "pending", activeForm: "Sweeping pipeline"},
])
```

**[GATE] Task 1 (collect inputs) must be marked `completed` before running any checks (tasks 2-7). Architecture docs are required inputs — not optional.**

After all implementation cards reach Passed Test, the verification phase runs a
final alignment check before sweeping cards to Completed-Unmapped. This replaces
the old `pipeline_sweep` as a trivial batch move with a substantive spec
conformance gate.

> **Trigger:** All task-pipeline cards for the session are in Passed Test (no cards
> remain in New Todo, Review, Untested, or Failed Review).

---

### Purpose

Implementation can drift from the spec — tasks pass individually but the whole
doesn't add up. Verification catches:

- **Goal gaps:** A goal from §2 that no task actually delivered
- **Non-goal leakage:** A non-goal from §3 that was accidentally implemented
- **User story failures:** A user story whose test case passes in isolation but
  doesn't work end-to-end
- **Concern regressions:** A gauntlet concern that was accepted but whose
  mitigation is missing or incomplete
- **Structural drift:** Files created that aren't in the execution plan, or
  planned files that were never created

---

### Inputs

Collect these before running verification:

1. **Spec** — `spec-output.md`: Goals (§2), Non-Goals (§3), User Stories, Milestones (§18)
2. **Test spec** — `tests-spec.md`: All test cases by milestone
3. **Execution plan** — `execution-plan.md`: Task list, file structure (Architecture Spine),
   concern coverage matrix
4. **Gauntlet concerns** — `gauntlet-concerns-*.json`: Accepted concerns and their mitigations
5. **Architecture docs** — `.architecture/INDEX.md`, component docs for modules touched
6. **Pipeline state** — All Passed Test cards with their state blocks and test summaries

---

### Verification Checklist

Run each check and record pass/fail with evidence.

#### 1. Goal Coverage

For each goal in §2:
- Which tasks delivered it?
- Is there test evidence (test case + result) proving it works?
- **Pass:** Every goal has ≥1 task with passing tests that address it
- **Fail:** Goal has no corresponding task, or task tests don't cover it

#### 2. Non-Goal Audit

For each non-goal in §3:
- Was any code written that implements it (even partially)?
- **Pass:** No non-goal functionality was implemented
- **Fail:** Non-goal functionality exists — flag for removal or scope change

#### 3. User Story Validation

For each user story referenced in Milestones (§18):
- Find the test cases from `tests-spec.md`
- Verify the test cases passed (from card test summaries)
- Run a representative end-to-end check if possible
- **Pass:** All user stories have passing test cases
- **Fail:** Missing or failing test coverage for a user story

#### 4. Concern Mitigation Audit

For each accepted gauntlet concern:
- The execution plan's concern coverage matrix maps concerns → tasks
- Verify those tasks are in Passed Test
- Spot-check: does the implementation actually address the concern?
- **Pass:** All accepted concerns have corresponding tasks in Passed Test
- **Fail:** Concern has no task, or task doesn't address the concern

#### 5. Structural Conformance

Compare the execution plan's Architecture Spine (file list) against actual files:
- Any files created that aren't in the plan?
- Any planned files that don't exist?
- **Pass:** 1:1 match (or documented deviations approved during implementation)
- **Fail:** Unexplained structural drift

#### 6. Regression Test Sweep

Run the full test suite one final time (not per-card, the whole suite):
- All tests pass?
- No test was disabled or skipped during implementation?
- **Pass:** Full suite green
- **Fail:** Any failure — card goes back to Failed Review via `pipeline_sweep_fail`

---

### Output: Verification Report

Write a verification report to `.adversarial-spec/specs/<slug>/[your llm model]-[session name]-verification-report.md`:

```markdown
# Verification Report: <Session Title>

> Session: <session_id>
> Date: <YYYY-MM-DD>
> Agent: <verifying agent>

## Summary
- Goals: X/Y covered
- Non-Goals: X/Y clean (no leakage)
- User Stories: X/Y passing
- Concerns: X/Y mitigated
- Structural: pass/fail
- Regression: pass/fail

## Goal Coverage
| Goal | Tasks | Evidence | Status |
|------|-------|----------|--------|
| ... | ... | ... | PASS/FAIL |

## Non-Goal Audit
| Non-Goal | Found? | Details | Status |
|----------|--------|---------|--------|
| ... | ... | ... | PASS/FAIL |

## User Story Validation
| Story | Test Cases | Results | Status |
|-------|-----------|---------|--------|
| ... | ... | ... | PASS/FAIL |

## Concern Mitigation
| Concern | Tasks | Evidence | Status |
|---------|-------|----------|--------|
| ... | ... | ... | PASS/FAIL |

## Structural Conformance
<diff or confirmation>

## Regression Suite
<test output summary>

## Verdict
PASS — all checks green, ready to sweep to Completed-Unmapped
FAIL — N issues found, cards returned to Failed Review: [list]
```

---

### Pipeline Integration

After the verification report is written:

- **All checks pass:** Call `pipeline_sweep(session_id, agent, summary, board_id)`
  to move all Passed Test cards to Completed-Unmapped. Summary should reference
  the verification report path.
- **Any check fails:** Call `pipeline_sweep_fail(session_id, agent, summary,
  failed_card_ids, board_id)` for the specific cards that failed verification.
  Those cards return to Failed Review with the verification report as evidence.
- **Update session state:** Record verification phase completion in the session
  detail file with the report path.

---

### Adversarial-Spec Session Flow (Updated)

```
Phase 1: Init & Requirements
Phase 2: Roadmap
Phase 3: Debate
Phase 4: Target Architecture
Phase 5: Gauntlet
Phase 6: Finalize
Phase 7: Execution Planning
Phase 8: Implementation (self-pickup loop)
Phase 9: Verification (this phase)  ← NEW
```

After Phase 9 completes with a PASS verdict, the session can be closed.
