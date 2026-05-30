#!/usr/bin/env python3
"""
Hook: pipeline_notifications
Purpose: Auto-notify Telegram + dispatch on Fizzy pipeline state changes.
Version: 2.0.0

Fires on: PostToolUse for mcp__fizzy__pipeline_* and mcp__trello__pipeline_*
Behavior: ASYNC, NEVER BLOCKS (exit 0 always).

Actions:
  pipeline_complete_task → Telegram + auto-dispatch review to all registered workers
  pipeline_review → Telegram + auto-dispatch back to implementer (baton return)
  pipeline_do_next_task → Telegram (informational)
  pipeline_test → Telegram (informational)

Config: .conductor/notifications.json
"""

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def _find_project_root() -> Path | None:
    cwd = Path.cwd()
    for p in [cwd, *cwd.parents]:
        if (p / ".git").exists():
            return p
    return None


def _load_config(root: Path) -> dict | None:
    config_path = root / ".conductor" / "notifications.json"
    if not config_path.exists():
        return None
    try:
        return json.loads(config_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _telegram_send(project: str, message: str) -> None:
    script = Path.home() / ".claude" / "bin" / "telegram-send"
    if not script.exists():
        return
    try:
        subprocess.Popen(
            [str(script), project, message],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        pass


AGENT_PREFIXES = {
    "codex": "\u2b1b [Codex]",   # black square
    "gemini": "\U0001f7e9 [Gemini]",  # green square
    "claude": "\U0001f7e7 [Claude]",  # orange square
    "glm": "\U0001f7e6 [GLM]",  # blue square
}

_RESULT_KEYS = {
    "ok",
    "action",
    "card_id",
    "card_name",
    "moved_to",
    "verdict",
    "result",
    "state",
}


def _append_dispatch(root: Path, target_agent: str, record: dict) -> None:
    """Append a dispatch record to a worker's updates.jsonl.

    For conductor (claude), also writes to the Telegram listener JSONL
    so the existing telegram-wake-listener wakes without a second process.
    """
    # Always write to the agent's dispatch JSONL
    path = root / ".conductor" / "dispatch" / target_agent / "updates.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")

    # For conductor: also write to Telegram listener JSONL to wake it
    if target_agent == "claude":
        project = root.name
        tg_path = (
            Path.home() / ".local" / "state"
            / f"{project}-listener" / "updates.jsonl"
        )
        if tg_path.parent.exists():
            from_agent = record.get("reviewer", record.get("from_agent", "?"))
            prefix = AGENT_PREFIXES.get(from_agent, f"[{from_agent}]")
            tg_record = {
                "type": "agent_dispatch",
                "source": from_agent,
                "prefix": prefix,
                "message": record.get("message", ""),
                "timestamp": record.get("timestamp", _now_iso()),
            }
            with open(tg_path, "a") as f:
                f.write(json.dumps(tg_record, default=str) + "\n")


def _get_registered_agents(root: Path, exclude: str = "") -> list[str]:
    """Get list of registered agent roles from .conductor/agents/."""
    agents_dir = root / ".conductor" / "agents"
    if not agents_dir.exists():
        return []
    agents = []
    for f in agents_dir.iterdir():
        if f.suffix == ".json":
            role = f.stem
            if role != exclude:
                agents.append(role)
    return agents


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _try_parse_json(value: str) -> dict | list | None:
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, (dict, list)) else None


def _unwrap_tool_payload(value) -> dict:
    """Return the pipeline result dict from Claude/Codex/MCP wrapper shapes."""
    if isinstance(value, str):
        parsed = _try_parse_json(value.strip())
        return _unwrap_tool_payload(parsed) if parsed is not None else {}

    if isinstance(value, list):
        for item in value:
            parsed = _unwrap_tool_payload(item)
            if parsed:
                return parsed
        return {}

    if not isinstance(value, dict):
        return {}

    if _RESULT_KEYS & value.keys():
        return value

    for key in (
        "structuredContent",
        "data",
        "result",
        "tool_result",
        "tool_response",
        "output",
    ):
        parsed = _unwrap_tool_payload(value.get(key))
        if parsed:
            return parsed

    content = value.get("content")
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                parsed = _unwrap_tool_payload(item.get("text") or item.get("content"))
                if parsed:
                    return parsed
            else:
                parsed = _unwrap_tool_payload(item)
                if parsed:
                    return parsed

    text = value.get("text")
    if isinstance(text, str):
        parsed = _unwrap_tool_payload(text)
        if parsed:
            return parsed

    return value


def _extract_tool_result(input_data: dict) -> dict:
    return _unwrap_tool_payload(
        input_data.get("tool_result")
        or input_data.get("tool_response")
        or input_data.get("output")
        or {}
    )


def _extract_tool_input(input_data: dict) -> dict:
    return _unwrap_tool_payload(
        input_data.get("tool_input")
        or input_data.get("input")
        or input_data.get("parameters")
        or {}
    )


def _first_string(*values) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _card_label(tool_result: dict) -> str:
    state = (
        tool_result.get("state")
        if isinstance(tool_result.get("state"), dict)
        else {}
    )
    card = tool_result.get("card") if isinstance(tool_result.get("card"), dict) else {}
    name = _first_string(
        tool_result.get("card_name"),
        tool_result.get("name"),
        tool_result.get("card_title"),
        tool_result.get("title"),
        card.get("name"),
        card.get("title"),
        state.get("card_name"),
        state.get("name"),
        state.get("title"),
    )
    if name:
        return name
    card_id = _first_string(
        tool_result.get("card_id"),
        card.get("card_id"),
        card.get("id"),
        state.get("card_id"),
    )
    return f"card {card_id}" if card_id else "unknown card"


