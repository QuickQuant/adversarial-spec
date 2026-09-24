# Adversarial Spec - Provider Setup

For usage, see [SKILL.md](SKILL.md). Select models, reasoning effort, and permitted
provider paths only from [current-models.md](reference/current-models.md).

## Requirements

- Python 3.14+, `uv`, and the project dependencies, including `litellm`.
- Credentials for the selected provider or an authenticated CLI.
- Do **not** install the unrelated `llm` package; this skill uses `litellm`.

## CLI Setup

### Codex

```bash
npm install -g @openai/codex
codex login
```

Select a Codex task class and invocation from `reference/current-models.md`.

### Google via Antigravity

Install and authenticate Antigravity's `agy` CLI with the intended account; ensure
`agy` is on PATH. Use `agy models` to inspect availability and the task-class
invocation in `reference/current-models.md` to select a seat.

**Runtime drift:** `scripts/providers.py` and `scripts/gauntlet/model_dispatch.py`
still contain retired provider/model defaults. This setup page does not change
those defaults; verify the actual selected route before dispatch.

## Provider Credentials

`scripts/providers.py` loads credentials from the environment and the file selected
by `LLM_PROVIDERS_ENV_FILE` (default `~/.config/secrets/llm-providers`). Keep secrets
out of the repository. The model authority above determines which routes may run.

| Provider | Credential variable |
|----------|---------------------|
| OpenAI | `OPENAI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| Google API | `GEMINI_API_KEY` |
| xAI | `XAI_API_KEY` |
| Mistral | `MISTRAL_API_KEY` |
| Groq | `GROQ_API_KEY` |
| OpenRouter | `OPENROUTER_API_KEY` |
| DeepSeek | `DEEPSEEK_API_KEY` |
| Zhipu | `ZHIPUAI_API_KEY` |
| NVIDIA NIM | `NVIDIA_NIM_API_KEY` |

Inspect detected credentials with
`python3 ~/.claude/skills/adversarial-spec/scripts/debate.py providers`.
For conflicting Anthropic token/API-key authentication, select the intended
credential: unset `ANTHROPIC_API_KEY` for subscription-token use, or log out of the
Claude CLI subscription before API-key use.

## AWS Bedrock

With AWS credentials and model access configured, use `debate.py bedrock enable
--region <region>` and `debate.py bedrock add-model <enabled-model-id>`.
`bedrock status`, `bedrock list-models`, and `bedrock disable` inspect or change
configuration at `~/.claude/adversarial-spec/config.json`. Select only models
permitted by `reference/current-models.md`.
