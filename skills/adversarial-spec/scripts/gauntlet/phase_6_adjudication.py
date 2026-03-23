"""Phase 6: Final Adjudication.

Extracted from gauntlet_monolith.py — final decisions on challenged
dismissals.
"""

from __future__ import annotations

import json
import sys

from gauntlet.core_types import PROGRAMMING_BUGS, Concern, GauntletConfig, Rebuttal
from gauntlet.model_dispatch import call_model
from models import cost_tracker


def final_adjudication(
    spec: str,
    rebuttals: list[Rebuttal],
    model: str,
    config: GauntletConfig,
) -> list[Concern]:
    """Phase 6: Final adjudication of challenged dismissals.

    Args:
        spec: The original specification
        rebuttals: Rebuttals that were sustained (challenged)
        model: Frontier model for final decision
        config: Gauntlet configuration (timeout)

    Returns:
        List of concerns that survived (need spec revision)
    """
    challenged = [r for r in rebuttals if r.sustained]
    if not challenged:
        return []

    challenges_text = "\n\n".join(
        f"### Challenge {i+1} (from {r.evaluation.concern.adversary})\n"
        f"Original concern: {r.evaluation.concern.text}\n"
        f"Dismissal reasoning: {r.evaluation.reasoning}\n"
        f"Rebuttal: {r.response}"
        for i, r in enumerate(challenged)
    )

    system_prompt = """You are making final decisions on challenged dismissals.

For each challenge, decide:
- UPHELD: The original dismissal was correct despite the challenge
- OVERTURNED: The challenge reveals a valid concern that needs addressing

Be rigorous. If the adversary raised a valid logical point, overturn the dismissal.

Output as JSON:
{
  "decisions": [
    {"challenge_index": 0, "verdict": "upheld|overturned", "reasoning": "..."},
    ...
  ]
}"""

    user_message = f"""## SPECIFICATION
{spec}

## CHALLENGED DISMISSALS
{challenges_text}

Make your final decisions. Output valid JSON."""

    try:
        response, in_tokens, out_tokens = call_model(
            model=model,
            system_prompt=system_prompt,
            user_message=user_message,
            timeout=config.timeout,
            codex_reasoning=config.eval_codex_reasoning,
        )
        cost_tracker.add(model, in_tokens, out_tokens)

        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            data = json.loads(json_str)

            surviving = []
            for decision in data.get("decisions", []):
                idx = decision.get("challenge_index", 0)
                if idx < len(challenged) and decision.get("verdict") == "overturned":
                    surviving.append(challenged[idx].evaluation.concern)
            return surviving

    except Exception as e:
        if isinstance(e, PROGRAMMING_BUGS):
            raise
        print(f"Warning: Final adjudication failed: {e}", file=sys.stderr)

    # Conservative fallback: all challenged concerns survive
    return [r.evaluation.concern for r in challenged]
