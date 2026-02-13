# Adversarial Spec - Provider Setup

This document covers provider configuration. For usage, see [SKILL.md](SKILL.md).

## Requirements

- Python 3.10+ with `litellm` package installed
- API key for at least one provider, OR CLI tools (codex, gemini) installed

**IMPORTANT: Do NOT install the `llm` package (Simon Willison's tool).** This skill uses `litellm`.

## Supported Providers

| Provider   | API Key Env Var        | Example Models                              |
|------------|------------------------|---------------------------------------------|
| OpenAI     | `OPENAI_API_KEY`       | `gpt-5.3`                                   |
| Anthropic  | `ANTHROPIC_API_KEY`    | `claude-sonnet-4-5-20250929`, `claude-opus-4-6`  |
| Google     | `GEMINI_API_KEY`       | `gemini/gemini-3-pro`, `gemini/gemini-3-flash` |
| xAI        | `XAI_API_KEY`          | `xai/grok-3`, `xai/grok-beta`               |
| Mistral    | `MISTRAL_API_KEY`      | `mistral/mistral-large`, `mistral/codestral`|
| Groq       | `GROQ_API_KEY`         | `groq/llama-3.3-70b-versatile`              |
| OpenRouter | `OPENROUTER_API_KEY`   | `openrouter/openai/gpt-5.3`, `openrouter/anthropic/claude-sonnet-4-5` |
| Deepseek   | `DEEPSEEK_API_KEY`     | `deepseek/deepseek-chat`                    |
| Zhipu      | `ZHIPUAI_API_KEY`      | `zhipu/glm-4`, `zhipu/glm-4-plus`           |
| Codex CLI  | (ChatGPT subscription) | `codex/gpt-5.3-codex`, `codex/gpt-5.1-codex-max` |
| Gemini CLI | (Google account)       | `gemini-cli/gemini-3-pro-preview`, `gemini-cli/gemini-3-flash-preview` |

Run `python3 ~/.claude/skills/adversarial-spec/scripts/debate.py providers` to see which keys are set.

## CLI Tool Setup

### Codex CLI
```bash
npm install -g @openai/codex && codex login
```
- `--codex-reasoning` (minimal, low, medium, high, xhigh)
- `--codex-search` enables web search

### Gemini CLI
```bash
npm install -g @google/gemini-cli && gemini auth
```
No API key needed - uses Google account.

## Troubleshooting Auth Conflicts

If you see "Both a token (claude.ai) and an API key (ANTHROPIC_API_KEY) are set":

**To use claude.ai token**: `unset ANTHROPIC_API_KEY`

**To use API key**: `claude /logout`

## AWS Bedrock Support

For enterprise users routing through AWS Bedrock:

```bash
# Enable
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py bedrock enable --region us-east-1
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py bedrock add-model claude-3-sonnet

# Check status
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py bedrock status

# Disable
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py bedrock disable

# List model mappings
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py bedrock list-models
```

Config stored at `~/.claude/adversarial-spec/config.json`.
