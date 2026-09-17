"""TC-10.0, TC-10.1, TC-10.2: Golden regression replay, metamorphic mutations, and reject coverage.

Verifies the 18 historical hardening incident fixtures against pure validators,
proves that single-field mutations are load-bearing, and ensures 100% coverage
across the 22 RejectCode catalog members.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from gate_policy import RejectCode
from golden_harness import (
    CATALOG_PATH,
    check_reject_code_coverage,
    replay_case,
    replay_catalog,
    run_mutation_matrix,
)


def test_tc_10_0_all_eighteen_golden_cases_replay_with_expected_codes():
    """TC-10.0: All 18 golden cases replay with exact expected reject codes.

    15 incident cases produce their expected codes; CTRL-001/002/003 produce [].
    Order-insensitive equality on code sets; no case skipped.
    """
    report = replay_catalog(CATALOG_PATH)
    assert report["total_cases"] == 18, f"Expected 18 cases in catalog, found {report['total_cases']}"
    assert report["failed"] == 0, f"Cases failed replay: {json.dumps({k: v for k, v in report['results'].items() if not v['passed']}, indent=2)}"
    assert report["passed"] == 18

    # Specific assertions for key incident classes
    results = report["results"]
    assert results["ASP-HARDEN-005"]["observed"] == [
        "PROOF_AUTHORITY_ROLE_MISMATCH",
        "PROOF_CALLER_MISMATCH",
        "PROOF_PATH_MISMATCH",
    ]
    assert results["ASP-HARDEN-007"]["observed"] == [
        "PACKAGE_COMPONENT_UNPROVEN",
        "RUNTIME_IDENTITY_INCOMPLETE",
    ]
    assert results["ASP-HARDEN-012"]["observed"] == ["FIXTURE_PROVENANCE_CEILING"]
    assert results["ASP-HARDEN-013"]["observed"] == ["TERMINAL_ENUM_UNCOVERED"]
    assert results["ASP-HARDEN-009"]["observed"] == ["PLAN_SCHEMA_VERSION_TYPE_INVALID"]
    assert results["ASP-HARDEN-010"]["observed"] == ["PLAN_SCHEMA_VERSION_TYPE_INVALID"]

    # All three control cases produce []
    assert results["ASP-HARDEN-CTRL-001"]["observed"] == []
    assert results["ASP-HARDEN-CTRL-002"]["observed"] == []
    assert results["ASP-HARDEN-CTRL-003"]["observed"] == []


def test_tc_10_1_one_field_mutation_produces_specific_code():
    """TC-10.1: One-field mutation sensitivity testing.

    Each single-field mutation on a passing proof fixture produces its
    specific target reject code, proving fields are load-bearing rather than decorative.
    """
    mutations = run_mutation_matrix()
    assert len(mutations) >= 12

    expected_mutation_codes = {
        "caller": RejectCode.PROOF_CALLER_MISMATCH.value,
        "route": RejectCode.PROOF_PATH_MISMATCH.value,
        "authority_role": RejectCode.PROOF_AUTHORITY_ROLE_MISMATCH.value,
        "producer_contract_hash": RejectCode.PRODUCER_CONSUMER_CONTRACT_UNPROVEN.value,
        "consumer_contract_hash": RejectCode.PRODUCER_CONSUMER_CONTRACT_UNPROVEN.value,
        "outcome": RejectCode.PROOF_OUTCOME_MISMATCH.value,
        "pid_stale": RejectCode.RUNTIME_IDENTITY_INCOMPLETE.value,
        "running_source": RejectCode.PACKAGE_COMPONENT_UNPROVEN.value,
        "terminal_enum": RejectCode.TERMINAL_ENUM_UNCOVERED.value,
        "fixture_provenance": RejectCode.FIXTURE_PROVENANCE_CEILING.value,
        "plan_version_type": RejectCode.PLAN_SCHEMA_VERSION_TYPE_INVALID.value,
        "freshness": RejectCode.RUNTIME_IDENTITY_INCOMPLETE.value,
    }

    for name, expected_code in expected_mutation_codes.items():
        observed_code = mutations.get(name)
        assert observed_code == expected_code, f"Mutation {name} expected {expected_code}, observed {observed_code}"
        assert observed_code != "", f"Mutation {name} yielded empty code (decorative field)"


def test_tc_10_2_reject_code_coverage_across_all_twenty_two_members():
    """TC-10.2: Every code in section-5 (22 RejectCodes) has coverage.

    Combines the 18 catalog cases, mutation matrix, and 4 amended synthetic cases
    to prove zero uncovered RejectCodes.
    """
    all_observed_codes: set[str] = set()

    # 1. Collect codes from catalog replay
    report = replay_catalog(CATALOG_PATH)
    for res in report["results"].values():
        all_observed_codes.update(res["observed"])

    # 2. Collect codes from metamorphic mutations
    mutations = run_mutation_matrix()
    all_observed_codes.update(mutations.values())

    # 3. Add the 4 amended cases (TC-10.2 explicit requirement)
    amended_cases = [
        {"case_id": "ASP-AMEND-016-OUTCOME-MISMATCH", "fixture": {}},
        {"case_id": "ASP-AMEND-017-TMR-BINDING-REQUIRED", "fixture": {"target_binding": None}},
        {"case_id": "ASP-AMEND-018-VALIDATE-LOAD-DIVERGENCE", "fixture": {"validate_mode": "warn", "load_mode": "reject"}},
        {"case_id": "ASP-AMEND-019-CUSTODY-ENTRY-MISSING", "fixture": {"worktree_exists": True, "ledger_entry_present": False}},
    ]
    for case in amended_cases:
        all_observed_codes.update(replay_case(case))

    missing = check_reject_code_coverage(all_observed_codes)
    assert missing == set(), f"Uncovered RejectCodes in catalog/mutation test suite: {missing}"
    assert len(all_observed_codes) == 22, f"Expected exactly 22 distinct RejectCodes covered, got {len(all_observed_codes)}"
