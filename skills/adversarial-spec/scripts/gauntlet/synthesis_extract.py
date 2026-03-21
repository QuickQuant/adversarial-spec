"""Extract gauntlet run logs into synthesis input text."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from gauntlet.core_types import SYNTHESIS_CATEGORIES

_CATEGORY_DESCRIPTIONS = {
    "Correctness Bugs": "implementation contradictions, data integrity, logic errors",
    "Race Conditions": "concurrency, ordering, lease violations",
    "Failure Modes": "recovery cascades, degraded mode, cold start",
    "Security": "injection, enumeration, PII leakage, auth bypass",
    "Operability": "monitoring, deployment, retention, memory budgets",
    "Scalability": "fan-out storms, thundering herds, unbounded operations",
    "Design Debt": "over-scoping, modularity, unnecessary complexity",
    "Underspecification": "missing details that block implementation",
}


class InvalidRunLogSchemaError(ValueError):
    """Raised when the persisted gauntlet run log is missing required fields."""


def _build_header() -> str:
    lines = [
        "You are synthesizing gauntlet results into the standard taxonomy.",
        "",
        "Categories (use EXACTLY these - do not invent new ones):",
    ]
    for idx, category in enumerate(SYNTHESIS_CATEGORIES, start=1):
        lines.append(f"{idx}. {category} - {_CATEGORY_DESCRIPTIONS[category]}")
    lines.extend(
        [
            "",
            "For each concern: assign ONE primary category, verdict (accept/acknowledge/dismiss), one-line summary.",
            "Group by category in output. Do NOT pre-filter by pipeline verdict - evaluate ALL concerns.",
        ]
    )
    return "\n".join(lines)


def _load_run_log(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidRunLogSchemaError(str(exc)) from exc
    if not isinstance(data, dict):
        raise InvalidRunLogSchemaError("top-level payload must be an object")
    return data


def _get_evaluations(run_log: dict[str, Any]) -> list[dict[str, Any]]:
    result = run_log.get("result")
    if not isinstance(result, dict):
        raise InvalidRunLogSchemaError("missing result object")

    evaluations = result.get("evaluations")
    if not isinstance(evaluations, list):
        raise InvalidRunLogSchemaError("result.evaluations must be a list")

    validated: list[dict[str, Any]] = []
    for index, evaluation in enumerate(evaluations):
        if not isinstance(evaluation, dict):
            raise InvalidRunLogSchemaError(f"evaluation {index} must be an object")

        concern = evaluation.get("concern")
        if not isinstance(concern, dict):
            raise InvalidRunLogSchemaError(f"evaluation {index} missing concern object")

        verdict = evaluation.get("verdict")
        if not isinstance(verdict, str):
            raise InvalidRunLogSchemaError(f"evaluation {index} missing verdict string")

        required_fields = ("id", "adversary", "severity", "text")
        for field in required_fields:
            value = concern.get(field)
            if not isinstance(value, str):
                raise InvalidRunLogSchemaError(
                    f"evaluation {index} concern missing {field} string"
                )

        validated.append(evaluation)

    return validated


def _flatten_text(text: str) -> str:
    return " ".join(text.splitlines())


def _format_concern_lines(evaluations: list[dict[str, Any]]) -> list[str]:
    entries: list[tuple[str, str]] = []
    for evaluation in evaluations:
        concern = evaluation["concern"]
        line = (
            f"[{concern['id']}] {concern['adversary']} | {concern['severity']} | "
            f"verdict={evaluation['verdict']} | {_flatten_text(concern['text'])}"
        )
        entries.append((concern["id"], line))
    entries.sort(key=lambda item: item[0])
    return [line for _, line in entries]


def build_synthesis_input(run_log: dict[str, Any]) -> str:
    """Convert a saved gauntlet run log into synthesis input text."""
    evaluations = _get_evaluations(run_log)
    lines = [_build_header()]
    concern_lines = _format_concern_lines(evaluations)
    if concern_lines:
        lines.extend(["", *concern_lines])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for synthesis extraction."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-log", required=True, help="Path to saved gauntlet run JSON")
    parser.add_argument("--output", required=True, help="Path to write synthesis input text")
    args = parser.parse_args(argv)

    try:
        run_log = _load_run_log(Path(args.run_log))
        output_text = build_synthesis_input(run_log)
    except InvalidRunLogSchemaError as exc:
        print(f"Invalid run log schema: {exc}", file=sys.stderr)
        return 2

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
