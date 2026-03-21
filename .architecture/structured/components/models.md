# Component: Models

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | LLM call abstraction across providers (API + 3 CLI tools) |
| Entry | `call_models_parallel()` at scripts/models.py:894 |
| Key files | models.py (937 lines), providers.py (683 lines) |
| Depends on | litellm, subprocess (Codex/Gemini/Claude CLI), Prompts, Providers |
| Used by | Debate Engine, Gauntlet |

## What This Component Does

Models provides a unified interface for calling multiple LLM providers. It handles four calling strategies: LiteLLM for standard API models (OpenAI, Anthropic, Google, Groq, Mistral, xAI, Bedrock), and subprocess for Codex CLI, Gemini CLI, and Claude CLI. It manages parallel execution via ThreadPoolExecutor, retries with exponential backoff, response parsing (agreement markers, spec extraction), and cost tracking via a global singleton.

## Data Flow

```
IN:  model list + system prompt + user message
     └─> call_models_parallel() (models.py:894)

PROCESS:
     ├─> ThreadPoolExecutor spawns one call_single_model() per model
     ├─> Each routes by prefix: codex/ | gemini-cli/ | claude-cli/ | litellm
     ├─> Parse response: extract text, [AGREE] marker, [SPEC]...[/SPEC] tags
     ├─> cost_tracker.add() per successful call
     └─> Collect results as list[ModelResponse]

OUT: list[ModelResponse]
     └─> returned to caller (debate loop or gauntlet)
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `call_models_parallel()` | ThreadPoolExecutor orchestration | models.py:894 |
| `call_single_model()` | Router: litellm vs codex vs gemini vs claude | models.py:619 |
| `call_codex_model()` | Subprocess call to `codex exec --json --full-auto` | models.py:351 |
| `call_gemini_cli_model()` | Subprocess call to `gemini -m <model> -y` | models.py:451 |
| `call_claude_cli_model()` | Subprocess call to `claude -p --json-out` | models.py:536 |
| `CostTracker.add()` | Token cost accumulation | models.py:163 |
| `CostTracker.summary()` | Human-readable cost report | models.py:186 |
| `detect_agreement()` | Check for [AGREE] marker | models.py:226 |
| `extract_spec()` | Extract [SPEC]...[/SPEC] content | models.py:231 |
| `extract_tasks()` | Parse [TASK]...[/TASK] structured task data | models.py:240 |
| `generate_diff()` | Diff between original and revised spec | models.py:340 |
| `load_context_files()` | Load --context files as markdown sections | models.py:207 |

## Common Patterns

### Model Routing by Prefix

`call_single_model()` checks model prefix to route:
- `codex/` prefix → subprocess to Codex CLI with JSON event stream parsing
- `gemini-cli/` prefix → subprocess to Gemini CLI with noise filtering
- `claude-cli/` prefix → subprocess to Claude CLI with JSON output parsing
- Everything else → `litellm.completion()`

### Retry with Exponential Backoff

Failed calls retry up to MAX_RETRIES=3 with backoff: RETRY_BASE_DELAY=1.0 * 2^attempt → 1s, 2s, 4s. On final failure, ModelResponse.error is populated.

### CLI File Safety Preamble

CLI tools get `CLI_FILE_SAFETY_PREAMBLE` (models.py:112-120) prepended to prevent them from modifying files.

## Error Handling

- **API timeouts**: Caught and retried with backoff
- **Subprocess failures**: TimeoutExpired and CalledProcessError caught, converted to error responses
- **Missing CLI tools**: `shutil.which()` check at import time (CODEX_AVAILABLE, GEMINI_CLI_AVAILABLE, CLAUDE_CLI_AVAILABLE)
- **JSON parse errors**: Malformed CLI responses logged but don't crash (graceful degradation)
- **Rate limits**: Handled by litellm's built-in retry logic

## Concurrency Concerns

| Resource | Callers | Synchronization | Risk |
|----------|---------|-----------------|------|
| `cost_tracker` (global singleton) | Multiple threads via `call_single_model()`, gauntlet phases | `threading.Lock` in `CostTracker.add()` | Shared totals and `by_model` updates are serialized; contention is low because model calls are I/O-bound. |

## Configuration

| Config | Source | Default |
|--------|--------|---------|
| MODEL_COSTS | providers.py dict | Per-model input/output rates |
| MAX_RETRIES | models.py constant | 3 |
| RETRY_BASE_DELAY | models.py constant | 1.0 seconds |
| Codex reasoning | `--codex-reasoning` for critique/attack flows, `--eval-codex-reasoning` for gauntlet eval | DEFAULT_CODEX_REASONING from providers / gauntlet defaults |

## Integration Points

**Calls out to:**
- `litellm.completion()` — standard API calls
- `subprocess.run("codex exec --json")` — Codex CLI
- `subprocess.run("gemini -m")` — Gemini CLI
- `subprocess.run("claude -p --json-out")` — Claude CLI
- `providers.MODEL_COSTS` — cost lookup

**Called by:**
- `debate.py:run_critique()` — debate rounds
- `gauntlet/model_dispatch.py` and gauntlet phase modules — adversary/eval calls

## LLM Notes

- CLI tool models (codex/, gemini-cli/, claude-cli/) have $0 cost (subscription-based) but tokens are still tracked.
- Token estimation for Gemini CLI: `len(text) // 4` (rough approximation).
- `is_o_series_model()` detects O-series models that need special handling (no custom temperature).
- `cost_tracker` is a module-level singleton (models.py:204). All calls in a process share it.
- When adding new models, update `MODEL_COSTS` in providers.py.
- ModelResponse dataclass at models.py:141 — fields: model, response, agreed, spec, input_tokens, output_tokens, cost, error.
