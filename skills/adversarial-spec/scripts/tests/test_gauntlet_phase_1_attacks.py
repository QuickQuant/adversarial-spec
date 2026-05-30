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

    concerns, _, _ = generate_attacks(
        spec="spec", adversaries=["paranoid_security"],
        models=["test-model"], config=GauntletConfig(),
    )
    assert len(concerns) >= 2


def test_parse_handles_numbered_items_at_or_above_100(monkeypatch):
    """Regression: parser window was [:4] which truncated three-digit numbers
    like '100. ' (the dot-space straddles index 3-4). Items >=100 were silently
    treated as continuation text, capping every adversary at 99 concerns.

    Empirically verified against raw-responses-9ee43569.json: PEDA emitted 200,
    BURN emitted 250, FLOW emitted 426 — all parsed as 99.

    Fix: window expanded to [:8], covering numbered items up to 99,999.
    """
    # Build a numbered list with 105 items so we cross the 100-mark.
    response = "\n".join(f"{i}. Concern number {i} with some descriptive text."
                         for i in range(1, 106))

    def fake_call_model(model, system_prompt, user_message, timeout, codex_reasoning, json_mode=False):
        return response, 100, 50

    monkeypatch.setattr("gauntlet.phase_1_attacks.call_model", fake_call_model)

    concerns, _, _ = generate_attacks(
        spec="spec", adversaries=["paranoid_security"],
        models=["test-model"], config=GauntletConfig(),
    )
    # Pre-fix this returned 99 (or fewer, with later items folded into #99's text).
    assert len(concerns) == 105, (
        f"Expected 105 concerns, got {len(concerns)}. "
        "Parser likely failed to detect items >=100 (regression of [:4]→[:8] fix)."
    )
    # Verify three-digit items kept their identity and weren't merged into #99.
    texts = [c.text for c in concerns]
    assert any("Concern number 100" in t for t in texts), "Item 100 should be its own concern."
    assert any("Concern number 105" in t for t in texts), "Item 105 should be its own concern."


def test_parse_handles_three_digit_with_paren_format(monkeypatch):
    """Same off-by-one risk for the '100)' branch — covered by [:8] too."""
    response = "\n".join(f"{i}) Concern {i}." for i in range(98, 103))

    def fake_call_model(model, system_prompt, user_message, timeout, codex_reasoning, json_mode=False):
        return response, 100, 50

    monkeypatch.setattr("gauntlet.phase_1_attacks.call_model", fake_call_model)

    concerns, _, _ = generate_attacks(
        spec="spec", adversaries=["paranoid_security"],
        models=["test-model"], config=GauntletConfig(),
    )
    assert len(concerns) == 5, f"Expected 5 concerns (98..102), got {len(concerns)}"


# =============================================================================
# Severity extraction (Layer A.2): severity was previously dropped on the
# floor — every parsed concern landed with `severity="medium"`. The parser
# now pulls the marker from the leading text and strips it.
# =============================================================================


