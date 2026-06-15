# System-validation close targeted the session card, not the system node (2026-06-14)

## Failure
The Phase 8 validation-leg **close algorithm** (`08-implementation.md`) instructed the
conductor to call `pipeline_mark_system_validation_complete` with
`card_id = SESSION_CARD_ID` (the session card, `fizzy_card_id` from the session detail
file). Fizzy's gate rejects that with `SESSION_MISMATCH`:

```
def _task_belongs_to_session(card, session_id):  # pipeline.py:1896
    return metadata.get("card_type") == "task" and metadata.get("parent_session_id") == session_id
```

The session card has `card_type == "session"`, so the precondition can **never** pass
for it. The flag `system_validation_complete` lives on the **system-altitude task
node** (`task_id "SYS"`), and the Finalization→Completed coverage gate reads it from
that node too.

## How it surfaced
The dogfood close-out (C-5-3 / US-10) ran the close for the first time against a live
board. On session card 5604 the gate returned `SESSION_MISMATCH`. Reading the fizzy
source proved the cause; retargeting to the SYS task node (card 5616) closed clean
(`system_validation_complete: true`, 14/14 rows, conops_ref_count 14).

## Why it went undetected
The close path had never been executed end-to-end before this dogfood. The contract was
extracted correctly into `fizzy-validation-contract.md` (precondition #1 =
`_task_belongs_to_session`), but the close algorithm prose and the code block both named
`SESSION_CARD_ID`, and the `SESSION_MISMATCH` playbook entry asserted the code was
"unreachable post-preflight" — reinforcing the wrong assumption. C-5-2 passed review and
"Passed Test" on doc inspection alone; no live close exercised the contradiction.

## Impact on validation rows
- **r-US0-1** ("run end-to-end from documented steps alone") and **r-US8-1** ("close is
  mechanical; every gate error code mapped") were *false as written* at judgment time —
  a conductor following the docs verbatim would have hit `SESSION_MISMATCH` with no
  correct recovery. Jason ruled **fix-forward (Option A)**: complete the close on the
  correct node and correct the docs; pass verdicts stand because the capability is sound
  and the defect was doc-only.

## Fix (this commit)
- `08-implementation.md`: close-call block now uses `SYSTEM_NODE_CARD_ID` with a hard
  contract note (`card_type == "task"`, `altitude == "system"`, `task_id "SYS"`,
  `parent_session_id` match); preflight step 1 resolves the system node from the board,
  not the session detail file; `SESSION_MISMATCH` playbook entry rewritten to name the
  session-card mistake and the retarget fix.
- `validation-approval-explainer.html`: close-mechanics step 4 corrected + dogfood-finding note.

## Follow-up (not blocking)
- Consider a preflight assertion in the close tooling/doc that refuses a `card_type !=
  "task"` target locally before the MCP call (fail-fast mirror of the gate).
- The SYS node (5616) still shows `system_verification_complete: false` and the
  subsystem/component verification flags false — separate VERIFICATION obligations,
  out of scope for this validation close, but relevant before the session advances to
  Completed.
