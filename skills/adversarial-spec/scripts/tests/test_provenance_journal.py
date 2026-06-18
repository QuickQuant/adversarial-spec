"""Tests for the W0-5 provenance journal writer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from provenance_journal import (
    JournalTransition,
    ProvenanceJournalError,
    ProvenanceJournalWriter,
    StaleExpectedFromError,
    active_spine_records,
    append_decision_log,
    extract_decision_ids,
)

pytestmark = pytest.mark.deterministic


def transition(
    *,
    field: str = "data_strategy",
    from_value: object = "MOCK",
    to_value: object = "REAL-DATA",
    expected_from: object = "MOCK",
    idempotency_key: str = "idem-1",
    driver: dict[str, str] | None = None,
    subject_id: str = "tmr-1",
    event_type: str = "field_changed",
) -> JournalTransition:
    return JournalTransition(
        session_id="session-1",
        subject_type="test",
        subject_id=subject_id,
        event_type=event_type,
        field=field,
        from_value=from_value,
        to_value=to_value,
        expected_from=expected_from,
        driver=driver or {"type": "guardrail", "ref": "TCOV-r2-7a3f"},
        idempotency_key=idempotency_key,
    )


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def write_registry(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text(json.dumps({"records": records}, sort_keys=True))


def base_tmr(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "tmr_uid": "tmr-1",
        "test_id": "TC-0",
        "title": "Old title",
        "user_story": "US-9",
        "status": "active",
        "tombstoned_at": None,
        "supersedes": [],
        "spine": True,
    }
    record.update(overrides)
    return record


def test_append_only_two_changes_keep_prior_byte_range_ac1_tc91(tmp_path):
    journal = tmp_path / "registry.journal.jsonl"
    writer = ProvenanceJournalWriter(journal)

    first = writer.append_transition(transition(), current_fallback="MOCK")
    first_bytes = journal.read_bytes()
    first_range = first_bytes[: len(first_bytes)]

    second = writer.append_transition(
        transition(
            from_value="REAL-DATA",
            to_value="REAL-DATA + PROPERTY",
            expected_from="REAL-DATA",
            idempotency_key="idem-2",
        )
    )

    assert first.appended is True
    assert second.appended is True
    assert journal.read_bytes()[: len(first_range)] == first_range
    records = writer.replay_subject("test", "tmr-1")
    assert [record["to"] for record in records] == [
        "REAL-DATA",
        "REAL-DATA + PROPERTY",
    ]
    assert not hasattr(writer, "edit_record")


def test_accepted_non_guardrail_changes_are_journaled_ac2_tc90(tmp_path):
    writer = ProvenanceJournalWriter(tmp_path / "registry.journal.jsonl")

    created = writer.append_transition(
        transition(
            field="maturity",
            from_value=None,
            to_value="nl",
            expected_from=None,
            idempotency_key="create-1",
            event_type="created",
            driver={"type": "promotion", "ref": "promote-TC-9.0"},
        )
    )
    evidence = writer.append_transition(
        transition(
            field="run_evidence",
            from_value=None,
            to_value={"tier": "code", "result": "pass"},
            expected_from=None,
            idempotency_key="receipt-1",
            driver={"type": "run_evidence", "ref": "pytest-20260618"},
        )
    )

    assert created.record["driver"] == {
        "type": "promotion",
        "ref": "promote-TC-9.0",
    }
    assert evidence.record["driver"]["type"] == "run_evidence"
    assert len(read_jsonl(writer.journal_path)) == 2


def test_replayed_idempotency_appends_once_and_stale_expected_from_rejected_ac3(tmp_path):
    writer = ProvenanceJournalWriter(tmp_path / "registry.journal.jsonl")
    first_transition = transition()

    first = writer.append_transition(first_transition, current_fallback="MOCK")
    replay = writer.append_transition(first_transition)

    assert first.appended is True
    assert replay.appended is False
    assert replay.record["record_id"] == first.record["record_id"]
    assert len(read_jsonl(writer.journal_path)) == 1

    with pytest.raises(StaleExpectedFromError, match="stale expected_from"):
        writer.append_transition(
            transition(
                from_value="MOCK",
                to_value="SYNTHETIC",
                expected_from="MOCK",
                idempotency_key="stale-1",
            )
        )


def test_registry_update_and_journal_append_roll_back_on_append_failure_ac4(tmp_path, monkeypatch):
    registry = tmp_path / "tmr-registry.json"
    write_registry(registry, [base_tmr(data_strategy="MOCK")])
    writer = ProvenanceJournalWriter(tmp_path / "registry.journal.jsonl")

    def update(payload: dict[str, object]) -> dict[str, object]:
        payload["records"][0]["data_strategy"] = "REAL-DATA"  # type: ignore[index]
        return payload

    def fail_append(*args: object, **kwargs: object) -> object:
        raise RuntimeError("simulated crash before journal append")

    monkeypatch.setattr(writer, "_append_transition_locked", fail_append)

    with pytest.raises(RuntimeError, match="simulated crash"):
        writer.apply_registry_transition(
            registry,
            transition(),
            update,
            current_fallback="MOCK",
        )

    assert json.loads(registry.read_text())["records"][0]["data_strategy"] == "MOCK"
    assert not writer.journal_path.exists()


def test_rename_replacement_and_tombstoned_records_do_not_satisfy_fprime_ac5(tmp_path):
    registry = tmp_path / "tmr-registry.json"
    write_registry(registry, [base_tmr()])
    writer = ProvenanceJournalWriter(tmp_path / "registry.journal.jsonl")

    rename_receipt = writer.rename_tmr(
        registry,
        tmr_uid="tmr-1",
        new_test_id="TC-9.0",
        new_title="Provenance journal spine",
        session_id="session-1",
        driver={"type": "human_correction", "ref": "rename-1"},
        idempotency_key="rename-1",
    )
    after_rename = json.loads(registry.read_text())
    renamed = after_rename["records"][0]
    assert renamed["tmr_uid"] == "tmr-1"
    assert renamed["test_id"] == "TC-9.0"
    assert rename_receipt.record["event_type"] == "rename"

    writer.replace_tmr(
        registry,
        old_tmr_uid="tmr-1",
        new_record=base_tmr(
            tmr_uid="tmr-2",
            test_id="TC-9.1",
            title="Replacement spine",
        ),
        tombstoned_at="2026-06-18T20:00:00Z",
        session_id="session-1",
        driver={"type": "human_correction", "ref": "replace-1"},
        idempotency_key="replace-1",
    )
    final_registry = json.loads(registry.read_text())
    old, new = final_registry["records"]
    assert old["status"] == "tombstoned"
    assert old["tombstoned_at"] == "2026-06-18T20:00:00Z"
    assert new["tmr_uid"] == "tmr-2"
    assert new["supersedes"] == ["tmr-1"]
    assert active_spine_records(final_registry, "US-9") == [new]


def test_per_subject_replay_uses_index_not_full_scan_ac6_tcinv013(tmp_path):
    journal = tmp_path / "registry.journal.jsonl"
    writer = ProvenanceJournalWriter(journal)
    writer.append_transition(transition(idempotency_key="target-1"), current_fallback="MOCK")
    writer.append_transition(
        transition(
            subject_id="tmr-other",
            idempotency_key="other-1",
        ),
        current_fallback="MOCK",
    )
    writer.append_transition(
        transition(
            from_value="REAL-DATA",
            to_value="REAL-DATA + PROPERTY",
            expected_from="REAL-DATA",
            idempotency_key="target-2",
        )
    )

    lines = journal.read_bytes().splitlines(keepends=True)
    lines[1] = b"not-json-but-same-line-length".ljust(len(lines[1]) - 1, b"!") + b"\n"
    journal.write_bytes(b"".join(lines))

    replayed = writer.replay_subject("test", "tmr-1")
    assert [record["idempotency_key"] for record in replayed] == [
        "target-1",
        "target-2",
    ]


def test_plain_text_decisions_log_joins_to_override_driven_journal_record_ac7(tmp_path):
    decisions_log = tmp_path / "sessions" / "session-1.decisions.log"
    decision_id = "DEC-20260618-001"
    line = append_decision_log(
        decisions_log,
        decision_id=decision_id,
        text="override accepted for TC-9.0; follow-up correction required",
        timestamp="2026-06-18T20:00:00Z",
    )
    writer = ProvenanceJournalWriter(tmp_path / "registry.journal.jsonl")
    receipt = writer.append_transition(
        transition(
            field="binding_status",
            from_value="unbound",
            to_value="bound",
            expected_from="unbound",
            idempotency_key="decision-correction-1",
            driver={"type": "decision", "ref": decision_id},
        ),
        current_fallback="unbound",
    )

    assert line.startswith("2026-06-18T20:00:00Z decision_id=DEC-20260618-001 ")
    assert not decisions_log.read_text().lstrip().startswith("{")
    assert decision_id in extract_decision_ids(decisions_log.read_text())
    assert receipt.record["driver"] == {"type": "decision", "ref": decision_id}


def test_invalid_driver_type_rejected():
    with pytest.raises(ProvenanceJournalError, match="driver"):
        transition(driver={"type": "session", "ref": "not-allowed"})
