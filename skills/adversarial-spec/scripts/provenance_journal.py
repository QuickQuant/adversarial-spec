"""Append-only provenance journal for test/node classification decisions."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

from filelock import FileLock

SUBJECT_TYPES = ("test", "node")
EVENT_TYPES = (
    "created",
    "field_changed",
    "rename",
    "tombstone",
    "replace",
    "split",
    "merge",
)
DRIVER_TYPES = (
    "guardrail",
    "debate_round",
    "human_correction",
    "promotion",
    "depth_triage",
    "reclassification",
    "close_attestation",
    "run_evidence",
    "decision",
)
INDEX_VERSION = 1

DECISION_ID_RE = re.compile(r"\bdecision_id=(?P<decision_id>[A-Za-z0-9_.:-]+)\b")


class ProvenanceJournalError(ValueError):
    """Base error for provenance journal contract violations."""


class StaleExpectedFromError(ProvenanceJournalError):
    """Raised when a transition is based on stale current state."""


@dataclass(frozen=True)
class JournalTransition:
    """One accepted state change to append to the journal."""

    session_id: str
    subject_type: Literal["test", "node"]
    subject_id: str
    field: str
    from_value: Any
    to_value: Any
    expected_from: Any
    driver: dict[str, str]
    idempotency_key: str
    event_type: Literal[
        "created",
        "field_changed",
        "rename",
        "tombstone",
        "replace",
        "split",
        "merge",
    ] = "field_changed"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.subject_type not in SUBJECT_TYPES:
            raise ProvenanceJournalError(
                f"unsupported subject_type: {self.subject_type!r}"
            )
        if self.event_type not in EVENT_TYPES:
            raise ProvenanceJournalError(f"unsupported event_type: {self.event_type!r}")
        if not self.session_id.strip():
            raise ProvenanceJournalError("session_id is required")
        if not self.subject_id.strip():
            raise ProvenanceJournalError("subject_id is required")
        if not self.field.strip():
            raise ProvenanceJournalError("field is required")
        if not self.idempotency_key.strip():
            raise ProvenanceJournalError("idempotency_key is required")
        driver_type = self.driver.get("type")
        driver_ref = self.driver.get("ref")
        if driver_type not in DRIVER_TYPES or not driver_ref:
            raise ProvenanceJournalError(
                "driver must include type and ref; type must be canonical"
            )

    @property
    def subject_key(self) -> str:
        return _subject_key(self.subject_type, self.subject_id)


@dataclass(frozen=True)
class AppendReceipt:
    """Append result. Replayed idempotency returns ``appended=False``."""

    record: dict[str, Any]
    appended: bool


class ProvenanceJournalWriter:
    """Locked append-only JSONL writer with a sidecar replay index."""

    def __init__(self, journal_path: Path) -> None:
        self.journal_path = Path(journal_path)
        self.index_path = self.journal_path.with_suffix(
            self.journal_path.suffix + ".index.json"
        )
        self.lock_path = self.journal_path.with_suffix(
            self.journal_path.suffix + ".lock"
        )
        self.lock = FileLock(str(self.lock_path))

    def append_transition(
        self,
        transition: JournalTransition,
        *,
        current_fallback: Any = None,
    ) -> AppendReceipt:
        """Append one transition unless its idempotency key is already present."""

        with self.lock:
            index = self._load_index()
            return self._append_transition_locked(
                transition,
                index=index,
                current_fallback=current_fallback,
            )

    def replay_subject(
        self,
        subject_type: Literal["test", "node"],
        subject_id: str,
    ) -> list[dict[str, Any]]:
        """Replay one subject using the sidecar index, not a full JSONL scan."""

        with self.lock:
            index = self._load_index()
            entries = index["subjects"].get(_subject_key(subject_type, subject_id), [])
            records: list[dict[str, Any]] = []
            with self.journal_path.open("rb") as journal:
                for entry in entries:
                    journal.seek(entry["offset"])
                    line = journal.read(entry["length"])
                    records.append(json.loads(line.decode("utf-8")))
            return records

    def current_value(
        self,
        subject_type: Literal["test", "node"],
        subject_id: str,
        field_name: str,
    ) -> Any:
        """Return the indexed current value for one subject field."""

        with self.lock:
            index = self._load_index()
            return index["current"].get(_subject_key(subject_type, subject_id), {}).get(
                field_name
            )

    def apply_registry_transition(
        self,
        registry_path: Path,
        transition: JournalTransition,
        update_registry: Callable[[dict[str, Any]], dict[str, Any]],
        *,
        current_fallback: Any = None,
    ) -> AppendReceipt:
        """Apply a registry mutation and append its journal record under locks.

        The registry write happens before the journal append. If append fails,
        the registry bytes are rolled back, preventing an orphan journal record
        for an update that did not land in the registry.
        """

        registry_path = Path(registry_path)
        with _ordered_file_locks(self.lock_path, registry_path.with_suffix(".lock")):
            index = self._load_index()
            self._assert_transition_is_fresh(
                transition,
                index=index,
                current_fallback=current_fallback,
            )

            previous_bytes = (
                registry_path.read_bytes() if registry_path.exists() else None
            )
            registry = _load_json_object(registry_path)
            updated_registry = update_registry(copy.deepcopy(registry))
            _write_json_atomic(registry_path, updated_registry)

            try:
                return self._append_transition_locked(
                    transition,
                    index=index,
                    current_fallback=current_fallback,
                    freshness_already_checked=True,
                )
            except BaseException:
                _restore_bytes(registry_path, previous_bytes)
                raise

    def rename_tmr(
        self,
        registry_path: Path,
        *,
        tmr_uid: str,
        new_test_id: str | None = None,
        new_user_story: str | None = None,
        new_title: str | None = None,
        session_id: str,
        driver: dict[str, str],
        idempotency_key: str,
    ) -> AppendReceipt:
        """Rename a TMR coordinate while preserving its stable ``tmr_uid``."""

        registry = _load_json_object(registry_path)
        current_record = _find_tmr(registry, tmr_uid)
        old_coordinates = _coordinates(current_record)
        new_coordinates = {
            "test_id": new_test_id or current_record.get("test_id"),
            "user_story": new_user_story or current_record.get("user_story"),
            "title": new_title or current_record.get("title"),
        }
        transition = JournalTransition(
            session_id=session_id,
            subject_type="test",
            subject_id=tmr_uid,
            event_type="rename",
            field="coordinates",
            from_value=old_coordinates,
            to_value=new_coordinates,
            expected_from=old_coordinates,
            driver=driver,
            idempotency_key=idempotency_key,
        )

        def update(registry_payload: dict[str, Any]) -> dict[str, Any]:
            record = _find_tmr(registry_payload, tmr_uid)
            record.update({k: v for k, v in new_coordinates.items() if v is not None})
            return registry_payload

        return self.apply_registry_transition(
            registry_path,
            transition,
            update,
            current_fallback=old_coordinates,
        )

    def replace_tmr(
        self,
        registry_path: Path,
        *,
        old_tmr_uid: str,
        new_record: dict[str, Any],
        tombstoned_at: str,
        session_id: str,
        driver: dict[str, str],
        idempotency_key: str,
    ) -> AppendReceipt:
        """Tombstone one TMR and add a replacement that supersedes it."""

        if new_record.get("tmr_uid") == old_tmr_uid:
            raise ProvenanceJournalError("replacement must mint a new tmr_uid")
        supersedes = list(new_record.get("supersedes") or [])
        if old_tmr_uid not in supersedes:
            supersedes.append(old_tmr_uid)
        replacement = copy.deepcopy(new_record)
        replacement["supersedes"] = supersedes
        replacement.setdefault("status", "active")

        registry = _load_json_object(registry_path)
        old_record = _find_tmr(registry, old_tmr_uid)
        transition = JournalTransition(
            session_id=session_id,
            subject_type="test",
            subject_id=old_tmr_uid,
            event_type="replace",
            field="status",
            from_value=old_record.get("status", "active"),
            to_value="tombstoned",
            expected_from=old_record.get("status", "active"),
            driver=driver,
            idempotency_key=idempotency_key,
            metadata={"replacement_tmr_uid": replacement["tmr_uid"]},
        )

        def update(registry_payload: dict[str, Any]) -> dict[str, Any]:
            record = _find_tmr(registry_payload, old_tmr_uid)
            record["status"] = "tombstoned"
            record["tombstoned_at"] = tombstoned_at
            _records(registry_payload).append(replacement)
            return registry_payload

        return self.apply_registry_transition(
            registry_path,
            transition,
            update,
            current_fallback=old_record.get("status", "active"),
        )

    def _append_transition_locked(
        self,
        transition: JournalTransition,
        *,
        index: dict[str, Any],
        current_fallback: Any = None,
        freshness_already_checked: bool = False,
    ) -> AppendReceipt:
        duplicate = index["idempotency"].get(transition.idempotency_key)
        if duplicate is not None:
            return AppendReceipt(
                record=self._read_indexed_record(duplicate),
                appended=False,
            )

        if not freshness_already_checked:
            self._assert_transition_is_fresh(
                transition,
                index=index,
                current_fallback=current_fallback,
            )

        record = _record_for_transition(transition)
        line = (_canonical_json(record) + "\n").encode("utf-8")
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(
            self.journal_path,
            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
            0o644,
        )
        try:
            offset = os.path.getsize(self.journal_path)
            os.write(fd, line)
            os.fsync(fd)
        finally:
            os.close(fd)

        entry = {"offset": offset, "length": len(line)}
        index["journal_size"] = offset + len(line)
        index["subjects"].setdefault(transition.subject_key, []).append(entry)
        index["idempotency"][transition.idempotency_key] = {
            **entry,
            "record_id": record["record_id"],
        }
        index["current"].setdefault(transition.subject_key, {})[
            transition.field
        ] = transition.to_value
        _write_json_atomic(self.index_path, index)
        return AppendReceipt(record=record, appended=True)

    def _assert_transition_is_fresh(
        self,
        transition: JournalTransition,
        *,
        index: dict[str, Any],
        current_fallback: Any = None,
    ) -> None:
        current = index["current"].get(transition.subject_key, {}).get(
            transition.field,
            current_fallback,
        )
        if current != transition.expected_from:
            raise StaleExpectedFromError(
                "stale expected_from for "
                f"{transition.subject_type}:{transition.subject_id}.{transition.field}: "
                f"expected {transition.expected_from!r}, current {current!r}"
            )

    def _read_indexed_record(self, entry: dict[str, Any]) -> dict[str, Any]:
        with self.journal_path.open("rb") as journal:
            journal.seek(entry["offset"])
            return json.loads(journal.read(entry["length"]).decode("utf-8"))

    def _load_index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return _empty_index()
        with self.index_path.open("r", encoding="utf-8") as handle:
            index = json.load(handle)
        if index.get("version") != INDEX_VERSION:
            raise ProvenanceJournalError("unsupported journal index version")
        index.setdefault("subjects", {})
        index.setdefault("idempotency", {})
        index.setdefault("current", {})
        index.setdefault("journal_size", 0)
        return index


def active_spine_records(
    registry: dict[str, Any],
    user_story: str,
) -> list[dict[str, Any]]:
    """Return active spine TMRs for the F-prime coverage check."""

    return [
        record
        for record in _records(registry)
        if record.get("status", "active") == "active"
        and record.get("user_story") == user_story
        and record.get("spine") is True
    ]


def append_decision_log(
    decisions_log_path: Path,
    *,
    decision_id: str,
    text: str,
    timestamp: str | None = None,
) -> str:
    """Append one plain-text decision-log line with a stable decision_id."""

    if not decision_id.strip():
        raise ProvenanceJournalError("decision_id is required")
    timestamp = timestamp or _utc_now()
    line = f"{timestamp} decision_id={decision_id} {text.rstrip()}\n"
    decisions_log_path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(decisions_log_path.with_suffix(".lock"))):
        fd = os.open(
            decisions_log_path,
            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
            0o644,
        )
        try:
            os.write(fd, line.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)
    return line


def extract_decision_ids(decisions_log_text: str) -> set[str]:
    """Extract stable decision IDs from the live plain-text log format."""

    return {match.group("decision_id") for match in DECISION_ID_RE.finditer(decisions_log_text)}


def write_pending_dispositions(
    pending_path: Path,
    payload: dict[str, Any],
) -> None:
    """Write pending dispositions through the same locked atomic JSON path."""

    with FileLock(str(pending_path.with_suffix(".lock"))):
        _write_json_atomic(pending_path, payload)


def _record_for_transition(transition: JournalTransition) -> dict[str, Any]:
    base = {
        "session_id": transition.session_id,
        "subject_type": transition.subject_type,
        "subject_id": transition.subject_id,
        "event_type": transition.event_type,
        "field": transition.field,
        "from": transition.from_value,
        "to": transition.to_value,
        "expected_from": transition.expected_from,
        "driver": transition.driver,
        "idempotency_key": transition.idempotency_key,
        "metadata": transition.metadata,
        "occurred_at": _utc_now(),
    }
    base["record_id"] = _record_id(base)
    return base


def _empty_index() -> dict[str, Any]:
    return {
        "version": INDEX_VERSION,
        "journal_size": 0,
        "subjects": {},
        "idempotency": {},
        "current": {},
    }


def _subject_key(subject_type: str, subject_id: str) -> str:
    return f"{subject_type}:{subject_id}"


def _record_id(record_without_id: dict[str, Any]) -> str:
    stable = copy.deepcopy(record_without_id)
    stable["nonce"] = uuid.uuid4().hex
    digest = hashlib.sha256(_canonical_json(stable).encode("utf-8")).hexdigest()
    return f"pjr_{digest[:24]}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00",
        "Z",
    )


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"records": []}
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ProvenanceJournalError(f"{path} must contain a JSON object")
    payload.setdefault("records", [])
    return payload


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        _fsync_dir(path.parent)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def _restore_bytes(path: Path, previous_bytes: bytes | None) -> None:
    if previous_bytes is None:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.rollback.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(previous_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        _fsync_dir(path.parent)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _ordered_file_locks(*lock_paths: Path):
    ordered = sorted({str(path) for path in lock_paths})
    return _MultiFileLock([FileLock(path) for path in ordered])


class _MultiFileLock:
    def __init__(self, locks: list[Any]) -> None:
        self.locks = locks

    def __enter__(self) -> "_MultiFileLock":
        for lock in self.locks:
            lock.acquire()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        for lock in reversed(self.locks):
            lock.release()


def _records(registry: dict[str, Any]) -> list[dict[str, Any]]:
    records = registry.setdefault("records", [])
    if not isinstance(records, list):
        raise ProvenanceJournalError("registry.records must be a list")
    return records


def _find_tmr(registry: dict[str, Any], tmr_uid: str) -> dict[str, Any]:
    for record in _records(registry):
        if record.get("tmr_uid") == tmr_uid:
            return record
    raise ProvenanceJournalError(f"unknown tmr_uid: {tmr_uid}")


def _coordinates(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "test_id": record.get("test_id"),
        "user_story": record.get("user_story"),
        "title": record.get("title"),
    }
