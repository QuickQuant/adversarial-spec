"""Shared pytest fixtures for the scripts test suite."""

import json
import time

import pytest


@pytest.fixture
def fresh_tracker(monkeypatch):
    """Provide isolated token accounting state for tests."""
    import token_tracking

    fresh = token_tracking.TokenTracker()
    monkeypatch.setattr(token_tracking, "tracker", fresh)
    yield fresh


@pytest.fixture
def tracked_session(tmp_path, monkeypatch):
    """Build a fake adversarial-spec session on disk and chdir into it.

    Yields the fizzy_card_id. Tests for pipeline activities (critique/gauntlet)
    must pass this id via --pipeline-card to satisfy the debate.py
    enforce_pipeline_card_gate.
    """
    fizzy_card_id = "9999"
    session_id = "test-session"
    spec_rel = f"specs/{session_id}/spec-output.md"
    tests_rel = f"specs/{session_id}/tests-pseudo.md"

    root = tmp_path / ".adversarial-spec"
    (root / "sessions").mkdir(parents=True)
    (root / f"specs/{session_id}").mkdir(parents=True)

    spec_path = root / spec_rel
    tests_path = root / tests_rel
    spec_path.write_text("# Test Spec\n")
    time.sleep(0.01)
    tests_path.write_text("# Tests Pseudo\n")

    (root / f"sessions/{session_id}.json").write_text(json.dumps({
        "session_id": session_id,
        "fizzy_card_id": fizzy_card_id,
        "spec_path": spec_rel,
        "tests_pseudo_path": tests_rel,
    }))
    (root / "session-state.json").write_text(json.dumps({
        "active_session_id": session_id,
        "active_session_file": f"sessions/{session_id}.json",
        "spec_path": spec_rel,
    }))

    monkeypatch.chdir(tmp_path)
    yield fizzy_card_id
