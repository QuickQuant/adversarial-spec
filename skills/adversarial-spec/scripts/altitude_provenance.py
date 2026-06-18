"""Skill-side altitude provenance emission and meta-analysis."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from provenance_journal import AppendReceipt, JournalTransition, ProvenanceJournalWriter

Altitude = Literal["component", "subsystem", "system"]
AltitudeFit = Literal["right", "too_high", "too_low"]
ALTITUDES = ("component", "subsystem", "system")
ALTITUDE_FITS = ("right", "too_high", "too_low")


@dataclass(frozen=True)
class FitSummary:
    total: int
    correct: int
    too_high: int
    too_low: int

    @property
    def precision(self) -> float:
        return self.correct / self.total if self.total else 0.0


def record_depth_triage_node(
    writer: ProvenanceJournalWriter,
    *,
    session_id: str,
    node_id: str,
    initial_altitude: Altitude,
    rationale: str,
    idempotency_key: str,
) -> AppendReceipt:
    """Append the created node-altitude decision from Phase-7 depth triage."""

    if initial_altitude not in ALTITUDES:
        raise ValueError(f"unsupported altitude: {initial_altitude!r}")
    if not rationale.strip():
        raise ValueError("rationale is required")
    return writer.append_transition(
        JournalTransition(
            session_id=session_id,
            subject_type="node",
            subject_id=node_id,
            event_type="created",
            field="altitude",
            from_value=None,
            to_value=initial_altitude,
            expected_from=None,
            driver={"type": "depth_triage", "ref": "phase7-depth-triage"},
            idempotency_key=idempotency_key,
            metadata={"rationale": rationale},
        ),
        current_fallback=None,
    )


def record_close_altitude_fit(
    writer: ProvenanceJournalWriter,
    *,
    session_id: str,
    node_id: str,
    altitude_fit: AltitudeFit,
    rationale: str,
    idempotency_key: str,
) -> AppendReceipt:
    """Append close-time fit assessment for a previously triaged node."""

    if altitude_fit not in ALTITUDE_FITS:
        raise ValueError(f"unsupported altitude_fit: {altitude_fit!r}")
    if not rationale.strip():
        raise ValueError("rationale is required")
    return writer.append_transition(
        JournalTransition(
            session_id=session_id,
            subject_type="node",
            subject_id=node_id,
            field="altitude_fit",
            from_value=None,
            to_value=altitude_fit,
            expected_from=None,
            driver={"type": "close_attestation", "ref": "phase8-altitude-fit"},
            idempotency_key=idempotency_key,
            metadata={"rationale": rationale},
        ),
        current_fallback=None,
    )


class AltitudeProvenanceAnalyzer:
    """Read node-only journal records and answer altitude meta-analysis queries."""

    def __init__(self, journal_path: Path) -> None:
        self.journal_path = Path(journal_path)

    def records(self) -> list[dict[str, Any]]:
        if not self.journal_path.exists():
            return []
        records = []
        for line in self.journal_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("subject_type") == "node":
                records.append(record)
        return records

    def distribution(self) -> dict[str, int]:
        return dict(Counter(self._initial_altitudes().values()))

    def fit_summary(self) -> FitSummary:
        fits = list(self._latest_fits().values())
        return _summarize_fits(fits)

    def subsystem_precision(self) -> float:
        initial = self._initial_altitudes()
        fits = self._latest_fits()
        subsystem_fits = [
            fits[node_id]
            for node_id, altitude in initial.items()
            if altitude == "subsystem" and node_id in fits
        ]
        return _summarize_fits(subsystem_fits).precision

    def confusion_matrix(self) -> dict[str, dict[str, int]]:
        initial = self._initial_altitudes()
        fits = self._latest_fits()
        matrix: dict[str, Counter[str]] = defaultdict(Counter)
        for node_id, altitude in initial.items():
            if node_id in fits:
                matrix[altitude][fits[node_id]] += 1
        return {altitude: dict(counter) for altitude, counter in matrix.items()}

    def _initial_altitudes(self) -> dict[str, str]:
        altitudes: dict[str, str] = {}
        for record in self.records():
            if record.get("field") == "altitude" and record.get("event_type") == "created":
                altitudes[str(record["subject_id"])] = str(record["to"])
        return altitudes

    def _latest_fits(self) -> dict[str, str]:
        fits: dict[str, str] = {}
        for record in self.records():
            if record.get("field") == "altitude_fit":
                fits[str(record["subject_id"])] = str(record["to"])
        return fits


def _summarize_fits(fits: Iterable[str]) -> FitSummary:
    counts = Counter(fits)
    return FitSummary(
        total=sum(counts.values()),
        correct=counts["right"],
        too_high=counts["too_high"],
        too_low=counts["too_low"],
    )
