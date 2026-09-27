"""Tripwire for drift from the Fizzy model-role registry."""

from models import ANTIGRAVITY_MODEL_MAP
from providers import (
    ANTIGRAVITY_GEMINI_38_FLASH_HIGH,
    GEMINI_38_FLASH_HIGH,
    GPT_56_LUNA,
    GPT_56_SOL,
    GPT_56_TERRA,
    MODEL_COSTS,
)

# Keystone-lite mirror of:
# fizzy-pipeline-mcp/src/fizzy_pipeline_mcp/model_invocation.py::_STATIC_ROUTING
# Gemini roles: gemini-3.8-flash @ high (Jason U2 ruling, 2026-09-27).
CANONICAL_ROLE_MODELS = {
    "codex.max_intelligence": "gpt-5.6-sol",
    "codex.single_issue": "gpt-5.6-terra",
    "codex.gauntlet_adversary": "gpt-5.6-luna",
    "codex.default": "gpt-5.6-luna",
    "gemini.single_issue": "gemini-3.8-flash-high",
    "gemini.exploration": "gemini-3.8-flash-high",
    "gemini.gauntlet_adversary": "gemini-3.8-flash-high",
    "gemini.default": "gemini-3.8-flash-high",
}

RETIRED_GEMINI_TOKENS = ("gemini-3.6-flash-high", "gemini-3.7-flash-high")


def _token(prefixed_model: str) -> str:
    return prefixed_model.split("/", 1)[-1]


def test_live_model_constants_match_fizzy_registry():
    live_role_models = {
        "codex.max_intelligence": _token(GPT_56_SOL),
        "codex.single_issue": _token(GPT_56_TERRA),
        "codex.gauntlet_adversary": _token(GPT_56_LUNA),
        "codex.default": _token(GPT_56_LUNA),
        "gemini.single_issue": GEMINI_38_FLASH_HIGH,
        "gemini.exploration": GEMINI_38_FLASH_HIGH,
        "gemini.gauntlet_adversary": GEMINI_38_FLASH_HIGH,
        "gemini.default": GEMINI_38_FLASH_HIGH,
    }

    assert live_role_models == CANONICAL_ROLE_MODELS
    assert ANTIGRAVITY_GEMINI_38_FLASH_HIGH == f"antigravity/{GEMINI_38_FLASH_HIGH}"
    assert GEMINI_38_FLASH_HIGH in ANTIGRAVITY_MODEL_MAP
    assert ANTIGRAVITY_GEMINI_38_FLASH_HIGH in MODEL_COSTS


def test_retired_gemini_seats_are_not_dispatchable():
    for token in RETIRED_GEMINI_TOKENS:
        assert token not in ANTIGRAVITY_MODEL_MAP
        assert f"antigravity/{token}" not in MODEL_COSTS
        assert f"gemini-cli/{token}" not in MODEL_COSTS
