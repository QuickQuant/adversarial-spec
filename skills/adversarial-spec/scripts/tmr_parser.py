"""TmrParser implementation for loading and validating the TMR registry.

This module acts as the single entrypoint for reading and parsing
tmr-registry.json, enforcing strict typed coercion, duplicate key detection,
and rejecting ambiguous string representations of null/None.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tmr_schema import (
    SchemaValidationError,
    TestMaturityRecord,
    validate_tmr_record,
)


class TmrParser:
    """Strict parser for the TMR registry.

    This is the single system of record reader for tmr-registry.json.
    """

    @staticmethod
    def parse_string(json_str: str) -> list[TestMaturityRecord]:
        """Parses a JSON string representing a list of TMR records.

        Enforces duplicate JSON key rejection, rejection of ambiguous scalars,
        duplicate tmr_uid checks, and full schema validation.
        """
        def _detect_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            keys = set()
            for k, v in pairs:
                if k in keys:
                    raise SchemaValidationError(k, f"Duplicate JSON key detected: {k}")
                keys.add(k)
            return dict(pairs)

        try:
            data = json.loads(json_str, object_pairs_hook=_detect_duplicates)
        except json.JSONDecodeError as exc:
            raise SchemaValidationError("<json>", f"Invalid JSON syntax: {exc}") from exc

        if not isinstance(data, list):
            raise SchemaValidationError("<registry>", "Registry must be a JSON array of TMR records")

        def _reject_ambiguous_strings(val: Any, path: str = "") -> None:
            if isinstance(val, dict):
                for k, v in val.items():
                    sub_path = f"{path}.{k}" if path else k
                    _reject_ambiguous_strings(v, sub_path)
            elif isinstance(val, list):
                for i, item in enumerate(val):
                    sub_path = f"{path}[{i}]"
                    _reject_ambiguous_strings(item, sub_path)
            elif isinstance(val, str):
                if val in ("null", "None", "~"):
                    raise SchemaValidationError(path or "<string>", f"Ambiguous scalar value {val!r} is rejected")

        seen_uids: set[str] = set()
        records: list[TestMaturityRecord] = []
        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                raise SchemaValidationError(f"[{idx}]", "Each TMR record must be a JSON object")

            _reject_ambiguous_strings(item)

            tmr_uid = item.get("tmr_uid")
            if tmr_uid is not None:
                if not isinstance(tmr_uid, str):
                    raise SchemaValidationError(f"[{idx}].tmr_uid", "tmr_uid must be a string")
                if tmr_uid in seen_uids:
                    raise SchemaValidationError(f"[{idx}].tmr_uid", f"Duplicate tmr_uid: {tmr_uid}")
                seen_uids.add(tmr_uid)

            # Validate the record via tmr_schema.py's validate_tmr_record
            record = validate_tmr_record(item)
            records.append(record)

        return records

    @staticmethod
    def parse_file(file_path: Path | str) -> list[TestMaturityRecord]:
        """Loads and parses tmr-registry.json.

        This is the single TMR reader for the codebase.
        """
        path = Path(file_path)
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise SchemaValidationError("<file>", f"Failed to read file {file_path}: {exc}") from exc
        return TmrParser.parse_string(content)
