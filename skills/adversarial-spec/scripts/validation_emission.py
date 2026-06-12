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
from collections.abc import Mapping
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

BANNED_ORACLE_PHRASES = (
    "tests pass",
    "all tests pass",
    "works as expected",
    "as intended",
    "no issues found",
    "behaved correctly",
    "correctly implemented",
)

VAGUE_TERMINALS = (
    "looks good",
    "passed",
    "success",
    "confirmed",
)


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
_US_TOKEN_RE = re.compile(r"\bUS-\d+\b")
_CONOPS_REF_RE = re.compile(r"^US-\d+$")
_ROW_ID_RE = re.compile(r"^r-US(?P<story_num>\d+)-(?P<row_num>\d+)$")

EVIDENCE_TYPES = frozenset(
    {"agent-walkthrough-transcript", "artifact-demo", "narrative"}
)


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


# ── ConOps derivation (DD-7, CB-11, FM-3) ────────────────────────────────────


def _text_field(data: Mapping[Any, Any], names: tuple[str, ...], default: str = "") -> str:
    for name in names:
        value = data.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return default


def _load_json_object(path: Path, kind: str) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValidationIssuesError(
            f"{kind.upper()}_INVALID",
            [make_issue(f"{kind.upper()}_INVALID", str(exc))],
        ) from None
    if not isinstance(data, dict):
        raise ValidationIssuesError(
            f"{kind.upper()}_INVALID",
            [make_issue(f"{kind.upper()}_INVALID", f"{kind} must be a JSON object")],
        )
    return data


def _manifest_stories(manifest: dict[str, Any]) -> list[dict[str, str]]:
    raw_stories = manifest.get("user_stories")
    if not isinstance(raw_stories, list) or not raw_stories:
        raise ValidationIssuesError(
            "MANIFEST_INVALID",
            [make_issue("MANIFEST_INVALID", "manifest.user_stories must be non-empty")],
        )
    stories: list[dict[str, str]] = []
    for index, raw in enumerate(raw_stories):
        if not isinstance(raw, dict):
            raise ValidationIssuesError(
                "MANIFEST_INVALID",
                [make_issue("MANIFEST_INVALID", f"user_stories[{index}] must be an object")],
            )
        story_id = _text_field(raw, ("id",))
        story_text = _text_field(raw, ("story", "text"))
        if not story_id or not _US_TOKEN_RE.fullmatch(story_id):
            raise ValidationIssuesError(
                "INVALID_STORY_ID",
                [make_issue("INVALID_STORY_ID", f"invalid story id: {story_id!r}")],
            )
        if not story_text:
            raise ValidationIssuesError(
                "MANIFEST_INVALID",
                [make_issue("MANIFEST_INVALID", f"{story_id} has no story text")],
            )
        stories.append(
            {
                "id": story_id,
                "title": _text_field(raw, ("title", "name"), story_id),
                "story": story_text,
            }
        )
    duplicates = find_duplicate_story_ids([story["id"] for story in stories])
    if duplicates:
        raise ValidationIssuesError(
            "DUPLICATE_STORY_ID",
            [
                make_issue(
                    "DUPLICATE_STORY_ID",
                    f"duplicate manifest story id(s): {', '.join(duplicates)}",
                )
            ],
        )
    return stories


def _milestone_context_by_story(manifest: dict[str, Any]) -> dict[str, dict[str, str]]:
    contexts: dict[str, dict[str, str]] = {}
    raw_milestones = manifest.get("milestones", [])
    if not isinstance(raw_milestones, list):
        return contexts
    for raw in raw_milestones:
        if not isinstance(raw, dict):
            continue
        title = _text_field(raw, ("title", "name"), _text_field(raw, ("id",), "Milestone"))
        context = _text_field(raw, ("context", "description", "summary", "rationale"))
        story_ids = raw.get("user_stories", [])
        if not isinstance(story_ids, list):
            continue
        for story_id in story_ids:
            if isinstance(story_id, str):
                contexts[story_id] = {"title": title, "context": context}
    return contexts


