"""Phase 1: Attack Generation.

Extracted from gauntlet_monolith.py — parallel adversary attack dispatch
with rate-limited batching per provider.
"""

from __future__ import annotations

import concurrent.futures
import json
import sys
import time
from collections import defaultdict

from adversaries import ADVERSARIES, resolve_adversary_name
from gauntlet.core_types import PROGRAMMING_BUGS, Concern, GauntletConfig
from gauntlet.model_dispatch import (
    _get_model_provider,
    call_model,
    get_rate_limit_config,
)
from gauntlet.prompts import (
    ATTACK_SYSTEM_PROMPT,
    ATTACK_USER_PROMPT,
    ATTACK_USER_PROMPT_JSON,
)
from models import cost_tracker


def _parse_json_concerns(
    response: str, adversary_key: str, model: str,
) -> list[Concern] | None:
    """Try to parse concerns from a JSON response.

    Returns list of Concern objects on success, None if response isn't valid JSON
    or doesn't match the expected schema.
    """
    try:
        data = json.loads(response)
    except (json.JSONDecodeError, ValueError):
        return None

    if not isinstance(data, dict):
        return None

    concerns_list = data.get("concerns")
    if not isinstance(concerns_list, list):
        return None

    parsed: list[Concern] = []
    seen_texts: set[str] = set()
    for item in concerns_list:
        if not isinstance(item, dict):
            continue
        text = item.get("text", "")
        if not isinstance(text, str) or not text.strip():
            continue
        text = text.strip()
        if text in seen_texts:
            continue
        seen_texts.add(text)
        severity = item.get("severity", "medium")
        if severity not in ("high", "medium", "low"):
            severity = "medium"
        parsed.append(Concern(
            adversary=adversary_key,
            text=text,
            severity=severity,
            source_model=model,
        ))

    return parsed if parsed else None


def generate_attacks(
    spec: str,
    adversaries: list[str],
    models: list[str] | str,
    config: GauntletConfig,
    prompts: dict[str, str] | None = None,
) -> tuple[list[Concern], dict[str, float], dict[str, str]]:
    """Phase 1: Generate attacks from all adversary personas in parallel.

    Args:
        spec: The specification to attack
        adversaries: List of adversary keys to use
        models: Model(s) to use for attack generation
        config: Gauntlet configuration (timeout, attack_codex_reasoning)
        prompts: Optional persona overrides keyed by adversary name

    Returns:
        Tuple of (concerns, timing_dict, raw_responses_dict)
    """
    if not adversaries:
        raise ValueError("At least one adversary is required")

    if isinstance(models, str):
        models = [models]
    models = [m.strip() for m in models if m and m.strip()]
    if not models:
        raise ValueError("At least one attack model is required")

    concerns: list[Concern] = []
    timing: dict[str, float] = {}
    raw_responses: dict[str, str] = {}

    def _parse_numbered_list(
        response: str, adversary_key: str, model: str,
    ) -> list[Concern]:
        """Parse concerns from a numbered-list response (regex fallback)."""
        local_concerns: list[Concern] = []
        current_concern_lines: list[str] = []
        seen_texts: set[str] = set()

        def flush_concern() -> None:
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

            is_numbered = False
            if line[0].isdigit() and (". " in line[:4] or ")" in line[:4]):
                is_numbered = True
            elif line.startswith("#"):
                stripped_hashes = line.lstrip("# ")
                if stripped_hashes and stripped_hashes[0].isdigit() and (
                    ". " in stripped_hashes[:4] or ")" in stripped_hashes[:4]
                ):
                    is_numbered = True

            if is_numbered:
                flush_concern()
                text = line.lstrip("#").lstrip(" ").lstrip("0123456789.-) ").strip()
                if text:
                    current_concern_lines.append(text)
            elif line.startswith(("-", "•", "*")):
                text = line.lstrip("-•* ").strip()
                if text and current_concern_lines:
                    current_concern_lines.append(text)
            elif current_concern_lines:
                current_concern_lines.append(line)

        flush_concern()
        return local_concerns

    def run_adversary_with_model(adversary_key: str, model: str) -> tuple[list[Concern], float, str]:
        """Run one adversary with one model and return concerns with timing.

        Uses JSON prompt for all models. Parses response as JSON first;
        falls back to numbered-list regex if JSON parsing fails.
        """
        start = time.time()
        canonical_key = resolve_adversary_name(adversary_key)
        adversary = ADVERSARIES.get(canonical_key)
        if not adversary:
            print(f"Warning: Unknown adversary '{adversary_key}'", file=sys.stderr)
            return [], 0.0, ""

        persona = adversary.persona
        if prompts:
            persona = (
                prompts.get(adversary_key)
                or prompts.get(canonical_key)
                or adversary.persona
            )

        system_prompt = ATTACK_SYSTEM_PROMPT.format(persona=persona)

        # CLI models (codex/, gemini-cli/, claude-cli/) can't enforce json_mode,
        # so use the numbered-list prompt for them to avoid unparseable output.
        is_cli_model = any(
            model.startswith(p) for p in ("codex/", "gemini-cli/", "claude-cli/")
        )
        prompt_template = ATTACK_USER_PROMPT if is_cli_model else ATTACK_USER_PROMPT_JSON
        user_message = prompt_template.format(spec=spec)

        try:
            response, in_tokens, out_tokens = call_model(
                model=model,
                system_prompt=system_prompt,
                user_message=user_message,
                timeout=config.timeout,
                codex_reasoning=config.attack_codex_reasoning,
                json_mode=not is_cli_model,
            )
            cost_tracker.add(model, in_tokens, out_tokens)

            # Try JSON parsing first, fall back to numbered-list regex
            local_concerns = _parse_json_concerns(response, adversary_key, model)
            if local_concerns is not None:
                print(
                    f"    {adversary_key}@{model}: parsed {len(local_concerns)} concerns (json)",
                    file=sys.stderr,
                )
            else:
                local_concerns = _parse_numbered_list(response, adversary_key, model)
                if local_concerns:
                    print(
                        f"    {adversary_key}@{model}: parsed {len(local_concerns)} concerns (regex fallback)",
                        file=sys.stderr,
                    )

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
            if isinstance(e, PROGRAMMING_BUGS):
                raise
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
        all_futures: dict[concurrent.futures.Future, tuple[str, str]] = {}

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

                for adv, model in batch:
                    future = executor.submit(run_adversary_with_model, adv, model)
                    all_futures[future] = (adv, model)

        for future in concurrent.futures.as_completed(all_futures):
            adv_key, model = all_futures[future]
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


def check_phase1_quality(
    concerns: list[Concern],
    raw_responses: dict[str, str],
) -> list[dict[str, str | int]]:
    """Detect parse failures: adversary×model pairs with non-empty response but 0 concerns.

    Empty responses indicate model errors (different error class) and are excluded.

    Returns:
        List of failure dicts with keys: adversary, model, response_length.
    """
    # Build set of adversary×model pairs that produced at least one concern
    pairs_with_concerns: set[tuple[str, str]] = set()
    for c in concerns:
        pairs_with_concerns.add((c.adversary, c.source_model))

    failures: list[dict[str, str | int]] = []
    for key, response in raw_responses.items():
        if "@" not in key:
            continue
        adversary, model = key.split("@", 1)
        if not response.strip():
            continue  # Empty response = model error, not parse failure
        if (adversary, model) not in pairs_with_concerns:
            failures.append({
                "adversary": adversary,
                "model": model,
                "response_length": len(response),
            })

    return failures
