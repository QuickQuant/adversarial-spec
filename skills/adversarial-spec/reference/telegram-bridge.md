# Telegram Bridge — Agent Reference

Projects can use a Telegram bot as a mobile-accessible interface for human-gated pipeline transitions and long-running reviews. Any agent operating in a project with a Telegram bridge configured can use it to communicate with Jason when he's away from the terminal.

## Per-Project Configuration

Each project that uses the bridge defines its own:

- **Bot handle** (e.g., `@masterfizzybot`)
- **Token env var** (e.g., `FIZZYBOT_TELEGRAM_KEY`) — stored in `/etc/environment`, available to systemd services; source it in shell scripts
- **Chat ID** — Jason's Telegram chat ID (same across projects, but projects should reference the value explicitly)
- **Project emoji framing** — e.g., `🍾🟦` for fizzy-pipeline-mcp. Every message starts and ends with the project emoji so Jason can visually distinguish which project is talking.

These values live in the project's `CLAUDE.md` (or a dedicated `onboarding/telegram-config.md`) so the agent can read them when initiating a message.

Throughout this reference, placeholders like `<BOT_TOKEN_ENV>`, `<CHAT_ID>`, and `<PROJECT_EMOJI>` stand in for those per-project values.

## Core Rules

1. **Never block the conversation polling for replies.** Use `run_in_background=true` on Bash calls that long-poll. Tell the user "listening in background" and keep working or hand control back.
2. **Use `reply_to_message_id` to correlate replies.** When Jason replies to a specific message, the Telegram API returns `reply_to_message.message_id`. Match that to the card/gate you sent the outbound for.
3. **Send full content, not summaries.** When presenting a plan, roadmap, or spec for review, send the complete content across multiple messages if needed. No shortcuts, no "you saw this earlier" — Jason may be reading on mobile with no prior context.
4. **Always frame with the project emoji.** Start and end every message with `<PROJECT_EMOJI>`. Non-negotiable — it's how Jason visually routes attention.
5. **Use Markdown parse_mode for structured content.** Escape underscores (`\\_`) and other Markdown specials in identifiers.

## Sending a Message

```bash
source <(grep <BOT_TOKEN_ENV> /etc/environment) && \
curl -s -X POST "https://api.telegram.org/bot${<BOT_TOKEN_ENV>}/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": <CHAT_ID>,
    "parse_mode": "Markdown",
    "text": "<PROJECT_EMOJI> your message here <PROJECT_EMOJI>"
  }'
```

For replies to a specific prior message (to maintain thread correlation):
```json
{"chat_id": <CHAT_ID>, "reply_to_message_id": 42, "text": "<PROJECT_EMOJI> ... <PROJECT_EMOJI>"}
```

## Listening for a Reply (Background Pattern)

```bash
source <(grep <BOT_TOKEN_ENV> /etc/environment) && \
LAST_UPDATE=$(curl -s "https://api.telegram.org/bot${<BOT_TOKEN_ENV>}/getUpdates?offset=-1" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); u=d.get('result',[]); print(u[-1]['update_id'] if u else 0)") && \
OFFSET=$((LAST_UPDATE + 1)) && \
while true; do
  RESULT=$(curl -s "https://api.telegram.org/bot${<BOT_TOKEN_ENV>}/getUpdates?offset=${OFFSET}&timeout=30") && \
  TEXT=$(echo "$RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
updates = data.get('result', [])
if updates:
    msg = updates[-1].get('message', {})
    text = msg.get('text', '')
    if text:
        print(text)
        sys.exit(0)
sys.exit(1)
" 2>/dev/null) && echo "$TEXT" && break
done
```

**Always run this with `run_in_background=true`.** When the reply arrives, the background task completes and a `task-notification` system message fires. Read the output file then to get the reply.

## Extracting reply_to_message_id

```python
import sys, json
data = json.load(sys.stdin)
updates = data.get('result', [])
if updates:
    msg = updates[-1].get('message', {})
    reply = msg.get('reply_to_message', {})
    print(f"text: {msg.get('text','')}")
    print(f"reply_to_message_id: {reply.get('message_id','none')}")
```

Use this to correlate Jason's reply back to the specific gate or question you sent.

## When to Use Telegram

- **Human-gated pipeline transitions** — roadmap confirmation, final plan approval
- **Long-running review requests** — when Jason may step away and need to approve from mobile
- **Dogfooding** — when explicitly testing the Telegram flow
- **Status updates during long background tasks** — only if Jason has asked for them

## When NOT to Use Telegram

- For routine conversation during an active terminal session — stay in the terminal
- For anything Jason hasn't asked you to move there
- For debugging output or verbose logs — keep those local
- As a substitute for proper logging or error handling

## Troubleshooting

- **`getUpdates` returns 0:** A webhook may be set (consumes updates). Check with `getWebhookInfo`. If the project has a dedicated systemd listener owning webhook consumption, use that listener's log/output instead of polling `getUpdates` directly.
- **Messages not arriving:** Verify `getMe` works to confirm token is valid.
- **Reply not detected:** Ensure you're using long polling with the correct `offset`. Use `offset=-1` on first fetch to skip old messages, then increment.

## Related Specs

- Human-Gated Pipeline Transitions — the full spec that turns this ad-hoc bridge into a proper webhook-driven system with assign/pin side effects. Lives in the project that owns the bridge implementation (currently `fizzy-pipeline-mcp/.adversarial-spec/specs/human-gated-pipeline-transitions/`).
