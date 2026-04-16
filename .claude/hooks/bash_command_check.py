#!/usr/bin/env python3
"""
Hook: bash_command_check
Practice: Section 2b - Environment and Tooling + Section 12 (Debugging Order)
Version: flexible=1.0.0, strict=1.0.0
Hash: See practices_registry.json

Checks Bash commands BEFORE execution for:
1. Direct python calls (should use uv run)
2. Dangerous operations
3. Other project-specific command patterns

Runs on PreToolUse for Bash operations.
"""

import json
import re
import sys
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
MODE = CONFIG.get("bash_command_check_mode", CONFIG.get("mode", "flexible"))

# -----------------------------------------------------------------------------
# Command patterns to check
# -----------------------------------------------------------------------------

BLOCKED_PATTERNS_FLEXIBLE = [
    # Python without uv
    (r"^python\s+\S+\.py", "Use 'uv run python script.py' instead", "block"),
    (r"^python3\s+\S+\.py", "Use 'uv run python script.py' instead", "block"),
    (r"^pip\s+install\b", "Use 'uv add <package>' instead", "warn"),
]

# -----------------------------------------------------------------------------
# Wasteful truncation patterns - expensive operations piped to head/tail
# -----------------------------------------------------------------------------

TRUNCATION_WASTE_PATTERNS = [
    # === Hard block: any .py invocation combined with head/tail ===
    # Python script output is unknown-length by definition. Never truncate it;
    # route to a file and inspect with Read.
    (r"\.py\b[^\n]*\|\s*(?:[^|\n]+\|\s*)*(?:head|tail)\b",
     "BLOCKED: .py output has unknown length. Never pipe Python output to "
     "head/tail — redirect to a file and use the Read tool, or run with a "
     "narrower test/filter selector so the raw output is already small.",
     "block"),
    # Require head/tail to be in command-position (after |, ;, &&, ||, or at start
    # of the command string). This prevents false-matching git refs like HEAD in:
    #   git diff --stat HEAD -- file.py
    #   git log --oneline SHA..HEAD -- file.py
    # which are NOT truncation operations. `[^\n|;]*` accepts any flags/args
    # (including `-n 5` style split-flag-value) up to the .py filename.
    (r"(?:^|[|;]|&&|\|\|)\s*(?:head|tail)\b[^\n|;]*\.py\b",
     "BLOCKED: Don't read .py files with head/tail — use the Read tool.",
     "block"),

    # === Warn on any other head/tail usage ===
    # Warns in flexible mode (stderr only, no block). The point is to force
    # Claude to acknowledge the cutoff before using it.
    (r"\|\s*(?:head|tail)\b",
     "WARN: Piping to head/tail truncates output. If the upstream command is "
     "expensive or has unpredictable length, redirect to a file and inspect "
     "with Read. Only use head/tail when the cutoff is justified (e.g. "
     "known-bounded output, tail -f on a log).",
     "warn"),
    (r"(?:^|\s|;|&&|\|\|)\s*(?:head|tail)\s+(?:-\S+\s+)*[^\s|;&]+",
     "WARN: head/tail on a file is usually the wrong tool — use Read for "
     "files of known path. Only acceptable for follow-mode (`tail -f`) or "
     "known-bounded files.",
     "warn"),

    # === Existing specific patterns (kept) ===
    # Multi-model debate operations truncated
    (r"debate\.py.*--models.*\|.*head\s+-?\d+",
     "Wasteful: multi-model debate truncated by head. Remove '| head' or use --depth shallow", "block"),
    (r"debate\.py.*--depth\s+full.*\|.*head\s+-?\d+",
     "Wasteful: full-depth debate truncated by head. Remove '| head' or use --depth shallow", "block"),

    # Heavy API operations truncated
    (r"(curl|wget).*\|.*head\s+-?\d+\s*$",
     "Potentially wasteful: API call truncated. Fetch only what you need or use full output", "warn"),

    # Long-running analysis truncated
    (r"--depth\s+full.*\|.*head\s+-?\d+",
     "Wasteful: full-depth analysis truncated by head", "warn"),
    (r"critique.*--models.*,.*\|.*head",
     "Wasteful: multi-model critique truncated. Use full output or fewer models", "block"),
]

