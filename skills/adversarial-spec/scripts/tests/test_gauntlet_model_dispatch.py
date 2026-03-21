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