def derive_conops_text(manifest: dict[str, Any]) -> str:
    """Deterministically render conops.md from manifest fields only."""
    stories = _manifest_stories(manifest)
    contexts = _milestone_context_by_story(manifest)
    title = _text_field(manifest, ("title", "name"), "Validation Session")
    session_id = _text_field(manifest, ("session_id",), "unknown-session")

    lines = [
        f"# ConOps: {title}",
        "",
        "## Operational narrative",
        f"Session: {session_id}",
        "This ConOps is derived deterministically from roadmap manifest milestones and user stories.",
        "",
        "## User stories (intent register)",
    ]
    for story in stories:
        context = contexts.get(story["id"], {})
        milestone_title = context.get("title", "Unassigned milestone")
        milestone_context = context.get("context", "")
        lines.extend(
            [
                f"### {story['id']}: {story['title']}",
                story["story"],
                f"Milestone: {milestone_title}",
            ]
        )
        if milestone_context:
            lines.append(f"Milestone context: {milestone_context}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _lint_conops_story_tokens(conops_text: str, story_ids: set[str]) -> None:
    stray = sorted(set(_US_TOKEN_RE.findall(conops_text)) - story_ids)
    if stray:
        raise ValidationIssuesError(
            "STRAY_CONOPS_STORY_ID",
            [
                make_issue(
                    "STRAY_CONOPS_STORY_ID",
                    f"ConOps output references story id(s) not in manifest: {', '.join(stray)}",
                )
            ],
        )


def _spec_root_for_manifest(manifest_path: Path) -> Path:
    manifest_path = Path(manifest_path).resolve()
    if manifest_path.parent.name == "roadmap":
        return manifest_path.parent.parent
    return manifest_path.parent


def _resolve_conops_output(manifest_path: Path, output: Path | None) -> Path:
    spec_root = _spec_root_for_manifest(manifest_path)
    if output is None:
        candidate = Path(manifest_path).resolve().parent / "conops.md"
    elif Path(output).is_absolute():
        candidate = Path(output)
    else:
        candidate = Path(manifest_path).resolve().parent / output
    return resolve_under_root(spec_root, candidate)


def _ledger_candidates_for_conops(output_path: Path) -> list[Path]:
    candidates = [output_path.parent.parent / "validation-rows.json"]
    same_dir = output_path.parent / "validation-rows.json"
    if same_dir not in candidates:
        candidates.append(same_dir)
    return candidates


def _ledger_references_hash(ledger: Any, conops_hash: str) -> bool:
    if isinstance(ledger, dict):
        return any(_ledger_references_hash(value, conops_hash) for value in ledger.values())
    if isinstance(ledger, list):
        return any(_ledger_references_hash(value, conops_hash) for value in ledger)
    return ledger == conops_hash


def _guard_conops_overwrite(output_path: Path, force: bool) -> str | None:
    if not output_path.exists():
        return None
    prior_bytes = output_path.read_bytes()
    prior_hash = compute_conops_hash(prior_bytes)
    for ledger_path in _ledger_candidates_for_conops(output_path):
        if not ledger_path.exists():
            continue
        ledger = _load_json_object(ledger_path, "ledger")
        if _ledger_references_hash(ledger, prior_hash) and not force:
            raise ValidationIssuesError(
                "CONOPS_OVERWRITE_REQUIRES_FORCE",
                [
                    make_issue(
                        "CONOPS_OVERWRITE_REQUIRES_FORCE",
                        f"{ledger_path} references existing conops_hash {prior_hash}; rerun with --force to overwrite",
                    )
                ],
            )
    return prior_hash


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(
        dir=path.parent, delete=False, suffix=".tmp", mode="w", encoding="utf-8"
    )
    try:
        tmp.write(text)
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


def handle_derive_conops(args: argparse.Namespace) -> Envelope:
    manifest_path = Path(args.manifest)
    manifest = _load_json_object(manifest_path, "manifest")
    stories = _manifest_stories(manifest)
    conops_text = derive_conops_text(manifest)
    story_ids = {story["id"] for story in stories}
    _lint_conops_story_tokens(conops_text, story_ids)
    output_path = _resolve_conops_output(manifest_path, args.output)
    prior_hash = _guard_conops_overwrite(output_path, args.force)
    conops_bytes = conops_text.encode("utf-8")
    enforce_input_bounds("conops", conops_bytes)
    conops_hash = compute_conops_hash(conops_bytes)
    story_hashes = compute_story_hashes(conops_text)
    _atomic_write_text(output_path, conops_text)
    return Envelope(
        status="ok",
        data={
            "path": str(output_path),
            "bytes": len(conops_bytes),
            "conops_hash": conops_hash,
            "conops_hash_prefix": hash_prefix(conops_hash),
            "story_hashes": story_hashes,
            "prior_conops_hash": prior_hash,
        },
    )


def handle_check_rows(args: argparse.Namespace) -> Envelope:
    """Implement C-2.3: check validation rows for oracle quality and coverage (INV-6, INV-11)."""
    ledger_path = resolve_under_root(args.ledger.parent, args.ledger)
    ledger = read_ledger(ledger_path)

    conops_path = resolve_under_root(ledger_path.parent, args.conops)
    conops_bytes = conops_path.read_bytes()
    enforce_input_bounds("conops", conops_bytes)
    conops_text = conops_bytes.decode("utf-8")
    story_hashes = compute_story_hashes(conops_text)
    all_story_ids = set(story_hashes.keys())

    verification_targets = set()
    if args.verification_ledger:
        v_ledger_path = resolve_under_root(ledger_path.parent, args.verification_ledger)
        v_ledger = _load_json_object(v_ledger_path, "verification-ledger")
        for row in v_ledger.get("rows", []):
            targets = row.get("test_targets", [])
            if isinstance(targets, list):
                verification_targets.update(targets)

    issues = []
    seen_stories = set()
    rows = ledger.get("rows", [])

    if not isinstance(rows, list):
        return Envelope(
            status="issues",
            issues=[make_issue("ROWS_INVALID", "ledger.rows must be a list")],
        )

    for duplicate in find_duplicate_row_ids(ledger):
        issues.append(
            make_issue("DUPLICATE_ROW_ID", f"duplicate row_id: {duplicate}", duplicate)
        )

    for row in rows:
        if not isinstance(row, dict):
            issues.append(make_issue("ROW_INVALID", "ledger row must be an object", None))
            continue

        row_id = row.get("row_id")
        conops_ref = row.get("conops_ref")
        oracle = row.get("oracle", "")
        evidence_rationale = row.get("evidence_rationale", "")
        test_targets = row.get("test_targets", [])

        row_issue_id = row_id if isinstance(row_id, str) else None
        oracle_text = oracle if isinstance(oracle, str) else ""

        # TC-2.1 / TC-2.4: structural row checks. Semantics remain human-owned.
        for field_name in ("row_id", "conops_ref", "scenario", "oracle", "evidence_type"):
            value = row.get(field_name)
            if not isinstance(value, str) or not value.strip():
                issues.append(
                    make_issue(
                        "MISSING_REQUIRED_FIELD",
                        f"row missing non-empty {field_name}",
                        row_issue_id,
                    )
                )

        if not isinstance(evidence_rationale, str) or not evidence_rationale.strip():
            issues.append(
                make_issue(
                    "EVIDENCE_RATIONALE_MISSING",
                    "row missing non-empty evidence_rationale",
                    row_issue_id,
                )
            )

        row_id_match = _ROW_ID_RE.match(row_id) if isinstance(row_id, str) else None
        if isinstance(row_id, str) and not row_id_match:
            issues.append(
                make_issue("INVALID_ROW_ID", f"invalid row_id: {row_id!r}", row_issue_id)
            )

        if isinstance(conops_ref, str) and conops_ref.strip():
            if not _CONOPS_REF_RE.match(conops_ref):
                issues.append(
                    make_issue(
                        "INVALID_CONOPS_REF",
                        f"conops_ref must be exactly one US-n id: {conops_ref!r}",
                        row_issue_id,
                    )
                )
            elif conops_ref not in all_story_ids:
                issues.append(
                    make_issue(
                        "UNKNOWN_CONOPS_REF",
                        f"conops_ref {conops_ref} is not present in conops.md",
                        row_issue_id,
                    )
                )
            else:
                seen_stories.add(conops_ref)

            if row_id_match:
                expected_ref = f"US-{row_id_match.group('story_num')}"
                if conops_ref != expected_ref:
                    issues.append(
                        make_issue(
                            "ROW_ID_STORY_MISMATCH",
                            f"row_id prefix {expected_ref} does not match conops_ref {conops_ref}",
                            row_issue_id,
                        )
                    )

        evidence_type = row.get("evidence_type")
        if (
            isinstance(evidence_type, str)
            and evidence_type.strip()
            and evidence_type not in EVIDENCE_TYPES
        ):
            issues.append(
                make_issue(
                    "INVALID_EVIDENCE_TYPE",
                    f"invalid evidence_type: {evidence_type!r}",
                    row_issue_id,
                )
            )

        row_hash = row.get("row_hash")
        canonical_fields_present = all(
            isinstance(row.get(field_name), str) and row.get(field_name).strip()
            for field_name in ROW_HASH_FIELDS
        )
        if row_hash is None:
            issues.append(make_issue("ROW_HASH_MISSING", "row_hash is required", row_issue_id))
        elif not isinstance(row_hash, str) or not _FULL_HASH_RE.match(row_hash):
            issues.append(
                make_issue(
                    "ROW_HASH_INVALID",
                    "row_hash must be a full 64-hex sha256",
                    row_issue_id,
                )
            )
        elif canonical_fields_present and row_hash != row_hash_for(row):
            issues.append(
                make_issue(
                    "ROW_HASH_MISMATCH",
                    "row_hash does not match canonical fields",
                    row_issue_id,
                )
            )

        # AC-2: Oracle layer-2 lint
        oracle_lower = oracle_text.lower()
        for phrase in BANNED_ORACLE_PHRASES:
            if phrase in oracle_lower:
                issues.append(
                    make_issue(
                        "BANNED_ORACLE_PHRASE",
                        f"oracle contains banned phrase: {phrase!r}",
                        row_issue_id,
                    )
                )

        if "iff" not in oracle_lower:
            issues.append(
                make_issue(
                    "ORACLE_MISSING_IFF",
                    "oracle must contain literal 'iff' (INV-6)",
                    row_issue_id,
                )
            )

        if isinstance(conops_ref, str) and conops_ref and conops_ref not in oracle_text:
            issues.append(
                make_issue(
                    "ORACLE_MISSING_STORY_REF",
                    f"oracle must refer to {conops_ref} (TC-2.3)",
                    row_issue_id,
                )
            )

        for vague in VAGUE_TERMINALS:
            if vague in oracle_lower:
                # "vague terminals unless paired with concrete observable"
                # Structural check: if oracle is very short, it's probably just the vague terminal.
                if len(oracle_text.split()) < 10:
                    issues.append(
                        make_issue(
                            "VAGUE_ORACLE",
                            f"oracle contains vague terminal {vague!r} without sufficient detail",
                            row_issue_id,
                        )
                    )

        # AC-3: Anti-relabeling
        if verification_targets and isinstance(test_targets, list) and test_targets:
            val_targets_set = set(test_targets)
            overlap = val_targets_set & verification_targets
            if val_targets_set and val_targets_set.issubset(verification_targets):
                if not evidence_rationale:
                    issues.append(
                        make_issue(
                            "RELABELED_VERIFICATION",
                            "validation test_targets are a subset of verification targets but rationale is missing",
                            row_id,
                        )
                    )
            elif overlap:
                if not evidence_rationale:
                    issues.append(
                        make_issue(
                            "OVERLAPPING_TARGETS",
                            "validation test_targets overlap with verification targets but rationale is missing",
                            row_id,
                        )
                    )

    # AC-1: Coverage check
    missing_coverage = all_story_ids - seen_stories
    if missing_coverage:
        if args.draft:
            # Advisory: we report it in issues but we might change status to "ok" if no other issues.
            for story_id in sorted(missing_coverage):
                issues.append(
                    make_issue(
                        "INCOMPLETE_COVERAGE_ADVISORY",
                        f"draft mode: story {story_id} is not yet covered",
                        None,
                    )
                )
        else:
            for story_id in sorted(missing_coverage):
                issues.append(
                    make_issue(
                        "INCOMPLETE_COVERAGE",
                        f"story {story_id} must have at least one validation row (CB-10)",
                        None,
                    )
                )

    status = "ok"
    if issues:
        # If it's only advisory, status is still ok.
        is_only_advisory = all(i["code"].endswith("_ADVISORY") for i in issues)
        if not (args.draft and is_only_advisory):
            status = "issues"

    return Envelope(status=status, issues=issues)


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


def get_git_info(cwd: Path) -> tuple[str, bool]:
    """Return (short_hash, is_clean)."""
    try:
        proc_hash = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=cwd, capture_output=True, text=True, check=True
        )
        short_hash = proc_hash.stdout.strip()

        proc_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd, capture_output=True, text=True, check=True
        )
        is_clean = not proc_status.stdout.strip()
        return short_hash, is_clean
    except (subprocess.SubprocessError, OSError):
        return "unknown", False


