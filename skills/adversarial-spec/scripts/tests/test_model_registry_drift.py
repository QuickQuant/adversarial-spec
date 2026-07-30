"""Tripwire for drift from the Fizzy model-role registry."""

from models import ANTIGRAVITY_MODEL_MAP
from providers import (
    ANTIGRAVITY_GEMINI_36_FLASH_HIGH,
    GEMINI_36_FLASH_HIGH,
    GEMINI_CLI_36_FLASH_HIGH,
    GPT_56_LUNA,
    GPT_56_SOL,
    GPT_56_TERRA,
    MODEL_COSTS,
)

# Keystone-lite mirror of:
# fizzy-pipeline-mcp/src/fizzy_pipeline_mcp/model_invocation.py::_STATIC_ROUTING
CANONICAL_ROLE_MODELS = {
    "codex.max_intelligence": "gpt-5.6-sol",
    "codex.single_issue": "gpt-5.6-terra",
    "codex.gauntlet_adversary": "gpt-5.6-luna",
    "codex.default": "gpt-5.6-luna",
    "gemini.single_issue": "gemini-3.6-flash-high",
    "gemini.exploration": "gemini-3.6-flash-high",
    "gemini.gauntlet_adversary": "gemini-3.6-flash-high",
    "gemini.default": "gemini-3.6-flash-high",
}


def _token(prefixed_model: str) -> str:
    return prefixed_model.split("/", 1)[-1]


def test_live_model_constants_match_fizzy_registry():
    live_role_models = {
        "codex.max_intelligence": _token(GPT_56_SOL),
        "codex.single_issue": _token(GPT_56_TERRA),
        "codex.gauntlet_adversary": _token(GPT_56_LUNA),
        "codex.default": _token(GPT_56_LUNA),
        "gemini.single_issue": GEMINI_36_FLASH_HIGH,
        "gemini.exploration": GEMINI_36_FLASH_HIGH,
        "gemini.gauntlet_adversary": GEMINI_36_FLASH_HIGH,
        "gemini.default": GEMINI_36_FLASH_HIGH,
    }

    assert live_role_models == CANONICAL_ROLE_MODELS
    assert GEMINI_CLI_36_FLASH_HIGH == f"gemini-cli/{GEMINI_36_FLASH_HIGH}"
    assert (
        ANTIGRAVITY_GEMINI_36_FLASH_HIGH
        == f"antigravity/{GEMINI_36_FLASH_HIGH}"
    )
    assert GEMINI_36_FLASH_HIGH in ANTIGRAVITY_MODEL_MAP
    assert GEMINI_CLI_36_FLASH_HIGH in MODEL_COSTS
    assert ANTIGRAVITY_GEMINI_36_FLASH_HIGH in MODEL_COSTS
