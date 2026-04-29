"""Phase 3: Filtering and Provenance Expansion.

Explanation matching pre-filter and dedup stats. Clustering was bypassed
in orchestrator.py (CR-8) and removed in CON-004.
"""

from __future__ import annotations

import concurrent.futures
import json
import re
import sys
from typing import Optional

from gauntlet.core_types import (
    PROGRAMMING_BUGS,
    Concern,
    Evaluation,
    ExplanationMatch,
    GauntletConfig,
)
from gauntlet.model_dispatch import call_model
from gauntlet.persistence import (
    CONFIDENCE_ACCEPT_THRESHOLD,
    CONFIDENCE_NOTE_THRESHOLD,
    calculate_explanation_confidence,
    load_resolved_concerns,
    record_explanation_match,
)
from gauntlet.prompts import EXPLANATION_MATCHING_PROMPT

# =============================================================================
# EXPLANATION MATCHING (Phase 3.5 pre-filter)
# =============================================================================


def find_matching_explanation(
    concern_text: str,
    adversary: str,
    model: str,
    current_spec_hash: Optional[str],
    config: GauntletConfig,
) -> Optional[ExplanationMatch]:
    """Check if a concern matches any resolved explanation.

    Uses a cheap model to compare concern text against resolved patterns.

    Returns:
        ExplanationMatch with action: "accept", "note", "ignore", or None
    """
    resolved = load_resolved_concerns()
    if not resolved["concerns"]:
        return None

    relevant = [
        c for c in resolved["concerns"]
        if c.get("adversary") == adversary or c.get("adversary") == "general"
    ]

    if not relevant:
        return None

    confidence_info = {}
    for i, c in enumerate(relevant):
        conf, reason = calculate_explanation_confidence(c, current_spec_hash)
        confidence_info[i] = (conf, reason)

    relevant_with_conf = [
        (i, c) for i, c in enumerate(relevant)
        if confidence_info[i][0] >= CONFIDENCE_NOTE_THRESHOLD * 0.5
    ]

    if not relevant_with_conf:
        return None

    explanations_text = "\n".join(
        f"[{i}] Pattern: {c['pattern']}\n"
        f"    Explanation: {c['explanation']}\n"
        f"    Confidence: {confidence_info[i][0]:.0%} ({confidence_info[i][1]})"
        for i, c in relevant_with_conf
    )

    system_prompt = EXPLANATION_MATCHING_PROMPT

    user_prompt = f"""NEW CONCERN:
{concern_text}

EXISTING EXPLANATIONS:
{explanations_text}

Does any existing explanation FULLY address this concern?"""

    try:
        response, _, _ = call_model(
            model=model,
            system_prompt=system_prompt,
            user_message=user_prompt,
            timeout=config.timeout,
        )

        if "MATCH:" in response.upper():
            match = re.search(r"MATCH:\s*\[?(\d+)\]?", response.upper())
            if match:
                idx = int(match.group(1))
                for orig_idx, expl in relevant_with_conf:
                    if orig_idx == idx:
                        confidence, reason = confidence_info[idx]

                        if confidence >= CONFIDENCE_ACCEPT_THRESHOLD:
                            action = "accept"
                        elif confidence >= CONFIDENCE_NOTE_THRESHOLD:
                            action = "note"
                        else:
                            action = "ignore"

                        return ExplanationMatch(
                            explanation=expl,
                            confidence=confidence,
                            reason=reason,
                            action=action,
                        )

    except Exception as e:
        if isinstance(e, PROGRAMMING_BUGS):
            raise

    return None


def filter_concerns_with_explanations(
    concerns: list[Concern],
    model: str,
    spec_hash: Optional[str],
    config: GauntletConfig,
) -> tuple[list[Concern], list[Concern], list[tuple[Concern, ExplanationMatch]]]:
    """Filter concerns against resolved explanations database.

    Returns:
        (filtered_concerns, dropped_concerns, noted_concerns)
    """
    filtered = []
    dropped = []
    noted = []

    def check_concern(concern: Concern) -> tuple[Concern, Optional[ExplanationMatch]]:
        match = find_matching_explanation(
            concern.text,
            concern.adversary,
            model,
            spec_hash,
            config,
        )
        return concern, match

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(check_concern, c) for c in concerns]
        for future in concurrent.futures.as_completed(futures):
            concern, match = future.result()

            if match is None:
                filtered.append(concern)
            elif match.action == "accept":
                dropped.append(concern)
                record_explanation_match(match.explanation.get("id", ""))
            elif match.action == "note":
                noted.append((concern, match))
                filtered.append(concern)
            else:
                filtered.append(concern)

    return filtered, dropped, noted


def expand_clustered_evaluations(
    clustered_evaluations: list[Evaluation],
    cluster_members: dict[str, list[Concern]],
) -> list[Evaluation]:
    """Fan out each clustered evaluation back to all original members for attribution stats."""
    expanded: list[Evaluation] = []
    for evaluation in clustered_evaluations:
        members = cluster_members.get(evaluation.concern.id, [evaluation.concern])
        cluster_size = len(members)
        for member in members:
            reasoning = evaluation.reasoning
            if cluster_size > 1:
                reasoning = f"[Clustered from {cluster_size} similar concerns; representative={evaluation.concern.id}] {reasoning}"
            expanded.append(
                Evaluation(
                    concern=member,
                    verdict=evaluation.verdict,
                    reasoning=reasoning,
                )
            )
    return expanded


def _track_dedup_stats(
    spec_hash: str,
    raw_count: int,
    post_filter_count: int,
    post_cluster_count: int,
    cluster_deduped: int,
    reduction_pct: float,
    attack_models: list[str],
    clustering_model: str,
) -> None:
    """Persist dedup/clustering stats to a JSON log for tracking over time."""
    import datetime
    from pathlib import Path

    stats_file = Path(".adversarial-spec-gauntlet") / "dedup-stats.json"
    stats_file.parent.mkdir(exist_ok=True)

    existing: list = []
    if stats_file.exists():
        try:
            existing = json.loads(stats_file.read_text())
        except (json.JSONDecodeError, OSError):
            existing = []

    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "spec_hash": spec_hash[:8],
        "raw_concerns": raw_count,
        "post_filter": post_filter_count,
        "post_cluster": post_cluster_count,
        "cluster_deduped": cluster_deduped,
        "reduction_pct": round(reduction_pct, 1),
        "attack_models": attack_models,
        "clustering_model": clustering_model,
    }
    existing.append(entry)
    stats_file.write_text(json.dumps(existing, indent=2) + "\n")

    if len(existing) >= 2:
        avg_reduction = sum(e["reduction_pct"] for e in existing) / len(existing)
        print(
            f"  Dedup history: {len(existing)} runs, avg {avg_reduction:.0f}% reduction",
            file=sys.stderr,
        )
