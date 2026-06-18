"""Dogfood fixture for the F-prime spine coverage gate."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from gauntlet_check_cli import main
from tmr_compile_step import CompileCandidate, compile_tmr_records
from tmr_parser import TmrParser

SPEC_ROOT = Path(".adversarial-spec/specs/liveness-gate-test-ladder")
ROADMAP_MANIFEST = SPEC_ROOT / "roadmap/manifest.json"
REGISTRY = SPEC_ROOT / "tmr-registry.json"
PROSE_VIEW = SPEC_ROOT / "tmr-prose-view.md"
ECHO_DIFF = SPEC_ROOT / "tmr-echo-diff.json"
CANDIDATES = SPEC_ROOT / "tmr-candidates.json"
SESSION = SPEC_ROOT / "bootstrap_fixtures/session"


def test_tc_8_0_dogfood_registry_has_one_active_spine_per_roadmap_story() -> None:
    records = TmrParser.parse_file(REGISTRY)
    roadmap = json.loads(ROADMAP_MANIFEST.read_text(encoding="utf-8"))
    roadmap_story_ids = [story["id"] for story in roadmap["user_stories"]]

    assert len(records) == 15
    assert {record.user_story for record in records} == set(roadmap_story_ids)
    assert {record.test_id for record in records} == {
        "TC-15.0",
        *(f"TC-{index}.0" for index in range(1, 15)),
    }

    for story_id in roadmap_story_ids:
        matching = [
            record
            for record in records
            if record.status == "active"
            and record.spine is True
            and record.user_story == story_id
        ]
        assert len(matching) == 1


def test_tc_8_0_dogfood_registry_is_compile_step_output() -> None:
    candidates = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    stored_registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    uid_iter = (record["tmr_uid"] for record in stored_registry)

    compiled = compile_tmr_records(
        [
            CompileCandidate(anchor=candidate["anchor"], record=candidate["record"])
            for candidate in candidates
        ],
        accessor_symbols={"dogfood_fprime_fixture"},
        uid_factory=lambda: next(uid_iter),
    )

    assert compiled.records == stored_registry
    assert PROSE_VIEW.read_text(encoding="utf-8") == compiled.prose_view

    clean_echo = compile_tmr_records(
        [
            CompileCandidate(anchor=candidate["anchor"], record=record)
            for candidate, record in zip(candidates, stored_registry, strict=True)
        ],
        existing_records=stored_registry,
        accessor_symbols={"dogfood_fprime_fixture"},
    )
    assert clean_echo.echo_diff == []
    assert json.loads(ECHO_DIFF.read_text(encoding="utf-8")) == []


def test_tc_inv_001_dogfood_fprime_passes_against_rich_roadmap_manifest() -> None:
    args = [
        "gauntlet-check",
        "--session",
        str(SESSION),
        "--roadmap-manifest",
        str(ROADMAP_MANIFEST),
        "--tmr-registry",
        str(REGISTRY),
        "--action",
        "gauntlet",
        "--output",
        "json",
    ]

    with patch("sys.argv", args):
        with patch("sys.stdout", new_callable=StringIO) as stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()

    assert exc_info.value.code == 0
    data = json.loads(stdout.getvalue())
    assert data == {"outcome": "pass", "findings": [], "override_eligible": False}
