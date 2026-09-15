"""Compile authored prose test records into the strict TMR registry."""

from __future__ import annotations

import json
import re
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
TARGET_ANNOTATION_FIELDS = {
    "Outcome obligation": frozenset({"outcome_id", "equivalence_group"}),
    "Intended caller": frozenset(
        {"caller_id", "caller_kind", "caller_equivalence_ref"}
    ),
    "Proof target": frozenset(
        {
            "path_id", "entrypoint", "authority_ref", "authority_role",
            "producer_contract", "consumer_contract", "runtime_chain_required",
            "runtime_slots", "terminal_oracle", "negative_oracle_ref",
            "predecessor_path_ids", "fixture_provenance",
        }
    ),
}
BINDING_TRIGGER_MARKERS = (
    "money-effect", "authority-change", "cross-runtime", "separately-deployed",
    "replacement",
)


class HumanConfirmationRequiredError(RuntimeError):
    """Raised when a registry write is attempted before echo-diff approval."""


@dataclass(frozen=True)
class CompileCandidate:
    """One LLM-emitted candidate plus compiler-owned authoring metadata."""

    anchor: str
    record: dict[str, object]
    # Synthesis (antigravity design point): typed callers can annotate too.
    annotations: str = ""


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
class TmrCompileDiagnostic:
    """An authored test whose required target still needs annotation lines."""

    test_id: str
    missing_annotations: list[str]
    trigger_reasons: list[str]
    code: Literal["TMR_TARGET_BINDING_REQUIRED"] = "TMR_TARGET_BINDING_REQUIRED"
    severity: Literal["warning"] = "warning"
    status: Literal["unresolved"] = "unresolved"


