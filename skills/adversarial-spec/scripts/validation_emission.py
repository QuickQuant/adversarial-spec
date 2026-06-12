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
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from filelock import FileLock, Timeout

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


# ── Path containment + input bounds (SEC-9, SEC-10) ──────────────────────────

#: Input byte budgets (spec §11, SEC-10). Sizes are UTF-8 BYTES, not characters.
REPLY_MAX_BYTES = 16 * 1024
JUSTIFICATION_MAX_BYTES = 2 * 1024
LEDGER_MAX_BYTES = 5 * 1024 * 1024
CONOPS_MAX_BYTES = 1024 * 1024

_INPUT_BOUNDS = {
    "reply": REPLY_MAX_BYTES,
    "justification": JUSTIFICATION_MAX_BYTES,
    "ledger": LEDGER_MAX_BYTES,
    "conops": CONOPS_MAX_BYTES,
}


class ValidationIssuesError(Exception):
    """Validation-class failure → exit 2 ``issues`` envelope at the boundary."""

    def __init__(self, code: str, issues: list[dict[str, Any]]) -> None:
        self.code = code
        self.issues = issues
        super().__init__(issues[0]["detail"] if issues else code)


def resolve_under_root(spec_root: Path, candidate: str | Path) -> Path:
    """Resolve an artifact path and require containment under the spec root.

    realpath both sides (the session.py is_relative_to pattern) so ``..``
    segments AND symlink escapes are rejected (SEC-9).
    """
    root_real = Path(spec_root).resolve()
    candidate_path = Path(candidate)
    if not candidate_path.is_absolute():
        candidate_path = root_real / candidate_path
    resolved = candidate_path.resolve()
    if not resolved.is_relative_to(root_real):
        raise ValidationIssuesError(
            "PATH_OUTSIDE_ROOT",
            [
                make_issue(
                    "PATH_OUTSIDE_ROOT",
                    f"artifact path escapes the spec root: {candidate} "
                    f"(resolved {resolved}, root {root_real})",
                )
            ],
        )
    return resolved


def enforce_input_bounds(kind: str, data: bytes | str) -> None:
    """Reject inputs over their byte budget (SEC-10) with a structured exit-2.

    Unknown ``kind`` is a programming error, not a validation issue.
    """
    try:
        limit = _INPUT_BOUNDS[kind]
    except KeyError:
        raise ValueError(f"unknown input-bounds kind: {kind!r}") from None
    size = len(data.encode("utf-8")) if isinstance(data, str) else len(data)
    if size > limit:
        raise ValidationIssuesError(
            "INPUT_BOUNDS_EXCEEDED",
            [
                make_issue(
                    "INPUT_BOUNDS_EXCEEDED",
                    f"{kind} input is {size} bytes, over the {limit}-byte budget",
                )
            ],
        )


def find_duplicate_row_ids(ledger: dict[str, Any]) -> list[str]:
    """row_id must be globally unique across active rows AND superseded
    snapshots (spec §3); returns duplicates in first-seen order."""
    seen: set[str] = set()
    duplicates: list[str] = []
    active_ids = (row.get("row_id") for row in ledger.get("rows", []))
    superseded_ids = (
        entry.get("row_snapshot", {}).get("row_id")
        for entry in ledger.get("superseded", [])
    )
    for row_id in (*active_ids, *superseded_ids):
        if not row_id:
            continue
        if row_id in seen and row_id not in duplicates:
            duplicates.append(row_id)
        seen.add(row_id)
    return duplicates


def find_duplicate_story_ids(story_ids: Any) -> list[str]:
    """Duplicate manifest story ids are a derivation error → exit 2 (SEC-9
    adjacent, spec §6.1); returns duplicates in first-seen order."""
    seen: set[str] = set()
    duplicates: list[str] = []
    for story_id in story_ids:
        if story_id in seen and story_id not in duplicates:
            duplicates.append(story_id)
        seen.add(story_id)
    return duplicates


# ── Hash canonicalization (INV-12, SEC-8, FM-3) ──────────────────────────────
#
# Hashes are computed ONLY by this module — the conductor never writes hex by
# hand (CB-7). Full 64-hex digests are stored; 12-hex prefixes appear only at
# the artifact boundary via hash_prefix() (SEC-8).

#: Minimum (and default) prefix length at the artifact boundary (SEC-8).
HASH_PREFIX_LEN = 12

#: The four row fields that feed row_hash, in canonical order. Everything else
#: — evidence_rationale, test_targets, summaries — is EXCLUDED (TC-2.6).
ROW_HASH_FIELDS = ("conops_ref", "scenario", "oracle", "evidence_type")

