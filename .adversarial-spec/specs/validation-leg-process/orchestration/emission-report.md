# Emission Report: validation-leg-process

## Produced

- `.adversarial-spec/specs/validation-leg-process/verification-coverage.json`
- `.adversarial-spec/specs/validation-leg-process/fizzy-plan.json`
- Per-node mini-spec and verification artifacts under `.adversarial-spec/specs/validation-leg-process/<task_id>/`
- `.adversarial-spec/specs/validation-leg-process/orchestration/emit_driver.py`

## Coverage JSON

```json
{
  "report_schema_version": 1,
  "total_tasks": 25,
  "behavior_changing_count": 20,
  "non_behavior_changing_count": 5,
  "counts_by_mode": {
    "automated-integration": 6,
    "automated-unit": 16,
    "artifact-sync": 1,
    "static-check": 1,
    "manual-ux": 1
  },
  "exempt_tasks": [
    {
      "task_id": "C-5.1",
      "mode": "artifact-sync",
      "reason": "Phase-7 doc section (process narrative, no runtime behavior); cold-read usability verified at dogfood TC-0.1 (fresh agent reaches check-rows-clean draft <30 min), not a CI unit test."
    },
    {
      "task_id": "C-5.2",
      "mode": "static-check",
      "reason": "Phase-8 close-algorithm doc; verified by TC-0.2 static grep asserting all 8 gate reject codes appear with documented responses — no runtime behavior of its own."
    },
    {
      "task_id": "C-5.3",
      "mode": "manual-ux",
      "reason": "Dogfood close: requires the real fizzy gate accepting on first call AND Jason's intent-level acceptance of the process experience (mobile-sufficient digest, unambiguous reply/re-prompt). Human-gated; cannot assert programmatically (NG3, ACK-4 bootstrap circularity acknowledged)."
    }
  ],
  "unmapped_behavior_tasks": [],
  "unmapped_non_behavior_tasks": [],
  "validation_errors": []
}
```

## self_check_plan raw output

```json
{
  "valid": true,
  "issues": []
}
```

## Requirement lint

```json
{
  "checked": 50,
  "failures": [],
  "all_ok": true
}
```

## Judgment Calls

- Coverage derivation matched orchestrator expected mode counts.
- Behavior derivation matched expected 20 behavior-changing nodes.
- Subsystem and system nodes without explicit verify_commands use the plan-declared full-suite scope.
- Final plan task ids are normalized to fizzy dash-form ids; artifact paths retain execution-plan dotted ids.
- Top-level verify_commands mirror the per-node execution-plan commands for automated nodes.
- Exempt doc/dogfood nodes keep their exemption_reason and use inspection/demonstration evidence in verification artifacts.
- Requirement IDs for dotted component ids use C-R<major><minor> so they satisfy ^[A-Z]+-R?\d+$ and stay unique.

## OPEN QUESTIONS

- None.