@dataclass(frozen=True)
class TmrCompileResult:
    records: list[dict[str, object]]
    prose_view: str
    echo_diff: list[SemanticDiffEvent]
    requires_human_confirm: bool = True
    diagnostics: list[TmrCompileDiagnostic] = field(default_factory=list)

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

    Mapping candidates may supply an ``annotations`` string outside ``record``.
    Its three JSON annotation lines provide the target binding; the canonical
    schema owns defaults, completeness at concrete maturity, and binding status.
    """

    uid_factory = uid_factory or mint_ulid
    existing = _parse_records(existing_records or [])
    existing_by_uid = {record["tmr_uid"]: record for record in existing}
    existing_by_test_id = {record["test_id"]: record for record in existing}

    seen_anchors: set[str] = set()
    seen_uids: set[str] = set()
    compiled: list[dict[str, object]] = []
    diagnostics: list[TmrCompileDiagnostic] = []
    for raw_candidate in candidates:
        candidate, annotations = _coerce_candidate(raw_candidate)
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
        try:
            diagnostic = _compile_target_binding(record, annotations)
            validated = _parse_records([record])[0]
        except SchemaValidationError as exc:
            raise SchemaValidationError(
                exc.field, f"{record.get('test_id', candidate.anchor)}: {exc.detail}"
            ) from exc
        compiled.append(validated)
        if diagnostic is not None:
            diagnostics.append(diagnostic)

    _check_outcome_collisions(compiled)
    echo_diff = _diff_by_tmr_uid(existing, compiled)
    return TmrCompileResult(
        records=compiled,
        prose_view=render_prose_view(compiled),
        echo_diff=echo_diff,
        diagnostics=diagnostics,
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


def _coerce_candidate(
    candidate: CompileCandidate | Mapping[str, object],
) -> tuple[CompileCandidate, object]:
    if isinstance(candidate, CompileCandidate):
        return candidate, candidate.annotations
    if "anchor" not in candidate:
        raise SchemaValidationError("anchor", "Compile candidate missing anchor")
    record = candidate.get("record", candidate)
    if not isinstance(record, Mapping):
        raise SchemaValidationError("record", "Compile candidate record must be an object")
    record_dict = dict(record)
    record_dict.pop("anchor", None)
    if record is candidate:
        record_dict.pop("annotations", None)
    return (
        CompileCandidate(anchor=str(candidate["anchor"]), record=record_dict),
        candidate.get("annotations", ""),
    )


def _annotation_json(label: str, text: str) -> object:
    def unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise SchemaValidationError(key, f"Duplicate JSON key in {label}: {key}")
            value[key] = item
        return value

    def reject_constant(value: str) -> object:
        raise SchemaValidationError(label, f"Invalid JSON constant: {value}")

    try:
        return json.loads(
            text, object_pairs_hook=unique_keys, parse_constant=reject_constant
        )
    except json.JSONDecodeError as exc:
        raise SchemaValidationError(label, f"Invalid annotation JSON: {exc}") from exc


def _parse_annotations(annotations: object) -> tuple[dict[str, dict[str, object]], list[str]]:
    """Read case-sensitive, single-line JSON annotations outside code fences."""

    if not isinstance(annotations, str):
        raise SchemaValidationError("annotations", "annotations must be a string")
    groups: dict[str, dict[str, object]] = {}
    markers: list[str] = []
    seen: set[str] = set()
    fence = ""
    for raw_line in annotations.splitlines():
        line = raw_line.strip()
        if fence:
            if re.fullmatch(re.escape(fence[0]) + "{" + str(len(fence)) + ",}", line):
                fence = ""
            continue
        opening = re.match(r"(`{3,}|~{3,})", line)
        if opening:
            fence = opening.group()
            continue
        label, colon, payload = line.partition(":")
        if not colon or label not in (*TARGET_ANNOTATION_FIELDS, "Binding triggers"):
            continue
        if label in seen:
            raise SchemaValidationError(label, f"Duplicate annotation: {label}")
        seen.add(label)
        value = _annotation_json(label, payload)
        if label == "Binding triggers":
            if not isinstance(value, list) or any(
                not isinstance(marker, str) or marker not in BINDING_TRIGGER_MARKERS
                for marker in value
            ):
                raise SchemaValidationError(
                    label, "Binding triggers must be an array of supported markers"
                )
            markers = value
            continue
        if not isinstance(value, dict):
            raise SchemaValidationError(label, f"{label} must be a JSON object")
        unknown = sorted(set(value) - TARGET_ANNOTATION_FIELDS[label])
        if unknown:
            raise SchemaValidationError(
                f"target_binding.{unknown[0]}",
                f"Unknown or misplaced field in {label}: {unknown[0]}",
            )
        groups[label] = value
    return groups, markers


def _compile_target_binding(
    record: dict[str, object], annotations: object,
) -> TmrCompileDiagnostic | None:
    groups, markers = _parse_annotations(annotations)
    missing = [label for label in TARGET_ANNOTATION_FIELDS if label not in groups]
    if not missing:
        binding: dict[str, object] = {"binding_version": 1}
        for values in groups.values():
            binding.update(values)
        record["target_binding"] = binding
        # Discard the old derived status during an annotated registry upgrade.
        # Validation supplies it again and sees only author-supplied fields.
        record.pop("target_binding_status", None)
        return None

    if groups and record.get("maturity") == "concrete":
        raise SchemaValidationError(
            "target_binding", f"Incomplete concrete annotations; missing {', '.join(missing)}"
        )
    if (
        record.get("target_binding") is not None
        or record.get("status") != "active"
        or record.get("maturity") not in {"nl", "acceptance"}
    ):
        return None
    reasons = [name for name in ("spine", "critical_seam") if record.get(name) is True]
    reasons.extend(marker for marker in BINDING_TRIGGER_MARKERS if marker in markers)
    if reasons:
        return TmrCompileDiagnostic(
            test_id=str(record.get("test_id", "")),
            missing_annotations=missing,
            trigger_reasons=reasons,
        )
    return None


def _check_outcome_collisions(records: Sequence[Mapping[str, object]]) -> None:
    """Check the complete new registry, including replayed bound records."""

    by_outcome: dict[str, list[tuple[str, object]]] = {}
    for record in records:
        binding = record.get("target_binding")
        if not isinstance(binding, dict):
            continue
        outcome = str(binding["outcome_id"])
        test_id = str(record["test_id"])
        group = binding.get("equivalence_group")
        members = by_outcome.setdefault(outcome, [])
        for other_test_id, other_group in members:
            if test_id != other_test_id and (not group or group != other_group):
                raise SchemaValidationError(
                    "target_binding.outcome_id",
                    f"Outcome {outcome} collides between {other_test_id} and {test_id}; "
                    "both tests must declare the same nonempty equivalence_group",
                )
        members.append((test_id, group))


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
