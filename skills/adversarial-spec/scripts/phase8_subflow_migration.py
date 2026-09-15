"""Phase 8 verification-subflow migration (B-11 / DF-20, resolving CON-002).

`verification` was a documentation boundary (`phases/09-verification.md`) that
leaked into lifecycle state: sessions were writing `current_phase: verification`,
a value the canonical order never contained. Promoting it to a real phase would
have forced router, board-FSM, artifact and glossary migrations merely to
legitimize a filename, so the operator decision (2026-07-21) went the other way --
verification is a **subflow of Phase 8**, tracked in `current_step` while
`current_phase` stays `implementation`.

This module owns the four DF-20 guarantees:

1. **Atomic remap.** `current_phase: verification` becomes
   `{current_phase: implementation, current_step: verification}` and nothing else
   about the session changes -- artifacts, board state and extended state are
   preserved byte-for-byte.
2. **Write rejection.** After migration, `verification` is not a writable phase;
   :func:`assert_writable_phase` is the choke point.
3. **Idempotent single event.** Exactly one ``phase8_subflow_migration`` journey
   event is appended, with zero additional events on any rerun.
4. **Legacy normalization.** Historical ``implementation -> verification``
   journey transitions read as legacy subflow events, so they do not trip the
   canonical-order anomaly detector -- without blunting it for real skips.

Ordering note: state files are migrated BEFORE the journey event is appended, and
both steps are independently idempotent. A crash between them leaves a migrated
session whose event is missing, which the next run completes -- and completes
once, because the guard is "does the journey already carry the event", not "did
we just migrate".
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

CANONICAL_PHASES: tuple[str, ...] = (
    "requirements",
    "roadmap",
    "debate",
    "target-architecture",
    "gauntlet",
    "finalize",
    "execution",
    "implementation",
    "complete",
)

# Version 6 moves architecture discovery into the D0 decomposition phase.  Its
# board flow intentionally has no Target-Architecture lane: Phase 4 may leave
# a skip-mode artifact, but it must not look like a skipped board transition.
V6_CANONICAL_PHASES: tuple[str, ...] = (
    "requirements",
    "roadmap",
    "decomposition",
    "debate",
    "gauntlet",
    "finalize",
    "execution",
    "implementation",
    "complete",
)

_V6_SHAPE_PHASES = frozenset({"pre-roadmap", "decomposition"})
_COMMON_FSM_INTERNAL_LANES: dict[str, str] = {
    "pre-gauntlet": "gauntlet",
    "reconciliation": "gauntlet",
}
_V6_FSM_INTERNAL_LANES: dict[str, str] = {
    **_COMMON_FSM_INTERNAL_LANES,
    "pre-roadmap": "roadmap",
}
_WRITABLE_PHASES = frozenset(
    (*CANONICAL_PHASES, "pre-roadmap", "decomposition", "pre-gauntlet", "reconciliation")
)
_TRANSITION_EVENT_RE = re.compile(
    r"^Phase transition:\s*"
    r"(?P<source>[a-z][a-z_-]*)\s*"
    r"(?:→|->)\s*"
    r"(?P<target>[a-z][a-z_-]*)(?:\b.*)?$"
)

#: The phase value that never was. Retained as a constant so every consumer
#: names the same string instead of open-coding it.
LEGACY_SUBFLOW_PHASE = "verification"

#: Where verification progress lives now. Same word, different field -- that is
#: the entire migration.
SUBFLOW_STEP = "verification"
SUBFLOW_PARENT_PHASE = "implementation"

#: v9.1 CANON fix: the bound event name. No other spelling is valid.
MIGRATION_EVENT = "phase8_subflow_migration"

class VerificationPhaseWriteError(ValueError):
    """Raised when something tries to write `verification` as a phase."""

    def __init__(self, value: str) -> None:
        self.value = value
        super().__init__(
            f"{value!r} is not a phase; verification is a Phase 8 subflow -- "
            f"write current_phase={SUBFLOW_PARENT_PHASE!r} with "
            f"current_step={SUBFLOW_STEP!r}"
        )


class JourneyTransitionParseError(ValueError):
    """A structured phase-transition event cannot be safely interpreted.

    Resume validation must fail closed when a record claims the canonical
    ``Phase transition:`` shape.  Older logs also use ``type: transition`` for
    narrative gate milestones; those are not phase-order records and are not
    candidates for this parser.
    """


@dataclass
class MigrationResult:
    """What a migration run actually did. Both flags are False on a no-op."""

    migrated: bool = False
    event_appended: bool = False
    changed_files: list[str] = field(default_factory=list)


def assert_writable_phase(phase: str) -> None:
    """Guarantee 2 -- the choke point for every new phase write.

    `verification` gets its own error because "unknown phase" would send a
    reader looking for a typo instead of at the subflow rule.
    """

    if phase == LEGACY_SUBFLOW_PHASE:
        raise VerificationPhaseWriteError(phase)
    if phase not in _WRITABLE_PHASES:
        raise ValueError(
            f"{phase!r} is not a canonical phase; expected one of "
            + ", ".join(CANONICAL_PHASES)
        )


def migrate_state_mapping(state: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Pure half of guarantee 1: remap one state mapping, preserving the rest."""

    if state.get("current_phase") != LEGACY_SUBFLOW_PHASE:
        return state, False
    migrated = dict(state)
    migrated["current_phase"] = SUBFLOW_PARENT_PHASE
    migrated["current_step"] = SUBFLOW_STEP
    return migrated, True


