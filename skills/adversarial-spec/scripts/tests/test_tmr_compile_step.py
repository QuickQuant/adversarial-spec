"""Tests for the prose-to-TMR compile step."""

from __future__ import annotations

import json

import pytest
from tmr_compile_step import (
    CompileCandidate,
    HumanConfirmationRequiredError,
    compile_tmr_records,
    mint_ulid,
    write_confirmed_registry,
)
from tmr_schema import SchemaValidationError


def valid_candidate(**overrides) -> CompileCandidate:
    record = {
        "test_id": "TC-1.0",
        "title": "Happy path compile step",
        "user_story": "US-1",
        "maturity": "acceptance",
        "data_strategy": "REAL-DATA",
        "spine": True,
        "verification_mode": "automated-contract",
        "verification_scope": "targeted",
        "altitude": "component",
        "tested_by": "llm",
        "critical_seam": False,
        "criticality_source": "explicit",
        "binding_status": "unbound",
        "status": "active",
        "source_spec": "tests-pseudo.md",
        "live_or_induced": {"kind": "natural-wait"},
        "run_evidence": None,
        "why_impossible_to_reproduce_live": None,
        "technical_constraint": None,
        "also_covers": [],
        "accessors": ["GatewayAccessor"],
        "architecture_link": [],
        "spine_steps": ["S1", "S2"],
        "supersedes": [],
        "tombstoned_at": None,
        "spine_of": None,
        "spine_step_ref": None,
    }
    record.update(overrides.pop("record_overrides", {}))
    return CompileCandidate(
        anchor=overrides.pop("anchor", "tests-pseudo.md#tc-1-0"),
        record=record | overrides,
    )


def deterministic_uid() -> str:
    return "01J0ABCDEFGHJKMNPQRSTVWXYZ"


def test_tc_1_0_compiler_mints_ulid_and_rejects_llm_allocated_identity():
    result = compile_tmr_records(
        [valid_candidate()],
        accessor_symbols={"GatewayAccessor"},
        uid_factory=deterministic_uid,
    )

    assert result.records[0]["tmr_uid"] == deterministic_uid()
    assert len(result.records[0]["tmr_uid"]) == 26
    assert result.echo_diff[0].event == "add"

    with pytest.raises(SchemaValidationError) as exc_info:
        compile_tmr_records(
            [valid_candidate(tmr_uid="01J0ABCDEFGHJKMNPQRSTVWXYA")],
            accessor_symbols={"GatewayAccessor"},
        )
    assert exc_info.value.code == "schema_error"
    assert exc_info.value.field == "tmr_uid"
    assert "compiler mints" in exc_info.value.detail


def test_tc_1_0_duplicate_anchor_and_duplicate_tmr_uid_are_schema_errors():
    with pytest.raises(SchemaValidationError) as anchor_exc:
        compile_tmr_records(
            [
                valid_candidate(anchor="same", test_id="TC-1.0"),
                valid_candidate(anchor="same", test_id="TC-1.1"),
            ],
            accessor_symbols={"GatewayAccessor"},
            uid_factory=deterministic_uid,
        )
    assert anchor_exc.value.field == "anchor"

    existing = compile_tmr_records(
        [valid_candidate()],
        accessor_symbols={"GatewayAccessor"},
        uid_factory=deterministic_uid,
    ).records
    with pytest.raises(SchemaValidationError) as uid_exc:
        compile_tmr_records(
            [
                valid_candidate(anchor="a", tmr_uid=deterministic_uid(), test_id="TC-1.0"),
                valid_candidate(anchor="b", tmr_uid=deterministic_uid(), test_id="TC-1.1"),
            ],
            existing_records=existing,
            accessor_symbols={"GatewayAccessor"},
        )
    assert uid_exc.value.field == "tmr_uid"


def test_tc_1_3_validate_on_emit_malformed_record_fails_closed():
    malformed = valid_candidate()
    malformed.record.pop("status")

    with pytest.raises(SchemaValidationError) as exc_info:
        compile_tmr_records(
            [malformed],
            accessor_symbols={"GatewayAccessor"},
            uid_factory=deterministic_uid,
        )

    assert exc_info.value.code == "schema_error"
    assert exc_info.value.field == "status"


def test_echo_diff_prose_view_and_human_confirm_gate(tmp_path):
    result = compile_tmr_records(
        [valid_candidate()],
        accessor_symbols={"GatewayAccessor"},
        uid_factory=deterministic_uid,
    )
    registry_path = tmp_path / "tmr-registry.json"

    assert result.requires_human_confirm is True
    assert "## TC-1.0" in result.prose_view
    assert deterministic_uid() in result.prose_view
    assert json.loads(result.echo_diff_json())[0]["event"] == "add"

    with pytest.raises(HumanConfirmationRequiredError):
        write_confirmed_registry(registry_path, result, confirmed=False)
    write_confirmed_registry(registry_path, result, confirmed=True)
    assert json.loads(registry_path.read_text(encoding="utf-8"))[0]["tmr_uid"] == deterministic_uid()


def test_prose_rename_diffs_on_tmr_uid_not_delete_add():
    existing = compile_tmr_records(
        [valid_candidate()],
        accessor_symbols={"GatewayAccessor"},
        uid_factory=deterministic_uid,
    ).records

    renamed = compile_tmr_records(
        [
            valid_candidate(
                tmr_uid=deterministic_uid(),
                test_id="TC-8.0",
                title="Renamed happy path compile step",
            )
        ],
        existing_records=existing,
        accessor_symbols={"GatewayAccessor"},
    )

    assert [event.event for event in renamed.echo_diff] == ["rename"]
    assert renamed.echo_diff[0].tmr_uid == deterministic_uid()
    assert renamed.echo_diff[0].changes["test_id"] == {"from": "TC-1.0", "to": "TC-8.0"}


def test_tc_inv_004_compile_cite_resolves_accessor_symbols():
    result = compile_tmr_records(
        [valid_candidate()],
        accessor_symbols={"GatewayAccessor": "gateway.client.submit"},
        uid_factory=deterministic_uid,
    )
    assert result.records[0]["accessors"] == ["gateway.client.submit"]

    with pytest.raises(SchemaValidationError) as exc_info:
        compile_tmr_records(
            [valid_candidate(accessors=["MissingAccessor"])],
            accessor_symbols={"GatewayAccessor": "gateway.client.submit"},
            uid_factory=deterministic_uid,
        )
    assert exc_info.value.field == "accessors"
    assert "MissingAccessor" in exc_info.value.detail


def test_mint_ulid_shape():
    uid = mint_ulid()
    assert len(uid) == 26
    assert set(uid) <= set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
