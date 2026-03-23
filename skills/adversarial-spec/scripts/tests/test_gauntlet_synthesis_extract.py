"""Contract tests for the gauntlet synthesis extraction tool."""

import json
from pathlib import Path

from gauntlet import synthesis_extract


def _write_run_log(path: Path, evaluations: list[dict]) -> None:
    path.write_text(
        json.dumps(
            {
                "timestamp": "2026-03-21T15:00:00",
                "spec_hash": "abcd1234",
                "result": {
                    "evaluations": evaluations,
                },
            }
        )
    )


def test_synthesis_extract_writes_header_and_sorted_full_concerns(tmp_path):
    """The output must keep full concern text and deterministic concern ordering."""
    run_log = tmp_path / "run.json"
    output = tmp_path / "synthesis.txt"
    _write_run_log(
        run_log,
        [
            {
                "concern": {
                    "id": "PEDA-2000",
                    "adversary": "pedantic_nitpicker",
                    "severity": "medium",
                    "text": "Second concern with\nmultiple lines and exact detail 12345",
                },
                "verdict": "dismissed",
                "reasoning": "not an issue",
            },
            {
                "concern": {
                    "id": "ARCH-1000",
                    "adversary": "architect",
                    "severity": "high",
                    "text": "First concern keeps every character including section §9.4 and variable foo_bar_baz",
                },
                "verdict": "accepted",
                "reasoning": "real issue",
            },
        ],
    )

    exit_code = synthesis_extract.main(
        ["--run-log", str(run_log), "--output", str(output)]
    )

    assert exit_code == 0
    content = output.read_text()
    assert "Categories (use EXACTLY these" in content
    assert "1. Correctness Bugs" in content
    assert "8. Underspecification" in content
    lines = [line for line in content.splitlines() if line.startswith("[")]
    assert lines == [
        "[ARCH-1000] architect | high | verdict=accepted | First concern keeps every character including section §9.4 and variable foo_bar_baz",
        "[PEDA-2000] pedantic_nitpicker | medium | verdict=dismissed | Second concern with multiple lines and exact detail 12345",
    ]


def test_synthesis_extract_returns_zero_for_empty_run_log(tmp_path):
    """Empty evaluation sets should still produce a valid synthesis header."""
    run_log = tmp_path / "run.json"
    output = tmp_path / "synthesis.txt"
    _write_run_log(run_log, [])

    exit_code = synthesis_extract.main(
        ["--run-log", str(run_log), "--output", str(output)]
    )

    assert exit_code == 0
    content = output.read_text()
    assert "You are synthesizing gauntlet results into the standard taxonomy." in content
    assert not any(line.startswith("[") for line in content.splitlines())


def test_synthesis_extract_returns_two_for_invalid_schema(tmp_path, capsys):
    """Malformed run logs must fail with exit code 2 instead of guessing."""
    run_log = tmp_path / "run.json"
    output = tmp_path / "synthesis.txt"
    run_log.write_text(json.dumps({"result": {"evaluations": [{"verdict": "accepted"}]}}))

    exit_code = synthesis_extract.main(
        ["--run-log", str(run_log), "--output", str(output)]
    )

    assert exit_code == 2
    assert "Invalid run log schema" in capsys.readouterr().err
    assert not output.exists()
