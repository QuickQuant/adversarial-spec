"""Phase 2: Big Picture Synthesis.

Extracted from gauntlet_monolith.py — holistic concern analysis before
evaluation. Uses call_model() for unified model dispatch.
"""

from __future__ import annotations

import sys

from gauntlet.core_types import (
    PROGRAMMING_BUGS,
    BigPictureSynthesis,
    Concern,
    GauntletConfig,
)
from gauntlet.model_dispatch import call_model
from gauntlet.prompts import BIG_PICTURE_PROMPT, SYNTHESIS_SYSTEM_PROMPT
from models import cost_tracker


def generate_big_picture_synthesis(
    concerns: list[Concern],
    model: str,
    config: GauntletConfig,
) -> BigPictureSynthesis:
    """Generate a holistic analysis of all concerns before evaluation.

    Synthesizes insights by looking at the full picture:
    - What are the real issues across all concerns?
    - Hidden connections between different adversaries' concerns
    - What's missing - blind spots no one caught
    - The meta-concern that ties everything together
    """
    by_adversary: dict[str, list[str]] = {}
    for c in concerns:
        if c.adversary not in by_adversary:
            by_adversary[c.adversary] = []
        by_adversary[c.adversary].append(c.text)

    concerns_text = ""
    for adv, texts in sorted(by_adversary.items()):
        concerns_text += f"\n### {adv} ({len(texts)} concerns)\n"
        for i, t in enumerate(texts, 1):
            concerns_text += f"{i}. {t}\n"

    prompt = BIG_PICTURE_PROMPT.format(concerns_by_adversary=concerns_text)

    try:
        response, in_tokens, out_tokens = call_model(
            model=model,
            system_prompt=SYNTHESIS_SYSTEM_PROMPT,
            user_message=prompt,
            timeout=config.timeout,
            codex_reasoning=config.attack_codex_reasoning,
        )
        cost_tracker.add(model, in_tokens, out_tokens)

        def extract_list(marker: str) -> list[str]:
            items = []
            if marker in response:
                start = response.find(marker) + len(marker)
                next_markers = ["REAL_ISSUES", "HIDDEN_CONNECTIONS", "WHATS_MISSING",
                               "META_CONCERN", "HIGH_SIGNAL"]
                end = len(response)
                for m in next_markers:
                    if m in response[start:]:
                        pos = response.find(m, start)
                        if pos < end and pos > start:
                            end = pos
                section = response[start:end]
                for line in section.split("\n"):
                    line = line.strip()
                    if line.startswith(("-", "•", "*")):
                        items.append(line.lstrip("-•* ").strip())
            return items

        def extract_single(marker: str) -> str:
            if marker in response:
                start = response.find(marker) + len(marker)
                end = response.find("\n", start)
                if end == -1:
                    end = len(response)
                return response[start:end].strip()
            return ""

        real_issues = extract_list("REAL_ISSUES:")
        hidden_connections = extract_list("HIDDEN_CONNECTIONS:")
        whats_missing = extract_list("WHATS_MISSING:")
        meta_concern = extract_single("META_CONCERN:")
        high_signal = extract_list("HIGH_SIGNAL:")

        unique_count = len(set(c.text for c in concerns))

        return BigPictureSynthesis(
            total_concerns=len(concerns),
            unique_texts=unique_count,
            real_issues=real_issues,
            hidden_connections=hidden_connections,
            whats_missing=whats_missing,
            meta_concern=meta_concern,
            high_signal=high_signal,
            raw_response=response,
        )

    except Exception as e:
        if isinstance(e, PROGRAMMING_BUGS):
            raise
        print(f"Warning: Big picture synthesis failed: {e}", file=sys.stderr)
        return BigPictureSynthesis(
            total_concerns=len(concerns),
            unique_texts=len(set(c.text for c in concerns)),
            real_issues=[],
            hidden_connections=[],
            whats_missing=[],
            meta_concern=f"Synthesis failed: {e}",
            high_signal=[],
            raw_response="",
        )
