"""Tests for the W0-3 GateResult contract."""

from __future__ import annotations

import pytest
from gate_result import (
    EXIT_BY_OUTCOME,
    GATE_OUTCOMES,
    GateFinding,
    GateResult,
    coverage_block,
    exit_code_for_outcome,
    mcp_error_for_outcome,
    pass_result,
    schema_error,
    setup_error,
    warn_result,
)
from pydantic import ValidationError

pytestmark = pytest.mark.deterministic


def finding(code: str = "missing_spine", severity: str = "blocking") -> GateFinding:
    return GateFinding(
        code=code,
        message="US-3 has no active happy-path spine TMR",
        severity=severity,
        target={"user_story": "US-3"},
    )


def test_outcome_exit_map_is_canonical_ac1():
    assert EXIT_BY_OUTCOME == {
        "pass": 0,
        "warn": 0,
        "block": 2,
        "schema_error": 3,
        "orch_error": 4,
        "setup_error": 5,
    }
    for outcome, exit_code in EXIT_BY_OUTCOME.items():
        assert exit_code_for_outcome(outcome) == exit_code
    with pytest.raises(ValueError, match="unknown gate outcome"):
        exit_code_for_outcome("golden-eval")


def test_warn_exits_zero_with_findings_ac1():
    result = warn_result([finding(severity="warning")])
    assert result.outcome == "warn"
    assert result.exit_code() == 0
    assert result.findings[0].severity == "warning"


def test_gate_result_envelope_uses_outcome_not_result_ac2():
    result = pass_result()
    envelope = result.to_envelope()
    assert envelope == {
        "outcome": "pass",
        "findings": [],
        "override_eligible": False,
    }
    assert "result" not in envelope

    with pytest.raises(ValidationError):
        GateResult.model_validate(
            {
                "outcome": "pass",
                "result": "pass",
                "findings": [],
                "override_eligible": False,
            }
        )


def test_schema_and_setup_errors_are_not_override_eligible_ac3():
    for outcome in ("schema_error", "setup_error", "orch_error"):
        with pytest.raises(ValidationError, match="not override-eligible"):
            GateResult(
                outcome=outcome,
                findings=[finding(code=outcome)],
                override_eligible=True,
            )

    assert schema_error([finding("bad_tmr")]).override_eligible is False
    assert setup_error([finding("missing_manifest")]).override_eligible is False


def test_coverage_block_is_override_eligible_and_exit_2_tc81():
    result = coverage_block([finding()])
    assert result.outcome == "block"
    assert result.exit_code() == 2
    assert result.override_eligible is True
    assert result.to_envelope()["findings"][0]["target"] == {"user_story": "US-3"}


def test_pass_result_is_exit_zero_tc80():
    result = pass_result()
    assert result.outcome == "pass"
    assert result.exit_code() == 0
    assert result.mcp_error_code() is None


def test_mcp_error_map_and_closed_outcome_set_tcinv018():
    assert set(GATE_OUTCOMES) == set(EXIT_BY_OUTCOME)
    assert mcp_error_for_outcome("block") == "GATE_BLOCKED"
    assert mcp_error_for_outcome("schema_error") == "GATE_SCHEMA_ERROR"
    assert mcp_error_for_outcome("setup_error") == "GATE_SETUP_ERROR"
    assert mcp_error_for_outcome("pass") is None
    with pytest.raises(ValueError, match="unknown gate outcome"):
        mcp_error_for_outcome("golden-eval")
