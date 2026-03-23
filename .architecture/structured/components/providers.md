# Component: Providers

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Model configuration, cost rates, Bedrock support, CLI availability |
| Entry | `providers.py` (module-level constants and functions) |
| Key files | providers.py |
| Depends on | Prompts |
| Used by | Models, Debate Engine, Gauntlet model_dispatch |
| Runtime status | implemented |
| Architecture status | active_primary |

## What This Component Does

Providers manages model configuration and cost metadata. `MODEL_COSTS` is a static lookup table mapping model names to input/output per-token costs. CLI availability flags (`CODEX_AVAILABLE`, `GEMINI_CLI_AVAILABLE`, `CLAUDE_CLI_AVAILABLE`) are set at import time by checking for CLI binaries. Bedrock configuration is loaded from `~/.claude/adversarial-spec/config.json`.

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `MODEL_COSTS` | Static cost-per-token lookup table | providers.py |
| `load_global_config()` | Load Bedrock config from ~/.claude/ | providers.py |
| `CODEX_AVAILABLE` | Check if codex CLI exists | providers.py |
| `GEMINI_CLI_AVAILABLE` | Check if gemini-cli exists | providers.py |
| `CLAUDE_CLI_AVAILABLE` | Check if claude CLI exists | providers.py |

## Contracts

### Type Contracts

| Contract | Purpose | Owner | Consumed By |
|----------|---------|-------|-------------|
| `MODEL_COSTS` | Per-token pricing dict | providers.py | models.py (cost_tracker) |

## Configuration

| Config | Source | Default |
|--------|--------|---------|
| Bedrock enabled | `~/.claude/adversarial-spec/config.json` | false |
| AWS credentials | `AWS_ACCESS_KEY_ID`, `AWS_PROFILE`, `AWS_ROLE_ARN` env vars | none |

## LLM Notes

- `MODEL_COSTS` must be updated manually when adding new models or prices change. This is a common mistake.
- CLI availability is checked at import time, not lazily. If CLIs are installed after import, they won't be detected.
