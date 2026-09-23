## Phase 8 Verification Subflow

Verification is the final subflow of implementation. Lifecycle state remains:

```json
{
  "current_phase": "implementation",
  "current_step": "verification"
}
```

Never write verification as a phase value.

```text
TodoWrite([
  {content: "Check sweep readiness without mutating cards [GATE]", status: "in_progress", activeForm: "Checking sweep readiness"},
  {content: "Collect the approved artifact chain and implementation evidence", status: "pending", activeForm: "Collecting verification evidence"},
  {content: "Replay goals, non-goals, stories, Concerns, and structure against the delivered change", status: "pending", activeForm: "Checking whole-change coverage"},
  {content: "Run final regression commands and reconcile every skip/quarantine [GATE]", status: "pending", activeForm: "Running final regression checks"},
  {content: "Write the verification report", status: "pending", activeForm: "Writing the verification report"},
  {content: "Call pipeline_sweep or pipeline_sweep_fail [GATE]", status: "pending", activeForm: "Recording the verification outcome"},
  {content: "Persist verification-subflow completion", status: "pending", activeForm: "Persisting verification completion"},
])
```

### 1. Check readiness first

The first board call in this subflow is read-only:

```text
pipeline_check_sweep_readiness(
  session_id=SESSION_ID,
  board_id=BOARD_ID,
)
```

If readiness reports a missing parent Session Card, a non-terminal lane,
incomplete card evidence, or another blocker, stop and resolve that exact issue.
Do not force a sweep and do not use `pipeline_patch_state` to skip the fence.

Sweep is the final verification gate: it validates uniform lane state,
per-card evidence/attestations, final command/summary fields, records a final
snapshot on the Session Card, and only then moves Passed Test cards.

### 2. Collect evidence

Read the active paths rather than searching for similarly named artifacts:

- finalized spec: goals, non-goals, stories, Slice North Star;
- `tests-spec.md` and its maturity/data-strategy records;
- approved `execution-plan.md`, `fizzy-plan.json`, Architecture Spine, and
  dependency report;
- accepted gauntlet Concern artifact and recorded dispositions;
- target architecture plus only the architecture docs for touched components;
- implementation diffs, Passed Test card metadata, acceptance/test
  attestations, test receipts, operator evidence, and final produced artifacts.

The pre-implementation documents state intent. The diffs, cards, receipts, and
artifacts prove what was delivered.

### 3. Replay whole-change coverage

Record pass/fail and concrete evidence for every dimension:

| Dimension | Post-implementation question |
|---|---|
| Goals | Which committed behavior and passing evidence discharge each goal and the Slice North Star? |
| Non-goals | Did any diff or artifact implement excluded behavior or widen scope without approval? |
| User stories | Do the bound tests and a representative end-to-end path prove the story as a workflow, not only isolated units? |
| Concerns | Does each accepted Concern's mapped task actually implement and prove the recorded mitigation? |
| Structure | Do actual files and boundaries match the approved Architecture Spine or an approved amendment? |
| Dependencies | Did the delivered order/evidence satisfy the hash-bound semantic report and live-spine obligations? |

A green card is necessary, not sufficient, when the combined system fails a goal
or accepted architecture constraint.

### 4. Final regression and skip reconciliation

Run the complete final verification command set against the committed result.
Capture the exact commands, working directories, collected counts, outcome, and
artifact/receipt paths. Zero collected tests is not a pass.

No **unapproved or undischarged** skip may remain. Reconcile all of these against
the approved plan and record their final disposition:

- test-ahead quarantines and todo/skip markers;
- spike strategies and exempt verification modes;
- unavailable environment or human-attestation deferrals;
- intentionally superseded or not-applicable tests.

A quarantine that should have become green, or an exemption lacking its required
approval/evidence, fails verification. Do not impose the false rule that a suite
can never contain an approved skip.

### 5. Write the durable report

Atomically write:

```text
.adversarial-spec/specs/<slug>/verification-report.md
```

Use this compact shape:

```markdown
# Verification Report: <Session title>

> Session: <session_id>
> Agent: <verifier>
> Commit/range: <verified bytes>

## Summary
- Goals: <covered/total>
- Non-goals: <clean/total>
- Stories: <passing/total>
- Concerns: <mitigated/total>
- Structure/dependencies: <pass/fail>
- Regression: <pass/fail>

## Coverage
| Dimension / ID | Delivered evidence | Status |
|---|---|---|
| ... | commit, card, command, receipt, or artifact | PASS/FAIL |

## Structural and Dependency Conformance
<actual-vs-approved diff, including approved deviations>

## Regression and Skip Reconciliation
<commands, counts, results, and every remaining skip disposition>

## Findings
<actionable failures mapped to specific card IDs, or "none">

## Verdict
PASS — ready for the final sweep
or
FAIL — failed cards: <ids and reasons>
```

Set `verification_report_path` in the active detail and pointer without changing
`current_phase`.

### 6. Record the outcome through the pipeline

On PASS, call the exact sweep contract:

```text
pipeline_sweep(
  session_id=SESSION_ID,
  agent=AGENT,
  summary="Verification PASS; report: <verification_report_path>",
  final_verification_commands=["<exact command>", "..."],
  final_verification_summary="<bounded result summary with counts and report path>",
  board_id=BOARD_ID,
)
```

Do not pass an empty or paraphrased command list. If sweep rejects after a PASS
report, treat its structured gate result as new evidence, correct the report or
underlying state, and rerun readiness before retrying.

On any verification failure, identify the Passed Test cards that own the failed
behavior and call:

```text
pipeline_sweep_fail(
  session_id=SESSION_ID,
  agent=AGENT,
  summary="Verification FAIL; report: <verification_report_path>; <reason>",
  failed_card_ids=["<card_id>", "..."],
  board_id=BOARD_ID,
)
```

This records the failed verification and returns only those cards to Failed
Review. Do not sweep unaffected cards and do not claim completion.

After a successful sweep, atomically set `current_step` to
`verification complete`, keep `current_phase: implementation`, and record the
report and sweep result. Continue through `SKILL.md` § Phase Transition Protocol;
use § Decisions Log and § Journey Log for their owned records.
