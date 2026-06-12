# Comments Draft Notes

- Parsed 25 required task IDs from `execution-plan.md` and wrote one comment per ID in `comments-draft.json`.
- Concern IDs referenced by the plan but not found as literal IDs in `gauntlet-concerns-2026-06-11.json`: `PARA-ledger-hash`, `US-0`, `US-10`.
- Judgment calls:
  - `PARA-ledger-hash` was treated as the plan's local shorthand for binding `system_validation.json` to the exact `validation-rows.json` state in C-4.4.
  - `US-0` and `US-10` were treated as roadmap user-story refs, not missing gauntlet concerns.
  - Suffix variants such as `SEC-6-reject`, `US-8(filelock-semantics)`, and `US-4-correction` were mapped to their base concern IDs (`SEC-6`, `US-8`, `US-4`).
