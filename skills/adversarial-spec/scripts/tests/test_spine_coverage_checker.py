"""Unit tests for the SpineCoverageChecker."""

from __future__ import annotations

import inspect

import pytest
from spine_coverage_checker import SpineCoverageChecker, check_spine_coverage
from tmr_schema import validate_tmr_record


def make_valid_code_evidence(**overrides):
    evidence = {
        "tier": "code",
        "command": "uv run pytest tests/test_gateway.py -q",
        "cwd": "/repo",
        "repo": "prediction-prime",
        "commit": "abcdef1",
        "started_at": "2026-06-18T12:00:00Z",
        "finished_at": "2026-06-18T12:00:02Z",
        "exit": 0,
        "result": "pass",
        "env": "dev",
        "artifact_uri": "artifacts/fill.json",
        "artifact_sha256": "a" * 64,
        "runner": "skill-runner",
        "live_or_induced": {"kind": "tc-netem:partition"},
    }
    evidence.update(overrides)
    return evidence


def make_valid_tmr(**overrides):
    payload = {
        "tmr_uid": "01J0EXEMPLARULID00000000XY",
        "test_id": "TC-1.0",
        "title": "Default Test Title",
        "user_story": "US-1",
        "maturity": "concrete",
        "data_strategy": "REAL-DATA",
        "spine": True,
        "verification_mode": "automated-contract",
        "verification_scope": "targeted",
        "altitude": "system",
        "tested_by": "llm",
        "critical_seam": False,
        "criticality_source": "explicit",
        "binding_status": "bound",
        "status": "active",
        "source_spec": "liveness-gate-test-ladder",
        "live_or_induced": {"kind": "natural-wait"},
        "run_evidence": make_valid_code_evidence(),
        "why_impossible_to_reproduce_live": None,
        "technical_constraint": None,
        "also_covers": [],
        "accessors": ["tmr_record"],
        "architecture_link": ["component:emission-toolchain"],
        "spine_steps": ["S1", "S2", "S3", "S4"],
        "supersedes": [],
        "tombstoned_at": None,
        "spine_of": None,
        "spine_step_ref": None,
    }
    payload.update(overrides)
    return validate_tmr_record(payload)


def test_tc_8_0_valid_full_coverage():
    """TC-8.0: Valid full coverage (exactly 1 designation per story)."""
    roadmap = ["US-1", "US-2", "US-3"]
    records = [
        make_valid_tmr(tmr_uid="01J0EXEMPLARULID00000000A1", test_id="TC-1.0", user_story="US-1", spine=True),
        make_valid_tmr(tmr_uid="01J0EXEMPLARULID00000000A2", test_id="TC-2.0", user_story="US-2", spine=True),
        make_valid_tmr(tmr_uid="01J0EXEMPLARULID00000000A3", test_id="TC-3.0", user_story="US-3", spine=True),
        # An inactive/non-spine record should not interfere
        make_valid_tmr(tmr_uid="01J0EXEMPLARULID00000000A4", test_id="TC-4.0", user_story="US-1", spine=False),
    ]

    result = SpineCoverageChecker.check(roadmap, records, "gauntlet")
    assert result.passed is True
    assert result.uncovered == []
    assert result.duplicate == []

    # Verify checker function wrapper also works
    func_result = check_spine_coverage(roadmap, records, "gauntlet")
    assert func_result.passed is True
    assert func_result.uncovered == []
    assert func_result.duplicate == []
    # phase is carried onto the result for traceability
    assert result.phase == "gauntlet"
    assert func_result.phase == "gauntlet"


def test_tc_8_4_duplicate_designations():
    """TC-8.4: Duplicate designations (>=2 spine records for a story)."""
    roadmap = ["US-1", "US-2"]
    records = [
        make_valid_tmr(tmr_uid="01J0EXEMPLARULID00000000B1", test_id="TC-1.0", user_story="US-1", spine=True),
        make_valid_tmr(tmr_uid="01J0EXEMPLARULID00000000B2", test_id="TC-2.0", user_story="US-2", spine=True),
        make_valid_tmr(tmr_uid="01J0EXEMPLARULID00000000B3", test_id="TC-3.0", user_story="US-1", spine=True),
    ]

    result = SpineCoverageChecker.check(roadmap, records, "gauntlet")
    assert result.passed is False
    assert result.uncovered == []
    assert result.duplicate == ["US-1"]


def test_tc_inv_001_tombstoned_and_also_covers_ignored_and_uncovered():
    """TC-INV-001: Tombstoned records ignored, also_covers ignored, list user_story ignored, and uncovered stories detected."""
    roadmap = ["US-1", "US-2", "US-3", "US-4"]
    records = [
        # Satisfies US-1
        make_valid_tmr(tmr_uid="01J0EXEMPLARULID00000000C1", test_id="TC-1.0", user_story="US-1", spine=True),
        # Tombstoned spine record for US-2 (ignored, so US-2 becomes uncovered)
        make_valid_tmr(
            tmr_uid="01J0EXEMPLARULID00000000C2",
            test_id="TC-2.0",
            user_story="US-2",
            spine=True,
            status="tombstoned",
            tombstoned_at="2026-06-18T12:00:00Z",
        ),
        # US-3 is in also_covers of an active spine record (ignored, so US-3 remains uncovered)
        make_valid_tmr(
            tmr_uid="01J0EXEMPLARULID00000000C3",
            test_id="TC-3.0",
            user_story="US-1",
            spine=True,
            also_covers=["US-3"],
        ),
        # US-4 is in a list user_story (ignored, so US-4 remains uncovered)
        make_valid_tmr(
            tmr_uid="01J0EXEMPLARULID00000000C4",
            test_id="TC-4.0",
            user_story=["US-4"],
            spine=True,
        ),
    ]

    result = SpineCoverageChecker.check(roadmap, records, "gauntlet")
    assert result.passed is False
    # US-1 is duplicate because we have C1 (active spine for US-1) and C3 (active spine for US-1, also_covers US-3)
    assert result.duplicate == ["US-1"]
    # US-2 (tombstoned), US-3 (only in also_covers), US-4 (only in list user_story) are uncovered
    assert result.uncovered == ["US-2", "US-3", "US-4"]


def test_w04_contract_signature_requires_phase():
    """W0-4 contract: (roadmap US set, parsed TMRs, phase). phase is required."""
    for fn in (SpineCoverageChecker.check, check_spine_coverage):
        params = list(inspect.signature(fn).parameters)
        assert "phase" in params, f"{fn.__name__} missing phase param"
        # phase has no default -> part of the required contract signature
        assert inspect.signature(fn).parameters["phase"].default is inspect.Parameter.empty

    # omitting phase is a TypeError (the 2-arg form codex flagged is no longer valid)
    with pytest.raises(TypeError):
        SpineCoverageChecker.check(["US-1"], [])  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        check_spine_coverage(["US-1"], [])  # type: ignore[call-arg]
