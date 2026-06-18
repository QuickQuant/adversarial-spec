#!/usr/bin/env python3
"""CLI script for checking gauntlet and spine coverage (W1-1)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from gate_result import (
    GateFinding,
    GateResult,
    coverage_block,
    pass_result,
    schema_error,
    setup_error,
    warn_result,
)
from pydantic import ValidationError
from spine_coverage_checker import SpineCoverageChecker
from tmr_parser import TmrParser
from tmr_schema import SchemaValidationError


def main() -> None:
    parser = argparse.ArgumentParser(description="Gauntlet spine coverage checker.")
    parser.add_argument("--session", required=True, help="Session directory")
    parser.add_argument("--roadmap-manifest", required=True, help="Roadmap manifest JSON path")
    parser.add_argument("--tmr-registry", required=True, help="TMR registry JSON path")
    parser.add_argument("--action", required=True, help="Action (critique or gauntlet)")
    parser.add_argument("--output", help="Output format (e.g., json)")
    parser.add_argument("--accept-missing-spine", action="store_true", help="Accept missing spine flag")
    parser.add_argument("--spine-override-reason", help="Spine override reason")
    parser.add_argument("--contract-version", default="tmr.v1", help="Contract version")

    args = parser.parse_args()

    # 1. Path containment check
    root = Path.cwd().resolve()
    for arg_name, path_str in [
        ("--session", args.session),
        ("--roadmap-manifest", args.roadmap_manifest),
        ("--tmr-registry", args.tmr_registry),
    ]:
        p = Path(path_str).resolve()
        try:
            p.relative_to(root)
        except ValueError:
            finding = GateFinding(
                code="setup_error",
                message=f"Path containment violation: path {path_str} escapes the workspace root {root}",
                severity="blocking",
                target={"path": path_str}
            )
            result = setup_error([finding])
            write_result_and_exit(result, args.output)

    # 2. Check file/directory existence
    session_path = Path(args.session).resolve()
    roadmap_path = Path(args.roadmap_manifest).resolve()
    tmr_path = Path(args.tmr_registry).resolve()

    if not session_path.is_dir():
        finding = GateFinding(
            code="setup_error",
            message=f"Session path {args.session} is not a directory",
            severity="blocking",
            target={"session": args.session}
        )
        result = setup_error([finding])
        write_result_and_exit(result, args.output)

    session_state_path = session_path / "session-state.json"
    if not session_state_path.is_file():
        finding = GateFinding(
            code="setup_error",
            message=f"session-state.json is missing in {args.session}",
            severity="blocking",
            target={"session_state": str(session_state_path)}
        )
        result = setup_error([finding])
        write_result_and_exit(result, args.output)

    if not roadmap_path.is_file():
        finding = GateFinding(
            code="setup_error",
            message=f"Roadmap manifest file missing at {args.roadmap_manifest}",
            severity="blocking",
            target={"roadmap_manifest": args.roadmap_manifest}
        )
        result = setup_error([finding])
        write_result_and_exit(result, args.output)

    if not tmr_path.is_file():
        finding = GateFinding(
            code="setup_error",
            message=f"TMR registry file missing at {args.tmr_registry}",
            severity="blocking",
            target={"tmr_registry": args.tmr_registry}
        )
        result = setup_error([finding])
        write_result_and_exit(result, args.output)

    # 3. Parse session-state.json to get active_session_id
    try:
        with open(session_state_path, "r", encoding="utf-8") as f:
            session_data = json.load(f)
        if not isinstance(session_data, dict):
            raise ValueError("session-state.json must be a JSON object")
        active_session_id = session_data.get("active_session_id")
        if not active_session_id or not isinstance(active_session_id, str):
            raise ValueError("active_session_id must be a non-empty string")
    except Exception as exc:
        finding = GateFinding(
            code="setup_error",
            message=f"Failed to read/parse active_session_id from session-state.json: {exc}",
            severity="blocking",
            target={"path": str(session_state_path)}
        )
        result = setup_error([finding])
        write_result_and_exit(result, args.output)

    # 4. Parse --roadmap-manifest
    try:
        with open(roadmap_path, "r", encoding="utf-8") as f:
            roadmap_data = json.load(f)
        if not isinstance(roadmap_data, dict) or "user_stories" not in roadmap_data:
            raise ValueError("Missing 'user_stories' key in roadmap manifest")
        roadmap_user_stories = roadmap_data["user_stories"]
        if not isinstance(roadmap_user_stories, list):
            raise ValueError("'user_stories' must be a list")
        for idx, story in enumerate(roadmap_user_stories):
            if not isinstance(story, str):
                raise ValueError(f"User story at index {idx} must be a string")
    except json.JSONDecodeError as exc:
        finding = GateFinding(
            code="schema_error",
            message=f"Invalid JSON in roadmap manifest: {exc}",
            severity="blocking",
            target={"path": str(roadmap_path)}
        )
        result = schema_error([finding])
        write_result_and_exit(result, args.output)
    except Exception as exc:
        finding = GateFinding(
            code="schema_error",
            message=f"Invalid roadmap manifest structure: {exc}",
            severity="blocking",
            target={"path": str(roadmap_path)}
        )
        result = schema_error([finding])
        write_result_and_exit(result, args.output)

    # 5. Parse --tmr-registry using TmrParser.parse_file(path)
    try:
        tmr_records = TmrParser.parse_file(tmr_path)
    except SchemaValidationError as exc:
        finding = GateFinding(
            code="schema_error",
            message=str(exc),
            severity="blocking",
            target={"field": getattr(exc, "field", "<unknown>")}
        )
        result = schema_error([finding])
        write_result_and_exit(result, args.output)
    except ValidationError as exc:
        findings = []
        for error in exc.errors():
            field = ".".join(str(p) for p in error.get("loc", ())) or "<record>"
            findings.append(
                GateFinding(
                    code="schema_error",
                    message=error.get("msg", str(exc)),
                    severity="blocking",
                    target={"field": field}
                )
            )
        result = schema_error(findings)
        write_result_and_exit(result, args.output)

    # 6. Perform spine coverage check
    coverage_result = SpineCoverageChecker.check(
        roadmap_user_stories, tmr_records, phase=args.action
    )

    if not coverage_result.passed:
        # Construct findings for coverage check failure
        findings = []
        is_blocking = (args.action == "gauntlet" and not args.accept_missing_spine)
        severity = "blocking" if is_blocking else "warning"

        for story in coverage_result.uncovered:
            findings.append(
                GateFinding(
                    code="uncovered_story",
                    message=f"User story '{story}' has no active spine designation",
                    severity=severity,
                    target={"user_story": story}
                )
            )
        for story in coverage_result.duplicate:
            findings.append(
                GateFinding(
                    code="duplicate_story",
                    message=f"User story '{story}' has duplicate active spine designations",
                    severity=severity,
                    target={"user_story": story}
                )
            )

        if args.action == "critique":
            result = warn_result(findings)
            write_result_and_exit(result, args.output)
        elif args.action == "gauntlet":
            if args.accept_missing_spine:
                reason = args.spine_override_reason
                if not reason or not isinstance(reason, str) or not reason.strip():
                    finding = GateFinding(
                        code="setup_error",
                        message="--accept-missing-spine requires a non-empty, non-whitespace --spine-override-reason",
                        severity="blocking",
                        target={"spine_override_reason": reason}
                    )
                    result = setup_error([finding])
                    write_result_and_exit(result, args.output)

                # Write override log to {session_dir}/sessions/{active_session_id}.decisions.log
                log_dir = session_path / "sessions"
                log_dir.mkdir(parents=True, exist_ok=True)
                log_file = log_dir / f"{active_session_id}.decisions.log"
                timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                log_line = f"{timestamp} [gauntlet-check] override missing spine; reason: {reason!r}\n"
                try:
                    with open(log_file, "a", encoding="utf-8") as lf:
                        lf.write(log_line)
                except Exception as exc:
                    finding = GateFinding(
                        code="setup_error",
                        message=f"Failed to write override log to decisions.log: {exc}",
                        severity="blocking",
                        target={"log_file": str(log_file)}
                    )
                    result = setup_error([finding])
                    write_result_and_exit(result, args.output)

                result = warn_result(findings)
                write_result_and_exit(result, args.output)
            else:
                result = coverage_block(findings)
                write_result_and_exit(result, args.output)
    else:
        result = pass_result()
        write_result_and_exit(result, args.output)


def write_result_and_exit(result: GateResult, output_format: str | None) -> None:
    if output_format == "json":
        sys.stdout.write(json.dumps(result.to_envelope()) + "\n")
    else:
        # Write user-friendly text message to stderr/stdout
        for finding in result.findings:
            sys.stderr.write(f"[{finding.severity.upper()}] {finding.message}\n")
        sys.stderr.write(f"Outcome: {result.outcome}\n")
    sys.exit(result.exit_code())


if __name__ == "__main__":
    main()
