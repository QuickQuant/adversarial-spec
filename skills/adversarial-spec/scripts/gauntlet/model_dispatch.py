"""Model dispatch and selection for the gauntlet pipeline.

Extracted from gauntlet_monolith.py — model calling, selection, rate
limiting, and validation. No phase logic lives here.
"""

from __future__ import annotations

import re
import sys
from typing import Optional

from models import (
    call_claude_cli_model,
    call_codex_model,
    call_gemini_cli_model,
)
from providers import (
    CODEX_AVAILABLE,
    DEFAULT_CODEX_REASONING,
    GEMINI_CLI_AVAILABLE,
)

try:
    from litellm import completion
except ImportError:
    print(
        "Error: litellm package not installed. Run: pip install litellm",
        file=sys.stderr,
    )
    sys.exit(1)


# =============================================================================
# MODEL NAME VALIDATION
# =============================================================================

# Blocklist patterns for model name injection prevention
_MODEL_NAME_BLOCKLIST = re.compile(r'[;|&$`\s]|[\x00-\x1f]|--|^-')


def _validate_model_name(model: str) -> None:
    """Validate model name against injection attacks.

    Rejects: shell metacharacters (;|&$`), spaces, control chars,
    flag-like patterns (--, starts with -), empty strings.
    """
    if not model:
        raise ValueError("Model name cannot be empty")
    if _MODEL_NAME_BLOCKLIST.search(model):
        raise ValueError(
            f"Model name contains forbidden characters: {model!r}"
        )


# =============================================================================
# MODEL CALLING
# =============================================================================


def call_model(
    model: str,
    system_prompt: str,
    user_message: str,
    timeout: int = 1800,
    codex_reasoning: str = DEFAULT_CODEX_REASONING,
    json_mode: bool = False,
) -> tuple[str, int, int]:
    """Call a model (CLI or API) and return response with token counts.

    Args:
        json_mode: Request JSON output via response_format (litellm path only).
            CLI models (codex/, gemini-cli/, claude-cli/) ignore this flag —
            use prompt-driven JSON requests for those.

    Returns:
        (response_text, input_tokens, output_tokens)
    """
    _validate_model_name(model)

    if model.startswith("codex/"):
        return call_codex_model(
            system_prompt=system_prompt,
            user_message=user_message,
            model=model,
            reasoning_effort=codex_reasoning,
            timeout=timeout,
        )

    if model.startswith("gemini-cli/"):
        return call_gemini_cli_model(
            system_prompt=system_prompt,
            user_message=user_message,
            model=model,
            timeout=timeout,
        )

    if model.startswith("claude-cli/"):
        return call_claude_cli_model(
            system_prompt=system_prompt,
            user_message=user_message,
            model=model,
            timeout=timeout,
        )

    # Standard litellm path
    kwargs: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.7,
        "timeout": timeout,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = completion(**kwargs)
    content = response.choices[0].message.content
    input_tokens = response.usage.prompt_tokens if response.usage else 0
    output_tokens = response.usage.completion_tokens if response.usage else 0

    return content, input_tokens, output_tokens


# =============================================================================
# MODEL SELECTION (FREE-FIRST)
# =============================================================================

_PREFERRED_CODEX_EVAL_MODEL = "codex/gpt-5.4"
_FALLBACK_CODEX_EVAL_MODEL = "codex/gpt-5.3-codex"


def running_in_claude_code() -> bool:
    """Detect if we're running inside Claude Code environment."""
    import os

    return bool(
        os.environ.get("CLAUDE_CODE")
        or os.environ.get("CC_WORKSPACE")
        or os.environ.get("ANTHROPIC_API_KEY")
    )


def _get_unavailable_models() -> set[str]:
    """Return models explicitly marked unavailable for the current environment."""
    import os

    raw = os.environ.get("ADVERSARIAL_SPEC_UNAVAILABLE_MODELS", "")
    return {model.strip() for model in raw.split(",") if model.strip()}


