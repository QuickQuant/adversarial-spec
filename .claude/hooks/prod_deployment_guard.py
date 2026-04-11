#!/usr/bin/env python3
"""
Hook: prod_deployment_guard
Purpose: Warns before running commands that affect production deployments

Owner: Claude (Opus 4.5)
Created: 2026-01-29
Source: Adapted from prediction-prime implementation

Catches:
- `npx convex deploy` (always deploys to prod)
- `npx convex run --prod` (runs function on prod)
- Any convex command with --prod flag

Safe alternatives suggested:
- `npx convex dev --once` for dev deployment
- `--deployment-name dev` for explicit dev targeting

Hook Type: PreToolUse
Matcher: Bash
Exit Codes:
- 0: Command is safe, proceed
- 1: Warning issued, ask for confirmation
- 2: Hard block (not used by this hook)
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
MODE = CONFIG.get("per_hook_overrides", {}).get("prod_deployment_guard_mode") or CONFIG.get("mode", "flexible")

# -----------------------------------------------------------------------------
# FLEXIBLE MODE: Warn but allow after confirmation (exit 1)
# STRICT MODE: Block entirely (exit 2)
# -----------------------------------------------------------------------------

# Patterns that indicate prod operations
PROD_PATTERNS = [
    # convex deploy always goes to prod
    (r"npx\s+convex\s+deploy\b", "npx convex deploy ALWAYS deploys to production"),

    # explicit --prod flag
    (r"convex\s+.*--prod\b", "The --prod flag runs against production"),

    # convex deploy with any flags
    (r"convex\s+deploy\b", "convex deploy targets production deployment"),
]

# Patterns that are OK (explicitly dev operations)
ALLOWED_PATTERNS = [
    r"convex\s+dev\b",           # npx convex dev is fine
    r"--deployment-name\s+dev",  # explicit dev deployment
]

# =============================================================================
# HOOK LOGIC
# =============================================================================

def is_allowed(command: str) -> bool:
    """Check if command is explicitly a dev operation."""
    for pattern in ALLOWED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True
    return False

def check_command(command: str) -> tuple[str, str] | None:
    """
    Check command for prod operations.
    Returns (pattern_matched, message) or None if OK.
    """
    if is_allowed(command):
        return None

    for pattern, message in PROD_PATTERNS:
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

        # Only check lines with convex commands
        if not re.search(r'\bconvex\b', line, re.IGNORECASE):
            continue

        result = check_command(line)
        if result:
            violations.append((line[:100], result[1]))

    if violations:
        # Output warning and require confirmation
        print("", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print("  PRODUCTION DEPLOYMENT DETECTED", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print("", file=sys.stderr)

        for cmd, message in violations:
            print(f"  Command: {cmd}", file=sys.stderr)
            print(f"  Warning: {message}", file=sys.stderr)
            print("", file=sys.stderr)

        if MODE == "strict":
            print("BLOCKED: Production deployment not allowed in strict mode.", file=sys.stderr)
            print("", file=sys.stderr)
            print("Use 'npx convex dev --once' to push to dev instead.", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            sys.exit(2)  # Hard block
        else:
            print("Are you sure you want to run this against PRODUCTION?", file=sys.stderr)
            print("", file=sys.stderr)
            print("Use 'npx convex dev --once' to push to dev instead.", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            sys.exit(1)  # Warn, ask for confirmation

    sys.exit(0)

if __name__ == "__main__":
    main()
