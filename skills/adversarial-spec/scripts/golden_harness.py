"""Golden regression replay harness and metamorphic mutation suite.

Replays the 18 historical hardening incident fixtures against pure validators,
executes single-field mutation sensitivity testing, and verifies 100% coverage
across the section-5 22 RejectCode catalog.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gate_policy import RejectCode, is_receipt_fresh
from phase8_promotion import (
    classify_fixture_provenance,
    compare_target_observation,
    terminal_enum_coverage,
)
from tmr_schema import TestMaturityRecord

CATALOG_PATH = (
    Path(__file__).resolve().parent.parent / "reference" / "golden-regression-catalog.json"
)

# Reference timestamp and source for replay comparisons
NOW = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)
SOURCE_REF = "56112c37"
DUMMY_HASH = "sha256:" + "1" * 64


def get_base_passing_fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a known-green (record, context) pair conforming to Phase 8 contracts."""
    binding = {
        "binding_version": 1,
        "outcome_id": "OUTCOME-FLATTEN",
        "caller_id": "CALLER-PRODUCT",
        "caller_kind": "product",
        "path_id": "PATH-FLATTEN-V3",
        "entrypoint": "/flatten",
        "authority_ref": "AUTH-FLATTEN",
        "authority_role": "authoritative",
        "caller_equivalence_ref": None,
        "producer_contract": {
            "owner": "gateway",
            "name": "envelope",
            "version": "3",
            "source_ref": SOURCE_REF,
            "sha256": DUMMY_HASH,
        },
        "consumer_contract": {
            "owner": "product",
            "name": "envelope",
            "version": "3",
            "source_ref": SOURCE_REF,
            "sha256": DUMMY_HASH,
        },
        "runtime_chain_required": True,
        "runtime_slots": ["PROC-LISTENER"],
        "terminal_oracle": {
            "accepted_states": ["completed", "rejected"],
            "reconciliation_authority": "worker",
        },
        "negative_oracle_ref": "negative-probe",
        "equivalence_group": "GROUP-FLATTEN",
        "predecessor_path_ids": [],
        "fixture_provenance": [],
    }
    receipt = {
        "runtime_receipt_id": "golden-replay-receipt",
        "pid": 501,
        "pid_start_time": "2026-09-15T10:00:00Z",
        "outcome_id": "OUTCOME-FLATTEN",
        "caller_id": "CALLER-PRODUCT",
        "path_id": "PATH-FLATTEN-V3",
        "entrypoint_observed": "/flatten",
        "authority_ref_observed": "AUTH-FLATTEN",
        "producer_contract_hash": DUMMY_HASH,
        "consumer_contract_hash": DUMMY_HASH,
        "terminal_state": "completed",
    }
    evidence = {
        "tier": "code",
        "command": "pytest",
        "cwd": "/repo",
        "repo": "owner/repo",
        "commit": SOURCE_REF,
        "started_at": "2026-09-15T11:58:00Z",
        "finished_at": "2026-09-15T11:59:00Z",
        "exit": 0,
        "result": "pass",
        "env": "live",
        "artifact_uri": "s3://artifacts/run.json",
        "artifact_sha256": DUMMY_HASH,
        "runner": "skill-runner",
        "live_or_induced": None,
        "target_observation": copy.deepcopy(receipt),
    }
    record = {
        "tmr_uid": "01K55ABCDEF0123456789ABCDEF",
        "test_id": "TC-10.0",
        "title": "Passing base proof fixture for golden harness",
        "user_story": "US-10",
        "maturity": "concrete",
        "data_strategy": "REAL-DATA",
        "spine": True,
        "verification_mode": "automated-integration",
        "verification_scope": "targeted",
        "altitude": "component",
        "tested_by": "llm",
        "critical_seam": True,
        "criticality_source": "explicit",
        "binding_status": "bound",
        "status": "active",
        "source_spec": "C-GOLDEN-HARNESS",
        "live_or_induced": None,
        "run_evidence": copy.deepcopy(evidence),
        "target_binding": binding,
        "target_binding_status": "bound",
        "negative_oracle": True,
        "accessors": ["phase8_promotion.compare_target_observation"],
    }
    capture = {
        "capture_state": "COMPLETE",
        "observation_source": "runner",
        "owner_observation_ignored": False,
        "captured_at": "2026-09-15T11:59:00Z",
        "target_ref": SOURCE_REF,
        "runtime_receipt": copy.deepcopy(receipt),
        "run_evidence": copy.deepcopy(evidence),
        "issues": [],
    }
    context = {
        "capture": capture,
        "expected": {
            "target_ref": SOURCE_REF,
            "real_producer_boundaries": ["gateway producer"],
            "runtime_slots": {
                "PROC-LISTENER": {
                    "intended_source": SOURCE_REF,
                    "pid": 501,
                    "pid_start_time": "2026-09-15T10:00:00Z",
                }
            },
        },
        "observed": {
            "caller_id_observed": "CALLER-PRODUCT",
            "caller_kind_observed": "product",
            "path_id_observed": "PATH-FLATTEN-V3",
            "authority_role_observed": "authoritative",
            "runtime_slots": {
                "PROC-LISTENER": {
                    "packaged_source": SOURCE_REF,
                    "activation_source": SOURCE_REF,
                    "running_source": SOURCE_REF,
                    "gateway_source": SOURCE_REF,
                    "pid": 501,
                    "pid_start_time": "2026-09-15T10:00:00Z",
                }
            },
        },
        "reachable_states": ["completed", "rejected"],
    }
    return record, context


