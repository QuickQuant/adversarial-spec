"""Phase 4: Structured Evaluation.

Extracted from gauntlet_monolith.py — single-model and multi-model
concern evaluation with consensus algorithm.
"""

from __future__ import annotations

import concurrent.futures
import json
import sys
import time

from adversaries import ADVERSARIES
from gauntlet.core_types import PROGRAMMING_BUGS, Concern, Evaluation, GauntletConfig
from gauntlet.model_dispatch import (
    call_model,
    get_rate_limit_config,
)
from gauntlet.prompts import EVALUATION_SYSTEM_PROMPT
from models import cost_tracker


def evaluate_concerns(
    spec: str,
    concerns: list[Concern],
    model: str,
    config: GauntletConfig,
) -> list[Evaluation]:
    """Phase 4: Evaluate each concern using the frontier model.

    Args:
        spec: The original specification
        concerns: List of concerns to evaluate
        model: Frontier model for evaluation
        config: Gauntlet configuration (timeout)

    Returns:
        List of Evaluation objects
    """
    if not concerns:
        return []

    concerns_text = "\n\n".join(
        f"### Concern {i+1} (from {c.adversary})\n{c.text}"
        for i, c in enumerate(concerns)
    )

    protocols_text = ""
    for adv_key in set(c.adversary for c in concerns):
        adversary = ADVERSARIES.get(adv_key)
        if adversary:
            protocols_text += f"\n### When evaluating {adv_key}:\n"
            protocols_text += f"Valid dismissal: {adversary.valid_dismissal}\n"
            protocols_text += f"Invalid dismissal: {adversary.invalid_dismissal}\n"
            protocols_text += f"Rule: {adversary.rule}\n"
        else:
            protocols_text += f"\n### When evaluating {adv_key}:\n"
            protocols_text += "Valid dismissal: Use your judgment\n"
            protocols_text += "Invalid dismissal: Be careful of handwaving\n"
            protocols_text += "Rule: Be rigorous\n"

    system_prompt = EVALUATION_SYSTEM_PROMPT.format(protocols_text=protocols_text)

    user_message = f"""## SPECIFICATION
{spec}

## CONCERNS TO EVALUATE
{concerns_text}

Evaluate each concern according to the response protocols. Output valid JSON."""

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

            evaluations = []
            for eval_data in data.get("evaluations", []):
                idx = eval_data.get("concern_index", 0)
                if idx < len(concerns):
                    severity = eval_data.get("severity", "")
                    if severity not in ("high", "medium", "low"):
                        severity = ""
                    evaluations.append(
                        Evaluation(
                            concern=concerns[idx],
                            verdict=eval_data.get("verdict", "deferred"),
                            reasoning=eval_data.get("reasoning", ""),
                            severity=severity,
                        )
                    )
            return evaluations

    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse evaluation JSON: {e}", file=sys.stderr)
    except Exception as e:
        if isinstance(e, PROGRAMMING_BUGS):
            raise
        print(f"Warning: Evaluation failed: {e}", file=sys.stderr)

    # Fallback: defer all concerns
    return [
        Evaluation(concern=c, verdict="deferred", reasoning="Evaluation failed")
        for c in concerns
    ]


