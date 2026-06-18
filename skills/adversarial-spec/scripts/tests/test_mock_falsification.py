"""Tests for strict MOCK falsification (W2-4 / spec §4.3).

TC-3.0 (justified MOCK cites BOTH why_impossible AND technical_constraint),
TC-3.1 deterministic part (naming a technique => promote), TC-3.2 (critical seam +
non-REAL + empty why_impossible => promote, not just literal MOCK).
"""

from __future__ import annotations

import pytest
from criticality_classifier import CriticalityClassifier
from mock_falsification import MockVerdict, falsify_mock, is_excuse_constraint
from tmr_schema import validate_tmr_record

pytestmark = pytest.mark.deterministic


def make_valid_code_evidence(**overrides):
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


def make_valid_tmr(**overrides):
    payload = {
        "tmr_uid": "01J0EXEMPLARULID00000000XY",
        "test_id": "TC-3.0",
        "title": "Strict MOCK falsification exemplar",
        "user_story": "US-3",
        "maturity": "concrete",
        "data_strategy": "REAL-DATA",
        "spine": False,
        "verification_mode": "automated-unit",
        "verification_scope": "targeted",
        "altitude": "system",
        "tested_by": "llm",
        "critical_seam": True,
        "criticality_source": "explicit",
        "binding_status": "bound",
        "status": "active",
        "source_spec": "liveness-gate-test-ladder",
        "live_or_induced": {"kind": "natural-wait"},
        "run_evidence": make_valid_code_evidence(),
        "why_impossible_to_reproduce_live": None,
        "technical_constraint": None,
        "also_covers": [],
        "accessors": ["seam"],
        "architecture_link": ["component:emission-toolchain"],
        "spine_steps": [],
        "supersedes": [],
        "tombstoned_at": None,
        "spine_of": None,
        "spine_step_ref": None,
    }
    payload.update(overrides)
    record = validate_tmr_record(payload)
    # falsify_mock is a post-classification consumer (INV-009): run the sole-writer
    # CriticalityClassifier so critical_seam is readable and normalized.
    CriticalityClassifier().classify([record])
    return record


# --- REAL-DATA: nothing to falsify ------------------------------------------

def test_real_data_is_justified():
    rec = make_valid_tmr(data_strategy="REAL-DATA", live_or_induced=None)
    assert falsify_mock(rec).outcome == "justified"


# --- TC-3.0: justified MOCK cites BOTH why_impossible AND technical_constraint -

def test_tc3_0_justified_mock_requires_both_fields():
    rec = make_valid_tmr(
        data_strategy="MOCK",
        critical_seam=True,
        live_or_induced=None,
        why_impossible_to_reproduce_live="Boundary only exists behind a vendor prod webhook.",
        technical_constraint="Third-party prod webhook with no sandbox or replay API.",
    )
    # the record genuinely carries both fields
    assert rec.why_impossible_to_reproduce_live
    assert rec.technical_constraint
    assert falsify_mock(rec).outcome == "justified"


def test_mock_missing_technical_constraint_promotes_via_dict():
    # schema requires technical_constraint for MOCK+null, so exercise the guardrail
    # layer on a raw authoring-stage dict that omitted it.
    rec = {
        "data_strategy": "MOCK",
        "critical_seam": True,
        "live_or_induced": None,
        "why_impossible_to_reproduce_live": "Cannot reproduce.",
        "technical_constraint": None,
    }
    v = falsify_mock(rec)
    assert v.outcome == "promote"
    assert "technical_constraint" in v.reason


# --- TC-3.1 (deterministic): naming a technique => promote -------------------

def test_tc3_1_naming_a_technique_promotes():
    rec = make_valid_tmr(
        data_strategy="MOCK",
        critical_seam=False,
        criticality_source="explicit",
        architecture_link=[],  # keep non-critical through classification
        live_or_induced={"kind": "tc-netem:partition"},
        why_impossible_to_reproduce_live=None,
        technical_constraint=None,
    )
    v = falsify_mock(rec)
    assert v.outcome == "promote"
    assert v.promote_to == "REAL-DATA"


# --- TC-3.2: critical seam + non-REAL + empty why_impossible => promote -------

def test_tc3_2_critical_non_real_empty_justification_promotes_not_just_mock():
    # SYNTHETIC (not literal MOCK) critical seam dodging the rule via relabel.
    rec = {
        "data_strategy": "SYNTHETIC",
        "critical_seam": True,
        "live_or_induced": None,
        "why_impossible_to_reproduce_live": "",
        "technical_constraint": None,
    }
    v = falsify_mock(rec)
    assert v.outcome == "promote"
    assert v.promote_to == "REAL-DATA"


# --- DD-3: scale/cost/time excuses are not impossibility => promote -----------

@pytest.mark.parametrize(
    "excuse",
    [
        "Would exhaust the rate limit.",
        "There are 2^31 items to enumerate.",
        "It is too slow to run live.",
        "Too expensive to provision the real service.",
        "Has 2³¹ entries; cannot enumerate.",
    ],
)
def test_excuse_constraints_promote(excuse):
    assert is_excuse_constraint(excuse) is True
    rec = make_valid_tmr(
        data_strategy="MOCK",
        critical_seam=True,
        live_or_induced=None,
        why_impossible_to_reproduce_live="Asserted impossible.",
        technical_constraint=excuse,
    )
    assert falsify_mock(rec).outcome == "promote"


def test_concrete_constraint_is_not_an_excuse():
    assert is_excuse_constraint("Requires NET_ADMIN unavailable in CI sandbox.") is False


# --- non-critical non-REAL non-MOCK is accepted ------------------------------

def test_non_critical_synthetic_is_justified():
    rec = {
        "data_strategy": "SYNTHETIC",
        "critical_seam": False,
        "live_or_induced": None,
        "why_impossible_to_reproduce_live": None,
        "technical_constraint": None,
    }
    assert isinstance(falsify_mock(rec), MockVerdict)
    assert falsify_mock(rec).outcome == "justified"
