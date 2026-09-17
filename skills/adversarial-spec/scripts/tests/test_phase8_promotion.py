"""Tests for Phase-8 pseudo-to-real promotion."""

from __future__ import annotations

from phase8_promotion import (
    RunExecution,
    build_promotion_requests,
    capture_run_evidence,
    evaluate_phase8_close,
)


def record(**overrides):
    payload = {
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
        "negative_oracle": True,
    }
    payload.update(overrides)
    return payload


def passing_receipt(**overrides):
    receipt = {
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
        "live_or_induced": None,
    }
    receipt.update(overrides)
    return receipt


def test_tc_11_1_real_data_critical_seam_with_null_run_evidence_fails_close():
    report = evaluate_phase8_close([record(run_evidence=None)])

    assert report.can_close is False
    assert "run_evidence_missing" in {issue.code for issue in report.issues}


def test_spine_or_critical_seam_cannot_close_as_spike_or_exempt():
    report = evaluate_phase8_close(
        [
            record(run_evidence=passing_receipt(), test_strategy="spike"),
            record(
                tmr_uid="01J0PROMOTIONSTEP000000000B",
                verification_mode="static-check",
                run_evidence=passing_receipt(),
            ),
        ]
    )

    assert [issue.code for issue in report.issues].count("spine_critical_exempt") == 2


def test_tc_11_0_emits_typed_promotion_request_and_halts_unbound_accessors():
    ok = build_promotion_requests(
        [record()],
        command_by_uid={"01J0PROMOTIONSTEP000000000A": "uv run pytest tests/test_gateway.py -q"},
        cwd="/repo",
        repo="owner-repo",
        commit="abcdef1",
    )
    assert ok.requests[0].to_dict()["kind"] == "promotion_request"
    assert ok.requests[0].negative_oracle_required is True
    assert ok.requests[0].owner_authors_and_binds is True

    blocked = build_promotion_requests(
        [record(binding_status="unbound", accessors=[])],
        command_by_uid={"01J0PROMOTIONSTEP000000000A": "uv run pytest tests/test_gateway.py -q"},
        cwd="/repo",
        repo="owner-repo",
        commit="abcdef1",
    )
    assert blocked.requests == []
    assert blocked.issues[0].code == "unbound_accessor_halt"


def test_skill_runner_captures_receipt_and_ignores_owner_written_result():
    intended_ids = {
        "outcome_id": "OUTCOME-GATEWAY",
        "caller_id": "CALLER-GATEWAY",
        "path_id": "PATH-GATEWAY",
    }
    request = build_promotion_requests(
        [record(target_binding=intended_ids)],
        command_by_uid={"01J0PROMOTIONSTEP000000000A": "uv run pytest tests/test_gateway.py -q"},
        cwd="/repo",
        repo="owner-repo",
        commit="abcdef1",
    ).requests[0]

    def failing_runner(_request):
        return RunExecution(
            exit_code=1,
            started_at="2026-06-18T12:00:00Z",
            finished_at="2026-06-18T12:00:02Z",
            artifact_uri="artifacts/gateway.json",
            artifact_sha256="b" * 64,
            live_or_induced={"kind": "natural-wait"},
            target_observation={
                "runtime_receipt_id": "runner-gateway-unit-receipt",
                "pid": 1234,
                "pid_start_time": "2026-06-18T12:00:00Z",
                **intended_ids,
                "entrypoint_observed": "tests/test_gateway.py",
                "authority_ref_observed": "AUTH-GATEWAY",
                "producer_contract_hash": "sha256:" + "a" * 64,
                "consumer_contract_hash": "sha256:" + "b" * 64,
                "terminal_state": "rejected",
            },
        )

    capture = capture_run_evidence(
        request,
        runner=failing_runner,
        env="ci",
        owner_written_result="pass",
    )

    assert capture["capture_state"] == "COMPLETE"
    assert capture["issues"] == []
    assert capture["observation_source"] == "runner"
    assert capture["owner_observation_ignored"] is False
    assert "result" not in capture
    evidence = capture["run_evidence"]
    assert evidence["target_observation"] == capture["runtime_receipt"]
    assert evidence["runner"] == "skill-runner"
    assert evidence["result"] == "fail"
    assert evidence["exit"] == 1


def test_mock_detection_lint_flags_boundary_mock():
    report = evaluate_phase8_close(
        [
            record(
                run_evidence=passing_receipt(live_or_induced={"kind": "natural-wait"}),
                title="Gateway boundary mock is still present",
            )
        ]
    )

    assert "boundary_mock_detected" in {issue.code for issue in report.issues}


def test_env_real_pass_matrix_requires_technique_for_dev_ci_critical_seam():
    dev_without_technique = evaluate_phase8_close(
        [record(run_evidence=passing_receipt(env="dev", live_or_induced=None))]
    )
    ci_with_technique = evaluate_phase8_close(
        [
            record(
                run_evidence=passing_receipt(
                    env="ci",
                    live_or_induced={"kind": "tc-netem:partition"},
                )
            )
        ]
    )

    assert "real_pass_technique_missing" in {
        issue.code for issue in dev_without_technique.issues
    }
    assert ci_with_technique.can_close is True


def test_tc_inv_017_negative_oracle_close_passing_on_null_run_evidence_fails():
    report = evaluate_phase8_close(
        [record(run_evidence=None, negative_oracle=False, negative_oracle_ref=None)]
    )

    codes = {issue.code for issue in report.issues}
    assert "negative_oracle_missing" in codes
    assert "run_evidence_missing" in codes
    assert report.can_close is False
