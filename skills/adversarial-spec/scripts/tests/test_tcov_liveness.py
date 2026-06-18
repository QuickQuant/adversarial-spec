"""Tests for TCOV liveness checks and promoter implementation (W2-3 / card 5749)."""

from __future__ import annotations

from tcov_liveness import TcovLivenessAuditor
from tests.test_tmr_schema_contract import valid_tmr
from tmr_schema import TestMaturityRecord, validate_tmr_record


def make_record(**overrides) -> TestMaturityRecord:
    payload = valid_tmr(**overrides)
    return validate_tmr_record(payload)


def test_tc_7_0_critical_seam_with_real_or_induced():
    """TC-7.0: Critical seam with real/induced test -> no missing_liveness_test finding."""
    # 1. Real data strategy
    rec_real = make_record(
        altitude="system",
        critical_seam=True,
        criticality_source="explicit",
        data_strategy="REAL-DATA",
        live_or_induced=None,
    )

    # 2. Induced test (MOCK with non-null live_or_induced)
    rec_induced = make_record(
        altitude="system",
        critical_seam=True,
        criticality_source="explicit",
        data_strategy="MOCK",
        live_or_induced={"kind": "natural-wait"},
        why_impossible_to_reproduce_live="Needed to mock latency/failure",
        technical_constraint="Cannot force in dev environment",
    )

    auditor = TcovLivenessAuditor()
    findings, promotions = auditor.audit([rec_real, rec_induced])

    # No missing_liveness_test finding should be generated
    missing_liveness_findings = [f for f in findings if f.code == "missing_liveness_test"]
    assert len(missing_liveness_findings) == 0


def test_tc_7_1_mock_only_critical_seam():
    """TC-7.1: Mock-only critical seam -> blocking missing_liveness_test finding."""
    # Mock only critical seam: critical_seam is True, data_strategy == "MOCK", live_or_induced is None
    rec_mock_only = make_record(
        altitude="system",
        critical_seam=True,
        criticality_source="explicit",
        data_strategy="MOCK",
        live_or_induced=None,
        why_impossible_to_reproduce_live="Needed to mock latency/failure",
        technical_constraint="Cannot force in dev environment",
    )

    auditor = TcovLivenessAuditor()
    findings, promotions = auditor.audit([rec_mock_only])

    missing_liveness_findings = [f for f in findings if f.code == "missing_liveness_test"]
    assert len(missing_liveness_findings) == 1
    finding = missing_liveness_findings[0]
    assert finding.severity == "blocking"
    assert finding.target == {"tmr_uid": rec_mock_only.tmr_uid}
    assert "mock-only critical seam is blocked" in finding.message


def test_tc_7_2_criticality_unknown_on_system_altitude_resolved_to_critical():
    """TC-7.2: Criticality unknown on system altitude resolved to critical -> mock-only triggers missing_liveness_test."""
    # Criticality unknown (critical_seam=None, criticality_source="unknown") under system altitude is resolved to True.
    # If mock-only (data_strategy == "MOCK", live_or_induced is None), it should trigger missing_liveness_test.
    rec_unknown = make_record(
        altitude="system",
        critical_seam=None,
        criticality_source="unknown",
        data_strategy="MOCK",
        live_or_induced=None,
        why_impossible_to_reproduce_live="Needed to mock latency/failure",
        technical_constraint="Cannot force in dev environment",
        architecture_link=[],
    )

    auditor = TcovLivenessAuditor()
    findings, promotions = auditor.audit([rec_unknown])

    # Should resolve to critical and trigger missing_liveness_test finding
    missing_liveness_findings = [f for f in findings if f.code == "missing_liveness_test"]
    assert len(missing_liveness_findings) == 1
    finding = missing_liveness_findings[0]
    assert finding.severity == "blocking"
    assert finding.target == {"tmr_uid": rec_unknown.tmr_uid}
    assert "mock-only critical seam is blocked" in finding.message


def test_tc_4_0_promoter_with_named_accessor():
    """TC-4.0: Promoter with >=1 named accessor promotes."""
    rec_nl = make_record(
        maturity="nl",
        accessors=["AccessorOne"],
    )

    auditor = TcovLivenessAuditor()
    findings, promotions = auditor.audit([rec_nl])

    assert promotions.get(rec_nl.tmr_uid) == "PROMOTE"


def test_tc_4_1_promoter_with_empty_accessors():
    """TC-4.1: Promoter with empty accessors blocks promotion."""
    rec_nl_empty = make_record(
        maturity="nl",
        accessors=[],
    )

    auditor = TcovLivenessAuditor()
    findings, promotions = auditor.audit([rec_nl_empty])

    assert promotions.get(rec_nl_empty.tmr_uid) == "BLOCK"


def test_data_strategy_mismatch_findings():
    """Test data_strategy_mismatch findings for non-real data strategy with empty/null why_impossible_to_reproduce_live."""
    # A non-real data strategy (e.g. MOCK) with empty/null why_impossible_to_reproduce_live
    rec_synthetic = make_record(
        altitude="component",
        critical_seam=False,
        criticality_source="explicit",
        data_strategy="SYNTHETIC",
        why_impossible_to_reproduce_live=None,
    )

    auditor = TcovLivenessAuditor()
    findings, promotions = auditor.audit([rec_synthetic])

    mismatch_findings = [f for f in findings if f.code == "data_strategy_mismatch"]
    assert len(mismatch_findings) == 1
    finding = mismatch_findings[0]
    assert finding.severity == "blocking"
    assert finding.target == {"tmr_uid": rec_synthetic.tmr_uid}
    assert "why_impossible_to_reproduce_live is empty/null" in finding.message
