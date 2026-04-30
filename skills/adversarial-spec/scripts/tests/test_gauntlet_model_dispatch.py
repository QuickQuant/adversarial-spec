"""Contract tests for gauntlet model dispatch helpers."""

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parent.parent / "gauntlet" / "model_dispatch.py"
SPEC = importlib.util.spec_from_file_location("test_gauntlet_model_dispatch", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
_validate_model_name = MODULE._validate_model_name
select_eval_model = MODULE.select_eval_model
get_available_eval_models = MODULE.get_available_eval_models
call_model = MODULE.call_model


def test_validate_model_name_accepts_expected_values():
    _validate_model_name("codex/gpt-5.5")
    _validate_model_name("claude-opus-4-7")
    _validate_model_name("gemini-cli/gemini-3.1-pro-preview")
    _validate_model_name("gemini/gemini-3-flash")
    _validate_model_name("deepseek/deepseek-v4")


@pytest.mark.parametrize(
    "model_name",
    [
        "",
        "model; rm -rf /",
        "model | cat /etc/passwd",
        "gpt 4",
        "model name with spaces",
        "-oops",
        "--oops",
        "--flag-injection",
        "gpt--help",
        "model$(command)",
        "model\ninjection",
    ],
)
def test_validate_model_name_rejects_forbidden_patterns(model_name: str):
    with pytest.raises(ValueError):
        _validate_model_name(model_name)


def test_select_eval_model_prefers_codex_gpt_5_5(monkeypatch):
    monkeypatch.setattr(MODULE, "CODEX_AVAILABLE", True)
    monkeypatch.setattr(MODULE, "GEMINI_CLI_AVAILABLE", True)
    monkeypatch.delenv("ADVERSARIAL_SPEC_UNAVAILABLE_MODELS", raising=False)

    assert select_eval_model() == "codex/gpt-5.5"


def test_select_eval_model_warns_before_falling_back_to_gpt_5_3(monkeypatch, capsys):
    monkeypatch.setattr(MODULE, "CODEX_AVAILABLE", True)
    monkeypatch.setattr(MODULE, "GEMINI_CLI_AVAILABLE", True)
    monkeypatch.setenv("ADVERSARIAL_SPEC_UNAVAILABLE_MODELS", "codex/gpt-5.5")

    assert select_eval_model() == "codex/gpt-5.3-codex"
    assert "codex/gpt-5.5 unavailable" in capsys.readouterr().err


def test_get_available_eval_models_prefers_codex_gpt_5_5(monkeypatch):
    monkeypatch.setattr(MODULE, "CODEX_AVAILABLE", True)
    monkeypatch.setattr(MODULE, "GEMINI_CLI_AVAILABLE", True)
    monkeypatch.delenv("ADVERSARIAL_SPEC_UNAVAILABLE_MODELS", raising=False)

    assert get_available_eval_models()[:2] == [
        "codex/gpt-5.5",
        "gemini-cli/gemini-3.1-pro-preview",
    ]


@pytest.mark.parametrize(
    ("model_name", "handler_name"),
    [
        ("codex/gpt-5.5", "call_codex_model"),
        ("gemini-cli/gemini-3.1-pro-preview", "call_gemini_cli_model"),
        ("claude-cli/claude-opus-4-7", "call_claude_cli_model"),
    ],
)
def test_call_model_records_cli_usage_once(monkeypatch, model_name: str, handler_name: str):
    calls = []

    class Tracker:
        def record_call(self, model, input_tokens, output_tokens):  # noqa: ANN001
            calls.append((model, input_tokens, output_tokens))
            return 0.0

    def fake_handler(**kwargs):  # noqa: ANN001
        assert kwargs["model"] == model_name
        return "ok", 11, 7

    monkeypatch.setattr(MODULE, handler_name, fake_handler)
    monkeypatch.setattr(MODULE.token_tracking, "tracker", Tracker())

    assert call_model(model_name, "system", "user") == ("ok", 11, 7)
    assert calls == [(model_name, 11, 7)]


def test_call_model_records_litellm_usage_once(monkeypatch):
    calls = []

    class Tracker:
        def record_call(self, model, input_tokens, output_tokens):  # noqa: ANN001
            calls.append((model, input_tokens, output_tokens))
            return 0.0

    class Usage:
        prompt_tokens = 13
        completion_tokens = 5

    class Message:
        content = "ok"

    class Choice:
        message = Message()

    class Response:
        choices = [Choice()]
        usage = Usage()

    monkeypatch.setattr(MODULE, "completion", lambda **kwargs: Response())
    monkeypatch.setattr(MODULE.token_tracking, "tracker", Tracker())

    assert call_model("gpt-4o", "system", "user") == ("ok", 13, 5)
    assert calls == [("gpt-4o", 13, 5)]