def normalized_transitions(
    transitions: Iterable[tuple[str, str]],
    *,
    pipeline_version: int | None = None,
) -> list[tuple[str, str]]:
    """Guarantee 4 -- fold legacy and FSM-internal values onto canonical phases.

    A historical `implementation -> verification` becomes
    `implementation -> implementation`: a self-transition, which the order check
    accepts, rather than a jump to a phase that does not exist.
    """

    raw = list(transitions)
    v6 = uses_v6_shape(raw, pipeline_version=pipeline_version)
    folded: list[tuple[str, str]] = []
    for source, target in raw:
        folded.append((_fold(source, v6=v6), _fold(target, v6=v6)))
    return folded


def uses_v6_shape(
    transitions: Iterable[tuple[str, str]],
    *,
    pipeline_version: int | None = None,
) -> bool:
    """Identify a v6 journey without trusting optional stale session metadata."""

    if pipeline_version is not None:
        return pipeline_version >= 6
    return any(
        phase in _V6_SHAPE_PHASES
        for source, target in transitions
        for phase in (source, target)
    )


def _fold(phase: str, *, v6: bool) -> str:
    if phase == LEGACY_SUBFLOW_PHASE:
        return SUBFLOW_PARENT_PHASE
    lanes = _V6_FSM_INTERNAL_LANES if v6 else _COMMON_FSM_INTERNAL_LANES
    return lanes.get(phase, phase)


def canonical_order_anomalies(
    transitions: Sequence[tuple[str, str]],
    *,
    pipeline_version: int | None = None,
) -> list[dict[str, Any]]:
    """Report skipped or backwards phase transitions.

    Normalization exempts exactly the legacy subflow case; a genuine skip (the
    2026-05-17 target-architecture incident) still reports, and so does a
    backwards move.
    """

    raw = list(transitions)
    v6 = uses_v6_shape(raw, pipeline_version=pipeline_version)
    phase_order = V6_CANONICAL_PHASES if v6 else CANONICAL_PHASES
    phase_index = {phase: index for index, phase in enumerate(phase_order)}

    anomalies: list[dict[str, Any]] = []
    for source, target in normalized_transitions(raw, pipeline_version=pipeline_version):
        # Triage is an additive front door, not a canonical phase.  Only its
        # normal entrance is exempt; any other jump from triage still reports.
        if (source, target) == ("triage", "requirements"):
            continue
        if source not in phase_index or target not in phase_index:
            anomalies.append(
                {
                    "kind": "unknown_phase",
                    "from": source,
                    "to": target,
                    "missing": [],
                }
            )
            continue
        start, end = phase_index[source], phase_index[target]
        if end < start:
            anomalies.append(
                {"kind": "regression", "from": source, "to": target, "missing": []}
            )
        elif end > start + 1:
            anomalies.append(
                {
                    "kind": "skipped_phase",
                    "from": source,
                    "to": target,
                    "missing": list(phase_order[start + 1 : end]),
                }
            )
    return anomalies


def parse_transition_event(event: Mapping[str, Any]) -> tuple[str, str] | None:
    """Extract one transition pair from either supported historical notation.

    Both ``→`` and ``->`` are accepted indefinitely because pipeline v6 wrote
    the latter.  New writes use the Unicode form, but a history checker must
    never turn a formatting migration into a false phase-skip incident.
    """

    if event.get("type") != "transition":
        return None
    text = event.get("event")
    if not isinstance(text, str):
        raise JourneyTransitionParseError("transition event must contain a string event field")
    if not text.startswith("Phase transition:"):
        return None
    match = _TRANSITION_EVENT_RE.match(text)
    if match is None:
        raise JourneyTransitionParseError(f"unparseable transition event: {text!r}")
    return match.group("source"), match.group("target")


