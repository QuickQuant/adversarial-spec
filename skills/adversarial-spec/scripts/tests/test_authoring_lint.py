"""Tests for happy-path spine authoring and maturity ladder rules."""

from __future__ import annotations

from pathlib import Path

from authoring_lint import AuthoringLint
from tests.test_tmr_schema_contract import valid_tmr
from tmr_schema import TestMaturityRecord, validate_tmr_record

REPO_ROOT = Path(__file__).resolve().parents[4]


def make_record(**overrides) -> TestMaturityRecord:
    return validate_tmr_record(valid_tmr(**overrides))


def test_tc_2_0_authoring_lint_uses_spine_coverage_checker():
    records = [
        make_record(
            tmr_uid="01J0EXEMPLARULID000000020A",
            test_id="TC-1.0",
            user_story="US-1",
            spine=True,
            spine_steps=["S1", "S2"],
        ),
        make_record(
            tmr_uid="01J0EXEMPLARULID000000020B",
            test_id="TC-2.0",
            user_story="US-2",
            spine=True,
            spine_steps=["S1", "S2"],
        ),
    ]

    result = AuthoringLint.check(["US-1", "US-2"], records)

    assert result.passed is True
    assert result.findings == []
    assert result.spine_coverage.phase == "authoring"
    assert result.spine_coverage.uncovered == []
    assert result.spine_coverage.duplicate == []


def test_tc_2_1_failure_test_without_spine_step_ref_is_rejected():
    spine = make_record(
        tmr_uid="01J0EXEMPLARULID000000021A",
        test_id="TC-1.0",
        user_story="US-1",
        spine=True,
        spine_steps=["S1", "S2"],
    )
    failure_test = make_record(
        tmr_uid="01J0EXEMPLARULID000000021B",
        test_id="TC-1.1",
        user_story="US-1",
        spine=False,
        spine_of="TC-1.0",
        spine_step_ref=None,
    )

    result = AuthoringLint.check(["US-1"], [spine, failure_test])

    assert result.passed is False
    assert [finding.code for finding in result.findings] == ["missing_spine_step_ref"]
    assert result.findings[0].target == {"test_id": "TC-1.1", "spine_of": "TC-1.0"}


def test_tc_2_2_two_user_story_fixture_has_exactly_one_spine_each():
    records = [
        make_record(
            tmr_uid="01J0EXEMPLARULID000000022A",
            test_id="TC-1.0",
            user_story="US-1",
            spine=True,
        ),
        make_record(
            tmr_uid="01J0EXEMPLARULID000000022B",
            test_id="TC-2.0",
            user_story="US-2",
            spine=True,
        ),
        make_record(
            tmr_uid="01J0EXEMPLARULID000000022C",
            test_id="TC-2.1",
            user_story="US-2",
            spine=False,
            spine_of="TC-2.0",
            spine_step_ref="S1",
        ),
    ]

    result = AuthoringLint.check(["US-1", "US-2"], records)

    assert result.passed is True
    assert result.spine_coverage.passed is True
    assert result.spine_coverage.uncovered == []
    assert result.spine_coverage.duplicate == []


def test_tc_4_0_nl_with_named_accessor_promotes():
    record = make_record(
        tmr_uid="01J0EXEMPLARULID000000040A",
        test_id="TC-4.0",
        maturity="nl",
        accessors=["OrderGateway"],
    )

    result = AuthoringLint.check(["US-1"], [record])

    assert result.promotions[record.tmr_uid] == "PROMOTE"


def test_tc_4_1_nl_without_named_accessor_blocks():
    record = make_record(
        tmr_uid="01J0EXEMPLARULID000000041A",
        test_id="TC-4.1",
        maturity="nl",
        accessors=[],
    )

    result = AuthoringLint.check(["US-1"], [record])

    assert result.promotions[record.tmr_uid] == "BLOCK"


def test_authoring_model_is_documented_in_phase_docs_and_document_types():
    phase_01 = (
        REPO_ROOT / "skills/adversarial-spec/phases/01-init-and-requirements.md"
    ).read_text(encoding="utf-8")
    phase_02 = (REPO_ROOT / "skills/adversarial-spec/phases/02-roadmap.md").read_text(
        encoding="utf-8"
    )
    document_types = (
        REPO_ROOT / "skills/adversarial-spec/reference/document-types.md"
    ).read_text(encoding="utf-8")
    combined = "\n".join([phase_01, phase_02, document_types])

    for required_text in (
        "happy-path spine designation",
        "spine_step_ref",
        "spine_of",
        "SpineCoverageChecker",
        "nl -> acceptance -> concrete",
        "acceptance has executable meaning without the facade",
        ">=1 named accessor",
    ):
        assert required_text in combined


def test_intake_and_slice_north_star_contract_orders_recovery_and_milestone():
    skill = (REPO_ROOT / "skills/adversarial-spec/SKILL.md").read_text(encoding="utf-8")
    phase_00 = (REPO_ROOT / "skills/adversarial-spec/phases/00-triage.md").read_text(
        encoding="utf-8"
    )
    phase_01 = (
        REPO_ROOT / "skills/adversarial-spec/phases/01-init-and-requirements.md"
    ).read_text(encoding="utf-8")
    phase_02 = (REPO_ROOT / "skills/adversarial-spec/phases/02-roadmap.md").read_text(
        encoding="utf-8"
    )

    assert skill.index("## FIRST GATE — Route New Work Before Bootstrap") < skill.index(
        "## ZEROTH ACTION — Conductor Registration"
    )
    assert "Do not register a conductor" in skill
    assert "### Incomplete Phase 0 Handoff Recovery" in skill
    assert "pipeline_sync_local_session(..., mode=\"repair\")" in skill
    assert "legacy `fizzy_card_id`" in skill
    assert "| evaluated-plans + incomplete intake receipt |" in skill
    assert "journey event is absent" in skill
    assert "card_id,fizzy_card_id" in skill

    intake_receipt = phase_00.index(".intake.json")
    card_creation = phase_00.index("pipeline_create_session(")
    local_repair = phase_00.index("pipeline_sync_local_session(")
    assert intake_receipt < card_creation < local_repair
    assert "sync_local_session=false" in phase_00
    assert 'mode="repair"' in phase_00
    assert "Never re-run triage, mint a new id, or create a" in phase_00

    assert phase_01.index("Restore `todowrite_snapshot`") < phase_01.index(
        "Lock Slice North Star [GATE]"
    )
    assert "Store the confirmed block as `requirements_summary.slice_north_star`." in phase_01
    assert "A `ui-target` names the primary surface and decisive user action." in phase_01

    assert "`bootstrap_steps` must be non-empty only when setup is a" in phase_02
    assert "Exactly one milestone MUST be marked `North Star Milestone: yes`." in phase_02
    assert phase_02.index("### Slice North Star") < phase_02.index(
        "### Milestone 1: [First Useful Outcome]"
    )
    assert "bootstrap is not automatically the useful outcome." in " ".join(phase_02.split())
