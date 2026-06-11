"""Regression test for CON-008: parallel same-role workers must not drop
conductor dispatch messages.

The original hook keyed its baseline file by (project, role) only; two
same-role sessions raced on it and one silently missed messages. The fix
keys the baseline by session_id and starts a session's first check at the
current log length (no replay of pre-session history).

Run: python3 -m pytest .claude/hooks/tests/test_dispatch_check.py
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
HOOK = PROJECT_ROOT / ".claude" / "hooks" / "dispatch_check.py"
DISPATCH_LOG = PROJECT_ROOT / ".conductor" / "dispatch" / "claude" / "updates.jsonl"


def _call_hook(session_id: str) -> dict:
    env = dict(os.environ, BQ_PIPELINE_AGENT_ROLE="claude")
    proc = subprocess.run(
        ["python3", str(HOOK)],
        input=json.dumps({"session_id": session_id}),
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        env=env,
    )
    return json.loads(proc.stdout)


@pytest.fixture
def dispatch_log():
    DISPATCH_LOG.parent.mkdir(parents=True, exist_ok=True)
    existing = DISPATCH_LOG.read_text() if DISPATCH_LOG.exists() else None
    yield DISPATCH_LOG
    if existing is None:
        DISPATCH_LOG.unlink(missing_ok=True)
    else:
        DISPATCH_LOG.write_text(existing)
    project = PROJECT_ROOT.name
    for f in Path("/tmp").glob(f"dispatch-baseline-{project}-claude-test-*"):
        f.unlink()


def test_parallel_sessions_both_see_message(dispatch_log):
    # First check per session establishes a baseline without replaying history
    assert "systemMessage" not in _call_hook("test-sess-a")
    assert "systemMessage" not in _call_hook("test-sess-b")

    with dispatch_log.open("a") as f:
        f.write(
            json.dumps(
                {"type": "task", "from": "conductor", "message": "msg-for-both"}
            )
            + "\n"
        )

    # The CON-008 race: with a shared baseline, whichever session checked
    # first advanced the count and the other never saw the message.
    assert "msg-for-both" in _call_hook("test-sess-a").get("systemMessage", "")
    assert "msg-for-both" in _call_hook("test-sess-b").get("systemMessage", "")

    # Same session re-checking must not re-alert
    assert "systemMessage" not in _call_hook("test-sess-a")
