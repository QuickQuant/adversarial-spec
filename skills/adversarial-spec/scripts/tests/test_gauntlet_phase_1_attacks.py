"""Regression tests for Phase 1 attack generation."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from adversaries import MINIMALIST
from gauntlet.core_types import GauntletConfig
from gauntlet.phase_1_attacks import generate_attacks


def test_generate_attacks_rejects_empty_adversary_list():
    """Phase 1 should hard-stop if the caller filtered out every adversary."""
    with pytest.raises(ValueError, match="At least one adversary is required"):
        generate_attacks(
            spec="spec",
            adversaries=[],
            models=["test-model"],
            config=GauntletConfig(),
        )


def test_generate_attacks_uses_prompt_override(monkeypatch):
    """Approved prompt text should override the static registry persona."""
    captured = {}

    def fake_call_model(model, system_prompt, user_message, timeout, codex_reasoning):  # noqa: ANN001
        captured["system_prompt"] = system_prompt
        return "1. Override concern", 10, 5

    monkeypatch.setattr("gauntlet.phase_1_attacks.call_model", fake_call_model)
    monkeypatch.setattr("gauntlet.phase_1_attacks.cost_tracker.add", lambda *args: None)

    concerns, timing, raw = generate_attacks(
        spec="spec",
        adversaries=["minimalist"],
        models=["test-model"],
        config=GauntletConfig(),
        prompts={"minimalist": "OVERRIDE PERSONA"},
    )

    assert "OVERRIDE PERSONA" in captured["system_prompt"]
    assert len(concerns) == 1
    assert timing
    assert raw


def test_generate_attacks_resolves_alias_before_static_fallback(monkeypatch):
    """Legacy adversary names should inherit the canonical persona fallback."""
    captured = {}

    def fake_call_model(model, system_prompt, user_message, timeout, codex_reasoning):  # noqa: ANN001
        captured["system_prompt"] = system_prompt
        return "1. Alias concern", 10, 5

    monkeypatch.setattr("gauntlet.phase_1_attacks.call_model", fake_call_model)
    monkeypatch.setattr("gauntlet.phase_1_attacks.cost_tracker.add", lambda *args: None)

    concerns, _, _ = generate_attacks(
        spec="spec",
        adversaries=["lazy_developer"],
        models=["test-model"],
        config=GauntletConfig(),
    )

    assert MINIMALIST.persona in captured["system_prompt"]
    assert len(concerns) == 1
