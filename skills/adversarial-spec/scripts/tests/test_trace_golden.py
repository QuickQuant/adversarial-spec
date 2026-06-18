"""Golden-corpus verification for the W2-2 TRACE spine-inversion (ORPHANED).

TRACE (REQUIREMENTS_TRACER) is a judgment-tier guardrail; its quality is anchored
by the reproducible golden corpus (US-5, W1-5) rather than a live LLM call. These
tests verify three things deterministically:

1. ORACLE INTEGRITY — the TC-6.0 case lives in golden_cases/manifest.json with the
   expected ORPHANED finding, valid negatives, and a content_hash that still matches
   the on-disk fixture (reproducibility guard). Reuses the W1-5 loader; no
   re-implemented manifest parsing/hashing.
2. COVERAGE LOGIC (AC-3) — prose-but-no-spine -> ORPHANED and the false-positive
   guard (a US that has a spine is NOT flagged) are both computed through
   SpineCoverageChecker, not a re-implemented count.
3. PROMPT CONTRACT — both the REQUIREMENTS_TRACER persona and the
   reference/guardrail-prompts.md TRACE block carry the spine-inversion directive,
   name SpineCoverageChecker, and preserve the non-spine no-flag guard.
"""

from __future__ import annotations

from pathlib import Path

from adversaries import REQUIREMENTS_TRACER
from spine_coverage_checker import SpineCoverageChecker
from tmr_schema import validate_tmr_record
from verification_tier_lint import GoldenManifest, lint_manifest_and_fixtures


def _find_golden_manifest() -> Path:
    """Walk up from this file to the repo root and locate the golden-cases manifest."""
    rel = Path(
        ".adversarial-spec/specs/liveness-gate-test-ladder/golden_cases/manifest.json"
    )
    for parent in Path(__file__).resolve().parents:
        candidate = parent / rel
        if candidate.exists():
            return candidate
    raise AssertionError(f"golden_cases manifest not found above {__file__}")


def _make_tmr(**overrides):
    payload = {
        "tmr_uid": "01J0EXEMPLARULID00000000XY",
        "test_id": "TC-1.0",
        "title": "Default Test Title",
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
        "run_evidence": {
            "tier": "code",
            "command": "uv run pytest tests/test_profile.py -q",
            "cwd": "/repo",
            "repo": "adversarial-spec",
            "commit": "abcdef1",
            "started_at": "2026-06-18T12:00:00Z",
            "finished_at": "2026-06-18T12:00:02Z",
            "exit": 0,
            "result": "pass",
            "env": "dev",
            "artifact_uri": "artifacts/profile.json",
            "artifact_sha256": "a" * 64,
            "runner": "skill-runner",
            "live_or_induced": {"kind": "natural-wait"},
        },
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
    return validate_tmr_record(payload)


def _tc_6_0_case():
    manifest: GoldenManifest = lint_manifest_and_fixtures(_find_golden_manifest())
    cases = {case.case_id: case for case in manifest.cases}
    assert "TC-6.0" in cases, "TC-6.0 (TRACE ORPHANED) must live in the golden corpus"
    return cases["TC-6.0"]


# --- 1. Oracle integrity (judgment tier) -------------------------------------


def test_tc_6_0_oracle_present_and_hash_valid():
    """TC-6.0: ORPHANED case is in the manifest with a hash-stable fixture.

    lint_manifest_and_fixtures re-hashes every fixture and raises on mismatch, so a
    clean return is itself the reproducibility guarantee (W1-5 content_hash).
    """
    case = _tc_6_0_case()
    finding_ids = {f["finding_id"] for f in case.expected_findings}
    assert "ORPHANED_SPINE" in finding_ids
    # The orphaned spine story (US-101) and spine-specific status must be named.
    orphaned = next(f for f in case.expected_findings if f["finding_id"] == "ORPHANED_SPINE")
    assert "US-101" in orphaned["description"]
    assert "ORPHANED-SPINE" in orphaned["description"]
    assert "unit" not in orphaned["description"].lower()
    # Negatives encode the false-positive guard: non-spine missing tests are not TRACE findings.
    assert case.negatives, "TC-6.0 must carry negatives (false-positive guard)"
    assert any("happy-path spine" in n.lower() for n in case.negatives)
    assert any("unit tests are not trace findings" in n.lower() for n in case.negatives)


# --- 2. Coverage logic via SpineCoverageChecker (AC-1 / AC-2 / AC-3) ----------


def test_tc_6_0_prose_without_spine_is_orphaned_via_checker():
    """AC-1: a US with prose but no happy-path spine test -> ORPHANED.

    The fixture's US-101 (Update Profile Picture) has prose + acceptance criteria but
    'No automated test is currently mapped'. With no active spine TMR bound to it, the
    shared SpineCoverageChecker reports it uncovered -> TRACE emits ORPHANED-SPINE.
    """
    roadmap = ["US-101"]
    records: list = []  # no spine test mapped to US-101 (matches the fixture)

    result = SpineCoverageChecker.check(roadmap, records, "trace")

    assert result.uncovered == ["US-101"]
    assert result.passed is False
    assert result.phase == "trace"


def test_tc_6_1_non_spine_missing_edge_test_is_not_flagged_via_checker():
    """AC-2 / TC-6.1: a US that HAS a happy-path spine is NOT orphaned.

    The false-positive guard: missing a non-spine edge/error/unit test never makes a
    user story orphaned. A US with one active spine designation passes the checker,
    so TRACE produces no ORPHANED-SPINE finding for it.
    """
    roadmap = ["US-200"]
    records = [_make_tmr(user_story="US-200", spine=True, test_id="TC-200.0")]

    result = SpineCoverageChecker.check(roadmap, records, "trace")

    assert result.uncovered == []
    assert result.duplicate == []
    assert result.passed is True


# --- 3. Prompt contract (deliverable: adversaries.py + guardrail-prompts.md) ---


def _guardrail_prompts_md() -> str:
    rel = Path("skills/adversarial-spec/reference/guardrail-prompts.md")
    for parent in Path(__file__).resolve().parents:
        candidate = parent / rel
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
    raise AssertionError("guardrail-prompts.md not found")


def test_requirements_tracer_persona_carries_spine_inversion():
    persona = REQUIREMENTS_TRACER.persona
    # The spine-inversion directive and the ORPHANED-SPINE status.
    assert "HAPPY-PATH SPINE" in persona
    assert "ORPHANED-SPINE" in persona
    # AC-3: defers to the shared checker, no re-implemented coverage counting.
    assert "SpineCoverageChecker" in persona
    assert "do NOT re-derive spine coverage" in persona
    # SPINE PRIMACY: absorbs the retired SPINE guardrail's semantic check.
    assert "primary success path" in persona
    # False-positive guard preserved for non-spine tests.
    assert "NON-SPINE" in persona


def test_guardrail_prompts_md_mirrors_persona():
    doc = _guardrail_prompts_md()
    for token in (
        "HAPPY-PATH SPINE",
        "ORPHANED-SPINE",
        "SpineCoverageChecker",
        "primary success path",
        "NON-SPINE",
    ):
        assert token in doc, f"guardrail-prompts.md missing {token!r}"
