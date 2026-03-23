"""Phase 3: Filtering, Clustering, and Provenance Expansion.

Extracted from gauntlet_monolith.py — explanation matching, concern
clustering with provenance tracking, and dedup stats.

QUOTA BURN FIX 2: Silent catch-all in clustering replaced with
retry-once + GauntletClusteringError.
"""

from __future__ import annotations

import concurrent.futures
import json
import re
import sys
import time
from typing import Optional

from gauntlet.core_types import (
    PROGRAMMING_BUGS,
    Concern,
    Evaluation,
    ExplanationMatch,
    GauntletClusteringError,
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
from models import cost_tracker

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

    system_prompt = """You are checking if a concern has already been addressed.

Compare the NEW CONCERN against the EXISTING EXPLANATIONS.

STRICT MATCHING RULES:
1. Only match if the explanation DIRECTLY and COMPLETELY addresses the concern
2. Partial matches = NO_MATCH (the concern has aspects not covered)
3. Vague explanations = NO_MATCH (can't verify they apply)
4. Consider the confidence level shown - low confidence means be MORE skeptical

Output ONLY ONE of:
- "MATCH: [index]" - The explanation at [index] FULLY addresses this exact concern
- "NO_MATCH" - No explanation fully covers this concern"""

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


# =============================================================================
# CLUSTERING
# =============================================================================


def choose_clustering_model(attack_models: list[str], fallback: str) -> str:
    """Choose a cheap model for dedup clustering."""
    if not attack_models:
        return fallback

    cheap_markers = ("flash", "mini", "haiku", "small", "low")
    for model in attack_models:
        model_lc = model.lower()
        if any(marker in model_lc for marker in cheap_markers):
            return model
    return attack_models[0]


def _normalize_concern_text(text: str) -> str:
    """Normalize concern text for cheap exact-match dedup."""
    normalized = text.lower().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"[`*_]+", "", normalized)
    return normalized


