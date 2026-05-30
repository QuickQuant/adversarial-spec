#!/usr/bin/env python3
"""
Hook: pipeline_idle_retry
Event: PostToolUse / AfterTool (matcher: pipeline_do_next_task)

Fires after every pipeline_do_next_task call. If the result contains
"idle", injects a systemMessage telling the LLM to sleep with
escalating backoff and retry. Tracks consecutive idle count in a
temp file for backoff calculation.

If the result is NOT idle (card picked up), resets the idle counter.
"""

import json
import os
import sys
from pathlib import Path

ACTIVE_BACKOFF = [30, 60, 120, 240]  # active hours (07-22), cap 240s
OVERNIGHT_BACKOFF = [30, 60, 120, 240, 480, 960]  # overnight (22-07), cap 960s
ACTIVE_START = 7
OVERNIGHT_START = 22
MAX_IDLE_BEFORE_STATUS = 6  # post status to conductor after this many consecutive idles
ROLE_ENV_VARS = ("BQ_PIPELINE_AGENT_ROLE", "BQ_WORKER_ROLE", "PIPELINE_AGENT_ROLE")
KNOWN_ROLES = {"claude", "codex", "gemini", "glm"}


def _role_from_registration(input_data: dict) -> str:
    session_id = input_data.get("session_id", "")
    transcript_path = input_data.get("transcript_path", "")
    agents_dir = Path(".conductor/agents")
    if not agents_dir.exists():
        return ""
    for agent_file in agents_dir.glob("*.json"):
        try:
            data = json.loads(agent_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        role = str(data.get("role") or agent_file.stem)
        if role not in KNOWN_ROLES:
            continue
        registered_sessions = {
            str(data.get("session_id", "")),
            str(data.get("claude_session_id", "")),
            str(data.get("hook_session_id", "")),
        }
        registered_transcripts = {
            str(data.get("transcript_path", "")),
            str(data.get("claude_transcript_path", "")),
        }
        if session_id and session_id in registered_sessions:
            return role
        if transcript_path and transcript_path in registered_transcripts:
            return role
    return ""


def _detect_role(input_data: dict | None = None) -> str:
    for env_var in ROLE_ENV_VARS:
        value = os.environ.get(env_var, "").strip().lower()
        if value in KNOWN_ROLES:
            return value
    registered_role = _role_from_registration(input_data or {})
    if registered_role:
        return registered_role
    if os.environ.get("CLAUDE_PROJECT_DIR"):
        return "claude"
    if os.environ.get("GEMINI_PROJECT_DIR"):
        return "gemini"
    return "codex"


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        json.dump({}, sys.stdout)
        return

    # Extract tool result from hook input
    # Claude Code uses "tool_result", Codex uses "tool_response",
    # Gemini may use "output".
    tool_output = (
        input_data.get("tool_result")
        or input_data.get("tool_response")
        or input_data.get("output")
        or ""
    )
    if isinstance(tool_output, dict):
        tool_output_str = json.dumps(tool_output)
    else:
        tool_output_str = str(tool_output)

    role = _detect_role(input_data)
    project = os.path.basename(os.getcwd())
    idle_file = Path(f"/tmp/pipeline-idle-count-{project}-{role}.txt")

    compact_output = tool_output_str.replace(" ", "")
    is_idle = (
        '"action":"idle"' in compact_output
        or '"action": "idle"' in tool_output_str
    )

    if not is_idle:
        # Card picked up — reset counter and notify
        try:
            idle_file.write_text("0")
        except OSError:
            pass

        json.dump({}, sys.stdout)
        return

    # Idle response — increment counter and enforce retry
    idle_count = 0
    if idle_file.exists():
        try:
            idle_count = int(idle_file.read_text().strip())
        except (ValueError, OSError):
            idle_count = 0
    idle_count += 1

    try:
        idle_file.write_text(str(idle_count))
    except OSError:
        pass

    from datetime import datetime

    hour = datetime.now().hour
    is_overnight = hour >= OVERNIGHT_START or hour < ACTIVE_START
    schedule = OVERNIGHT_BACKOFF if is_overnight else ACTIVE_BACKOFF
    backoff_idx = min(idle_count - 1, len(schedule) - 1)
    sleep_secs = schedule[backoff_idx]

    # Actually sleep here — the LLM won't do it reliably
    import time
    time.sleep(sleep_secs)

    status_note = ""
    if idle_count == MAX_IDLE_BEFORE_STATUS:
        status_note = (
            f"\n\nThis is idle attempt #{idle_count}. Post a status update to "
            f".conductor/dispatch/claude/updates.jsonl:\n"
            f'{{"type":"worker_idle","role":"{role}","consecutive_idles":{idle_count},'
            f'"timestamp":"<ISO8601>"}}'
        )

    system_msg = (
        f"PIPELINE IDLE — no card available (attempt #{idle_count}, "
        f"slept {sleep_secs}s). DO NOT STOP. "
        f"Call pipeline_do_next_task again now with the same parameters."
        f"{status_note}"
    )

    json.dump({"systemMessage": system_msg}, sys.stdout)


if __name__ == "__main__":
    main()
