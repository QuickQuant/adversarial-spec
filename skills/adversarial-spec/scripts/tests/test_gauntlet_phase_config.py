"""Contract tests for phase config threading in extracted gauntlet modules."""

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from gauntlet.core_types import Concern, Evaluation, GauntletConfig, Rebuttal
from gauntlet.phase_2_synthesis import generate_big_picture_synthesis
from gauntlet.phase_3_filtering import (
    filter_concerns_with_explanations,
    find_matching_explanation,
)
from gauntlet.phase_4_evaluation import evaluate_concerns
from gauntlet.phase_5_rebuttals import run_rebuttals
from gauntlet.phase_6_adjudication import final_adjudication


def _concern() -> Concern:
    return Concern(adversary="paranoid_security", text="Test concern", id="PARA-1")


def test_phase_2_uses_attack_codex_reasoning(monkeypatch):
    """Phase 2 should forward attack reasoning to direct Codex dispatch."""
    captured = {}
    monkeypatch.setattr(
        "gauntlet.phase_2_synthesis.call_codex_model",
        lambda **kwargs: (captured.update(kwargs) or ("REAL_ISSUES:\n- x\nHIDDEN_CONNECTIONS:\nWHATS_MISSING:\nMETA_CONCERN: y\nHIGH_SIGNAL:\n- z", 0, 0)),
    )
    monkeypatch.setattr("gauntlet.phase_2_synthesis.cost_tracker.add", lambda *args, **kwargs: None)

    generate_big_picture_synthesis(
        [_concern()],
        "codex/gpt-5.4",
        GauntletConfig(timeout=123, attack_codex_reasoning="minimal"),
    )

    assert captured["reasoning_effort"] == "minimal"
    assert captured["timeout"] == 123


def test_phase_4_uses_eval_codex_reasoning(monkeypatch):
    """Phase 4 should forward eval reasoning into model dispatch."""
    captured = {}
    monkeypatch.setattr(
        "gauntlet.phase_4_evaluation.call_model",
        lambda **kwargs: (captured.update(kwargs) or ('{"evaluations": []}', 0, 0)),
    )
    monkeypatch.setattr("gauntlet.phase_4_evaluation.cost_tracker.add", lambda *args, **kwargs: None)

    evaluate_concerns(
        "spec",
        [_concern()],
        "codex/gpt-5.4",
        GauntletConfig(timeout=321, eval_codex_reasoning="medium"),
    )

    assert captured["codex_reasoning"] == "medium"
    assert captured["timeout"] == 321


def test_phase_5_uses_attack_codex_reasoning(monkeypatch):
    """Phase 5 rebuttals should reuse the attack reasoning setting."""
    captured = {}
    concern = _concern()
    evaluation = Evaluation(concern=concern, verdict="dismissed", reasoning="reason")

    monkeypatch.setattr(
        "gauntlet.phase_5_rebuttals.call_model",
        lambda **kwargs: (captured.update(kwargs) or ("ACCEPTED: valid", 0, 0)),
    )
    monkeypatch.setattr("gauntlet.phase_5_rebuttals.cost_tracker.add", lambda *args, **kwargs: None)

    run_rebuttals(
        [evaluation],
        "codex/gpt-5.4",
        GauntletConfig(timeout=222, attack_codex_reasoning="low"),
    )

    assert captured["codex_reasoning"] == "low"
    assert captured["timeout"] == 222


def test_phase_6_uses_eval_codex_reasoning(monkeypatch):
    """Phase 6 adjudication should reuse the eval reasoning setting."""
    captured = {}
    concern = _concern()
    evaluation = Evaluation(concern=concern, verdict="dismissed", reasoning="reason")
    rebuttal = Rebuttal(evaluation=evaluation, response="challenge", sustained=True)

    monkeypatch.setattr(
        "gauntlet.phase_6_adjudication.call_model",
        lambda **kwargs: (captured.update(kwargs) or ('{"decisions": []}', 0, 0)),
    )
    monkeypatch.setattr("gauntlet.phase_6_adjudication.cost_tracker.add", lambda *args, **kwargs: None)

    final_adjudication(
        "spec",
        [rebuttal],
        "codex/gpt-5.4",
        GauntletConfig(timeout=444, eval_codex_reasoning="high"),
    )

    assert captured["codex_reasoning"] == "high"
    assert captured["timeout"] == 444


def test_phase_3_filtering_requires_config():
    """Phase 3 helpers should no longer carry default timeout fallbacks."""
    find_sig = inspect.signature(find_matching_explanation)
    filter_sig = inspect.signature(filter_concerns_with_explanations)

    assert find_sig.parameters["config"].default is inspect._empty
    assert filter_sig.parameters["config"].default is inspect._empty
