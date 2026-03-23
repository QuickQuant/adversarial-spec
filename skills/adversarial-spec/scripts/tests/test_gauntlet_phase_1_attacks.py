"""Regression tests for Phase 1 attack generation."""

import json

import pytest
from adversaries import MINIMALIST
from gauntlet.core_types import Concern, GauntletConfig
from gauntlet.phase_1_attacks import _parse_json_concerns, generate_attacks


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

    def fake_call_model(model, system_prompt, user_message, timeout, codex_reasoning, json_mode=False):  # noqa: ANN001
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

    def fake_call_model(model, system_prompt, user_message, timeout, codex_reasoning, json_mode=False):  # noqa: ANN001
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


# =============================================================================
# T8: Parse failure detection and quality gate
# =============================================================================


def test_parse_detects_numbered_list(monkeypatch):
    """Backward compat: standard numbered list parses correctly."""
    response = """1. Missing error handling for network failures
2. No timeout configuration for API calls
3. Authentication tokens are not rotated"""

    def fake_call_model(model, system_prompt, user_message, timeout, codex_reasoning, json_mode=False):
        return response, 100, 50

    monkeypatch.setattr("gauntlet.phase_1_attacks.call_model", fake_call_model)
    monkeypatch.setattr("gauntlet.phase_1_attacks.cost_tracker.add", lambda *a: None)

    concerns, _, _ = generate_attacks(
        spec="spec", adversaries=["paranoid_security"],
        models=["test-model"], config=GauntletConfig(),
    )
    assert len(concerns) == 3


def test_parse_detects_gemini_header_format(monkeypatch):
    """Gemini outputs ### N. Title headers — should still parse."""
    response = """### 1. Missing rate limiting
The API has no rate limiting which could lead to abuse.

### 2. No input validation
User inputs are not sanitized before processing."""

    def fake_call_model(model, system_prompt, user_message, timeout, codex_reasoning, json_mode=False):
        return response, 100, 50

    monkeypatch.setattr("gauntlet.phase_1_attacks.call_model", fake_call_model)
    monkeypatch.setattr("gauntlet.phase_1_attacks.cost_tracker.add", lambda *a: None)

    concerns, _, _ = generate_attacks(
        spec="spec", adversaries=["paranoid_security"],
        models=["test-model"], config=GauntletConfig(),
    )
    assert len(concerns) >= 2


def test_parse_failure_detection_nonempty_response_zero_concerns(monkeypatch):
    """Non-empty response + 0 parsed concerns → parse_failures populated."""
    # Prose-only response that doesn't match any numbered pattern
    response = """This specification has several issues that need attention.
The authentication mechanism is poorly defined and the error
handling strategy is missing entirely from the document."""

    def fake_call_model(model, system_prompt, user_message, timeout, codex_reasoning, json_mode=False):
        return response, 100, 50

    monkeypatch.setattr("gauntlet.phase_1_attacks.call_model", fake_call_model)
    monkeypatch.setattr("gauntlet.phase_1_attacks.cost_tracker.add", lambda *a: None)

    concerns, timing, raw = generate_attacks(
        spec="spec", adversaries=["paranoid_security"],
        models=["test-model"], config=GauntletConfig(),
    )
    # The raw response should still be captured even if 0 concerns parsed
    assert "paranoid_security@test-model" in raw
    assert raw["paranoid_security@test-model"] == response


def test_quality_gate_flags_parse_failures(monkeypatch):
    """Quality gate: check_phase1_quality detects adversary×model with 0 concerns."""
    from gauntlet.phase_1_attacks import check_phase1_quality

    concerns = [
        Concern(adversary="paranoid_security", text="concern 1", source_model="model-a"),
        Concern(adversary="paranoid_security", text="concern 2", source_model="model-a"),
    ]
    raw_responses = {
        "paranoid_security@model-a": "1. concern 1\n2. concern 2",
        "burned_oncall@model-a": "This spec is missing retry logic and the error handling...",
    }

    failures = check_phase1_quality(concerns, raw_responses)
    assert len(failures) == 1
    assert failures[0]["adversary"] == "burned_oncall"
    assert failures[0]["model"] == "model-a"
    assert failures[0]["response_length"] > 0


