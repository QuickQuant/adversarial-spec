#!/usr/bin/env python3
"""
Hook: dispatch_check
Event: PreToolUse (matcher: pipeline_do_next_task)

Fires before every pipeline_do_next_task call. Reads the dispatch log
for the calling agent, compares against a stored baseline, and injects
any new messages as a systemMessage so the LLM is forced to see them.

Baseline stored in /tmp/dispatch-baseline-<project>-<role>.txt
"""

import json
import os
import sys
from pathlib import Path

ROLE_ENV_VARS = ("BQ_PIPELINE_AGENT_ROLE", "BQ_WORKER_ROLE", "PIPELINE_AGENT_ROLE")
KNOWN_ROLES = {"claude", "codex", "gemini", "glm"}


def _role_from_registration(input_data: dict) -> str:
    """Match this Claude Code hook invocation to a registered worker marker."""
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
    """Best-effort role detection from environment."""
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
    # Codex: check for sandbox indicators or default
    if os.environ.get("CODEX_PROJECT_DIR") or os.environ.get("CODEX_SANDBOX"):
        return "codex"
    # Fallback: check agent registration files
    for role in ("codex", "gemini", "glm", "claude"):
        agent_file = Path(".conductor/agents") / f"{role}.json"
        if agent_file.exists():
            try:
                data = json.loads(agent_file.read_text())
                pid = data.get("pid")
                if pid == "sandboxed" and role == "codex":
                    return "codex"
            except (json.JSONDecodeError, OSError):
                pass
    return "codex"  # conservative default for this hook's purpose


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        json.dump({"decision": "allow"}, sys.stdout)
        return

    role = _detect_role(input_data)
    project = os.path.basename(os.getcwd())
    dispatch_log = Path(f".conductor/dispatch/{role}/updates.jsonl")
    baseline_file = Path(f"/tmp/dispatch-baseline-{project}-{role}.txt")

    if not dispatch_log.exists():
        json.dump({"decision": "allow"}, sys.stdout)
        return

    # Read current line count
    try:
        lines = dispatch_log.read_text().splitlines()
        current_count = len(lines)
    except OSError:
        json.dump({"decision": "allow"}, sys.stdout)
        return

    # Read baseline
    baseline = 0
    if baseline_file.exists():
        try:
            baseline = int(baseline_file.read_text().strip())
        except (ValueError, OSError):
            baseline = 0

    # Update baseline
    try:
        baseline_file.write_text(str(current_count))
    except OSError:
        pass

    # Check for new messages
    if current_count > baseline:
        new_lines = lines[baseline:]
        messages = []
        for line in new_lines:
            try:
                entry = json.loads(line)
                msg_type = entry.get("type", "unknown")
                msg_from = entry.get("from", entry.get("role", "?"))
                msg_text = entry.get("message", entry.get("text", json.dumps(entry)))
                messages.append(f"[{msg_type}] from={msg_from}: {msg_text}")
            except json.JSONDecodeError:
                messages.append(line.strip())

        system_msg = (
            f"DISPATCH ALERT: {len(new_lines)} new message(s) in "
            f".conductor/dispatch/{role}/updates.jsonl since last check:\n\n"
            + "\n".join(messages)
            + "\n\nProcess these messages before continuing with pipeline work. "
            "If a stop signal is present, do NOT call pipeline_do_next_task."
        )
        json.dump({"decision": "allow", "systemMessage": system_msg}, sys.stdout)
    else:
        json.dump({"decision": "allow"}, sys.stdout)


if __name__ == "__main__":
    main()
