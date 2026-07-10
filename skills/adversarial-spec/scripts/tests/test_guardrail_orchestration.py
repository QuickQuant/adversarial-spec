"""Tests for parallel guardrail orchestration."""

from __future__ import annotations

import json

from guardrail_orchestration import (
    GUARDRAIL_ORDER,
    GuardrailAggregate,
    GuardrailOrchestrator,
    GuardrailPayload,
    GuardrailResult,
    GuardrailTransientError,
    StructuredFinding,
    persist_round_results,
)


def prompts() -> dict[str, str]:
    return {guardrail: f"{guardrail} persona" for guardrail in GUARDRAIL_ORDER}


def run_orchestrator(dispatch, *, action="gauntlet", sleeper=lambda _: None):
    orchestrator = GuardrailOrchestrator(dispatch, backoff_seconds=0.01, sleeper=sleeper)
    return orchestrator.run(
        action=action,
        persona_prompts=prompts(),
        content_bundle={
            "spec": "current spec",
            "roadmap": "US-1\nUS-2",
            "tests": "TC-1.0",
        },
        text_diff="@@ spec changed @@",
        tmr_semantic_delta={
            "changed_records": [
                {"tmr_uid": "tmr-1", "test_id": "TC-1.0", "user_story": "US-1"}
            ],
            "join_keys": ["tmr-1", "TC-1.0", "US-1"],
        },
    )


def test_tc_5_0_five_separate_structured_results_are_persisted(tmp_path):
    calls: list[str] = []

    def dispatch(payload: GuardrailPayload) -> GuardrailResult:
        calls.append(payload.guardrail)
        return GuardrailResult(
            guardrail=payload.guardrail,
            findings=[
                StructuredFinding(
                    guardrail=payload.guardrail,
                    code=f"{payload.guardrail}_FINDING",
                    message="finding",
                    target_type="user_story",
                    target_id="US-1",
                    severity="warning",
                )
            ],
        )

    aggregate = run_orchestrator(dispatch, action="critique")
    out_path = tmp_path / "round-1" / "guardrail-results.json"
    persist_round_results(out_path, aggregate)
    persisted = json.loads(out_path.read_text(encoding="utf-8"))

    assert sorted(calls) == sorted(GUARDRAIL_ORDER)
    assert set(aggregate.results) == set(GUARDRAIL_ORDER)
    assert len(aggregate.findings) == 5
    assert persisted["results"]["CONS"]["findings"][0]["target_id"] == "US-1"
    assert persisted["outcome"] == "warn"


def test_tc_5_1_subagents_receive_text_diff_and_tmr_semantic_delta():
    captured: dict[str, GuardrailPayload] = {}

    def dispatch(payload: GuardrailPayload) -> GuardrailResult:
        captured[payload.guardrail] = payload
        return GuardrailResult(guardrail=payload.guardrail)

    run_orchestrator(dispatch)

    for guardrail in GUARDRAIL_ORDER:
        payload = captured[guardrail]
        assert payload.text_diff == "@@ spec changed @@"
        assert payload.tmr_semantic_delta["join_keys"] == ["tmr-1", "TC-1.0", "US-1"]
        assert payload.content_bundle["tests"] == "TC-1.0"


def test_tc_5_2_subagent_failure_synthesizes_orch_and_blocks_gauntlet():
    def dispatch(payload: GuardrailPayload) -> GuardrailResult:
        if payload.guardrail == "TCOV":
            raise RuntimeError("subagent died")
        return GuardrailResult(guardrail=payload.guardrail)

    aggregate = run_orchestrator(dispatch, action="gauntlet")

    assert aggregate.outcome == "block"
    assert aggregate.results["TCOV"].orch_error == "subagent died"
    assert aggregate.results["TCOV"].findings[0].code == "ORCH"
    assert aggregate.results["TCOV"].findings[0].severity == "blocking"
    assert sum(result.passed for result in aggregate.results.values()) == 4