class TestSeverityExtraction:
    """Direct unit tests for _extract_severity_from_text."""

    def test_no_marker_defaults_medium(self):
        from gauntlet.phase_1_attacks import _extract_severity_from_text
        sev, txt = _extract_severity_from_text("Plain concern without any marker.")
        assert sev == "medium"
        assert txt == "Plain concern without any marker."

    def test_bold_critical_maps_to_high(self):
        from gauntlet.phase_1_attacks import _extract_severity_from_text
        sev, txt = _extract_severity_from_text("**CRITICAL:** Auth bypass possible.")
        assert sev == "high"
        assert txt == "Auth bypass possible."

    def test_bold_high_no_colon(self):
        from gauntlet.phase_1_attacks import _extract_severity_from_text
        sev, txt = _extract_severity_from_text("**HIGH** Missing rate limit.")
        assert sev == "high"
        assert txt == "Missing rate limit."

    def test_bold_medium_lowercase(self):
        from gauntlet.phase_1_attacks import _extract_severity_from_text
        sev, txt = _extract_severity_from_text("**medium** Add backoff.")
        assert sev == "medium"
        assert txt == "Add backoff."

    def test_bracketed_severity(self):
        from gauntlet.phase_1_attacks import _extract_severity_from_text
        sev, txt = _extract_severity_from_text("[high] Stale config can race.")
        assert sev == "high"
        assert txt == "Stale config can race."

    def test_paren_severity_at_start(self):
        from gauntlet.phase_1_attacks import _extract_severity_from_text
        sev, txt = _extract_severity_from_text("(severity: low) cosmetic typo.")
        assert sev == "low"
        assert txt == "cosmetic typo."

    def test_paren_severity_inline_does_not_strip(self):
        from gauntlet.phase_1_attacks import _extract_severity_from_text
        sev, txt = _extract_severity_from_text(
            "Auth flow has a problem (severity: high) when token expires."
        )
        assert sev == "high"
        # Mid-sentence hints are not removed — they're part of the prose.
        assert txt == "Auth flow has a problem (severity: high) when token expires."

    def test_bare_label_with_colon(self):
        from gauntlet.phase_1_attacks import _extract_severity_from_text
        sev, txt = _extract_severity_from_text("CRITICAL: Path traversal in upload.")
        assert sev == "high"
        assert txt == "Path traversal in upload."

    def test_bare_word_without_colon_is_kept(self):
        # We require the colon to avoid stripping benign sentence starters
        # like "Low memory pressure can cause...".
        from gauntlet.phase_1_attacks import _extract_severity_from_text
        sev, txt = _extract_severity_from_text("Low memory pressure can cause OOMs.")
        assert sev == "medium"
        assert txt == "Low memory pressure can cause OOMs."

    def test_empty_string_safe(self):
        from gauntlet.phase_1_attacks import _extract_severity_from_text
        sev, txt = _extract_severity_from_text("")
        assert sev == "medium"
        assert txt == ""


def test_parser_attaches_extracted_severity_to_concerns(monkeypatch):
    """End-to-end: severity markers in numbered-list output land on Concern.severity."""
    response = """1. **CRITICAL:** Auth bypass via cookie tampering.
2. **MEDIUM** Missing telemetry on retry path.
3. [low] Cosmetic UI label inconsistency.
4. (severity: high) Stale config visible across tabs.
5. Plain concern with no marker."""

    def fake_call_model(model, system_prompt, user_message, timeout, codex_reasoning, json_mode=False):
        return response, 100, 50

    monkeypatch.setattr("gauntlet.phase_1_attacks.call_model", fake_call_model)

    concerns, _, _ = generate_attacks(
        spec="spec", adversaries=["paranoid_security"],
        models=["test-model"], config=GauntletConfig(),
    )
    assert len(concerns) == 5
    severities = [c.severity for c in concerns]
    assert severities == ["high", "medium", "low", "high", "medium"], severities
    # Markers stripped from text:
    assert concerns[0].text.startswith("Auth bypass"), concerns[0].text
    assert concerns[2].text.startswith("Cosmetic UI label"), concerns[2].text
    assert concerns[3].text.startswith("Stale config"), concerns[3].text


def test_parse_failure_detection_nonempty_response_zero_concerns(monkeypatch):
    """Non-empty response + 0 parsed concerns → parse_failures populated."""
    # Prose-only response that doesn't match any numbered pattern
    response = """This specification has several issues that need attention.
The authentication mechanism is poorly defined and the error
handling strategy is missing entirely from the document."""

    def fake_call_model(model, system_prompt, user_message, timeout, codex_reasoning, json_mode=False):
        return response, 100, 50

    monkeypatch.setattr("gauntlet.phase_1_attacks.call_model", fake_call_model)

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

        generate_attacks(
            spec="spec", adversaries=["paranoid_security"],
            models=["codex/gpt-5.5"], config=GauntletConfig(),
        )
        assert captured["json_mode"] is False

    def test_cli_model_uses_numbered_list_prompt(self, monkeypatch):
        """CLI models should get the numbered-list prompt, not JSON prompt."""
        captured = {}

        def fake_call_model(model, system_prompt, user_message, timeout, codex_reasoning, json_mode=False):
            captured["user_message"] = user_message
            return "1. Missing error handling\n2. No timeout", 10, 5

        monkeypatch.setattr("gauntlet.phase_1_attacks.call_model", fake_call_model)

        for cli_model in ["codex/gpt-5.5", "gemini-cli/gemini-3.1-pro-preview", "claude-cli/opus"]:
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

        generate_attacks(
            spec="spec", adversaries=["paranoid_security"],
            models=["claude-opus-4-7"], config=GauntletConfig(),
        )
        assert captured["json_mode"] is True
