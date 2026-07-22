"""Contract tests for the TMR keystone schema (W0-1)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from tmr_schema import (
    SchemaSnapshotDriftError,
    SchemaValidationError,
    assert_schema_snapshot_current,
    dump_tmr_record,
    lint_tmr_schema_copies,
    schema_sha256,
    tmr_json_schema,
    validate_tmr_record,
)

pytestmark = pytest.mark.deterministic


def valid_code_evidence(**overrides):
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


def valid_tmr(**overrides):
    payload = {
        "tmr_uid": "01J0EXEMPLARULID00000000XY",
        "test_id": "TC-1.0",
        "title": "Round-trip one TMR record",
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
        "run_evidence": valid_code_evidence(),
        # Obligation identity (B-1) -- optional with null defaults, but spelled
        # out here because this round-trip is field-for-field.
        "obligation_revision": "1",
        "obligation_policy_version": "tmr-obligation.v1",
        "required_liveness_class": "natural-wait",
        "required_environment": "live",
        "required_tier": "code",
        "tmr_record_hash": None,
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
    return payload


def test_tmr_round_trips_field_for_field_and_preserves_identity_tc10():
    payload = valid_tmr()
    record = validate_tmr_record(payload)
    dumped = dump_tmr_record(record)

    assert dumped.keys() == payload.keys()
    assert dumped["tmr_uid"] == payload["tmr_uid"]
    assert dumped["test_id"] == payload["test_id"]
    assert dumped["user_story"] == payload["user_story"]
    assert dumped["run_evidence"]["tier"] == "code"
    assert dumped["live_or_induced"] == {"kind": "natural-wait", "detail": None}


def test_unknown_field_and_bad_enum_are_named_schema_errors_tc11_tc12():
    unknown = valid_tmr(unexpected_field="silent drift")
    with pytest.raises(SchemaValidationError) as extra_exc:
        validate_tmr_record(unknown)
    assert extra_exc.value.code == "schema_error"
    assert extra_exc.value.field == "unexpected_field"

    bad_enum = valid_tmr(data_strategy="FAKE-DATA")
    with pytest.raises(SchemaValidationError) as enum_exc:
        validate_tmr_record(bad_enum)
    assert enum_exc.value.code == "schema_error"
    assert enum_exc.value.field == "data_strategy"


def test_missing_required_status_is_rejected_not_defaulted_cb1():
    payload = valid_tmr()
    payload.pop("status")

    with pytest.raises(SchemaValidationError) as exc_info:
        validate_tmr_record(payload)

    assert exc_info.value.field == "status"
    assert "required" in exc_info.value.detail.lower()


def test_tombstone_and_supersedes_shape_cb1():
    tombstoned = valid_tmr(
        status="tombstoned",
        tombstoned_at="2026-06-18T12:00:00Z",
        supersedes=["01J0PREVIOUSULID000000001"],
    )
    assert validate_tmr_record(tombstoned).supersedes == [
        "01J0PREVIOUSULID000000001"
    ]

    missing_tombstone_time = valid_tmr(status="tombstoned", tombstoned_at=None)
    with pytest.raises(SchemaValidationError) as exc_info:
        validate_tmr_record(missing_tombstone_time)
    assert "tombstoned_at" in exc_info.value.detail


def test_live_or_induced_strict_union_tc14():
    validate_tmr_record(valid_tmr(live_or_induced=None))
    validate_tmr_record(valid_tmr(live_or_induced={"kind": "tc-netem:partition"}))
    validate_tmr_record(
        valid_tmr(live_or_induced={"kind": "other", "detail": "cgroups"})
    )

    invalid_values = [
        {"kind": None},
        {"kind": "null"},
        {"kind": "other"},
        {"kind": "state-injection"},
    ]
    for live_or_induced in invalid_values:
        with pytest.raises(SchemaValidationError):
            validate_tmr_record(valid_tmr(live_or_induced=live_or_induced))


def test_mock_null_live_or_induced_requires_justification_and_constraint():
    justified = valid_tmr(
        data_strategy="MOCK",
        critical_seam=False,
        live_or_induced=None,
        why_impossible_to_reproduce_live="No listed or constructible technique exists.",
        technical_constraint="Vendor only exposes this state in an offline simulator.",
    )
    validate_tmr_record(justified)

    missing_constraint = valid_tmr(
        data_strategy="MOCK",
        live_or_induced=None,
        why_impossible_to_reproduce_live="Impossible for cited technical reason.",
        technical_constraint=None,
    )
    with pytest.raises(SchemaValidationError) as exc_info:
        validate_tmr_record(missing_constraint)
    assert "technical_constraint" in exc_info.value.detail


def test_run_evidence_discriminated_union_and_mode_compatibility_cb2():
    validate_tmr_record(valid_tmr(verification_mode="automated-unit"))
    validate_tmr_record(
        valid_tmr(
            verification_mode="system-validation",
            run_evidence={
                "tier": "system-validation",
                "transcript_uri": "artifacts/transcript.md",
                "transcript_sha256": "b" * 64,
                "model": "gpt-5.5",
                "model_settings": {"temperature": 0},
                "prompt_sha256": "c" * 64,
                "corpus_id": "bootstrap-fixture",
                "run_id": "run-1",
                "result": "pass",
                "runner": "skill-runner",
                "captured_at": "2026-06-18T12:00:00Z",
            },
        )
    )
    validate_tmr_record(
        valid_tmr(
            verification_mode="system-validation",
            run_evidence={
                "tier": "judgment",
                "golden_manifest_id": "liveness-mock-falsification",
                "golden_manifest_sha256": "d" * 64,
                "model": "gpt-5.5",
                "model_settings": {"temperature": 0},
                "score": 0.98,
                "threshold": 0.9,
                "per_case_results": [{"case_id": "LIV-POS", "passed": True}],
                "result": "pass",
                "runner": "skill-runner",
                "captured_at": "2026-06-18T12:00:00Z",
            },
        )
    )

    with pytest.raises(SchemaValidationError) as wrong_tier:
        validate_tmr_record(
            valid_tmr(verification_mode="automated-contract", run_evidence={
                "tier": "system-validation",
                "transcript_uri": "artifacts/transcript.md",
                "transcript_sha256": "b" * 64,
                "model": "gpt-5.5",
                "model_settings": {},
                "prompt_sha256": "c" * 64,
                "corpus_id": "fixture",
                "run_id": "run-1",
                "result": "pass",
                "runner": "skill-runner",
                "captured_at": "2026-06-18T12:00:00Z",
            })
        )
    assert "run_evidence.tier='code'" in wrong_tier.value.detail

    with pytest.raises(SchemaValidationError) as exempt_with_receipt:
        validate_tmr_record(
            valid_tmr(verification_mode="static-check", run_evidence=valid_code_evidence())
        )
    assert "run_evidence=null" in exempt_with_receipt.value.detail

    validate_tmr_record(
        valid_tmr(
            maturity="concrete",
            verification_mode="static-check",
            run_evidence=None,
        )
    )
    with pytest.raises(SchemaValidationError) as concrete_unrun:
        validate_tmr_record(valid_tmr(maturity="concrete", run_evidence=None))
    assert "run_evidence is required" in concrete_unrun.value.detail


def test_json_schema_is_extra_forbid_and_hashable_ac2():
    schema = tmr_json_schema(include_generated_comment=True)
    assert schema["additionalProperties"] is False
    assert schema["$comment"] == f"generated-from:{schema_sha256()}"
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", schema_sha256())
    assert "status" in schema["required"]
    assert "live_or_induced" in schema["required"]
    assert "run_evidence" in schema["required"]

    defs = schema["$defs"]
    assert defs["CodeRunEvidence"]["additionalProperties"] is False
    assert defs["LiveOrInducedTechnique"]["additionalProperties"] is False


def test_published_json_schema_file_matches_model():
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "reference"
        / "test-maturity-record.schema.json"
    )
    assert schema_path.exists()
    published = json.loads(schema_path.read_text(encoding="utf-8"))
    assert published == tmr_json_schema(include_generated_comment=True)


def test_schema_snapshot_hash_gate_catches_drift_ac2():
    current = f"> schema_sha256: {schema_sha256()}\n"
    assert_schema_snapshot_current(current)

    stale = "> schema_sha256: sha256:" + ("0" * 64) + "\n"
    with pytest.raises(SchemaSnapshotDriftError):
        assert_schema_snapshot_current(stale)


def test_copy_drift_lint_fails_first_and_never_deletes_inv008(tmp_path):
    canonical = tmp_path / "canonical.md"
    canonical.write_text(
        "# Schema: Test Maturity Record + Guardrail Findings + Provenance Ledger\n"
        f"> schema_sha256: {schema_sha256()}\n"
        "`tmr_uid` and `live_or_induced` live here.\n",
        encoding="utf-8",
    )
    unallowlisted = tmp_path / "copy.md"
    unallowlisted.write_text(canonical.read_text(encoding="utf-8"), encoding="utf-8")
    allowlisted = tmp_path / "generated.md"
    allowlisted.write_text(
        canonical.read_text(encoding="utf-8")
        + f"\n<!-- generated-from:{schema_sha256()} -->\n",
        encoding="utf-8",
    )
    stale = tmp_path / "stale.md"
    stale.write_text(
        canonical.read_text(encoding="utf-8")
        + "\n<!-- generated-from:sha256:"
        + ("0" * 64)
        + " -->\n",
        encoding="utf-8",
    )

    findings = lint_tmr_schema_copies(
        [tmp_path], canonical_path=canonical, canonical_sha256=schema_sha256()
    )

    assert unallowlisted.exists(), "lint must never delete offending files"
    assert stale.exists(), "lint must never delete offending files"
    assert {f.path.name: f.code for f in findings} == {
        "copy.md": "tmr_schema_copy_unallowlisted",
        "stale.md": "tmr_schema_copy_stale_generated_from",
    }