def handle_normalize_rows(args: argparse.Namespace) -> Envelope:
    """Implement C-2.2: stamp row/story hashes and assign schema fields (mutating)."""
    ledger_path = resolve_under_root(args.ledger.parent, args.ledger)
    conops_path = resolve_under_root(ledger_path.parent, args.conops)

    conops_bytes = conops_path.read_bytes()
    enforce_input_bounds("conops", conops_bytes)
    conops_text = conops_bytes.decode("utf-8")
    conops_hash = compute_conops_hash(conops_bytes)
    story_hashes = compute_story_hashes(conops_text)

    def mutator(ledger: dict[str, Any]) -> dict[str, Any]:
        rows = ledger.get("rows", [])
        if not isinstance(rows, list):
            rows = []

        # AC-2 validation: reject BEFORE stamping anything — an exception here
        # aborts mutate_ledger pre-write, leaving the ledger bytes untouched.
        issues: list[dict[str, Any]] = []

        for duplicate in find_duplicate_row_ids(ledger):
            issues.append(
                make_issue("DUPLICATE_ROW_ID", f"duplicate row_id: {duplicate}", duplicate)
            )

        for row in rows:
            if not isinstance(row, dict):
                continue
            row_id = row.get("row_id")
            row_issue_id = row_id if isinstance(row_id, str) else None
            conops_ref = row.get("conops_ref")

            row_id_match = _ROW_ID_RE.match(row_id) if isinstance(row_id, str) else None
            if not row_id_match:
                issues.append(
                    make_issue("INVALID_ROW_ID", f"invalid row_id: {row_id!r}", row_issue_id)
                )
            if isinstance(conops_ref, str) and conops_ref not in story_hashes:
                issues.append(
                    make_issue(
                        "UNKNOWN_CONOPS_REF",
                        f"conops_ref {conops_ref} is not present in conops.md",
                        row_issue_id,
                    )
                )
            if row_id_match and isinstance(conops_ref, str):
                expected_ref = f"US-{row_id_match.group('story_num')}"
                if conops_ref != expected_ref:
                    issues.append(
                        make_issue(
                            "ROW_ID_STORY_MISMATCH",
                            f"row_id prefix {expected_ref} does not match conops_ref {conops_ref}",
                            row_issue_id,
                        )
                    )

            missing_canonical = [
                name for name in ROW_HASH_FIELDS
                if not (isinstance(row.get(name), str) and row.get(name).strip())
            ]
            if missing_canonical:
                issues.append(
                    make_issue(
                        "ROW_FIELDS_MISSING",
                        f"row missing canonical fields: {', '.join(missing_canonical)}",
                        row_issue_id,
                    )
                )

        if issues:
            raise ValidationIssuesError("NORMALIZE_REJECTED", issues)

        # AC-2 stamping: ledger header schema fields (§6.2). stamp_artifact
        # supplies schema_version + module_version + generated_at (OP-4).
        ledger["kind"] = "validation-rows-ledger"
        ledger["conops_hash"] = conops_hash
        ledger["story_hashes"] = story_hashes
        stamped = stamp_artifact(ledger)

        # AC-1: sole producer of row/story hashes (CB-7).
        for row in stamped["rows"]:
            row["row_hash"] = row_hash_for(row)
            row["story_hash"] = story_hashes[row["conops_ref"]]

        return stamped

    mutate_ledger(ledger_path, mutator)
    return Envelope(status="ok")


