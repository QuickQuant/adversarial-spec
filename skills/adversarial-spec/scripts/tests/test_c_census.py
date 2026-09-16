"""Unit and contract tests for C-CENSUS (#21550).

Verifies structural trigger evaluation, schema validation, coexistence rules,
predecessor negative proof enforcement, and deterministic fingerprinting.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from authority_census import (
    author_authority_census,
    compute_census_fingerprint,
    discover_effect_paths,
    evaluate_structural_trigger,
    validate_authority_paths,
)
from gate_policy import RejectCode


def make_valid_path(
    path_id: str = "PATH-FLATTEN-V3",
    role: str = "authoritative",
    entrypoint: str = "/flatten",
    authority_ref: str = "AUTH-FLATTEN",
    supersedes: list[str] | None = None,
    compatibility_window: dict | None = None,
    negative_probe_ref: str | None = None,
    disposition: str = "retained",
) -> dict:
    return {
        "path_id": path_id,
        "operation": f"op_{path_id.lower()}",
        "component": "order_gateway",
        "concrete_entrypoint": entrypoint,
        "callers": [
            {
                "caller_id": "CALLER-PRODUCT",
                "kind": "product",
                "evidence_ref": "evidence:product:prod-01",
            }
        ],
        "current_role": role,
        "target_role": role,
        "authority_ref": authority_ref,
        "gate_manifest": ["GATE-CONVERGENCE", "GATE-FRESHNESS"],
        "contract_owner_version": "1.0",
        "deployment_slot": "SLOT-PRIMARY",
        "supersedes": supersedes or [],
        "compatibility_window": compatibility_window,
        "target_disposition": disposition,
        "negative_probe_ref": negative_probe_ref,
        "claim_predicates": {
            "source": {"state": "observed", "evidence_ref": f"ref:{path_id}:source"},
            "integration": {"state": "observed", "evidence_ref": f"ref:{path_id}:integration"},
            "artifact": {"state": "observed", "evidence_ref": f"ref:{path_id}:artifact"},
            "activation": {"state": "observed", "evidence_ref": f"ref:{path_id}:activation"},
            "running": {"state": "observed", "evidence_ref": f"ref:{path_id}:running"},
            "live_acceptance": {"state": "observed", "evidence_ref": f"ref:{path_id}:live"},
            "retirement": {"state": "not_applicable", "reason": "active path"},
        },
    }


def test_structural_trigger_evaluation_control_case():
    """ASP-HARDEN-CTRL-002: Single-path nondeployed component does not trigger census."""
    trigger = evaluate_structural_trigger(
        equivalent_effect_paths_count=1,
        separate_runtime=False,
        authority_role_change=False,
    )
    assert trigger["triggered"] is False
    assert trigger["structural_reasons"] == []
    assert "evaluated_at" in trigger


def test_structural_trigger_evaluation_active_reasons():
    """Triggered on equivalent effect paths, separate runtimes, or authority changes."""
    t1 = evaluate_structural_trigger(equivalent_effect_paths_count=2)
    assert t1["triggered"] is True
    assert t1["structural_reasons"] == ["equivalent_effect_paths"]

    t2 = evaluate_structural_trigger(separate_runtime=True)
    assert t2["triggered"] is True
    assert t2["structural_reasons"] == ["separate_runtime"]

    t3 = evaluate_structural_trigger(authority_role_change=True)
    assert t3["triggered"] is True
    assert t3["structural_reasons"] == ["authority_role_change"]

    t_all = evaluate_structural_trigger(
        equivalent_effect_paths_count=3,
        separate_runtime=True,
        authority_role_change=True,
    )
    assert t_all["triggered"] is True
    assert t_all["structural_reasons"] == [
        "authority_role_change",
        "equivalent_effect_paths",
        "separate_runtime",
    ]


def test_valid_authority_census_passes_schema_and_policy():
    """A well-formed census passes Draft 2020-12 schema and semantic checks."""
    trigger = evaluate_structural_trigger(equivalent_effect_paths_count=1)
    path = make_valid_path()
    outcome_class = {
        "outcome_id": "OUTCOME-FLATTEN",
        "description": "Flatten held position",
        "paths": [path],
    }
    census = author_authority_census(trigger, [outcome_class])
    issues = validate_authority_paths(census)
    assert issues == []


def test_invalid_schema_catches_malformed_stable_id():
    """Schema and semantic validation catch malformed identifiers."""
    trigger = evaluate_structural_trigger(equivalent_effect_paths_count=1)
    path = make_valid_path(path_id="invalid_lowercase_id")
    outcome_class = {
        "outcome_id": "OUTCOME-FLATTEN",
        "description": "Flatten held position",
        "paths": [path],
    }
    census = author_authority_census(trigger, [outcome_class])
    issues = validate_authority_paths(census)
    assert len(issues) > 0
    assert any("SCHEMA_VALIDATION_ERROR" in i.code or "INVALID_STABLE_ID" in i.code for i in issues)


def test_coexistence_without_compatibility_window_yields_proof_path_uncensused():
    """ASP-HARDEN-006: Multiple authoritative paths without compatibility window reject."""
    trigger = evaluate_structural_trigger(equivalent_effect_paths_count=2)
    path1 = make_valid_path(
        path_id="PATH-EXIT-V2",
        role="authoritative",
        entrypoint="/exit",
        authority_ref="AUTH-EXIT",
    )
    path2 = make_valid_path(
        path_id="PATH-FLATTEN-V3",
        role="authoritative",
        entrypoint="/flatten",
        authority_ref="AUTH-FLATTEN",
    )
    outcome_class = {
        "outcome_id": "OUTCOME-FLATTEN",
        "description": "Flatten held position",
        "paths": [path1, path2],
    }
    census = author_authority_census(trigger, [outcome_class])
    issues = validate_authority_paths(census)
    codes = [i.code for i in issues]
    assert RejectCode.PROOF_PATH_UNCENSUSED.value in codes
    assert RejectCode.PREDECESSOR_NEGATIVE_PROOF_MISSING.value in codes


def test_coexistence_with_compatibility_window_and_negative_probe_passes():
    """Coexistence passes when compatibility window and negative probes are defined."""
    trigger = evaluate_structural_trigger(equivalent_effect_paths_count=2)
    compat = {
        "owner": "trading_gateway",
        "reason": "Gradual cutover window from /exit to /flatten",
        "expires": "2026-10-01T00:00:00Z",
        "differential_test_ref": "tests/differential/test_exit_vs_flatten.py",
    }
    path1 = make_valid_path(
        path_id="PATH-EXIT-V2",
        role="authoritative",
        entrypoint="/exit",
        authority_ref="AUTH-EXIT",
        compatibility_window=compat,
        negative_probe_ref="tests/probes/test_exit_v2_inactive.py",
    )
    path2 = make_valid_path(
        path_id="PATH-FLATTEN-V3",
        role="authoritative",
        entrypoint="/flatten",
        authority_ref="AUTH-FLATTEN",
        compatibility_window=compat,
        negative_probe_ref="tests/probes/test_exit_v2_inactive.py",
    )
    outcome_class = {
        "outcome_id": "OUTCOME-FLATTEN",
        "description": "Flatten held position",
        "paths": [path1, path2],
    }
    census = author_authority_census(trigger, [outcome_class])
    issues = validate_authority_paths(census)
    assert issues == []


def test_predecessor_negative_proof_missing():
    """Successor superseding older path without negative probe emits reject code."""
    trigger = evaluate_structural_trigger(authority_role_change=True)
    path = make_valid_path(
        path_id="PATH-FLATTEN-V3",
        role="authoritative",
        entrypoint="/flatten",
        authority_ref="AUTH-FLATTEN",
        supersedes=["PATH-EXIT-V2"],
        negative_probe_ref=None,  # Missing!
    )
    outcome_class = {
        "outcome_id": "OUTCOME-FLATTEN",
        "description": "Flatten held position",
        "paths": [path],
    }
    census = author_authority_census(trigger, [outcome_class])
    issues = validate_authority_paths(census)
    assert any(i.code == RejectCode.PREDECESSOR_NEGATIVE_PROOF_MISSING.value for i in issues)


def test_duplicate_path_id_rejected():
    """Duplicate path_id across outcome classes is halted."""
    trigger = evaluate_structural_trigger(equivalent_effect_paths_count=2)
    path1 = make_valid_path(path_id="PATH-DUPLICATE")
    path2 = make_valid_path(path_id="PATH-DUPLICATE")
    outcome_class1 = {
        "outcome_id": "OUTCOME-A",
        "description": "Outcome A",
        "paths": [path1],
    }
    outcome_class2 = {
        "outcome_id": "OUTCOME-B",
        "description": "Outcome B",
        "paths": [path2],
    }
    census = author_authority_census(trigger, [outcome_class1, outcome_class2])
    issues = validate_authority_paths(census)
    assert any(i.code == "DUPLICATE_PATH_ID" for i in issues)


def test_deterministic_census_fingerprint():
    """Fingerprint is deterministic and immune to transient metadata differences."""
    trigger1 = evaluate_structural_trigger(
        equivalent_effect_paths_count=2,
        rationale="Evaluation round 1",
        evaluated_at=datetime(2026, 9, 15, 10, 0, 0, tzinfo=UTC),
    )
    trigger2 = evaluate_structural_trigger(
        equivalent_effect_paths_count=2,
        rationale="Evaluation round 2 with different notes",
        evaluated_at=datetime(2026, 9, 15, 12, 0, 0, tzinfo=UTC),
    )
    path = make_valid_path()
    outcome_class = {
        "outcome_id": "OUTCOME-FLATTEN",
        "description": "Flatten held position",
        "paths": [path],
    }
    census1 = author_authority_census(trigger1, [outcome_class])
    census2 = author_authority_census(trigger2, [outcome_class])

    fp1 = compute_census_fingerprint(census1)
    fp2 = compute_census_fingerprint(census2)

    assert fp1.startswith("sha256:")
    assert fp1 == fp2, "Transient metadata must not change structural fingerprint"

    # Structural change alters fingerprint
    path_modified = make_valid_path(entrypoint="/flatten_v4")
    census3 = author_authority_census(trigger1, [{
        "outcome_id": "OUTCOME-FLATTEN",
        "description": "Flatten held position",
        "paths": [path_modified],
    }])
    fp3 = compute_census_fingerprint(census3)
    assert fp3 != fp1


def test_discover_effect_paths_from_tmr_bindings():
    """Discovers outcome classes and paths from TMR bindings."""
    records = [
        {
            "target_binding": {
                "outcome_id": "OUTCOME-ORDER-SUBMIT",
                "path_id": "PATH-REST-ORDER",
                "entrypoint": "/api/v1/orders",
                "caller_id": "CALLER-REST-CLIENT",
                "caller_kind": "product",
                "authority_role": "authoritative",
                "authority_ref": "AUTH-REST",
                "predecessor_path_ids": [],
            }
        },
        {
            "target_binding": {
                "outcome_id": "OUTCOME-ORDER-SUBMIT",
                "path_id": "PATH-WS-ORDER",
                "entrypoint": "/ws/orders",
                "caller_id": "CALLER-WS-CLIENT",
                "caller_kind": "product",
                "authority_role": "authoritative",
                "authority_ref": "AUTH-WS",
                "predecessor_path_ids": [],
            }
        },
    ]
    outcome_classes = discover_effect_paths(records)
    assert len(outcome_classes) == 1
    assert outcome_classes[0]["outcome_id"] == "OUTCOME-ORDER-SUBMIT"
    assert len(outcome_classes[0]["paths"]) == 2
    path_ids = [p["path_id"] for p in outcome_classes[0]["paths"]]
    assert "PATH-REST-ORDER" in path_ids
    assert "PATH-WS-ORDER" in path_ids
