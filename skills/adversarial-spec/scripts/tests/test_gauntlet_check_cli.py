"""Unit and integration tests for the gauntlet_check_cli script."""

from __future__ import annotations

import json
import re
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from gauntlet_check_cli import main


def make_valid_tmr_dict(
    tmr_uid: str,
    test_id: str,
    user_story: str | list[str],
    spine: bool = True,
    status: str = "active",
    maturity: str = "concrete",
    also_covers: list[str] | None = None,
    why_impossible_to_reproduce_live: str | None = None,
    technical_constraint: str | None = None,
    run_evidence: dict | None = None,
) -> dict:
    if also_covers is None:
        also_covers = []

    if run_evidence is None and maturity != "nl":
        run_evidence = {
            "tier": "code",
            "command": "uv run pytest tests/test_gateway.py -q",
            "cwd": "/repo",
            "repo": "prediction-prime",
            "commit": "abcdef1",
            "started_at": "2026-06-18T12:00:00Z",
            "finished_at": "2026-06-18T12:00:02Z",
            "exit": 0,
            "result": "pass",
            "env": "dev",
            "artifact_uri": "artifacts/fill.json",
            "artifact_sha256": "a" * 64,
            "runner": "skill-runner",
            "live_or_induced": {"kind": "tc-netem:partition"},
        }

    return {
        "tmr_uid": tmr_uid,
        "test_id": test_id,
        "title": "Default Test Title",
        "user_story": user_story,
        "maturity": maturity,
        "data_strategy": "REAL-DATA",
        "spine": spine,
        "verification_mode": "automated-contract",
        "verification_scope": "targeted",
        "altitude": "system",
        "tested_by": "llm",
        "critical_seam": False,
        "criticality_source": "explicit",
        "binding_status": "bound",
        "status": status,
        "source_spec": "liveness-gate-test-ladder",
        "live_or_induced": {"kind": "natural-wait"},
        "run_evidence": run_evidence,
        "why_impossible_to_reproduce_live": why_impossible_to_reproduce_live,
        "technical_constraint": technical_constraint,
        "also_covers": also_covers,
        "accessors": ["tmr_record"],
        "architecture_link": ["component:emission-toolchain"],
        "spine_steps": ["S1", "S2", "S3", "S4"],
        "supersedes": [],
        "tombstoned_at": "2026-06-18T12:00:00Z" if status == "tombstoned" else None,
        "spine_of": None,
        "spine_step_ref": None,
    }


@pytest.fixture
def temp_workspace() -> Path:
    # Use a temporary directory under Path.cwd() to satisfy path containment checks
    with tempfile.TemporaryDirectory(dir=Path.cwd(), prefix=".tmp_test_cli_") as tmpdir:
        yield Path(tmpdir)


def test_path_containment_violation() -> None:
    """If paths escape workspace root, return setup_error (exit 5)."""
    # Use standard /tmp directory which is outside workspace root
    with tempfile.TemporaryDirectory() as external_dir:
        ext_path = Path(external_dir)
        args = [
            "gauntlet-check",
            "--session", str(ext_path),
            "--roadmap-manifest", str(Path.cwd() / "roadmap.json"),
            "--tmr-registry", str(Path.cwd() / "tmr-registry.json"),
            "--action", "gauntlet",
            "--output", "json"
        ]
        with patch("sys.argv", args):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == 5
        data = json.loads(mock_stdout.getvalue())
        assert data["outcome"] == "setup_error"
        assert len(data["findings"]) == 1
        assert data["findings"][0]["code"] == "setup_error"
        assert "escapes" in data["findings"][0]["message"]


