"""Phase 5: Adversary Rebuttals.

Extracted from gauntlet_monolith.py — dismissed concern rebuttals
with rate-limited batching.
"""

from __future__ import annotations

import concurrent.futures
import sys
from typing import Optional

from adversaries import ADVERSARIES
from gauntlet.core_types import Evaluation, GauntletConfig, Rebuttal
from gauntlet.model_dispatch import call_model, get_rate_limit_config
from models import cost_tracker

# =============================================================================
# PROMPT
# =============================================================================

REBUTTAL_PROMPT = """The frontier model dismissed your concern with this reasoning:

{dismissal_reasoning}

Evaluate this dismissal. You have two options:

OPTION A - ACCEPT DISMISSAL:
If the dismissal is logically sound, respond with:
"ACCEPTED: [brief acknowledgment that the reasoning is valid]"

OPTION B - CHALLENGE DISMISSAL:
If the dismissal is NOT logically sound, respond with:
"CHALLENGED: [specific counter-evidence or logical flaw]"

RULES:
1. No emotional language ("that's unfair", "they're ignoring me")
2. No appeals to authority ("but I'm the security expert")
3. Only logic and evidence
4. If their reasoning is actually valid, accept it gracefully
5. If you have new evidence, present it clearly
"""


def run_rebuttals(
    evaluations: list[Evaluation],
    model: str,
    config: GauntletConfig,
) -> list[Rebuttal]:
    """Phase 5: Allow adversaries to rebut dismissals.

    Args:
        evaluations: List of evaluations (only dismissed ones get rebuttals)
        model: Model for adversary rebuttals
        config: Gauntlet configuration (timeout)

    Returns:
        List of Rebuttal objects
    """
    dismissed = [e for e in evaluations if e.verdict == "dismissed"]
    if not dismissed:
        return []

    rebuttals: list[Rebuttal] = []

    def run_rebuttal(evaluation: Evaluation) -> Optional[Rebuttal]:
        adversary_key = evaluation.concern.adversary
        adversary = ADVERSARIES.get(adversary_key)
        persona = adversary.persona if adversary else ""

        system_prompt = f"""You are an adversarial reviewer with this persona:

{persona}

You raised a concern that was dismissed. Evaluate the dismissal LOGICALLY.

{REBUTTAL_PROMPT}"""

        user_message = f"""Your original concern:
{evaluation.concern.text}

The dismissal reasoning:
{evaluation.reasoning}

Evaluate this dismissal. Output either:
ACCEPTED: [brief acknowledgment] if the reasoning is valid
CHALLENGED: [counter-evidence or logical flaw] if the reasoning is flawed"""

        try:
            response, in_tokens, out_tokens = call_model(
                model=model,
                system_prompt=system_prompt,
                user_message=user_message,
                timeout=config.timeout,
                codex_reasoning=config.attack_codex_reasoning,
            )
            cost_tracker.add(model, in_tokens, out_tokens)

            response_upper = response.upper()
            sustained = "CHALLENGED:" in response_upper

            return Rebuttal(
                evaluation=evaluation,
                response=response.strip(),
                sustained=sustained,
            )

        except Exception as e:
            print(f"Warning: Rebuttal failed for {adversary_key}: {e}", file=sys.stderr)
            return None

    # Run rebuttals in batches to avoid rate limits
    batch_size, batch_delay = get_rate_limit_config(model)

    for i in range(0, len(dismissed), batch_size):
        batch = dismissed[i:i + batch_size]
        if i > 0:
            print(f"    Batch {i // batch_size + 1}/{(len(dismissed) + batch_size - 1) // batch_size}...", file=sys.stderr)
            import time
            time.sleep(batch_delay)
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(batch)) as executor:
            futures = [executor.submit(run_rebuttal, e) for e in batch]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    rebuttals.append(result)

    return rebuttals
