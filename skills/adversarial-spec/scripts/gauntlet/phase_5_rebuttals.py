"""Phase 5: Adversary Rebuttals.

Extracted from gauntlet_monolith.py — dismissed concern rebuttals
with rate-limited batching.
"""

from __future__ import annotations

import concurrent.futures
import sys
from typing import Optional

from adversaries import ADVERSARIES
from gauntlet.core_types import PROGRAMMING_BUGS, Evaluation, GauntletConfig, Rebuttal
from gauntlet.model_dispatch import call_model, get_rate_limit_config
from gauntlet.prompts import REBUTTAL_SYSTEM_TEMPLATE, REBUTTAL_USER_TEMPLATE


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

        system_prompt = REBUTTAL_SYSTEM_TEMPLATE.format(persona=persona)
        user_message = REBUTTAL_USER_TEMPLATE.format(
            concern_text=evaluation.concern.text,
            dismissal_reasoning=evaluation.reasoning,
        )

        try:
            response, in_tokens, out_tokens = call_model(
                model=model,
                system_prompt=system_prompt,
                user_message=user_message,
                timeout=config.timeout,
                codex_reasoning=config.attack_codex_reasoning,
            )
            response_upper = response.upper()
            sustained = "CHALLENGED:" in response_upper

            return Rebuttal(
                evaluation=evaluation,
                response=response.strip(),
                sustained=sustained,
            )

        except Exception as e:
            if isinstance(e, PROGRAMMING_BUGS):
                raise
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
