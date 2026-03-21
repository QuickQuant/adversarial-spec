"""Medal awards for adversary performance.

Extracted from gauntlet_monolith.py — medal calculation, report
generation, persistence, and display formatting.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Optional

from adversaries import get_version_manifest
from gauntlet.core_types import (
    Evaluation,
    GauntletResult,
    Medal,
)
from gauntlet.persistence import MEDALS_DIR, STATS_DIR


# =============================================================================
# CONCERN SIMILARITY
# =============================================================================

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "can", "this", "that", "these",
    "those", "it", "its", "to", "of", "in", "for", "on", "with", "at",
    "by", "from", "as", "or", "and", "but", "if", "when", "what", "which",
    "who", "how", "why", "where", "there", "here", "all", "each", "every",
    "both", "few", "more", "most", "other", "some", "such", "no", "not",
    "only", "same", "so", "than", "too", "very", "just", "also", "now",
    "any", "into", "out", "up", "down", "about", "above", "below", "between",
}


def _get_concern_keywords(text: str) -> set[str]:
    """Extract significant keywords from concern text for similarity detection."""
    words = set(re.findall(r'\b[a-z]{3,}\b', text.lower()))
    return words - _STOPWORDS


def _concerns_are_similar(concern1: str, concern2: str, threshold: float = 0.3) -> bool:
    """Check if two concerns are semantically similar using keyword overlap."""
    kw1 = _get_concern_keywords(concern1)
    kw2 = _get_concern_keywords(concern2)
    if not kw1 or not kw2:
        return False
    intersection = len(kw1 & kw2)
    union = len(kw1 | kw2)
    similarity = intersection / union if union > 0 else 0
    return similarity >= threshold


# =============================================================================
# MEDAL CALCULATION
# =============================================================================


def calculate_medals(result: GauntletResult, spec_hash: str, run_id: str) -> list[Medal]:
    """Calculate medal awards for a gauntlet run.

    Medal criteria (only when 6+ adversaries):
    - GOLD: Critical insight (high severity), only this adversary caught it
    - SILVER: Critical + 2 adversaries caught it, OR minor + only this adversary
    - BRONZE: Minor fix, fewer than half of adversaries caught it
    """
    active_adversaries = set(c.adversary for c in result.concerns)
    if len(active_adversaries) < 6:
        return []

    medals: list[Medal] = []
    versions = get_version_manifest()
    timestamp = datetime.now().isoformat()

    valuable_evals = [
        e for e in result.evaluations
        if e.verdict in ("accepted", "acknowledged")
    ]

    for eval_item in valuable_evals:
        concern = eval_item.concern
        adversary = concern.adversary

        similar_adversaries = {adversary}
        for other_eval in valuable_evals:
            if other_eval.concern.adversary == adversary:
                continue
            if _concerns_are_similar(concern.text, other_eval.concern.text):
                similar_adversaries.add(other_eval.concern.adversary)

        num_catchers = len(similar_adversaries)
        is_critical = concern.severity == "high"
        is_minor = concern.severity == "low"
        half_adversaries = len(active_adversaries) / 2

        medal_type = None
        uniqueness = ""

        if is_critical and num_catchers == 1:
            medal_type = "gold"
            uniqueness = f"Critical insight caught exclusively by {adversary} - no other adversary identified this issue"
        elif is_critical and num_catchers == 2:
            other = [a for a in similar_adversaries if a != adversary][0]
            medal_type = "silver"
            uniqueness = f"Critical insight caught by {adversary} and {other}"
        elif is_minor and num_catchers == 1:
            medal_type = "silver"
            uniqueness = f"Minor fix caught exclusively by {adversary}"
        elif is_minor and num_catchers < half_adversaries:
            medal_type = "bronze"
            uniqueness = f"Minor fix caught by {num_catchers}/{len(active_adversaries)} adversaries"
        elif is_critical and num_catchers > 2:
            medal_type = "silver"
            uniqueness = f"Critical insight caught by {num_catchers} adversaries: {', '.join(sorted(similar_adversaries))}"

        if medal_type:
            already_awarded = any(
                m.concern_id == concern.id for m in medals
            )
            if not already_awarded:
                adv_version = versions.get(adversary, {}).get("version", "unknown")
                medal = Medal(
                    type=medal_type,
                    adversary=adversary,
                    adversary_version=adv_version,
                    concern_id=concern.id,
                    concern_text=concern.text,
                    severity=concern.severity,
                    uniqueness=uniqueness,
                    report="",
                    timestamp=timestamp,
                    spec_hash=spec_hash,
                    run_id=run_id,
                )
                medals.append(medal)

    return medals


# =============================================================================
# MEDAL REPORTS
# =============================================================================


def generate_medal_report(medal: Medal) -> str:
    """Generate the report text for a medal."""
    concern = medal.concern_text[:500] + "..." if len(medal.concern_text) > 500 else medal.concern_text

    if medal.type == "gold":
        report = f"""## Gold Medal: {medal.adversary}

### The Catch
{concern}

### Why This Matters
This concern was classified as **{medal.severity} severity** and represents a critical insight that was missed during the constructive phase of spec development. The {medal.adversary} persona uniquely identified this issue - no other adversary in the gauntlet run caught it.

### Analysis
{medal.uniqueness}

This demonstrates the value of the {medal.adversary} perspective in catching issues that other review approaches miss. The adversarial nature of this persona allowed it to identify a gap that consensus-based review overlooked.

