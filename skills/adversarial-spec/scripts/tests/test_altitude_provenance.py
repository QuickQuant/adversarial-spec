"""Tests for skill-side altitude provenance and analysis."""

from __future__ import annotations

from altitude_provenance import (
    AltitudeProvenanceAnalyzer,
    record_close_altitude_fit,
    record_depth_triage_node,
)
from provenance_journal import ProvenanceJournalWriter


def writer(tmp_path):
    return ProvenanceJournalWriter(tmp_path / "node-altitude.journal.jsonl")


def create_node(
    journal_writer,
    node_id: str,
    altitude: str,
    *,
    rationale: str = "Depth triage placed this node at the stated blast radius.",
):
    return record_depth_triage_node(
        journal_writer,
        session_id="session-1",
        node_id=node_id,
        initial_altitude=altitude,
        rationale=rationale,
        idempotency_key=f"create-{node_id}",
    )


def fit_node(journal_writer, node_id: str, fit: str):
    return record_close_altitude_fit(
        journal_writer,
        session_id="session-1",
        node_id=node_id,
        altitude_fit=fit,
        rationale=f"Close-time altitude fit is {fit}.",
        idempotency_key=f"fit-{node_id}",
    )


def test_tc_10_0_altitude_fit_right_counts_correct_too_low_does_not(tmp_path):
    journal_writer = writer(tmp_path)
    create_node(journal_writer, "SS-1", "subsystem")
    create_node(journal_writer, "SS-2", "subsystem")
    fit_node(journal_writer, "SS-1", "right")
    fit_node(journal_writer, "SS-2", "too_low")

    summary = AltitudeProvenanceAnalyzer(journal_writer.journal_path).fit_summary()

    assert summary.total == 2
    assert summary.correct == 1
    assert summary.too_low == 1
    assert summary.precision == 0.5


def test_tc_10_1_node_journal_created_at_depth_triage_with_rationale(tmp_path):
    journal_writer = writer(tmp_path)
    receipt = create_node(
        journal_writer,
        "SYS",
        "system",
        rationale="Highest blast item crosses the whole workflow.",
    )

    record = receipt.record
    assert record["subject_type"] == "node"
    assert record["event_type"] == "created"
    assert record["field"] == "altitude"
    assert record["to"] == "system"
    assert record["driver"] == {
        "type": "depth_triage",
        "ref": "phase7-depth-triage",
    }
    assert record["metadata"]["rationale"] == "Highest blast item crosses the whole workflow."


def test_tc_inv_015_meta_analysis_queries_over_node_subjects_only(tmp_path):
    journal_writer = writer(tmp_path)
    create_node(journal_writer, "SYS", "system")
    create_node(journal_writer, "SS-1", "subsystem")
    create_node(journal_writer, "SS-2", "subsystem")
    create_node(journal_writer, "C-1", "component")
    fit_node(journal_writer, "SYS", "right")
    fit_node(journal_writer, "SS-1", "right")
    fit_node(journal_writer, "SS-2", "too_high")
    fit_node(journal_writer, "C-1", "too_low")

    analyzer = AltitudeProvenanceAnalyzer(journal_writer.journal_path)

    assert analyzer.distribution() == {
        "system": 1,
        "subsystem": 2,
        "component": 1,
    }
    assert analyzer.subsystem_precision() == 0.5
    assert analyzer.confusion_matrix()["subsystem"] == {
        "right": 1,
        "too_high": 1,
    }
