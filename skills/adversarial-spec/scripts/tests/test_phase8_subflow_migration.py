"""B-11 / DF-20: Phase 8 verification-subflow migration mechanics.

`verification` was never a canonical phase -- it was a documentation boundary
(`phases/09-verification.md`) that leaked into lifecycle state. The resolution
(CON-002, operator decision 2026-07-21) demotes it to a *subflow* of Phase 8:
progress is tracked as `current_step`, and `current_phase` stays
`implementation`.

DF-20 names four guarantees, one section each below:

1. atomic remap of `current_phase: verification` preserving artifacts + board state
2. post-migration rejection of every new `current_phase: verification` write
3. idempotent append of exactly ONE `phase8_subflow_migration` event
4. canonical-order validation normalizes historical `implementation -> verification`
   journey transitions as legacy subflow events

Plus TC-1.0's inventory leg: the canonical phase list is Phases 1-8 and does not
contain `verification`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from phase8_subflow_migration import (
    CANONICAL_PHASES,
    LEGACY_SUBFLOW_PHASE,
    MIGRATION_EVENT,
    SUBFLOW_STEP,
    VerificationPhaseWriteError,
    assert_writable_phase,
    canonical_order_anomalies,
    migrate_session_files,
    normalized_transitions,
)

SESSION_ID = "adv-spec-202607221200-df20-fixture"


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _journey_lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@pytest.fixture
def session(tmp_path: Path):
    """A session parked mid-verification, with artifacts and board state set."""
    root = tmp_path / ".adversarial-spec"
    (root / "sessions").mkdir(parents=True)

    detail = root / "sessions" / f"{SESSION_ID}.json"
    pointer = root / "session-state.json"
    journey = root / "sessions" / f"{SESSION_ID}.journey.log"

    _write(
        detail,
        {
            "current_phase": LEGACY_SUBFLOW_PHASE,
            "current_step": "running component verification",
            "fizzy_card_id": "5857",
            "spec_path": "specs/x/spec-final.md",
            "execution_plan_path": "specs/x/execution-plan.md",
            "verification_report_path": "specs/x/verification-report.md",
            "checkpointed_cleanly": True,
            "extended_state": {"gauntlet_results": {"accepted": 35}},
        },
    )
    _write(
        pointer,
        {
            "active_session_id": SESSION_ID,
            "current_phase": LEGACY_SUBFLOW_PHASE,
            "current_step": "running component verification",
            "next_action": "finish verification",
        },
    )
    journey.write_text(
        "\n".join(
            json.dumps(event)
            for event in [
                {"time": "2026-07-01T00:00:00Z", "event": "Phase transition: execution → implementation", "type": "transition"},
                {"time": "2026-07-02T00:00:00Z", "event": "Phase transition: implementation → verification", "type": "transition"},
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return {"root": root, "detail": detail, "pointer": pointer, "journey": journey}


def _migrate(session, **kwargs):
    return migrate_session_files(
        detail_path=session["detail"],
        pointer_path=session["pointer"],
        journey_path=session["journey"],
        **kwargs,
    )


# --------------------------------------------------------------------------
# TC-1.0 inventory leg
# --------------------------------------------------------------------------


def test_canonical_phases_are_the_eight_pipeline_phases_plus_complete() -> None:
    assert CANONICAL_PHASES == (
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


def test_verification_is_not_a_canonical_phase() -> None:
    assert LEGACY_SUBFLOW_PHASE not in CANONICAL_PHASES
    assert SUBFLOW_STEP == LEGACY_SUBFLOW_PHASE


# --------------------------------------------------------------------------
# Guarantee 1: atomic remap preserving artifacts + board state
# --------------------------------------------------------------------------


def test_migration_remaps_phase_and_records_the_subflow_step(session) -> None:
    result = _migrate(session, now="2026-07-22T12:00:00Z")
    assert result.migrated is True

    detail = json.loads(session["detail"].read_text(encoding="utf-8"))
    assert detail["current_phase"] == "implementation"
    assert detail["current_step"] == SUBFLOW_STEP

    pointer = json.loads(session["pointer"].read_text(encoding="utf-8"))
    assert pointer["current_phase"] == "implementation"
    assert pointer["current_step"] == SUBFLOW_STEP


def test_migration_preserves_artifacts_and_board_state(session) -> None:
    before = json.loads(session["detail"].read_text(encoding="utf-8"))
    _migrate(session, now="2026-07-22T12:00:00Z")
    after = json.loads(session["detail"].read_text(encoding="utf-8"))

    for key in (
        "fizzy_card_id",
        "spec_path",
        "execution_plan_path",
        "verification_report_path",
        "extended_state",
    ):
        assert after[key] == before[key], f"migration disturbed {key}"
    assert set(after) - set(before) == set()


def test_migration_leaves_a_non_verification_session_untouched(session) -> None:
    _write(
        session["detail"],
        {"current_phase": "gauntlet", "current_step": "attacks", "fizzy_card_id": "1"},
    )
    _write(session["pointer"], {"current_phase": "gauntlet", "current_step": "attacks"})
    result = _migrate(session, now="2026-07-22T12:00:00Z")

    assert result.migrated is False
    assert json.loads(session["detail"].read_text(encoding="utf-8"))["current_phase"] == "gauntlet"
    assert not any(e.get("event") == MIGRATION_EVENT for e in _journey_lines(session["journey"]))


def test_partial_crash_between_state_and_journey_heals_on_rerun(session) -> None:
    """Detail migrated, event never appended -- the rerun completes it, once."""
    _migrate(session, now="2026-07-22T12:00:00Z")
    lines = [e for e in _journey_lines(session["journey"]) if e.get("event") != MIGRATION_EVENT]
    session["journey"].write_text(
        "\n".join(json.dumps(e) for e in lines) + "\n", encoding="utf-8"
    )

    result = _migrate(session, now="2026-07-22T13:00:00Z")
    assert result.event_appended is True
    events = [e for e in _journey_lines(session["journey"]) if e.get("event") == MIGRATION_EVENT]
    assert len(events) == 1


# --------------------------------------------------------------------------
# Guarantee 2: post-migration write rejection
# --------------------------------------------------------------------------


def test_writing_verification_as_a_phase_is_rejected() -> None:
    with pytest.raises(VerificationPhaseWriteError) as excinfo:
        assert_writable_phase(LEGACY_SUBFLOW_PHASE)
    assert SUBFLOW_STEP in str(excinfo.value)


@pytest.mark.parametrize("phase", CANONICAL_PHASES)
def test_canonical_phases_remain_writable(phase: str) -> None:
    assert_writable_phase(phase)


def test_unknown_phase_is_rejected_too() -> None:
    with pytest.raises(ValueError):
        assert_writable_phase("verifying")


def test_migration_refuses_to_reintroduce_verification(session) -> None:
    """A post-migration session that somehow carries the old phase is an error."""
    _migrate(session, now="2026-07-22T12:00:00Z")
    detail = json.loads(session["detail"].read_text(encoding="utf-8"))
    detail["current_phase"] = LEGACY_SUBFLOW_PHASE
    _write(session["detail"], detail)

    with pytest.raises(VerificationPhaseWriteError):
        _migrate(session, now="2026-07-22T14:00:00Z", strict=True)


# --------------------------------------------------------------------------
# Guarantee 3: idempotent single event
# --------------------------------------------------------------------------


def test_migration_appends_exactly_one_event(session) -> None:
    _migrate(session, now="2026-07-22T12:00:00Z")
    events = [e for e in _journey_lines(session["journey"]) if e.get("event") == MIGRATION_EVENT]
    assert len(events) == 1
    assert events[0]["type"] == "migration"
    assert events[0]["time"] == "2026-07-22T12:00:00Z"


def test_rerun_appends_zero_additional_events(session) -> None:
    _migrate(session, now="2026-07-22T12:00:00Z")
    before = _journey_lines(session["journey"])

    second = _migrate(session, now="2026-07-22T13:00:00Z")
    third = _migrate(session, now="2026-07-22T14:00:00Z")

    assert second.migrated is False and second.event_appended is False
    assert third.migrated is False and third.event_appended is False
    assert _journey_lines(session["journey"]) == before


def test_event_token_spelling_is_bound() -> None:
    """v9.1 CANON fix: this exact token, no other spelling."""
    assert MIGRATION_EVENT == "phase8_subflow_migration"


# --------------------------------------------------------------------------
# Guarantee 4: legacy journey normalization in canonical-order validation
# --------------------------------------------------------------------------


LEGACY_JOURNEY = [
    ("execution", "implementation"),
    ("implementation", "verification"),
    ("verification", "complete"),
]


def test_legacy_verification_transitions_normalize_to_implementation() -> None:
    assert normalized_transitions(LEGACY_JOURNEY) == [
        ("execution", "implementation"),
        ("implementation", "implementation"),
        ("implementation", "complete"),
    ]


def test_legacy_journey_raises_no_canonical_order_anomaly() -> None:
    assert canonical_order_anomalies(LEGACY_JOURNEY) == []


def test_fsm_internal_lanes_still_fold_into_gauntlet() -> None:
    journey = [
        ("debate", "target-architecture"),
        ("target-architecture", "gauntlet"),
        ("gauntlet", "reconciliation"),
        ("reconciliation", "finalize"),
    ]
    assert canonical_order_anomalies(journey) == []


def test_resume_checker_passes_implementation_subflow_complete() -> None:
    """AC-2: the post-migration journey shape a resumed session actually has."""
    journey = [
        ("execution", "implementation"),
        ("implementation", "complete"),
    ]
    assert canonical_order_anomalies(journey) == []


def test_a_genuinely_skipped_phase_is_still_reported() -> None:
    """Normalization must not blunt the detector it is exempting one case from."""
    anomalies = canonical_order_anomalies(
        [("debate", "gauntlet")]  # target-architecture skipped
    )
    assert len(anomalies) == 1
    assert anomalies[0]["missing"] == ["target-architecture"]
    assert anomalies[0]["from"] == "debate"
    assert anomalies[0]["to"] == "gauntlet"


def test_backwards_transition_is_reported() -> None:
    anomalies = canonical_order_anomalies([("gauntlet", "debate")])
    assert len(anomalies) == 1
    assert anomalies[0]["kind"] == "regression"


def test_migrated_session_resumes_cleanly(session) -> None:
    """AC-3 end to end: migrate, then read back exactly what resume reads."""
    _migrate(session, now="2026-07-22T12:00:00Z")

    detail = json.loads(session["detail"].read_text(encoding="utf-8"))
    pointer = json.loads(session["pointer"].read_text(encoding="utf-8"))
    assert_writable_phase(detail["current_phase"])
    assert detail["current_phase"] == pointer["current_phase"] == "implementation"

    transitions = []
    for event in _journey_lines(session["journey"]):
        if event.get("type") != "transition":
            continue
        text = event["event"].removeprefix("Phase transition: ")
        source, _, target = text.partition(" → ")
        transitions.append((source.strip(), target.strip()))
    assert canonical_order_anomalies(transitions) == []
