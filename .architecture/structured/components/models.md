# Component: Models and Provider Routing

> Derived from: `skills/adversarial-spec/scripts/models.py`, `providers.py`, `token_tracking.py` | Verified at: `ef18c66`
> If any derived-from file changed since `ef18c66`, trust source over this doc.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Normalize model selection and invoke hosted/CLI/Bedrock transports |
| Entry | `call_models_parallel()` at `models.py:1114` |
| Key files | `models.py`, `providers.py`, `token_tracking.py` |
| Depends on | LiteLLM, provider config, subprocess CLIs |
| Used by | Debate Engine, Gauntlet model dispatch, tests |
| Runtime status | implemented |
| Architecture status | active_primary |

## What This Component Does

The component turns a logical model name into one of several transport adapters, executes calls, parses provider-specific results into `ModelResponse`, and tracks token/cost totals. It supports CLI subprocess routes as well as LiteLLM/Bedrock routes; the provider registry and credential checks decide which names are usable.

## Contracts

### Type Contracts

| Contract | Purpose | Owner | Consumed By |
|---|---|---|---|
| `ModelResponse` | normalized model result | `models.py:141-151` | debate/gauntlet/output |
| `MODEL_COSTS`/`DEFAULT_COST` | cost lookup | `providers.py:26-69` | `token_tracking.py:8-70` |
| `Route` | usage-router route choice | `usage_router.py:48-53` | usage router only |

### Boundary Field Contracts

Chain: logical model → adapter → CLI/provider response → `ModelResponse`.

| Field | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| model name | always requested | yes | adapter dispatch | response metadata | invalid/unknown model must fail validation, not silently route | provider/model resolver | `models.py:688-711`, `providers.py:413-481` | verified |
| text | provider-success dependent | normalized | `ModelResponse.text` | output/session conditional | provider failure or empty content; caller must inspect error | adapter/provider | `models.py:141-151,298-688` | verified |
| input/output tokens | provider-dependent | best-effort normalization | tracker accepts optional counts | totals/output conditional | unknown usage; CLI subscription routes may intentionally report zero | adapter/provider | `models.py:141-151,688-711`, `token_tracking.py:19-70` | verified |

## Invariants

- `call_single_model` is the transport selection point (`models.py:688`); callers should not duplicate provider-specific subprocess/LiteLLM logic.
- Parallel calls return a result per requested route, including failure metadata; missing responses must not be interpreted as agreement (`models.py:1114-1168`).
- Token tracker updates are guarded by a `threading.Lock` (`token_tracking.py:19-70`).
- CLI-prefixed model routes are intentionally zero-cost/usage-optional; provider billing must not be inferred from a zero token count (`providers.py:26-69`).

## Data Flow

```text
IN: model names + prompt/context
    └─> preflight_models()/call_models_parallel() (models.py:1088-1168)
PROCESS:
    ├─> adapter selection
    ├─> subprocess/LiteLLM/Bedrock invocation
    ├─> parse text and usage
    └─> tracker update + partial-result save
OUT: ModelResponse list
     └─> debate/gauntlet callers
```

## Key Functions

| Function | Purpose | Location |
|---|---|---|
| `call_codex_model()` | Codex CLI transport | `models.py:298` |
| `call_gemini_cli_model()` | Gemini CLI transport | `models.py:405` |
| `call_claude_cli_model()` | Claude CLI transport | `models.py:500` |
| `call_single_model()` | unified transport selector | `models.py:688` |
| `preflight_models()` | lightweight model availability check | `models.py:1088` |
| `call_models_parallel()` | worker-pool dispatch and collection | `models.py:1114` |

## Common Patterns

- **Adapter normalization:** provider-specific stdout/JSON is converted to one response shape.
- **Preflight before batch:** a short `OK` probe avoids launching a large batch against unavailable CLI routes (`models.py:1027-1112`).
- **Partial recovery:** worker failures create partial artifacts for inspection (`models.py:1170-1197`).

## Error Handling

- CLI timeout/error paths become `ModelResponse` error metadata (`models.py:298-688`).
- Provider credential checks happen in `providers.validate_model_credentials` (`providers.py:481`).
- Batch collection retains failures instead of swallowing them (`models.py:1114-1168`).

## Concurrency Concerns

| Resource | Callers | Synchronization | Risk |
|---|---|---|---|
| token totals | every parallel model worker | `threading.Lock` at `token_tracking.py:19` | guarded; incorrect provider usage metadata can still distort totals |
| partial-result files | worker futures | per-result path convention; no shared lock visible | duplicate model-name routes or concurrent runs can collide |

## Configuration

| Config | Source | Default | Precedence |
|---|---|---|---|
| model costs | `providers.MODEL_COSTS` | `DEFAULT_COST` | explicit model entry overrides default |
| credentials/availability | environment + CLI presence | unavailable | env/provider checks determine eligibility |
| Bedrock | global config/profile/environment | disabled unless configured | explicit Bedrock mode/model overrides defaults |

## Integration Points

**Calls out to:** LiteLLM, model CLI binaries, AWS/Bedrock environment (`models.py:298-711`).

**Called by:** `debate.run_critique`, `gauntlet.model_dispatch.call_model`, tests.

## Active vs Target

- **Active consumers:** debate and gauntlet dispatch.
- **Legacy consumers:** direct tests/imports using script-directory module names.
- **Target architecture:** one low-level call wrapper with provider-neutral error/usage semantics.
- **Drift note:** top-level model calls and gauntlet model dispatch still expose separate configuration/selection paths.

## LLM Notes

- Do not add a third provider-specific call path in a phase module; add it to the adapter boundary and normalize into `ModelResponse`.
- `models.py` sets LiteLLM log behavior at import (`models.py:16`); import-time environment side effects are part of the current runtime contract.