def _calling_agent(tool_result: dict, tool_input: dict | None = None) -> str:
    tool_input = tool_input or {}
    state = (
        tool_result.get("state")
        if isinstance(tool_result.get("state"), dict)
        else {}
    )
    return _first_string(
        tool_input.get("agent"),
        tool_result.get("agent"),
        tool_result.get("role"),
        state.get("reviewer_agent"),
        state.get("implementer_agent"),
        "unknown",
    )


def _normalized_verdict(verdict: str) -> tuple[str, str]:
    value = verdict.strip().lower()
    if value in {"approve", "approved", "pass", "passed"}:
        return ("approved", "\u2705")
    if value in {
        "reject",
        "rejected",
        "changes_requested",
        "changes-requested",
        "fail",
        "failed",
    }:
        return ("changes requested", "\u274c")
    return (verdict or "unknown", "\u2754")


def _handle_complete_task(
    root: Path, project: str, tool_result: dict, calling_agent: str
) -> tuple[str, str] | None:
    """Card moved to Review — auto-dispatch review to all other agents."""
    card_id = str(tool_result.get("card_id", "?"))
    card_name = _card_label(tool_result)
    moved_to = _first_string(tool_result.get("moved_to"), "Review")
    commit_hash = _first_string(
        tool_result.get("commit_hash"),
        tool_result.get("commit"),
    )
    board_id = _first_string(tool_result.get("board_id"), tool_result.get("board"))
    session_id = _first_string(tool_result.get("session_id"))

    # Dispatch review request to all registered agents except the implementer
    other_agents = _get_registered_agents(root, exclude=calling_agent)
    for agent in other_agents:
        _append_dispatch(root, agent, {
            "type": "review_requested",
            "card_id": card_id,
            "card_name": card_name,
            "commit_hash": commit_hash,
            "board_id": board_id,
            "session_id": session_id,
            "from_agent": calling_agent,
            "timestamp": _now_iso(),
            "message": (
                f"{card_name} needs review. "
                f"Use pipeline_do_next_task to pick up review work."
            ),
            "on_complete": (
                "After reviewing, the hook will auto-notify the "
                "implementer. No manual dispatch needed."
            ),
        })

    return ("task_completed", f"Completed: {card_name}, moved to {moved_to}")


def _handle_review(
    root: Path, project: str, tool_result: dict, calling_agent: str
) -> tuple[str, str] | None:
    """Review completed — auto-dispatch baton back to implementer."""
    card_id = str(tool_result.get("card_id", "?"))
    card_name = _card_label(tool_result)
    verdict, emoji = _normalized_verdict(str(tool_result.get("verdict", "")))
    moved_to = _first_string(tool_result.get("moved_to"), "?")

    # Find implementer from card state
    state = tool_result.get("state", {})
    if not isinstance(state, dict):
        state = {}
    implementer = state.get("implementer_agent", "")

    if implementer and implementer != calling_agent:
        _append_dispatch(root, implementer, {
            "type": "review_completed",
            "card_id": card_id,
            "card_name": card_name,
            "verdict": verdict,
            "reviewer": calling_agent,
            "timestamp": _now_iso(),
            "message": (
                f"{emoji} {card_name} {verdict} by {calling_agent}. "
                f"Moved to {moved_to}."
            ),
        })

    return (
        "review_completed",
        f"{emoji} Review: {card_name} {verdict}, moved to {moved_to}",
    )


def _extract_event(
    tool_name: str,
    tool_result: dict,
    root: Path,
    project: str,
    tool_input: dict | None = None,
) -> tuple[str, str] | None:
    """Map tool name + result to (event_type, message).

    Also performs auto-dispatch side effects for complete_task and review.
    """
    if not tool_result.get("ok", False):
        return None

    calling_agent = _calling_agent(tool_result, tool_input)

    if "pipeline_do_next_task" in tool_name:
        action = tool_result.get("action", "")
        if action == "idle":
            return None
        card = _card_label(tool_result)
        lane = _first_string(tool_result.get("lane"), tool_result.get("from_lane"), "?")
        return ("task_picked", f"Picked up: {card} (from {lane})")

    if "pipeline_complete_task" in tool_name:
        return _handle_complete_task(root, project, tool_result, calling_agent)

    if "pipeline_review" in tool_name:
        return _handle_review(root, project, tool_result, calling_agent)

    if "pipeline_test" in tool_name:
        card = _card_label(tool_result)
        result = str(tool_result.get("result", "?"))
        moved_to = _first_string(tool_result.get("moved_to"), "?")
        emoji = "\u2705" if result == "pass" else "\u274c"
        return (
            "test_completed",
            f"{emoji} Test: {card} {result}, moved to {moved_to}",
        )

    return None


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")

    # Only handle pipeline tools
    if "pipeline_" not in tool_name:
        sys.exit(0)

    root = _find_project_root()
    if not root:
        sys.exit(0)

    config = _load_config(root)
    if not config:
        sys.exit(0)

    tg = config.get("telegram", {})
    if not tg.get("enabled", False):
        sys.exit(0)

    project = tg.get("project", "")
    if not project:
        sys.exit(0)

    events_config = tg.get("events", {})

    tool_result = _extract_tool_result(input_data)
    tool_input = _extract_tool_input(input_data)

    event = _extract_event(tool_name, tool_result, root, project, tool_input)
    if not event:
        sys.exit(0)

    event_type, message = event
    if not events_config.get(event_type, False):
        sys.exit(0)

    # Detect calling agent for prefix
    calling_agent = _calling_agent(tool_result, tool_input)
    prefix = AGENT_PREFIXES.get(calling_agent, f"[{calling_agent}]")
    _telegram_send(project, f"{prefix} {message}")
    sys.exit(0)


if __name__ == "__main__":
    main()