_FULL_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_STORY_HEADING_RE = re.compile(r"^### (US-\d+)\b", re.MULTILINE)


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def compute_row_hash(
    conops_ref: str, scenario: str, oracle: str, evidence_type: str
) -> str:
    """spec §6.2 canonicalization: sha256 over the NFC-normalized 4-field list
    in json.dumps list form (ensure_ascii=False, separators=(",",":"))."""
    payload = json.dumps(
        [_nfc(conops_ref), _nfc(scenario), _nfc(oracle), _nfc(evidence_type)],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def row_hash_for(row: dict[str, Any]) -> str:
    """Compute row_hash from a row dict; missing canonical fields are an error."""
    missing = [name for name in ROW_HASH_FIELDS if not isinstance(row.get(name), str)]
    if missing:
        raise ValueError(f"row is missing canonical hash fields: {', '.join(missing)}")
    return compute_row_hash(*(row[name] for name in ROW_HASH_FIELDS))


def compute_conops_hash(conops_bytes: bytes) -> str:
    """Full-file conops_hash: sha256 of conops.md bytes (spec §6.1)."""
    return hashlib.sha256(conops_bytes).hexdigest()


def compute_story_hashes(conops_text: str) -> dict[str, str]:
    """Per-story hashes: sha256 over each ``### US-n`` section's bytes, heading
    through the next US heading (or EOF). Evidence binds per story, so editing
    one story invalidates only that story's evidence (spec §6.1, FM-3)."""
    matches = list(_STORY_HEADING_RE.finditer(conops_text))
    hashes: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(conops_text)
        section = conops_text[match.start() : end]
        hashes[match.group(1)] = hashlib.sha256(section.encode("utf-8")).hexdigest()
    return hashes


def hash_prefix(full_hash: str, length: int = HASH_PREFIX_LEN) -> str:
    """Artifact-boundary prefix of a FULL stored hash. Prefixes shorter than
    HASH_PREFIX_LEN are rejected (SEC-8 — self-check mirrors this)."""
    if not _FULL_HASH_RE.match(full_hash):
        raise ValueError("hash_prefix requires a full 64-hex sha256")
    if length < HASH_PREFIX_LEN:
        raise ValueError(
            f"hash prefix length {length} below minimum {HASH_PREFIX_LEN} (SEC-8)"
        )
    return full_hash[:length]


# ── Ledger I/O: lock + atomic write + corrupt quarantine (INV-A2, FM-7) ─────

#: spec §7 (R3 convergent): FileLock timeout before LEDGER_BUSY.
LEDGER_LOCK_TIMEOUT_S = 10.0

_CORRUPT_TS_FORMAT = "%Y%m%dT%H%M%SZ"


class LedgerBusyError(Exception):
    """Lock not acquired within the timeout → exit 3 ``LEDGER_BUSY``."""

    def __init__(
        self,
        lock_path: Path,
        owner_pid: int | None = None,
        lock_age_s: float | None = None,
    ) -> None:
        self.lock_path = Path(lock_path)
        self.owner_pid = owner_pid
        self.lock_age_s = lock_age_s
        owner = f"owner pid {owner_pid}" if owner_pid is not None else "owner unknown"
        age = f"lock age {lock_age_s:.1f}s" if lock_age_s is not None else "lock age unknown"
        super().__init__(f"ledger lock busy ({owner}; {age}): {self.lock_path}")


class LedgerCorruptError(Exception):
    """Unparseable ledger → exit 3 ``LEDGER_CORRUPT``; bytes quarantined first,
    the ledger itself is NEVER auto-repaired (restore from git — spec §7)."""

    def __init__(self, ledger_path: Path, quarantine_path: Path) -> None:
        self.ledger_path = Path(ledger_path)
        self.quarantine_path = Path(quarantine_path)
        super().__init__(
            f"ledger unparseable: {self.ledger_path}; "
            f"corrupt bytes copied to {self.quarantine_path}; restore from git"
        )


def _ledger_lock_path(ledger_path: Path) -> Path:
    return Path(f"{ledger_path}.lock")


def _lock_owner_path(lock_path: Path) -> Path:
    return Path(f"{lock_path}.owner")


def _read_lock_diagnostics(lock_path: Path) -> tuple[int | None, float | None]:
    """Best-effort owner pid + lock age for the LEDGER_BUSY detail ("when readable")."""
    owner_pid: int | None = None
    lock_age_s: float | None = None
    try:
        owner = json.loads(_lock_owner_path(lock_path).read_text(encoding="utf-8"))
        if isinstance(owner.get("pid"), int):
            owner_pid = owner["pid"]
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        pass
    try:
        lock_age_s = max(0.0, time.time() - lock_path.stat().st_mtime)
    except OSError:
        pass
    return owner_pid, lock_age_s


def _quarantine_corrupt(ledger_path: Path, raw: bytes) -> Path:
    """Copy corrupt bytes aside FIRST (forensics); never touch the ledger."""
    stamp = datetime.now(timezone.utc).strftime(_CORRUPT_TS_FORMAT)
    quarantine = ledger_path.with_name(f"{ledger_path.name}.corrupt-{stamp}")
    quarantine.write_bytes(raw)
    return quarantine


def _parse_ledger(ledger_path: Path) -> dict[str, Any]:
    raw = ledger_path.read_bytes()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        quarantine = _quarantine_corrupt(ledger_path, raw)
        raise LedgerCorruptError(ledger_path, quarantine) from None
    if not isinstance(data, dict):
        quarantine = _quarantine_corrupt(ledger_path, raw)
        raise LedgerCorruptError(ledger_path, quarantine)
    return data


def read_ledger(ledger_path: Path) -> dict[str, Any]:
    """Read-only ledger access — no lock file, no write path (INV-A2).

    Atomic rename on the write side guarantees readers never see torn bytes.
    """
    return _parse_ledger(Path(ledger_path))


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Same-directory tmp + fsync + os.replace (the gauntlet/persistence.py
    pattern). Crash mid-write leaves the prior file intact and no .tmp litter.
    Durability scope is process death, not power loss (spec §7 / AUDT)."""
    tmp = tempfile.NamedTemporaryFile(
        dir=path.parent, delete=False, suffix=".tmp", mode="w", encoding="utf-8"
    )
    try:
        json.dump(data, tmp, indent=2, ensure_ascii=False)
        tmp.write("\n")
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, path)
    except Exception:
        try:
            tmp.close()
        except OSError:
            pass
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        raise


def mutate_ledger(
    ledger_path: Path,
    mutator: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    timeout_s: float = LEDGER_LOCK_TIMEOUT_S,
) -> dict[str, Any]:
    """THE single mutation helper (INV-A2): read → mutate → atomic tmp+rename,
    all INSIDE ``validation-rows.json.lock``. The eight mutating subcommands
    route through here; nothing else writes the ledger."""
    ledger_path = Path(ledger_path)
    lock_path = _ledger_lock_path(ledger_path)
    lock = FileLock(str(lock_path))
    try:
        lock.acquire(timeout=timeout_s)
    except Timeout:
        owner_pid, lock_age_s = _read_lock_diagnostics(lock_path)
        raise LedgerBusyError(lock_path, owner_pid, lock_age_s) from None
    owner_path = _lock_owner_path(lock_path)
    try:
        try:
            owner_path.write_text(
                json.dumps({"pid": os.getpid(), "acquired_at": utc_now()}),
                encoding="utf-8",
            )
        except OSError:
            pass  # owner sidecar is diagnostic-only — never blocks the mutation
        data = _parse_ledger(ledger_path)
        mutated = mutator(data)
        _atomic_write_json(ledger_path, mutated)
        return mutated
    finally:
        try:
            owner_path.unlink()
        except OSError:
            pass
        lock.release()


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


def _help_requested(argv: list[str]) -> bool:
    return any(arg in ("-h", "--help") for arg in argv)


def _help_envelope(argv: list[str]) -> Envelope:
    subcommand = next((arg for arg in argv if arg in SUBCOMMANDS), None)
    usage = (
        f"validation_emission.py {subcommand} [options]"
        if subcommand
        else "validation_emission.py <subcommand> [options]"
    )
    return Envelope(
        status="ok",
        data={
            "usage": usage,
            "subcommand": subcommand,
            "subcommands": list(SUBCOMMANDS),
        },
    )


def _module_description() -> str:
    doc = __doc__ or "validation_emission.py"
    return doc.splitlines()[0]


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
        description=_module_description(),
        add_help=False,
    )
    subparsers = parser.add_subparsers(
        dest="subcommand", required=True, parser_class=_Parser
    )
    for name in SUBCOMMANDS:
        subparsers.add_parser(name, add_help=False)
    return parser


def _emit(envelope: Envelope) -> int:
    print(json.dumps(envelope.as_dict(), ensure_ascii=False))
    return envelope.exit_code


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if _help_requested(argv):
        return _emit(_help_envelope(argv))
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
    except ValidationIssuesError as exc:
        envelope = Envelope("issues", exc.code, issues=exc.issues)
    except LedgerBusyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        envelope = Envelope(
            "error", "LEDGER_BUSY", issues=[make_issue("LEDGER_BUSY", str(exc))]
        )
    except LedgerCorruptError as exc:
        print(f"error: {exc}", file=sys.stderr)
        envelope = Envelope(
            "error", "LEDGER_CORRUPT", issues=[make_issue("LEDGER_CORRUPT", str(exc))]
        )
    except Exception as exc:  # noqa: BLE001 — boundary: stdout stays an envelope
        print(f"error: {exc}", file=sys.stderr)
        envelope = Envelope(
            "error", "INTERNAL_ERROR", issues=[make_issue("INTERNAL_ERROR", str(exc))]
        )
    return _emit(envelope)


if __name__ == "__main__":
    sys.exit(main())
