"""Integration tests for debate.py advisory F-prime gate wiring."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pytest
from debate import enforce_pipeline_card_gate
from tests.test_tmr_schema_contract import valid_tmr


def args_for(
    action: str,
    pipeline_card: str = "9999",
    accept_tests_stale: bool = False,
    accept_missing_spine: bool = False,
    spine_override_reason: str | None = None,
) -> argparse.Namespace:
    return argparse.Namespace(
        action=action,
        pipeline_card=pipeline_card,
        override_reason=None,
        accept_tests_stale=accept_tests_stale,
        accept_missing_spine=accept_missing_spine,
        spine_override_reason=spine_override_reason,
    )


def write_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    records: list[dict],
    *,
    stale_tests: bool = False,
) -> Path:
    session_id = "fprime-session"
    root = tmp_path / ".adversarial-spec"
    specs = root / "specs" / session_id
    roadmap_dir = specs / "roadmap"
    sessions_dir = root / "sessions"
    roadmap_dir.mkdir(parents=True)
    sessions_dir.mkdir(parents=True)

    spec_path = specs / "spec-output.md"
    tests_path = specs / "tests-pseudo.md"
    if stale_tests:
        tests_path.write_text("# Tests\n", encoding="utf-8")
        time.sleep(0.01)
        spec_path.write_text("# Spec\n", encoding="utf-8")
    else:
        spec_path.write_text("# Spec\n", encoding="utf-8")
        time.sleep(0.01)
        tests_path.write_text("# Tests\n", encoding="utf-8")

    roadmap_path = roadmap_dir / "manifest.json"
    roadmap_path.write_text(
        json.dumps({"user_stories": ["US-1", "US-2"]}),
        encoding="utf-8",
    )
    registry_path = specs / "tmr-registry.json"
    registry_path.write_text(json.dumps(records), encoding="utf-8")

    detail = {
        "session_id": session_id,
        "fizzy_card_id": "9999",
        "spec_path": f"specs/{session_id}/spec-output.md",
        "tests_pseudo_path": f"specs/{session_id}/tests-pseudo.md",
        "roadmap_path": f"specs/{session_id}/roadmap/manifest.json",
        "tmr_registry_path": f"specs/{session_id}/tmr-registry.json",
    }
    (sessions_dir / f"{session_id}.json").write_text(json.dumps(detail), encoding="utf-8")
    (root / "session-state.json").write_text(
        json.dumps(
            {
                "active_session_id": session_id,
                "active_session_file": f"sessions/{session_id}.json",
                "spec_path": detail["spec_path"],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    return root


def spine_record(uid_suffix: str, story: str) -> dict:
    return valid_tmr(
        tmr_uid=f"01J0EXEMPLARULID0000000{uid_suffix}",
        test_id=f"TC-{story.removeprefix('US-')}.0",
        user_story=story,
        spine=True,
    )


def test_tc_8_3_missing_spine_blocks_gauntlet_but_warns_critique(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_session(tmp_path, monkeypatch, [spine_record("831", "US-1")])

    with pytest.raises(SystemExit) as exc_info:
        enforce_pipeline_card_gate(args_for("gauntlet"))
    assert exc_info.value.code == 2
    assert "uncovered_story" in capsys.readouterr().err

    enforce_pipeline_card_gate(args_for("critique"))
    assert "WARNING: F-prime spine coverage check" in capsys.readouterr().err


def test_fprime_gate_is_sibling_to_staleness_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    records = [spine_record("841", "US-1"), spine_record("842", "US-2")]
    write_session(tmp_path, monkeypatch, records, stale_tests=True)

    with pytest.raises(SystemExit) as exc_info:
        enforce_pipeline_card_gate(args_for("gauntlet"))
    assert exc_info.value.code == 2

    enforce_pipeline_card_gate(args_for("gauntlet", accept_tests_stale=True))


def test_tc_inv_001_missing_spine_override_is_separate_from_stale_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = write_session(tmp_path, monkeypatch, [spine_record("851", "US-1")])

    with pytest.raises(SystemExit) as exc_info:
        enforce_pipeline_card_gate(args_for("gauntlet", accept_tests_stale=True))
    assert exc_info.value.code == 2

    enforce_pipeline_card_gate(
        args_for(
            "gauntlet",
            accept_missing_spine=True,
            spine_override_reason="US-2 intentionally deferred for this advisory run",
        )
    )
    decisions_log = root / "sessions" / "fprime-session.decisions.log"
    assert decisions_log.is_file()
    assert "override missing spine" in decisions_log.read_text(encoding="utf-8")