def load_journey_transitions(path: Path) -> list[tuple[str, str]]:
    """Load every transition from a JSONL journey, failing closed on bad data."""

    transitions: list[tuple[str, str]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise JourneyTransitionParseError(
                f"invalid JSON in journey {path} line {line_number}"
            ) from exc
        if not isinstance(event, dict):
            raise JourneyTransitionParseError(
                f"journey {path} line {line_number} must be a JSON object"
            )
        transition = parse_transition_event(event)
        if transition is not None:
            transitions.append(transition)
    return transitions


def journey_carries_migration_event(path: Path) -> bool:
    """Guarantee 3's idempotency key -- the log, not a local flag."""

    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event") == MIGRATION_EVENT:
            return True
    return False


def migrate_session_files(
    *,
    detail_path: Path,
    pointer_path: Path,
    journey_path: Path,
    now: str,
    strict: bool = False,
) -> MigrationResult:
    """Run the migration over one session's files. Safe to re-run.

    ``strict`` rejects a session that carries `verification` again after the
    migration event is already on the log -- that is a post-migration write
    slipping past :func:`assert_writable_phase`, not more legacy state.
    """

    result = MigrationResult()
    already_migrated = journey_carries_migration_event(journey_path)
    in_subflow_shape = False

    for path in (detail_path, pointer_path):
        if not path.exists():
            continue
        state = json.loads(path.read_text(encoding="utf-8"))
        if strict and already_migrated and state.get("current_phase") == LEGACY_SUBFLOW_PHASE:
            raise VerificationPhaseWriteError(LEGACY_SUBFLOW_PHASE)
        if _carries_subflow_shape(state):
            in_subflow_shape = True
        migrated_state, changed = migrate_state_mapping(state)
        if not changed:
            continue
        _atomic_write_json(path, migrated_state)
        result.migrated = True
        result.changed_files.append(str(path))

    # The event is owed by the state's SHAPE, not by whether this particular run
    # did the remapping -- otherwise a crash between the state write and the
    # append would leave a migrated session with no record of it, forever.
    owes_event = result.migrated or in_subflow_shape
    if owes_event and not already_migrated:
        _append_journey_event(journey_path, now)
        result.event_appended = True

    return result


def _carries_subflow_shape(state: dict[str, Any]) -> bool:
    return (
        state.get("current_phase") == SUBFLOW_PARENT_PHASE
        and state.get("current_step") == SUBFLOW_STEP
    )


def _atomic_write_json(path: Path, payload: Any) -> None:
    """Same-directory temp file -> fsync -> atomic replace -> directory fsync."""

    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    _fsync_dir(path.parent)


def _append_journey_event(path: Path, now: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(
        {
            "time": now,
            "event": MIGRATION_EVENT,
            "type": "migration",
            "detail": (
                "current_phase: verification remapped to "
                "{implementation, current_step: verification}"
            ),
        }
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_dir(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _main(argv: Sequence[str] | None = None) -> int:
    """Expose the canonical journey check without re-implementing its parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-journey",
        type=Path,
        metavar="PATH",
        help="Validate phase-transition order in a JSONL journey log.",
    )
    parser.add_argument(
        "--pipeline-version",
        type=int,
        help="Optional explicit pipeline version; inferred from v6-only lanes when omitted.",
    )
    args = parser.parse_args(argv)
    if args.check_journey is None:
        parser.error("--check-journey is required")

    try:
        transitions = load_journey_transitions(args.check_journey)
    except (OSError, JourneyTransitionParseError) as exc:
        print(json.dumps({"ok": False, "parse_error": str(exc)}), file=sys.stderr)
        return 2

    anomalies = canonical_order_anomalies(
        transitions,
        pipeline_version=args.pipeline_version,
    )
    print(
        json.dumps(
            {
                "ok": not anomalies,
                "mode": "v6"
                if uses_v6_shape(transitions, pipeline_version=args.pipeline_version)
                else "legacy",
                "transitions": transitions,
                "anomalies": anomalies,
            },
            indent=2,
        )
    )
    return 0 if not anomalies else 1


if __name__ == "__main__":
    raise SystemExit(_main())
