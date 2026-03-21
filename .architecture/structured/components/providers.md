# Component: Providers

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Model configuration, credentials, cost rates, Bedrock support |
| Entry | `validate_model_credentials()` at scripts/providers.py:436 |
| Key files | providers.py (683 lines) |
| Depends on | Prompts (FOCUS_AREAS, PERSONAS), standard library |
| Used by | Models, Debate Engine, Gauntlet |

## What This Component Does

Providers is the configuration hub for model management. It defines MODEL_COSTS (per-token rates for all supported models), handles credential validation against environment variables, manages saved profiles (model + focus + persona combos), implements Bedrock support (enable/disable, model resolution, region config), and exposes listing functions for providers, focus areas, and personas.

## Data Flow

```
IN:  model names, profile names, bedrock settings
     └─> validate_model_credentials(), load_profile(), etc.

PROCESS:
     ├─> Check env vars for API keys per provider
     ├─> Check shutil.which() for CLI tool availability
     ├─> Load/save profiles from ~/.config/adversarial-spec/profiles/
     ├─> Load/save global config from ~/.claude/adversarial-spec/config.json
     └─> Resolve Bedrock model IDs from friendly names

OUT: Validation results, profile data, config data
     └─> consumed by debate.py and models.py
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `validate_model_credentials()` | Check API keys/CLI tools for model list | providers.py:436 |
| `load_profile()` | Load saved profile | providers.py |
| `save_profile()` | Save profile to disk | providers.py |
| `list_providers()` | List available providers | providers.py |
| `list_focus_areas()` | List available focus areas (from prompts) | providers.py |
| `list_personas()` | List available personas (from prompts) | providers.py |
| `load_global_config()` | Read global JSON config | providers.py:95 |
| `save_global_config()` | Write global JSON config | providers.py:106 |
| `is_bedrock_enabled()` | Check Bedrock toggle | providers.py:112 |
| `resolve_bedrock_model()` | Map friendly name to Bedrock ID | providers.py:124 |
| `handle_bedrock_command()` | CLI bedrock subcommand handler | providers.py |

## Key Data

| Constant | Purpose |
|----------|---------|
| `MODEL_COSTS` | Dict mapping model names to {input, output} per-million-token rates | providers.py:18-47 |
| `PROFILES_DIR` | `~/.config/adversarial-spec/profiles/` |
| `GLOBAL_CONFIG_PATH` | `~/.claude/adversarial-spec/config.json` |
| `DEFAULT_CODEX_REASONING` | Default reasoning level for Codex CLI |
| `CODEX_AVAILABLE` | Boolean: is `codex` binary on PATH |
| `GEMINI_CLI_AVAILABLE` | Boolean: is `gemini` binary on PATH |
| `CLAUDE_CLI_AVAILABLE` | Boolean: is `claude` binary on PATH |

## Error Handling

- **Missing config file**: `load_global_config()` returns empty dict if file doesn't exist or JSON is invalid
- **Missing profiles dir**: Created on first save
- **Invalid Bedrock model**: Returns None from resolve, caller handles

## Integration Points

**Calls out to:**
- `prompts.FOCUS_AREAS` — for listing focus areas
- `prompts.PERSONAS` — for listing personas
- File system — config and profile JSON files
- Environment variables — API keys

**Called by:**
- `debate.py` — credential validation, profile loading, bedrock setup
- `models.py` — MODEL_COSTS for cost calculation
- `gauntlet/model_dispatch.py` — gauntlet model selection and credential-sensitive fallbacks

## LLM Notes

- When adding a new model, add its cost entry to `MODEL_COSTS` dict. CLI models (codex/, gemini-cli/, claude-cli/) use {input: 0, output: 0}.
- Provider detection is prefix-based: gpt- → OpenAI, claude- → Anthropic, gemini/ → Google, etc.
- CLI tool availability is checked once at import time via `shutil.which()`, not per-call.
- Bedrock support remaps model names with "bedrock/" prefix and sets AWS_REGION env var.
