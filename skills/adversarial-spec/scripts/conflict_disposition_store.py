"""Persisted conflict-disposition store (W1-4 / MW-005).

Implements the spec §5 (US-6 / RC-2) / INV-012 / INV-021 / INV-025 contract:

- Conflicts are **typed transitions** ``{subject, field, from, to, action}`` — detected
  semantically (incompatible target states / destructive-vs-mutating on the same
  subject), NOT by identical ``required_action`` string match, so cross-field
  conflicts are caught (``promote`` vs ``delete`` on the same TMR).
- A contradiction enters a ``conflict`` state requiring disposition **before** any
  journaled field transition (no silent last-writer-wins).
- Pending conflicts are **persisted** to a discrete ``pending-dispositions.json``
  (filelock-guarded), never memory-only — so a crash/restart re-reads them and a
  fail-closed gate cannot silently fail *open* (RC-2). The main loop refuses to
  advance a phase while the file is non-empty.
- Resolution is **deterministic in a headless loop**: a declared precedence
  (more-conservative / destructive wins) records a structured machine justification
  ``{decision_id, resolution, precedence_rule, winning_transition, losing_transition}``;
  interactive mode records a human reason. The loop never deadlocks and never
  silently picks a winner.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from filelock import FileLock

STORE_VERSION = 1

# Action taxonomy for semantic conflict detection + precedence.
DESTRUCTIVE_ACTIONS = frozenset({"delete", "tombstone", "remove"})
MUTATING_ACTIONS = frozenset({"promote", "set", "bind", "create"})

# Conservatism ranking — higher wins under headless precedence (fail-closed /
# destructive / more-conservative beats a permissive change).
_CONSERVATISM = {
    "delete": 4,
    "tombstone": 4,
    "remove": 4,
    "block": 4,
    "promote": 3,
    "set": 2,
    "bind": 2,
    "create": 2,
    "keep": 1,
}


@dataclass(frozen=True)
class TypedTransition:
    """A typed field transition ``{subject, field, from, to, action}``."""

    subject: str
    field: str
    to: object
    action: str
    from_: object = None

    def to_dict(self) -> dict:
        return {
            "subject": self.subject,
            "field": self.field,
            "from": self.from_,
            "to": self.to,
            "action": self.action,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TypedTransition":
        return cls(
            subject=data["subject"],
            field=data["field"],
            to=data.get("to"),
            action=data["action"],
            from_=data.get("from"),
        )

    def canonical(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class Conflict:
    conflict_id: str
    subject: str
    transitions: list[TypedTransition]
    detail: str

    def to_dict(self) -> dict:
        return {
            "conflict_id": self.conflict_id,
            "subject": self.subject,
            "transitions": [t.to_dict() for t in self.transitions],
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Conflict":
        return cls(
            conflict_id=data["conflict_id"],
            subject=data["subject"],
            transitions=[TypedTransition.from_dict(t) for t in data["transitions"]],
            detail=data["detail"],
        )


@dataclass(frozen=True)
class Disposition:
    decision_id: str
    conflict_id: str
    resolution: str  # "headless-precedence" | "human"
    winning_transition: TypedTransition
    losing_transition: Optional[TypedTransition] = None
    precedence_rule: Optional[str] = None
    reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "conflict_id": self.conflict_id,
            "resolution": self.resolution,
            "precedence_rule": self.precedence_rule,
            "winning_transition": self.winning_transition.to_dict(),
            "losing_transition": (
                self.losing_transition.to_dict() if self.losing_transition else None
            ),
            "reason": self.reason,
        }


def _conflict_id(subject: str, transitions: list[TypedTransition]) -> str:
    canon = "|".join(sorted(t.canonical() for t in transitions))
    digest = hashlib.sha256(f"{subject}::{canon}".encode("utf-8")).hexdigest()
    return f"cf-{digest[:12]}"


def _decision_id(conflict_id: str, winner: TypedTransition, loser: Optional[TypedTransition], resolution: str) -> str:
    parts = [conflict_id, resolution, winner.canonical(), loser.canonical() if loser else ""]
    digest = hashlib.sha256("::".join(parts).encode("utf-8")).hexdigest()
    return f"dec-{digest[:12]}"


def detect_conflicts(transitions: list[TypedTransition]) -> list[Conflict]:
    """Detect semantic conflicts among typed transitions (pure, deterministic)."""
    by_subject: dict[str, list[TypedTransition]] = {}
    for t in transitions:
        by_subject.setdefault(t.subject, []).append(t)

    conflicts: dict[str, Conflict] = {}
    for subject, ts in by_subject.items():
        involved: dict[str, TypedTransition] = {}
        detail_bits: list[str] = []

        # Rule A: same field, incompatible target states.
        by_field: dict[str, list[TypedTransition]] = {}
        for t in ts:
            by_field.setdefault(t.field, []).append(t)
        for field, fts in by_field.items():
            distinct_to = {json.dumps(t.to, sort_keys=True) for t in fts}
            if len(distinct_to) > 1:
                for t in fts:
                    involved[t.canonical()] = t
                detail_bits.append(f"incompatible target states on {field}")

        # Rule B: a destructive action coexisting with a mutating action on the
        # same subject (e.g. promote vs delete) — a cross-field conflict.
        destructive = [t for t in ts if t.action in DESTRUCTIVE_ACTIONS]
        mutating = [t for t in ts if t.action in MUTATING_ACTIONS]
        if destructive and mutating:
            for t in (*destructive, *mutating):
                involved[t.canonical()] = t
            detail_bits.append("destructive vs mutating on same subject")

        if len(involved) >= 2:
            members = sorted(involved.values(), key=lambda t: t.canonical())
            cid = _conflict_id(subject, members)
            conflicts[cid] = Conflict(
                conflict_id=cid,
                subject=subject,
                transitions=members,
                detail="; ".join(sorted(set(detail_bits))),
            )

    return sorted(conflicts.values(), key=lambda c: c.conflict_id)


def _conservatism(t: TypedTransition) -> int:
    score = _CONSERVATISM.get(t.action, 1)
    # higher altitude / a true critical_seam is more conservative
    if t.field == "altitude":
        score += {"system": 2, "subsystem": 1, "component": 0}.get(str(t.to), 0)
    if t.field == "critical_seam" and t.to is True:
        score += 1
    return score


def default_precedence(transitions: list[TypedTransition]) -> tuple[TypedTransition, TypedTransition, str]:
    """Pick a deterministic winner: more-conservative wins, lexical tiebreak."""
    ranked = sorted(
        transitions,
        key=lambda t: (-_conservatism(t), t.canonical()),
    )
    winner, loser = ranked[0], ranked[-1]
    rule = (
        "more-conservative"
        if _conservatism(winner) != _conservatism(loser)
        else "lexical-tiebreak"
    )
    return winner, loser, rule


class ConflictDispositionStore:
    """Persisted, filelock-guarded pending-conflict store."""

    def __init__(self, path: os.PathLike | str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = FileLock(str(self._path) + ".lock")

    # --- persistence ---------------------------------------------------------

    def _read(self) -> dict:
        if not self._path.exists():
            return {"version": STORE_VERSION, "pending": [], "resolved": []}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"version": STORE_VERSION, "pending": [], "resolved": []}

    def _write(self, data: dict) -> None:
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, self._path)

    # --- API -----------------------------------------------------------------

    def detect_and_record(self, transitions: list[TypedTransition]) -> list[Conflict]:
        conflicts = detect_conflicts(transitions)
        if not conflicts:
            return []
        with self._lock:
            data = self._read()
            existing = {c["conflict_id"] for c in data["pending"]}
            for c in conflicts:
                if c.conflict_id not in existing:
                    data["pending"].append(c.to_dict())
            self._write(data)
        return conflicts

    def pending(self) -> list[Conflict]:
        with self._lock:
            return [Conflict.from_dict(c) for c in self._read()["pending"]]

    def has_pending(self) -> bool:
        with self._lock:
            return len(self._read()["pending"]) > 0

    def can_advance_phase(self) -> bool:
        return not self.has_pending()

    def _resolve(self, disp: Disposition) -> Disposition:
        with self._lock:
            data = self._read()
            data["pending"] = [
                c for c in data["pending"] if c["conflict_id"] != disp.conflict_id
            ]
            data["resolved"].append(disp.to_dict())
            self._write(data)
        return disp

    def _get_pending(self, conflict_id: str) -> Conflict:
        for c in self.pending():
            if c.conflict_id == conflict_id:
                return c
        raise KeyError(f"no pending conflict {conflict_id!r}")

    def resolve_headless(
        self, conflict_id: str, precedence=default_precedence
    ) -> Disposition:
        conflict = self._get_pending(conflict_id)
        winner, loser, rule = precedence(conflict.transitions)
        disp = Disposition(
            decision_id=_decision_id(conflict_id, winner, loser, "headless-precedence"),
            conflict_id=conflict_id,
            resolution="headless-precedence",
            winning_transition=winner,
            losing_transition=loser,
            precedence_rule=rule,
        )
        return self._resolve(disp)

    def resolve_interactive(
        self, conflict_id: str, winning_index: int, reason: str
    ) -> Disposition:
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("interactive disposition requires a non-empty reason")
        conflict = self._get_pending(conflict_id)
        winner = conflict.transitions[winning_index]
        losers = [t for i, t in enumerate(conflict.transitions) if i != winning_index]
        disp = Disposition(
            decision_id=_decision_id(conflict_id, winner, losers[0] if losers else None, "human"),
            conflict_id=conflict_id,
            resolution="human",
            winning_transition=winner,
            losing_transition=losers[0] if losers else None,
            reason=reason.strip(),
        )
        return self._resolve(disp)
