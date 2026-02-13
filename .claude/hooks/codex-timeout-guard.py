#!/usr/bin/env python3
"""
Hook: Codex Timeout Guard

Owner: Claude (Opus 4.5)
Created: 2026-01-29

Prevents dispatching codex commands with insufficient timeout.
Codex with xhigh reasoning needs at least 15 minutes for light work,
30 minutes for heavier work.

Exit codes:
  0 = Allow
  2 = Block with error message

Note: This hook ALWAYS blocks regardless of mode - insufficient timeout
means the command will fail anyway, so blocking prevents wasted API calls.
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
# Note: This hook always blocks - mode is read for consistency but not used
# because insufficient timeout = guaranteed failure
MODE = CONFIG.get("per_hook_overrides", {}).get("codex_timeout_guard_mode") or CONFIG.get("mode", "flexible")

# =============================================================================
# HOOK LOGIC
# =============================================================================

def main():
    # Read hook input from stdin
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # Can't parse input, allow by default
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")

    # Only check commands that involve codex
    if "codex/" not in command and "codex-reasoning" not in command:
        sys.exit(0)

    # Check for --timeout flag
    timeout_match = re.search(r"--timeout\s+(\d+)", command)

    if timeout_match:
        timeout_seconds = int(timeout_match.group(1))

        # Determine minimum based on reasoning level
        if "xhigh" in command:
            min_timeout = 1800  # 30 minutes for xhigh
            level = "xhigh"
        elif "high" in command:
            min_timeout = 1200  # 20 minutes for high
            level = "high"
        else:
            min_timeout = 900  # 15 minutes for light work
            level = "default"

        if timeout_seconds < min_timeout:
            # Output error message and block
            print(
                json.dumps(
                    {
                        "decision": "block",
                        "reason": f"BLOCKED: Codex ({level}) requires --timeout {min_timeout} or higher (got {timeout_seconds}). "
                        f"Use --timeout {min_timeout} (or {min_timeout // 60} minutes) minimum.",
                    }
                )
            )
            sys.exit(2)

    # Also check the Bash tool's timeout parameter (in milliseconds)
    bash_timeout = tool_input.get("timeout")
    if bash_timeout is not None:
        timeout_ms = int(bash_timeout)

        if "xhigh" in command:
            min_timeout_ms = 1800000  # 30 minutes
            level = "xhigh"
        elif "high" in command:
            min_timeout_ms = 1200000  # 20 minutes
            level = "high"
        else:
            min_timeout_ms = 900000  # 15 minutes
            level = "default"

        if timeout_ms < min_timeout_ms:
            print(
                json.dumps(
                    {
                        "decision": "block",
                        "reason": f"BLOCKED: Codex ({level}) Bash timeout too short ({timeout_ms}ms). "
                        f"Use timeout={min_timeout_ms} ({min_timeout_ms // 60000} minutes) minimum.",
                    }
                )
            )
            sys.exit(2)

    # Allow the command
    sys.exit(0)


if __name__ == "__main__":
    main()
