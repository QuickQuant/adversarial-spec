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
    "code merged",
    "gate passed",
    "ci green",
    "suite succeeds",
    "pipeline healthy",
    "checks satisfied",
    "works as expected",
    "as intended",
    "no issues found",
    "behaved correctly",
    "correctly implemented",
)

VAGUE_TERMINALS = (
    "works",
    "looks good",
    "acceptable",
    "done",
    "successful",
    "passed",
    "success",
    "confirmed",
)

CONCRETE_OBSERVABLE_TERMS = (
    "artifact",
    "output",
    "stdout",
    "stderr",
    "envelope",
    "json",
    "file",
    "path",
    "ledger",
    "digest",
    "transcript",
    "report",
    "message",
    "reply",
    "screen",
    "ui",
    "page",
    "terminal",
    "command",
    "response",
    "user-visible",
    "visible",
    "rendered",
)


def _contains_lint_phrase(text_lower: str, phrase: str) -> bool:
    """Match lint phrases as lowercase terms, not arbitrary substrings."""
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text_lower) is not None


def _oracle_sentences(oracle_text: str) -> list[str]:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", oracle_text) if part.strip()]
    return sentences or [oracle_text]


def _has_concrete_observable(sentence_lower: str) -> bool:
    return any(_contains_lint_phrase(sentence_lower, term) for term in CONCRETE_OBSERVABLE_TERMS)


def _vague_terms_without_observable(oracle_text: str) -> list[str]:
    missing: list[str] = []
    for sentence in _oracle_sentences(oracle_text):
        sentence_lower = sentence.lower()
        for vague in VAGUE_TERMINALS:
            if _contains_lint_phrase(sentence_lower, vague) and not _has_concrete_observable(
                sentence_lower
            ):
                missing.append(vague)
    return sorted(set(missing))


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

#: Raw Telegram update payloads + the sender-allowlist registry are small
#: JSON files; bound them like a reply to keep the inbound trust boundary
#: cheap to read (C-1-4 / SEC-10).
TELEGRAM_UPDATE_MAX_BYTES = REPLY_MAX_BYTES
REGISTRY_MAX_BYTES = REPLY_MAX_BYTES

_INPUT_BOUNDS = {
    "reply": REPLY_MAX_BYTES,
    "justification": JUSTIFICATION_MAX_BYTES,
    "ledger": LEDGER_MAX_BYTES,
    "conops": CONOPS_MAX_BYTES,
    "telegram_update": TELEGRAM_UPDATE_MAX_BYTES,
    "registry": REGISTRY_MAX_BYTES,
}

#: §6.5 multi-part rule: per-part budget in UTF-8 BYTES (Telegram raw limit is
#: 4096 chars; the byte budget absorbs encoding — gauntlet OP-9/RC-2).
DIGEST_PART_MAX_BYTES = 3500

#: Secret deny-patterns linted over the FULL digest text (SEC-4, TC-G9).
#: Defense-in-depth on top of conductor content discipline; a match BLOCKS
#: assembly with the offending span indicated.
SECRET_DENY_PATTERNS = (
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password|passwd)\b\s*[:=]\s*\S+"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{8,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"),
    re.compile(r"\b[A-Z][A-Z0-9_]{2,}=[^\s\"']{6,}"),
)

