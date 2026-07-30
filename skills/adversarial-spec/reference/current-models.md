# Current Model Recommendations

> **Last updated: 2026-07-30**
> Review this file when a new model is released. Update models here, then sync hardcoded
> defaults in `scripts/` (search for the old model name).

## Recommended Models by Role

### Attack / Critique (concern generation)
Models that find issues in specs. Diverse perspectives matter more than raw power.

| Provider | Model ID | Notes |
|----------|----------|-------|
| Codex CLI | `codex/gpt-5.6-luna` | **Primary attack model.** Free via ChatGPT subscription. Use xhigh effort. |
| Gemini CLI | `gemini-cli/gemini-3.6-flash-high` | Free. Strong on unique angles. Parser may need sanity check (outputs `### N.` headers). |
| Claude CLI | `claude-cli/claude-opus-4-7` | Free. Cannot nest inside a Claude session — use only from Codex or standalone. |
| Gemini CLI | `gemini-cli/gemini-3-flash-preview` | Free. Faster, cheaper, good for quick passes. |

### Evaluation (concern judgment)
Models that evaluate whether concerns are valid. The pipeline auto-selects eval models, but
**Claude (the orchestrator) is the final evaluator** — pipeline eval is advisory.

| Provider | Model ID | Notes |
|----------|----------|-------|
| Codex CLI | `codex/gpt-5.6-sol` | Default eval model. Use max effort for gauntlet evals. |
| Gemini CLI | `gemini-cli/gemini-3.6-flash-high` | Second eval model for multi-model consensus. |

### Frontier (deep analysis, final boss)
For tasks requiring maximum reasoning depth.

| Provider | Model ID | Notes |
|----------|----------|-------|
| Claude | Claude Opus 4.7 | The orchestrating model. Best evaluator — has full codebase context. |
| Codex CLI | `codex/gpt-5.6-sol` | Max-intelligence work with max effort; use Terra max for single-issue work and Luna xhigh for gauntlet attacks. |

## Deprecated Models

| Old Model | Replacement | When |
|-----------|-------------|------|
| Retired pre-5.6 Codex CLI tokens | Role-specific GPT-5.6 token | 2026-07-09 |
| Retired pre-5.6 OpenAI API tokens | `gpt-5.6-sol` (if using API) | 2026-07-09 |
| Retired Gemini Pro preview tokens | `gemini-cli/gemini-3.6-flash-high` | 2026-07-30 |

> **WARNING:** Do not use retired Gemini Pro-generation tokens (API or CLI). Use `gemini-3.6-flash-high` for Gemini critic, adversary, and evaluation seats.

## Paid API Models (avoid for adversarial-spec debates)

Per user preference: **never use paid APIs for adversarial-spec debates — use CLIs only (free).**

| Provider | Model ID | Cost | When to use |
|----------|----------|------|-------------|
| OpenAI API | `gpt-5.6-sol` | $5/$30 per 1M tok | Only if CLI is unavailable |
| OpenRouter | `openrouter/openai/gpt-5.6-sol` | Varies | Only if CLI is unavailable |

## Keeping Defaults in Sync

When updating this file, also update hardcoded model defaults in:
- `scripts/providers.py` — `MODEL_COSTS`, `PROVIDERS` list, `auto_detect_providers()`
- `scripts/gauntlet/` — search fallback strings in `model_dispatch.py` and `phase_7_final_boss.py`
- `scripts/debate.py` — docstring examples, help text
- `SETUP.md` — provider table
