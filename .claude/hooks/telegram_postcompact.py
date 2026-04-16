#!/usr/bin/env python3
"""
Hook: telegram_postcompact
Hook Type: PostCompact
Matcher: (none — fires on every compaction)

After context compaction, check if a Telegram wake listener exited but its
messages were never processed. This happens when the one-shot wake listener
fires during compaction — the task-notification is lost, and Jason's replies
go unanswered.

If unprocessed messages exist, output them to stderr (exit 2) so Claude
processes them immediately after compaction.
"""

import json
import os
import sys
from pathlib import Path


# Resolve project name from git root or cwd
def get_project_name() -> str:
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if project_dir:
        return Path(project_dir).name
    return Path.cwd().name

def main():
    project = get_project_name()
    baseline_file = Path(f"/tmp/claude-telegram-baseline-{project}")
    pid_file = Path(f"/tmp/claude-telegram-wake-{project}.pid")
    log_file = Path.home() / ".local" / "state" / f"{project}-listener" / "updates.jsonl"

    # No baseline file = no Telegram handback in progress
    if not baseline_file.exists():
        sys.exit(0)

    # Wake listener still alive = working correctly, no action needed
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)  # Check if process is alive (signal 0)
            sys.exit(0)  # Listener is alive, all good
        except (ProcessLookupError, ValueError):
            pass  # PID is dead or invalid — listener exited
        except PermissionError:
            sys.exit(0)  # Process exists but we can't signal it — assume alive

    # Listener is dead. Check for new messages since baseline.
    if not log_file.exists():
        sys.exit(0)

    try:
        baseline = int(baseline_file.read_text().strip())
    except (ValueError, OSError):
        sys.exit(0)

    with open(log_file) as f:
        all_lines = f.readlines()

    current_count = len(all_lines)
    if current_count <= baseline:
        sys.exit(0)  # No new messages

    # Extract new messages
    new_lines = all_lines[baseline:]
    messages = []
    for line in new_lines:
        try:
            update = json.loads(line.strip())
            msg = update.get("message", {})
            text = msg.get("text", "")
            sender = msg.get("from", {}).get("first_name", "Unknown")
            if text:
                messages.append(f"  {sender}: {text}")
        except (json.JSONDecodeError, AttributeError):
            continue

    if not messages:
        sys.exit(0)

    # Alert Claude about unprocessed Telegram messages
    print("UNPROCESSED TELEGRAM MESSAGES", file=sys.stderr)
    print(f"The wake listener exited during compaction. {len(messages)} message(s) from Telegram were never processed:", file=sys.stderr)
    print("", file=sys.stderr)
    for msg in messages:
        print(msg, file=sys.stderr)
    print("", file=sys.stderr)
    print("ACTION REQUIRED: Read and respond to these messages via Telegram.", file=sys.stderr)
    print(f"Then launch a new wake listener or remove {baseline_file} if no handback needed.", file=sys.stderr)

    sys.exit(2)  # Feed to Claude

if __name__ == "__main__":
    main()
