#!/usr/bin/env python3
"""
Hook: session_activity_logger
Purpose: Log session activity timestamps for conductor cross-session visibility.
Version: 1.0.0

Fires on: SessionStart, UserPromptSubmit, SessionEnd
Runs async (non-blocking) at the user level across all projects.

Writes per-project activity log to <project_root>/.claude/session-activity.jsonl.
Conductor reads this to show "last activity per session" in briefings.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Max log size before rotation (1MB — much smaller than conductor's 20MB
# since this only stores timestamps, not content)
MAX_LOG_BYTES = 1_000_000


def find_project_root(cwd: str) -> Path | None:
    """Find git root from cwd."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except Exception:
        pass
    return None


def rotate_if_needed(log_path: Path) -> None:
    """Rotate log if it exceeds MAX_LOG_BYTES. Keep 1 backup."""
    try:
        if log_path.exists() and log_path.stat().st_size > MAX_LOG_BYTES:
            backup = log_path.with_suffix(".jsonl.1")
            if backup.exists():
                backup.unlink()
            log_path.rename(backup)
    except Exception:
        pass


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    session_id = input_data.get("session_id", "")
    event = input_data.get("hook_event_name", "")
    cwd = input_data.get("cwd", os.getcwd())

    if not session_id or not event:
        sys.exit(0)

    project_root = find_project_root(cwd)
    if not project_root:
        sys.exit(0)

    claude_dir = project_root / ".claude"
    if not claude_dir.is_dir():
        sys.exit(0)

    log_path = claude_dir / "session-activity.jsonl"

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "event": event,
        "project": project_root.name,
    }

    # Add event-specific fields
    if event == "SessionStart":
        entry["source"] = input_data.get("source", "")
        entry["model"] = input_data.get("model", "")
    elif event == "SessionEnd":
        entry["reason"] = input_data.get("reason", "")

    try:
        rotate_if_needed(log_path)
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # Never fail — this is passive logging

    # Codex Stop hooks require JSON output on stdout.
    # Other CLIs ignore stdout from non-blocking hooks, so this is safe everywhere.
    if event in ("Stop", "SessionEnd"):
        print('{"continue": true}')

    sys.exit(0)


if __name__ == "__main__":
    main()