def test_tc_8_0_valid_full_coverage(temp_workspace: Path) -> None:
    """TC-8.0: Valid full coverage (exits 0 with outcome 'pass')."""
    session_dir = temp_workspace / "session"
    session_dir.mkdir()

    # Write session-state.json
    (session_dir / "session-state.json").write_text(
        json.dumps({"active_session_id": "session_80"})
    )

    # Write roadmap-manifest.json
    roadmap_path = temp_workspace / "roadmap-manifest.json"
    roadmap_path.write_text(json.dumps({"user_stories": ["US-1", "US-2"]}))

    # Write tmr-registry.json with valid spine records
    tmr_path = temp_workspace / "tmr-registry.json"
    records = [
        make_valid_tmr_dict("01J0EXEMPLARULID0000000080A1", "TC-1.0", "US-1"),
        make_valid_tmr_dict("01J0EXEMPLARULID0000000080A2", "TC-2.0", "US-2"),
    ]
    tmr_path.write_text(json.dumps(records))

    args = [
        "gauntlet-check",
        "--session", str(session_dir),
        "--roadmap-manifest", str(roadmap_path),
        "--tmr-registry", str(tmr_path),
        "--action", "gauntlet",
        "--output", "json",
    ]

    with patch("sys.argv", args):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()

    assert exc_info.value.code == 0
    data = json.loads(mock_stdout.getvalue())
    assert data["outcome"] == "pass"
    assert data["override_eligible"] is False
    assert len(data["findings"]) == 0


def test_tc_8_1_branch_on_action(temp_workspace: Path) -> None:
    """TC-8.1: Branch on action (action critique warns/exits 0, action gauntlet blocks/exits 2)."""
    session_dir = temp_workspace / "session"
    session_dir.mkdir()

    (session_dir / "session-state.json").write_text(
        json.dumps({"active_session_id": "session_81"})
    )

    roadmap_path = temp_workspace / "roadmap-manifest.json"
    # US-2 is missing a spine record
    roadmap_path.write_text(json.dumps({"user_stories": ["US-1", "US-2"]}))

    tmr_path = temp_workspace / "tmr-registry.json"
    records = [
        make_valid_tmr_dict("01J0EXEMPLARULID0000000081A1", "TC-1.0", "US-1"),
    ]
    tmr_path.write_text(json.dumps(records))

    # 1. Action = critique
    args_critique = [
        "gauntlet-check",
        "--session", str(session_dir),
        "--roadmap-manifest", str(roadmap_path),
        "--tmr-registry", str(tmr_path),
        "--action", "critique",
        "--output", "json",
    ]

    with patch("sys.argv", args_critique):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()

    assert exc_info.value.code == 0
    data = json.loads(mock_stdout.getvalue())
    assert data["outcome"] == "warn"
    assert data["override_eligible"] is False
    assert len(data["findings"]) == 1
    assert data["findings"][0]["code"] == "uncovered_story"
    assert data["findings"][0]["target"] == {"user_story": "US-2"}

    # 2. Action = gauntlet
    args_gauntlet = [
        "gauntlet-check",
        "--session", str(session_dir),
        "--roadmap-manifest", str(roadmap_path),
        "--tmr-registry", str(tmr_path),
        "--action", "gauntlet",
        "--output", "json",
    ]

    with patch("sys.argv", args_gauntlet):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()

    assert exc_info.value.code == 2
    data = json.loads(mock_stdout.getvalue())
    assert data["outcome"] == "block"
    assert data["override_eligible"] is True
    assert len(data["findings"]) == 1
    assert data["findings"][0]["code"] == "uncovered_story"
    assert data["findings"][0]["severity"] == "blocking"


def test_tc_8_2_maturity_aware(temp_workspace: Path) -> None:
    """TC-8.2: Maturity aware (a spine record with maturity="nl" is counted and passes)."""
    session_dir = temp_workspace / "session"
    session_dir.mkdir()

    (session_dir / "session-state.json").write_text(
        json.dumps({"active_session_id": "session_82"})
    )

    roadmap_path = temp_workspace / "roadmap-manifest.json"
    roadmap_path.write_text(json.dumps({"user_stories": ["US-1", "US-2"]}))

    tmr_path = temp_workspace / "tmr-registry.json"
    # US-2 record has maturity="nl"
    records = [
        make_valid_tmr_dict("01J0EXEMPLARULID0000000082A1", "TC-1.0", "US-1"),
        make_valid_tmr_dict("01J0EXEMPLARULID0000000082A2", "TC-2.0", "US-2", maturity="nl"),
    ]
    tmr_path.write_text(json.dumps(records))

    args = [
        "gauntlet-check",
        "--session", str(session_dir),
        "--roadmap-manifest", str(roadmap_path),
        "--tmr-registry", str(tmr_path),
        "--action", "gauntlet",
        "--output", "json",
    ]

    with patch("sys.argv", args):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()

    assert exc_info.value.code == 0
    data = json.loads(mock_stdout.getvalue())
    assert data["outcome"] == "pass"


