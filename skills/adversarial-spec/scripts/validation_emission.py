#!/usr/bin/env python3
"""validation_emission.py — validation-leg production-line CLI (spec card 5604).

Doc-driven process, code-checked shapes: the sibling of ``mini_spec_emission.py``
for the system-altitude validation leg. The conductor LLM writes scenario /
oracle / summary prose; this module validates shapes and mechanizes the close —
it never generates prose and never judges (spec NG3).

Contract (spec §7, gauntlet FM-5 / INV-A3):
- Every invocation prints exactly ONE stdout JSON envelope::

    {"status": "ok|issues|reprompt|error", "code": "<stable code|null>",
     "issues": [{"code": "...", "row_id": "<id|null>", "detail": "..."}],
     "data": {...}}

- Human-readable warnings/diagnostics go to stderr ONLY.
- Exit codes: 0 = ok; 2 = validation issues (incl. reprompt); 3 =
  environment/IO/lock/corrupt.
- Global (non-row) issues carry ``row_id: null``.
- JSON artifacts are stamped with ``schema_version`` + ``module_version``
  (``__version__`` + git short hash) and UTC RFC3339 ``Z`` timestamps
  (OP-3, OP-4, DD-6).

Stable error codes live in spec §10; ``NOT_IMPLEMENTED`` is a skeleton-only
transitional code that disappears as components C-1.2 … C-4.6 land.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

__version__ = "0.1.0"

#: Stamped on every JSON artifact this module writes (OP-4).
SCHEMA_VERSION = 1

ENVELOPE_STATUSES = ("ok", "issues", "reprompt", "error")

EXIT_OK = 0
EXIT_ISSUES = 2
EXIT_ENV = 3

_STATUS_EXIT = {
    "ok": EXIT_OK,
    "issues": EXIT_ISSUES,
    "reprompt": EXIT_ISSUES,
    "error": EXIT_ENV,
}

#: The 13 subcommands of spec §7, in documentation order.
SUBCOMMANDS = (
    "derive-conops",
    "normalize-rows",
    "check-rows",
    "record-evidence",
    "self-check",
    "assemble-digest",
    "record-send",
    "cancel-batch",
    "reset-failed",
    "supersede-row",
    "parse-reply",
    "emit-system-validation",
    "status",
)

#: Which execution-plan component delivers each subcommand (skeleton stubs
#: name their owner so a NOT_IMPLEMENTED envelope routes the reader).
_DELIVERED_BY = {
    "derive-conops": "C-2.1",
    "normalize-rows": "C-2.2",
    "check-rows": "C-2.3",
    "record-evidence": "C-3.1",
    "assemble-digest": "C-3.2",
    "record-send": "C-3.3",
    "cancel-batch": "C-3.3",
    "parse-reply": "C-4.1/C-4.2",
    "reset-failed": "C-4.3",
    "supersede-row": "C-4.3",
    "emit-system-validation": "C-4.4",
    "self-check": "C-4.5",
    "status": "C-4.6",
}

_GIT_HASH_RE = re.compile(r"^[0-9a-f]{4,40}$")


# ── Envelope primitives (INV-A3) ─────────────────────────────────────────────


def exit_code_for_status(status: str) -> int:
    """Map an envelope status to the CLI exit code (spec §7 contract)."""
    try:
        return _STATUS_EXIT[status]
    except KeyError:
        raise ValueError(f"unknown envelope status: {status!r}") from None


def make_issue(code: str, detail: str, row_id: str | None = None) -> dict[str, Any]:
    """One issue entry; global (non-row) issues carry row_id null."""
    return {"code": code, "row_id": row_id, "detail": detail}


@dataclass
class Envelope:
    """The single stdout JSON object every invocation prints (FM-5)."""

    status: str
    code: str | None = None
    issues: list[dict[str, Any]] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "code": self.code,
            "issues": self.issues,
            "data": self.data,
        }

    @property
    def exit_code(self) -> int:
        return exit_code_for_status(self.status)


# ── Artifact stamping (OP-3, OP-4, DD-6) ─────────────────────────────────────


def utc_now() -> str:
    """UTC RFC3339 with Z suffix — the only timestamp format this module emits."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git_short_hash() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except OSError:
        return "unknown"
    candidate = proc.stdout.strip()
    if proc.returncode == 0 and _GIT_HASH_RE.match(candidate):
        return candidate
    return "unknown"


def module_version() -> str:
    """``__version__`` + git short hash, e.g. ``0.1.0+b6bb7d4`` (DD-6)."""
    return f"{__version__}+{_git_short_hash()}"


def stamp_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``artifact`` carrying the provenance stamp (OP-4)."""
    stamped = dict(artifact)
    stamped["schema_version"] = SCHEMA_VERSION
    stamped["module_version"] = module_version()
    stamped["generated_at"] = utc_now()
    return stamped


# ── CLI boundary ─────────────────────────────────────────────────────────────


class CliArgumentError(Exception):
    """Raised instead of argparse's SystemExit so the boundary can answer
    with an envelope (AC-2: every invocation prints one)."""

    def __init__(self, message: str, code: str = "INVALID_ARGUMENTS") -> None:
        super().__init__(message)
        self.code = code


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Any:  # noqa: D102 — argparse override
        code = "UNKNOWN_SUBCOMMAND" if "invalid choice" in message else "INVALID_ARGUMENTS"
        raise CliArgumentError(message, code)


def _not_implemented(name: str) -> Callable[[argparse.Namespace], Envelope]:
    component = _DELIVERED_BY[name]

    def handler(_args: argparse.Namespace) -> Envelope:
        return Envelope(
            status="error",
            code="NOT_IMPLEMENTED",
            issues=[
                make_issue(
                    "NOT_IMPLEMENTED",
                    f"'{name}' lands with component {component}; "
                    "the C-1.1 skeleton provides dispatch + envelope only",
                )
            ],
        )

    return handler


#: Subcommand → handler. Components C-1.2 … C-4.6 replace stubs in place.
HANDLERS: dict[str, Callable[[argparse.Namespace], Envelope]] = {
    name: _not_implemented(name) for name in SUBCOMMANDS
}


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="validation_emission.py",
        description=__doc__.splitlines()[0],
        add_help=True,
    )
    subparsers = parser.add_subparsers(
        dest="subcommand", required=True, parser_class=_Parser
    )
    for name in SUBCOMMANDS:
        subparsers.add_parser(name, add_help=True)
    return parser


def _emit(envelope: Envelope) -> int:
    print(json.dumps(envelope.as_dict(), ensure_ascii=False))
    return envelope.exit_code


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args, extras = parser.parse_known_args(argv)
    except CliArgumentError as exc:
        return _emit(
            Envelope("issues", exc.code, issues=[make_issue(exc.code, str(exc))])
        )
    if extras:
        print(
            f"warning: ignoring unrecognized arguments: {' '.join(extras)}",
            file=sys.stderr,
        )
    handler = HANDLERS[args.subcommand]
    try:
        envelope = handler(args)
    except Exception as exc:  # noqa: BLE001 — boundary: stdout stays an envelope
        print(f"error: {exc}", file=sys.stderr)
        envelope = Envelope(
            "error", "INTERNAL_ERROR", issues=[make_issue("INTERNAL_ERROR", str(exc))]
        )
    return _emit(envelope)


if __name__ == "__main__":
    sys.exit(main())
