# Model Reference for Adversarial Spec

**Last Updated:** February 2026

This file is the single source of truth for model references throughout the adversarial-spec skill. When new models are released, update this file first, then use the mappings to update examples in SKILL.md, debate.py, and specs.

## Architecture: Who Is Who?

**Claude (Opus) = The Orchestrator**
- Claude is running the adversarial-spec skill
- Claude is NOT called via API - it IS the coordinating agent
- Claude provides its own critiques alongside the opponent models

**Opponent Models = External Challengers**
- These are the models called via CLI/API to challenge the spec
- You want **strong** models here - weak opponents defeat the purpose
- CLI tools are ideal: **FREE + frontier quality**

**Haiku's role**: NOT for debate opponents. Haiku is only useful for Claude Code's internal quick tasks. In adversarial debate, you want the strongest challengers possible.

---

## IMPORTANT: CLI Tools = Free Frontier Models

**CLI tools give you frontier-quality models for FREE (part of subscriptions).**

Why pay for `deepseek/r1-distill` at $0.03/1M when `codex/gpt-5.3-codex` is **$0.00** AND better?

### Priority Order:
1. **CLI tools (free + frontier)**: Codex CLI, Gemini CLI
2. **API (if no subscriptions)**: Only as fallback

---

## CLI Tools (FREE - Subscription-Based)

### Codex CLI (ChatGPT Plus $20/mo or Pro $200/mo)

| Model | Default Reasoning | Notes |
|-------|-------------------|-------|
| `codex/gpt-5.3-codex` | **xhigh** | **NEW (Feb 2026)** 25% faster, 400k context, 128k output, mid-turn steering |
| `codex/gpt-5.2-codex` | xhigh | Previous frontier, still available |
| `codex/gpt-5.1-codex-max` | xhigh | Extended tasks (24+ hours) |
| `codex/gpt-5.1-codex-mini` | medium | Quick iterations (but why use weaker?) |

**Requires Codex CLI v0.98.0+** for gpt-5.3-codex. Update: `npm install -g @openai/codex@latest`

**Reasoning effort**: `--codex-reasoning` (minimal, low, medium, high, xhigh)
- Default for gpt-5.3-codex: **xhigh**
- OpenAI recommends "medium" as daily driver, "xhigh" for hard tasks
- For adversarial debate: **use xhigh** (we want rigorous critique)

### Gemini CLI (Free tier or Google AI Premium)

| Model | Use Case | Notes |
|-------|----------|-------|
| `gemini-cli/gemini-3.1-pro-preview` | **Best for debate** | Top LMArena (1501 Elo) |
| `gemini-cli/gemini-3-flash-preview` | Fast iteration | Pro-level at Flash speed |

**Free tier**: 60 requests/min, 1000/day with personal Google account

### Claude Code (Claude Pro $20/mo, Max $100-200/mo)

**Note**: Claude is the orchestrator, not an opponent. These models are for when YOU'RE running Claude Code, not for calling as debate opponents.

| Model | Notes |
|-------|-------|
| `claude-opus-4-7` | **Use this (Apr 2026)**. Latest Opus, most capable. |
| `claude-sonnet-4-6` | Good, but Opus is often same total cost due to efficiency |
| `claude-haiku-4-5-20251001` | NOT for debate. Only for quick internal tasks. |

**Economics**: Opus uses fewer tokens for the same prompt, so total cost is often on par with Sonnet. When in doubt, use Opus.

---

## API Models (Pay-Per-Token)

Only use these when CLI tools are unavailable.

## Model Tier Definitions

| Tier | Use Case | Characteristics |
|------|----------|-----------------|
| **Frontier** | Best quality, complex tasks | Highest capability, slower, most expensive |
| **Balanced** | Good quality/cost tradeoff | Near-frontier quality, moderate cost |
| **Fast** | Quick iterations, simple tasks | Lower latency, good for drafts |
| **Budget** | High volume, cost-sensitive | Cheapest, basic tasks |

---

## API Model Mappings (April 2026)

### OpenAI (API: `OPENAI_API_KEY`)

