# Human-Gate Cross-Project Leak (FPM-G1+G2 Misapplication)

- **Date:** 2026-04-29 (G1), updated 2026-04-30 (G2 hit by same root cause)
- **Trigger:** Card `1851` (session `adv-spec-202604291604-dispatch-cost-tracker-unify`)
  was stuck in `Pre-Roadmap` with `g1_rejected_count: 4` after every
  `pipeline_advance` call.
- **Affected board:** adversarial-spec (Fizzy `03fw5alxw15iqwh6hq15vfdsb`)
- **Affected MCP package:** `fizzy-pipeline-mcp` (shared dependency)

## What broke

The G1 human gate at `Pre-Roadmap → Debate` was specced for fizzy-pipeline-mcp's
own development workflow (see
`.adversarial-spec-checkpoints/adv-spec-202604041811-human-gated-pipeline-transitions-round-2.md`).
Implementation landed 2026-04-05 in fizzy-pipeline-mcp commits `[HGP-T7]`
through `[HGP-T10]`.

Two configuration choices coupled the gate to every consumer of the package:

1. `fizzy_pipeline_mcp.config:137` hardcodes `ENABLE_HUMAN_GATES = True`
   ("# ENABLE_HUMAN_GATES hard coded on for now").
2. `fizzy_pipeline_mcp.pipeline:100` defines the G1 gate tuple
   `("Pre-Roadmap", "Debate", None, None, "g1_approved")` at module level,
   so it applies to every board / project that uses the MCP, not only
   fizzy-pipeline-mcp's own board.

adversarial-spec uses the same MCP package and therefore inherits the gate.
But adversarial-spec has no relay daemon to set `g1_approved=True`:

- `adversarial-spec-listener.service` is a Claude wake listener, not a Fizzy
  relay. It only forwards Telegram updates to the active Claude session.
- `fizzy-pipeline-mcp-listener.service` is currently a stub shell script that
  appends Telegram updates to `~/.local/state/fizzy-pipeline-mcp-listener/updates.jsonl`
  and never invokes `relay._handle_update()`. The stub's own header notes:
  "This is intentionally dumb. The 'real' relay daemon from spec-draft-v3
  (M-3) will replace this... That is downstream work."

Result: any session card on a non-fizzy-pipeline-mcp board hits a closed
G1 gate that no operator command can open. `pipeline_advance` increments
`g{n}_rejected_count` on every attempt and notifies an operator that does
not exist.

## Short-term workaround (this incident)

`pipeline_patch_state` is invoked once on card `1851` to set
`g1_approved: True`, with this file as the `process_failure_path`.
After the patch, Codex's next `pipeline_advance` call moves the card from
`Pre-Roadmap` to `Debate` normally.

Patch payload:

```json
{"g1_approved": true}
```

Patch is one-shot and limited to card `1851`. No other board / card / session
is touched by this workaround.

## Permanent fix (separate session)

The fizzy-pipeline-mcp package needs to make human-gate enforcement scoped
rather than global. Two minimum changes:

1. Replace the hardcoded `ENABLE_HUMAN_GATES = True` with environment-driven
   config (already partially scaffolded in `config.py` — the env-var path
   exists; just remove the hardcode override). Default off; opt-in per
   project via env or per-board metadata.
2. Either gate the global G1/G2/G3 tuples behind the same flag, or move
   the gate definition to a per-board config the MCP reads at startup.

Owner: a fresh adversarial-spec session against the fizzy-pipeline-mcp
project. NOT bundled into this session
(`adv-spec-202604291604-dispatch-cost-tracker-unify`), whose declared scope
is CON-002 only (cost_tracker → token_tracking refactor inside the
adversarial-spec project).

## Recurrence: G2 (2026-04-30)

After 3 debate rounds converged on `spec-draft-v3.md`, Codex's
`pipeline_advance` to move card 1851 from `Debate → Pre-Gauntlet`
hit the same cross-project leak — `g2_rejected_count: 3` accumulated.
Same root cause (hardcoded `ENABLE_HUMAN_GATES=1`, no relay daemon
for adversarial-spec board). Same workaround applied: one-shot
`pipeline_patch_state {"g2_approved": true}` against card 1851
referencing this same incident note. Patch is limited to card
1851; no other card / board touched. Permanent fix remains owned
by the future fizzy-pipeline-mcp session described below.

## Audit trail

- Diagnostic chain captured in
  `.adversarial-spec/sessions/adv-spec-202604291604-dispatch-cost-tracker-unify.journey.log`.
- Telegram thread on `@adversarialspecbot` chat id 866010103 records the
  user-side debugging.
- This file is the canonical incident record for the
  `pipeline_patch_state` invocation.
