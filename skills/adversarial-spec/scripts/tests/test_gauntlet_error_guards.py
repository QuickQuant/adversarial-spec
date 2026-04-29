"""Tests for CR-4: programming bug re-raise guards in gauntlet phases.

Verifies that _PROGRAMMING_BUGS (TypeError, NameError, etc.) propagate
through except-Exception blocks instead of being silently swallowed,
while operational errors (API failures, JSON parse errors) are still
caught with graceful fallbacks.
"""

import pytest
from gauntlet.core_types import PROGRAMMING_BUGS, Concern, GauntletConfig

# =============================================================================
# Phase 1: generate_attacks — adversary model call failure
# =============================================================================


class TestPhase1ErrorGuard:
    """phase_1_attacks.py:158 — except Exception in run_adversary_with_model."""

    def test_type_error_propagates(self, monkeypatch):
        """TypeError in model call must NOT be swallowed."""
        def raise_type_error(model, system_prompt, user_message, timeout, codex_reasoning, json_mode=False):
            raise TypeError("unexpected keyword argument 'foo'")

        monkeypatch.setattr("gauntlet.phase_1_attacks.call_model", raise_type_error)
        monkeypatch.setattr("gauntlet.phase_1_attacks.cost_tracker.add", lambda *a: None)

        from gauntlet.phase_1_attacks import generate_attacks

        with pytest.raises(TypeError, match="unexpected keyword argument"):
            generate_attacks(
                spec="spec",
                adversaries=["paranoid_security"],
                models=["test-model"],
                config=GauntletConfig(),
            )

    def test_runtime_error_caught_with_warning(self, monkeypatch, capsys):
        """Operational errors (like API failures) should be caught, not raised."""
        def raise_runtime(model, system_prompt, user_message, timeout, codex_reasoning, json_mode=False):
            raise RuntimeError("API rate limit exceeded")

        monkeypatch.setattr("gauntlet.phase_1_attacks.call_model", raise_runtime)
        monkeypatch.setattr("gauntlet.phase_1_attacks.cost_tracker.add", lambda *a: None)

        from gauntlet.phase_1_attacks import generate_attacks

        concerns, timing, raw = generate_attacks(
            spec="spec",
            adversaries=["paranoid_security"],
            models=["test-model"],
            config=GauntletConfig(),
        )
        assert concerns == []
        assert "Warning" in capsys.readouterr().err


# =============================================================================
# Phase 3: find_matching_explanation — the silent `except Exception: pass`
# =============================================================================


class TestPhase3ErrorGuard:
    """phase_3_filtering.py:139 — was `except Exception: pass`."""

    def test_attribute_error_propagates(self, monkeypatch):
        """AttributeError in explanation matching must NOT be silently passed."""
        from gauntlet.phase_3_filtering import find_matching_explanation

        # Monkeypatch call_model to raise an AttributeError (programming bug)
        def raise_attr_error(**kwargs):
            raise AttributeError("'NoneType' object has no attribute 'strip'")

        monkeypatch.setattr("gauntlet.phase_3_filtering.call_model", raise_attr_error)
        # Provide a fake resolved concerns DB so it reaches the call_model path
        monkeypatch.setattr(
            "gauntlet.phase_3_filtering.load_resolved_concerns",
            lambda: {"concerns": [{"adversary": "test", "pattern": "test", "explanation": "x", "spec_hash": "abc"}]},
        )

        with pytest.raises(AttributeError, match="NoneType"):
            find_matching_explanation("test concern", "test", "test-model", "abc", GauntletConfig())

    def test_value_error_caught_returns_none(self, monkeypatch):
        """ValueError from bad JSON parsing should be caught (not re-raised)."""
        from gauntlet.phase_3_filtering import find_matching_explanation

        def raise_value_error(**kwargs):
            raise ValueError("malformed response")

        monkeypatch.setattr("gauntlet.phase_3_filtering.call_model", raise_value_error)
        monkeypatch.setattr(
            "gauntlet.phase_3_filtering.load_resolved_concerns",
            lambda: {"concerns": [{"adversary": "test", "pattern": "test", "explanation": "x", "spec_hash": "abc"}]},
        )

        result = find_matching_explanation("test concern", "test", "test-model", "abc", GauntletConfig())
        assert result is None


# =============================================================================
# Phase 4: evaluate_concerns — multiple except blocks
# =============================================================================


class TestPhase4ErrorGuard:
    """phase_4_evaluation.py:128 — except Exception in evaluate_concerns."""

    def test_name_error_propagates(self, monkeypatch):
        """NameError in evaluation must NOT produce deferred fallback."""
        def raise_name_error(model, system_prompt, user_message, timeout, codex_reasoning):
            raise NameError("name 'undefined_var' is not defined")

        monkeypatch.setattr("gauntlet.phase_4_evaluation.call_model", raise_name_error)
        monkeypatch.setattr("gauntlet.phase_4_evaluation.cost_tracker.add", lambda *a: None)

        from gauntlet.phase_4_evaluation import evaluate_concerns

        concerns = [Concern(adversary="test", text="c1", source_model="m")]
        with pytest.raises(NameError, match="undefined_var"):
            evaluate_concerns("spec", concerns, "test-model", GauntletConfig())

    def test_connection_error_caught_defers(self, monkeypatch, capsys):
        """Network errors should be caught and produce deferred verdicts."""
        def raise_connection(model, system_prompt, user_message, timeout, codex_reasoning):
            raise ConnectionError("Connection refused")

        monkeypatch.setattr("gauntlet.phase_4_evaluation.call_model", raise_connection)
        monkeypatch.setattr("gauntlet.phase_4_evaluation.cost_tracker.add", lambda *a: None)

        from gauntlet.phase_4_evaluation import evaluate_concerns

        concerns = [Concern(adversary="test", text="c1", source_model="m")]
        result = evaluate_concerns("spec", concerns, "test-model", GauntletConfig())
        assert len(result) == 1
        assert result[0].verdict == "deferred"
        assert "Warning" in capsys.readouterr().err


