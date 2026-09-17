"""C-PROMOTION-COMPARE A/B oracle: |T| = |O| = 9; no collection expansion.

SYNTHETIC inputs prove validator behavior, never live boundary reality.
AB_TARGET_ROOT selects every candidate module; AB_CONTROL=good|bad calibrates.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import sys
from contextlib import ExitStack
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
from functools import cache
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import pytest

SUITE_DIR = Path(__file__).resolve().parent
NOW = datetime(2026, 9, 15, 12, tzinfo=timezone.utc)
START = "2026-09-15T10:00:00Z"
SOURCE = "56112c37"
HASH = "sha256:" + "1" * 64
UID = "01K55ABCDEF0123456789ABCDEF"
PREFIXES = ("PROOF_", "RUNTIME_", "FIXTURE_", "TERMINAL_")


def _module(name, path):
    if not path.is_file():
        raise ModuleNotFoundError(f"AB target module missing: {path}", name=name)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@cache
def _contract():
    control = os.environ.get("AB_CONTROL")
    if control in {"good", "bad"}:
        result = _module(f"_ab_promotion_{control}", SUITE_DIR / "ab_controls" / f"{control}_contract.py").MODULE
    else:
        if control:
            raise ValueError(f"Unknown AB_CONTROL: {control!r}")
        if not os.environ.get("AB_TARGET_ROOT"):
            raise ValueError("Set AB_TARGET_ROOT to the candidate checkout; no main-tree fallback")
        scripts = Path(os.environ["AB_TARGET_ROOT"]).resolve() / "skills/adversarial-spec/scripts"
        package = ModuleType("_ab_promotion_candidate")
        package.__path__ = [str(scripts)]
        sys.modules[package.__name__] = package
        schema = _module(f"{package.__name__}.tmr_schema", scripts / "tmr_schema.py")
        policy = _module(f"{package.__name__}.gate_policy", scripts / "gate_policy.py")
        # Both relative and absolute imports resolve to the selected target.
        sys.modules["tmr_schema"] = schema
        sys.modules["gate_policy"] = policy
        sys.path.insert(0, str(scripts))
        promotion = _module(f"{package.__name__}.phase8_promotion", scripts / "phase8_promotion.py")
        result = SimpleNamespace(phase8_promotion=promotion, tmr_schema=schema, gate_policy=policy)
    assert callable(getattr(result.phase8_promotion, "compare_target_observation", None)), (
        "C-PROMOTION-COMPARE missing compare_target_observation"
    )
    return result


def _dict(value):
    return asdict(value) if is_dataclass(value) else value


def _pure_call(function, *args, **kwargs):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("pure promotion validator attempted filesystem, process, or network I/O")
    with ExitStack() as stack:
        for name in ("builtins.open", "io.open", "os.open", "os.stat", "os.listdir",
                     "subprocess.Popen", "subprocess.run", "socket.socket", "os.system"):
            stack.enter_context(patch(name, forbidden))
        return function(*args, **kwargs)


def _codes(contract, issues):
    result = {str(_dict(issue)["code"]) for issue in issues}
    for code in result:
        if code.startswith(PREFIXES) or code in {"PACKAGE_COMPONENT_UNPROVEN", "PRODUCER_CONSUMER_CONTRACT_UNPROVEN"}:
            assert contract.gate_policy.RejectCode(code).value == code
    return result


def _case(case_id):
    catalog = json.loads((SUITE_DIR / "golden-fixtures.json").read_text())
    return next(row for row in catalog["cases"] if row["case_id"] == case_id)


def _inputs(contract):
    """Canonical E-2/E-8 data; comparison-only facts never enter the TMR schema."""
    binding = {
        "binding_version": 1, "outcome_id": "OUTCOME-FLATTEN", "caller_id": "CALLER-PRODUCT",
        "caller_kind": "product", "path_id": "PATH-FLATTEN-V3", "entrypoint": "/flatten",
        "authority_ref": "AUTH-FLATTEN", "authority_role": "authoritative",
        "caller_equivalence_ref": None,
        "producer_contract": {"owner": "gateway", "name": "envelope", "version": "3", "source_ref": SOURCE, "sha256": HASH},
        "consumer_contract": {"owner": "product", "name": "envelope", "version": "3", "source_ref": SOURCE, "sha256": HASH},
        "runtime_chain_required": True, "runtime_slots": ["PROC-LISTENER"],
        "terminal_oracle": {"accepted_states": ["completed", "rejected"], "reconciliation_authority": "worker"},
        "negative_oracle_ref": "negative-probe", "equivalence_group": "GROUP-FLATTEN",
        "predecessor_path_ids": [], "fixture_provenance": [],
    }
    receipt = {
        "runtime_receipt_id": "synthetic-validator-receipt", "pid": 501, "pid_start_time": START,
        "outcome_id": binding["outcome_id"], "caller_id": binding["caller_id"], "path_id": binding["path_id"],
        "entrypoint_observed": binding["entrypoint"], "authority_ref_observed": binding["authority_ref"],
        "producer_contract_hash": HASH, "consumer_contract_hash": HASH, "terminal_state": "completed",
    }
    evidence = {
        "tier": "code", "command": "synthetic-validator-input", "cwd": "/validator-input",
        "repo": "synthetic-validator-input", "commit": SOURCE,
        "started_at": "2026-09-15T11:58:00Z", "finished_at": "2026-09-15T11:59:00Z",
        "exit": 0, "result": "pass", "env": "live", "artifact_uri": "synthetic:validator-input",
        "artifact_sha256": HASH, "runner": "skill-runner", "live_or_induced": None,
        "target_observation": receipt,
    }
    record = {
        "tmr_uid": UID, "test_id": "TC-5.0", "title": "Synthetic input to promotion validator",
        "user_story": "US-5", "maturity": "concrete", "data_strategy": "REAL-DATA",
        "spine": True, "verification_mode": "automated-integration", "verification_scope": "targeted",
        "altitude": "component", "tested_by": "llm", "critical_seam": True,
        "criticality_source": "explicit", "binding_status": "bound", "status": "active",
        "source_spec": "C-PROMOTION-COMPARE", "live_or_induced": None, "run_evidence": evidence,
        "target_binding": binding, "target_binding_status": "bound", "negative_oracle": True,
        "accessors": ["phase8_promotion.compare_target_observation"],
    }
    schema = contract.tmr_schema
    # This exercises the actual candidate schema, not a permissive oracle adapter.
    schema.TargetObservation.model_validate(receipt)
    schema.CodeRunEvidence.model_validate(evidence)
    record = schema.TestMaturityRecord.model_validate(record).model_dump(mode="json")
    capture = {
        "capture_state": "COMPLETE", "observation_source": "runner", "owner_observation_ignored": False,
        "captured_at": "2026-09-15T11:59:00Z", "target_ref": SOURCE,
        "runtime_receipt": copy.deepcopy(receipt), "run_evidence": copy.deepcopy(record["run_evidence"]), "issues": [],
    }
    context = {
        "capture": capture,
        "expected": {
            "target_ref": SOURCE, "real_producer_boundaries": ["gateway producer"],
            "runtime_slots": {"PROC-LISTENER": {"intended_source": SOURCE, "pid": 501, "pid_start_time": START}},
        },
        "observed": {
            "caller_id_observed": "CALLER-PRODUCT", "caller_kind_observed": "product",
            "path_id_observed": "PATH-FLATTEN-V3", "authority_role_observed": "authoritative",
            "runtime_slots": {"PROC-LISTENER": {
                "packaged_source": SOURCE, "activation_source": SOURCE, "running_source": SOURCE,
                "gateway_source": SOURCE, "pid": 501, "pid_start_time": START,
            }},
        },
        "reachable_states": ["completed", "rejected"],
    }
    return record, context


def _compare(contract, record, context, *, now=NOW, mode="reject"):
    binding = {**copy.deepcopy(record["target_binding"]), "_comparison": copy.deepcopy(context["expected"])}
    capture = context["capture"]
    observation = None if capture is None else {**copy.deepcopy(capture), "_comparison": copy.deepcopy(context["observed"])}
    before = copy.deepcopy((binding, observation))
    issues = _pure_call(contract.phase8_promotion.compare_target_observation, binding, observation, now=now, cutover_mode=mode)
    assert isinstance(issues, list)
    assert (binding, observation) == before, "pure comparison must not mutate evidence or obligations"
    _codes(contract, issues)
    return issues


def _close(contract, record, context, *, mode="reject"):
    before = copy.deepcopy((record, context))
    report = _pure_call(contract.phase8_promotion.evaluate_phase8_close,
        [record], now=NOW, cutover_mode=mode, comparison_contexts={record["tmr_uid"]: context},
    )
    assert (record, context) == before, "close evaluation must preserve E-8 records and E-12 partial receipts"
    _codes(contract, report.issues)
    return report


def _receipt(context, **changes):
    context["capture"]["runtime_receipt"].update(changes)
    context["capture"]["run_evidence"]["target_observation"].update(changes)


def _wrong_route(record, context, fixture):
    record["target_binding"]["path_id"] = fixture["obligation_path"]
    record["target_binding"]["caller_equivalence_ref"] = fixture["caller_equivalence_ref"]
    context["observed"].update({
        "caller_id_observed": "CALLER-HARNESS", "caller_kind_observed": fixture["caller_kind"],
        "path_id_observed": fixture["observed_path"], "authority_role_observed": "legacy",
    })
    context["capture"]["run_evidence"]["env"] = fixture["environment"]
    _receipt(context, caller_id="CALLER-HARNESS", path_id=fixture["observed_path"],
             entrypoint_observed="/exit", authority_ref_observed="AUTH-EXIT")


def test_o1_matching_validated_record_closes_and_modes_preserve_old_guards():
    c = _contract()
    for mode in ("reject", "warn", "legacy"):
        record, context = _inputs(c)
        assert _compare(c, record, context, mode=mode) == []
        assert _close(c, record, context, mode=mode).can_close is True
    # A warning must not block close. It also cannot disable existing checks.
    for mode, severity, can_close in (("reject", "halt", False), ("warn", "warning", True)):
        record, context = _inputs(c)
        context["observed"]["path_id_observed"] = "PATH-EXIT-V2"
        issues = _compare(c, record, context, mode=mode)
        assert _codes(c, issues) == {"PROOF_PATH_MISMATCH"}
        assert all(_dict(issue)["severity"] == severity for issue in issues)
        report = _close(c, record, context, mode=mode)
        assert report.can_close is can_close
        assert _codes(c, report.issues) == {"PROOF_PATH_MISMATCH"}
        assert all(_dict(issue)["severity"] == severity for issue in report.issues)
    for field, value, code in (("negative_oracle", False, "negative_oracle_missing"),
                               ("binding_status", "unbound", "unbound_accessor_halt")):
        record, context = _inputs(c)
        record[field] = value
        report = _close(c, record, context, mode="warn")
        assert not report.can_close and code in _codes(c, report.issues)
    record, context = _inputs(c)
    context["capture"]["run_evidence"]["result"] = "fail"
    context["capture"]["run_evidence"]["exit"] = 7
    assert not _close(c, record, context).can_close
    with pytest.raises(ValueError):
        _compare(c, record, context, mode="permissive")


def test_o2_wrong_caller_path_authority_and_contracts_reject_without_live_widening():
    c = _contract()
    case = _case("ASP-HARDEN-005")
    for env in (case["fixture"]["environment"], "dev", "ci"):
        record, context = _inputs(c)
        _wrong_route(record, context, case["fixture"])
        context["capture"]["run_evidence"]["env"] = env
        context["capture"]["run_evidence"]["live_or_induced"] = {"kind": "other", "detail": "validator input"}
        assert _codes(c, _compare(c, record, context)) == set(case["expected_reject_codes"])
        assert not _close(c, record, context).can_close
    rows = [
        ("caller_id_observed", "CALLER-HARNESS", "PROOF_CALLER_MISMATCH"),
        ("caller_kind_observed", "harness", "PROOF_CALLER_MISMATCH"),
        ("path_id_observed", "PATH-EXIT-V2", "PROOF_PATH_MISMATCH"),
        ("authority_role_observed", "legacy", "PROOF_AUTHORITY_ROLE_MISMATCH"),
        ("authority_role_observed", "emergency", "PROOF_AUTHORITY_ROLE_MISMATCH"),
        ("authority_role_observed", "dead", "PROOF_AUTHORITY_ROLE_MISMATCH"),
    ]
    for field, value, code in rows:
        record, context = _inputs(c)
        context["observed"][field] = value
        # Capture's intended caller/path labels still match: measured facts decide.
        assert _codes(c, _compare(c, record, context)) == {code}
    for field, value, code in (
        ("entrypoint_observed", "/exit", "PROOF_PATH_MISMATCH"),
        ("authority_ref_observed", "AUTH-EXIT", "PROOF_AUTHORITY_ROLE_MISMATCH"),
        ("outcome_id", "OUTCOME-OTHER", "PROOF_OUTCOME_MISMATCH"),
        ("producer_contract_hash", "sha256:" + "2" * 64, "PRODUCER_CONSUMER_CONTRACT_UNPROVEN"),
        ("consumer_contract_hash", "sha256:" + "2" * 64, "PRODUCER_CONSUMER_CONTRACT_UNPROVEN"),
    ):
        record, context = _inputs(c)
        _receipt(context, **{field: value})
        assert _codes(c, _compare(c, record, context)) == {code}


def test_o3_package_runtime_join_names_broken_link_and_unproven_component():
    c = _contract()
    case = _case("ASP-HARDEN-007")
    record, context = _inputs(c)
    fixture = case["fixture"]
    expected = context["expected"]["runtime_slots"]["PROC-LISTENER"]
    actual = context["observed"]["runtime_slots"]["PROC-LISTENER"]
    expected["intended_source"] = fixture["intended_source"]
    actual.update({key: fixture[key] for key in ("packaged_source", "running_source", "gateway_source")})
    actual["activation_source"] = fixture["packaged_source"]
    issues = _compare(c, record, context)
    assert _codes(c, issues) == set(case["expected_reject_codes"])
    text = json.dumps([_dict(c.phase8_promotion.diagnose(issue, record)) for issue in issues])
    assert all(word in text for word in ("activation", "running", "PROC-LISTENER", "56112c37", "05742a38"))
    assert not _close(c, record, context).can_close
    actual["running_source"] = fixture["packaged_source"]
    assert _compare(c, record, context) == []
    assert _close(c, record, context).can_close
    for field in ("packaged_source", "activation_source", "running_source", "gateway_source"):
        record, context = _inputs(c)
        context["observed"]["runtime_slots"]["PROC-LISTENER"].pop(field)
        issues = _compare(c, record, context)
        assert _codes(c, issues) == {"RUNTIME_IDENTITY_INCOMPLETE", "PACKAGE_COMPONENT_UNPROVEN"}
        assert all(_dict(c.phase8_promotion.diagnose(i, record))["evidence_class"] == "MISSING" for i in issues)
    record, context = _inputs(c)
    record["target_binding"]["runtime_slots"].append("PROC-WORKER")
    context["expected"]["runtime_slots"]["PROC-WORKER"] = copy.deepcopy(expected)
    assert "PACKAGE_COMPONENT_UNPROVEN" in _codes(c, _compare(c, record, context))
    context["expected"]["runtime_slots"]["PROC-WORKER"]["pid"] = 502
    context["observed"]["runtime_slots"]["PROC-WORKER"] = {
        **copy.deepcopy(context["observed"]["runtime_slots"]["PROC-LISTENER"]), "pid": 502,
    }
    assert _compare(c, record, context) == []


def test_o4_policy_freshness_window_ref_and_process_restart_invalidate(monkeypatch):
    c = _contract()
    assert c.gate_policy.FRESHNESS_WINDOW_SECONDS == 86400
    for age, valid in ((0, True), (86399, True), (86400, True), (86401, False), (-1, False)):
        record, context = _inputs(c)
        context["capture"]["captured_at"] = (NOW - timedelta(seconds=age)).isoformat()
        issues = _compare(c, record, context)
        assert _codes(c, issues) == (set() if valid else {"RUNTIME_IDENTITY_INCOMPLETE"})
        if not valid:
            assert _dict(c.phase8_promotion.diagnose(issues[0], record))["evidence_class"] == "STALE"
    for field, value in (("target_ref", "rebuilt-source"), ("pid", 502),
                         ("pid_start_time", "2026-09-15T11:30:00Z")):
        record, context = _inputs(c)
        if field == "target_ref":
            context["expected"][field] = value
        else:
            context["expected"]["runtime_slots"]["PROC-LISTENER"][field] = value
        issues = _compare(c, record, context)
        assert "RUNTIME_IDENTITY_INCOMPLETE" in _codes(c, issues)
        assert any(_dict(c.phase8_promotion.diagnose(i, record))["evidence_class"] == "STALE" for i in issues)
    # Behavioral dependency test: a local copy of the 24h formula cannot pass.
    record, context = _inputs(c)
    policy_function = c.gate_policy.is_receipt_fresh
    calls = []
    def deny(*args, **kwargs):
        calls.append((args, kwargs))
        return False
    with monkeypatch.context() as patch:
        patch.setattr(c.gate_policy, "is_receipt_fresh", deny)
        # Allow direct imports as well as module-qualified calls.
        for name, value in list(vars(c.phase8_promotion).items()):
            if value is policy_function:
                patch.setattr(c.phase8_promotion, name, deny)
        assert "RUNTIME_IDENTITY_INCOMPLETE" in _codes(c, _compare(c, record, context))
    assert calls
    args, kwargs = calls[-1]
    assert args[:2] == (context["capture"]["captured_at"], NOW)
    assert kwargs == {"target_ref_at_capture": SOURCE, "target_ref_now": SOURCE}


def test_o5_terminal_matrix_names_all_uncovered_states_including_golden_aborted():
    c = _contract()
    record, context = _inputs(c)
    binding = record["target_binding"]
    binding["terminal_oracle"]["accepted_states"] = ["completed"]
    reachable = ["timeout", "completed", "partial", "rejected", "partial"]
    before = copy.deepcopy((binding, reachable))
    issue = c.phase8_promotion.terminal_enum_coverage(binding, reachable)
    assert _codes(c, [issue]) == {"TERMINAL_ENUM_UNCOVERED"}
    diagnostic = _dict(c.phase8_promotion.diagnose(issue, record))
    assert diagnostic["observed"]["uncovered_states"] == ["partial", "rejected", "timeout"]
    assert (binding, reachable) == before
    context["reachable_states"] = reachable
    assert not _close(c, record, context).can_close
    binding["terminal_oracle"]["accepted_states"] = sorted(set(reachable))
    assert c.phase8_promotion.terminal_enum_coverage(binding, reachable) is None
    assert _close(c, record, context).can_close
    fixture = _case("ASP-HARDEN-013")["fixture"]
    binding["terminal_oracle"]["accepted_states"] = fixture["runner_known_terminals"]
    issue = c.phase8_promotion.terminal_enum_coverage(binding, [fixture["system_terminal"]])
    assert _codes(c, [issue]) == set(_case("ASP-HARDEN-013")["expected_reject_codes"])
    assert _dict(c.phase8_promotion.diagnose(issue, record))["observed"]["uncovered_states"] == ["aborted"]


def test_o6_typed_fixture_ceiling_checks_each_bound_real_producer():
    c = _contract()
    case = _case("ASP-HARDEN-012")
    fixture = case["fixture"]
    assert fixture["contains_word_mock"] is False and "mock" not in fixture["test_helper"].lower()
    for kind in ("none", "real-source", "recorded", "constructed", "stub", "mock"):
        for boundary in (fixture["replaced_boundary"], "unrelated formula"):
            record, context = _inputs(c)
            record["target_binding"]["fixture_provenance"] = [
                {"boundary": "unrelated formula", "kind": "none", "source": "formula", "claim_ceiling": "formula"},
                {"boundary": boundary, "kind": kind, "source": fixture["test_helper"], "claim_ceiling": "owner says REAL-DATA"},
            ]
            projected = {**copy.deepcopy(record), "_comparison": copy.deepcopy(context["expected"])}
            before = copy.deepcopy(projected)
            issue = c.phase8_promotion.classify_fixture_provenance(projected)
            reject = kind not in {"none", "real-source"} and boundary == fixture["replaced_boundary"]
            assert projected == before
            if reject:
                assert _codes(c, [issue]) == set(case["expected_reject_codes"])
                diagnostic = _dict(c.phase8_promotion.diagnose(issue, record))
                assert diagnostic["evidence_class"] == "UNSUPPORTED_ORIGIN"
                assert fixture["replaced_boundary"] in json.dumps(diagnostic)
                assert not _close(c, record, context).can_close
            else:
                assert issue is None
                assert _close(c, record, context).can_close
    record, context = _inputs(c)
    record["target_binding"]["fixture_provenance"] = [
        {"boundary": "gateway producer", "kind": "constructed", "source": "makeEnvelope", "claim_ceiling": "fixture"},
    ]
    with pytest.raises(ValueError):
        c.phase8_promotion.classify_fixture_provenance(record)
    report = _close(c, record, context, mode="warn")
    assert report.can_close
    assert _codes(c, report.issues) == {"FIXTURE_PROVENANCE_CEILING"}
    assert all(_dict(i)["severity"] == "warning" for i in report.issues)


def test_o7_lexical_mock_is_advisory_and_ctrl001_has_no_binding_burden():
    c = _contract()
    record, context = _inputs(c)
    record["title"] = "Verified real test - no mocks used anywhere"
    for mode in ("reject", "warn", "legacy"):
        issue = c.phase8_promotion._lint_boundary_mock(record)
        assert issue is not None and _dict(issue)["code"] == "boundary_mock_detected"
        assert _dict(issue)["severity"] == "advisory"
        report = _close(c, record, context, mode=mode)
        assert report.can_close
        assert all(_dict(i)["severity"] == "advisory" for i in report.issues)
    case = _case("ASP-HARDEN-CTRL-001")
    control = {"tmr_uid": "CTRL-001", "test_id": "CTRL-001", "status": "active", "spine": False,
               "target_binding": None, **case["fixture"]}
    before = copy.deepcopy(control)
    assert c.phase8_promotion.requires_target_binding(control) is False
    assert c.phase8_promotion.classify_fixture_provenance(control) is None
    report = c.phase8_promotion.evaluate_phase8_close([control], now=NOW, cutover_mode="reject", comparison_contexts={})
    assert report.can_close and _codes(c, report.issues) == set(case["expected_reject_codes"])
    assert control == before


def test_o8_diagnostics_identify_obligation_values_class_actor_and_recovery():
    c = _contract()
    record, context = _inputs(c)
    record["test_id"] = "TC-13.0"
    _wrong_route(record, context, _case("ASP-HARDEN-005")["fixture"])
    issues = _compare(c, record, context)
    for issue in issues:
        before = copy.deepcopy((_dict(issue), record))
        diagnostic = _dict(c.phase8_promotion.diagnose(issue, record))
        required = {"code", "message", "test_id", "obligation_id", "expected", "observed", "evidence_class", "next_actor", "permitted_recovery"}
        assert required <= diagnostic.keys()
        assert diagnostic["code"] == _dict(issue)["code"]
        assert diagnostic["test_id"] == "TC-13.0" and diagnostic["obligation_id"] == UID
        assert diagnostic["evidence_class"] == "MISMATCH"
        assert diagnostic["expected"] != diagnostic["observed"]
        assert diagnostic["next_actor"] == "worker"
        assert isinstance(diagnostic["permitted_recovery"], list) and diagnostic["permitted_recovery"]
        assert len(diagnostic["message"].split()) >= 5
        assert diagnostic["code"] != diagnostic["message"]
        if diagnostic["code"] == "PROOF_PATH_MISMATCH":
            assert "PATH-FLATTEN-V3" in json.dumps(diagnostic["expected"])
            assert "PATH-EXIT-V2" in json.dumps(diagnostic["observed"])
            assert "PATH-FLATTEN-V3" in " ".join(diagnostic["permitted_recovery"])
        assert (_dict(issue), record) == before
        json.dumps(diagnostic)
    # Recovery is scoped: immutable unrelated records and their completed evidence survive.
    unrelated, good_context = _inputs(c)
    unrelated["tmr_uid"] = "UNRELATED-CLOSED"
    before = copy.deepcopy(unrelated)
    report = c.phase8_promotion.evaluate_phase8_close(
        [record, unrelated], now=NOW, cutover_mode="reject",
        comparison_contexts={UID: context, "UNRELATED-CLOSED": good_context},
    )
    assert not report.can_close and unrelated == before
    assert all(_dict(i)["tmr_uid"] == UID for i in report.issues)
    repaired, repaired_context = _inputs(c)
    assert _close(c, repaired, repaired_context).can_close


def test_o9_missing_partial_and_unsupported_observations_never_become_mismatch_or_pass():
    c = _contract()
    for gap in ("absent", "partial", "receipt_id", "pid", "pid_start_time", "entrypoint",
                "measured_caller", "measured_role", "captured_at", "untrusted", "detached_evidence"):
        record, context = _inputs(c)
        if gap == "absent":
            context["capture"] = None
        elif gap == "partial":
            context["capture"].update(capture_state="INCOMPLETE", run_evidence=None)
            context["capture"]["runtime_receipt"]["pid_start_time"] = None
        elif gap in {"receipt_id", "pid", "pid_start_time", "entrypoint"}:
            field = {"receipt_id": "runtime_receipt_id", "entrypoint": "entrypoint_observed"}.get(gap, gap)
            _receipt(context, **{field: None})
        elif gap.startswith("measured_"):
            context["observed"].pop("caller_id_observed" if gap == "measured_caller" else "authority_role_observed")
        elif gap == "captured_at":
            context["capture"].pop("captured_at")
        elif gap == "untrusted":
            context["capture"]["observation_source"] = "owner"
        else:
            context["capture"]["run_evidence"]["target_observation"]["path_id"] = "PATH-DETACHED"
        issues = _compare(c, record, context)
        codes = _codes(c, issues)
        assert codes == {"RUNTIME_IDENTITY_INCOMPLETE"}
        expected_class = "UNSUPPORTED_ORIGIN" if gap in {"untrusted", "detached_evidence"} else "MISSING"
        assert all(_dict(c.phase8_promotion.diagnose(i, record))["evidence_class"] == expected_class for i in issues)
        assert not _close(c, record, context).can_close
        assert not any(code.startswith("PROOF_") for code in codes)
    # A stored green record cannot replace an absent fresh runner envelope.
    record, context = _inputs(c)
    report = c.phase8_promotion.evaluate_phase8_close([record], now=NOW, cutover_mode="reject", comparison_contexts={})
    assert not report.can_close and _codes(c, report.issues) == {"RUNTIME_IDENTITY_INCOMPLETE"}
