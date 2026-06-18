"""Compile authored prose test records into the strict TMR registry."""

from __future__ import annotations

import json
import secrets
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, cast

from tmr_parser import TmrParser
from tmr_schema import SchemaValidationError, TestMaturityRecord, dump_tmr_record

CROCKFORD32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
ULID_LENGTH = 26


class HumanConfirmationRequiredError(RuntimeError):
    """Raised when a registry write is attempted before echo-diff approval."""


@dataclass(frozen=True)
class CompileCandidate:
    """One LLM-emitted candidate plus compiler-owned authoring metadata."""

    anchor: str
    record: dict[str, object]


@dataclass(frozen=True)
class SemanticDiffEvent:
    event: Literal["add", "remove", "rename", "update"]
    tmr_uid: str
    changes: dict[str, dict[str, object | None]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "event": self.event,
            "tmr_uid": self.tmr_uid,
            "changes": self.changes,
        }


@dataclass(frozen=True)
class TmrCompileResult:
    records: list[dict[str, object]]
    prose_view: str
    echo_diff: list[SemanticDiffEvent]
    requires_human_confirm: bool = True

    def registry_json(self) -> str:
        return json.dumps(self.records, indent=2, sort_keys=True)

    def echo_diff_json(self) -> str:
        return json.dumps(
            [event.to_dict() for event in self.echo_diff],
            indent=2,
            sort_keys=True,
        )


def compile_tmr_records(
    candidates: Sequence[CompileCandidate | Mapping[str, object]],
    *,
    existing_records: Sequence[Mapping[str, object]] | None = None,
    accessor_symbols: Mapping[str, str] | set[str] | frozenset[str] | None = None,
    uid_factory: Callable[[], str] | None = None,
) -> TmrCompileResult:
    """Compile LLM-emitted records and return a pending human-confirm result.

    The LLM may preserve an existing ``tmr_uid`` from a regenerated prose view,
    but it may not allocate a new one. New records receive compiler-minted
    ULIDs immediately before TmrParser validation.
    """

    uid_factory = uid_factory or mint_ulid
    existing = _parse_records(existing_records or [])
    existing_by_uid = {record["tmr_uid"]: record for record in existing}
    existing_by_test_id = {record["test_id"]: record for record in existing}

    seen_anchors: set[str] = set()
    seen_uids: set[str] = set()
    compiled: list[dict[str, object]] = []
    for raw_candidate in candidates:
        candidate = _coerce_candidate(raw_candidate)
        if candidate.anchor in seen_anchors:
            raise SchemaValidationError("anchor", f"Duplicate anchor: {candidate.anchor}")
        seen_anchors.add(candidate.anchor)

        record = dict(candidate.record)
        _resolve_accessors(record, accessor_symbols)
        tmr_uid = record.get("tmr_uid")
        if tmr_uid is None:
            previous = existing_by_test_id.get(record.get("test_id"))
            record["tmr_uid"] = (
                previous["tmr_uid"] if previous else _validate_minted_uid(uid_factory())
            )
        elif not isinstance(tmr_uid, str):
            raise SchemaValidationError("tmr_uid", "tmr_uid must be a string")
        elif tmr_uid not in existing_by_uid:
            raise SchemaValidationError(
                "tmr_uid",
                "LLM-emitted tmr_uid is not allowed for new records; compiler mints first emit identity",
            )

        resolved_uid = str(record["tmr_uid"])
        if resolved_uid in seen_uids:
            raise SchemaValidationError("tmr_uid", f"Duplicate tmr_uid: {resolved_uid}")
        seen_uids.add(resolved_uid)
        compiled.append(record)

    parsed = _parse_records(compiled)
    echo_diff = _diff_by_tmr_uid(existing, parsed)
    return TmrCompileResult(
        records=parsed,
        prose_view=render_prose_view(parsed),
        echo_diff=echo_diff,
    )


def write_confirmed_registry(
    path: Path,
    result: TmrCompileResult,
    *,
    confirmed: bool,
) -> None:
    """Write compiled registry bytes only after the human accepts echo-diff."""

    if not confirmed:
        raise HumanConfirmationRequiredError(
            "human confirmation required before registry write"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.registry_json() + "\n", encoding="utf-8")