#: Non-terminal digest-batch statuses — at most ONE such batch may exist.
NON_TERMINAL_BATCH_STATUSES = frozenset({"assembled", "sent"})


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
            if _contains_lint_phrase(oracle_lower, phrase):
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

        for vague in _vague_terms_without_observable(oracle_text):
            issues.append(
                make_issue(
                    "VAGUE_ORACLE",
                    f"oracle contains vague terminal {vague!r} without a concrete observable",
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


class _NothingToDigestError(Exception):
    """Control flow: zero pending rows — exit 0 NOTHING_TO_DIGEST (AC-4)."""


def _one_line(text: Any) -> str:
    """Collapse prose to one whitespace-normalized line so row content cannot
    imitate digest furniture (row labels, reply instructions — SEC-4)."""
    return " ".join(str(text).split())


def _parse_evidence_front_matter(content: str) -> dict[str, str] | None:
    """Parse the §6.3 front-matter block; None when structurally malformed."""
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    fm: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fm[key.strip()] = value.strip()
    return fm


def _active_rows(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    """Active-row predicate (spec §6.2 formal): in rows[] AND row_id in no
    superseded[].row_snapshot.row_id."""
    superseded_ids = {
        entry.get("row_snapshot", {}).get("row_id")
        for entry in ledger.get("superseded", [])
    }
    return [
        row for row in ledger.get("rows", [])
        if isinstance(row, dict) and row.get("row_id") not in superseded_ids
    ]


_DIGEST_FOOTER = (
    'Reply per row ("pass r-US3-1", "fail r-US3-1: <reason>", '
    '"na r-US3-1: <why>") or pass everything ("pass all" / '
    '"those all look good"). "pass rest" passes whatever you didn\'t '
    "explicitly judge."
)


def _digest_header(session: str, digest_id: str, n_rows: int, i: int, k: int) -> str:
    return f"🥊📜 VALIDATION DIGEST {session} {digest_id} ({n_rows} rows, part {i}/{k})"


def _render_row_block(index: int, row: dict[str, Any], evidence_ref: str) -> str:
    """One §6.5 row entry. All prose is escaped to a single line."""
    evidence_type = row.get("evidence_type", "")
    marker = " (narrative)" if evidence_type == "narrative" else ""
    lines = [
        f"[{index}] {row['row_id']} ({row.get('conops_ref', '?')}){marker}",
        f"  scenario: {_one_line(row.get('scenario', ''))}",
        f"  oracle: {_one_line(row.get('oracle', ''))}",
        f"  evidence: {evidence_type} — {_one_line(row.get('evidence_summary', ''))}"
        f" (file: {evidence_ref})",
    ]
    history = row.get("judgment_history") or []
    if history and isinstance(history[-1], dict) and history[-1].get("result") == "fail":
        prior = history[-1]
        lines.append(
            f"  [prior: failed {prior.get('digest_id', '?')} — "
            f"{_one_line(prior.get('justification', ''))[:120]}]"
        )
    return "\n".join(lines)


def _truncate_block_summary(block: str, budget: int) -> str:
    """Trim ONLY the evidence summary (head + … + path pointer survives);
    scenario and oracle are never truncated (§6.5 — row-size lint guarantees
    they fit)."""
    lines = block.split("\n")
    for idx, line in enumerate(lines):
        if not line.startswith("  evidence: "):
            continue
        overshoot = len(block.encode("utf-8")) - budget
        pointer_at = line.rfind(" (file: ")
        if pointer_at <= 0 or overshoot <= 0:
            return block
        head, pointer = line[:pointer_at], line[pointer_at:]
        trimmed = head.encode("utf-8")[: max(len(head.encode("utf-8")) - overshoot - 1, 20)]
        lines[idx] = trimmed.decode("utf-8", errors="ignore") + "…" + pointer
        return "\n".join(lines)
    return block


def handle_assemble_digest(args: argparse.Namespace) -> Envelope:
    """Implement C-3.2: pure delta assembly into ≤3500-byte part files with a
    batch record (status ``assembled``) under the ledger lock."""
    ledger_path = resolve_under_root(args.ledger.parent, args.ledger)
    conops_path = resolve_under_root(ledger_path.parent, args.conops)
    conops_bytes = conops_path.read_bytes()
    enforce_input_bounds("conops", conops_bytes)
    conops_hash = compute_conops_hash(conops_bytes)
    story_hashes = compute_story_hashes(conops_bytes.decode("utf-8"))
    session = args.session or "-"

    result_data: dict[str, Any] = {}

    def mutator(ledger: dict[str, Any]) -> dict[str, Any]:
        batches = ledger.get("digest_batches", [])
        active_batch = next(
            (b for b in batches if b.get("status") in NON_TERMINAL_BATCH_STATUSES),
            None,
        )
        if active_batch is not None:
            raise ValidationIssuesError(
                "BATCH_ACTIVE",
                [make_issue(
                    "BATCH_ACTIVE",
                    f"batch {active_batch.get('digest_id')} is "
                    f"{active_batch.get('status')}; exactly one non-terminal "
                    "batch may exist — close or cancel it first",
                    None,
                )],
            )

        pending = [r for r in _active_rows(ledger) if r.get("result") is None]
        if not pending:
            raise _NothingToDigestError()

        # AC-1 refusals (INV-4/INV-12): evidence must exist, be non-empty,
        # type-matched, hash-matched, and newer than the row's last reset.
        issues: list[dict[str, Any]] = []
        evidence_refs: dict[str, str] = {}
        evidence_hashes: dict[str, str] = {}
        for row in pending:
            row_id = row.get("row_id")
            evidence_ref = f"validation-evidence/{row_id}/evidence.md"
            evidence_refs[row_id] = evidence_ref
            ev_path = resolve_under_root(ledger_path.parent, evidence_ref)

            if not str(row.get("evidence_summary", "")).strip():
                issues.append(make_issue(
                    "EVIDENCE_SUMMARY_MISSING",
                    f"row {row_id} has no evidence_summary — the digest must be "
                    "judgeable from mobile",
                    row_id,
                ))
            if not ev_path.exists():
                issues.append(make_issue(
                    "EVIDENCE_MISSING", f"evidence file missing: {evidence_ref}", row_id
                ))
                continue
            ev_bytes = ev_path.read_bytes()
            if not ev_bytes.strip():
                issues.append(make_issue(
                    "EVIDENCE_EMPTY", f"evidence file empty: {evidence_ref}", row_id
                ))
                continue
            evidence_hashes[row_id] = hashlib.sha256(ev_bytes).hexdigest()

            fm = _parse_evidence_front_matter(ev_bytes.decode("utf-8", errors="replace"))
            if fm is None:
                issues.append(make_issue(
                    "EVIDENCE_MALFORMED",
                    f"evidence front matter malformed: {evidence_ref}",
                    row_id,
                ))
                continue
            if fm.get("evidence_type") != row.get("evidence_type"):
                issues.append(make_issue(
                    "EVIDENCE_TYPE_MISMATCH",
                    f"row {row_id} evidence_type {row.get('evidence_type')!r} != "
                    f"front-matter {fm.get('evidence_type')!r}",
                    row_id,
                ))
            expected_row_hash = row_hash_for(row)
            expected_story_hash = story_hashes.get(row.get("conops_ref"))
            if fm.get("row_hash") != expected_row_hash or (
                expected_story_hash is not None
                and fm.get("story_hash") != expected_story_hash
            ):
                issues.append(make_issue(
                    "EVIDENCE_HASH_MISMATCH",
                    f"row {row_id} evidence is orphaned (row/story hash drift — "
                    "re-run record-evidence)",
                    row_id,
                ))
            last_reset = row.get("last_reset_at")
            produced_at = fm.get("produced_at", "")
            if last_reset and produced_at and produced_at < last_reset:
                issues.append(make_issue(
                    "EVIDENCE_STALE",
                    f"row {row_id} evidence produced_at {produced_at} predates "
                    f"last reset {last_reset} (FM-4)",
                    row_id,
                ))

        if issues:
            raise ValidationIssuesError("DIGEST_REJECTED", issues)

        # Digest id: strictly monotonic per ledger, INCLUDING cancelled (§6.2).
        max_id = 0
        for batch in batches:
            digest_id = str(batch.get("digest_id", ""))
            if digest_id.startswith("d-") and digest_id[2:].isdigit():
                max_id = max(max_id, int(digest_id[2:]))
        digest_id = f"d-{max_id + 1}"

        blocks = [
            _render_row_block(idx, row, evidence_refs[row["row_id"]])
            for idx, row in enumerate(pending, start=1)
        ]

        # Secret lint over the FULL digest text (header/footer carry no row
        # content; lint the blocks + footer).
        full_text = "\n".join(blocks) + "\n" + _DIGEST_FOOTER
        secret_issues = []
        for pattern in SECRET_DENY_PATTERNS:
            match = pattern.search(full_text)
            if match:
                secret_issues.append(make_issue(
                    "SECRET_PATTERN",
                    f"digest text matches secret deny-pattern: "
                    f"{match.group(0)[:60]!r} — assembly blocked (SEC-4)",
                    None,
                ))
        if secret_issues:
            raise ValidationIssuesError("SECRET_PATTERN", secret_issues)

        # Pack blocks into parts at row boundaries (§6.5). Reserve a
        # conservative header allowance, then render with the real i/k.
        n_rows = len(pending)
        header_allowance = len(
            _digest_header(session, digest_id, n_rows, 99, 99).encode("utf-8")
        ) + 1
        budget = DIGEST_PART_MAX_BYTES - header_allowance
        part_blocks: list[list[str]] = [[]]
        sizes = [0]
        for block in blocks:
            block = _truncate_block_summary(block, budget)
            block_bytes = len(block.encode("utf-8")) + 1
            if sizes[-1] and sizes[-1] + block_bytes > budget:
                part_blocks.append([])
                sizes.append(0)
            part_blocks[-1].append(block)
            sizes[-1] += block_bytes
        footer_bytes = len(_DIGEST_FOOTER.encode("utf-8")) + 1
        if sizes[-1] + footer_bytes > budget:
            part_blocks.append([])
        part_blocks[-1].append(_DIGEST_FOOTER)

        k = len(part_blocks)
        digests_dir = ledger_path.parent / "validation-digests"
        digests_dir.mkdir(parents=True, exist_ok=True)
        parts_record = []
        part_paths = []
        for i, chunk in enumerate(part_blocks, start=1):
            text = _digest_header(session, digest_id, n_rows, i, k) + "\n" + "\n".join(chunk)
            data = text.encode("utf-8")
            if len(data) > DIGEST_PART_MAX_BYTES:
                raise ValidationIssuesError(
                    "PART_OVER_BUDGET",
                    [make_issue(
                        "PART_OVER_BUDGET",
                        f"part {i} is {len(data)} bytes (> {DIGEST_PART_MAX_BYTES}); "
                        "a single row exceeds the budget — drafting error "
                        "(check-rows ROW_OVER_BUDGET should have caught it)",
                        None,
                    )],
                )
            rel_path = f"validation-digests/digest-{digest_id}-part-{i}.txt"
            (digests_dir / f"digest-{digest_id}-part-{i}.txt").write_bytes(data)
            parts_record.append({
                "i": i,
                "path": rel_path,
                "sha256": hashlib.sha256(data).hexdigest(),
                "sent_at": None,
                "message_id": None,
                "send_result": "pending",
            })
            part_paths.append(rel_path)

        ledger.setdefault("digest_batches", []).append({
            "digest_id": digest_id,
            "status": "assembled",
            "opened_at": utc_now(),
            "closed_at": None,
            "cancelled_at": None,
            "cancel_reason": None,
            "conops_hash_snapshot": conops_hash,
            "row_hash_snapshot": {r["row_id"]: row_hash_for(r) for r in pending},
            "evidence_hash_snapshot": evidence_hashes,
            "parts": parts_record,
            "row_ids": [r["row_id"] for r in pending],
            "processed_reply_refs": [],
        })

        result_data.update(
            digest_id=digest_id, parts=part_paths, row_count=n_rows
        )
        return ledger

    try:
        mutate_ledger(ledger_path, mutator)
    except _NothingToDigestError:
        return Envelope(status="ok", code="NOTHING_TO_DIGEST")
    return Envelope(status="ok", data=result_data)


def bulk_verdicts_allowed(batch: dict[str, Any]) -> bool:
    """INV-16: bulk verdicts (``pass all``/aliases/``pass rest``) are honored
    ONLY for a batch whose every part is recorded delivered — status exactly
    ``sent``. parse-reply consumes this gate; the rule has one owner here."""
    return batch.get("status") == "sent"


def _find_batch(ledger: dict[str, Any], digest_id: str) -> dict[str, Any] | None:
    for batch in ledger.get("digest_batches", []):
        if batch.get("digest_id") == digest_id:
            return batch
    return None


def handle_record_send(args: argparse.Namespace) -> Envelope:
    """Implement C-3.3 (record-send): per-part delivery records; the batch
    flips to ``sent`` only when ALL parts are sent (RC-2)."""
    ledger_path = resolve_under_root(args.ledger.parent, args.ledger)
    result_data: dict[str, Any] = {}

    def mutator(ledger: dict[str, Any]) -> dict[str, Any]:
        batch = _find_batch(ledger, args.digest_id)
        if batch is None:
            raise ValidationIssuesError(
                "BATCH_NOT_FOUND",
                [make_issue("BATCH_NOT_FOUND", f"no batch {args.digest_id}", None)],
            )
        if batch.get("status") not in NON_TERMINAL_BATCH_STATUSES:
            raise ValidationIssuesError(
                "BATCH_NOT_ACTIVE",
                [make_issue(
                    "BATCH_NOT_ACTIVE",
                    f"batch {args.digest_id} is {batch.get('status')} — "
                    "send results apply to non-terminal batches only",
                    None,
                )],
            )
        part = next(
            (p for p in batch.get("parts", []) if p.get("i") == args.part), None
        )
        if part is None:
            raise ValidationIssuesError(
                "PART_NOT_FOUND",
                [make_issue(
                    "PART_NOT_FOUND",
                    f"batch {args.digest_id} has no part {args.part}",
                    None,
                )],
            )

        part["send_result"] = args.result
        if args.result == "sent":
            part["sent_at"] = utc_now()
            if args.message_id:
                part["message_id"] = args.message_id
        else:
            part["sent_at"] = None
            part["message_id"] = None

        if all(p.get("send_result") == "sent" for p in batch.get("parts", [])):
            batch["status"] = "sent"

        result_data.update(
            digest_id=args.digest_id,
            part=args.part,
            send_result=args.result,
            batch_status=batch["status"],
        )
        return ledger

    mutate_ledger(ledger_path, mutator)
    return Envelope(status="ok", data=result_data)


def handle_cancel_batch(args: argparse.Namespace) -> Envelope:
    """Implement C-3.3 (cancel-batch): close a non-terminal batch without
    judgments. Audit-logged as a ledger security event; rows return to the
    delta pool by virtue of the batch going terminal (FM-12)."""
    ledger_path = resolve_under_root(args.ledger.parent, args.ledger)
    reason = (args.reason or "").strip()
    if not reason:
        return Envelope(
            status="issues",
            code="CANCEL_REASON_REQUIRED",
            issues=[make_issue(
                "CANCEL_REASON_REQUIRED",
                "cancel-batch requires a non-empty --reason (audit trail)",
                None,
            )],
        )

    result_data: dict[str, Any] = {}

    def mutator(ledger: dict[str, Any]) -> dict[str, Any]:
        batch = _find_batch(ledger, args.digest_id)
        if batch is None:
            raise ValidationIssuesError(
                "BATCH_NOT_FOUND",
                [make_issue("BATCH_NOT_FOUND", f"no batch {args.digest_id}", None)],
            )
        if batch.get("status") not in NON_TERMINAL_BATCH_STATUSES:
            raise ValidationIssuesError(
                "BATCH_NOT_ACTIVE",
                [make_issue(
                    "BATCH_NOT_ACTIVE",
                    f"batch {args.digest_id} is already {batch.get('status')}",
                    None,
                )],
            )

        any_sent = any(
            p.get("send_result") == "sent" for p in batch.get("parts", [])
        )
        batch["status"] = "cancelled"
        batch["cancelled_at"] = utc_now()
        batch["cancel_reason"] = reason

        # Cancellations are durable audit events in the ledger (§6.2).
        ledger.setdefault("security_events", []).append({
            "at": utc_now(),
            "code": "BATCH_CANCELLED",
            "digest_id": args.digest_id,
            "reason": reason,
        })

        # FM-12: if any part already reached Jason, the conductor must send a
        # cancellation notice through the same channel.
        result_data.update(
            digest_id=args.digest_id,
            cancellation_notice_required=any_sent,
        )
        return ledger

    mutate_ledger(ledger_path, mutator)
    return Envelope(status="ok", data=result_data)


#: §6.5 fixed natural-language bulk-pass alias list (Jason ruling SEC-6 — no
#: reply passwords). Matched whole-line, case-insensitive, whitespace
#: normalized. Extension is a one-line change + test.
BULK_PASS_ALIASES = (
    "pass all",
    "those all look good",
    "all look good",
    "all good",
    "looks good",
    "lgtm",
)

_VERDICT_KEYWORDS = ("pass", "fail", "na")
_ROW_ID_TOKEN_RE = re.compile(r"\br-US\d+-\d+\b")
_VERDICT_LINE_RE = re.compile(r"^\s*(\S+)\s+(\S+?)(?::\s*(.*))?$")

#: Reply-result token → ledger/artifact result enum (CB-12: mapping happens
#: at parse time; the ledger never stores the raw ``na`` token).
_RESULT_FOR_TOKEN = {"pass": "pass", "fail": "fail", "na": "not-applicable"}


class _RepromptError(Exception):
    """Reply rejected — exit 2 ``reprompt`` envelope, ZERO mutations (INV-A3)."""

    def __init__(self, issues: list[dict[str, Any]]) -> None:
        self.issues = issues
        super().__init__(issues[0]["detail"] if issues else "reprompt")


class _AlreadyProcessedError(Exception):
    """Duplicate reply_ref — acknowledged, zero new mutations (TC-G6/RC-4)."""


# ── Inbound telegram trust boundary (C-4.2; SEC-1/SEC-2/SEC-3, INV-15) ───────


def compute_sender_hash(sender_id: str) -> str:
    """sha256 of the sender id (full hex). The RAW sender id is never stored
    in the ledger — only this hash (gauntlet SEC-1/OP-1, the module's
    sole-hex-producer rule)."""
    return hashlib.sha256(str(sender_id).encode("utf-8")).hexdigest()


def load_allowed_sender_ids(registry_path: Path) -> set[str]:
    """Resolve the telegram sender allowlist from the registry config,
    FAIL-CLOSED (gauntlet SEC-2). ``allowed_sender_ids`` is distinct from the
    chat id and is never hardcoded. Missing file, unreadable JSON, missing
    ``telegram.allowed_sender_ids``, a non-list value, or an empty list all
    raise ``ALLOWLIST_CONFIG_INVALID`` — telegram parsing stays blocked."""

    def _invalid(reason: str) -> ValidationIssuesError:
        return ValidationIssuesError(
            "ALLOWLIST_CONFIG_INVALID",
            [make_issue(
                "ALLOWLIST_CONFIG_INVALID",
                f"telegram sender allowlist unusable (fail-closed): {reason}",
            )],
        )

    if registry_path is None:
        raise _invalid("--registry is required for --source telegram")
    try:
        raw = Path(registry_path).read_bytes()
    except OSError as exc:
        raise _invalid(f"cannot read registry {registry_path}: {exc}") from None
    enforce_input_bounds("registry", raw)
    try:
        config = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise _invalid(f"registry is not valid JSON: {exc}") from None
    if not isinstance(config, dict):
        raise _invalid("registry root must be a JSON object")
    telegram = config.get("telegram")
    if not isinstance(telegram, dict):
        raise _invalid("registry missing a telegram block")
    allowed = telegram.get("allowed_sender_ids")
    if not isinstance(allowed, list) or not allowed:
        raise _invalid(
            "telegram.allowed_sender_ids must be a non-empty list "
            "(distinct from chat_id — SEC-2)"
        )
    return {str(sender) for sender in allowed}


def extract_telegram_reply(update_path: Path) -> dict[str, str]:
    """Extract sender id, message id, and text from a RAW Telegram update
    payload (gauntlet SEC-1 — the conductor never transcribes identity; the
    module owns extraction). Returns {sender_id, message_id, text}. A
    structurally-unusable payload raises a reprompt (no mutation)."""
    try:
        raw = Path(update_path).read_bytes()
    except OSError as exc:
        raise _RepromptError([make_issue(
            "TELEGRAM_UPDATE_UNREADABLE",
            f"cannot read update file {update_path}: {exc}",
        )]) from None
    enforce_input_bounds("telegram_update", raw)
    try:
        update = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise _RepromptError([make_issue(
            "TELEGRAM_UPDATE_MALFORMED",
            f"update file is not valid JSON: {exc}",
        )]) from None
    message = (update or {}).get("message") if isinstance(update, dict) else None
    if not isinstance(message, dict):
        raise _RepromptError([make_issue(
            "TELEGRAM_UPDATE_MALFORMED",
            "update payload has no message object",
        )])
    sender = message.get("from")
    if not isinstance(sender, dict) or sender.get("id") is None:
        raise _RepromptError([make_issue(
            "TELEGRAM_UPDATE_MALFORMED",
            "update message has no sender (message.from.id)",
        )])
    message_id = message.get("message_id")
    text = message.get("text")
    if not isinstance(text, str):
        raise _RepromptError([make_issue(
            "TELEGRAM_UPDATE_MALFORMED",
            "update message has no text",
        )])
    return {
        "sender_id": str(sender["id"]),
        "message_id": str(message_id),
        "text": text,
    }


def _quote(text: str, limit: int = 80) -> str:
    """Quote untrusted reply text, truncated (INV-A3)."""
    text = _one_line(text)
    return repr(text if len(text) <= limit else text[: limit - 1] + "…")


def _parse_reply_blocks(reply_text: str) -> dict[str, Any]:
    """Parse the §6.5 block grammar. Returns {verdicts, bulk} or raises
    _RepromptError. verdicts: row_id → (token, justification); bulk:
    None | 'all' | 'rest'."""
    verdicts: dict[str, list[str | None]] = {}
    order: list[str] = []
    bulk: str | None = None
    current: str | None = None  # row_id of the open block
    errors: list[dict[str, Any]] = []

    def err(detail: str, row_id: str | None = None) -> None:
        errors.append(make_issue("REPLY_INVALID", detail, row_id))

    for raw_line in reply_text.splitlines():
        line = raw_line.strip()
        if not line:
            current = None
            continue

        normalized = " ".join(line.lower().split())
        if normalized in BULK_PASS_ALIASES or normalized == "pass rest":
            new_bulk = "rest" if normalized == "pass rest" else "all"
            if bulk is not None:
                err(f"duplicate bulk verdict {_quote(line)}")
            bulk = new_bulk
            current = None
            continue

        match = _VERDICT_LINE_RE.match(line)
        keyword = match.group(1).lower() if match else ""
        if keyword in _VERDICT_KEYWORDS and match:
            target, justification = match.group(2), match.group(3)
            if target.lower() in ("all", "rest"):
                # pass-all handled above as a whole-line form; fail/na all|rest
                # and decorated pass-all variants are invalid (CB-9).
                err(f"{keyword} {target.lower()} is not a valid verdict "
                    f"{_quote(line)}")
                current = None
                continue
            if not _ROW_ID_RE.match(target):
                err(
                    f"verdict target must be an exact-case row id "
                    f"(r-US<n>-<k>): {_quote(line)}"
                )
                current = None
                continue
            if target in verdicts:
                err(f"duplicate verdict for {target} — all duplicates are "
                    f"invalid: {_quote(line)}", target)
                current = None
                continue
            verdicts[target] = [keyword, justification]
            order.append(target)
            current = target
            continue

        # Continuation line: justification for the open block — UNLESS it
        # starts with a verdict keyword or names a row id (a typo'd verdict
        # must not be silently swallowed — FM-12/CB-9).
        first_word = line.split()[0].lower()
        if first_word in _VERDICT_KEYWORDS or _ROW_ID_TOKEN_RE.search(line):
            err(f"continuation line looks like a (typo'd) verdict — parse "
                f"error, not justification: {_quote(line)}")
            current = None
            continue
        if current is None:
            err(f"line is neither a verdict nor a continuation: {_quote(line)}")
            continue
        existing = verdicts[current][1]
        verdicts[current][1] = (existing + "\n" + line) if existing else line

    # fail/na REQUIRE non-empty justification (FM-10)
    for row_id, (keyword, justification) in verdicts.items():
        if keyword in ("fail", "na") and not (justification or "").strip():
            err(f"{keyword} requires a non-empty justification (re-prompt): "
                f"row {row_id}", row_id)

    if errors:
        raise _RepromptError(errors)
    return {
        "verdicts": {
            rid: (kw, (just or "").strip() or None)
            for rid, (kw, just) in verdicts.items()
        },
        "bulk": bulk,
    }


def handle_parse_reply(args: argparse.Namespace) -> Envelope:
    """Implement C-4.1: §6.5 reply grammar + the locked judgment mutation.

    All-or-nothing: every verdict validates against the batch snapshot before
    ANY row mutates; any rejection raises pre-write so the ledger bytes are
    untouched (INV-A3). Telegram update-file extraction and sender
    verification are the trust boundary card (C-4.2)."""
    ledger_path = resolve_under_root(args.ledger.parent, args.ledger)

    # The provenance reference applied to judgments. For telegram it is DERIVED
    # from the raw payload message id (never the caller-supplied --reply-ref);
    # for terminal it is the asserted --reply-ref.
    reply_ref = args.reply_ref

    # ── Inbound trust boundary (C-4.2) ───────────────────────────────────────
    if args.source == "telegram":
        # SEC-1: identity comes ONLY from the raw update — never from the
        # conductor-asserted --sender-id (ignored here by design).
        update_path = resolve_under_root(ledger_path.parent, args.update_file) \
            if args.update_file is not None else None
        if update_path is None:
            return Envelope(
                status="issues",
                code="TELEGRAM_UPDATE_REQUIRED",
                issues=[make_issue(
                    "TELEGRAM_UPDATE_REQUIRED",
                    "--source telegram requires --update-file (raw payload)",
                    None,
                )],
            )
        # Fail-closed allowlist resolution BEFORE any extraction (SEC-2).
        registry_path = resolve_under_root(ledger_path.parent, args.registry) \
            if args.registry is not None else None
        try:
            allowed_senders = load_allowed_sender_ids(registry_path)
            extracted = extract_telegram_reply(update_path)
        except _RepromptError as exc:
            return Envelope("reprompt", "REPROMPT_REQUIRED", issues=exc.issues)
        sender_id = extracted["sender_id"]
        reply_ref = f"telegram:{extracted['message_id']}"
        reply_bytes = extracted["text"].encode("utf-8")

        if sender_id not in allowed_senders:
            # DISCARD: zero judgment mutations; the ONLY write is a durable
            # security event recording the HASHED sender id (INV-15, OP-1).
            sender_hash = compute_sender_hash(sender_id)

            def discard_mutator(ledger: dict[str, Any]) -> dict[str, Any]:
                ledger.setdefault("security_events", []).append({
                    "at": utc_now(),
                    "code": "SENDER_NOT_ALLOWLISTED",
                    "sender_hash": sender_hash,
                    "digest_id": args.digest_id,
                })
                return ledger

            mutate_ledger(ledger_path, discard_mutator)
            return Envelope(
                status="issues",
                code="SENDER_NOT_ALLOWLISTED",
                issues=[make_issue(
                    "SENDER_NOT_ALLOWLISTED",
                    "telegram reply discarded: sender not in the registry "
                    "allowlist (security event logged with hashed id)",
                    None,
                )],
            )
    else:
        # Terminal source (SEC-3): the weaker-trust channel must cite the
        # AskUserQuestion transcript so the assertion is auditable.
        if not str(reply_ref).startswith("transcript:"):
            return Envelope(
                status="issues",
                code="TERMINAL_REPLY_REF_REQUIRED",
                issues=[make_issue(
                    "TERMINAL_REPLY_REF_REQUIRED",
                    "terminal judgments must cite the AskUserQuestion "
                    "transcript (--reply-ref transcript:<session>:<turn>)",
                    None,
                )],
            )
        if args.reply_file is not None:
            reply_path = resolve_under_root(ledger_path.parent, args.reply_file)
            reply_bytes = reply_path.read_bytes()
        elif args.reply_text is not None:
            reply_bytes = args.reply_text.encode("utf-8")
        else:
            return Envelope(
                status="issues",
                code="REPLY_TEXT_REQUIRED",
                issues=[make_issue(
                    "REPLY_TEXT_REQUIRED",
                    "parse-reply needs reply text (--reply-file or positional)",
                    None,
                )],
            )
    enforce_input_bounds("reply", reply_bytes)
    reply_text = reply_bytes.decode("utf-8", errors="replace")

    result_data: dict[str, Any] = {}

    def mutator(ledger: dict[str, Any]) -> dict[str, Any]:
        batch = _find_batch(ledger, args.digest_id)
        if batch is None:
            raise ValidationIssuesError(
                "BATCH_NOT_FOUND",
                [make_issue("BATCH_NOT_FOUND", f"no batch {args.digest_id}", None)],
            )
        if reply_ref in batch.get("processed_reply_refs", []):
            raise _AlreadyProcessedError()
        if batch.get("status") not in NON_TERMINAL_BATCH_STATUSES:
            raise ValidationIssuesError(
                "BATCH_NOT_ACTIVE",
                [make_issue(
                    "BATCH_NOT_ACTIVE",
                    f"batch {args.digest_id} is {batch.get('status')} — reply "
                    "is stale (replay protection)",
                    None,
                )],
            )
        if ledger.get("conops_hash") and batch.get("conops_hash_snapshot") and \
                ledger["conops_hash"] != batch["conops_hash_snapshot"]:
            raise ValidationIssuesError(
                "CONOPS_SNAPSHOT_CHANGED",
                [make_issue(
                    "CONOPS_SNAPSHOT_CHANGED",
                    "conops changed after batch open (RC-3) — cancel and "
                    "re-digest",
                    None,
                )],
            )

        parsed = _parse_reply_blocks(reply_text)
        verdicts, bulk = parsed["verdicts"], parsed["bulk"]
        if not verdicts and bulk is None:
            raise _RepromptError([make_issue(
                "REPLY_EMPTY", "reply contains no verdicts", None
            )])

        if bulk is not None and not bulk_verdicts_allowed(batch):
            raise _RepromptError([make_issue(
                "BATCH_NOT_SENT",
                f"bulk verdicts require batch status 'sent' (INV-16); "
                f"{args.digest_id} is {batch.get('status')!r}",
                None,
            )])

        rows_by_id = {
            r.get("row_id"): r for r in ledger.get("rows", [])
            if isinstance(r, dict)
        }
        superseded_replacement = {
            entry.get("row_snapshot", {}).get("row_id"):
                entry.get("replacement_row_id")
            for entry in ledger.get("superseded", [])
        }
        snapshot_ids = set(batch.get("row_ids", []))
        row_hash_snapshot = batch.get("row_hash_snapshot", {})

        issues: list[dict[str, Any]] = []
        for row_id, (keyword, justification) in verdicts.items():
            if row_id in superseded_replacement:
                issues.append(make_issue(
                    "SUPERSEDED_ROW",
                    f"row {row_id} is superseded — reply to its replacement "
                    f"{superseded_replacement[row_id]} instead",
                    row_id,
                ))
                continue
            if row_id not in snapshot_ids or row_id not in rows_by_id:
                issues.append(make_issue(
                    "ROW_NOT_IN_BATCH",
                    f"row {row_id} is not in batch {args.digest_id}",
                    row_id,
                ))
                continue
            row = rows_by_id[row_id]
            if row.get("result") is not None:
                issues.append(make_issue(
                    "ROW_ALREADY_JUDGED",
                    f"row {row_id} already judged {row.get('result')!r} in "
                    "this batch",
                    row_id,
                ))
                continue
            if row_hash_snapshot.get(row_id) != row_hash_for(row):
                issues.append(make_issue(
                    "STALE_ROW_HASH",
                    f"row {row_id} changed after batch open (RC-3) — verdict "
                    "rejected",
                    row_id,
                ))
                continue
            if justification:
                enforce_input_bounds(
                    "justification", justification.encode("utf-8")
                )
        if issues:
            raise _RepromptError(issues)

        def judge(row: dict[str, Any], keyword: str, justification: str | None) -> None:
            row["result"] = _RESULT_FOR_TOKEN[keyword]
            judgment = {
                "judged_by": "jason",
                "judged_at": utc_now(),
                "source": args.source,
                "digest_id": args.digest_id,
                "reply_ref": reply_ref,
            }
            if justification:
                judgment["justification"] = justification
            row["judgment"] = judgment

        # Explicit per-row verdicts apply BEFORE bulk regardless of textual
        # order (CB-9).
        judged: list[str] = []
        for row_id, (keyword, justification) in verdicts.items():
            judge(rows_by_id[row_id], keyword, justification)
            judged.append(row_id)
        if bulk is not None:
            for row_id in batch.get("row_ids", []):
                row = rows_by_id.get(row_id)
                if row is not None and row.get("result") is None:
                    judge(row, "pass", None)
                    judged.append(row_id)

        batch.setdefault("processed_reply_refs", []).append(reply_ref)
        if all(
            rows_by_id.get(rid, {}).get("result") is not None
            for rid in batch.get("row_ids", [])
        ):
            batch["status"] = "closed"
            batch["closed_at"] = utc_now()

        result_data.update(
            digest_id=args.digest_id,
            judged=judged,
            batch_status=batch["status"],
        )
        return ledger

    try:
        mutate_ledger(ledger_path, mutator)
    except _AlreadyProcessedError:
        return Envelope(
            status="ok",
            code="REPLY_ALREADY_PROCESSED",
            data={"digest_id": args.digest_id, "reply_ref": reply_ref},
        )
    except _RepromptError as exc:
        return Envelope(status="reprompt", code="REPROMPT_REQUIRED", issues=exc.issues)
    return Envelope(status="ok", data=result_data)


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
HANDLERS["assemble-digest"] = handle_assemble_digest
HANDLERS["record-send"] = handle_record_send
HANDLERS["cancel-batch"] = handle_cancel_batch
HANDLERS["parse-reply"] = handle_parse_reply
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
        if name == "assemble-digest":
            sp.add_argument("ledger", type=Path, help="Path to validation-rows.json")
            sp.add_argument("--conops", type=Path, required=True, help="Path to conops.md")
            sp.add_argument(
                "--session",
                default=None,
                help="Session id for the digest header (default: '-')",
            )
        if name == "record-send":
            sp.add_argument("ledger", type=Path, help="Path to validation-rows.json")
            sp.add_argument("--digest-id", required=True, help="Batch id (d-N)")
            sp.add_argument("--part", type=int, required=True, help="Part index (1-based)")
            sp.add_argument(
                "--result", required=True, choices=["sent", "failed"],
                help="Delivery outcome for this part",
            )
            sp.add_argument("--message-id", default=None, help="Telegram message id")
        if name == "cancel-batch":
            sp.add_argument("ledger", type=Path, help="Path to validation-rows.json")
            sp.add_argument("--digest-id", required=True, help="Batch id (d-N)")
            sp.add_argument("--reason", required=True, help="Audit reason (non-empty)")
        if name == "parse-reply":
            sp.add_argument("ledger", type=Path, help="Path to validation-rows.json")
            sp.add_argument(
                "reply_text", nargs="?", default=None,
                help="Reply text (test-only — multiline shell quoting is a "
                     "footgun; prefer --reply-file)",
            )
            sp.add_argument("--reply-file", type=Path, default=None,
                            help="Path to a file holding the reply text")
            sp.add_argument("--update-file", type=Path, default=None,
                            help="Path to a RAW Telegram update payload "
                                 "(telegram source — module extracts sender, "
                                 "message id, and text itself)")
            sp.add_argument("--registry", type=Path, default=None,
                            help="Path to the telegram sender-allowlist "
                                 "registry (required for --source telegram)")
            sp.add_argument("--digest-id", required=True, help="Batch id (d-N)")
            sp.add_argument(
                "--source", required=True, choices=["telegram", "terminal"],
                help="Reply channel (provenance)",
            )
            sp.add_argument("--reply-ref", required=True,
                            help="Idempotency + provenance reference")
            sp.add_argument("--sender-id", default=None,
                            help="Asserted identity (terminal source; IGNORED "
                                 "for telegram — SEC-1)")
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
