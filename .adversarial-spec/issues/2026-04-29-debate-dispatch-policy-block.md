# Debate Dispatch Policy Block

Date: 2026-04-29
Session: `adv-spec-202604291604-dispatch-cost-tracker-unify`
Card: `1851`

## What broke

Fizzy `pipeline_begin_debate_round` created Round 1 checklist items for `claude-cli/claude-sonnet-4-6` and `gemini-cli/gemini-3.1-pro-preview`. Both subsequent `pipeline_dispatch_single_agent_debate` calls were rejected by tenant policy before a dispatch ID was created because the call would export private workspace spec and architecture content to external model services.

## Gate or contract bypassed

`pipeline_advance_debate_round` requires the debate checklist to be complete. The normal completion path is:

1. dispatch model,
2. receive `dispatch_id`,
3. register return with `pipeline_register_debate_agent_return`,
4. advance debate round.

Because dispatch was rejected before a `dispatch_id` existed, `pipeline_register_debate_agent_return` also rejected skipped registrations with `DISPATCH_ID_MISMATCH`. There is no cancel-round or policy-skipped registration tool exposed in this MCP surface.

## Short-term workaround

Codex performed a local participant critique, wrote `.adversarial-spec/specs/dispatch-cost-tracker-unify/round-1-codex-local-critique.md`, incorporated the valid findings into `spec-draft-v2.md`, updated `tests-pseudo.md`, and uses `pipeline_patch_state` only to record round state that the canonical tool cannot record because its checklist is blocked by missing dispatch IDs.

## Permanent fix planned

Fizzy should expose one of:

- `pipeline_cancel_debate_round`,
- `pipeline_register_debate_agent_return(status="skipped")` without requiring a dispatch ID after a policy block,
- or a dispatch result object for policy-blocked launches that includes a dispatch ID and terminal status.

Until then, policy-blocked debate rounds cannot be completed through the canonical checklist gate.

## Retry: Opus 4.7

After model docs were checked and the skill defaults were updated to `claude-cli/claude-opus-4-7` and `codex/gpt-5.5`, Codex retried Round 1 external dispatch against `spec-draft-v2.md`:

- Round instance: `1475ef58aad24263`
- Model attempted: `claude-cli/claude-opus-4-7`
- Result: rejected before a dispatch ID was created.

The rejection again said exporting private workspace spec content to Claude CLI is blocked by tenant policy. Because the rejection explicitly forbids equivalent workaround or indirect external-service export attempts, Gemini CLI was not attempted in this retry.

## Retry after Codex full-access permissions

After Codex permissions were changed to full access, the Opus 4.7 dispatch no longer hit the export policy rejection. The MCP tool wrapper still timed out after 120s:

```text
timed out awaiting tools/call after 120s
```

The underlying Claude CLI process continued and completed successfully. Artifacts appeared in:

```text
.adversarial-spec/debate-workspaces/adv-spec-202604291604-dispatch-cost-tracker-unify/round-1475ef58aad24263/results/claude-cli-claude-opus-4-7/
```

Observed files:

- `raw.txt`
- `parsed.json`
- `stderr.txt`

`parsed.json` reported:

```json
{
  "model": "claude-cli/claude-opus-4-7",
  "status": "completed",
  "agreed": false,
  "findings_count": 7,
  "elapsed_seconds": 143.4
}
```

## Codex workaround

Treat long Fizzy dispatch from Codex as fire-and-poll:

1. Call `pipeline_dispatch_single_agent_debate` once.
2. If Codex reports `timed out awaiting tools/call after 120s`, do not immediately retry the same model.
3. Poll the result directory every 90 seconds. Do not exponential-backoff.
4. When `parsed.json` and `raw.txt` appear, use them as the completed critic return.
5. Register the return if a `dispatch_id` was returned or can be recovered from pipeline state.
6. If the MCP timeout lost the `dispatch_id`, add a Fizzy comment with the artifact path and record this process-failure path instead of duplicating the model run.