| Tier | Old Reference | Current Model | Notes |
|------|---------------|---------------|-------|
| Frontier | `o1`, `gpt-4-turbo` | `gpt-5.5` | Best reasoning, $5/$30 per 1M tokens |
| Balanced | `gpt-4o` | `o3-mini` | Good reasoning at lower cost |
| Fast | `gpt-4o-mini` | `gpt-5.2-mini` | Fast, cheaper |
| Budget | - | `o4-mini` | Batch processing available |

### OpenAI Codex CLI (Subscription-based)

| Tier | Old Reference | Current Model | Notes |
|------|---------------|---------------|-------|
| Frontier | `codex/gpt-5.2-codex` | `codex/gpt-5.5` | Current flagship, 1M ctx, 128k output |
| Balanced | `codex/o1-codex` | `codex/gpt-5.5` | Current recommended Codex model |
| Extended | - | `codex/gpt-5.1-codex-max` | 24+ hour tasks |

### Anthropic (API: `ANTHROPIC_API_KEY`)

| Tier | Old Reference | Current Model | Notes |
|------|---------------|---------------|-------|
| Frontier | `claude-opus-4-5-20251124` | `claude-opus-4-7` | Latest Opus, best for complex reasoning |
| Balanced | `claude-3.5-sonnet`, `claude-sonnet-4` | `claude-sonnet-4-6` | Best value, $3/$15 per 1M |
| Fast | `claude-3-sonnet` | `claude-haiku-4-5` | Near-frontier quality, fast |
| Budget | `claude-3-haiku` | `claude-haiku-4-5` | Same as fast tier now |

### Google Gemini (API: `GEMINI_API_KEY`)

| Tier | Old Reference | Current Model | Notes |
|------|---------------|---------------|-------|
| Frontier | `gemini/gemini-pro` | `gemini/gemini-3-pro` | Top LMArena score (1501 Elo) |
| Balanced | `gemini/gemini-2.0-flash` | `gemini/gemini-2.5-pro` | Stable, long-context |
| Fast | `gemini/gemini-1.5-flash` | `gemini/gemini-3-flash` | 3x faster than 2.5 Pro, $0.50/$3 per 1M |
| Budget | - | `gemini/gemini-3-flash` | Same as fast (very cheap) |

### Google Gemini CLI (Subscription-based)

| Tier | Old Reference | Current Model | Notes |
|------|---------------|---------------|-------|
| Frontier | - | `gemini-cli/gemini-3.1-pro-preview` | Full Gemini 3 Pro |
| Fast | - | `gemini-cli/gemini-3-flash-preview` | Fast iteration |

### xAI (API: `XAI_API_KEY`)

| Tier | Old Reference | Current Model | Notes |
|------|---------------|---------------|-------|
| Frontier | `xai/grok-2`, `xai/grok-3` | `xai/grok-4` | Native tool use, real-time search |
| Balanced | `xai/grok-beta` | `xai/grok-4.1-fast` | Enterprise API |
| Fast | - | `xai/grok-3-mini-think` | Reasoning model |

### Mistral (API: `MISTRAL_API_KEY`)

| Tier | Old Reference | Current Model | Notes |
|------|---------------|---------------|-------|
| Frontier | `mistral/mistral-large` | `mistral/mistral-large-3` | 675B MoE, Apache 2.0 |
| Balanced | `mistral/mistral-medium` | `mistral/mistral-medium-3` | $0.40/$2 per 1M |
| Fast | `mistral/mistral-small` | `mistral/mistral-small-3.1` | Efficient |
| Budget | `mistral/mistral-tiny` | `mistral/ministral-8b` | Edge/local use |

### Groq (API: `GROQ_API_KEY`)

| Tier | Old Reference | Current Model | Notes |
|------|---------------|---------------|-------|
| Frontier | `groq/llama-3-70b` | `groq/llama-4-maverick` | 400B total params |
| Balanced | `groq/llama-3.3-70b-versatile` | `groq/llama-3.3-70b-versatile` | Still excellent |
| Fast | `groq/llama-3-8b` | `groq/llama-4-scout` | 460 tok/s, $0.11/$0.34 per 1M |
| Budget | - | `groq/llama-3.3-70b-specdec` | 1665 tok/s with spec decoding |

### DeepSeek (API: `DEEPSEEK_API_KEY`)