### Context
- Spec hash: {medal.spec_hash}
- Run ID: {medal.run_id}
- Adversary version: {medal.adversary_version}
- Awarded: {medal.timestamp}
"""
    elif medal.type == "silver":
        report = f"""## Silver Medal: {medal.adversary}

**Concern ({medal.severity} severity):** {concern}

{medal.uniqueness}. This catch contributed to improving the specification quality. (Spec: {medal.spec_hash}, Run: {medal.run_id}, Adversary v{medal.adversary_version})
"""
    else:  # bronze
        report = f"""## Bronze Medal: {medal.adversary}

{medal.severity.title()} severity fix: {concern[:200]}... {medal.uniqueness}. (Run: {medal.run_id})
"""

    return report


def save_medal_reports(medals: list[Medal]) -> str:
    """Save all medal reports to persistent storage. Returns path."""
    if not medals:
        return ""

    MEDALS_DIR.mkdir(parents=True, exist_ok=True)

    for medal in medals:
        if not medal.report:
            medal.report = generate_medal_report(medal)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = medals[0].run_id if medals else "unknown"
    filename = f"medals_{timestamp}_{run_id[:8]}.json"
    filepath = MEDALS_DIR / filename

    data = {
        "timestamp": datetime.now().isoformat(),
        "run_id": run_id,
        "spec_hash": medals[0].spec_hash if medals else "",
        "medal_counts": {
            "gold": len([m for m in medals if m.type == "gold"]),
            "silver": len([m for m in medals if m.type == "silver"]),
            "bronze": len([m for m in medals if m.type == "bronze"]),
        },
        "medals": [m.to_dict() for m in medals],
    }

    filepath.write_text(json.dumps(data, indent=2))

    medals_index = STATS_DIR / "medals_index.json"
    try:
        index = json.loads(medals_index.read_text()) if medals_index.exists() else {"medals": []}
    except (json.JSONDecodeError, OSError):
        index = {"medals": []}

    for medal in medals:
        index["medals"].append({
            "type": medal.type,
            "adversary": medal.adversary,
            "adversary_version": medal.adversary_version,
            "concern_id": medal.concern_id,
            "timestamp": medal.timestamp,
            "run_id": medal.run_id,
            "file": filename,
        })

    index["medals"] = index["medals"][-500:]
    medals_index.write_text(json.dumps(index, indent=2))

    return str(filepath)


def format_medals_for_display(medals: list[Medal]) -> str:
    """Format medals for display in gauntlet output."""
    if not medals:
        return ""

    lines = [
        "",
        "=" * 60,
        "MEDAL AWARDS (6+ adversaries participated)",
        "=" * 60,
    ]

    gold = [m for m in medals if m.type == "gold"]
    silver = [m for m in medals if m.type == "silver"]
    bronze = [m for m in medals if m.type == "bronze"]

    if gold:
        lines.append("")
        lines.append("GOLD MEDALS (Critical insight, exclusive catch):")
        for m in gold:
            lines.append(f"  - {m.adversary} (v{m.adversary_version}): {m.concern_id}")
            lines.append(f"    {m.concern_text[:100]}...")

    if silver:
        lines.append("")
        lines.append("SILVER MEDALS:")
        for m in silver:
            reason = "critical shared" if m.severity == "high" else "minor exclusive"
            lines.append(f"  - {m.adversary} (v{m.adversary_version}): {m.concern_id} [{reason}]")

    if bronze:
        lines.append("")
        lines.append("BRONZE MEDALS (Minor fix, limited coverage):")
        for m in bronze:
            lines.append(f"  - {m.adversary}: {m.concern_id}")

    lines.append("")
    lines.append(f"Full reports saved to: {MEDALS_DIR}")
    lines.append("=" * 60)

    return "\n".join(lines)


# =============================================================================
# MEDAL LEADERBOARD
# =============================================================================


def get_medal_leaderboard() -> str:
    """Get all-time medal standings for adversaries."""
    medals_index = STATS_DIR / "medals_index.json"

    if not medals_index.exists():
        return "No medals awarded yet.\n\nMedals are awarded for gauntlet runs with 6+ adversaries."

    try:
        index = json.loads(medals_index.read_text())
    except (json.JSONDecodeError, OSError):
        return "Error reading medals index."

    if not index.get("medals"):
        return "No medals awarded yet."

    # Count medals by adversary
    counts: dict[str, dict[str, int]] = {}
    for medal in index["medals"]:
        adv = medal["adversary"]
        mtype = medal["type"]
        if adv not in counts:
            counts[adv] = {"gold": 0, "silver": 0, "bronze": 0, "total_points": 0}
        counts[adv][mtype] += 1

    # Calculate points (gold=3, silver=2, bronze=1)
    for adv, c in counts.items():
        c["total_points"] = c["gold"] * 3 + c["silver"] * 2 + c["bronze"] * 1

    # Sort by total points
    sorted_advs = sorted(counts.items(), key=lambda x: x[1]["total_points"], reverse=True)

    lines = [
        "=== Medal Leaderboard (All Time) ===",
        f"Total medals awarded: {len(index['medals'])}",
        "",
        "Rank  Adversary                    G   S   B  Points",
        "-" * 55,
    ]

    for rank, (adv, c) in enumerate(sorted_advs, 1):
        lines.append(
            f"{rank:4}  {adv:28} {c['gold']:3} {c['silver']:3} {c['bronze']:3}  {c['total_points']:6}"
        )

    lines.append("")
    lines.append("Points: Gold=3, Silver=2, Bronze=1")

    return "\n".join(lines)
