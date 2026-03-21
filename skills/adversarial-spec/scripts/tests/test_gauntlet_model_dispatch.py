"""Contract tests for gauntlet model dispatch helpers."""

import importlib.util
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

MODULE_PATH = Path(__file__).parent.parent / "gauntlet" / "model_dispatch.py"
SPEC = importlib.util.spec_from_file_location("test_gauntlet_model_dispatch", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
_validate_model_name = MODULE._validate_model_name
select_eval_model = MODULE.select_eval_model
get_available_eval_models = MODULE.get_available_eval_models


def test_validate_model_name_accepts_expected_values():
    _validate_model_name("codex/gpt-5.4")
    _validate_model_name("claude-opus-4-6")
    _validate_model_name("gemini-cli/gemini-3-pro-preview")
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


def test_select_eval_model_prefers_codex_gpt_5_4(monkeypatch):
    monkeypatch.setattr(MODULE, "CODEX_AVAILABLE", True)
    monkeypatch.setattr(MODULE, "GEMINI_CLI_AVAILABLE", True)
    monkeypatch.delenv("ADVERSARIAL_SPEC_UNAVAILABLE_MODELS", raising=False)

    assert select_eval_model() == "codex/gpt-5.4"


def test_select_eval_model_warns_before_falling_back_to_gpt_5_3(monkeypatch, capsys):
    monkeypatch.setattr(MODULE, "CODEX_AVAILABLE", True)
    monkeypatch.setattr(MODULE, "GEMINI_CLI_AVAILABLE", True)
    monkeypatch.setenv("ADVERSARIAL_SPEC_UNAVAILABLE_MODELS", "codex/gpt-5.4")

    assert select_eval_model() == "codex/gpt-5.3-codex"
    assert "codex/gpt-5.4 unavailable" in capsys.readouterr().err


def test_get_available_eval_models_prefers_codex_gpt_5_4(monkeypatch):
    monkeypatch.setattr(MODULE, "CODEX_AVAILABLE", True)
    monkeypatch.setattr(MODULE, "GEMINI_CLI_AVAILABLE", True)
    monkeypatch.delenv("ADVERSARIAL_SPEC_UNAVAILABLE_MODELS", raising=False)

    assert get_available_eval_models()[:2] == [
        "codex/gpt-5.4",
        "gemini-cli/gemini-3-pro-preview",
    ]
