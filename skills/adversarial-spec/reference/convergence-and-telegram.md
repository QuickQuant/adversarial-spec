## Convergence Rules

- Stop after 10 rounds and ask the user whether to continue.
- Require every critic and the orchestrator to agree.
- Treat each additional critic as another required perspective, not a vote to average away.
- Apply the criteria for the active `spec`, `debug`, or `architecture` contract.
- Address every valid concern before accepting `[AGREE]`.

Quality controls the stopping point. Use `--press` when agreement in rounds 1–2
does not demonstrate that the complete document was reviewed.

Declare convergence only when the document is ready for its next consumer:

- `spec`: the product or engineering team can proceed without inventing requirements;
- `debug`: evidence establishes the mechanism and supports a proportional fix; or
- `architecture`: implementation tasks have coherent shared patterns and boundaries.

## Direct `debate.py --telegram` integration

This section applies only to `debate.py critique --telegram`. It is separate
from pipeline transition and milestone notifications. See `SKILL.md` § **Phase
Transition Protocol** for that owner. Set `$CARD_ID` and `$MODEL_LIST` before
using the command template.

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --pipeline-card "$CARD_ID" --models "$MODEL_LIST" \
  --doc-type spec --depth technical --telegram < spec.md
```

The direct integration requires its Telegram environment configuration to
already exist. After each round it snapshots the latest update ID, sends the
round summary, then synchronously waits for the first later text message from
the configured chat. `--poll-timeout` defaults to 60 seconds. Received text is
returned as debate feedback; no reply means the debate continues automatically.

The poller correlates only by chat ID and update offset. It does not prove that a
message answers a particular pipeline gate. Never use this direct feedback path
as gate approval.
