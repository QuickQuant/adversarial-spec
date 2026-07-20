# Component: Providers and Model Configuration

> Derived from: `skills/adversarial-spec/scripts/providers.py`, `MODEL_REFERENCE.md`, `pyproject.toml` | Verified at: `ef18c66`
> If any derived-from file changed since `ef18c66`, trust source over this doc.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Model constants, costs, provider availability, profiles, Bedrock config |
| Entry | `load_global_config()` at `providers.py:125` |
| Key files | `providers.py`, `pyproject.toml`, user config/profile paths |
| Depends on | environment, pathlib/JSON, CLI discovery |
| Used by | Models, Debate Engine, Gauntlet dispatch, Token Tracking |
| Runtime status | implemented |
| Architecture status | active_primary |

## What This Component Does

Providers is the configuration authority for model names, cost rates, CLI availability, API-key presence, named profiles, and Bedrock resolution. It reports presence/availability rather than exposing credential values.

## Contracts

### Type Contracts

| Contract | Purpose | Owner | Consumed By |
|---|---|---|---|
| `MODEL_COSTS` | per-model input/output rates | `providers.py:26-69` | token tracker/reporting |
| profile mapping | named provider/model configuration | `providers.py:225-250` | debate CLI |
| available provider tuple | provider/key/model status | `providers.py:413-451` | CLI info/validation |

### Configuration Boundary

| Field/source | Emitted | Adapter forwards | Consumer accepts | Persist | Absent means | Authority | Evidence | Verified |
|---|---|---|---|---|---|---|---|---|
| provider API-key env var | conditional | key presence only | credential validator | never value | provider unavailable; no secret value should be logged | environment/provider module | `providers.py:16,299-340,481-569` | verified |
| global config JSON | conditional | parsed mapping | config/profile functions | user config file | defaults apply; malformed JSON is a config error | `providers.py:22-25,125-142` | verified |
| named profile JSON | conditional | parsed mapping | `load_profile`/debate | profile file | no profile selected/available | `providers.py:225-250` | verified |

## Invariants

- Cost lookup falls back to `DEFAULT_COST` when a model has no explicit rate (`providers.py:26-69`).
- Credential validation returns available/missing model lists; it does not mint or expose keys (`providers.py:481-569`).
- Bedrock resolution is explicit and validates configured model/region before use (`providers.py:142-225`).

## Data Flow

```text
IN: env + global config + profile + CLI model names
    └─> load/validate/resolve (providers.py:125-284,481-571)
PROCESS: availability -> credentials -> provider/model selection -> cost lookup
OUT: model routes, config, availability status
    └─> models.py and debate.py
```

## Key Functions

| Function | Purpose | Location |
|---|---|---|
| `load_global_config()` / `save_global_config()` | user global config | `providers.py:125-142` |
| `load_profile()` / `save_profile()` | named profile storage | `providers.py:225-250` |
| `get_available_providers()` | provider/key/CLI status | `providers.py:413` |
| `get_default_model()` | choose default configured model | `providers.py:457` |
| `validate_model_credentials()` | separate available/missing models | `providers.py:481` |
| `handle_bedrock_command()` | Bedrock CLI operations | `providers.py:571` |

## Error Handling

- Malformed global/profile JSON is surfaced to callers; no silent replacement of user config (`providers.py:125-250`).
- Missing credentials are represented as unavailable models, not subprocess failures (`providers.py:481-569`).

## Concurrency Concerns

| Resource | Callers | Synchronization | Risk |
|---|---|---|---|
| HAZ-003: global/profile config files | CLI config commands, profile save, and model reads | no FileLock or atomic replacement in `providers.py:125-250` | concurrent save/read can expose partial JSON; single-user CLI is assumed |

## Configuration

| Config | Source | Default | Precedence |
|---|---|---|---|
| model constants/costs | module tables | code defaults | explicit model entry, then `DEFAULT_COST` |
| credentials | environment | missing | env presence controls availability |
| global config | `~/.claude/adversarial-spec/config.json` | `{}` | selected profile/CLI flags override |
| profiles | `~/.config/adversarial-spec/profiles/` | none | explicit profile overrides global/default |

## Integration Points

**Calls out to:** filesystem and `shutil.which` for CLI availability.

**Called by:** `models.py`, `debate.py`, `gauntlet/model_dispatch.py`, `token_tracking.py`.

## Active vs Target

- **Active consumers:** all model routing paths.
- **Legacy consumers:** documentation may refer to older provider lists.
- **Target architecture:** one registry/config authority consumed by all model dispatch paths.
- **Drift note:** top-level model routing and gauntlet model dispatch have independent selection helpers.

## LLM Notes

- Record only environment variable names in architecture docs; credential values are intentionally outside the corpus.