def _select_codex_eval_model() -> str | None:
    """Select the best available Codex evaluation model."""
    if not CODEX_AVAILABLE:
        return None

    unavailable = _get_unavailable_models()
    if _PREFERRED_CODEX_EVAL_MODEL not in unavailable:
        return _PREFERRED_CODEX_EVAL_MODEL

    if _FALLBACK_CODEX_EVAL_MODEL not in unavailable:
        print(
            f"Warning: {_PREFERRED_CODEX_EVAL_MODEL} unavailable, "
            f"falling back to {_FALLBACK_CODEX_EVAL_MODEL}",
            file=sys.stderr,
        )
        return _FALLBACK_CODEX_EVAL_MODEL

    return None


def select_adversary_model() -> str:
    """Select model for adversary attacks (Phase 1 & 3).

    Priority: FREE first (Gemini CLI), then cheapest API.
    Adversaries don't need to be smart - they need to be aggressive.
    """
    if GEMINI_CLI_AVAILABLE:
        return "gemini-cli/gemini-3-flash-preview"

    import os

    if os.environ.get("GROQ_API_KEY"):
        return "groq/llama-3.3-70b-versatile"
    if os.environ.get("DEEPSEEK_API_KEY"):
        return "deepseek/deepseek-chat"
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini/gemini-3-flash"

    raise RuntimeError(
        "No model available for adversaries. Install Gemini CLI (free) or set an API key."
    )


def select_eval_model() -> str:
    """Select model for evaluation (Phase 4 & 6).

    Priority: FREE frontier CLI tools, then strongest API.
    Evaluation needs to be rigorous - use the best available.
    """
    codex_model = _select_codex_eval_model()
    if codex_model:
        return codex_model

    if GEMINI_CLI_AVAILABLE:
        return "gemini-cli/gemini-3.1-pro-preview"

    import os

    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude-sonnet-4-5-20250929"
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini/gemini-3-pro"

    raise RuntimeError(
        "No model available for evaluation. Install Codex CLI (free) or set an API key."
    )


def select_gauntlet_models(
    adversary_override: Optional[str] = None,
    eval_override: Optional[str] = None,
) -> tuple[str, str]:
    """Select models for the gauntlet.

    Returns:
        (adversary_model, eval_model) tuple
    """
    adversary = adversary_override or select_adversary_model()
    eval_model = eval_override or select_eval_model()
    return adversary, eval_model


def get_available_eval_models() -> list[str]:
    """Get list of available evaluation models (prioritize free).

    Returns up to 3 models for multi-model consensus evaluation.
    Prefers free CLI tools over paid APIs.
    """
    import os

    models = []

    codex_model = _select_codex_eval_model()
    if codex_model:
        models.append(codex_model)
    if GEMINI_CLI_AVAILABLE:
        models.append("gemini-cli/gemini-3.1-pro-preview")

    if len(models) < 2:
        if os.environ.get("ANTHROPIC_API_KEY"):
            models.append("claude-sonnet-4-5-20250929")
        if len(models) < 2 and os.environ.get("GEMINI_API_KEY"):
            models.append("gemini/gemini-3-pro")

    return models


# =============================================================================
# RATE LIMITING
# =============================================================================


def get_rate_limit_config(model_name: str) -> tuple[int, int]:
    """Return (batch_size, delay_seconds) for the given model.

    Rate limits vary by provider:
      Gemini: 5-15 RPM (free), 150+ RPM (paid) - set GEMINI_PAID_TIER=true
      Claude: 50 RPM (Tier 1), 2000+ (Tier 3+) - set CLAUDE_PAID_TIER=true
      Codex: message quotas, generally generous
    """
    import os

    model_lower = model_name.lower()
    if "gemini" in model_lower:
        paid = os.environ.get("GEMINI_PAID_TIER", "").lower() == "true"
        return (10, 2) if paid else (3, 15)
    elif "claude" in model_lower or "anthropic" in model_lower:
        paid = os.environ.get("CLAUDE_PAID_TIER", "").lower() == "true"
        return (20, 1) if paid else (5, 5)
    elif "codex" in model_lower or "gpt" in model_lower or "openai" in model_lower:
        return (10, 2)
    else:
        return (3, 10)


def _get_model_provider(model: str) -> str:
    """Extract provider key from model name for rate limit grouping."""
    for prefix in ("codex/", "gemini-cli/", "gemini/", "claude-cli/", "claude-",
                    "xai/", "mistral/", "groq/", "deepseek/", "zhipu/", "gpt-"):
        if model.startswith(prefix):
            return prefix.rstrip("/-")
    return model
