#!/usr/bin/env python3
"""
Hook: deprecated_models
Practice: Model Hygiene - Block deprecated AI model usage
Version: 1.0.0

Blocks attempts to use deprecated AI models that are no longer available or
have been superseded by better alternatives.

Hook Type: PreToolUse
Matcher: Bash
"""

import sys
import json
import re
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

def load_config():
    config_path = Path(__file__).parent / "hook_config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {"mode": "flexible"}

CONFIG = load_config()
MODE = CONFIG.get("deprecated_models_mode", CONFIG.get("mode", "flexible"))

# -----------------------------------------------------------------------------
# DEPRECATED MODELS - These are no longer available or have better alternatives
# -----------------------------------------------------------------------------

DEPRECATED_MODELS = {
    # OpenAI legacy models - replaced by gpt-5.x series
    "gpt-4o": "Use codex/gpt-5.2-codex-medium (free with ChatGPT subscription) or claude-sonnet-4-5",
    "gpt-4o-mini": "Use codex/gpt-5.2-codex-medium (free) or gemini-cli/gemini-3-flash-preview (free)",
    "gpt-4-turbo": "Use codex/gpt-5.2-codex (free with ChatGPT subscription)",
    "gpt-4": "Use codex/gpt-5.2-codex (free with ChatGPT subscription)",
    "gpt-3.5-turbo": "Use gemini-cli/gemini-3-flash-preview (free) or groq/llama-3.3-70b-versatile",
    "o3-mini": "Use codex/gpt-5.2-codex-medium (free with ChatGPT subscription)",

    # Old Gemini models
    "gemini-pro": "Use gemini/gemini-3-pro or gemini-cli/gemini-3-pro-preview (free)",
    "gemini-1.5-pro": "Use gemini/gemini-3-pro or gemini-cli/gemini-3-pro-preview (free)",
    "gemini-1.5-flash": "Use gemini/gemini-3-flash or gemini-cli/gemini-3-flash-preview (free)",

    # Old Claude models
    "claude-3-opus": "Use claude-opus-4-5-20250514",
    "claude-3-sonnet": "Use claude-sonnet-4-5-20250929",
    "claude-3-haiku": "Use claude-haiku-3-5-20250929",
}

# Patterns to match model specifications in commands
MODEL_PATTERNS = [
    r"--model[s]?\s+['\"]?(\S+)['\"]?",
    r"--adversary-model\s+['\"]?(\S+)['\"]?",
    r"--eval-model\s+['\"]?(\S+)['\"]?",
    r"-m\s+['\"]?(\S+)['\"]?",  # Common short flag
]

# =============================================================================
# HOOK LOGIC
# =============================================================================

def extract_models(command: str) -> list[str]:
    """Extract model names from command."""
    models = []
    for pattern in MODEL_PATTERNS:
        matches = re.findall(pattern, command, re.IGNORECASE)
        for match in matches:
            # Handle comma-separated model lists
            models.extend(m.strip() for m in match.split(','))
    return models

def check_deprecated_models(command: str) -> list[tuple[str, str]]:
    """
    Check command for deprecated model usage.
    Returns list of (deprecated_model, suggestion) tuples.
    """
    violations = []
    models = extract_models(command)

    for model in models:
        # Check exact match
        if model in DEPRECATED_MODELS:
            violations.append((model, DEPRECATED_MODELS[model]))
            continue

        # Check partial match (e.g., "openai/gpt-4o" or "openrouter/openai/gpt-4o")
        model_base = model.split('/')[-1]
        if model_base in DEPRECATED_MODELS:
            violations.append((model, DEPRECATED_MODELS[model_base]))

    return violations

def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    if not command:
        sys.exit(0)

    # Only check commands that look like they're running debate.py or model-related scripts
    if not re.search(r'(debate\.py|gauntlet\.py|--model|adversarial)', command, re.IGNORECASE):
        sys.exit(0)

    violations = check_deprecated_models(command)

    if violations:
        print("🚫 DEPRECATED MODEL DETECTED - BLOCKED", file=sys.stderr)
        print("", file=sys.stderr)
        print("The following models are deprecated and no longer available:", file=sys.stderr)
        print("", file=sys.stderr)

        for model, suggestion in violations:
            print(f"  ❌ {model}", file=sys.stderr)
            print(f"     → {suggestion}", file=sys.stderr)
            print("", file=sys.stderr)

        print("Update your command to use a supported model.", file=sys.stderr)
        print("", file=sys.stderr)
        print("Free options with no API cost:", file=sys.stderr)
        print("  • codex/gpt-5.2-codex (requires ChatGPT subscription + npm install -g @openai/codex)", file=sys.stderr)
        print("  • gemini-cli/gemini-3-pro-preview (requires Google account + install gemini CLI)", file=sys.stderr)

        sys.exit(2)  # Block the command

    sys.exit(0)

if __name__ == "__main__":
    main()
