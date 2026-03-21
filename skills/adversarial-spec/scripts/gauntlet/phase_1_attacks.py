"""Phase 1: Attack Generation.

Extracted from gauntlet_monolith.py — parallel adversary attack dispatch
with rate-limited batching per provider.
"""

from __future__ import annotations

import concurrent.futures
import sys
import time
from collections import defaultdict

from adversaries import ADVERSARIES
from gauntlet.core_types import Concern, GauntletConfig
from gauntlet.model_dispatch import (
    _get_model_provider,
    call_model,
    get_rate_limit_config,
)
from models import cost_tracker


def generate_attacks(
    spec: str,
    adversaries: list[str],
    models: list[str] | str,
    config: GauntletConfig,
) -> tuple[list[Concern], dict[str, float], dict[str, str]]:
    """Phase 1: Generate attacks from all adversary personas in parallel.

    Args:
        spec: The specification to attack
        adversaries: List of adversary keys to use
        models: Model(s) to use for attack generation
        config: Gauntlet configuration (timeout, attack_codex_reasoning)

    Returns:
        Tuple of (concerns, timing_dict, raw_responses_dict)
    """
    if isinstance(models, str):
        models = [models]
    models = [m.strip() for m in models if m and m.strip()]
    if not models:
        raise ValueError("At least one attack model is required")

    concerns: list[Concern] = []
    timing: dict[str, float] = {}
    raw_responses: dict[str, str] = {}

    def run_adversary_with_model(adversary_key: str, model: str) -> tuple[list[Concern], float, str]:
        """Run one adversary with one model and return concerns with timing."""
        start = time.time()
        adversary = ADVERSARIES.get(adversary_key)
        if not adversary:
            print(f"Warning: Unknown adversary '{adversary_key}'", file=sys.stderr)
            return [], 0.0, ""

        system_prompt = f"""You are an adversarial reviewer with this persona:

{adversary.persona}

Your job is to find problems with the specification below. Be aggressive.
Output a numbered list of concerns. Each concern should be a potential problem
you've identified. Don't hold back - even if you're not 100% sure, raise it."""

        user_message = f"""Review this specification and identify all potential problems:

{spec}

Output your concerns as a numbered list. Be specific and cite parts of the spec."""

        try:
            response, in_tokens, out_tokens = call_model(
                model=model,
                system_prompt=system_prompt,
                user_message=user_message,
                timeout=config.timeout,
                codex_reasoning=config.attack_codex_reasoning,
            )
            cost_tracker.add(model, in_tokens, out_tokens)

            # Parse concerns from response - group numbered items with their sub-bullets
            local_concerns = []
            current_concern_lines: list[str] = []
            seen_texts: set[str] = set()

            def flush_concern():
                """Flush accumulated lines as a single concern."""
                if current_concern_lines:
                    full_text = " ".join(current_concern_lines)
                    if full_text and full_text not in seen_texts:
                        seen_texts.add(full_text)
                        local_concerns.append(
                            Concern(
                                adversary=adversary_key,
                                text=full_text,
                                source_model=model,
                            )
                        )
                    current_concern_lines.clear()

            for line in response.split("\n"):
                line = line.strip()
                if not line:
                    continue

                is_numbered = line and line[0].isdigit() and (
                    ". " in line[:4] or ")" in line[:4]
                )

                if is_numbered:
                    flush_concern()
                    text = line.lstrip("0123456789.-) ").strip()
                    if text:
                        current_concern_lines.append(text)
                elif line.startswith(("-", "•", "*")):
                    text = line.lstrip("-•* ").strip()
                    if text and current_concern_lines:
                        current_concern_lines.append(text)
                elif current_concern_lines:
                    current_concern_lines.append(line)

            flush_concern()

            for c in local_concerns:
                if len(c.text) < 80 and ("quote" in c.text.lower() or c.text.startswith('"')):
                    print(
                        f"Warning: Concern from {adversary_key} looks like a bare quote "
                        f"(possible parse issue): {c.text[:60]}...",
                        file=sys.stderr,
                    )

            elapsed = time.time() - start
            return local_concerns, elapsed, response

        except Exception as e:
            print(
                f"Warning: Adversary {adversary_key} failed: {e}",
                file=sys.stderr,
            )
            return [], time.time() - start, ""

    # Run adversary/model pairs in batches, respecting provider rate limits.
    pairs = [(adv, model) for adv in adversaries for model in models]

    by_provider: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for adv, model in pairs:
        by_provider[_get_model_provider(model)].append((adv, model))

    def collect_result(future, adv_key, model):
        adv_concerns, elapsed, raw_response = future.result()
        concerns.extend(adv_concerns)
        timing[f"{adv_key}@{model}"] = elapsed
        if raw_response:
            raw_responses[f"{adv_key}@{model}"] = raw_response

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, len(pairs) or 1)) as executor:
        for provider, provider_pairs in by_provider.items():
            batch_size, batch_delay = get_rate_limit_config(provider_pairs[0][1])

            for batch_idx in range(0, len(provider_pairs), batch_size):
                batch = provider_pairs[batch_idx:batch_idx + batch_size]
                if batch_idx > 0:
                    print(
                        f"  Rate limit pause: {batch_delay}s before {provider} batch "
                        f"{batch_idx // batch_size + 1}/{(len(provider_pairs) + batch_size - 1) // batch_size}...",
                        file=sys.stderr,
                    )
                    time.sleep(batch_delay)

                batch_futures = {
                    executor.submit(run_adversary_with_model, adv, model): (adv, model)
                    for adv, model in batch
                }
                for future in concurrent.futures.as_completed(batch_futures):
                    adv_key, model = batch_futures[future]
                    collect_result(future, adv_key, model)

    if timing:
        sorted_timing = sorted(timing.items(), key=lambda x: x[1], reverse=True)
        print("  Adversary timing (adversary@model):", file=sys.stderr)
        for adv_model, elapsed in sorted_timing:
            if "@" in adv_model:
                adv, model = adv_model.split("@", 1)
            else:
                adv, model = adv_model, ""
            count = len(
                [
                    c for c in concerns
                    if c.adversary == adv and (not model or c.source_model == model)
                ]
            )
            print(f"    {adv_model}: {elapsed:.1f}s ({count} concerns)", file=sys.stderr)

    return concerns, timing, raw_responses