def test_tc_8_3_overrides(temp_workspace: Path) -> None:
    """TC-8.3: Overrides (providing --accept-missing-spine and reason logs to decisions.log)."""
    session_dir = temp_workspace / "session"
    session_dir.mkdir()

    (session_dir / "session-state.json").write_text(
        json.dumps({"active_session_id": "session_83"})
    )

    roadmap_path = temp_workspace / "roadmap-manifest.json"
    roadmap_path.write_text(json.dumps({"user_stories": ["US-1", "US-2"]}))

    tmr_path = temp_workspace / "tmr-registry.json"
    records = [
        make_valid_tmr_dict("01J0EXEMPLARULID0000000083A1", "TC-1.0", "US-1"),
    ]
    tmr_path.write_text(json.dumps(records))

    # 1. Success override path
    args_success = [
        "gauntlet-check",
        "--session", str(session_dir),
        "--roadmap-manifest", str(roadmap_path),
        "--tmr-registry", str(tmr_path),
        "--action", "gauntlet",
        "--accept-missing-spine",
        "--spine-override-reason", "US-2 is not implemented yet",
        "--output", "json",
    ]

    with patch("sys.argv", args_success):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()

    assert exc_info.value.code == 0
    data = json.loads(mock_stdout.getvalue())
    assert data["outcome"] == "warn"
    assert data["override_eligible"] is False

    # Verify decisions.log contains expected line
    log_file = session_dir / "sessions" / "session_83.decisions.log"
    assert log_file.is_file()
    log_content = log_file.read_text(encoding="utf-8")
    assert "[gauntlet-check] override missing spine; reason: 'US-2 is not implemented yet'" in log_content
    # ISO8601 validation
    timestamp_match = re.search(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", log_content)
    assert timestamp_match is not None

    # 2. Failure path - empty reason
    args_empty_reason = [
        "gauntlet-check",
        "--session", str(session_dir),
        "--roadmap-manifest", str(roadmap_path),
        "--tmr-registry", str(tmr_path),
        "--action", "gauntlet",
        "--accept-missing-spine",
        "--spine-override-reason", "   ",
        "--output", "json",
    ]
    with patch("sys.argv", args_empty_reason):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()
    assert exc_info.value.code == 5
    data = json.loads(mock_stdout.getvalue())
    assert data["outcome"] == "setup_error"

    # 3. Failure path - missing reason
    args_missing_reason = [
        "gauntlet-check",
        "--session", str(session_dir),
        "--roadmap-manifest", str(roadmap_path),
        "--tmr-registry", str(tmr_path),
        "--action", "gauntlet",
        "--accept-missing-spine",
        "--output", "json",
    ]
    with patch("sys.argv", args_missing_reason):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()
    assert exc_info.value.code == 5
    data = json.loads(mock_stdout.getvalue())
    assert data["outcome"] == "setup_error"


def test_tc_8_4_duplicate_designations(temp_workspace: Path) -> None:
    """TC-8.4: Duplicate designations (exits 2 with outcome 'block')."""
    session_dir = temp_workspace / "session"
    session_dir.mkdir()

    (session_dir / "session-state.json").write_text(
        json.dumps({"active_session_id": "session_84"})
    )

    roadmap_path = temp_workspace / "roadmap-manifest.json"
    roadmap_path.write_text(json.dumps({"user_stories": ["US-1", "US-2"]}))

    tmr_path = temp_workspace / "tmr-registry.json"
    # Duplicate active spine designations for US-1
    records = [
        make_valid_tmr_dict("01J0EXEMPLARULID0000000084A1", "TC-1.0", "US-1"),
        make_valid_tmr_dict("01J0EXEMPLARULID0000000084A2", "TC-2.0", "US-1"),
        make_valid_tmr_dict("01J0EXEMPLARULID0000000084A3", "TC-3.0", "US-2"),
    ]
    tmr_path.write_text(json.dumps(records))

    args = [
        "gauntlet-check",
        "--session", str(session_dir),
        "--roadmap-manifest", str(roadmap_path),
        "--tmr-registry", str(tmr_path),
        "--action", "gauntlet",
        "--output", "json",
    ]

    with patch("sys.argv", args):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()

    assert exc_info.value.code == 2
    data = json.loads(mock_stdout.getvalue())
    assert data["outcome"] == "block"
    assert data["override_eligible"] is True
    assert len(data["findings"]) == 1
    assert data["findings"][0]["code"] == "duplicate_story"
    assert data["findings"][0]["target"] == {"user_story": "US-1"}

    args_with_missing_spine_override = [
        "gauntlet-check",
        "--session", str(session_dir),
        "--roadmap-manifest", str(roadmap_path),
        "--tmr-registry", str(tmr_path),
        "--action", "gauntlet",
        "--accept-missing-spine",
        "--spine-override-reason", "temporarily accept missing spine",
        "--output", "json",
    ]

    with patch("sys.argv", args_with_missing_spine_override):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()

    assert exc_info.value.code == 2
    data = json.loads(mock_stdout.getvalue())
    assert data["outcome"] == "block"
    assert data["findings"][0]["code"] == "duplicate_story"
    assert data["findings"][0]["severity"] == "blocking"


def test_tc_inv_001_tombstoned_and_also_covers_ignored_and_missing_setup_error_and_invalid_schema(
    temp_workspace: Path,
) -> None:
    """TC-INV-001: Tombstoned/also_covers ignored, uncovered stories detected (exit 2).

    Also checks missing files setup error (exit 5) and invalid schema (exit 3).
    """
    session_dir = temp_workspace / "session"
    session_dir.mkdir()

    (session_dir / "session-state.json").write_text(
        json.dumps({"active_session_id": "session_inv"})
    )

    roadmap_path = temp_workspace / "roadmap-manifest.json"
    roadmap_path.write_text(json.dumps({"user_stories": ["US-1", "US-2", "US-3"]}))

    tmr_path = temp_workspace / "tmr-registry.json"
    records = [
        # US-1 has active spine
        make_valid_tmr_dict("01J0EXEMPLARULID00000000INVA", "TC-1.0", "US-1"),
        # US-2 has tombstoned spine (ignored, so US-2 is uncovered)
        make_valid_tmr_dict("01J0EXEMPLARULID00000000INVB", "TC-2.0", "US-2", status="tombstoned"),
        # US-3 is only covered via also_covers (ignored, so US-3 is uncovered)
        make_valid_tmr_dict(
            "01J0EXEMPLARULID00000000INVC", "TC-3.0", "US-1", also_covers=["US-3"]
        ),
    ]
    tmr_path.write_text(json.dumps(records))

    # Sub-test 1: Tombstoned/also_covers ignored, uncovered detected -> block (exit 2)
    args_run = [
        "gauntlet-check",
        "--session", str(session_dir),
        "--roadmap-manifest", str(roadmap_path),
        "--tmr-registry", str(tmr_path),
        "--action", "gauntlet",
        "--output", "json",
    ]
    with patch("sys.argv", args_run):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()
    assert exc_info.value.code == 2
    data = json.loads(mock_stdout.getvalue())
    assert data["outcome"] == "block"
    uncovered_stories = [f["target"]["user_story"] for f in data["findings"] if f["code"] == "uncovered_story"]
    # US-2 and US-3 must be uncovered
    assert "US-2" in uncovered_stories
    assert "US-3" in uncovered_stories

    # Sub-test 2: Missing manifest -> setup_error (exit 5)
    args_missing = [
        "gauntlet-check",
        "--session", str(session_dir),
        "--roadmap-manifest", str(temp_workspace / "nonexistent-roadmap.json"),
        "--tmr-registry", str(tmr_path),
        "--action", "gauntlet",
        "--output", "json",
    ]
    with patch("sys.argv", args_missing):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()
    assert exc_info.value.code == 5
    data = json.loads(mock_stdout.getvalue())
    assert data["outcome"] == "setup_error"

    # Sub-test 3: Invalid schema -> schema_error (exit 3)
    # TMR registry is not valid JSON
    tmr_path_invalid = temp_workspace / "tmr-registry-invalid.json"
    tmr_path_invalid.write_text("{invalid json}")

    args_invalid_schema = [
        "gauntlet-check",
        "--session", str(session_dir),
        "--roadmap-manifest", str(roadmap_path),
        "--tmr-registry", str(tmr_path_invalid),
        "--action", "gauntlet",
        "--output", "json",
    ]
    with patch("sys.argv", args_invalid_schema):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()
    assert exc_info.value.code == 3
    data = json.loads(mock_stdout.getvalue())
    assert data["outcome"] == "schema_error"
