# Adversarial-spec process failure guard index

This is an operational index, not an incident archive. Diagnose new failures by
their mechanism and exact signature; keep run-specific evidence with the owning
Session artifacts.

| Failure mechanism | Observable signature | Current guard |
|---|---|---|
| Intent was never locked before critique | Detailed design exists, but the approved boundary, Slice North Star, or user-visible outcome is missing. | Phase 1 locks `requirements_summary` and the Slice North Star. Phase 2 requires user-confirmed milestones, test intent, and exactly one North Star milestone before Debate. |
| A prose artifact does not satisfy its consumer contract | A downstream validator extracts no actionable records or rejects required fields although the document looks complete. | Use the canonical artifact shape, validate required fields and provenance, run `pipeline_validate_plan`, and block `pipeline_load` until the plan is valid. The [spec-record contract](contracts/spec-record-contract.md) owns machine-facing grammar. |
| A Phase advanced without its durable output | Local state or a Card names a later Phase while the required artifact is absent, empty, stale, or unrecorded. | The Phase router and entry gates verify prior outputs. Phase 4 skip mode still writes its stub. See [`SKILL.md`](skills/adversarial-spec/SKILL.md) § `Phase Transition Protocol`; never patch state across the missing fence. |
| Independent agreement amplified an unverified premise | Multiple reviewers converge on an endpoint, schema, invariant, or runtime claim that no inspected source supports. | Carry source-backed context into Debate and the gauntlet, preserve claim ceilings, and verify consequential external contracts against official documentation or live evidence before incorporation. |
| Local Session state and the pipeline diverged | Pointer, detail, and live Session Card disagree about Phase, step, or artifact path. | First Gate recovery selects one unambiguous receipt, preserves valid active work, and updates detail before pointer before Card. Notifications and comments are never treated as state. |
| Task-level success hid whole-change failure | Every Task Card passed, but a goal, non-goal, user journey, spec Concern, architecture constraint, or regression remains unresolved. | Phase 8 verification re-reads the full artifact chain, writes a verification report, and supplies final commands and summary to the sweep gate. |

## Investigation order

1. Read [`.architecture/INDEX.md`](.architecture/INDEX.md) and
   [`.architecture/primer.md`](.architecture/primer.md).
2. Read the active Phase file under
   [`skills/adversarial-spec/phases/`](skills/adversarial-spec/phases/).
3. Capture the complete tool error, artifact path, Session id, Card id, and
   `board_id` without exposing secrets.
4. Compare the producer's output with the consuming schema or tool signature.
5. Save a failing regression test for a code defect; preserve malformed input as
   evidence when safe.
6. Apply the smallest fix at the earliest proven boundary and re-run that same
   boundary.

See [`onboarding/core-practices.md`](onboarding/core-practices.md) for evidence
ceilings and fail-fast rules. Historical narratives remain available in Git
history when an audit requires them.
