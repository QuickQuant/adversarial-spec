# Current Model Recommendations

> **Last updated: 2026-03-12**
> Review this file when a new model is released. Update models here, then sync hardcoded
> defaults in `scripts/` (search for the old model name).

## Recommended Models by Role

### Attack / Critique (concern generation)
Models that find issues in specs. Diverse perspectives matter more than raw power.

| Provider | Model ID | Notes |
|----------|----------|-------|
| Codex CLI | `codex/gpt-5.4` | **Primary.** Free via ChatGPT subscription. Token-efficient. |
| Gemini CLI | `gemini-cli/gemini-3.1-pro-preview` | Free. Strong on unique angles. Parser may need sanity check (outputs `### N.` headers). |
| Claude CLI | `claude-cli/claude-sonnet-4-6` | Free. Cannot nest inside a Claude session — use only from Codex or standalone. |
| Gemini CLI | `gemini-cli/gemini-3-flash-preview` | Free. Faster, cheaper, good for quick passes. |

### Evaluation (concern judgment)
Models that evaluate whether concerns are valid. The pipeline auto-selects eval models, but
**Claude (the orchestrator) is the final evaluator** — pipeline eval is advisory.

| Provider | Model ID | Notes |
|----------|----------|-------|
| Codex CLI | `codex/gpt-5.4` | Default eval model. Use `--eval-codex-reasoning medium` for gauntlet evals. |
| Gemini CLI | `gemini-cli/gemini-3.1-pro-preview` | Second eval model for multi-model consensus. |

### Frontier (deep analysis, final boss)
For tasks requiring maximum reasoning depth.

| Provider | Model ID | Notes |
|----------|----------|-------|
| Claude | Claude Opus 4.6 | The orchestrating model. Best evaluator — has full codebase context. |
| Codex CLI | `codex/gpt-5.4` | With `--codex-reasoning high` for critique/attack work or `--eval-codex-reasoning xhigh` for gauntlet evaluation. |

## Deprecated Models

| Old Model | Replacement | When |
|-----------|-------------|------|
| `codex/gpt-5.3-codex` | `codex/gpt-5.4` | 2026-03-05 (GPT-5.4 release) |
| `codex/gpt-5.1-codex-max` | `codex/gpt-5.4` | 2026-03-05 |
| `gpt-5.3` (API) | `gpt-5.4` (if using API) | 2026-03-05 |
| `gemini-cli/gemini-3-pro-preview` | `gemini-cli/gemini-3.1-pro-preview` | 2026-03-28 (Gemini 3.1 Pro release) |

> **WARNING:** Do NOT use `gemini-2.5-pro` (API or CLI). It shares the same quota as `gemini-3.1-pro-preview` and will burn through your free-tier allowance. Always use `gemini-3.1-pro-preview` instead — it is strictly better.

## Paid API Models (avoid for adversarial-spec debates)

Per user preference: **never use paid APIs for adversarial-spec debates — use CLIs only (free).**

| Provider | Model ID | Cost | When to use |
|----------|----------|------|-------------|
| OpenAI API | `gpt-5.4` | $5/$15 per 1M tok | Only if CLI is unavailable |
| OpenRouter | `openrouter/openai/gpt-5.4` | Varies | Only if CLI is unavailable |

## Keeping Defaults in Sync

When updating this file, also update hardcoded model defaults in:
- `scripts/providers.py` — `MODEL_COSTS`, `PROVIDERS` list, `auto_detect_providers()`
- `scripts/gauntlet/` — search fallback strings in `model_dispatch.py` and `phase_7_final_boss.py`
- `scripts/debate.py` — docstring examples, help text
- `SETUP.md` — provider table