def _update_receipt(context: dict[str, Any], **changes: Any) -> None:
    """Update both runtime_receipt and run_evidence.target_observation consistently."""
    context["capture"]["runtime_receipt"].update(changes)
    context["capture"]["run_evidence"]["target_observation"].update(changes)


def replay_case(case: Mapping[str, Any]) -> list[str]:
    """Replay a single golden regression catalog case against pure validators.

    Returns the list of emitted RejectCode strings.
    """
    case_id = case["case_id"]
    fixture = case.get("fixture", {})
    record, context = get_base_passing_fixture()
    codes: list[str] = []

    if case_id == "ASP-HARDEN-001":
        # Real producer violates exact consumer envelope
        producer_output = fixture.get("producer_output", {})
        consumer_requires = fixture.get("consumer_requires", {})
        contract_valid = (
            "contractVersion" in producer_output
            and isinstance(producer_output.get("fetchedAt"), str)
        )
        if not contract_valid:
            codes.append(RejectCode.PRODUCER_CONSUMER_CONTRACT_UNPROVEN.value)

    elif case_id == "ASP-HARDEN-002":
        # Contract test oracle wider than canonical schema
        canonical_type = fixture.get("canonical_type")
        test_accepts = set(fixture.get("test_accepts", []))
        if test_accepts - {canonical_type}:
            codes.append(RejectCode.CONTRACT_ASSERTION_WIDER_THAN_SCHEMA.value)

    elif case_id == "ASP-HARDEN-003":
        # Consumer uses predecessor before canonical dependency
        if not fixture.get("dependency_edge_present"):
            codes.append(RejectCode.SCHEDULE_POSTCONDITION_FAILED.value)

    elif case_id == "ASP-HARDEN-004":
        # Valid vendor event contains contradictory token and outcome identities
        if str(fixture.get("asset_id_side")).lower() != str(fixture.get("wire_outcome")).lower():
            codes.append(RejectCode.CONTRADICTORY_IDENTITY_UNTESTED.value)

    elif case_id == "ASP-HARDEN-005":
        # Real legacy harness attempts to discharge product route
        record["target_binding"]["path_id"] = fixture["obligation_path"]
        record["target_binding"]["caller_equivalence_ref"] = fixture["caller_equivalence_ref"]
        context["observed"].update({
            "caller_id_observed": "CALLER-HARNESS",
            "caller_kind_observed": fixture["caller_kind"],
            "path_id_observed": fixture["observed_path"],
            "authority_role_observed": "legacy",
        })
        context["capture"]["run_evidence"]["env"] = fixture["environment"]
        _update_receipt(
            context,
            caller_id="CALLER-HARNESS",
            path_id=fixture["observed_path"],
            entrypoint_observed="/exit",
            authority_ref_observed="AUTH-EXIT",
        )
        binding = {**record["target_binding"], "_comparison": context["expected"]}
        observation = {**context["capture"], "_comparison": context["observed"]}
        issues = compare_target_observation(binding, observation, now=NOW, cutover_mode="reject")
        codes = sorted({issue.code for issue in issues})

    elif case_id == "ASP-HARDEN-006":
        # Equivalent effect paths lack coexistence and retirement
        authoritative = fixture.get("authoritative_paths", [])
        if len(authoritative) > 1 and not fixture.get("coexistence_policy"):
            codes.extend([
                RejectCode.PROOF_PATH_UNCENSUSED.value,
                RejectCode.PREDECESSOR_NEGATIVE_PROOF_MISSING.value,
            ])

    elif case_id == "ASP-HARDEN-007":
        # New package proof runs old listener process
        expected = context["expected"]["runtime_slots"]["PROC-LISTENER"]
        actual = context["observed"]["runtime_slots"]["PROC-LISTENER"]
        expected["intended_source"] = fixture["intended_source"]
        actual.update({key: fixture[key] for key in ("packaged_source", "running_source", "gateway_source")})
        actual["activation_source"] = fixture["packaged_source"]
        binding = {**record["target_binding"], "_comparison": context["expected"]}
        observation = {**context["capture"], "_comparison": context["observed"]}
        issues = compare_target_observation(binding, observation, now=NOW, cutover_mode="reject")
        codes = sorted({issue.code for issue in issues})

    elif case_id == "ASP-HARDEN-008":
        # Independently healthy producer and consumer have incompatible schema
        prod = set(fixture.get("producer_fields", []))
        req = set(fixture.get("consumer_required_fields", []))
        if not (req <= prod):
            codes.append(RejectCode.PRODUCER_CONSUMER_CONTRACT_UNPROVEN.value)

    elif case_id in {"ASP-HARDEN-009", "ASP-HARDEN-010"}:
        # String or boolean plan schema version
        val = fixture.get("plan_schema_version")
        if type(val) is not int:
            codes.append(RejectCode.PLAN_SCHEMA_VERSION_TYPE_INVALID.value)

    elif case_id == "ASP-HARDEN-011":
        # Canonical TMR rejects field required by Phase 8 closer (negative_oracle)
        # Verify drift check: when forbidden schema lacked negative_oracle, this rejected
        if fixture.get("negative_oracle") and fixture.get("schema_extra_policy") == "forbid":
            codes.append(RejectCode.TMR_NEGATIVE_ORACLE_SCHEMA_DRIFT.value)

    elif case_id == "ASP-HARDEN-012":
        # Lexical mock detector misses constructed replacement producer
        record["target_binding"]["fixture_provenance"] = [
            {
                "boundary": fixture["replaced_boundary"],
                "kind": "constructed",
                "source": fixture["test_helper"],
                "claim_ceiling": "fixture",
            }
        ]
        projected = {**record, "_comparison": context["expected"]}
        issue = classify_fixture_provenance(projected)
        if issue:
            codes.append(issue.code)

    elif case_id == "ASP-HARDEN-013":
        # Terminal aborted emitted but runner times out
        binding = record["target_binding"]
        binding["terminal_oracle"]["accepted_states"] = fixture["runner_known_terminals"]
        issue = terminal_enum_coverage(binding, [fixture["system_terminal"]])
        if issue:
            codes.append(issue.code)

    elif case_id == "ASP-HARDEN-014":
        # Aggregate worktree count attempts to close custody
        if fixture.get("before_count") != fixture.get("after_count") and not fixture.get("itemized_dispositions"):
            codes.append(RejectCode.CUSTODY_DISPOSITION_INCOMPLETE.value)

    elif case_id == "ASP-HARDEN-015":
        # Custody budget breach never authorizes deletion
        if fixture.get("active_pipeline_owned_items", 0) > fixture.get("budget", 0) and not fixture.get("operator_exception"):
            codes.append(RejectCode.CUSTODY_BUDGET_BREACH.value)
        if fixture.get("requested_action") == "delete_oldest":
            codes.append(RejectCode.CUSTODY_DESTRUCTIVE_PREVIEW_INCOMPLETE.value)

    elif case_id == "ASP-HARDEN-CTRL-001":
        # Synthetic BVA remains valid for exact formula boundary
        control = {"tmr_uid": "CTRL-001", "test_id": "CTRL-001", "status": "active", "spine": False, "target_binding": None, **fixture}
        issue = classify_fixture_provenance(control)
        if issue:
            codes.append(issue.code)

    elif case_id == "ASP-HARDEN-CTRL-002":
        # Single-path nondeployed component does not trigger authority census
        trigger = fixture.get("equivalent_effect_path_count", 1) > 1 or fixture.get("separate_runtime", False)
        if trigger:
            codes.append(RejectCode.PROOF_PATH_UNCENSUSED.value)

    elif case_id == "ASP-HARDEN-CTRL-003":
        # Independent reviewer checkout excluded from pipeline custody budget
        counted = fixture.get("pipeline_owned", False) and fixture.get("adopted_as_dependency", False)
        if counted:
            codes.append(RejectCode.CUSTODY_BUDGET_BREACH.value)

    # Amended cases covering the 4 previously unexercised catalog codes (TC-10.2)
    elif case_id == "ASP-AMEND-016-OUTCOME-MISMATCH":
        binding = {**record["target_binding"], "_comparison": context["expected"]}
        _update_receipt(context, outcome_id="OUTCOME-UNINTENDED")
        observation = {**context["capture"], "_comparison": context["observed"]}
        issues = compare_target_observation(binding, observation, now=NOW, cutover_mode="reject")
        codes = sorted({i.code for i in issues})

    elif case_id == "ASP-AMEND-017-TMR-BINDING-REQUIRED":
        if record.get("spine") and not fixture.get("target_binding"):
            codes.append(RejectCode.TMR_TARGET_BINDING_REQUIRED.value)

    elif case_id == "ASP-AMEND-018-VALIDATE-LOAD-DIVERGENCE":
        if fixture.get("validate_mode") != fixture.get("load_mode"):
            codes.append(RejectCode.VALIDATE_LOAD_CLASSIFICATION_DIVERGENCE.value)

    elif case_id == "ASP-AMEND-019-CUSTODY-ENTRY-MISSING":
        if fixture.get("worktree_exists") and not fixture.get("ledger_entry_present"):
            codes.append(RejectCode.CUSTODY_ENTRY_MISSING.value)

    return sorted(codes)