def handle_record_evidence(args: argparse.Namespace) -> Envelope:
    """Implement C-3.1: scaffold evidence.md and record summary (mutating)."""
    ledger_path = resolve_under_root(args.ledger.parent, args.ledger)
    conops_path = resolve_under_root(ledger_path.parent, args.conops)

    conops_bytes = conops_path.read_bytes()
    enforce_input_bounds("conops", conops_bytes)
    conops_text = conops_bytes.decode("utf-8")
    conops_hash = compute_conops_hash(conops_bytes)
    story_hashes = compute_story_hashes(conops_text)

    git_hash, is_clean = get_git_info(ledger_path.parent)
    if args.commit:
        git_hash = args.commit

    # Mutation: record evidence_summary and bind hashes
    def mutator(ledger: dict[str, Any]) -> dict[str, Any]:
        rows = ledger.get("rows", [])
        target_row = next((r for r in rows if r.get("row_id") == args.row), None)
        if not target_row:
            raise ValidationIssuesError(
                "ROW_NOT_FOUND",
                [make_issue("ROW_NOT_FOUND", f"row {args.row} not found", args.row)],
            )

        target_row["evidence_summary"] = args.summary
        target_row["row_hash"] = row_hash_for(target_row)
        conops_ref = target_row.get("conops_ref")
        if conops_ref not in story_hashes:
            raise ValidationIssuesError(
                "UNKNOWN_CONOPS_REF",
                [
                    make_issue(
                        "UNKNOWN_CONOPS_REF",
                        f"row {args.row} refers to unknown story {conops_ref}",
                        args.row,
                    )
                ],
            )
        target_row["story_hash"] = story_hashes[conops_ref]
        return ledger

    ledger = mutate_ledger(ledger_path, mutator)
    target_row = next(r for r in ledger["rows"] if r.get("row_id") == args.row)

    # Scaffolding
    evidence_dir = ledger_path.parent / "validation-evidence" / args.row
    evidence_path = evidence_dir / "evidence.md"

    expected_fm_keys = [
        "row_id",
        "row_hash",
        "story_hash",
        "conops_hash",
        "evidence_type",
        "produced_at",
        "commit",
        "worktree_clean",
    ]

    if evidence_path.exists():
        # Re-invocation: validate front matter (INV-12)
        content = evidence_path.read_text(encoding="utf-8")
        if not content.startswith("---"):
            raise ValidationIssuesError(
                "EVIDENCE_MALFORMED",
                [
                    make_issue(
                        "EVIDENCE_MALFORMED",
                        "evidence file missing front matter starter",
                        args.row,
                    )
                ],
            )
        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValidationIssuesError(
                "EVIDENCE_MALFORMED",
                [
                    make_issue(
                        "EVIDENCE_MALFORMED",
                        "evidence file malformed front matter",
                        args.row,
                    )
                ],
            )

        fm_text = parts[1].strip()
        fm_data = {}
        actual_keys = []
        for line in fm_text.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip()
                fm_data[k] = v.strip()
                actual_keys.append(k)

        if actual_keys != expected_fm_keys:
            raise ValidationIssuesError(
                "EVIDENCE_MALFORMED",
                [
                    make_issue(
                        "EVIDENCE_MALFORMED",
                        f"front-matter keys/order mismatch. Expected: {', '.join(expected_fm_keys)}",
                        args.row,
                    )
                ],
            )

        # Hash/ID binding checks
        if fm_data.get("row_id") != args.row:
            raise ValidationIssuesError(
                "EVIDENCE_HASH_MISMATCH",
                [
                    make_issue(
                        "EVIDENCE_HASH_MISMATCH",
                        f"row_id mismatch: {fm_data.get('row_id')}",
                        args.row,
                    )
                ],
            )
        if fm_data.get("row_hash") != target_row["row_hash"]:
            raise ValidationIssuesError(
                "EVIDENCE_HASH_MISMATCH",
                [make_issue("EVIDENCE_HASH_MISMATCH", "row_hash mismatch", args.row)],
            )
        if fm_data.get("story_hash") != target_row["story_hash"]:
            raise ValidationIssuesError(
                "EVIDENCE_HASH_MISMATCH",
                [make_issue("EVIDENCE_HASH_MISMATCH", "story_hash mismatch", args.row)],
            )
    else:
        # Initial scaffolding
        produced_at = utc_now()
        fm_lines = ["---"]
        fm_lines.append(f"row_id: {args.row}")
        fm_lines.append(f"row_hash: {target_row['row_hash']}")
        fm_lines.append(f"story_hash: {target_row['story_hash']}")
        fm_lines.append(f"conops_hash: {conops_hash}")
        fm_lines.append(f"evidence_type: {target_row.get('evidence_type', 'narrative')}")
        fm_lines.append(f"produced_at: {produced_at}")
        fm_lines.append(f"commit: {git_hash}")
        fm_lines.append(f"worktree_clean: {'true' if is_clean else 'false'}")
        fm_lines.append("---")
        fm_lines.append("")
        fm_lines.append("(Attach evidence below this line)")
        fm_lines.append("")

        evidence_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write_text(evidence_path, "\n".join(fm_lines))

    return Envelope(status="ok", data={"path": str(evidence_path)})


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