BLOCKED_PATTERNS_STRICT = BLOCKED_PATTERNS_FLEXIBLE + [
    # More aggressive python checks
    (r"^python\s+-m\s+", "Use 'uv run python -m <module>' instead", "block"),
    (r"^pip\s+", "Use uv equivalents for all pip commands", "block"),

    # Dangerous operations (warn in flexible, block in strict)
    (r"rm\s+-rf\s+/", "Dangerous: recursive delete from root", "block"),
    (r"rm\s+-rf\s+~", "Dangerous: recursive delete from home", "block"),
    (r">\s*/dev/sd", "Dangerous: writing directly to disk device", "block"),

    # Git operations that might need review
    (r"git\s+push\s+--force", "Force push requires confirmation", "warn"),
    (r"git\s+reset\s+--hard", "Hard reset requires confirmation", "warn"),
]

# Commands that are always OK (bypass checks)
ALLOWED_PATTERNS = [
    r"^uv\s+",
    r"^uvx\s+",
    r"^cd\s+",
    r"^ls\b",
    r"^cat\b",
    r"^echo\b",
    r"^grep\b",
    r"^find\b",
    r"^which\b",
    r"^pwd\b",
    r"^mkdir\b",
    r"^volta\s+run",
    # Skill scripts manage their own dependencies — NOT part of the project's uv env.
    # Wrapping these with `uv run` would use the wrong venv and break imports.
    r"^python3?\s+~/\.claude/skills/",
    r"^python3?\s+/home/\S+/\.claude/skills/",
    r"^python3?\s+~/\.codex/skills/",
    r"^python3?\s+/home/\S+/\.codex/skills/",
]

EXIT_BEHAVIOR = {
    "flexible": {"block": 2, "warn": 0},
    "strict": {"block": 2, "warn": 2},  # In strict, warnings also block
}

# =============================================================================
# HOOK LOGIC
# =============================================================================

def get_blocked_patterns():
    if MODE == "strict":
        return BLOCKED_PATTERNS_STRICT
    return BLOCKED_PATTERNS_FLEXIBLE

def is_allowed(command: str) -> bool:
    """Check if command matches allowed patterns."""
    for pattern in ALLOWED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True
    return False

def check_command(command: str) -> tuple[str, str, str] | None:
    """
    Check command against blocked patterns.
    Returns (pattern_matched, message, severity) or None if OK.
    """
    if is_allowed(command):
        return None

    patterns = get_blocked_patterns()

    for pattern, message, severity in patterns:
        if re.search(pattern, command, re.IGNORECASE | re.MULTILINE):
            return (pattern, message, severity)

    return None

def check_truncation_waste(command: str) -> tuple[str, str, str] | None:
    """
    Check for wasteful patterns: expensive operations piped to head/tail.
    These checks run on the FULL command (not line-by-line) to catch pipes.
    """
    for pattern, message, severity in TRUNCATION_WASTE_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return (pattern, message, severity)
    return None

def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    if not command:
        sys.exit(0)

    # Check each line of the command (for multi-line commands)
    violations = []
    for line in command.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        result = check_command(line)
        if result:
            violations.append((line[:60], result[1], result[2]))

    # Check full command for truncation waste (pipe patterns span the full command)
    truncation_result = check_truncation_waste(command)
    if truncation_result:
        violations.append((command[:60] + "...", truncation_result[1], truncation_result[2]))

    if violations:
        # Determine overall severity
        severities = [v[2] for v in violations]
        overall_severity = "block" if "block" in severities else "warn"

        behavior = EXIT_BEHAVIOR[MODE]
        exit_code = behavior[overall_severity]

        action = "BLOCKING" if exit_code == 2 else "WARNING"
        print(f"⚠️ COMMAND CHECK [{MODE.upper()} MODE] - {action}", file=sys.stderr)
        print("", file=sys.stderr)

        for cmd, message, severity in violations:
            icon = "🛑" if severity == "block" else "⚠️"
            print(f"  {icon} {cmd}", file=sys.stderr)
            print(f"     → {message}", file=sys.stderr)
            print("", file=sys.stderr)

        if exit_code == 2:
            print("Revise the command before proceeding.", file=sys.stderr)

        sys.exit(exit_code)

    sys.exit(0)

if __name__ == "__main__":
    main()