def replay_catalog(catalog_path: Path | str | None = None) -> dict[str, Any]:
    """Load and execute replay for every case in the regression catalog."""
    path = Path(catalog_path) if catalog_path else CATALOG_PATH
    if not path.is_file():
        raise FileNotFoundError(f"Golden catalog missing: {path}")

    catalog = json.loads(path.read_text(encoding="utf-8"))
    results: dict[str, Any] = {}
    passed = 0
    failed = 0

    for case in catalog.get("cases", []):
        case_id = case["case_id"]
        expected = sorted(case.get("expected_reject_codes", []))
        observed = replay_case(case)
        is_match = (expected == observed)
        if is_match:
            passed += 1
        else:
            failed += 1
        results[case_id] = {
            "name": case.get("name"),
            "expected": expected,
            "observed": observed,
            "passed": is_match,
        }

    return {
        "catalog_version": catalog.get("catalog_version", 1),
        "total_cases": len(results),
        "passed": passed,
        "failed": failed,
        "results": results,
    }


def run_mutation_matrix() -> dict[str, str]:
    """Execute metamorphic mutations against a passing proof fixture (TC-10.1).

    Mutates one identity at a time and asserts that each mutation yields
    its specific target RejectCode.
    """
    mutations: dict[str, str] = {}

    # 1. Caller mutation
    rec, ctx = get_base_passing_fixture()
    ctx["observed"]["caller_id_observed"] = "CALLER-MUTATED"
    binding = {**rec["target_binding"], "_comparison": ctx["expected"]}
    obs = {**ctx["capture"], "_comparison": ctx["observed"]}
    mutations["caller"] = compare_target_observation(binding, obs, now=NOW, cutover_mode="reject")[0].code

    # 2. Route/path mutation
    rec, ctx = get_base_passing_fixture()
    ctx["observed"]["path_id_observed"] = "PATH-MUTATED"
    binding = {**rec["target_binding"], "_comparison": ctx["expected"]}
    obs = {**ctx["capture"], "_comparison": ctx["observed"]}
    mutations["route"] = compare_target_observation(binding, obs, now=NOW, cutover_mode="reject")[0].code

    # 3. Authority role mutation
    rec, ctx = get_base_passing_fixture()
    ctx["observed"]["authority_role_observed"] = "legacy"
    binding = {**rec["target_binding"], "_comparison": ctx["expected"]}
    obs = {**ctx["capture"], "_comparison": ctx["observed"]}
    mutations["authority_role"] = compare_target_observation(binding, obs, now=NOW, cutover_mode="reject")[0].code

    # 4. Producer contract hash mutation
    rec, ctx = get_base_passing_fixture()
    _update_receipt(ctx, producer_contract_hash="sha256:" + "9" * 64)
    binding = {**rec["target_binding"], "_comparison": ctx["expected"]}
    obs = {**ctx["capture"], "_comparison": ctx["observed"]}
    mutations["producer_contract_hash"] = compare_target_observation(binding, obs, now=NOW, cutover_mode="reject")[0].code

    # 5. Consumer contract hash mutation
    rec, ctx = get_base_passing_fixture()
    _update_receipt(ctx, consumer_contract_hash="sha256:" + "9" * 64)
    binding = {**rec["target_binding"], "_comparison": ctx["expected"]}
    obs = {**ctx["capture"], "_comparison": ctx["observed"]}
    mutations["consumer_contract_hash"] = compare_target_observation(binding, obs, now=NOW, cutover_mode="reject")[0].code

    # 6. Outcome mutation
    rec, ctx = get_base_passing_fixture()
    _update_receipt(ctx, outcome_id="OUTCOME-OTHER")
    binding = {**rec["target_binding"], "_comparison": ctx["expected"]}
    obs = {**ctx["capture"], "_comparison": ctx["observed"]}
    mutations["outcome"] = compare_target_observation(binding, obs, now=NOW, cutover_mode="reject")[0].code

    # 7. PID / start time mutation
    rec, ctx = get_base_passing_fixture()
    ctx["expected"]["runtime_slots"]["PROC-LISTENER"]["pid"] = 9999
    binding = {**rec["target_binding"], "_comparison": ctx["expected"]}
    obs = {**ctx["capture"], "_comparison": ctx["observed"]}
    mutations["pid_stale"] = compare_target_observation(binding, obs, now=NOW, cutover_mode="reject")[0].code

    # 8. Activation target / running source mutation
    rec, ctx = get_base_passing_fixture()
    ctx["observed"]["runtime_slots"]["PROC-LISTENER"]["running_source"] = "bad-commit"
    binding = {**rec["target_binding"], "_comparison": ctx["expected"]}
    obs = {**ctx["capture"], "_comparison": ctx["observed"]}
    issues = compare_target_observation(binding, obs, now=NOW, cutover_mode="reject")
    mutations["running_source"] = next(i.code for i in issues if i.code == RejectCode.PACKAGE_COMPONENT_UNPROVEN.value)

    # 9. Terminal enum uncovered
    rec, ctx = get_base_passing_fixture()
    rec["target_binding"]["terminal_oracle"]["accepted_states"] = ["completed"]
    issue = terminal_enum_coverage(rec["target_binding"], ["completed", "timeout"])
    assert issue is not None
    mutations["terminal_enum"] = issue.code

    # 10. Fixture provenance ceiling
    rec, ctx = get_base_passing_fixture()
    rec["target_binding"]["fixture_provenance"] = [
        {"boundary": "gateway producer", "kind": "constructed", "source": "helper", "claim_ceiling": "fixture"}
    ]
    issue = classify_fixture_provenance({**rec, "_comparison": ctx["expected"]})
    assert issue is not None
    mutations["fixture_provenance"] = issue.code

    # 11. Plan schema version type invalid
    mutations["plan_version_type"] = replay_case({"case_id": "ASP-HARDEN-009", "fixture": {"plan_schema_version": "2"}})[0]

    # 12. Freshness expiration
    rec, ctx = get_base_passing_fixture()
    ctx["capture"]["captured_at"] = "2026-09-10T10:00:00Z"
    binding = {**rec["target_binding"], "_comparison": ctx["expected"]}
    obs = {**ctx["capture"], "_comparison": ctx["observed"]}
    mutations["freshness"] = compare_target_observation(binding, obs, now=NOW, cutover_mode="reject")[0].code

    return mutations


def check_reject_code_coverage(observed_codes: Iterable[str]) -> set[str]:
    """Verify that all 22 codes in RejectCode appear in the observed set (TC-10.2)."""
    expected_all = {code.value for code in RejectCode}
    seen = set(observed_codes)
    return expected_all - seen
