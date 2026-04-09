#!/usr/bin/env python3
"""
Hook: pip_install_block
Practice: Supply Chain Safety - Block all pip install commands
Version: flexible=1.0.0, strict=1.0.0

ALWAYS BLOCKS regardless of mode - pip supply chain attack safeguard.
Blocks: pip install, pip3 install, python -m pip install, pip download, pipx install

Hook Type: PreToolUse
Matcher: Bash
"""

import sys
import json
import re

# Patterns that indicate pip package installation
PIP_PATTERNS = [
    # Direct pip install
    (r"\bpip3?\s+install\b", "pip install blocked - supply chain attack safeguard"),
    # python -m pip install
    (r"\bpython3?\s+-m\s+pip\s+install\b", "python -m pip install blocked - supply chain attack safeguard"),
    # pip download (fetches packages)
    (r"\bpip3?\s+download\b", "pip download blocked - supply chain attack safeguard"),
    # python -m pip download
    (r"\bpython3?\s+-m\s+pip\s+download\b", "python -m pip download blocked - supply chain attack safeguard"),
    # pipx install
    (r"\bpipx\s+install\b", "pipx install blocked - supply chain attack safeguard"),
    # pip wheel (builds from PyPI)
    (r"\bpip3?\s+wheel\b", "pip wheel blocked - supply chain attack safeguard"),
]


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    if not command:
        sys.exit(0)

    violations = []
    for line in command.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        for pattern, message in PIP_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                violations.append((line[:80], message))
                break

    if not violations:
        sys.exit(0)

    print("BLOCKED: pip supply chain attack safeguard", file=sys.stderr)
    print("", file=sys.stderr)
    for cmd, message in violations:
        print(f"  {cmd}", file=sys.stderr)
        print(f"     {message}", file=sys.stderr)
        print("", file=sys.stderr)
    print("Use 'uv add <package>' or 'uv pip install' instead.", file=sys.stderr)
    print("If you must use pip, ask the user to run the command manually.", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