def test_quality_gate_no_failures_when_all_produce_concerns(monkeypatch):
    """Quality gate: all pairs produced concerns → empty failures list."""
    from gauntlet.phase_1_attacks import check_phase1_quality

    concerns = [
        Concern(adversary="paranoid_security", text="c1", source_model="model-a"),
        Concern(adversary="burned_oncall", text="c2", source_model="model-a"),
    ]
    raw_responses = {
        "paranoid_security@model-a": "1. c1",
        "burned_oncall@model-a": "1. c2",
    }

    failures = check_phase1_quality(concerns, raw_responses)
    assert failures == []


def test_quality_gate_ignores_empty_responses():
    """Empty response = model error, not parse failure (different error class)."""
    from gauntlet.phase_1_attacks import check_phase1_quality

    concerns = []
    raw_responses = {
        "paranoid_security@model-a": "",  # Empty = model error, not parse failure
        "burned_oncall@model-a": "Some non-empty response here",
    }

    failures = check_phase1_quality(concerns, raw_responses)
    # Only burned_oncall is a parse failure (non-empty + 0 concerns)
    assert len(failures) == 1
    assert failures[0]["adversary"] == "burned_oncall"


# =============================================================================
# T8: JSON parsing and fallback chain
# =============================================================================


class TestJsonParsing:
    """Tests for structured JSON concern parsing."""

    def test_parses_valid_json_concerns(self):
        """Valid JSON with concerns array → list of Concern objects."""
        response = json.dumps({
            "concerns": [
                {"text": "Missing error handling for API calls", "severity": "high"},
                {"text": "No rate limiting configured", "severity": "medium"},
            ]
        })
        result = _parse_json_concerns(response, "paranoid_security", "test-model")
        assert result is not None
        assert len(result) == 2
        assert result[0].text == "Missing error handling for API calls"
        assert result[0].severity == "high"
        assert result[0].adversary == "paranoid_security"
        assert result[0].source_model == "test-model"
        assert result[1].severity == "medium"

    def test_returns_none_for_non_json(self):
        """Non-JSON response → None (triggers regex fallback)."""
        result = _parse_json_concerns(
            "1. Missing error handling\n2. No rate limiting",
            "paranoid_security", "test-model",
        )
        assert result is None

    def test_returns_none_for_empty_concerns(self):
        """JSON with empty concerns array → None (triggers fallback)."""
        result = _parse_json_concerns(
            json.dumps({"concerns": []}),
            "paranoid_security", "test-model",
        )
        assert result is None

    def test_deduplicates_json_concerns(self):
        """Duplicate text in JSON → deduplicated."""
        response = json.dumps({
            "concerns": [
                {"text": "Same concern", "severity": "high"},
                {"text": "Same concern", "severity": "medium"},
            ]
        })
        result = _parse_json_concerns(response, "para", "m")
        assert result is not None
        assert len(result) == 1

    def test_normalizes_invalid_severity(self):
        """Unknown severity → defaults to medium."""
        response = json.dumps({
            "concerns": [{"text": "A concern", "severity": "critical"}]
        })
        result = _parse_json_concerns(response, "para", "m")
        assert result is not None
        assert result[0].severity == "medium"

    def test_skips_items_without_text(self):
        """Items missing text field → skipped."""
        response = json.dumps({
            "concerns": [
                {"severity": "high"},
                {"text": "Valid concern", "severity": "low"},
                {"text": "", "severity": "medium"},
            ]
        })
        result = _parse_json_concerns(response, "para", "m")
        assert result is not None
        assert len(result) == 1
        assert result[0].text == "Valid concern"


