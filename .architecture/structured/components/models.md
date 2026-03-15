# Component: Models

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | LLM call abstraction across providers (API + CLI tools) |
| Entry | `call_models_parallel()` at scripts/models.py |
| Key files | models.py, providers.py |
| Depends on | litellm, subprocess (Codex/Gemini CLI), Prompts, Providers |
| Used by | Debate Engine, Gauntlet |

## What This Component Does

Models provides a unified interface for calling multiple LLM providers. It handles three calling strategies: LiteLLM for standard API models (OpenAI, Anthropic, Google, Groq, Mistral, xAI, Bedrock), subprocess for Codex CLI (agentic mode with file access), and subprocess for Gemini CLI. It manages parallel execution, retries with backoff, response parsing, and cost tracking.

## Data Flow

```
IN:  model list + system prompt + user message
     └─> call_models_parallel() (models.py)

PROCESS:
     ├─> ThreadPoolExecutor spawns one call_single_model() per model
     ├─> Each routes to: litellm | codex subprocess | gemini subprocess
     ├─> Parse response: extract text, [AGREE] marker, [SPEC]...[/SPEC] tags
     ├─> cost_tracker.add() per successful call
     └─> Collect results as list[ModelResponse]

OUT: list[ModelResponse]
     └─> returned to caller (debate loop or gauntlet)
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `call_models_parallel()` | ThreadPoolExecutor orchestration | models.py |
| `call_single_model()` | Router: litellm vs codex vs gemini | models.py:470 |
| `call_codex_model()` | Subprocess call to `codex exec --json` | models.py |
| `call_gemini_cli_model()` | Subprocess call to `gemini -m` | models.py |
| `CostTracker.add()` | Token cost accumulation | models.py:101 |
| `CostTracker.summary()` | Human-readable cost report | models.py:120 |
| `extract_tasks()` | Parse tasks from LLM response | models.py |
| `generate_diff()` | Diff between original and revised spec | models.py |
| `load_context_files()` | Load additional context files for prompts | models.py:141 |

## Common Patterns

### Model Routing

`call_single_model()` checks model prefix to route:
- `codex/` prefix → subprocess to Codex CLI
- `gemini-cli/` prefix → subprocess to Gemini CLI
- Everything else → `litellm.completion()`

### Retry with Backoff

Failed calls retry up to MAX_RETRIES=3 times with exponential backoff (2^attempt seconds). On final failure, ModelResponse.error is populated.

### Agreement Detection

Responses are scanned for `[AGREE]` marker. If present, `ModelResponse.agreed = True`. Revised specs are extracted from `[SPEC]...[/SPEC]` tags.

## Error Handling

- **API timeouts**: Caught and retried with backoff
- **Subprocess failures**: TimeoutExpired and CalledProcessError caught, converted to error responses
- **Missing CLI tools**: `shutil.which()` check before attempting subprocess calls
- **Rate limits**: Handled by litellm's built-in retry logic

## Configuration

| Config | Source | Default |
|--------|--------|---------|
| MODEL_COSTS | providers.py dict | Per-model input/output rates |
| MAX_RETRIES | models.py constant | 3 |
| Codex reasoning | `--codex-reasoning` CLI | DEFAULT_CODEX_REASONING from providers |
| Codex timeout | Computed from reasoning level | Varies (hook enforces minimums) |

## Integration Points

**Calls out to:**
- `litellm.completion()` — standard API calls
- `subprocess.run("codex exec --json")` — Codex CLI
- `subprocess.run("gemini -m")` — Gemini CLI
- `providers.MODEL_COSTS` — cost lookup
- `prompts.get_system_prompt()` — prompt construction

**Called by:**
- `debate.py:run_critique()` — debate rounds
- `gauntlet.py:run_gauntlet()` — adversary calls (uses litellm directly)

## LLM Notes

- Codex and Gemini CLI models have $0 cost (subscription-based) but tokens are still tracked.
- Token estimation for Gemini CLI: `len(text) // 4` (rough approximation).
- The `is_o_series_model()` helper detects O-series models that need special prompt formatting.
- `cost_tracker` is a module-level singleton — all calls in a process share the same tracker.
- When adding new models, update `MODEL_COSTS` in providers.py.
