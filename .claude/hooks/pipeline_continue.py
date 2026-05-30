#!/usr/bin/env python3
"""
Hook: pipeline_continue
Event: PostToolUse / AfterTool
Matcher: pipeline_complete_task|pipeline_review|pipeline_test

After a worker completes, reviews, or tests a card, inject a systemMessage
forcing it to call pipeline_do_next_task. This ensures the worker enters
the idle retry loop instead of deciding on its own to stop.

Without this hook, workers bypass pipeline_do_next_task after completing
work and go straight to Stop — defeating the idle retry and dispatch
check hooks entirely.
"""

import json
import os
import sys
from pathlib import Path

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

    tool_name = input_data.get("tool_name", "")

    # Only inject after successful pipeline state changes
    # Claude Code uses "tool_result", Codex uses "tool_response",
    # Gemini may use "output".
    tool_result = (
        input_data.get("tool_result")
        or input_data.get("tool_response")
        or input_data.get("output")
        or {}
    )
    if isinstance(tool_result, str):
        try:
            tool_result = json.loads(tool_result)
        except (json.JSONDecodeError, TypeError):
            tool_result = {}
    if isinstance(tool_result, dict) and not tool_result.get("ok", True):
        json.dump({}, sys.stdout)
        return

    action = ""
    if "complete_task" in tool_name:
        action = "completed implementation"
    elif "review" in tool_name:
        action = "completed review"
    elif "test" in tool_name:
        action = "completed testing"

    if not action:
        json.dump({}, sys.stdout)
        return

    role = _detect_role(input_data)

    msg = (
        f"You just {action}. DO NOT STOP. "
        f"Call pipeline_do_next_task immediately with the same session_id, "
        f'pipeline, agent="{role}", and board_id to pick up your next card. '
        f"The idle retry hook will handle backoff if no cards are available."
    )

    json.dump({"systemMessage": msg}, sys.stdout)


if __name__ == "__main__":
    main()