class TestJsonFallbackChain:
    """Tests for JSON-first with regex fallback in generate_attacks."""

    def test_json_response_parsed_as_json(self, monkeypatch):
        """Model returns JSON → parsed via JSON path, not regex."""
        json_response = json.dumps({
            "concerns": [
                {"text": "Missing auth", "severity": "high"},
                {"text": "No retries", "severity": "medium"},
            ]
        })

        def fake_call_model(model, system_prompt, user_message, timeout, codex_reasoning, json_mode=False):
            return json_response, 100, 50

        monkeypatch.setattr("gauntlet.phase_1_attacks.call_model", fake_call_model)
        monkeypatch.setattr("gauntlet.phase_1_attacks.cost_tracker.add", lambda *a: None)

        concerns, _, raw = generate_attacks(
            spec="spec", adversaries=["paranoid_security"],
            models=["test-model"], config=GauntletConfig(),
        )
        assert len(concerns) == 2
        assert concerns[0].severity == "high"

    def test_numbered_list_falls_back_to_regex(self, monkeypatch):
        """Model ignores JSON request, returns numbered list → regex fallback."""
        response = "1. Missing error handling\n2. No timeout configuration"

        def fake_call_model(model, system_prompt, user_message, timeout, codex_reasoning, json_mode=False):
            return response, 100, 50

        monkeypatch.setattr("gauntlet.phase_1_attacks.call_model", fake_call_model)
        monkeypatch.setattr("gauntlet.phase_1_attacks.cost_tracker.add", lambda *a: None)

        concerns, _, _ = generate_attacks(
            spec="spec", adversaries=["paranoid_security"],
            models=["test-model"], config=GauntletConfig(),
        )
        assert len(concerns) == 2

    def test_json_prompt_used(self, monkeypatch):
        """Attack prompt should request JSON output format."""
        captured = {}

        def fake_call_model(model, system_prompt, user_message, timeout, codex_reasoning, json_mode=False):
            captured["user_message"] = user_message
            captured["json_mode"] = json_mode
            return json.dumps({"concerns": [{"text": "c1", "severity": "low"}]}), 10, 5

        monkeypatch.setattr("gauntlet.phase_1_attacks.call_model", fake_call_model)
        monkeypatch.setattr("gauntlet.phase_1_attacks.cost_tracker.add", lambda *a: None)

        generate_attacks(
            spec="spec", adversaries=["paranoid_security"],
            models=["test-model"], config=GauntletConfig(),
        )
        assert "JSON" in captured["user_message"] or "json" in captured["user_message"]

    def test_cli_model_does_not_use_json_mode_flag(self, monkeypatch):
        """CLI models (codex/) should not pass json_mode=True."""
        captured = {}

        def fake_call_model(model, system_prompt, user_message, timeout, codex_reasoning, json_mode=False):
            captured["json_mode"] = json_mode
            return json.dumps({"concerns": [{"text": "c1", "severity": "low"}]}), 10, 5

        monkeypatch.setattr("gauntlet.phase_1_attacks.call_model", fake_call_model)
        monkeypatch.setattr("gauntlet.phase_1_attacks.cost_tracker.add", lambda *a: None)

        generate_attacks(
            spec="spec", adversaries=["paranoid_security"],
            models=["codex/gpt-5.4"], config=GauntletConfig(),
        )
        assert captured["json_mode"] is False

    def test_cli_model_uses_numbered_list_prompt(self, monkeypatch):
        """CLI models should get the numbered-list prompt, not JSON prompt."""
        captured = {}

        def fake_call_model(model, system_prompt, user_message, timeout, codex_reasoning, json_mode=False):
            captured["user_message"] = user_message
            return "1. Missing error handling\n2. No timeout", 10, 5

        monkeypatch.setattr("gauntlet.phase_1_attacks.call_model", fake_call_model)
        monkeypatch.setattr("gauntlet.phase_1_attacks.cost_tracker.add", lambda *a: None)

        for cli_model in ["codex/gpt-5.4", "gemini-cli/gemini-3-pro-preview", "claude-cli/opus"]:
            generate_attacks(
                spec="spec", adversaries=["paranoid_security"],
                models=[cli_model], config=GauntletConfig(),
            )
            assert "JSON" not in captured["user_message"], f"{cli_model} got JSON prompt"
            assert "numbered list" in captured["user_message"], f"{cli_model} missing numbered list instruction"

    def test_litellm_model_uses_json_mode_flag(self, monkeypatch):
        """LiteLLM-path models should pass json_mode=True."""
        captured = {}

        def fake_call_model(model, system_prompt, user_message, timeout, codex_reasoning, json_mode=False):
            captured["json_mode"] = json_mode
            return json.dumps({"concerns": [{"text": "c1", "severity": "low"}]}), 10, 5

        monkeypatch.setattr("gauntlet.phase_1_attacks.call_model", fake_call_model)
        monkeypatch.setattr("gauntlet.phase_1_attacks.cost_tracker.add", lambda *a: None)

        generate_attacks(
            spec="spec", adversaries=["paranoid_security"],
            models=["claude-opus-4-6"], config=GauntletConfig(),
        )
        assert captured["json_mode"] is True
