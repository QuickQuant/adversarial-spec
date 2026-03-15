#!/usr/bin/env python3
"""
Hook: force_flag_defense
Practice: N/A - Meta-safety for --force operations
Version: 1.0.0

Requires explicit defense before using --force flags. Claude must list
every individual item that will be affected by the force operation.

The defense must appear in the command's description field as a single
concise line per affected item, e.g.:
  "Force sync: overwrites banned_git_commands.py (v1.0.0→v1.0.0, no changes),
   adds codex-timeout-guard.py (new), adds deprecated_models.py (new)"

Exception: Skip if description mentions explicit version numbers that Claude
already incremented in the current session.

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
MODE = CONFIG.get("force_flag_defense_mode", CONFIG.get("mode", "flexible"))

# Commands that commonly use --force and need defense
FORCE_PATTERNS = [
    r"--force\b",
    r"\s-f\b(?!\s*['\"])",  # -f flag but not -f "filename"
    r"--force-with-lease",
]

# Patterns in description that indicate valid defense
DEFENSE_INDICATORS = [
    r"overwrit(e|es|ing)\s+\S+",      # "overwrites file.py"
    r"replac(e|es|ing)\s+\S+",        # "replaces config.json"
    r"delet(e|es|ing)\s+\S+",         # "deletes old.txt"
    r"add(s|ing)?\s+\S+",             # "adds new.py"
    r"updat(e|es|ing)\s+\S+",         # "updates hook.py"
    r"reset(s|ting)?\s+\S+",          # "resets branch"
    r"v\d+\.\d+(\.\d+)?",             # version numbers like v1.0.0
    r"\d+\.\d+(\.\d+)?\s*→\s*\d+",    # version transitions 1.0→1.1
    r"no\s+changes",                   # explicit "no changes"
    r"\(new\)",                        # marking new items
]

# Commands where -f means something else (not force)
FALSE_POSITIVE_COMMANDS = [
    r"grep\s+-[a-zA-Z]*f",            # grep -f (pattern file)
    r"tar\s+-[a-zA-Z]*f",             # tar -f (archive file)
    r"ssh\s+-[a-zA-Z]*f",             # ssh -f (background)
    r"tail\s+-[a-zA-Z]*f",            # tail -f (follow)
    r"cut\s+-[a-zA-Z]*f",             # cut -f (field)
    r"sort\s+-[a-zA-Z]*f",            # sort -f (fold case)
    r"test\s+-f\b",                    # test -f (file exists check)
    r"\[\s+-f\b",                      # [ -f (file exists check)
    r"\[\[\s+-f\b",                    # [[ -f (file exists check)
]

# =============================================================================
# DETECTION LOGIC
# =============================================================================

def has_force_flag(command: str) -> bool:
    """Check if command contains a --force or -f flag."""
    # First check for false positives
    for pattern in FALSE_POSITIVE_COMMANDS:
        if re.search(pattern, command, re.IGNORECASE):
            return False

    # Check for force patterns
    for pattern in FORCE_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True
    return False

def has_adequate_defense(description: str) -> bool:
    """
    Check if description contains adequate defense for the force operation.

    A good defense:
    - Lists specific items being affected
    - Mentions version numbers or "no changes" for overwrites
    - Explicitly marks new additions
    """
    if not description:
        return False

    # Count how many defense indicators are present
    defense_count = 0
    for pattern in DEFENSE_INDICATORS:
        if re.search(pattern, description, re.IGNORECASE):
            defense_count += 1

    # Require at least 2 indicators for a valid defense
    # (e.g., "overwrites X" + version number, or "adds Y" + "(new)")
    return defense_count >= 2

def extract_force_context(command: str) -> str:
    """Extract what the force is being applied to."""
    # Common patterns
    if "sync" in command.lower():
        return "sync operation"
    if "push" in command.lower():
        return "git push"
    if "reset" in command.lower():
        return "git reset"
    if "rm" in command.lower() or "remove" in command.lower():
        return "removal"
    if "cp" in command.lower() or "copy" in command.lower():
        return "copy/overwrite"
    if "install" in command.lower():
        return "install"
    return "operation"

# =============================================================================
# MAIN
# =============================================================================

def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")
    description = tool_input.get("description", "")

    if not command:
        sys.exit(0)

    # Check for force flag
    if not has_force_flag(command):
        sys.exit(0)

    # Check if there's adequate defense in the description
    if has_adequate_defense(description):
        sys.exit(0)

    # Block and require defense
    context = extract_force_context(command)

    print("🛡️ FORCE FLAG DEFENSE REQUIRED", file=sys.stderr)
    print("", file=sys.stderr)
    print(f"Command uses --force for: {context}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Before using --force, add a description that lists:", file=sys.stderr)
    print("  • Every individual item that will be affected", file=sys.stderr)
    print("  • For overwrites: version info or 'no changes'", file=sys.stderr)
    print("  • For new items: mark with '(new)'", file=sys.stderr)
    print("", file=sys.stderr)
    print("Example description:", file=sys.stderr)
    print('  "Force sync: overwrites hook.py (v1.0→v1.1), adds new.py (new)"', file=sys.stderr)
    print("", file=sys.stderr)
    print("Exception: Skip this check if you've already verified each item", file=sys.stderr)
    print("or explicitly incremented version numbers in this session.", file=sys.stderr)

    sys.exit(2)  # Block

if __name__ == "__main__":
    main()
