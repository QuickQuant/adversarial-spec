"""Unit tests for the TMR registry parser (W0-2)."""

from __future__ import annotations

import json

import pytest
from tests.test_tmr_schema_contract import valid_code_evidence, valid_tmr
from tmr_parser import TmrParser
from tmr_schema import SchemaValidationError

pytestmark = pytest.mark.deterministic


def test_parser_round_trip_valid_registry_tc10(tmp_path):
    """TC-1.0: Round-trip valid registry.

    Verifies a valid registry is parsed correctly with no dropped fields,
    identity is preserved on tmr_uid, and it works via string and file parsing.
    """
    records_data = [
        valid_tmr(tmr_uid="01J0EXEMPLARULID0000000001", test_id="TC-1.0"),
        valid_tmr(tmr_uid="01J0EXEMPLARULID0000000002", test_id="TC-2.0", spine=False),
    ]

    json_str = json.dumps(records_data)

    # 1. Parse from string
    records = TmrParser.parse_string(json_str)
    assert len(records) == 2
    assert records[0].tmr_uid == "01J0EXEMPLARULID0000000001"
    assert records[0].test_id == "TC-1.0"
    assert records[0].spine is True

    assert records[1].tmr_uid == "01J0EXEMPLARULID0000000002"
    assert records[1].test_id == "TC-2.0"
    assert records[1].spine is False

    # 2. Parse from file
    temp_file = tmp_path / "tmr-registry.json"
    temp_file.write_text(json_str, encoding="utf-8")
    file_records = TmrParser.parse_file(temp_file)
    assert len(file_records) == 2
    assert file_records[0].tmr_uid == "01J0EXEMPLARULID0000000001"
    assert file_records[1].tmr_uid == "01J0EXEMPLARULID0000000002"


def test_parser_rejects_unknown_missing_bad_enum_ambiguous_scalar_tc13():
    """TC-1.3: Reject unknown/missing key / bad enum / ambiguous scalar.

    Verifies that SchemaValidationError is raised citing the offending field.
    """
    # Unknown key
    record_unknown = valid_tmr(unexpected_field="silent drift")
    with pytest.raises(SchemaValidationError) as exc:
        TmrParser.parse_string(json.dumps([record_unknown]))
    assert exc.value.field == "unexpected_field"

    # Missing required key
    record_missing = valid_tmr()
    record_missing.pop("status")
    with pytest.raises(SchemaValidationError) as exc:
        TmrParser.parse_string(json.dumps([record_missing]))
    assert exc.value.field == "status"

    # Bad enum value
    record_bad_enum = valid_tmr(data_strategy="FAKE-DATA")
    with pytest.raises(SchemaValidationError) as exc:
        TmrParser.parse_string(json.dumps([record_bad_enum]))
    assert exc.value.field == "data_strategy"

    # Ambiguous scalar (bool coerced from string)
    record_ambiguous_bool = valid_tmr(spine="true")
    with pytest.raises(SchemaValidationError) as exc:
        TmrParser.parse_string(json.dumps([record_ambiguous_bool]))
    assert exc.value.field == "spine"

    # Ambiguous scalar (bool coerced from int)
    record_ambiguous_bool_int = valid_tmr(spine=1)
    with pytest.raises(SchemaValidationError) as exc:
        TmrParser.parse_string(json.dumps([record_ambiguous_bool_int]))
    assert exc.value.field == "spine"

    # Reject string 'null' as value
    record_str_null = valid_tmr(why_impossible_to_reproduce_live="null")
    with pytest.raises(SchemaValidationError) as exc:
        TmrParser.parse_string(json.dumps([record_str_null]))
    assert exc.value.field == "why_impossible_to_reproduce_live"
    assert "Ambiguous scalar value" in exc.value.detail

    # Reject string 'None' as value
    record_str_none = valid_tmr(why_impossible_to_reproduce_live="None")
    with pytest.raises(SchemaValidationError) as exc:
        TmrParser.parse_string(json.dumps([record_str_none]))
    assert exc.value.field == "why_impossible_to_reproduce_live"

    # Reject string '~' as value
    record_str_tilde = valid_tmr(why_impossible_to_reproduce_live="~")
    with pytest.raises(SchemaValidationError) as exc:
        TmrParser.parse_string(json.dumps([record_str_tilde]))
    assert exc.value.field == "why_impossible_to_reproduce_live"

    # Reject ambiguous string in nested structure (run_evidence)
    evidence_bad = valid_code_evidence(command="null")
    record_nested_bad = valid_tmr(run_evidence=evidence_bad)
    with pytest.raises(SchemaValidationError) as exc:
        TmrParser.parse_string(json.dumps([record_nested_bad]))
    assert exc.value.field == "run_evidence.command"


def test_parser_rejects_duplicate_json_keys_tc14():
    """TC-1.4: Reject duplicate JSON keys.

    Verifies duplicate keys anywhere in JSON structure are detected and raise
    SchemaValidationError citing the duplicate key.
    """
    # Duplicate key at root level of record
    bad_json_root = (
        '[{"tmr_uid": "01J0EXEMPLARULID00000000XY", "tmr_uid": "01J0EXEMPLARULID00000000XY"}]'
    )
    with pytest.raises(SchemaValidationError) as exc:
        TmrParser.parse_string(bad_json_root)
    assert exc.value.field == "tmr_uid"
    assert "Duplicate JSON key" in exc.value.detail

    # Duplicate key in nested object
    bad_json_nested = """
    [{
        "tmr_uid": "01J0EXEMPLARULID00000000XY",
        "test_id": "TC-1.0",
        "title": "Dup Test",
        "user_story": "US-1",
        "maturity": "concrete",
        "data_strategy": "REAL-DATA",
        "spine": true,
        "verification_mode": "automated-contract",
        "verification_scope": "targeted",
        "altitude": "system",
        "tested_by": "llm",
        "critical_seam": false,
        "criticality_source": "explicit",
        "binding_status": "bound",
        "status": "active",
        "source_spec": "liveness-gate-test-ladder",
        "live_or_induced": {"kind": "natural-wait", "kind": "natural-wait"},
        "run_evidence": null
    }]
    """
    with pytest.raises(SchemaValidationError) as exc:
        TmrParser.parse_string(bad_json_nested)
    assert exc.value.field == "kind"
    assert "Duplicate JSON key" in exc.value.detail


def test_parser_rejects_duplicate_tmr_uid_tcinv_004():
    """TC-INV-004: Reject duplicate tmr_uid.

    Verifies list-level validation catches identical tmr_uid values.
    """
    records_data = [
        valid_tmr(tmr_uid="01J0EXEMPLARULID0000000001", test_id="TC-1.0"),
        valid_tmr(tmr_uid="01J0EXEMPLARULID0000000001", test_id="TC-2.0"),
    ]
    with pytest.raises(SchemaValidationError) as exc:
        TmrParser.parse_string(json.dumps(records_data))
    assert exc.value.field == "[1].tmr_uid"
    assert "Duplicate tmr_uid" in exc.value.detail
