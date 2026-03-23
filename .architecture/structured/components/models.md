# Component: Models

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | LLM call abstraction via LiteLLM + CLI subprocess routing |
| Entry | `call_models_parallel()` at models.py:901 |
| Key files | models.py |
| Depends on | Providers, Prompts |
| Used by | Debate Engine, Gauntlet Pipeline (all phases) |
| Runtime status | implemented |
| Architecture status | active_primary |

## What This Component Does

The models layer abstracts 7+ LLM providers behind a unified interface. API-based models (OpenAI, Anthropic, Google, xAI, Mistral, Groq) route through LiteLLM's `completion()` call. Subscription-based CLI models (Codex, Gemini CLI, Claude CLI) route through subprocess calls, bypassing LiteLLM entirely. A global thread-safe `CostTracker` accumulates token usage and costs across all parallel calls.

## Data Flow

```
IN:  Model list + system/user prompts
     └─> call_models_parallel() (models.py:901)

PROCESS:
     ├─> ThreadPoolExecutor(max_workers=len(models))
     ├─> Per model: call_single_model() routes by prefix
     │   ├─> [codex/] -> call_codex_model() (subprocess)
     │   ├─> [gemini-cli/] -> call_gemini_cli_model() (subprocess)
     │   ├─> [claude-cli/] -> call_claude_cli_model() (subprocess)
     │   └─> [other] -> litellm.completion()
     └─> cost_tracker.add() per response (Lock-protected)

OUT: list[ModelResponse] + cost summary
     └─> Collected by caller (debate or gauntlet)
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `call_models_parallel()` | Parallel dispatch to N models | models.py:901 |
| `call_single_model()` | Route to provider, retry on failure | models.py:626 |
| `call_codex_model()` | Subprocess call to Codex CLI | models.py:~650 |
| `call_gemini_cli_model()` | Subprocess call to Gemini CLI | models.py:~700 |
| `call_claude_cli_model()` | Subprocess call to Claude CLI | models.py:~750 |
| `cost_tracker.add()` | Thread-safe cost accumulation | models.py:165 |
| `_extract_claude_cli_output()` | Parse Claude CLI event format | models.py:52 |

## Contracts

### Type Contracts

| Contract | Purpose | Owner | Consumed By |
|----------|---------|-------|-------------|
| `ModelResponse` | Per-model result (response, tokens, cost, agreed) | models.py:142 | debate.py, gauntlet phases |
| `CostTracker` | Thread-safe cost accumulator | models.py:156 | Global singleton at models.py:211 |

## Common Patterns

### CLI Subprocess Pattern
Three CLI model functions duplicate 80+ lines each of subprocess boilerplate (spawn process, capture output, parse response, handle timeout). This is a known pattern debt (see patterns.md).

### Retry with Exponential Backoff
MAX_RETRIES=3, RETRY_BASE_DELAY=1.0s. Backoff: 1s, 2s, 4s. On final failure, returns error ModelResponse (doesn't raise).

## Error Handling

- **Model call failure**: Caught, logged, retried up to 3 times. Returns error ModelResponse on exhaustion.
- **CLI subprocess timeout**: Subprocess killed, treated as failure, triggers retry.
- **litellm import failure**: ImportError handler with helpful installation message.

## Concurrency Concerns

| Resource | Callers | Synchronization | Risk |
|----------|---------|-----------------|------|
| `cost_tracker` (global) | All ThreadPoolExecutor workers | `threading.Lock` (models.py:163) | Low — Lock is lightweight, short hold time |

## Configuration

| Config | Source | Default |
|--------|--------|---------|
| `MAX_RETRIES` | Constant | 3 |
| `RETRY_BASE_DELAY` | Constant | 1.0 seconds |
| `LITELLM_LOG` | Set at import | "ERROR" |

## Integration Points

**Calls out to:**
- `litellm.completion()` — for API-based models
- `subprocess` — for CLI models (codex, gemini, claude)
- `Providers.MODEL_COSTS` — for cost rate lookup

**Called by:**
- `debate.py:run_critique()` — for debate rounds
- `gauntlet/phase_*.py` — for all gauntlet phases (via model_dispatch)

## LLM Notes

- CLI models report 0 tokens and $0 cost. This is intentional — they're subscription-based.
- The three CLI subprocess functions are nearly identical (known duplication). A refactor to extract `_call_cli_model()` is pending.
- `cost_tracker` is a global singleton. Thread-safe via Lock but not idiomatic. Works for the threading model used here.