def test_tc_5_3_transient_error_retries_before_orch():
    attempts = {"TCOV": 0}
    sleeps: list[float] = []

    def dispatch(payload: GuardrailPayload) -> GuardrailResult:
        if payload.guardrail == "TCOV":
            attempts["TCOV"] += 1
            if attempts["TCOV"] == 1:
                raise GuardrailTransientError("429")
        return GuardrailResult(guardrail=payload.guardrail)

    aggregate = run_orchestrator(dispatch, sleeper=sleeps.append)

    assert aggregate.outcome == "pass"
    assert aggregate.results["TCOV"].attempts == 2
    assert aggregate.results["TCOV"].orch_error is None
    assert sleeps == [0.01]


def test_finalize_gate_blocks_on_warning_severity_cons_finding():
    """Option a (q-20260709-two-matrix-ownership): finalize has no next round —
    an unresolved CONS finding blocks even at warning severity."""

    def dispatch(payload: GuardrailPayload) -> GuardrailResult:
        if payload.guardrail != "CONS":
            return GuardrailResult(guardrail=payload.guardrail)
        return GuardrailResult(
            guardrail="CONS",
            findings=[
                StructuredFinding(
                    guardrail="CONS",
                    code="OWNERSHIP_CONTRADICTION",
                    message="table homed in two components",
                    target_type="section",
                    target_id="sec-10.5",
                    severity="warning",
                )
            ],
        )

    assert run_orchestrator(dispatch, action="finalize").outcome == "block"
    # Same finding mid-debate stays a warning (fix-next-round preserved).
    assert run_orchestrator(dispatch, action="critique").outcome == "warn"


def test_finalize_gate_non_cons_warning_does_not_block():
    def dispatch(payload: GuardrailPayload) -> GuardrailResult:
        if payload.guardrail != "TCOV":
            return GuardrailResult(guardrail=payload.guardrail)
        return GuardrailResult(
            guardrail="TCOV",
            findings=[
                StructuredFinding(
                    guardrail="TCOV",
                    code="TCOV_GAP",
                    message="coverage gap",
                    target_type="test",
                    target_id="TC-1.0",
                    severity="warning",
                )
            ],
        )

    assert run_orchestrator(dispatch, action="finalize").outcome == "warn"


def test_finalize_subagent_failure_is_fail_closed():
    def dispatch(payload: GuardrailPayload) -> GuardrailResult:
        if payload.guardrail == "CONS":
            raise RuntimeError("subagent died")
        return GuardrailResult(guardrail=payload.guardrail)

    aggregate = run_orchestrator(dispatch, action="finalize")

    assert aggregate.outcome == "block"
    assert aggregate.results["CONS"].findings[0].severity == "blocking"


def test_tc_inv_010_journal_only_tmr_changing_findings():
    def dispatch(payload: GuardrailPayload) -> GuardrailResult:
        if payload.guardrail != "CANON":
            return GuardrailResult(guardrail=payload.guardrail)
        return GuardrailResult(
            guardrail=payload.guardrail,
            findings=[
                StructuredFinding(
                    guardrail="CANON",
                    code="SPEC_DRIFT",
                    message="section prose changed",
                    target_type="section",
                    target_id="sec-4",
                    severity="warning",
                    changes_tmr_field=False,
                ),
                StructuredFinding(
                    guardrail="CANON",
                    code="TMR_FIELD_CHANGE",
                    message="maturity changed",
                    target_type="tmr",
                    target_id="tmr-1",
                    severity="warning",
                    changes_tmr_field=True,
                    tmr_uid="tmr-1",
                    field="maturity",
                ),
            ],
        )

    aggregate: GuardrailAggregate = run_orchestrator(dispatch, action="critique")
    journalable = aggregate.journalable_findings()

    assert [finding.code for finding in journalable] == ["TMR_FIELD_CHANGE"]
    assert journalable[0].tmr_uid == "tmr-1"
    assert journalable[0].field == "maturity"
