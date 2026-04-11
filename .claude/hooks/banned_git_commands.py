#!/usr/bin/env python3
"""
Hook: banned_git_commands
Practice: Section 11 - Git Safety
Version: flexible=1.0.0, strict=1.0.0
Hash: See practices_registry.json

Blocks destructive git commands that can cause data loss or break shared branches.
This hook ALWAYS blocks regardless of mode - these are hard constraints.

Hook Type: PreToolUse
Matcher: Bash
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
MODE = CONFIG.get("banned_git_commands_mode", CONFIG.get("mode", "flexible"))

# -----------------------------------------------------------------------------
# ALWAYS BLOCKED - These commands are dangerous regardless of mode
# -----------------------------------------------------------------------------

ALWAYS_BLOCKED = [
    # Force push (overwrites remote history)
    (r"git\s+push\s+.*(-f|--force)\b", "Force push overwrites remote history - ask user to run manually"),
    (r"git\s+push\s+.*--force-with-lease\b", "Force-with-lease still overwrites history - ask user to run manually"),

    # Force delete branch (loses unmerged work)
    (r"git\s+branch\s+.*-D\b", "Force delete loses unmerged work - use -d or ask user"),

    # Hard reset (discards uncommitted changes)
    (r"git\s+reset\s+.*--hard\b", "Hard reset discards uncommitted changes - ask user to run manually"),

    # Clean with force (permanently deletes untracked files)
    (r"git\s+clean\s+.*-f\b", "git clean -f permanently deletes untracked files - ask user"),

    # Delete remote branch (affects all collaborators)
    (r"git\s+push\s+.*--delete\b", "Deleting remote branches affects all collaborators - ask user"),
    (r"git\s+push\s+\S+\s+:\S+", "Deleting remote branches affects all collaborators - ask user"),

    # Force checkout (discards local changes)
    (r"git\s+checkout\s+.*(-f|--force)\b", "Force checkout discards local changes - ask user"),

    # Rebase (rewrites history - requires explicit approval)
    (r"git\s+rebase\s+(?!--abort|--continue|--skip)", "Rebase rewrites history - requires explicit user approval"),

    # Filter-branch / filter-repo (rewrites entire history)
    (r"git\s+filter-branch\b", "filter-branch rewrites entire history - ask user"),
    (r"git\s+filter-repo\b", "filter-repo rewrites entire history - ask user"),

    # Reflog manipulation (loses recovery points)
    (r"git\s+reflog\s+(expire|delete)\b", "Reflog manipulation loses recovery points - ask user"),
]

# Patterns that are OK (recovery commands)
ALLOWED_PATTERNS = [
    r"git\s+rebase\s+--abort\b",
    r"git\s+rebase\s+--continue\b",
    r"git\s+rebase\s+--skip\b",
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

def check_command(command: str) -> tuple[str, str] | None:
    """
    Check command against banned patterns.
    Returns (pattern_matched, message) or None if OK.
    """
    if is_allowed(command):
        return None

    for pattern, message in ALWAYS_BLOCKED:
        if re.search(pattern, command, re.IGNORECASE):
            return (pattern, message)

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

        # Only check lines that look like git commands
        if not re.search(r'\bgit\b', line, re.IGNORECASE):
            continue

        result = check_command(line)
        if result:
            violations.append((line[:80], result[1]))

    if violations:
        # ALWAYS block - this is a hard constraint
        print("🛑 BANNED GIT COMMAND - BLOCKED", file=sys.stderr)
        print("", file=sys.stderr)
        print("These commands can cause irreversible data loss.", file=sys.stderr)
        print("", file=sys.stderr)

        for cmd, message in violations:
            print(f"  ❌ {cmd}", file=sys.stderr)
            print(f"     → {message}", file=sys.stderr)
            print("", file=sys.stderr)

        print("Ask the user to run this command manually if needed.", file=sys.stderr)

        # Always exit 2 (block) regardless of mode
        sys.exit(2)

    sys.exit(0)

if __name__ == "__main__":
    main()
