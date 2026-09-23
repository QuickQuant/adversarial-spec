# Telegram Bridge — Agent Reference

Telegram is an attention and feedback channel. It is never the durable pipeline
state or evidence that a human gate passed.

## Canonical send route

```bash
~/.claude/bin/telegram-send <project> "<message>"

# Multiline content may be supplied on stdin.
~/.claude/bin/telegram-send <project> -
```

The helper resolves the project's chat ID, token environment name, and optional
emoji through the project registry. It prepends the configured emoji and sends
Markdown, retrying as plain text if entity parsing fails. There is no required
emoji suffix. Do not replace the helper with raw Telegram API calls.

Never print, echo, log, or expose a bot token. Let the helper resolve
credentials; if it reports missing configuration, surface that error without
dumping environment variables or secret files.

For pipeline transition and milestone behavior, see `SKILL.md` § **Phase
Transition Protocol**. Board state and the owning human-gate tool remain
authoritative even after a notification is delivered.

## Reply and approval boundary

The implemented direct poller in `scripts/telegram_bot.py` snapshots an update
ID, then accepts the first later text message from the configured chat. It
filters by chat ID and update offset only. It does not inspect
`reply_to_message_id`, a gate identifier, or a card identifier, and it polls
synchronously. `debate.py --telegram` uses this only for optional debate
feedback; see `reference/convergence-and-telegram.md`.

An uncorrelated same-chat message **never approves a gate**. If the owning gate
cannot correlate the response to the exact pending decision, keep the gate
pending and request confirmation through a correlated pipeline or terminal
path. Do not infer approval from timing or message content alone.

Do not create a raw background polling loop. Use the owning pipeline protocol
for pauses and wakeups; allow the direct debate CLI to own its bounded
synchronous feedback wait.

## When to use

- Human-gated transitions when the owning protocol requests a notification
- Long-running review requests the user asked to receive on mobile
- Explicit Telegram-flow testing
- Requested status updates during long-running work

Include enough context to identify the project, card/gate, decision, evidence,
and required response without relying on earlier terminal conversation.

## When not to use

- Routine terminal conversation
- Unrequested notifications
- Debug output, verbose logs, or secrets
- A substitute for Fizzy state, evidence, or an approval receipt

## Troubleshooting

- **No project configuration:** verify the project registry entry through its
  owner; do not bypass it with a hard-coded chat or token.
- **Missing token:** ask the operator to restore the configured credential; do
  not inspect or print unrelated environment state.
- **Markdown send failure:** the helper retries plain text automatically. Report
  its final error if both attempts fail.
- **No direct debate reply:** the poll may have timed out, received no later text
  from the configured chat, or conflicted with a webhook/listener that owns
  updates. Keep any gate pending and use the owning listener or terminal path;
  do not start a competing raw poller.
