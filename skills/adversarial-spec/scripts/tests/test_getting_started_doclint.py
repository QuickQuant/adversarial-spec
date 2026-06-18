"""Getting Started bootstrap doc lint and fixture validation."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from gauntlet_check_cli import main as gauntlet_check_main

ROOT = Path(__file__).resolve().parents[4]
SPEC = ROOT / ".adversarial-spec/specs/liveness-gate-test-ladder/spec.md"
FIXTURES = ROOT / ".adversarial-spec/specs/liveness-gate-test-ladder/bootstrap_fixtures"


def run_gauntlet_check(tmr_registry: Path) -> tuple[int, dict]:
    args = [
        "gauntlet-check",
        "--session",
        str(FIXTURES / "session"),
        "--roadmap-manifest",
        str(FIXTURES / "roadmap-manifest.json"),
        "--tmr-registry",
        str(tmr_registry),
        "--action",
        "gauntlet",
        "--output",
        "json",
    ]
    with patch("sys.argv", args):
        with patch("sys.stdout", new_callable=StringIO) as stdout:
            with pytest.raises(SystemExit) as exc_info:
                gauntlet_check_main()
    return int(exc_info.value.code), json.loads(stdout.getvalue())


def getting_started_section() -> str:
    text = SPEC.read_text(encoding="utf-8")
    start = text.index("## 2. Getting Started (bootstrap)")
    end = text.index("### 2.1 Lifecycle", start)
    return text[start:end]


def test_tc_15_0_documented_bootstrap_fixtures_reach_pass_and_exit_2():
    full_exit, full_result = run_gauntlet_check(FIXTURES / "tmr-registry-full.json")
    missing_exit, missing_result = run_gauntlet_check(
        FIXTURES / "tmr-registry-missing-spine.json"
    )

    assert full_exit == 0
    assert full_result["outcome"] == "pass"
    assert missing_exit == 2
    assert missing_result["outcome"] == "block"
    assert missing_result["findings"][0]["target"] == {"user_story": "US-2"}


def test_tc_15_0_getting_started_names_the_checked_fixture_commands():
    section = getting_started_section()
    for token in (
        "uv run gauntlet-check",
        "bootstrap_fixtures/session",
        "bootstrap_fixtures/roadmap-manifest.json",
        "tmr-registry-full.json",
        "tmr-registry-missing-spine.json",
        "exit 0",
        "exit 2",
        "US-2",
    ):
        assert token in section


def test_tc_15_1_symlink_live_edits_and_no_affirmative_copy_deploy():
    section = getting_started_section()
    assert "~/.claude/skills/adversarial-spec" in section
    assert "symlink" in section.lower()
    assert "Edits to source are live immediately" in section
    assert "NO copy step" in section

    for line in section.splitlines():
        if "cp -r" not in line or "~/.claude/skills" not in line:
            continue
        lowered = line.lower()
        assert any(guard in lowered for guard in ("do **not**", "do not", "never"))
