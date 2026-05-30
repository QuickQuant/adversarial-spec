"""
Shared config resolver for hooks.

Resolves hook_config.json per-project regardless of which agent is calling.
Claude hooks live per-project, but Gemini/Codex call Brainquarters scripts
by absolute path. This module resolves the *project's* config, not the
script's directory.

Resolution order:
1. GEMINI_PROJECT_DIR env var → <dir>/.claude/hooks/hook_config.json
2. CLAUDE_PROJECT_DIR env var → <dir>/.claude/hooks/hook_config.json
3. CWD git root → <root>/.claude/hooks/hook_config.json
4. Script's own directory → hook_config.json (Claude per-project fallback)
5. Default: {"mode": "flexible"}
"""

import json
import os
import subprocess
from functools import lru_cache
from pathlib import Path


def _git_root() -> Path | None:
    """Find git root from CWD."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=3,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


@lru_cache(maxsize=1)
def resolve_config(hook_file: str | None = None) -> dict:
    """
    Load the project-local hook_config.json.

    Args:
        hook_file: __file__ of the calling hook (used as final fallback).
    """
    candidates: list[Path] = []

    # 1. Agent-specific project dir env vars
    for env_var in ("GEMINI_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        project_dir = os.environ.get(env_var)
        if project_dir:
            candidates.append(Path(project_dir) / ".claude" / "hooks" / "hook_config.json")

    # 2. CWD git root
    git_root = _git_root()
    if git_root:
        candidates.append(git_root / ".claude" / "hooks" / "hook_config.json")

    # 3. Script's own directory (Claude per-project)
    if hook_file:
        candidates.append(Path(hook_file).parent / "hook_config.json")

    for config_path in candidates:
        if config_path.exists():
            try:
                with open(config_path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

    return {"mode": "flexible"}
