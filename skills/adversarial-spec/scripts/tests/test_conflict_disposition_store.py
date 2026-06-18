"""Unit tests for ConflictDispositionStore (W1-4).

Spec §5 (US-6 / RC-2) / INV-012 / INV-021 / INV-025: contradictory typed
transitions on the same subject enter a `conflict` state BEFORE any journaled
field transition; pending conflicts are PERSISTED (survive crash/restart) and a
non-empty pending file REFUSES phase-advance; headless resolution applies a
declared precedence and records a structured machine justification.
"""

from __future__ import annotations

import pytest
from conflict_disposition_store import (
    ConflictDispositionStore,
    ConflictDispositionStoreError,
    TypedTransition,
)

pytestmark = pytest.mark.deterministic


def tx(subject, field, to, action, from_=None):
    return TypedTransition(
        subject=subject, field=field, from_=from_, to=to, action=action
    )


def store(tmp_path):
    return ConflictDispositionStore(tmp_path / "pending-dispositions.json")


# --- TC-5.3 / INV-012: contradictory transitions -> conflict BEFORE journaling -

def test_tc5_3_contradictory_transitions_enter_conflict_state(tmp_path):
    s = store(tmp_path)
    conflicts = s.detect_and_record(
        [
            tx("t-001", "data_strategy", to="REAL-DATA", action="promote"),
            tx("t-001", "data_strategy", to="MOCK", action="keep"),
        ]
    )
    assert len(conflicts) == 1
    # no silent last-writer-wins: a conflict exists, so the phase cannot advance
    assert s.has_pending() is True
    assert s.can_advance_phase() is False


def test_inv012_same_field_same_target_is_not_a_conflict(tmp_path):
    s = store(tmp_path)
    conflicts = s.detect_and_record(
        [
            tx("t-1", "status", to="active", action="keep"),
            tx("t-1", "status", to="active", action="keep"),
        ]
    )
    assert conflicts == []
    assert s.has_pending() is False
    assert s.can_advance_phase() is True


# --- INV-025 / US-6: cross-field promote-vs-delete on the same subject ---------

def test_inv025_cross_field_promote_vs_delete_is_a_conflict(tmp_path):
    s = store(tmp_path)
    conflicts = s.detect_and_record(
        [
            tx("t-1", "data_strategy", to="REAL-DATA", action="promote"),
            tx("t-1", "status", to="tombstoned", action="delete"),
        ]
    )
    assert len(conflicts) == 1
    assert s.can_advance_phase() is False


# --- INV-021 / RC-2: pending PERSISTS across crash/restart (no fail-open) ------

def test_inv021_rc2_pending_survives_restart_negative_oracle(tmp_path):
    path = tmp_path / "pending-dispositions.json"
    s1 = ConflictDispositionStore(path)
    s1.detect_and_record(
        [
            tx("t-1", "data_strategy", to="REAL-DATA", action="promote"),
            tx("t-1", "data_strategy", to="MOCK", action="keep"),
        ]
    )
    assert s1.has_pending() is True

    # simulate crash/restart: a brand-new instance over the same file must still
    # see the conflict and REFUSE to advance (the silent fail-open hole).
    s2 = ConflictDispositionStore(path)
    assert s2.has_pending() is True
    assert s2.can_advance_phase() is False


def test_inv021_rc2_corrupt_pending_file_fails_closed(tmp_path):
    path = tmp_path / "pending-dispositions.json"
    path.write_text("{bad json", encoding="utf-8")

    s = ConflictDispositionStore(path)
    with pytest.raises(ConflictDispositionStoreError):
        s.pending()
    assert s.can_advance_phase() is False


# --- INV-025 / US-6: deterministic headless resolution records justification ---

def test_inv025_headless_resolution_records_structured_justification(tmp_path):
    s = store(tmp_path)
    conflicts = s.detect_and_record(
        [
            tx("t-1", "data_strategy", to="REAL-DATA", action="promote"),
            tx("t-1", "status", to="tombstoned", action="delete"),
        ]
    )
    disp = s.resolve_headless(conflicts[0].conflict_id)
    assert disp.resolution == "headless-precedence"
    assert disp.precedence_rule
    assert disp.decision_id
    assert disp.winning_transition is not None
    assert disp.losing_transition is not None
    # more-conservative (destructive delete) wins over promote
    assert disp.winning_transition.action == "delete"

    # resolved -> pending drains -> advance allowed; persists across restart
    assert s.has_pending() is False
    assert s.can_advance_phase() is True
    assert ConflictDispositionStore(
        tmp_path / "pending-dispositions.json"
    ).can_advance_phase() is True


def test_headless_resolution_is_deterministic(tmp_path):
    a = store(tmp_path / "a")
    b = store(tmp_path / "b")
    pair = [
        tx("t-1", "data_strategy", to="REAL-DATA", action="promote"),
        tx("t-1", "status", to="tombstoned", action="delete"),
    ]
    ca = a.detect_and_record(list(pair))
    cb = b.detect_and_record(list(pair))
    assert ca[0].conflict_id == cb[0].conflict_id
    da = a.resolve_headless(ca[0].conflict_id)
    db = b.resolve_headless(cb[0].conflict_id)
    assert da.decision_id == db.decision_id
    assert da.precedence_rule == db.precedence_rule


# --- interactive disposition records a human reason ---------------------------

def test_interactive_resolution_records_reason(tmp_path):
    s = store(tmp_path)
    conflicts = s.detect_and_record(
        [
            tx("t-1", "data_strategy", to="REAL-DATA", action="promote"),
            tx("t-1", "data_strategy", to="MOCK", action="keep"),
        ]
    )
    # conflict.transitions is deterministically sorted; pick the winner by content
    c = conflicts[0]
    win_idx = next(i for i, t in enumerate(c.transitions) if t.to == "REAL-DATA")
    disp = s.resolve_interactive(
        c.conflict_id,
        winning_index=win_idx,
        reason="operator chose REAL-DATA after checking the seam",
    )
    assert disp.resolution == "human"
    assert disp.reason
    assert disp.winning_transition.to == "REAL-DATA"
    assert s.can_advance_phase() is True


def test_interactive_resolution_requires_nonempty_reason(tmp_path):
    s = store(tmp_path)
    conflicts = s.detect_and_record(
        [
            tx("t-1", "data_strategy", to="REAL-DATA", action="promote"),
            tx("t-1", "data_strategy", to="MOCK", action="keep"),
        ]
    )
    with pytest.raises(ValueError):
        s.resolve_interactive(conflicts[0].conflict_id, winning_index=0, reason="  ")
