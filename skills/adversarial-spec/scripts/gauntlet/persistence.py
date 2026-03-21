"""Persistence layer for the gauntlet pipeline.

Extracted from gauntlet_monolith.py — file I/O, stats tracking, resolved
concerns database, and checkpoint/resume support.
"""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from gauntlet.core_types import (
    Evaluation,
    GauntletResult,
)


# =============================================================================
# PATH CONSTANTS
# =============================================================================

STATS_DIR = Path.home() / ".adversarial-spec"
STATS_FILE = STATS_DIR / "adversary_stats.json"
RUNS_DIR = STATS_DIR / "runs"
MEDALS_DIR = STATS_DIR / "medals"
RESOLVED_CONCERNS_FILE = STATS_DIR / "resolved_concerns.json"


# =============================================================================
# ADVERSARY STATS
# =============================================================================


def load_adversary_stats() -> dict:
    """Load adversary statistics from disk."""
    if not STATS_FILE.exists():
        return {
            "last_updated": None,
            "total_runs": 0,
            "adversaries": {},
            "models": {},
        }

    try:
        return json.loads(STATS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {
            "last_updated": None,
            "total_runs": 0,
            "adversaries": {},
            "models": {},
        }


def save_adversary_stats(stats: dict) -> None:
    """Save adversary statistics to disk."""
    STATS_DIR.mkdir(parents=True, exist_ok=True)
    STATS_FILE.write_text(json.dumps(stats, indent=2))


def update_adversary_stats(result: GauntletResult) -> dict:
    """Update adversary statistics with results from a gauntlet run.

    Tracks cost-weighted metrics:
    - dismissal_effort_total: cumulative chars in dismissal reasoning
    - signal_score_sum: sum of signal scores across runs (for averaging)
    """
    stats = load_adversary_stats()

    stats["last_updated"] = datetime.now().isoformat()
    stats["total_runs"] = stats.get("total_runs", 0) + 1

    # Update per-adversary stats
    run_stats = result.get_adversary_stats()
    for adv, adv_run in run_stats.items():
        if adv not in stats["adversaries"]:
            stats["adversaries"][adv] = {
                "concerns_raised": 0,
                "accepted": 0,
                "acknowledged": 0,
                "dismissed": 0,
                "deferred": 0,
                "rebuttals_won": 0,
                "rebuttals_lost": 0,
                "dismissal_effort_total": 0,
                "signal_score_sum": 0.0,
                "runs_with_concerns": 0,
                "notable_finds": [],
            }

        existing = stats["adversaries"][adv]
        existing["concerns_raised"] += adv_run["concerns_raised"]
        existing["accepted"] += adv_run["accepted"]
        existing["acknowledged"] = existing.get("acknowledged", 0) + adv_run.get("acknowledged", 0)
        existing["dismissed"] += adv_run["dismissed"]
        existing["deferred"] += adv_run["deferred"]
        existing["rebuttals_won"] += adv_run["rebuttals_won"]
        existing["rebuttals_lost"] += adv_run["rebuttals_lost"]

        existing["dismissal_effort_total"] = existing.get("dismissal_effort_total", 0) + (
            adv_run["dismissal_effort"] * adv_run["dismissed"]
        )

        if adv_run["concerns_raised"] > 0:
            existing["signal_score_sum"] = existing.get("signal_score_sum", 0) + adv_run["signal_score"]
            existing["runs_with_concerns"] = existing.get("runs_with_concerns", 0) + 1

        total = existing["concerns_raised"]
        existing["acceptance_rate"] = round(existing["accepted"] / total, 3) if total > 0 else 0.0

        if existing["dismissed"] > 0:
            existing["avg_dismissal_effort"] = round(
                existing["dismissal_effort_total"] / existing["dismissed"], 0
            )
        else:
            existing["avg_dismissal_effort"] = 0

        if existing.get("runs_with_concerns", 0) > 0:
            existing["avg_signal_score"] = round(
                existing["signal_score_sum"] / existing["runs_with_concerns"], 3
            )
        else:
            existing["avg_signal_score"] = 0.0

    # Update model stats
    model_roles: list[tuple[str, str]] = []
    attack_models = [m.strip() for m in result.adversary_model.split(",") if m.strip()]
    eval_models = [m.strip() for m in result.eval_model.split(",") if m.strip()]
    for model in attack_models:
        model_roles.append((model, "adversary"))
    for model in eval_models:
        model_roles.append((model, "evaluation"))

    cost_share = result.total_cost / max(1, len(model_roles))
    for model, role in model_roles:
        if model not in stats["models"]:
            stats["models"][model] = {
                "role": role,
                "runs": 0,
                "total_cost": 0.0,
            }
        stats["models"][model]["runs"] += 1
        stats["models"][model]["total_cost"] += cost_share

    # Track model pairing effectiveness
    pairing_key = f"{result.adversary_model} + {result.eval_model}"
    if "model_pairings" not in stats:
        stats["model_pairings"] = {}
    if pairing_key not in stats["model_pairings"]:
        stats["model_pairings"][pairing_key] = {
            "runs": 0,
            "total_concerns": 0,
            "accepted": 0,
            "dismissed": 0,
            "avg_acceptance_rate": 0.0,
        }

    pairing = stats["model_pairings"][pairing_key]
    pairing["runs"] += 1
    total_concerns = len(result.concerns)
    accepted = len([e for e in result.evaluations if e.verdict in ("accepted", "acknowledged")])
    dismissed = len([e for e in result.evaluations if e.verdict == "dismissed"])
    pairing["total_concerns"] += total_concerns
    pairing["accepted"] += accepted
    pairing["dismissed"] += dismissed
    if pairing["total_concerns"] > 0:
        pairing["avg_acceptance_rate"] = round(pairing["accepted"] / pairing["total_concerns"], 3)

    save_adversary_stats(stats)
    return stats


# =============================================================================
# GAUNTLET RUN STORAGE
# =============================================================================


def save_gauntlet_run(result: GauntletResult, spec: str) -> str:
    """Save a full gauntlet run to disk for analysis and debugging.

    Returns path to saved file.
    """
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    spec_hash = result.spec_hash or get_spec_hash(spec)[:8]
    filename = f"{timestamp}_{spec_hash}.json"
    filepath = RUNS_DIR / filename

    run_data = {
        "timestamp": datetime.now().isoformat(),
        "spec_hash": spec_hash,
        "spec_preview": spec[:500] + "..." if len(spec) > 500 else spec,
        "spec_length": len(spec),
        "result": result.to_dict(),
    }

    filepath.write_text(json.dumps(run_data, indent=2))

    # Update index
    index_file = STATS_DIR / "runs_index.json"
    try:
        index = json.loads(index_file.read_text()) if index_file.exists() else {"runs": []}
    except (json.JSONDecodeError, OSError):
        index = {"runs": []}

    raw_count = len(result.raw_concerns) if result.raw_concerns else len(result.concerns)
    index["runs"].append({
        "file": filename,
        "timestamp": run_data["timestamp"],
        "spec_hash": spec_hash,
        "raw_concerns": raw_count,
        "final_concerns": len(result.final_concerns),
        "adversary_model": result.adversary_model,
        "eval_model": result.eval_model,
        "total_cost": result.total_cost,
        "total_time": result.total_time,
    })

    index["runs"] = index["runs"][-100:]
    index_file.write_text(json.dumps(index, indent=2))

    return str(filepath)


def list_gauntlet_runs(limit: int = 10) -> str:
    """List recent gauntlet runs with summary stats."""
    index_file = STATS_DIR / "runs_index.json"

    if not index_file.exists():
        return "No gauntlet runs recorded yet."

    try:
        index = json.loads(index_file.read_text())
    except (json.JSONDecodeError, OSError):
        return "Error reading runs index."

    if not index.get("runs"):
        return "No gauntlet runs recorded yet."

    runs = index["runs"][-limit:][::-1]

    lines = [f"=== Recent Gauntlet Runs (last {len(runs)}) ===", ""]

    for run in runs:
        ts = run.get("timestamp", "unknown")[:19]
        raw = run.get("raw_concerns", "?")
        final = run.get("final_concerns", "?")
        cost = run.get("total_cost", 0)
        time_s = run.get("total_time", 0)

        lines.append(f"{ts}  [{run.get('spec_hash', '?')[:8]}]")
        lines.append(f"  Concerns: {raw} raw → {final} final")
        lines.append(f"  Time: {time_s:.1f}s  Cost: ${cost:.4f}")
        lines.append("")

    return "\n".join(lines)


def load_gauntlet_run(filename: str) -> Optional[dict]:
    """Load a specific gauntlet run by filename."""
    filepath = RUNS_DIR / filename
    if not filepath.exists():
        return None

    try:
        return json.loads(filepath.read_text())
    except (json.JSONDecodeError, OSError):
        return None


# =============================================================================
# SPEC HASHING
# =============================================================================


def get_spec_hash(spec: str) -> str:
    """Get a short hash of a spec for change detection."""
    return hashlib.sha256(spec.encode()).hexdigest()[:16]


# =============================================================================
# RESOLVED CONCERNS DATABASE
# =============================================================================

CONFIDENCE_ACCEPT_THRESHOLD = 0.7
CONFIDENCE_NOTE_THRESHOLD = 0.4
AGE_DECAY_HALFLIFE_DAYS = 14
SPEC_CHANGE_PENALTY = 0.7
USAGE_BOOST_PER_MATCH = 0.05
USAGE_BOOST_CAP = 0.3


def load_resolved_concerns() -> dict:
    """Load resolved concerns database."""
    if not RESOLVED_CONCERNS_FILE.exists():
        return {"concerns": [], "last_updated": None}

    try:
        return json.loads(RESOLVED_CONCERNS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {"concerns": [], "last_updated": None}


def save_resolved_concerns(data: dict) -> None:
    """Save resolved concerns database."""
    STATS_DIR.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = datetime.now().isoformat()
    RESOLVED_CONCERNS_FILE.write_text(json.dumps(data, indent=2))


def add_resolved_concern(
    pattern: str,
    explanation: str,
    adversary: str,
    spec_hash: Optional[str] = None,
    confidence: float = 0.9,
) -> None:
    """Add a resolved concern to the database."""
    data = load_resolved_concerns()
    data["concerns"].append({
        "id": str(uuid.uuid4()),
        "pattern": pattern,
        "explanation": explanation,
        "added_at": datetime.now().isoformat(),
        "adversary": adversary,
        "confidence": confidence,
        "spec_hash": spec_hash,
        "times_matched": 0,
        "last_matched": None,
        "verified_at": None,
    })
    save_resolved_concerns(data)


def calculate_explanation_confidence(
    explanation: dict,
    current_spec_hash: Optional[str] = None,
) -> tuple[float, str]:
    """Calculate current confidence in an explanation.

    Factors: age decay, spec change, usage boost, manual verification.
    """
    base_confidence = explanation.get("confidence", 0.9)
    added_at = explanation.get("added_at", "")
    verified_at = explanation.get("verified_at")
    spec_hash = explanation.get("spec_hash")
    times_matched = explanation.get("times_matched", 0)

    factors = []
    final_confidence = base_confidence

    reference_date = verified_at or added_at
    try:
        ref = datetime.fromisoformat(reference_date.replace("Z", "+00:00"))
        now = datetime.now()
        if ref.tzinfo is not None:
            ref = ref.replace(tzinfo=None)
        age_days = (now - ref).days

        age_factor = math.pow(0.5, age_days / AGE_DECAY_HALFLIFE_DAYS)
        final_confidence *= age_factor

        if age_days > 30:
            factors.append(f"old ({age_days}d)")
        elif age_days > 14:
            factors.append(f"aging ({age_days}d)")
        elif verified_at:
            factors.append(f"verified {age_days}d ago")
    except (ValueError, TypeError):
        factors.append("invalid date")
        final_confidence *= 0.5

    if current_spec_hash and spec_hash and current_spec_hash != spec_hash:
        final_confidence *= SPEC_CHANGE_PENALTY
        factors.append("spec changed")

    if times_matched > 0:
        usage_boost = min(times_matched * USAGE_BOOST_PER_MATCH, USAGE_BOOST_CAP)
        final_confidence = min(final_confidence + usage_boost, 0.95)
        if times_matched >= 3:
            factors.append(f"validated {times_matched}x")

    reason = "; ".join(factors) if factors else "fresh"
    return round(min(final_confidence, 0.99), 3), reason


def record_explanation_match(explanation_id: str) -> None:
    """Record that an explanation was matched (for confidence boosting)."""
    data = load_resolved_concerns()
    for concern in data["concerns"]:
        if concern.get("id") == explanation_id:
            concern["times_matched"] = concern.get("times_matched", 0) + 1
            concern["last_matched"] = datetime.now().isoformat()
            break
    save_resolved_concerns(data)


def verify_explanation(explanation_id: str) -> None:
    """Manually mark an explanation as re-verified (resets age decay)."""
    data = load_resolved_concerns()
    for concern in data["concerns"]:
        if concern.get("id") == explanation_id:
            concern["verified_at"] = datetime.now().isoformat()
            break
    save_resolved_concerns(data)