# =============================================================================
# Phase 5: run_rebuttal — adversary rebuttal failure
# =============================================================================


class TestPhase5ErrorGuard:
    """phase_5_rebuttals.py:108 — except Exception in run_rebuttal."""

    def test_import_error_propagates(self, monkeypatch):
        """ImportError in rebuttal generation must NOT return None silently."""
        def raise_import(model, system_prompt, user_message, timeout, codex_reasoning):
            raise ImportError("No module named 'missing_dep'")

        monkeypatch.setattr("gauntlet.phase_5_rebuttals.call_model", raise_import)
        monkeypatch.setattr("gauntlet.phase_5_rebuttals.cost_tracker.add", lambda *a: None)

        from gauntlet.core_types import Evaluation
        from gauntlet.phase_5_rebuttals import run_rebuttals

        concern = Concern(adversary="test", text="c1", source_model="m")
        dismissed = [Evaluation(concern=concern, verdict="dismissed", reasoning="r")]

        with pytest.raises(ImportError, match="missing_dep"):
            run_rebuttals(dismissed, "test-model", GauntletConfig())

    def test_runtime_error_caught_returns_none(self, monkeypatch, capsys):
        """Operational errors should be caught, rebuttal skipped."""
        def raise_runtime(model, system_prompt, user_message, timeout, codex_reasoning):
            raise RuntimeError("Timeout")

        monkeypatch.setattr("gauntlet.phase_5_rebuttals.call_model", raise_runtime)
        monkeypatch.setattr("gauntlet.phase_5_rebuttals.cost_tracker.add", lambda *a: None)

        from gauntlet.core_types import Evaluation
        from gauntlet.phase_5_rebuttals import run_rebuttals

        concern = Concern(adversary="test", text="c1", source_model="m")
        dismissed = [Evaluation(concern=concern, verdict="dismissed", reasoning="r")]

        result = run_rebuttals(dismissed, "test-model", GauntletConfig())
        assert result == []  # None filtered out
        assert "Warning" in capsys.readouterr().err


# =============================================================================
# Phase 6: final_adjudication — adjudication failure
# =============================================================================


class TestPhase6ErrorGuard:
    """phase_6_adjudication.py:93 — except Exception in final_adjudication."""

    def test_syntax_error_propagates(self, monkeypatch):
        """SyntaxError must NOT trigger conservative fallback."""
        def raise_syntax(model, system_prompt, user_message, timeout, codex_reasoning):
            raise SyntaxError("invalid syntax")

        monkeypatch.setattr("gauntlet.phase_6_adjudication.call_model", raise_syntax)
        monkeypatch.setattr("gauntlet.phase_6_adjudication.cost_tracker.add", lambda *a: None)

        from gauntlet.core_types import Evaluation, Rebuttal
        from gauntlet.phase_6_adjudication import final_adjudication

        concern = Concern(adversary="test", text="c1", source_model="m")
        evaluation = Evaluation(concern=concern, verdict="dismissed", reasoning="r")
        challenged = [Rebuttal(evaluation=evaluation, response="CHALLENGED: reason", sustained=True)]

        with pytest.raises(SyntaxError):
            final_adjudication("spec", challenged, "test-model", GauntletConfig())

    def test_os_error_caught_returns_all_surviving(self, monkeypatch, capsys):
        """OSError should be caught, all challenged concerns survive."""
        def raise_os(model, system_prompt, user_message, timeout, codex_reasoning):
            raise OSError("disk full")

        monkeypatch.setattr("gauntlet.phase_6_adjudication.call_model", raise_os)
        monkeypatch.setattr("gauntlet.phase_6_adjudication.cost_tracker.add", lambda *a: None)

        from gauntlet.core_types import Evaluation, Rebuttal
        from gauntlet.phase_6_adjudication import final_adjudication

        concern = Concern(adversary="test", text="c1", source_model="m")
        evaluation = Evaluation(concern=concern, verdict="dismissed", reasoning="r")
        challenged = [Rebuttal(evaluation=evaluation, response="CHALLENGED: reason", sustained=True)]

        result = final_adjudication("spec", challenged, "test-model", GauntletConfig())
        assert len(result) == 1
        assert result[0] is concern
        assert "Warning" in capsys.readouterr().err


# =============================================================================
# PROGRAMMING_BUGS tuple coverage
# =============================================================================


class TestProgrammingBugsTuple:
    """Verify the tuple contains exactly the right exception types."""

    def test_contains_expected_types(self):
        expected = {TypeError, NameError, AttributeError, ImportError, SyntaxError, AssertionError}
        assert set(PROGRAMMING_BUGS) == expected

    def test_excludes_value_error(self):
        assert ValueError not in PROGRAMMING_BUGS

    def test_excludes_key_error(self):
        assert KeyError not in PROGRAMMING_BUGS

    def test_excludes_runtime_error(self):
        assert RuntimeError not in PROGRAMMING_BUGS