| Tier | Old Reference | Current Model | Notes |
|------|---------------|---------------|-------|
| Frontier | - | `deepseek/deepseek-r1` | o1-level reasoning, $0.70/$2.40 per 1M |
| Balanced | `deepseek/deepseek-chat` | `deepseek/deepseek-v3.2-exp` | $0.028/$0.32 per 1M (extremely cheap) |
| Fast | - | `deepseek/deepseek-v3.1` | $0.15/$0.75 per 1M |
| Budget | - | `deepseek/r1-distill-llama-70b` | $0.03/$0.11 per 1M |

### OpenRouter (API: `OPENROUTER_API_KEY`)

Routes to other providers. Update prefixes to match current models:

| Old Reference | Current Model |
|---------------|---------------|
| `openrouter/openai/gpt-4o` | `openrouter/openai/gpt-5.2` |
| `openrouter/anthropic/claude-3.5-sonnet` | `openrouter/anthropic/claude-sonnet-4-6` |

---

## Recommended Opponent Combinations for Debate

**Goal**: Get the strongest challengers possible. Weak opponents = weak specs.

### Best (FREE - CLI tools):
```bash
# Frontier models, zero cost
codex/gpt-5.3-codex,gemini-cli/gemini-3.1-pro-preview

# Add Flash for a third perspective (still free, still strong)
codex/gpt-5.3-codex,gemini-cli/gemini-3.1-pro-preview,gemini-cli/gemini-3-flash-preview
```

### If no subscriptions (API fallback):
```bash
# Best API value - still want strong models, not budget
deepseek/deepseek-r1,groq/llama-4-maverick

# NOT recommended: weak models like deepseek-v3.2-exp or groq/llama-4-scout
# Save money on volume tasks, not on quality critique
```

### DON'T use for debate:
- `codex/gpt-5.1-codex-mini` - weaker model, defeats purpose
- `claude-haiku-*` - not an opponent, and too weak anyway
- Any "budget" tier model - you want rigorous critique

---

## Example Replacements

When updating documentation, **use CLI tools** (free + frontier):

| Old (2024 model) | New (CLI - FREE + frontier) |
|------------------|----------------------------|
| `gpt-4o` | `codex/gpt-5.3-codex` |
| `gpt-4o,gemini/gemini-2.0-flash` | `codex/gpt-5.3-codex,gemini-cli/gemini-3.1-pro-preview` |
| `o1` | `codex/gpt-5.3-codex` (defaults to xhigh reasoning) |
| `gemini/gemini-2.0-flash` | `gemini-cli/gemini-3-flash-preview` |
| `gemini/gemini-pro` | `gemini-cli/gemini-3.1-pro-preview` |

**API fallback** (only if no subscriptions):

| Old | New (API - strong models) |
|-----|---------------------------|
| `gpt-4o` | `deepseek/deepseek-r1` or `groq/llama-4-maverick` |
| Multi-model | `deepseek/deepseek-r1,xai/grok-4` |

**Notes:**
- Don't recommend budget API models for debate - defeats the purpose
- CLI tools are both free AND frontier quality - no tradeoff
- Always show CLI examples first in docs

---

## Sources

- [OpenAI Pricing](https://openai.com/api/pricing/) - GPT-5.2, o3 series
- [Anthropic Claude](https://www.anthropic.com/claude/opus) - Opus 4.7, Sonnet 4.5, Haiku 4.5
- [Google Gemini](https://blog.google/products/gemini/gemini-3/) - Gemini 3 Pro/Flash
- [xAI Grok](https://x.ai/news) - Grok 4 series
- [Mistral AI](https://mistral.ai/pricing) - Large 3, Medium 3
- [Groq](https://groq.com/pricing) - Llama 4 on LPU
- [DeepSeek](https://api-docs.deepseek.com/quick_start/pricing) - V3.2, R1

---

## Maintenance Notes

**When to update this file:**
1. New model releases from any provider
2. Model deprecations
3. Significant pricing changes
4. New providers added to litellm

**After updating this file:**
1. Update SKILL.md examples
2. Update debate.py docstring examples
3. Update providers.py model lists
4. Consider updating test fixtures (optional - tests use model names as fixtures)