def evaluate_concerns_multi_model(
    spec: str,
    concerns: list[Concern],
    models: list[str],
    config: GauntletConfig,
    batch_size: int = 15,
) -> list[Evaluation]:
    """Phase 4: Evaluate concerns using MULTIPLE models in parallel.

    Runs all batches for each model concurrently (respecting per-provider rate limits),
    and runs different models in parallel with each other.

    Args:
        spec: The specification
        concerns: List of concerns to evaluate
        models: List of models to use (will use up to 3)
        config: Gauntlet configuration (timeout)
        batch_size: Number of concerns per batch

    Returns:
        List of Evaluation objects with consensus verdicts
    """
    if not concerns:
        return []

    eval_models = models[:3] if len(models) >= 3 else models

    if len(eval_models) < 2:
        print(f"  Warning: Only {len(eval_models)} model(s) available, using single-model eval", file=sys.stderr)
        return evaluate_concerns(spec, concerns, eval_models[0], config)

    print(f"  Using {len(eval_models)} models: {', '.join(eval_models)}", file=sys.stderr)

    batches = [concerns[i:i + batch_size] for i in range(0, len(concerns), batch_size)]
    print(f"  Processing {len(concerns)} concerns in {len(batches)} batches", file=sys.stderr)

    def run_all_batches_for_model(model: str) -> dict[int, list[Evaluation]]:
        """Run all batches for a single model, respecting its rate limit.

        Launches waves with staggered delays but does NOT wait for a wave
        to finish before launching the next. All batches run concurrently
        within a single executor — the delay is only between submission
        moments, not between completions.
        """
        rate_batch_size, rate_delay = get_rate_limit_config(model)
        results: dict[int, list[Evaluation]] = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(batches)) as executor:
            future_to_idx = {}

            for wave_start in range(0, len(batches), rate_batch_size):
                wave_end = min(wave_start + rate_batch_size, len(batches))
                wave_batches = list(range(wave_start, wave_end))

                if wave_start > 0:
                    print(
                        f"  {model}: rate limit pause {rate_delay}s before wave "
                        f"{wave_start // rate_batch_size + 1}...",
                        file=sys.stderr,
                    )
                    time.sleep(rate_delay)

                for batch_idx in wave_batches:
                    future = executor.submit(
                        evaluate_concerns, spec, batches[batch_idx], model, config
                    )
                    future_to_idx[future] = batch_idx

            # Collect all results after all waves launched
            for future in concurrent.futures.as_completed(future_to_idx):
                batch_idx = future_to_idx[future]
                try:
                    evals = future.result()
                    results[batch_idx] = evals
                    print(
                        f"  {model}: batch {batch_idx + 1}/{len(batches)} done "
                        f"({len(evals)} evals)",
                        file=sys.stderr,
                    )
                except Exception as e:
                    if isinstance(e, PROGRAMMING_BUGS):
                        raise
                    print(
                        f"  Warning: {model} batch {batch_idx + 1} failed: {e}",
                        file=sys.stderr,
                    )
                    results[batch_idx] = []

        return results

    model_all_results: dict[str, dict[int, list[Evaluation]]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(eval_models)) as model_executor:
        model_futures = {
            model_executor.submit(run_all_batches_for_model, m): m
            for m in eval_models
        }
        for future in concurrent.futures.as_completed(model_futures):
            model = model_futures[future]
            try:
                model_all_results[model] = future.result()
                total_evals = sum(len(v) for v in model_all_results[model].values())
                print(f"  {model}: all batches complete ({total_evals} evals)", file=sys.stderr)
            except Exception as e:
                if isinstance(e, PROGRAMMING_BUGS):
                    raise
                print(f"  Warning: {model} failed entirely: {e}", file=sys.stderr)
                model_all_results[model] = {}

    # Build consensus across models for each concern
    all_evaluations: list[Evaluation] = []
    disagreements = 0

    for batch_idx, batch in enumerate(batches):
        for i, concern in enumerate(batch):
            verdicts = {}
            reasonings = {}
            severities = {}

            for model in eval_models:
                batch_results = model_all_results.get(model, {}).get(batch_idx, [])
                if i < len(batch_results):
                    eval_item = batch_results[i]
                    verdicts[model] = eval_item.verdict
                    reasonings[model] = eval_item.reasoning
                    if eval_item.severity in ("high", "medium", "low"):
                        severities[model] = eval_item.severity

            verdict_counts = {}
            for v in verdicts.values():
                verdict_counts[v] = verdict_counts.get(v, 0) + 1

            if verdict_counts:
                max_count = max(verdict_counts.values())
                winners = [v for v, c in verdict_counts.items() if c == max_count]

                if len(winners) == 1:
                    consensus_verdict = winners[0]
                else:
                    if "accepted" in winners:
                        consensus_verdict = "accepted"
                    elif "deferred" in winners:
                        consensus_verdict = "deferred"
                    else:
                        consensus_verdict = "dismissed"

                if len(set(verdicts.values())) > 1:
                    disagreements += 1

                # Severity consensus: take the highest (most conservative)
                severity_order = {"high": 3, "medium": 2, "low": 1}
                consensus_severity = ""
                if severities:
                    consensus_severity = max(
                        severities.values(),
                        key=lambda s: severity_order.get(s, 0),
                    )

                combined_reasoning = f"[Consensus: {dict(verdict_counts)}] "
                combined_reasoning += reasonings.get(eval_models[0], "")

                all_evaluations.append(Evaluation(
                    concern=concern,
                    verdict=consensus_verdict,
                    reasoning=combined_reasoning,
                    severity=consensus_severity,
                ))

    if disagreements > 0:
        print(f"  Model disagreements: {disagreements}/{len(concerns)}", file=sys.stderr)

    return all_evaluations
