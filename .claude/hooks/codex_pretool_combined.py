#!/usr/bin/env python3
"""
Combined PreToolUse hook for Codex CLI.

Runs all safety checks (banned git commands, banned filesystem commands,
force flag defense, pip install block) in a single hook invocation to
avoid spamming Codex's UI with 4 separate status messages per Bash call.

Each sub-hook is imported and run in sequence. First violation wins.
"""
import importlib.util
import json
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).parent

SUB_HOOKS = [
    "banned_git_commands.py",
    "banned_filesystem_commands.py",
    "force_flag_defense.py",
    "pip_install_block.py",
]


def load_and_run(hook_file: str, input_data: dict) -> int:
    """Load a hook module and run its main(), capturing exit code."""
    path = HOOKS_DIR / hook_file
    if not path.exists():
        return 0

    spec = importlib.util.spec_from_file_location(hook_file.replace(".py", ""), path)
    if spec is None or spec.loader is None:
        return 0

    module = importlib.util.module_from_spec(spec)

    # Each sub-hook reads from stdin via json.load(sys.stdin).
    # We've already consumed stdin, so we patch it.
    import io
    original_stdin = sys.stdin
    sys.stdin = io.StringIO(json.dumps(input_data))

    try:
        spec.loader.exec_module(module)
        # Sub-hooks call sys.exit() — catch SystemExit to get the code
        if hasattr(module, "main"):
            module.main()
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 0
    finally:
        sys.stdin = original_stdin

    return 0


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    for hook_file in SUB_HOOKS:
        exit_code = load_and_run(hook_file, input_data)
        if exit_code != 0:
            # Sub-hook already printed its error message to stderr
            sys.exit(exit_code)

    sys.exit(0)


if __name__ == "__main__":
    main()
