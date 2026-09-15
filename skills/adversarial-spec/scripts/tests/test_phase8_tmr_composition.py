"""Composition: canonical TMR validation -> Phase 8 promotion (Defect A).

Hardening packet (prediction-prime, 2026-09-13) Defect A: ``phase8_promotion``
read ``negative_oracle`` / ``negative_oracle_ref`` while the canonical TMR
schema forbade them (``extra: forbid``). ``test_phase8_promotion.py`` fed the
promoter untyped dicts and ``test_tmr_schema_contract.py`` never reached the
promoter, so both suites were green while no *validated* record could ever
satisfy promotion. These tests join the two modules so that drift between the
promoter's field names and the keystone is a failing test, not a silent gap.
"""

from __future__ import annotations

import copy
import json

import pytest
from phase8_promotion import evaluate_phase8_close
from tmr_schema import (
    SchemaValidationError,
    dump_tmr_record,
    tmr_json_schema,
    validate_tmr_record,
)

pytestmark = pytest.mark.deterministic

PROMOTER_NEGATIVE_ORACLE_FIELDS = ("negative_oracle", "negative_oracle_ref")

PASSING_RECEIPT = {
    "tier": "code",
    "command": "uv run pytest tests/test_gateway.py -q",
    "cwd": "/repo",
    "repo": "owner-repo",
    "commit": "abcdef1",
    "started_at": "2026-06-18T12:00:00Z",
    "finished_at": "2026-06-18T12:00:02Z",
    "exit": 0,
    "result": "pass",
    "env": "live",
    "artifact_uri": "artifacts/gateway.json",
    "artifact_sha256": "a" * 64,
    "runner": "skill-runner",
    "live_or_induced": {"kind": "natural-wait"},
}

# A REAL-DATA critical/spine record: the class the promoter holds to the
# negative-oracle requirement. Mirrors test_phase8_promotion.record() but is
# routed through the canonical model instead of being handed over raw.
BASE_RECORD = {
    "tmr_uid": "01J0PROMOTIONSTEP000000000A",
    "test_id": "TC-11.0",
    "title": "Real critical seam closes only with runner evidence",
    "user_story": "US-11",
    "maturity": "acceptance",
    "data_strategy": "REAL-DATA",
    "spine": True,
    "verification_mode": "automated-contract",
    "verification_scope": "targeted",
    "altitude": "system",
    "tested_by": "llm",
    "critical_seam": True,
    "criticality_source": "explicit",
    "binding_status": "bound",
    "status": "active",
    "source_spec": "tests-pseudo.md",
    "live_or_induced": {"kind": "natural-wait"},
    "run_evidence": PASSING_RECEIPT,
    "accessors": ["GatewayAccessor"],
    "spine_steps": ["S1", "S2"],
}


def _validated(**overrides) -> dict:
    payload = copy.deepcopy(BASE_RECORD)
    payload.update(overrides)
    validated_record = validate_tmr_record(payload)
    serialized_json = json.dumps(dump_tmr_record(validated_record))
    return json.loads(serialized_json)


def test_promoter_negative_oracle_fields_exist_in_canonical_schema() -> None:
    """The exact drift: the promoter's field names must be keystone fields."""
    properties = tmr_json_schema()["properties"]
    missing = [f for f in PROMOTER_NEGATIVE_ORACLE_FIELDS if f not in properties]
    assert missing == [], f"promoter reads fields the keystone forbids: {missing}"


def test_validated_record_with_negative_oracle_reaches_close() -> None:
    """Defect A reproduction, inverted: validate -> dump -> promote closes."""
    report = evaluate_phase8_close([_validated(negative_oracle=True)])

    codes = {issue.code for issue in report.issues}
    assert "negative_oracle_missing" not in codes
    assert report.can_close is True, codes


def test_validated_record_with_negative_oracle_ref_reaches_close() -> None:
    report = evaluate_phase8_close(
        [_validated(negative_oracle=None, negative_oracle_ref="TC-11.0-neg")]
    )

    codes = {issue.code for issue in report.issues}
    assert "negative_oracle_missing" not in codes
    assert report.can_close is True, codes


def test_validated_record_without_negative_oracle_still_blocks_close() -> None:
    """Null defaults fail the promotion condition; they never waive it."""
    report = evaluate_phase8_close([_validated()])

    assert "negative_oracle_missing" in {issue.code for issue in report.issues}
    assert report.can_close is False


@pytest.mark.parametrize(
    ("field", "value"),
    [("negative_oracle", "yes"), ("negative_oracle", 1), ("negative_oracle_ref", 7)],
)
def test_negative_oracle_fields_are_strictly_typed(field: str, value: object) -> None:
    with pytest.raises(SchemaValidationError) as excinfo:
        validate_tmr_record({**copy.deepcopy(BASE_RECORD), field: value})
    assert excinfo.value.field == field


def test_validated_record_full_json_model_round_trip() -> None:
    """Explicitly verify model -> JSON string -> model validate -> promote."""
    payload = copy.deepcopy(BASE_RECORD)
    payload["negative_oracle"] = True

    record = validate_tmr_record(payload)
    json_str = json.dumps(dump_tmr_record(record))

    reloaded_dict = json.loads(json_str)
    reloaded_record = validate_tmr_record(reloaded_dict)

    assert reloaded_record.negative_oracle is True
    report = evaluate_phase8_close([dump_tmr_record(reloaded_record)])
    assert report.can_close is True

