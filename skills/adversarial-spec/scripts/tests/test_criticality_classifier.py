from __future__ import annotations

import pytest
from criticality_classifier import CriticalityClassifier
from tests.test_tmr_schema_contract import valid_tmr
from tmr_schema import TestMaturityRecord, validate_tmr_record


def make_record(**overrides) -> TestMaturityRecord:
    payload = valid_tmr(**overrides)
    return validate_tmr_record(payload)


def test_tc_7_2_disagreement_resolution():
    """TC-7.2: Disagreement resolution (explicit False vs non-empty architecture_link resolved to True)."""
    # Create record with explicit critical_seam = False, but non-empty architecture_link on system altitude
    record = make_record(
        altitude="system",
        critical_seam=False,
        criticality_source="explicit",
        architecture_link=["component:emission-toolchain"],
    )

    # Before classification:
    # 1. Reading critical_seam raises ValueError (unclassified)
    with pytest.raises(ValueError, match="rejected because the record has not been classified"):
        _ = record.critical_seam

    # 2. Reading criticality_source raises ValueError
    with pytest.raises(ValueError, match="rejected because the record has not been classified"):
        _ = record.criticality_source

    # 3. Reading architecture_link raises ValueError (restricted)
    with pytest.raises(ValueError, match="Access to 'architecture_link' is restricted"):
        _ = record.architecture_link

    # Classify the record
    classifier = CriticalityClassifier()
    records, findings = classifier.classify([record])

    assert len(records) == 1
    classified_rec = records[0]

    # After classification:
    # 1. Consumer can read critical_seam and it must be coerced/resolved to True
    assert classified_rec.critical_seam is True

    # 2. Consumer can read criticality_source and it must be resolved to "architecture_link"
    assert classified_rec.criticality_source == "architecture_link"

    # 3. Consumer still CANNOT read architecture_link (restricted to classifier only)
    with pytest.raises(ValueError, match="Access to 'architecture_link' is restricted"):
        _ = classified_rec.architecture_link

    # 4. There must be a blocking disagreement finding
    assert len(findings) == 1
    finding = findings[0]
    assert finding.code == "DISAGREEMENT_WARNING"
    assert finding.severity == "blocking"
    assert finding.target == {"tmr_uid": classified_rec.tmr_uid}
    assert "explicit critical_seam = False" in finding.message


def test_tc_inv_009_criticality_unknown_fail_closed_and_rejection():
    """TC-INV-009: Criticality unknown fail-closed on system altitude and unclassified record rejection by consumers."""
    # Part 1: Criticality unknown fail-closed on system altitude
    record_unknown = make_record(
        altitude="system",
        criticality_source="unknown",
        critical_seam=None,
        architecture_link=[],
    )

    classifier = CriticalityClassifier()
    records, findings = classifier.classify([record_unknown])

    assert len(records) == 1
    classified_unknown = records[0]

    # Under system altitude, unknown source -> coerced/resolved to critical_seam = True
    assert classified_unknown.critical_seam is True
    assert classified_unknown.criticality_source == "unknown"
    # No disagreement warning findings (since there is no explicit False vs architecture_link disagreement)
    assert len(findings) == 0

    # Part 2: Unclassified record rejection by consumers
    record_unclassified = make_record(
        altitude="component",
        criticality_source="unknown",
        critical_seam=False,
    )

    # Consumers reading unclassified fields must fail
    with pytest.raises(ValueError, match="rejected because the record has not been classified"):
        _ = record_unclassified.critical_seam

    with pytest.raises(ValueError, match="rejected because the record has not been classified"):
        _ = record_unclassified.criticality_source

    # Sole writer constraint: consumer trying to write to fields must fail
    with pytest.raises(ValueError, match="Only CriticalityClassifier can write to/update field"):
        record_unclassified.critical_seam = True

    with pytest.raises(ValueError, match="Only CriticalityClassifier can write to/update field"):
        record_unclassified.criticality_source = "explicit"


def test_non_system_altitude_behavior():
    """Verify that non-system altitudes do not trigger fail-closed or disagreement warning coercions."""
    record = make_record(
        altitude="component",
        critical_seam=False,
        criticality_source="explicit",
        architecture_link=["component:emission-toolchain"],
    )

    classifier = CriticalityClassifier()
    records, findings = classifier.classify([record])

    assert len(records) == 1
    classified_rec = records[0]

    # Non-system altitude:
    # 1. criticality_source updated to "architecture_link" due to presence of links
    assert classified_rec.criticality_source == "architecture_link"
    # 2. critical_seam keeps its explicit value for non-system records.
    assert classified_rec.critical_seam is False
    # 3. No findings/disagreement warnings
    assert len(findings) == 0
