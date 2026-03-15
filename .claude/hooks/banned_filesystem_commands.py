#!/usr/bin/env python3
"""
Hook: banned_filesystem_commands
Practice: Section 12 - Filesystem Safety
Version: flexible=1.0.0, strict=1.0.0
Hash: See practices_registry.json

Tiered enforcement for file deletion commands:
- ALWAYS BLOCKED: Recursive, wildcard, bulk operations
- MODE DEPENDENT: Single file deletion (warn in flexible, block in strict)
- ALLOWED: rm -i (interactive), rmdir (empty dirs only)

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
MODE = CONFIG.get("banned_filesystem_commands_mode", CONFIG.get("mode", "flexible"))

# -----------------------------------------------------------------------------
# ALWAYS BLOCKED - Recursive, wildcard, or bulk operations
# -----------------------------------------------------------------------------

ALWAYS_BLOCKED = [
    # Recursive deletion
    (r"\brm\s+.*-[rR]\b", "Recursive deletion blocked - use rmdir for empty dirs or ask user"),
    (r"\brm\s+.*-rf\b", "Recursive force deletion blocked - ask user to run manually"),
    (r"\brm\s+.*-fr\b", "Recursive force deletion blocked - ask user to run manually"),

    # Wildcards in rm
    (r"\brm\s+[^|]*[*?]", "Wildcard deletion blocked - be explicit about files to delete"),

    # Find with delete
    (r"\bfind\b.*-delete\b", "find -delete blocked - too dangerous, ask user"),
    (r"\bfind\b.*-exec\s+rm\b", "find -exec rm blocked - too dangerous, ask user"),

    # Loop deletion
    (r"\bfor\b.*\brm\b", "Loop deletion blocked - be explicit about files"),
    (r"\bwhile\b.*\brm\b", "Loop deletion blocked - be explicit about files"),

    # Dangerous parent directory removal
    (r"\brmdir\s+.*(-p|--parents)\b", "rmdir -p blocked - removes parent directories"),

    # Dangerous paths
    (r"\brm\s+.*\s+/\s*$", "Deleting / is blocked"),
    (r"\brm\s+.*\s+/[^/\s]*\s*$", "Deleting top-level directories blocked"),
    (r"\brm\s+.*~/", "Deleting from home directory blocked - be explicit"),
    (r"\brm\s+.*\$HOME", "Deleting from $HOME blocked - be explicit"),
]

# -----------------------------------------------------------------------------
# MODE DEPENDENT - Single file deletion
# -----------------------------------------------------------------------------

SINGLE_FILE_PATTERNS = [
    (r"\brm\s+(?!-[rRi])[^|*?]*\.\w+\s*$", "Single file deletion"),
    (r"\brm\s+-f\s+(?!-[rR])[^|*?]*\.\w+\s*$", "Force single file deletion"),
]

# -----------------------------------------------------------------------------
# ALLOWED - Always OK
# -----------------------------------------------------------------------------

ALLOWED_PATTERNS = [
    r"\brm\s+-i\b",      # Interactive mode
    r"\brmdir\s+(?!-p)", # rmdir without -p (empty dirs only)
]

# =============================================================================
# HOOK LOGIC
# =============================================================================

def is_allowed(command: str) -> bool:
    """Check if command matches an allowed pattern."""
    for pattern in ALLOWED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True
    return False

def check_command(command: str) -> tuple[str, str, str] | None:
    """
    Check command against patterns.
    Returns (pattern_matched, message, severity) or None if OK.
    severity: "always_block" | "mode_dependent"
    """
    if is_allowed(command):
        return None

    # Check always-blocked patterns first
    for pattern, message in ALWAYS_BLOCKED:
        if re.search(pattern, command, re.IGNORECASE):
            return (pattern, message, "always_block")

    # Check single-file patterns (mode dependent)
    for pattern, message in SINGLE_FILE_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return (pattern, message, "mode_dependent")

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

    # Check each line of the command
    violations = []
    for line in command.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # Only check lines with rm, rmdir, or find
        if not re.search(r'\b(rm|rmdir|find)\b', line, re.IGNORECASE):
            continue

        result = check_command(line)
        if result:
            violations.append((line[:80], result[1], result[2]))

    if not violations:
        sys.exit(0)

    # Determine exit behavior
    has_always_block = any(v[2] == "always_block" for v in violations)
    has_mode_dependent = any(v[2] == "mode_dependent" for v in violations)

    if has_always_block:
        # Always block recursive/wildcard/bulk operations
        print(f"🛑 DANGEROUS FILESYSTEM COMMAND - BLOCKED", file=sys.stderr)
        print("", file=sys.stderr)

        for cmd, message, severity in violations:
            if severity == "always_block":
                print(f"  ❌ {cmd}", file=sys.stderr)
                print(f"     → {message}", file=sys.stderr)
                print("", file=sys.stderr)

        print("Ask the user to run this command manually if needed.", file=sys.stderr)
        sys.exit(2)

    elif has_mode_dependent:
        if MODE == "strict":
            # Block in strict mode
            print(f"🛑 FILE DELETION - BLOCKED [STRICT MODE]", file=sys.stderr)
            print("", file=sys.stderr)

            for cmd, message, severity in violations:
                print(f"  ❌ {cmd}", file=sys.stderr)
                print(f"     → {message}", file=sys.stderr)
                print("", file=sys.stderr)

            print("In strict mode, all file deletions require user confirmation.", file=sys.stderr)
            sys.exit(2)
        else:
            # Warn in flexible mode
            print(f"⚠️ FILE DELETION - WARNING [FLEXIBLE MODE]", file=sys.stderr)
            print("", file=sys.stderr)

            for cmd, message, severity in violations:
                print(f"  ⚠️ {cmd}", file=sys.stderr)
                print(f"     → {message}", file=sys.stderr)
                print("", file=sys.stderr)

            print("Proceeding, but verify this is intentional.", file=sys.stderr)
            sys.exit(0)  # Warn only, don't block

    sys.exit(0)

if __name__ == "__main__":
    main()