def cluster_concerns_with_provenance(
    concerns: list[Concern],
    model: str,
    config: GauntletConfig,
) -> tuple[list[Concern], dict[str, list[Concern]]]:
    """Cluster near-duplicate concerns using a cheap model.

    QUOTA BURN FIX 2: Silent catch-all replaced with retry-once +
    GauntletClusteringError. No more silent fallback to singleton clusters.

    Returns:
        (representatives, cluster_members)
    """
    if not concerns:
        return [], {}

    # Step 1: exact dedup by normalized text (free + deterministic).
    exact_groups: dict[str, list[Concern]] = {}
    for concern in concerns:
        norm = _normalize_concern_text(concern.text)
        exact_groups.setdefault(norm, []).append(concern)

    candidate_groups = list(exact_groups.values())
    candidate_reps = [group[0] for group in candidate_groups]

    if len(candidate_reps) <= 1:
        rep = candidate_reps[0]
        return [rep], {rep.id: candidate_groups[0]}

    # Step 2: semantic clustering over representative candidates.
    concerns_text = "\n".join(
        f"[{idx}] adversary={c.adversary}; model={c.source_model or 'unknown'}\n{c.text}"
        for idx, c in enumerate(candidate_reps, 1)
    )

    system_prompt = """You cluster near-duplicate engineering concerns.

Goal: Merge concerns that describe the SAME underlying issue in different words.

Rules:
1. Merge ONLY when the root cause AND required mitigation are the same.
2. Do NOT merge concerns that are thematically related but require different fixes.
3. Every concern index must appear in exactly one cluster.
4. When in doubt, keep concerns SEPARATE. Over-merging loses insights.

## GOOD merges (same root cause, same fix):
- "Fill events could be lost if DB write fails midway" + "No transactional guarantee for fill event insertion" → MERGE (both about atomicity of fill writes, same fix: wrap in transaction)
- "getMyFills has no pagination" + "Fill query returns unbounded results" → MERGE (both about missing pagination on the same endpoint)
- "Status filter uses wrong enum values" + "getActiveAlgoStates filters on 'executing' but DB has 'working'" → MERGE (same bug described at different abstraction levels)
- "No auth check on /devtest" + "Dev test page accessible without authentication" → MERGE (identical concern, different wording)

## BAD merges (related topic but DIFFERENT root causes or fixes):
- "Fill events lost during concurrent writes" + "Fill events lost if mutation fails midway" → DO NOT MERGE (first is race condition needing locking, second is atomicity needing transactions)
- "getMyFills missing exchange field" + "getMyExecutions missing exchange field" → DO NOT MERGE (different endpoints, different code paths, fixed independently)
- "DMA orders show 0/0 progress" + "Arb orders show wrong leg count" → DO NOT MERGE (different order types, different display bugs, different fixes)
- "No rate limiting on order placement" + "No rate limiting on fill queries" → DO NOT MERGE (different endpoints, different risk profiles)

Output JSON only:
{
  "clusters": [
    [1, 7, 14],
    [2],
    [3, 9]
  ]
}
"""

    user_prompt = f"""Cluster these concerns by semantic equivalence.
Remember: only merge when root cause AND fix are the same. When in doubt, keep separate.

{concerns_text}

Return JSON only."""

    semantic_clusters: list[list[int]] = [[i] for i in range(len(candidate_reps))]

    def _parse_clustering_response(response: str) -> list[list[int]]:
        """Parse clustering JSON response into validated cluster indices."""
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start < 0 or json_end <= json_start:
            return []

        payload = json.loads(response[json_start:json_end])
        raw_clusters = payload.get("clusters", [])
        parsed_clusters: list[list[int]] = []

        for raw_cluster in raw_clusters:
            if isinstance(raw_cluster, dict):
                members = raw_cluster.get("member_indexes") or raw_cluster.get("members") or []
            else:
                members = raw_cluster

            if not isinstance(members, list):
                continue

            converted: list[int] = []
            for idx in members:
                if not isinstance(idx, int):
                    continue
                zero_idx = idx - 1
                if 0 <= zero_idx < len(candidate_reps) and zero_idx not in converted:
                    converted.append(zero_idx)
            if converted:
                parsed_clusters.append(converted)

        if not parsed_clusters:
            return []

        assigned: set[int] = set()
        normalized_clusters: list[list[int]] = []
        for cluster in parsed_clusters:
            fresh = [idx for idx in cluster if idx not in assigned]
            if fresh:
                normalized_clusters.append(fresh)
                assigned.update(fresh)
        for idx in range(len(candidate_reps)):
            if idx not in assigned:
                normalized_clusters.append([idx])

        return normalized_clusters

    try:
        response, in_tokens, out_tokens = call_model(
            model=model,
            system_prompt=system_prompt,
            user_message=user_prompt,
            timeout=config.timeout,
        )
        cost_tracker.add(model, in_tokens, out_tokens)

        result = _parse_clustering_response(response)
        if result:
            semantic_clusters = result

    except Exception as e:
        # QUOTA BURN FIX 2: Retry once with backoff for transient API failures
        print(f"  Clustering failed ({e}), retrying in 2s...", file=sys.stderr)
        time.sleep(2)
        try:
            response, in_tokens, out_tokens = call_model(
                model=model,
                system_prompt=system_prompt,
                user_message=user_prompt,
                timeout=config.timeout,
            )
            cost_tracker.add(model, in_tokens, out_tokens)

            result = _parse_clustering_response(response)
            if result:
                semantic_clusters = result
        except Exception as e2:
            raise GauntletClusteringError(
                f"Clustering failed after retry: {e2}. "
                f"Original error: {e}. "
                f"{len(concerns)} concerns would have hit expensive eval unfiltered."
            )

    # Step 3: expand clusters back to full member concerns and choose representatives.
    representatives: list[Concern] = []
    cluster_members: dict[str, list[Concern]] = {}

    for cluster in semantic_clusters:
        members: list[Concern] = []
        for candidate_idx in cluster:
            members.extend(candidate_groups[candidate_idx])
        if not members:
            continue
        representative = members[0]
        representatives.append(representative)
        cluster_members[representative.id] = members

    return representatives, cluster_members


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
