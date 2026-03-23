## Convergence Rules

- Maximum 10 rounds per cycle (ask user to continue if reached)
- ALL models AND Claude must agree for convergence
- More models = stricter convergence (each adds a perspective)
- Do not agree prematurely - only accept when document is genuinely complete
- Apply critique criteria rigorously based on document type

**Quality over speed**: The goal is a document that needs no further refinement. If any participant raises a valid concern, address it thoroughly. A spec that takes 7 rounds but is bulletproof is better than one that converges in 2 rounds with gaps.

**When to say [AGREE]**: Only agree when you would confidently hand this document to:
- For PRD: A product team starting implementation planning
- For Tech Spec: An engineering team starting a sprint

**Skepticism of early agreement**: If opponent models agree too quickly (rounds 1-2), they may not have read the full document carefully. Always press for confirmation.

## Telegram Integration (Optional)

Enable real-time notifications and human-in-the-loop feedback. Only active with `--telegram` flag.

### Setup

1. Message @BotFather on Telegram, send `/newbot`, follow prompts
2. Copy the bot token
3. Run setup:
   ```bash
   python3 ~/.claude/skills/adversarial-spec/scripts/telegram_bot.py setup
   ```
4. Message your bot, then run setup again to get chat ID
5. Set environment variables:
   ```bash
   export TELEGRAM_BOT_TOKEN="your-token"
   export TELEGRAM_CHAT_ID="your-chat-id"
   ```

### Usage

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --model codex/gpt-5.4 --doc-type tech --telegram <<'SPEC_EOF'
<document here>
SPEC_EOF
```

After each round:
- Bot sends summary to Telegram
- 60 seconds to reply with feedback (configurable via `--poll-timeout`)
- Reply incorporated into next round
- No reply = auto-continue