def render_prose_view(records: Sequence[Mapping[str, object]]) -> str:
    lines = ["# TMR Prose View", ""]
    for record in records:
        accessors = record.get("accessors", [])
        accessor_text = ", ".join(cast(list[str], accessors)) if accessors else "(none)"
        lines.extend(
            [
                f"## {record['test_id']} — {record['title']}",
                f"- tmr_uid: {record['tmr_uid']}",
                f"- user_story: {record['user_story']}",
                f"- maturity: {record['maturity']}",
                f"- data_strategy: {record['data_strategy']}",
                f"- accessors: {accessor_text}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def mint_ulid() -> str:
    """Return a 26-char Crockford-base32 ULID using current ms + randomness."""

    timestamp_ms = int(time.time() * 1000)
    random_bits = secrets.randbits(80)
    value = (timestamp_ms << 80) | random_bits
    chars = []
    for shift in range(125, -1, -5):
        chars.append(CROCKFORD32[(value >> shift) & 0b11111])
    return "".join(chars)


def _validate_minted_uid(tmr_uid: str) -> str:
    if len(tmr_uid) != ULID_LENGTH or any(char not in CROCKFORD32 for char in tmr_uid):
        raise SchemaValidationError(
            "tmr_uid", "compiler-minted tmr_uid must be a 26-character ULID"
        )
    return tmr_uid


def _parse_records(records: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    parsed: list[TestMaturityRecord] = TmrParser.parse_string(json.dumps(list(records)))
    return [dump_tmr_record(record) for record in parsed]


def _coerce_candidate(candidate: CompileCandidate | Mapping[str, object]) -> CompileCandidate:
    if isinstance(candidate, CompileCandidate):
        return candidate
    if "anchor" not in candidate:
        raise SchemaValidationError("anchor", "Compile candidate missing anchor")
    record = candidate.get("record", candidate)
    if not isinstance(record, Mapping):
        raise SchemaValidationError("record", "Compile candidate record must be an object")
    record_dict = dict(record)
    record_dict.pop("anchor", None)
    return CompileCandidate(anchor=str(candidate["anchor"]), record=record_dict)


def _resolve_accessors(
    record: dict[str, object],
    accessor_symbols: Mapping[str, str] | set[str] | frozenset[str] | None,
) -> None:
    if accessor_symbols is None:
        return
    accessors = record.get("accessors", [])
    if not isinstance(accessors, list):
        raise SchemaValidationError("accessors", "accessors must be a list")

    resolved: list[str] = []
    for accessor in accessors:
        if not isinstance(accessor, str):
            raise SchemaValidationError("accessors", "accessor symbols must be strings")
        if isinstance(accessor_symbols, Mapping):
            symbol_map = cast(Mapping[str, str], accessor_symbols)
            if accessor not in accessor_symbols:
                raise SchemaValidationError(
                    "accessors", f"Unknown accessor symbol: {accessor}"
                )
            resolved.append(symbol_map[accessor])
        elif accessor not in accessor_symbols:
            raise SchemaValidationError("accessors", f"Unknown accessor symbol: {accessor}")
        else:
            resolved.append(accessor)
    record["accessors"] = resolved


def _diff_by_tmr_uid(
    old_records: Sequence[Mapping[str, object]],
    new_records: Sequence[Mapping[str, object]],
) -> list[SemanticDiffEvent]:
    old_by_uid = {str(record["tmr_uid"]): record for record in old_records}
    new_by_uid = {str(record["tmr_uid"]): record for record in new_records}
    events: list[SemanticDiffEvent] = []

    for uid in sorted(new_by_uid):
        if uid not in old_by_uid:
            events.append(SemanticDiffEvent(event="add", tmr_uid=uid))
            continue
        changes = _changed_fields(old_by_uid[uid], new_by_uid[uid])
        if not changes:
            continue
        event: Literal["rename", "update"] = (
            "rename" if "test_id" in changes else "update"
        )
        events.append(SemanticDiffEvent(event=event, tmr_uid=uid, changes=changes))

    for uid in sorted(set(old_by_uid) - set(new_by_uid)):
        events.append(SemanticDiffEvent(event="remove", tmr_uid=uid))
    return events


def _changed_fields(
    old_record: Mapping[str, object],
    new_record: Mapping[str, object],
) -> dict[str, dict[str, object | None]]:
    changes: dict[str, dict[str, object | None]] = {}
    for field_name in sorted(set(old_record) | set(new_record)):
        old_value = old_record.get(field_name)
        new_value = new_record.get(field_name)
        if old_value != new_value:
            changes[field_name] = {"from": old_value, "to": new_value}
    return changes
