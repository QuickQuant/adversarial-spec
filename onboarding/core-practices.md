# Adversarial-spec core practices

This file supplements [`AGENTS.md`](../AGENTS.md). It contains only rules unique
to adversarial-spec; global secret, process, filesystem, Git, and debugging
policy remains in `AGENTS.md`.

## State and artifact safety

- Treat intake receipts, Session detail, the pointer, versioned artifacts, and
  Fizzy Card state as contracts. Missing required fields are errors, not values
  to infer or replace with empty defaults.
- Validate schema, provenance, hashes, and required paths before a state-changing
  call. Stop at the first mismatch and preserve the rejected artifact.
- Never repair a rejected pipeline transition by invoking a standalone script or
  editing state into the desired result.
- Never use `pipeline_patch_state` to cross a gate. Its process-failure path is
  recovery evidence, not an alternate workflow.
- Follow [`SKILL.md`](../skills/adversarial-spec/SKILL.md) § `Phase Transition Protocol`
  for atomic detail, pointer, Card, and notification ordering.

## Evidence boundaries

- Model agreement is not evidence that a source contract, external API, test,
  or runtime behavior is correct. Bind consequential claims to inspected source,
  official documentation, or an executed check.
- A gauntlet seat is a read-only reviewer. It may raise a spec Concern; it may
  not manufacture observed runtime or credential evidence.
- A Card comment, dispatch record, or notification proves only that the record
  was emitted. Confirm the live Card and tool result before claiming a move or
  acknowledgement succeeded.
- Keep claims within the evidence ceiling. Mock or fixture evidence cannot prove
  live browser, wire, permission, credential, or money-path behavior.
- Preserve the implementer/reviewer split even for small changes.

## Fail-fast diagnostics

When a Phase, artifact, or pipeline action fails:

1. Capture the exact observed signature and full structured error.
2. Identify the producing artifact and the consumer that rejected it.
3. Compare local Session detail, pointer state, and live Card state without
   mutating any of them.
4. Reproduce a code defect with a saved failing test when behavior is involved.
5. Fix the earliest proven contract violation; do not patch later state to hide
   it.
6. Re-run the rejected boundary, then verify the downstream state directly.

If the mechanism is still unknown, write a diagnostic plan and keep the Phase
blocked. Do not label uncertainty as a transient failure.