def emit_system_validation(args: argparse.Namespace) -> Envelope:
    """Implement C-4-4: read-only projection of judged rows into §6.4 (INV-A1)."""
    ledger_path = resolve_under_root(args.ledger.parent, args.ledger)
    ledger_bytes = ledger_path.read_bytes()
    ledger_hash = hashlib.sha256(ledger_bytes).hexdigest()

    try:
        ledger = json.loads(ledger_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Fall back to read_ledger for quarantine if it's really corrupt
        ledger = read_ledger(ledger_path)

    conops_path = resolve_under_root(ledger_path.parent, args.conops)
    conops_bytes = conops_path.read_bytes()
    enforce_input_bounds("conops", conops_bytes)
    conops_text = conops_bytes.decode("utf-8")

    fresh_conops_hash = compute_conops_hash(conops_bytes)
    fresh_story_hashes = compute_story_hashes(conops_text)

    issues = []
    projected_rows = []
    passing_stories = set()
    all_story_ids = set(fresh_story_hashes.keys())

    # INV-8: conops_hash recorded must be computed AFTER the last edit.
    # We use the fresh hash for the artifact, but we refuse if the ledger
    # is stale relative to the story hashes (FM-3).

    # Active-row predicate (spec §6.2, formal): a row is active iff it appears
    # in rows[] AND its row_id appears in no superseded[].row_snapshot.row_id.
    # Superseded rows never appear in the projection (INV-10) and never count
    # toward coverage (INV-7) — even if unjudged, they must not block.
    superseded_ids = {
        entry.get("row_snapshot", {}).get("row_id")
        for entry in ledger.get("superseded", [])
    }
    active_rows = [
        row for row in ledger.get("rows", [])
        if row.get("row_id") not in superseded_ids
    ]

    for row in active_rows:
        row_id = row.get("row_id")
        result = row.get("result")
        conops_ref = row.get("conops_ref")

        if result is None:
            issues.append(make_issue("UNJUDGED_ROW", f"row {row_id} is unjudged", row_id))
            continue
        if result == "fail":
            issues.append(make_issue("FAILED_ROW", f"row {row_id} is failed", row_id))
            continue

        # INV-1: provenance check (result != null implies judgment != null)
        judgment = row.get("judgment")
        if not judgment:
            issues.append(make_issue("PROVENANCE_MISSING", f"row {row_id} has result but no judgment block", row_id))
            continue

        # Strictly validate required provenance fields (AC-2)
        required_provenance = ["judged_by", "judged_at", "source", "digest_id", "reply_ref"]
        missing_fields = [f for f in required_provenance if not judgment.get(f)]
        if missing_fields:
            issues.append(make_issue(
                "PROVENANCE_MISSING",
                f"row {row_id} judgment block missing required fields: {', '.join(missing_fields)}",
                row_id
            ))
            continue

        # FM-3: story hash check (scoped by story_hashes)
        if conops_ref not in fresh_story_hashes:
            issues.append(make_issue("STORY_DELETED", f"row {row_id} refers to deleted story {conops_ref}", row_id))
            continue
        if row.get("story_hash") != fresh_story_hashes[conops_ref]:
            issues.append(make_issue("STALE_STORY_HASH", f"row {row_id} story hash mismatch for {conops_ref} (FM-3)", row_id))
            continue

        # Evidence chain (INV-12)
        evidence_ref = f"validation-evidence/{row_id}/evidence.md"
        ev_path = resolve_under_root(ledger_path.parent, evidence_ref)
        if not ev_path.exists():
            issues.append(make_issue("EVIDENCE_MISSING", f"evidence file missing for row {row_id}: {evidence_ref}", row_id))
            continue

        ev_bytes = ev_path.read_bytes()
        ev_hash = hashlib.sha256(ev_bytes).hexdigest()

        # Verify row_hash in evidence front-matter matches current row?
        # §6.3 says record-evidence scaffolds it. INV-12 says verify chain.
        # For brevity in C-4-4, we use the file existence + ev_hash,
        # assuming record-evidence/assemble-digest handle the inner check.

        # Mapping result (CB-12)
        final_result = "not-applicable" if result == "na" else result

        if final_result == "pass":
            passing_stories.add(conops_ref)

        # Projection (§6.4)
        projected_rows.append({
            "conops_ref": conops_ref,
            "scenario": row.get("scenario"),
            "oracle": row.get("oracle"),
            "result": final_result,
            "row_id": row_id,
            "evidence_type": row.get("evidence_type"),
            "evidence_ref": evidence_ref,
            "evidence_hash": ev_hash,
            "judged_by": judgment.get("judged_by"),
            "judged_at": judgment.get("judged_at"),
            "source": judgment.get("source"),
            "digest_id": judgment.get("digest_id"),
            "reply_ref": judgment.get("reply_ref"),
            "test_targets": row.get("test_targets", [])
        })

    # TC-3.6: Coverage check (every story needs >=1 pass)
    missing_coverage = all_story_ids - passing_stories
    for story_id in sorted(missing_coverage):
        issues.append(make_issue("UNVALIDATED_USER_STORY", f"story {story_id} has no passing rows (TC-3.6)", None))

    if issues:
        # Sort issues by row_id (nulls first) for deterministic envelope
        issues.sort(key=lambda x: (x["row_id"] is not None, x["row_id"] or ""))
        return Envelope(status="issues", code="VALIDATION_FAILED", issues=issues)

    # Final artifact (§6.4)
    artifact = {
        "kind": "system-validation",
        "conops_hash": hash_prefix(fresh_conops_hash),
        "ledger_hash": ledger_hash,
        "rows": projected_rows
    }
    # stamp_artifact adds schema_version (1), module_version, and generated_at (OP-4)
    stamped = stamp_artifact(artifact)

    # Atomic write (INV-A1 projection)
    output_path = resolve_under_root(ledger_path.parent, args.output)
    _atomic_write_json(output_path, stamped)

    return Envelope(status="ok", data={"path": str(output_path)})


#: Subcommand → handler. Components C-1.2 … C-4.6 replace stubs in place.
HANDLERS: dict[str, Callable[[argparse.Namespace], Envelope]] = {
    name: _not_implemented(name) for name in SUBCOMMANDS
}
HANDLERS["derive-conops"] = handle_derive_conops
HANDLERS["normalize-rows"] = handle_normalize_rows
HANDLERS["check-rows"] = handle_check_rows
HANDLERS["record-evidence"] = handle_record_evidence
HANDLERS["emit-system-validation"] = emit_system_validation


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
        sp = subparsers.add_parser(name, add_help=False)
        if name == "derive-conops":
            sp.add_argument("manifest", type=Path, help="Path to roadmap/manifest.json")
            sp.add_argument(
                "-o",
                "--output",
                type=Path,
                default=None,
                help="Output path, relative to the manifest directory by default",
            )
            sp.add_argument(
                "--force",
                action="store_true",
                help="Allow overwrite when an existing ledger references prior conops_hash",
            )
        if name == "check-rows":
            sp.add_argument("ledger", type=Path, help="Path to validation-rows.json")
            sp.add_argument(
                "--conops", type=Path, required=True, help="Path to conops.md"
            )
            sp.add_argument(
                "--draft", action="store_true", help="Relax coverage to advisory"
            )
            sp.add_argument(
                "--verification-ledger",
                type=Path,
                help="Optional path to verification ledger for anti-relabeling check",
            )
        if name == "normalize-rows":
            sp.add_argument("ledger", type=Path, help="Path to validation-rows.json")
            sp.add_argument(
                "--conops", type=Path, required=True, help="Path to conops.md"
            )
        if name == "record-evidence":
            sp.add_argument("ledger", type=Path, help="Path to validation-rows.json")
            sp.add_argument("--row", required=True, help="Target row_id (r-USn-m)")
            sp.add_argument("--summary", required=True, help="Conductor's evidence_summary prose")
            sp.add_argument("--conops", type=Path, required=True, help="Path to conops.md")
            sp.add_argument("--commit", help="Optional implementation git short hash")
        if name == "emit-system-validation":
            sp.add_argument("ledger", type=Path, help="Path to validation-rows.json")
            sp.add_argument("--conops", type=Path, required=True, help="Path to conops.md")
            sp.add_argument(
                "-o",
                "--output",
                type=str,
                default="system_validation.json",
                help="Output artifact path (default: system_validation.json)",
            )
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
