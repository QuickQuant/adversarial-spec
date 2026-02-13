#!/usr/bin/env python3
"""
Adversarial Gauntlet - Genuinely adversarial spec review mechanism.

Philosophy: False positives are features, not bugs. A cheap model finding a "hole"
that isn't real forces a frontier model to articulate WHY it's not a problem.
That articulation either:
1. Proves the concern was unfounded (and documents why)
2. Reveals the frontier model can't actually justify the design (real hole!)

Usage:
    # Run gauntlet on a spec
    cat spec.md | python3 debate.py gauntlet

    # Run gauntlet with specific adversaries
    cat spec.md | python3 debate.py gauntlet --gauntlet-adversaries paranoid_security,burned_oncall

    # Run gauntlet before debate
    cat spec.md | python3 debate.py critique --models codex/gpt-5.3-codex --gauntlet
"""

from __future__ import annotations

import concurrent.futures
import json
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class FinalBossVerdict(str, Enum):
    """Verdict from the Final Boss review."""
    PASS = "pass"           # Proceed to implementation
    REFINE = "refine"       # Address concerns, then proceed
    RECONSIDER = "reconsider"  # Re-evaluate approach before proceeding

from adversaries import (
    ADVERSARIES,
    FINAL_BOSS,
    generate_concern_id,
)
from models import (
    call_codex_model,
    call_gemini_cli_model,
    cost_tracker,
)
from providers import (
    CODEX_AVAILABLE,
    DEFAULT_CODEX_REASONING,
    GEMINI_CLI_AVAILABLE,
)

try:
    from litellm import completion
except ImportError:
    print(
        "Error: litellm package not installed. Run: pip install litellm",
        file=sys.stderr,
    )
    sys.exit(1)


# =============================================================================
# ADVERSARY PERSONAS - imported from adversaries.py
# =============================================================================
# ADVERSARIES and FINAL_BOSS are imported from adversaries.py
# Each adversary has: name, prefix, persona, valid_dismissal, invalid_dismissal,
# valid_acceptance, and rule fields.
# Access persona with: ADVERSARIES["name"].persona

# =============================================================================
# FINAL BOSS ADVERSARY (runs after all others, uses Opus 4.6)
# =============================================================================
# FINAL_BOSS is imported from adversaries.py - includes verdict system (PASS/REFINE/RECONSIDER)



# =============================================================================
# RESPONSE PROTOCOLS - now defined in adversaries.py
# =============================================================================
# All adversary personas and dismissal protocols are defined in adversaries.py
# Access via: ADVERSARIES["name"].persona, .valid_dismissal, .invalid_dismissal, etc.


# =============================================================================
# REBUTTAL PROMPT
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


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class Concern:
    """A concern raised by an adversary."""

    adversary: str
    text: str
    severity: str = "medium"  # low, medium, high
    id: str = ""  # Stable ID for linking (auto-generated if empty)
    source_model: str = ""  # Which attack model generated this concern

    def __post_init__(self):
        """Generate ID if not provided."""
        if not self.id:
            self.id = generate_concern_id(self.adversary, self.text)


@dataclass
class Evaluation:
    """Frontier model's evaluation of a concern."""

    concern: Concern
    verdict: str  # dismissed, accepted, acknowledged, deferred
    reasoning: str


@dataclass
class Rebuttal:
    """Adversary's response to a dismissal."""

    evaluation: Evaluation
    response: str
    sustained: bool  # True if challenge was successful


@dataclass
class BigPictureSynthesis:
    """Holistic analysis of all concerns before evaluation.

    Synthesizes insights by looking at the full picture across all adversaries.
    """

    total_concerns: int
    unique_texts: int
    real_issues: list[str]  # The 2-4 things that actually matter
    hidden_connections: list[str]  # Links between different adversaries' concerns
    whats_missing: list[str]  # Blind spots - what no one caught
    meta_concern: str  # The parent concern that would generate all others
    high_signal: list[str]  # 2-3 concerns deserving most attention
    raw_response: str


@dataclass
class GauntletResult:
    """Complete result of running the gauntlet."""

    concerns: list[Concern]  # Post-filtering concerns before clustering
    evaluations: list[Evaluation]
    rebuttals: list[Rebuttal]
    final_concerns: list[Concern]  # Concerns that survived (technical + UX)
    adversary_model: str
    eval_model: str
    total_time: float
    total_cost: float
    final_boss_result: Optional["FinalBossResult"] = None  # Phase 7 result
    raw_concerns: Optional[list[Concern]] = None  # Pre-filtering concerns (all generated)
    dropped_concerns: Optional[list[Concern]] = None  # Concerns dropped by filtering
    spec_hash: Optional[str] = None  # Hash of the spec that was reviewed
    adversary_timing: Optional[dict[str, float]] = None  # Time per adversary in seconds
    big_picture: Optional[BigPictureSynthesis] = None  # Holistic concern analysis
    clustered_concerns: Optional[list[Concern]] = None  # Concerns evaluated after dedup
    clustered_evaluations: Optional[list[Evaluation]] = None  # One evaluation per cluster representative
    cluster_members: Optional[dict[str, list[Concern]]] = None  # representative concern id -> member concerns

    def get_adversary_stats(self) -> dict[str, dict]:
        """Get per-adversary statistics from this run.

        Includes cost-weighted metrics:
        - dismissal_effort: average characters in dismissal reasoning (proxy for effort)
        - signal_score: acceptance_rate * avg_dismissal_effort (higher = better signal:noise)
        """
        stats: dict[str, dict] = {}

        for adv in ADVERSARIES.keys():
            adv_concerns = [c for c in self.concerns if c.adversary == adv]
            adv_evals = [e for e in self.evaluations if e.concern.adversary == adv]
            adv_rebuttals = [r for r in self.rebuttals if r.evaluation.concern.adversary == adv]

            accepted = len([e for e in adv_evals if e.verdict == "accepted"])
            acknowledged = len([e for e in adv_evals if e.verdict == "acknowledged"])
            dismissed = len([e for e in adv_evals if e.verdict == "dismissed"])
            deferred = len([e for e in adv_evals if e.verdict == "deferred"])
            rebuttals_won = len([r for r in adv_rebuttals if r.sustained])
            rebuttals_lost = len([r for r in adv_rebuttals if not r.sustained])

            total = len(adv_concerns)
            # Valuable concerns = accepted + acknowledged (both credit the adversary)
            valuable = accepted + acknowledged
            acceptance_rate = valuable / total if total > 0 else 0.0

            # Cost-weighted metrics: how much effort to dismiss?
            # Longer dismissal reasoning = more expensive false positive
            dismissed_evals = [e for e in adv_evals if e.verdict == "dismissed"]
            dismissal_effort = (
                sum(len(e.reasoning) for e in dismissed_evals) / len(dismissed_evals)
                if dismissed_evals
                else 0
            )

            # Signal score: accepted concerns are valuable, dismissed concerns cost effort
            # Higher is better: high acceptance + long dismissals (hard to disprove)
            # Lower is worse: low acceptance + long dismissals (wasted effort)
            if total > 0:
                # Normalize dismissal effort (0-1 scale, 500 chars = 1.0)
                norm_effort = min(dismissal_effort / 500, 2.0)
                # Signal = acceptance gives you points, expensive dismissals cost points
                signal_score = acceptance_rate - (1 - acceptance_rate) * norm_effort * 0.5
            else:
                signal_score = 0.0

            # NEW: Concern length stats
            concern_lengths = [len(c.text) for c in adv_concerns]
            avg_concern_length = sum(concern_lengths) / len(concern_lengths) if concern_lengths else 0

            # NEW: Rebuttal success by severity
            rebuttal_by_severity = {"high": {"won": 0, "lost": 0}, "medium": {"won": 0, "lost": 0}, "low": {"won": 0, "lost": 0}}
            for r in adv_rebuttals:
                severity = r.evaluation.concern.severity or "medium"
                if r.sustained:
                    rebuttal_by_severity[severity]["won"] += 1
                else:
                    rebuttal_by_severity[severity]["lost"] += 1

            stats[adv] = {
                "concerns_raised": total,
                "accepted": accepted,
                "acknowledged": acknowledged,
                "dismissed": dismissed,
                "deferred": deferred,
                "acceptance_rate": round(acceptance_rate, 3),  # includes acknowledged
                "rebuttals_won": rebuttals_won,
                "rebuttals_lost": rebuttals_lost,
                "dismissal_effort": round(dismissal_effort, 0),  # avg chars
                "signal_score": round(signal_score, 3),
                # NEW metrics
                "avg_concern_length": round(avg_concern_length, 0),
                "rebuttal_by_severity": rebuttal_by_severity,
            }

        return stats

    def to_dict(self) -> dict:
        """Serialize the gauntlet result to a dictionary for JSON storage."""

        def concern_to_dict(c: Concern) -> dict:
            result = {
                "id": c.id,
                "adversary": c.adversary,
                "text": c.text,
                "severity": c.severity,
            }
            if c.source_model:
                result["source_model"] = c.source_model
            return result

        def eval_to_dict(e: Evaluation) -> dict:
            return {
                "concern": concern_to_dict(e.concern),
                "verdict": e.verdict,
                "reasoning": e.reasoning,
            }

        def rebuttal_to_dict(r: Rebuttal) -> dict:
            return {
                "evaluation": eval_to_dict(r.evaluation),
                "response": r.response,
                "sustained": r.sustained,
            }

        result = {
            "adversary_model": self.adversary_model,
            "eval_model": self.eval_model,
            "total_time": self.total_time,
            "total_cost": self.total_cost,
            "spec_hash": self.spec_hash,
            "raw_concerns": (
                [concern_to_dict(c) for c in self.raw_concerns]
                if self.raw_concerns
                else None
            ),
            "dropped_concerns": (
                [concern_to_dict(c) for c in self.dropped_concerns]
                if self.dropped_concerns
                else None
            ),
            "concerns": [concern_to_dict(c) for c in self.concerns],
            "evaluations": [eval_to_dict(e) for e in self.evaluations],
            "rebuttals": [rebuttal_to_dict(r) for r in self.rebuttals],
            "final_concerns": [concern_to_dict(c) for c in self.final_concerns],
            "adversary_stats": self.get_adversary_stats(),
            "adversary_timing": self.adversary_timing,
        }
        if self.clustered_concerns is not None:
            result["clustered_concerns"] = [concern_to_dict(c) for c in self.clustered_concerns]
        if self.clustered_evaluations is not None:
            result["clustered_evaluations"] = [eval_to_dict(e) for e in self.clustered_evaluations]
        if self.cluster_members is not None:
            result["cluster_members"] = {
                rep_id: [concern_to_dict(c) for c in members]
                for rep_id, members in self.cluster_members.items()
            }

        if self.final_boss_result:
            result["final_boss"] = {
                "verdict": self.final_boss_result.verdict.value,
                "approved": self.final_boss_result.approved,  # Backwards compat
                "response": self.final_boss_result.response,
                "concerns": self.final_boss_result.concerns,
                "alternate_approaches": self.final_boss_result.alternate_approaches,
                "reconsider_reason": self.final_boss_result.reconsider_reason,
                "model": self.final_boss_result.model,
                "tokens_used": self.final_boss_result.tokens_used,
                "dismissal_review_stats": (
                    self.final_boss_result.dismissal_review_stats.to_dict()
                    if self.final_boss_result.dismissal_review_stats else None
                ),
                "process_meta_report": self.final_boss_result.process_meta_report,
                "self_meta_report": self.final_boss_result.self_meta_report,
            }

        return result


# =============================================================================
# ADVERSARY STATS PERSISTENCE
# =============================================================================

from datetime import datetime
from pathlib import Path

STATS_DIR = Path.home() / ".adversarial-spec"
STATS_FILE = STATS_DIR / "adversary_stats.json"
RUNS_DIR = STATS_DIR / "runs"  # Directory for full run logs


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
                "dismissal_effort_total": 0,  # cumulative for averaging
                "signal_score_sum": 0.0,  # cumulative for averaging
                "runs_with_concerns": 0,  # for signal score averaging
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

        # Track dismissal effort (cumulative)
        existing["dismissal_effort_total"] = existing.get("dismissal_effort_total", 0) + (
            adv_run["dismissal_effort"] * adv_run["dismissed"]
        )

        # Track signal score for averaging
        if adv_run["concerns_raised"] > 0:
            existing["signal_score_sum"] = existing.get("signal_score_sum", 0) + adv_run["signal_score"]
            existing["runs_with_concerns"] = existing.get("runs_with_concerns", 0) + 1

        # Recalculate derived metrics
        total = existing["concerns_raised"]
        existing["acceptance_rate"] = round(existing["accepted"] / total, 3) if total > 0 else 0.0

        # Average dismissal effort
        if existing["dismissed"] > 0:
            existing["avg_dismissal_effort"] = round(
                existing["dismissal_effort_total"] / existing["dismissed"], 0
            )
        else:
            existing["avg_dismissal_effort"] = 0

        # Average signal score
        if existing.get("runs_with_concerns", 0) > 0:
            existing["avg_signal_score"] = round(
                existing["signal_score_sum"] / existing["runs_with_concerns"], 3
            )
        else:
            existing["avg_signal_score"] = 0.0

    # Update model stats (supports comma-separated model lists).
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

    # NEW: Track model pairing effectiveness
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


def save_gauntlet_run(result: GauntletResult, spec: str) -> str:
    """
    Save a full gauntlet run to disk for analysis and debugging.

    Saves to ~/.adversarial-spec/runs/<timestamp>_<spec_hash>.json

    Args:
        result: The complete gauntlet result
        spec: The original specification text

    Returns:
        Path to the saved file
    """
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    # Create filename with timestamp and spec hash
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    spec_hash = result.spec_hash or get_spec_hash(spec)[:8]
    filename = f"{timestamp}_{spec_hash}.json"
    filepath = RUNS_DIR / filename

    # Build full run data
    run_data = {
        "timestamp": datetime.now().isoformat(),
        "spec_hash": spec_hash,
        "spec_preview": spec[:500] + "..." if len(spec) > 500 else spec,
        "spec_length": len(spec),
        "result": result.to_dict(),
    }

    filepath.write_text(json.dumps(run_data, indent=2))

    # Also update the index file for quick lookups
    index_file = STATS_DIR / "runs_index.json"
    try:
        index = json.loads(index_file.read_text()) if index_file.exists() else {"runs": []}
    except (json.JSONDecodeError, OSError):
        index = {"runs": []}

    # Add summary to index
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

    # Keep last 100 runs in index
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

    runs = index["runs"][-limit:][::-1]  # Most recent first

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


def get_adversary_leaderboard() -> str:
    """Get formatted adversary leaderboard from stats.

    Shows:
    - Signal Score: Best metric (accounts for acceptance rate AND dismissal cost)
    - Acceptance Rate: Raw percentage of concerns accepted
    - Dismissal Effort: Average chars to dismiss (higher = more expensive false positives)
    - Rebuttal Success: How often adversaries win when challenging dismissals
    """
    stats = load_adversary_stats()

    if not stats["adversaries"]:
        return "No gauntlet runs recorded yet.\n\nRun: cat spec.md | python3 debate.py gauntlet"

    lines = [
        f"=== Adversary Leaderboard ({stats['total_runs']} total runs) ===",
        f"Last updated: {stats.get('last_updated', 'unknown')[:19]}",
        "",
        "By Signal Score (best overall metric - balances acceptance vs dismissal cost):",
    ]

    # Sort by signal score (best overall metric)
    sorted_signal = sorted(
        stats["adversaries"].items(),
        key=lambda x: x[1].get("avg_signal_score", 0),
        reverse=True,
    )

    for i, (adv, data) in enumerate(sorted_signal, 1):
        signal = data.get("avg_signal_score", 0)
        rate = data.get("acceptance_rate", 0) * 100
        effort = data.get("avg_dismissal_effort", 0)
        total = data.get("concerns_raised", 0)
        accepted = data.get("accepted", 0)
        acknowledged = data.get("acknowledged", 0)
        valuable = accepted + acknowledged

        # Color-code signal score interpretation
        if signal > 0.3:
            quality = "excellent"
        elif signal > 0.1:
            quality = "good"
        elif signal > -0.1:
            quality = "neutral"
        else:
            quality = "needs work"

        lines.append(
            f"  {i}. {adv}: {signal:+.2f} ({quality})"
        )
        if acknowledged > 0:
            lines.append(
                f"     {rate:.0f}% valuable ({accepted} accepted + {acknowledged} acknowledged = {valuable}/{total})"
            )
        else:
            lines.append(
                f"     {rate:.0f}% accepted ({accepted}/{total}), {effort:.0f} chars avg dismissal"
            )

    # Acceptance rate for comparison
    lines.append("")
    lines.append("By Value Rate (accepted + acknowledged = valuable concerns):")

    sorted_acceptance = sorted(
        stats["adversaries"].items(),
        key=lambda x: x[1].get("acceptance_rate", 0),
        reverse=True,
    )

    for i, (adv, data) in enumerate(sorted_acceptance, 1):
        rate = data.get("acceptance_rate", 0) * 100
        total = data.get("concerns_raised", 0)
        accepted = data.get("accepted", 0)
        acknowledged = data.get("acknowledged", 0)
        if acknowledged > 0:
            lines.append(f"  {i}. {adv}: {rate:.0f}% ({accepted}+{acknowledged}={accepted+acknowledged}/{total})")
        else:
            lines.append(f"  {i}. {adv}: {rate:.0f}% ({accepted}/{total})")

    # Dismissal cost (identifies expensive false positives)
    lines.append("")
    lines.append("By Dismissal Cost (avg effort to dismiss - lower = cheaper false positives):")

    sorted_effort = sorted(
        [(a, d) for a, d in stats["adversaries"].items() if d.get("dismissed", 0) > 0],
        key=lambda x: x[1].get("avg_dismissal_effort", 0),
    )

    for adv, data in sorted_effort:
        effort = data.get("avg_dismissal_effort", 0)
        dismissed = data.get("dismissed", 0)
        lines.append(f"  {adv}: {effort:.0f} chars avg ({dismissed} dismissed)")

    # Rebuttal performance
    sorted_rebuttals = [
        (a, d) for a, d in stats["adversaries"].items()
        if d.get("rebuttals_won", 0) + d.get("rebuttals_lost", 0) > 0
    ]

    if sorted_rebuttals:
        lines.append("")
        lines.append("By Rebuttal Success (challenges won when dismissed):")

        sorted_rebuttals = sorted(
            sorted_rebuttals,
            key=lambda x: x[1].get("rebuttals_won", 0) / max(1, x[1].get("rebuttals_won", 0) + x[1].get("rebuttals_lost", 0)),
            reverse=True,
        )

        for adv, data in sorted_rebuttals:
            won = data.get("rebuttals_won", 0)
            lost = data.get("rebuttals_lost", 0)
            total = won + lost
            rate = won / total * 100 if total > 0 else 0
            lines.append(f"  {adv}: {rate:.0f}% ({won}/{total} won)")

    # Interpretation guide
    lines.append("")
    lines.append("Signal Score Interpretation:")
    lines.append("  > +0.3: Excellent - high value concerns")
    lines.append("  +0.1 to +0.3: Good - useful contributor")
    lines.append("  -0.1 to +0.1: Neutral - consider tuning prompt")
    lines.append("  < -0.1: Needs work - too many expensive false positives")
    lines.append("")
    lines.append("Verdicts: accepted (needs spec change), acknowledged (valid but out of scope),")
    lines.append("          dismissed (invalid), deferred (needs context)")

    return "\n".join(lines)


# =============================================================================
# MEDAL AWARDS SYSTEM
# =============================================================================
# Awards adversaries for unique, high-value catches during gauntlet runs.
# Only awarded when 6+ adversaries participate in a run.

MEDALS_DIR = STATS_DIR / "medals"


@dataclass
class Medal:
    """An award given to an adversary for a notable catch."""
    type: str  # "gold", "silver", "bronze"
    adversary: str
    adversary_version: str  # Version of adversary persona at time of award
    concern_id: str
    concern_text: str
    severity: str  # "high", "medium", "low"
    uniqueness: str  # Description of why this was unique
    report: str  # Full report text (2-4 para gold, 1 para silver, concise bronze)
    timestamp: str
    spec_hash: str
    run_id: str  # Link back to the gauntlet run

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "adversary": self.adversary,
            "adversary_version": self.adversary_version,
            "concern_id": self.concern_id,
            "concern_text": self.concern_text,
            "severity": self.severity,
            "uniqueness": self.uniqueness,
            "report": self.report,
            "timestamp": self.timestamp,
            "spec_hash": self.spec_hash,
            "run_id": self.run_id,
        }


def _get_concern_keywords(text: str) -> set[str]:
    """Extract significant keywords from concern text for similarity detection."""
    import re
    # Remove common words and get significant terms
    stopwords = {
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
    # Extract words, lowercase, filter
    words = set(re.findall(r'\b[a-z]{3,}\b', text.lower()))
    return words - stopwords


def _concerns_are_similar(concern1: str, concern2: str, threshold: float = 0.3) -> bool:
    """Check if two concerns are semantically similar using keyword overlap."""
    kw1 = _get_concern_keywords(concern1)
    kw2 = _get_concern_keywords(concern2)
    if not kw1 or not kw2:
        return False
    # Jaccard similarity
    intersection = len(kw1 & kw2)
    union = len(kw1 | kw2)
    similarity = intersection / union if union > 0 else 0
    return similarity >= threshold


def calculate_medals(result: GauntletResult, spec_hash: str, run_id: str) -> list[Medal]:
    """
    Calculate medal awards for a gauntlet run.

    Medal criteria (only when 6+ adversaries):
    - GOLD: Critical insight (high severity), only this adversary caught it
    - SILVER: Critical + 2 adversaries caught it, OR minor + only this adversary
    - BRONZE: Minor fix, fewer than half of adversaries caught it

    Returns list of Medal objects.
    """
    from adversaries import get_version_manifest

    # Only award medals for runs with 6+ adversaries
    active_adversaries = set(c.adversary for c in result.concerns)
    if len(active_adversaries) < 6:
        return []

    medals: list[Medal] = []
    versions = get_version_manifest()
    timestamp = datetime.now().isoformat()

    # Get accepted/acknowledged evaluations (valuable concerns)
    valuable_evals = [
        e for e in result.evaluations
        if e.verdict in ("accepted", "acknowledged")
    ]

    # Group by adversary
    concerns_by_adversary: dict[str, list[Evaluation]] = {}
    for e in valuable_evals:
        adv = e.concern.adversary
        if adv not in concerns_by_adversary:
            concerns_by_adversary[adv] = []
        concerns_by_adversary[adv].append(e)

    # For each valuable concern, check how many OTHER adversaries caught similar issues
    for eval_item in valuable_evals:
        concern = eval_item.concern
        adversary = concern.adversary

        # Count how many other adversaries caught similar concerns
        similar_adversaries = {adversary}  # Start with self
        for other_eval in valuable_evals:
            if other_eval.concern.adversary == adversary:
                continue
            if _concerns_are_similar(concern.text, other_eval.concern.text):
                similar_adversaries.add(other_eval.concern.adversary)

        num_catchers = len(similar_adversaries)
        is_critical = concern.severity == "high"
        is_minor = concern.severity == "low"
        half_adversaries = len(active_adversaries) / 2

        # Determine medal type
        medal_type = None
        uniqueness = ""

        if is_critical and num_catchers == 1:
            # Gold: Critical insight, only this adversary caught it
            medal_type = "gold"
            uniqueness = f"Critical insight caught exclusively by {adversary} - no other adversary identified this issue"
        elif is_critical and num_catchers == 2:
            # Silver: Critical + exactly 2 adversaries
            other = [a for a in similar_adversaries if a != adversary][0]
            medal_type = "silver"
            uniqueness = f"Critical insight caught by {adversary} and {other}"
        elif is_minor and num_catchers == 1:
            # Silver: Minor fix but nobody else got it
            medal_type = "silver"
            uniqueness = f"Minor fix caught exclusively by {adversary}"
        elif is_minor and num_catchers < half_adversaries:
            # Bronze: Minor fix, fewer than half caught it
            medal_type = "bronze"
            uniqueness = f"Minor fix caught by {num_catchers}/{len(active_adversaries)} adversaries"
        elif is_critical and num_catchers > 2:
            # Silver for major fix with 2+ catchers (shared credit)
            medal_type = "silver"
            uniqueness = f"Critical insight caught by {num_catchers} adversaries: {', '.join(sorted(similar_adversaries))}"

        if medal_type:
            # Check if we already awarded this adversary a medal for this concern type
            # (avoid duplicate medals for same concern)
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
                    report="",  # Will be generated separately
                    timestamp=timestamp,
                    spec_hash=spec_hash,
                    run_id=run_id,
                )
                medals.append(medal)

    return medals


def generate_medal_report(medal: Medal) -> str:
    """
    Generate the report text for a medal.

    - Gold: 2-4 paragraph detailed analysis
    - Silver: 1 paragraph note
    - Bronze: Concise description
    """
    concern = medal.concern_text[:500] + "..." if len(medal.concern_text) > 500 else medal.concern_text

    if medal.type == "gold":
        # 2-4 paragraph detailed report
        report = f"""## 🥇 Gold Medal: {medal.adversary}

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
        # 1 paragraph note
        report = f"""## 🥈 Silver Medal: {medal.adversary}

**Concern ({medal.severity} severity):** {concern}

{medal.uniqueness}. This catch contributed to improving the specification quality. (Spec: {medal.spec_hash}, Run: {medal.run_id}, Adversary v{medal.adversary_version})
"""
    else:  # bronze
        # Concise description
        report = f"""## 🥉 Bronze Medal: {medal.adversary}

{medal.severity.title()} severity fix: {concern[:200]}... {medal.uniqueness}. (Run: {medal.run_id})
"""

    return report


def save_medal_reports(medals: list[Medal]) -> str:
    """
    Save all medal reports to persistent storage.

    Returns path to the saved file.
    """
    if not medals:
        return ""

    MEDALS_DIR.mkdir(parents=True, exist_ok=True)

    # Generate reports for all medals
    for medal in medals:
        if not medal.report:
            medal.report = generate_medal_report(medal)

    # Create filename with timestamp and run info
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = medals[0].run_id if medals else "unknown"
    filename = f"medals_{timestamp}_{run_id[:8]}.json"
    filepath = MEDALS_DIR / filename

    # Save medals with their reports
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

    # Also append to a running log of all medals for quick lookups
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

    # Keep last 500 medals in index
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
        "🏆 MEDAL AWARDS (6+ adversaries participated)",
        "=" * 60,
    ]

    gold = [m for m in medals if m.type == "gold"]
    silver = [m for m in medals if m.type == "silver"]
    bronze = [m for m in medals if m.type == "bronze"]

    if gold:
        lines.append("")
        lines.append("🥇 GOLD MEDALS (Critical insight, exclusive catch):")
        for m in gold:
            lines.append(f"  • {m.adversary} (v{m.adversary_version}): {m.concern_id}")
            lines.append(f"    {m.concern_text[:100]}...")

    if silver:
        lines.append("")
        lines.append("🥈 SILVER MEDALS:")
        for m in silver:
            reason = "critical shared" if m.severity == "high" else "minor exclusive"
            lines.append(f"  • {m.adversary} (v{m.adversary_version}): {m.concern_id} [{reason}]")

    if bronze:
        lines.append("")
        lines.append("🥉 BRONZE MEDALS (Minor fix, limited coverage):")
        for m in bronze:
            lines.append(f"  • {m.adversary}: {m.concern_id}")

    lines.append("")
    lines.append(f"Full reports saved to: {MEDALS_DIR}")
    lines.append("=" * 60)

    return "\n".join(lines)


def get_adversary_synergy(result: GauntletResult) -> dict[str, dict]:
    """
    Calculate synergy between adversary pairs for a single run.

    Synergy is measured by:
    - Overlap: How often do two adversaries catch the same issue?
    - Complementarity: How often do they catch DIFFERENT issues?

    High overlap = redundant coverage
    High complementarity = good pairing (they cover each other's blind spots)

    Returns dict mapping pair names to synergy metrics.
    """
    accepted_by_adv: dict[str, set[str]] = {}

    for e in result.evaluations:
        if e.verdict in ("accepted", "acknowledged"):
            adv = e.concern.adversary
            if adv not in accepted_by_adv:
                accepted_by_adv[adv] = set()
            # Use first 50 chars as a rough "issue fingerprint"
            # (full similarity would be expensive)
            fingerprint = e.concern.text[:50].lower()
            accepted_by_adv[adv].add(fingerprint)

    synergy: dict[str, dict] = {}
    adversaries = list(accepted_by_adv.keys())

    for i, adv1 in enumerate(adversaries):
        for adv2 in adversaries[i + 1:]:
            pair_key = f"{adv1} + {adv2}"
            issues1 = accepted_by_adv[adv1]
            issues2 = accepted_by_adv[adv2]

            # Jaccard-style overlap
            intersection = len(issues1 & issues2)
            union = len(issues1 | issues2)
            overlap_rate = intersection / union if union > 0 else 0

            # Unique issues each found
            unique1 = len(issues1 - issues2)
            unique2 = len(issues2 - issues1)
            total_unique = unique1 + unique2

            synergy[pair_key] = {
                "overlap_rate": round(overlap_rate, 2),
                "total_issues": len(issues1 | issues2),
                f"unique_{adv1}": unique1,
                f"unique_{adv2}": unique2,
                "complementarity": round(total_unique / union, 2) if union > 0 else 0,
            }

    return synergy


def format_synergy_report(synergy: dict[str, dict]) -> str:
    """Format synergy data for display."""
    if not synergy:
        return "No synergy data (need at least 2 adversaries with accepted concerns)"

    lines = ["=== Adversary Pair Synergy ===", ""]

    # Sort by complementarity (higher = better pairing)
    sorted_pairs = sorted(synergy.items(), key=lambda x: x[1].get("complementarity", 0), reverse=True)

    lines.append("Best Pairings (high complementarity = cover each other's blind spots):")
    for pair, data in sorted_pairs[:5]:
        comp = data.get("complementarity", 0)
        overlap = data.get("overlap_rate", 0)
        total = data.get("total_issues", 0)
        lines.append(f"  {pair}")
        lines.append(f"    Complementarity: {comp:.0%}  Overlap: {overlap:.0%}  Total issues: {total}")

    if len(sorted_pairs) > 5:
        lines.append("")
        lines.append("Redundant Pairings (high overlap = consider dropping one):")
        high_overlap = [p for p in sorted_pairs if p[1].get("overlap_rate", 0) > 0.5]
        for pair, data in high_overlap[:3]:
            overlap = data.get("overlap_rate", 0)
            lines.append(f"  {pair}: {overlap:.0%} overlap")

    return "\n".join(lines)


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
        "Rank  Adversary                    🥇  🥈  🥉  Points",
        "-" * 55,
    ]

    for rank, (adv, c) in enumerate(sorted_advs, 1):
        lines.append(
            f"{rank:4}  {adv:28} {c['gold']:3} {c['silver']:3} {c['bronze']:3}  {c['total_points']:6}"
        )

    lines.append("")
    lines.append("Points: Gold=3, Silver=2, Bronze=1")

    return "\n".join(lines)


# =============================================================================
# RESOLVED CONCERNS DATABASE
# =============================================================================

RESOLVED_CONCERNS_FILE = STATS_DIR / "resolved_concerns.json"

# Staleness configuration
CONFIDENCE_ACCEPT_THRESHOLD = 0.7  # Above this = auto-accept explanation
CONFIDENCE_NOTE_THRESHOLD = 0.4  # Above this = note it but still raise
AGE_DECAY_HALFLIFE_DAYS = 14  # Confidence halves every 14 days
SPEC_CHANGE_PENALTY = 0.7  # Multiply confidence by this if spec hash changed
USAGE_BOOST_PER_MATCH = 0.05  # Add this for each successful match (capped)
USAGE_BOOST_CAP = 0.3  # Max boost from usage


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


def get_spec_hash(spec: str) -> str:
    """Get a short hash of a spec for change detection."""
    import hashlib
    return hashlib.sha256(spec.encode()).hexdigest()[:16]


def add_resolved_concern(
    pattern: str,
    explanation: str,
    adversary: str,
    spec_hash: Optional[str] = None,
    confidence: float = 0.9,
) -> None:
    """
    Add a resolved concern to the database.

    Args:
        pattern: Short description of the concern type
        explanation: Why it's resolved
        adversary: Which adversary type raised it
        spec_hash: Hash of the spec when this was resolved
        confidence: Initial confidence (0.0-1.0)
    """
    import uuid

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
        "verified_at": None,  # Set when manually re-verified
    })
    save_resolved_concerns(data)


def calculate_explanation_confidence(
    explanation: dict,
    current_spec_hash: Optional[str] = None,
) -> tuple[float, str]:
    """
    Calculate current confidence in an explanation.

    Factors:
    1. Age decay (exponential with halflife)
    2. Spec change (penalty if spec hash differs)
    3. Usage boost (confidence grows with successful matches)
    4. Manual verification (resets age decay)

    Returns:
        (confidence, reason) tuple
    """
    import math

    base_confidence = explanation.get("confidence", 0.9)
    added_at = explanation.get("added_at", "")
    verified_at = explanation.get("verified_at")  # Manual re-verification
    spec_hash = explanation.get("spec_hash")
    times_matched = explanation.get("times_matched", 0)

    factors = []
    final_confidence = base_confidence

    # 1. Age decay (use verified_at if available, else added_at)
    reference_date = verified_at or added_at
    try:
        ref = datetime.fromisoformat(reference_date.replace("Z", "+00:00"))
        now = datetime.now()
        if ref.tzinfo is not None:
            ref = ref.replace(tzinfo=None)
        age_days = (now - ref).days

        # Exponential decay
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

    # 2. Spec change penalty
    if current_spec_hash and spec_hash and current_spec_hash != spec_hash:
        final_confidence *= SPEC_CHANGE_PENALTY
        factors.append("spec changed")

    # 3. Usage boost (caps at USAGE_BOOST_CAP)
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


@dataclass
class ExplanationMatch:
    """Result of matching a concern against resolved explanations."""
    explanation: dict
    confidence: float
    reason: str
    action: str  # "accept", "note", "ignore"


def find_matching_explanation(
    concern_text: str,
    adversary: str,
    model: str,
    current_spec_hash: Optional[str] = None,
    timeout: int = 60,
) -> Optional[ExplanationMatch]:
    """
    Check if a concern matches any resolved explanation.

    Uses a cheap model to compare concern text against resolved patterns.

    Returns:
        ExplanationMatch with action:
        - "accept": Confidence >= ACCEPT_THRESHOLD, drop the concern
        - "note": Confidence >= NOTE_THRESHOLD, raise but include note
        - "ignore": Below threshold or no match
        - None: No match found
    """
    resolved = load_resolved_concerns()
    if not resolved["concerns"]:
        return None

    # Filter to relevant concerns (same adversary type or general)
    relevant = [
        c for c in resolved["concerns"]
        if c.get("adversary") == adversary or c.get("adversary") == "general"
    ]

    if not relevant:
        return None

    # Pre-calculate confidence for each explanation
    confidence_info = {}
    for i, c in enumerate(relevant):
        conf, reason = calculate_explanation_confidence(c, current_spec_hash)
        confidence_info[i] = (conf, reason)

    # Filter out very low confidence explanations (not worth checking)
    relevant_with_conf = [
        (i, c) for i, c in enumerate(relevant)
        if confidence_info[i][0] >= CONFIDENCE_NOTE_THRESHOLD * 0.5
    ]

    if not relevant_with_conf:
        return None

    # Build comparison prompt with confidence info
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
            timeout=timeout,
        )

        if "MATCH:" in response.upper():
            import re
            match = re.search(r"MATCH:\s*\[?(\d+)\]?", response.upper())
            if match:
                idx = int(match.group(1))
                # Find the actual explanation (idx refers to position in relevant_with_conf)
                for orig_idx, expl in relevant_with_conf:
                    if orig_idx == idx:
                        confidence, reason = confidence_info[idx]

                        # Determine action based on confidence
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

    except Exception:
        pass  # On error, don't filter

    return None


def filter_concerns_with_explanations(
    concerns: list[Concern],
    model: str,
    spec_hash: Optional[str] = None,
    timeout: int = 60,
) -> tuple[list[Concern], list[Concern], list[tuple[Concern, ExplanationMatch]]]:
    """
    Filter concerns against resolved explanations database.

    Args:
        concerns: List of concerns to filter
        model: Model to use for matching
        spec_hash: Hash of current spec
        timeout: Timeout per match

    Returns:
        (
            filtered_concerns,  # Concerns to evaluate (no match or low confidence)
            dropped_concerns,   # Concerns dropped (high confidence match)
            noted_concerns,     # Concerns with notes (medium confidence match)
        )
    """
    filtered = []
    dropped = []
    noted = []

    # Process in parallel for speed
    def check_concern(concern: Concern) -> tuple[Concern, Optional[ExplanationMatch]]:
        match = find_matching_explanation(
            concern.text,
            concern.adversary,
            model,
            spec_hash,
            timeout,
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
                # Record the match for confidence boosting
                record_explanation_match(match.explanation.get("id", ""))
            elif match.action == "note":
                noted.append((concern, match))
                # Still raise but with context
                filtered.append(concern)
            else:
                filtered.append(concern)

    return filtered, dropped, noted


# =============================================================================
# FINAL BOSS REVIEW (Phase 7)
# =============================================================================

@dataclass
class DismissalReviewStats:
    """Tracks efficiency of reviewing dismissed simplification concerns."""
    dismissed_simplifications_reviewed: int = 0  # How many we showed to Final Boss
    dismissals_flagged_invalid: int = 0  # How many the Final Boss said were wrong
    flagged_dismissals: list[str] = None  # Which ones were flagged

    def __post_init__(self):
        if self.flagged_dismissals is None:
            self.flagged_dismissals = []

    @property
    def review_yield_rate(self) -> float:
        """Percentage of reviewed dismissals that were flagged as invalid."""
        if self.dismissed_simplifications_reviewed == 0:
            return 0.0
        return self.dismissals_flagged_invalid / self.dismissed_simplifications_reviewed

    def to_dict(self) -> dict:
        return {
            "dismissed_simplifications_reviewed": self.dismissed_simplifications_reviewed,
            "dismissals_flagged_invalid": self.dismissals_flagged_invalid,
            "flagged_dismissals": self.flagged_dismissals,
            "review_yield_rate": self.review_yield_rate,
        }


@dataclass
class FinalBossResult:
    """Result from the final boss UX review."""
    verdict: FinalBossVerdict
    response: str
    concerns: list[str]  # Concerns to address (for REFINE)
    alternate_approaches: list[str]  # Suggested alternates (for RECONSIDER)
    reconsider_reason: str  # Why reconsideration is needed
    model: str
    tokens_used: int
    dismissal_review_stats: DismissalReviewStats = None  # Telemetry for dismissal review efficiency
    # Meta-reports for process improvement
    process_meta_report: str = ""  # Reflection on entire gauntlet process
    self_meta_report: str = ""  # Reflection on final boss's own process

    def __post_init__(self):
        if self.dismissal_review_stats is None:
            self.dismissal_review_stats = DismissalReviewStats()

    @property
    def approved(self) -> bool:
        """Backwards compatibility - PASS means approved."""
        return self.verdict == FinalBossVerdict.PASS


BIG_PICTURE_PROMPT = """You are analyzing ALL concerns raised by adversarial reviewers about a spec.
Your job is to look at these concerns HOLISTICALLY and synthesize insights that individual
evaluation would miss.

## Concerns by Adversary

{concerns_by_adversary}

## Your Analysis

Look at these concerns as a WHOLE. What story do they tell?

1. **THE REAL ISSUES**: Looking across all adversaries, what are the 2-4 things that
   actually matter most? Cut through the noise. What would you tell the spec author
   if you only had 30 seconds?

2. **HIDDEN CONNECTIONS**: Where do concerns from different adversaries connect in
   ways they don't realize? Security concern X and operations concern Y might be
   the same underlying issue.

3. **WHAT'S MISSING**: Given all the concerns raised, what DIDN'T anyone catch?
   Is there a blind spot? Sometimes the most important insight is what's absent.

4. **THE META-CONCERN**: If these concerns had one parent concern that generated
   them all, what would it be? "The spec doesn't understand X" or "The architecture
   is fighting against Y."

5. **HIGH-SIGNAL ALERTS**: If you had to prioritize the evaluator's attention,
   which 2-3 concerns deserve the most careful review? Why?

Be concise and insightful. Don't just summarize - synthesize.

Format:

REAL_ISSUES:
- [Issue 1]
- [Issue 2]

HIDDEN_CONNECTIONS:
- [Connection 1]

WHATS_MISSING:
- [Gap 1]

META_CONCERN: [One sentence]

HIGH_SIGNAL:
- [Concern ID or quote]: [why it matters]
"""


def generate_big_picture_synthesis(
    concerns: list[Concern],
    model: str,
    timeout: int = 120,
) -> BigPictureSynthesis:
    """Generate a holistic analysis of all concerns before evaluation.

    Synthesizes insights by looking at the full picture:
    - What are the real issues across all concerns?
    - Hidden connections between different adversaries' concerns
    - What's missing - blind spots no one caught
    - The meta-concern that ties everything together
    """
    # Group concerns by adversary for the prompt
    by_adversary: dict[str, list[str]] = {}
    for c in concerns:
        if c.adversary not in by_adversary:
            by_adversary[c.adversary] = []
        by_adversary[c.adversary].append(c.text)

    concerns_text = ""
    for adv, texts in sorted(by_adversary.items()):
        concerns_text += f"\n### {adv} ({len(texts)} concerns)\n"
        for i, t in enumerate(texts, 1):
            concerns_text += f"{i}. {t}\n"

    prompt = BIG_PICTURE_PROMPT.format(concerns_by_adversary=concerns_text)

    try:
        # Use a capable model for synthesis
        if model.startswith("codex/"):
            response, in_tokens, out_tokens = call_codex_model(
                model=model.replace("codex/", ""),
                system_prompt="You are an expert at pattern recognition and synthesis.",
                user_message=prompt,
                timeout=timeout,
            )
        elif model.startswith("gemini-cli/"):
            response, in_tokens, out_tokens = call_gemini_cli_model(
                model=model.replace("gemini-cli/", ""),
                system_prompt="You are an expert at pattern recognition and synthesis.",
                user_message=prompt,
                timeout=timeout,
            )
        else:
            result = completion(
                model=model,
                messages=[
                    {"role": "system", "content": "Expert at pattern recognition."},
                    {"role": "user", "content": prompt},
                ],
                timeout=timeout,
            )
            response = result.choices[0].message.content
            in_tokens = result.usage.prompt_tokens if result.usage else 0
            out_tokens = result.usage.completion_tokens if result.usage else 0

        cost_tracker.add(model, in_tokens, out_tokens)

        # Extract lists from response
        def extract_list(marker: str) -> list[str]:
            items = []
            if marker in response:
                start = response.find(marker) + len(marker)
                # Find next section header
                next_markers = ["REAL_ISSUES", "HIDDEN_CONNECTIONS", "WHATS_MISSING",
                               "META_CONCERN", "HIGH_SIGNAL"]
                end = len(response)
                for m in next_markers:
                    if m in response[start:]:
                        pos = response.find(m, start)
                        if pos < end and pos > start:
                            end = pos
                section = response[start:end]
                for line in section.split("\n"):
                    line = line.strip()
                    if line.startswith(("-", "•", "*")):
                        items.append(line.lstrip("-•* ").strip())
            return items

        def extract_single(marker: str) -> str:
            if marker in response:
                start = response.find(marker) + len(marker)
                end = response.find("\n", start)
                if end == -1:
                    end = len(response)
                return response[start:end].strip()
            return ""

        real_issues = extract_list("REAL_ISSUES:")
        hidden_connections = extract_list("HIDDEN_CONNECTIONS:")
        whats_missing = extract_list("WHATS_MISSING:")
        meta_concern = extract_single("META_CONCERN:")
        high_signal = extract_list("HIGH_SIGNAL:")

        unique_count = len(set(c.text for c in concerns))

        return BigPictureSynthesis(
            total_concerns=len(concerns),
            unique_texts=unique_count,
            real_issues=real_issues,
            hidden_connections=hidden_connections,
            whats_missing=whats_missing,
            meta_concern=meta_concern,
            high_signal=high_signal,
            raw_response=response,
        )

    except Exception as e:
        print(f"Warning: Big picture synthesis failed: {e}", file=sys.stderr)
        return BigPictureSynthesis(
            total_concerns=len(concerns),
            unique_texts=len(set(c.text for c in concerns)),
            real_issues=[],
            hidden_connections=[],
            whats_missing=[],
            meta_concern=f"Synthesis failed: {e}",
            high_signal=[],
            raw_response="",
        )


def run_final_boss_review(
    spec: str,
    gauntlet_summary: str,
    accepted_concerns: list[Concern],
    dismissed_evaluations: list["Evaluation"],
    timeout: int = 600,
) -> FinalBossResult:
    """
    Phase 7: Final Boss UX/User Story Review with Verdict.

    Runs AFTER all other adversaries have been satisfied. Uses Opus 4.6 to do
    a high-level sanity check on whether the spec actually serves users.

    The Final Boss can issue three verdicts:
    - PASS: Proceed to implementation
    - REFINE: Address listed concerns, then proceed
    - RECONSIDER: Fundamental issues exist, models should debate re-architecture

    Args:
        spec: The specification being reviewed
        gauntlet_summary: Summary of what the gauntlet found
        accepted_concerns: List of accepted concerns for pattern analysis
        dismissed_evaluations: Dismissed concerns with their reasoning (for reviewing simplification dismissals)
        timeout: Timeout (longer for Opus)

    Returns:
        FinalBossResult with verdict and details
    """
    import os

    # Final boss uses Opus 4.6 - expensive but thorough
    # Check for Claude Code first (uses subscription)
    if os.environ.get("ANTHROPIC_API_KEY"):
        model = "claude-opus-4-6"
    else:
        # Fall back to best available
        print("  Warning: Opus 4.6 not available, using best alternative", file=sys.stderr)
        if CODEX_AVAILABLE:
            model = "codex/gpt-5.3-codex"
        else:
            model = select_eval_model()

    # Get persona from adversaries.py
    system_prompt = FINAL_BOSS["ux_architect"].persona

    # Build concern analysis for the prompt
    concern_by_adversary = {}
    for c in accepted_concerns:
        if c.adversary not in concern_by_adversary:
            concern_by_adversary[c.adversary] = []
        concern_by_adversary[c.adversary].append(c.text)

    concern_analysis = "\n".join([
        f"- {adv}: {len(concerns)} concerns"
        for adv, concerns in concern_by_adversary.items()
    ])

    # Check for alternate approaches suggested in ACCEPTED concerns
    alternate_approaches = []
    for c in accepted_concerns:
        text_lower = c.text.lower()
        if any(phrase in text_lower for phrase in [
            "alternative", "instead", "could use", "should consider",
            "existing", "already have", "port", "extend", "reuse"
        ]):
            alternate_approaches.append(f"[{c.adversary}] {c.text[:150]}...")

    # CRITICAL: Also check DISMISSED concerns from lazy_developer and prior_art_scout
    # These often suggest simpler approaches that were dismissed without proper evaluation
    dismissed_simplifications = []
    simplification_adversaries = {"lazy_developer", "prior_art_scout", "information_flow_auditor"}
    for e in dismissed_evaluations:
        if e.concern.adversary in simplification_adversaries:
            text_lower = e.concern.text.lower()
            # Look for "use X instead" or "why not just" patterns
            if any(phrase in text_lower for phrase in [
                "why can't", "why not", "just use", "instead", "simpler",
                "over-engineer", "overengineer", "already", "platform",
                "scheduled function", "native", "built-in", "sdk"
            ]):
                dismissed_simplifications.append({
                    "concern": f"[{e.concern.adversary}] {e.concern.text[:200]}",
                    "dismissal": e.reasoning[:200] if e.reasoning else "No reasoning provided",
                })

    alternate_section = ""
    if alternate_approaches:
        alternate_section = f"""
## ALTERNATE APPROACHES SUGGESTED (ACCEPTED)

The following concerns suggested alternate implementations:

{chr(10).join(alternate_approaches[:5])}

Consider whether these alternates would sidestep many of the other concerns.
"""

    # CRITICAL: Show dismissed simplification concerns - these often contain valid alternatives
    # that were dismissed without proper evaluation
    dismissed_section = ""
    num_dismissed_reviewed = len(dismissed_simplifications[:5])  # Track for telemetry
    if dismissed_simplifications:
        dismissed_items = []
        for i, d in enumerate(dismissed_simplifications[:5], 1):
            dismissed_items.append(f"D{i}. CONCERN: {d['concern']}\n    DISMISSED WITH: {d['dismissal']}\n")
        dismissed_section = f"""
## DISMISSED SIMPLIFICATION CONCERNS (REVIEW THESE!)

The following {num_dismissed_reviewed} concerns suggested simpler approaches but were DISMISSED.
**Critically evaluate whether these dismissals properly addressed the alternative:**

{chr(10).join(dismissed_items)}

A dismissal is INVALID if it just says "we need X" without proving the simpler approach can't do X.

**If any dismissals are invalid, list them in your output as:**
INVALID DISMISSALS: D1, D3 (etc.)
"""

    user_prompt = f"""## SPECIFICATION TO REVIEW

{spec}

## GAUNTLET RESULTS

This spec has passed through the adversarial gauntlet:

{gauntlet_summary}

## CONCERN DISTRIBUTION BY ADVERSARY

{concern_analysis}

Total accepted concerns: {len(accepted_concerns)}
{alternate_section}{dismissed_section}
## YOUR TASK

Step back from the technical details. Consider:

1. **USER STORY**: Is this user actually better off?
2. **CONCERN VOLUME**: With {len(accepted_concerns)} accepted concerns, is this spec trying to do too much?
3. **FUNDAMENTAL CHALLENGES**: Did multiple adversaries challenge the same core assumption?
4. **ALTERNATE APPROACHES**: Should any suggested alternates have been explored first?
5. **DISMISSED SIMPLIFICATIONS**: Were any "use simpler X" concerns dismissed without proving X doesn't work?

## REQUIRED OUTPUT FORMAT

You MUST issue one of three verdicts:

```
VERDICT: PASS
RATIONALE: [Why the user story is sound and concerns are normal refinements]
```

OR

```
VERDICT: REFINE
CONCERNS TO ADDRESS:
1. [Concern]
2. [Concern]
```

OR

```
VERDICT: RECONSIDER
FUNDAMENTAL ISSUE: [What's wrong with the current approach]
ALTERNATE APPROACHES TO EVALUATE:
1. [Approach]
2. [Approach]
```

## REQUIRED META-REPORTS (after your verdict)

After your verdict, provide two concise meta-reports for process improvement:

```
PROCESS META-REPORT:
[2-3 sentences reflecting on the entire gauntlet process. Was the adversary coverage appropriate?
Did any adversary add disproportionate value or noise? Any gaps in coverage?]

SELF META-REPORT:
[2-3 sentences reflecting on YOUR process. Was reviewing dismissed concerns worthwhile?
Did the alternate approaches analysis surface anything useful? What would improve your review?]
```

Issue your verdict and meta-reports now."""

    try:
        response, in_tokens, out_tokens = call_model(
            model=model,
            system_prompt=system_prompt,
            user_message=user_prompt,
            timeout=timeout,
        )
        cost_tracker.add(model, in_tokens, out_tokens)

        # Parse verdict from response
        response_upper = response.upper()

        if "VERDICT: RECONSIDER" in response_upper:
            verdict = FinalBossVerdict.RECONSIDER
        elif "VERDICT: REFINE" in response_upper:
            verdict = FinalBossVerdict.REFINE
        elif "VERDICT: PASS" in response_upper:
            verdict = FinalBossVerdict.PASS
        else:
            # Legacy format fallback
            if "APPROVED:" in response_upper:
                verdict = FinalBossVerdict.PASS
            else:
                verdict = FinalBossVerdict.REFINE

        # Extract concerns (for REFINE)
        concerns = []
        if verdict == FinalBossVerdict.REFINE:
            in_concerns_section = False
            for line in response.split("\n"):
                line = line.strip()
                if "CONCERNS TO ADDRESS" in line.upper():
                    in_concerns_section = True
                    continue
                if in_concerns_section and line:
                    if line[0].isdigit() or line.startswith("-") or line.startswith("•"):
                        text = line.lstrip("0123456789.-•) ").strip()
                        if text and len(text) > 10:
                            concerns.append(text)
                    elif line.startswith("VERDICT") or line.startswith("```"):
                        break

        # Extract alternate approaches and reason (for RECONSIDER)
        alts = []
        reconsider_reason = ""
        if verdict == FinalBossVerdict.RECONSIDER:
            in_alts_section = False
            for line in response.split("\n"):
                line = line.strip()
                if "FUNDAMENTAL ISSUE" in line.upper():
                    # Extract the issue
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        reconsider_reason = parts[1].strip()
                    continue
                if "ALTERNATE APPROACHES" in line.upper():
                    in_alts_section = True
                    continue
                if in_alts_section and line:
                    if line[0].isdigit() or line.startswith("-") or line.startswith("•"):
                        text = line.lstrip("0123456789.-•) ").strip()
                        if text and len(text) > 10:
                            alts.append(text)
                    elif line.startswith("```"):
                        break

        # Extract invalid dismissals for telemetry
        flagged_dismissals = []
        for line in response.split("\n"):
            if "INVALID DISMISSALS" in line.upper():
                # Extract D1, D3, etc.
                import re
                matches = re.findall(r'D(\d+)', line, re.IGNORECASE)
                flagged_dismissals = [f"D{m}" for m in matches]
                break

        # Extract meta-reports
        process_meta = ""
        self_meta = ""
        response_lines = response.split("\n")
        for i, line in enumerate(response_lines):
            if "PROCESS META-REPORT" in line.upper():
                # Gather lines until next section or end
                meta_lines = []
                for j in range(i + 1, min(i + 10, len(response_lines))):
                    next_line = response_lines[j].strip()
                    if next_line and not next_line.startswith("```"):
                        if "SELF META-REPORT" in next_line.upper():
                            break
                        meta_lines.append(next_line)
                    elif next_line.startswith("```"):
                        break
                process_meta = " ".join(meta_lines)
            elif "SELF META-REPORT" in line.upper():
                # Gather lines until end
                meta_lines = []
                for j in range(i + 1, min(i + 10, len(response_lines))):
                    next_line = response_lines[j].strip()
                    if next_line and not next_line.startswith("```"):
                        meta_lines.append(next_line)
                    elif next_line.startswith("```"):
                        break
                self_meta = " ".join(meta_lines)

        # Build dismissal review stats
        dismissal_stats = DismissalReviewStats(
            dismissed_simplifications_reviewed=num_dismissed_reviewed,
            dismissals_flagged_invalid=len(flagged_dismissals),
            flagged_dismissals=flagged_dismissals,
        )

        return FinalBossResult(
            verdict=verdict,
            response=response.strip(),
            concerns=concerns,
            alternate_approaches=alts,
            reconsider_reason=reconsider_reason,
            model=model,
            tokens_used=in_tokens + out_tokens,
            dismissal_review_stats=dismissal_stats,
            process_meta_report=process_meta,
            self_meta_report=self_meta,
        )

    except Exception as e:
        print(f"  Warning: Final boss review failed: {e}", file=sys.stderr)
        # On failure, don't block - just note it
        return FinalBossResult(
            verdict=FinalBossVerdict.PASS,
            response=f"Review failed: {e}. Proceeding with caution.",
            concerns=[],
            alternate_approaches=[],
            reconsider_reason="",
            model=model,
            tokens_used=0,
            dismissal_review_stats=DismissalReviewStats(
                dismissed_simplifications_reviewed=num_dismissed_reviewed,
            ),
        )


# =============================================================================
# MULTI-MODEL EVALUATION
# =============================================================================

def get_available_eval_models() -> list[str]:
    """Get list of available evaluation models (prioritize free).

    Returns up to 3 models for multi-model consensus evaluation.
    Prefers free CLI tools over paid APIs.
    """
    import os

    models = []

    # Free CLI tools first (prefer these over paid APIs)
    if CODEX_AVAILABLE:
        models.append("codex/gpt-5.3-codex")
    if GEMINI_CLI_AVAILABLE:
        models.append("gemini-cli/gemini-3-pro-preview")

    # Only add paid API models if we need more models for consensus
    # We want 2-3 models for good consensus, but free is better
    if len(models) < 2:
        if os.environ.get("ANTHROPIC_API_KEY"):
            models.append("claude-sonnet-4-5-20250929")
        if len(models) < 2 and os.environ.get("GEMINI_API_KEY"):
            models.append("gemini/gemini-3-pro")

    return models


def evaluate_concerns_multi_model(
    spec: str,
    concerns: list[Concern],
    models: list[str],
    batch_size: int = 15,
    timeout: int = 300,
) -> list[Evaluation]:
    """
    Phase 4: Evaluate concerns using MULTIPLE models in parallel.

    Args:
        spec: The specification
        concerns: List of concerns to evaluate
        models: List of models to use (will use up to 3)
        batch_size: Number of concerns per batch
        timeout: Timeout per model call

    Returns:
        List of Evaluation objects with consensus verdicts
    """
    if not concerns:
        return []

    # Use up to 3 models for diversity
    eval_models = models[:3] if len(models) >= 3 else models

    if len(eval_models) < 2:
        # Fall back to single-model evaluation
        print(f"  Warning: Only {len(eval_models)} model(s) available, using single-model eval", file=sys.stderr)
        return evaluate_concerns(spec, concerns, eval_models[0], timeout)

    print(f"  Using {len(eval_models)} models: {', '.join(eval_models)}", file=sys.stderr)

    # Split concerns into batches
    batches = [concerns[i:i + batch_size] for i in range(0, len(concerns), batch_size)]
    print(f"  Processing {len(concerns)} concerns in {len(batches)} batches", file=sys.stderr)

    all_evaluations: list[Evaluation] = []
    disagreements = 0

    for batch_idx, batch in enumerate(batches):
        print(f"  Batch {batch_idx + 1}/{len(batches)} ({len(batch)} concerns)...", file=sys.stderr)

        # Evaluate batch with all models in parallel
        model_results: dict[str, list[Evaluation]] = {}

        def eval_with_model(model: str) -> tuple[str, list[Evaluation]]:
            evals = evaluate_concerns(spec, batch, model, timeout)
            return model, evals

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(eval_models)) as executor:
            futures = [executor.submit(eval_with_model, m) for m in eval_models]
            for future in concurrent.futures.as_completed(futures):
                model, evals = future.result()
                model_results[model] = evals

        # Build consensus for each concern in batch
        for i, concern in enumerate(batch):
            verdicts = {}
            reasonings = {}

            for model, evals in model_results.items():
                if i < len(evals):
                    eval_item = evals[i]
                    verdicts[model] = eval_item.verdict
                    reasonings[model] = eval_item.reasoning

            # Determine consensus
            verdict_counts = {}
            for v in verdicts.values():
                verdict_counts[v] = verdict_counts.get(v, 0) + 1

            # Majority wins, ties go to "accepted" (conservative)
            if verdict_counts:
                max_count = max(verdict_counts.values())
                winners = [v for v, c in verdict_counts.items() if c == max_count]

                if len(winners) == 1:
                    consensus_verdict = winners[0]
                else:
                    # Tie - be conservative
                    if "accepted" in winners:
                        consensus_verdict = "accepted"
                    elif "deferred" in winners:
                        consensus_verdict = "deferred"
                    else:
                        consensus_verdict = "dismissed"

                # Check for disagreement
                if len(set(verdicts.values())) > 1:
                    disagreements += 1

                # Combine reasoning
                combined_reasoning = f"[Consensus: {dict(verdict_counts)}] "
                combined_reasoning += reasonings.get(eval_models[0], "")

                all_evaluations.append(Evaluation(
                    concern=concern,
                    verdict=consensus_verdict,
                    reasoning=combined_reasoning,
                ))

    if disagreements > 0:
        print(f"  Model disagreements: {disagreements}/{len(concerns)}", file=sys.stderr)

    return all_evaluations


# =============================================================================
# MODEL SELECTION (FREE-FIRST)
# =============================================================================


def running_in_claude_code() -> bool:
    """Detect if we're running inside Claude Code environment."""
    import os

    # Claude Code sets specific environment variables
    return bool(
        os.environ.get("CLAUDE_CODE")
        or os.environ.get("CC_WORKSPACE")
        or os.environ.get("ANTHROPIC_API_KEY")  # Likely CC if this is set
    )


def select_adversary_model() -> str:
    """
    Select model for adversary attacks (Phase 1 & 3).
    Priority: FREE first (Gemini CLI), then cheapest API.

    Adversaries don't need to be smart - they need to be aggressive.
    """
    # Gemini CLI is free with Google account
    if GEMINI_CLI_AVAILABLE:
        return "gemini-cli/gemini-3-flash-preview"

    # Fall back to cheapest available API
    import os

    if os.environ.get("GROQ_API_KEY"):
        return "groq/llama-3.3-70b-versatile"
    if os.environ.get("DEEPSEEK_API_KEY"):
        return "deepseek/deepseek-chat"
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini/gemini-3-flash"

    raise RuntimeError(
        "No model available for adversaries. Install Gemini CLI (free) or set an API key."
    )


def select_eval_model() -> str:
    """
    Select model for evaluation (Phase 4 & 6).
    Priority: FREE frontier CLI tools, then strongest API.

    Evaluation needs to be rigorous - use the best available.
    """
    # Codex CLI is free with ChatGPT subscription and is frontier quality
    if CODEX_AVAILABLE:
        return "codex/gpt-5.3-codex"

    # Gemini CLI Pro is also frontier quality
    if GEMINI_CLI_AVAILABLE:
        return "gemini-cli/gemini-3-pro-preview"

    # Fall back to strongest available API
    import os

    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude-sonnet-4-5-20250929"
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini/gemini-3-pro"

    raise RuntimeError(
        "No model available for evaluation. Install Codex CLI (free) or set an API key."
    )


def select_gauntlet_models(
    adversary_override: Optional[str] = None,
    eval_override: Optional[str] = None,
) -> tuple[str, str]:
    """
    Select models for the gauntlet.

    Returns:
        (adversary_model, eval_model) tuple
    """
    adversary = adversary_override or select_adversary_model()
    eval_model = eval_override or select_eval_model()
    return adversary, eval_model


# =============================================================================
# MODEL CALLING
# =============================================================================


def call_model(
    model: str,
    system_prompt: str,
    user_message: str,
    timeout: int = 300,
    codex_reasoning: str = DEFAULT_CODEX_REASONING,
) -> tuple[str, int, int]:
    """
    Call a model (CLI or API) and return response with token counts.

    Returns:
        (response_text, input_tokens, output_tokens)
    """
    if model.startswith("codex/"):
        return call_codex_model(
            system_prompt=system_prompt,
            user_message=user_message,
            model=model,
            reasoning_effort=codex_reasoning,
            timeout=timeout,
        )

    if model.startswith("gemini-cli/"):
        return call_gemini_cli_model(
            system_prompt=system_prompt,
            user_message=user_message,
            model=model,
            timeout=timeout,
        )

    # Standard litellm path
    response = completion(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        max_tokens=4000,
        temperature=0.7,
        timeout=timeout,
    )
    content = response.choices[0].message.content
    input_tokens = response.usage.prompt_tokens if response.usage else 0
    output_tokens = response.usage.completion_tokens if response.usage else 0

    return content, input_tokens, output_tokens


# =============================================================================
# PHASE 1: ATTACK GENERATION
# =============================================================================


def generate_attacks(
    spec: str,
    adversaries: list[str],
    models: list[str] | str,
    timeout: int = 300,
    codex_reasoning: str = "low",
) -> tuple[list[Concern], dict[str, float]]:
    """
    Phase 1: Generate attacks from all adversary personas in parallel.

    Args:
        spec: The specification to attack
        adversaries: List of adversary keys to use
        models: Model(s) to use for attack generation
        timeout: Timeout per adversary call
        codex_reasoning: Reasoning effort for Codex attacks (default: "low" to conserve tokens)

    Returns:
        Tuple of (List of Concern objects, dict of adversary@model -> elapsed time in seconds)
    """
    if isinstance(models, str):
        models = [models]
    models = [m.strip() for m in models if m and m.strip()]
    if not models:
        raise ValueError("At least one attack model is required")

    concerns: list[Concern] = []
    timing: dict[str, float] = {}  # Track time per adversary@model

    def run_adversary_with_model(adversary_key: str, model: str) -> tuple[list[Concern], float]:
        """Run one adversary with one model and return concerns with timing."""
        start = time.time()
        adversary = ADVERSARIES.get(adversary_key)
        if not adversary:
            print(f"Warning: Unknown adversary '{adversary_key}'", file=sys.stderr)
            return [], 0.0

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
                timeout=timeout,
                codex_reasoning=codex_reasoning,
            )
            cost_tracker.add(model, in_tokens, out_tokens)

            # Parse concerns from response - group numbered items with their sub-bullets
            local_concerns = []
            current_concern_lines: list[str] = []
            seen_texts: set[str] = set()  # Deduplication

            def flush_concern():
                """Flush accumulated lines as a single concern."""
                if current_concern_lines:
                    # Join all lines into one concern
                    full_text = " ".join(current_concern_lines)
                    # Deduplicate
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

                # Check if this is a new numbered concern (1., 2., etc.)
                is_numbered = line and line[0].isdigit() and (
                    ". " in line[:4] or ")" in line[:4]
                )

                if is_numbered:
                    # Flush previous concern before starting new one
                    flush_concern()
                    # Start new concern with cleaned text
                    text = line.lstrip("0123456789.-) ").strip()
                    if text:
                        current_concern_lines.append(text)
                elif line.startswith(("-", "•", "*")):
                    # Sub-bullet - append to current concern
                    text = line.lstrip("-•* ").strip()
                    if text and current_concern_lines:
                        current_concern_lines.append(text)
                # Ignore other lines (headers, blank, etc.)

            # Flush final concern
            flush_concern()

            elapsed = time.time() - start
            return local_concerns, elapsed

        except Exception as e:
            print(
                f"Warning: Adversary {adversary_key} failed: {e}",
                file=sys.stderr,
            )
            return [], time.time() - start

    # Run adversary/model pairs in parallel
    pairs = [(adv, model) for adv in adversaries for model in models]
    max_workers = min(32, len(pairs)) if pairs else 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(run_adversary_with_model, adv, model): (adv, model)
            for adv, model in pairs
        }
        for future in concurrent.futures.as_completed(futures):
            adv_key, model = futures[future]
            adv_concerns, elapsed = future.result()
            concerns.extend(adv_concerns)
            timing[f"{adv_key}@{model}"] = elapsed

    # Print timing summary
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

    return concerns, timing


# =============================================================================
# PHASE 3.5: CLUSTERING + PROVENANCE EXPANSION
# =============================================================================


def choose_clustering_model(attack_models: list[str], fallback: str) -> str:
    """Choose a cheap model for dedup clustering."""
    if not attack_models:
        return fallback

    # Prefer explicitly cheap model families when available.
    cheap_markers = ("flash", "mini", "haiku", "small", "low")
    for model in attack_models:
        model_lc = model.lower()
        if any(marker in model_lc for marker in cheap_markers):
            return model
    return attack_models[0]


def _normalize_concern_text(text: str) -> str:
    """Normalize concern text for cheap exact-match dedup."""
    import re

    normalized = text.lower().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"[`*_]+", "", normalized)
    return normalized


def cluster_concerns_with_provenance(
    concerns: list[Concern],
    model: str,
    timeout: int = 60,
) -> tuple[list[Concern], dict[str, list[Concern]]]:
    """
    Cluster near-duplicate concerns using a cheap model.

    Returns:
        (
            representatives,   # one concern per cluster
            cluster_members,   # representative concern id -> full member concerns
        )
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

    # If one candidate remains, we're done.
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

    try:
        response, in_tokens, out_tokens = call_model(
            model=model,
            system_prompt=system_prompt,
            user_message=user_prompt,
            timeout=timeout,
        )
        cost_tracker.add(model, in_tokens, out_tokens)

        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
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

                # Convert 1-based indexes to 0-based and validate bounds.
                converted: list[int] = []
                for idx in members:
                    if not isinstance(idx, int):
                        continue
                    zero_idx = idx - 1
                    if 0 <= zero_idx < len(candidate_reps) and zero_idx not in converted:
                        converted.append(zero_idx)
                if converted:
                    parsed_clusters.append(converted)

            if parsed_clusters:
                assigned: set[int] = set()
                normalized_clusters: list[list[int]] = []
                for cluster in parsed_clusters:
                    fresh = [idx for idx in cluster if idx not in assigned]
                    if fresh:
                        normalized_clusters.append(fresh)
                        assigned.update(fresh)
                # Add any unassigned concerns as singleton clusters.
                for idx in range(len(candidate_reps)):
                    if idx not in assigned:
                        normalized_clusters.append([idx])
                if normalized_clusters:
                    semantic_clusters = normalized_clusters

    except Exception as e:
        print(f"  Warning: Clustering failed ({e}); falling back to exact dedup only", file=sys.stderr)

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
    """
    Fan out each clustered evaluation back to all original members for attribution stats.
    """
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

    # Print historical summary if we have multiple runs
    if len(existing) >= 2:
        avg_reduction = sum(e["reduction_pct"] for e in existing) / len(existing)
        print(
            f"  Dedup history: {len(existing)} runs, avg {avg_reduction:.0f}% reduction",
            file=sys.stderr,
        )


# =============================================================================
# PHASE 4: STRUCTURED EVALUATION
# =============================================================================


def evaluate_concerns(
    spec: str,
    concerns: list[Concern],
    model: str,
    timeout: int = 300,
) -> list[Evaluation]:
    """
    Phase 4: Evaluate each concern using the frontier model.

    Args:
        spec: The original specification
        concerns: List of concerns to evaluate
        model: Frontier model for evaluation
        timeout: Timeout for evaluation call

    Returns:
        List of Evaluation objects
    """
    if not concerns:
        return []

    # Build evaluation prompt with all concerns
    concerns_text = "\n\n".join(
        f"### Concern {i+1} (from {c.adversary})\n{c.text}"
        for i, c in enumerate(concerns)
    )

    # Build response protocol reference from Adversary class
    protocols_text = ""
    for adv_key in set(c.adversary for c in concerns):
        adversary = ADVERSARIES.get(adv_key)
        if adversary:
            protocols_text += f"\n### When evaluating {adv_key}:\n"
            protocols_text += f"Valid dismissal: {adversary.valid_dismissal}\n"
            protocols_text += f"Invalid dismissal: {adversary.invalid_dismissal}\n"
            protocols_text += f"Rule: {adversary.rule}\n"
        else:
            # Fallback for unknown adversaries
            protocols_text += f"\n### When evaluating {adv_key}:\n"
            protocols_text += "Valid dismissal: Use your judgment\n"
            protocols_text += "Invalid dismissal: Be careful of handwaving\n"
            protocols_text += "Rule: Be rigorous\n"

    system_prompt = f"""You are a senior engineer evaluating concerns raised by adversarial reviewers.

For each concern, you must decide:
- DISMISS: The concern is not valid (must cite specific evidence)
- ACCEPT: The concern is valid (spec needs revision)
- ACKNOWLEDGE: The concern is valid and insightful, but won't be addressed due to external constraints (out of scope, known tradeoff, business decision, etc.)
- DEFER: Need more context to decide

IMPORTANT: Use ACKNOWLEDGE when the adversary raised a GOOD point that you appreciate them thinking about, but you're choosing not to act on it for reasons they couldn't have known. This credits the adversary for valuable thinking without requiring spec changes.

RESPONSE PROTOCOLS:{protocols_text}

CRITICAL RULES:
1. No emotional language - just logic and evidence
2. For DISMISS: You MUST cite specific reasons from the spec or architecture
3. For ACCEPT: Briefly note what needs to change
4. For ACKNOWLEDGE: Note why the point is valid AND why it's not being addressed
5. For DEFER: Note what information is missing

Output your evaluation as JSON with this structure:
{{
  "evaluations": [
    {{"concern_index": 0, "verdict": "dismissed|accepted|acknowledged|deferred", "reasoning": "..."}},
    ...
  ]
}}"""

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
            timeout=timeout,
        )
        cost_tracker.add(model, in_tokens, out_tokens)

        # Parse JSON response
        # Find JSON in response (may be wrapped in markdown)
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            data = json.loads(json_str)

            evaluations = []
            for eval_data in data.get("evaluations", []):
                idx = eval_data.get("concern_index", 0)
                if idx < len(concerns):
                    evaluations.append(
                        Evaluation(
                            concern=concerns[idx],
                            verdict=eval_data.get("verdict", "deferred"),
                            reasoning=eval_data.get("reasoning", ""),
                        )
                    )
            return evaluations

    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse evaluation JSON: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Evaluation failed: {e}", file=sys.stderr)

    # Fallback: defer all concerns
    return [
        Evaluation(concern=c, verdict="deferred", reasoning="Evaluation failed")
        for c in concerns
    ]


# =============================================================================
# PHASE 3: ADVERSARY REBUTTAL
# =============================================================================


def run_rebuttals(
    evaluations: list[Evaluation],
    model: str,
    timeout: int = 300,
) -> list[Rebuttal]:
    """
    Phase 5: Allow adversaries to rebut dismissals.

    Args:
        evaluations: List of evaluations (only dismissed ones get rebuttals)
        model: Model for adversary rebuttals
        timeout: Timeout per rebuttal

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
                timeout=timeout,
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
    # Rate limits vary by provider:
    #   Gemini: 5-15 RPM (free), 150+ RPM (paid) - set GEMINI_PAID_TIER=true
    #   Claude: 50 RPM (Tier 1), 2000+ (Tier 3+) - set CLAUDE_PAID_TIER=true
    #   Codex: message quotas, generally generous
    import os

    def get_rate_limit_config(model_name: str) -> tuple[int, int]:
        """Return (batch_size, delay_seconds) for the given model."""
        model_lower = model_name.lower()
        if "gemini" in model_lower:
            paid = os.environ.get("GEMINI_PAID_TIER", "").lower() == "true"
            return (10, 2) if paid else (3, 15)
        elif "claude" in model_lower or "anthropic" in model_lower:
            paid = os.environ.get("CLAUDE_PAID_TIER", "").lower() == "true"
            return (20, 1) if paid else (5, 5)
        elif "codex" in model_lower or "gpt" in model_lower or "openai" in model_lower:
            # Codex uses message quotas, not RPM - be generous
            return (10, 2)
        else:
            # Unknown provider - be conservative
            return (3, 10)

    batch_size, batch_delay = get_rate_limit_config(model)

    for i in range(0, len(dismissed), batch_size):
        batch = dismissed[i:i + batch_size]
        if i > 0:
            print(f"    Batch {i // batch_size + 1}/{(len(dismissed) + batch_size - 1) // batch_size}...", file=sys.stderr)
            time.sleep(batch_delay)
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(batch)) as executor:
            futures = [executor.submit(run_rebuttal, e) for e in batch]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    rebuttals.append(result)

    return rebuttals


# =============================================================================
# PHASE 4: FINAL ADJUDICATION
# =============================================================================


def final_adjudication(
    spec: str,
    rebuttals: list[Rebuttal],
    model: str,
    timeout: int = 300,
) -> list[Concern]:
    """
    Phase 6: Final adjudication of challenged dismissals.

    Args:
        spec: The original specification
        rebuttals: Rebuttals that were sustained (challenged)
        model: Frontier model for final decision
        timeout: Timeout for adjudication

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
            timeout=timeout,
        )
        cost_tracker.add(model, in_tokens, out_tokens)

        # Parse JSON
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
        print(f"Warning: Final adjudication failed: {e}", file=sys.stderr)

    # Conservative fallback: all challenged concerns survive
    return [r.evaluation.concern for r in challenged]


# =============================================================================
# MAIN GAUNTLET RUNNER
# =============================================================================


def run_gauntlet(
    spec: str,
    adversaries: Optional[list[str]] = None,
    adversary_model: Optional[str] = None,
    attack_models: Optional[list[str]] = None,
    eval_models: Optional[list[str]] = None,
    allow_rebuttals: bool = True,
    use_multi_model: bool = True,
    skip_filtering: bool = False,
    run_final_boss: bool = False,
    timeout: int = 300,
    attack_codex_reasoning: str = "low",
) -> GauntletResult:
    """
    Run the full adversarial gauntlet on a specification.

    Args:
        spec: The specification to review
        adversaries: List of adversary keys (default: all)
        adversary_model: Legacy single-model override for adversaries
        attack_models: Model list for adversary attacks (default: auto-select one cheap model)
        eval_models: Models for evaluation (default: auto-select multiple)
        allow_rebuttals: Whether to run rebuttal phase
        use_multi_model: Use multiple models for evaluation consensus
        skip_filtering: Skip filtering against resolved concerns
        run_final_boss: Run Phase 7 Final Boss UX review (expensive, uses Opus 4.6)
        timeout: Timeout per model call
        attack_codex_reasoning: Reasoning effort for Codex in attack phase (default: "low")

    Returns:
        GauntletResult with all phases' outputs
    """
    start_time = time.time()
    spec_hash = get_spec_hash(spec)

    # Select models
    if attack_models is None:
        if adversary_model:
            attack_models = [m.strip() for m in adversary_model.split(",") if m.strip()]
        else:
            attack_models = [select_adversary_model()]
    else:
        attack_models = [m.strip() for m in attack_models if m and m.strip()]
    if not attack_models:
        attack_models = [select_adversary_model()]

    # Keep legacy field populated for backwards compatibility in reports/stats.
    adversary_model = ", ".join(attack_models)
    primary_attack_model = attack_models[0]

    if eval_models is None:
        if use_multi_model:
            eval_models = get_available_eval_models()[:3]  # Up to 3 models
        else:
            eval_models = [select_eval_model()]

    # Default to all adversaries
    if adversaries is None:
        adversaries = list(ADVERSARIES.keys())

    print("=== Adversarial Gauntlet ===", file=sys.stderr)
    print(f"Adversaries: {', '.join(adversaries)}", file=sys.stderr)
    print(f"Attack models: {', '.join(attack_models)}", file=sys.stderr)
    print(f"Eval models: {', '.join(eval_models)}", file=sys.stderr)
    print(file=sys.stderr)

    # Phase 1: Attack Generation (parallel)
    print("Phase 1: Generating attacks...", file=sys.stderr)
    raw_concerns, adversary_timing = generate_attacks(
        spec, adversaries, attack_models, timeout,
        codex_reasoning=attack_codex_reasoning,
    )
    print(f"  Generated {len(raw_concerns)} raw concerns", file=sys.stderr)

    # Save raw concerns before any filtering
    concerns = raw_concerns  # Will be replaced if filtering is enabled

    # Persist concerns immediately so they survive crashes
    gauntlet_dir = Path(".adversarial-spec-gauntlet")
    gauntlet_dir.mkdir(exist_ok=True)
    concerns_file = gauntlet_dir / f"concerns-{spec_hash[:8]}.json"
    with open(concerns_file, 'w') as f:
        json.dump(
            [
                {
                    "id": c.id,
                    "adversary": c.adversary,
                    "text": c.text,
                    "severity": c.severity,
                    "source_model": c.source_model,
                }
                for c in concerns
            ],
            f,
            indent=2,
        )
    print(f"  Concerns saved: {concerns_file}", file=sys.stderr)

    # Phase 2: Big Picture Synthesis
    print("Phase 2: Big picture synthesis...", file=sys.stderr)
    big_picture = generate_big_picture_synthesis(
        concerns,
        primary_attack_model,
        timeout=120,
    )
    if big_picture.real_issues:
        print(f"  Real issues: {len(big_picture.real_issues)}", file=sys.stderr)
        for issue in big_picture.real_issues[:2]:
            print(f"    • {issue[:70]}...", file=sys.stderr)
    if big_picture.meta_concern:
        print(f"  Meta-concern: {big_picture.meta_concern[:80]}...", file=sys.stderr)
    if big_picture.high_signal:
        n = len(big_picture.high_signal)
        print(f"  High-signal: {n} concerns flagged", file=sys.stderr)

    # Phase 3: Self-Filtering
    dropped_concerns: list[Concern] = []
    noted_concerns: list[tuple[Concern, ExplanationMatch]] = []

    if not skip_filtering:
        print("Phase 3: Filtering against resolved concerns...", file=sys.stderr)
        concerns, dropped_concerns, noted_concerns = filter_concerns_with_explanations(
            concerns,
            primary_attack_model,  # Use cheap model for filtering
            spec_hash,
            timeout=60,
        )
        if dropped_concerns:
            print(f"  Dropped: {len(dropped_concerns)} (already addressed)", file=sys.stderr)
        if noted_concerns:
            print(f"  Noted: {len(noted_concerns)} (has explanation but re-verifying)", file=sys.stderr)
        print(f"  Proceeding with: {len(concerns)} concerns", file=sys.stderr)

    # Preserve post-filter concerns for adversary-level stats before clustering.
    post_filter_concerns = concerns

    # Phase 3.5: Cluster + Dedup
    clustering_model = choose_clustering_model(attack_models, primary_attack_model)
    print(f"Phase 3.5: Clustering near-duplicates ({clustering_model})...", file=sys.stderr)
    clustered_concerns, cluster_members = cluster_concerns_with_provenance(
        concerns,
        clustering_model,
        timeout=60,
    )
    cluster_deduped = len(concerns) - len(clustered_concerns)
    reduction_pct = (cluster_deduped / len(concerns) * 100) if concerns else 0
    print(
        f"  Clustered: {len(concerns)} -> {len(clustered_concerns)} ({cluster_deduped} merged, {reduction_pct:.0f}% reduction)",
        file=sys.stderr,
    )

    # Persist dedup stats for tracking over time
    _track_dedup_stats(
        spec_hash=spec_hash,
        raw_count=len(raw_concerns),
        post_filter_count=len(post_filter_concerns),
        post_cluster_count=len(clustered_concerns),
        cluster_deduped=cluster_deduped,
        reduction_pct=reduction_pct,
        attack_models=attack_models,
        clustering_model=clustering_model,
    )

    # Phase 4: Multi-Model Evaluation (batched, parallel)
    print("Phase 4: Evaluating concerns...", file=sys.stderr)
    evaluation_concerns = clustered_concerns
    if use_multi_model and len(eval_models) >= 2:
        clustered_evaluations = evaluate_concerns_multi_model(
            spec,
            evaluation_concerns,
            eval_models,
            timeout=timeout,
        )
    else:
        clustered_evaluations = evaluate_concerns(
            spec,
            evaluation_concerns,
            eval_models[0],
            timeout,
        )

    dismissed = [e for e in clustered_evaluations if e.verdict == "dismissed"]
    accepted = [e for e in clustered_evaluations if e.verdict == "accepted"]
    acknowledged = [e for e in clustered_evaluations if e.verdict == "acknowledged"]
    deferred = [e for e in clustered_evaluations if e.verdict == "deferred"]
    print(
        f"  Dismissed: {len(dismissed)}, Accepted: {len(accepted)}, Acknowledged: {len(acknowledged)}, Deferred: {len(deferred)}",
        file=sys.stderr,
    )

    # Persist evaluations immediately so they survive crashes
    evals_file = gauntlet_dir / f"evaluations-{spec_hash[:8]}.json"
    with open(evals_file, 'w') as f:
        eval_data = [
            {
                "concern": {
                    "id": e.concern.id,
                    "adversary": e.concern.adversary,
                    "text": e.concern.text,
                    "severity": e.concern.severity,
                    "source_model": e.concern.source_model,
                },
                "verdict": e.verdict,
                "reasoning": e.reasoning,
            }
            for e in clustered_evaluations
        ]
        json.dump(eval_data, f, indent=2)
    print(f"  Evaluations saved: {evals_file}", file=sys.stderr)

    # Print intermediate summary (so results visible even if later phases crash)
    print("\n=== Phase 4 Summary (accepted concerns) ===", file=sys.stderr)
    for e in accepted[:10]:
        print(f"  [{e.concern.adversary}] {e.concern.text[:80]}...", file=sys.stderr)
    if len(accepted) > 10:
        print(f"  ... and {len(accepted) - 10} more", file=sys.stderr)
    if acknowledged:
        print("\n=== Acknowledged (valid but out of scope) ===", file=sys.stderr)
        for e in acknowledged[:5]:
            print(f"  [{e.concern.adversary}] {e.concern.text[:80]}...", file=sys.stderr)
        if len(acknowledged) > 5:
            print(f"  ... and {len(acknowledged) - 5} more", file=sys.stderr)
    print(file=sys.stderr)

    # Phase 5: Rebuttals (parallel)
    rebuttals: list[Rebuttal] = []
    if allow_rebuttals and dismissed:
        print("Phase 5: Running rebuttals...", file=sys.stderr)
        rebuttals = run_rebuttals(clustered_evaluations, primary_attack_model, timeout)
        sustained = sum(1 for r in rebuttals if r.sustained)
        print(f"  Challenges: {sustained} of {len(rebuttals)}", file=sys.stderr)

    # Phase 6: Final Adjudication
    surviving_challenges: list[Concern] = []
    primary_eval_model = eval_models[0] if eval_models else select_eval_model()
    if rebuttals:
        challenged = [r for r in rebuttals if r.sustained]
        if challenged:
            print("Phase 6: Final adjudication...", file=sys.stderr)
            surviving_challenges = final_adjudication(spec, rebuttals, primary_eval_model, timeout)
            print(f"  Overturned: {len(surviving_challenges)}", file=sys.stderr)

    # Compile technical concerns (accepted + deferred + surviving challenges)
    technical_concerns = (
        [e.concern for e in accepted]
        + [e.concern for e in deferred]
        + surviving_challenges
    )

    # Print full summary BEFORE Final Boss prompt (survives crashes/EOFError)
    print("\n=== Gauntlet Summary (Phases 1-6) ===", file=sys.stderr)
    print(
        f"Total concerns: {len(raw_concerns)} generated, "
        f"{len(post_filter_concerns)} post-filter, "
        f"{len(clustered_concerns)} clustered for eval",
        file=sys.stderr,
    )
    print(f"Verdicts: {len(accepted)} accepted, {len(dismissed)} dismissed, {len(deferred)} deferred", file=sys.stderr)
    if surviving_challenges:
        print(f"Rebuttals: {len(surviving_challenges)} overturned", file=sys.stderr)
    print(f"Technical concerns requiring revision: {len(technical_concerns)}", file=sys.stderr)
    print(f"Checkpoint files: {gauntlet_dir}/", file=sys.stderr)
    print(file=sys.stderr)

    # Phase 7: Final Boss UX Review (optional, expensive)
    final_boss_result: Optional[FinalBossResult] = None
    ux_concerns: list[Concern] = []

    # Determine whether to run Final Boss
    do_final_boss = run_final_boss
    if not do_final_boss:
        try:
            do_final_boss = input("Run Final Boss UX review? (y/n): ").strip().lower().startswith('y')
        except EOFError:
            print("  Skipping Final Boss (no stdin available, use --final-boss to enable)", file=sys.stderr)
            do_final_boss = False

    if do_final_boss:
        print("Phase 7: Final Boss UX Review (Opus 4.6)...", file=sys.stderr)

        # Build summary of what the gauntlet found
        gauntlet_summary = f"""Technical review results:
- {len(raw_concerns)} concerns raised by adversaries
- {len(dropped_concerns)} filtered out (already addressed)
- {len(clustered_concerns)} clustered concerns evaluated
- {len(dismissed)} dismissed with justification
- {len(accepted)} accepted (spec needs revision)
- {len(deferred)} deferred (need more context)
- {len(surviving_challenges)} reinstated via rebuttal

Technical concerns requiring revision: {len(technical_concerns)}
"""
        if technical_concerns:
            gauntlet_summary += "\nConcerns being addressed:\n"
            for c in technical_concerns[:5]:  # Show first 5
                gauntlet_summary += f"- [{c.adversary}] {c.text[:100]}...\n"

        # Get accepted concerns for pattern analysis
        accepted_concerns = [e.concern for e in accepted]

        final_boss_result = run_final_boss_review(
            spec=spec,
            gauntlet_summary=gauntlet_summary,
            accepted_concerns=accepted_concerns,
            dismissed_evaluations=dismissed,
            timeout=600,
        )

        # Handle verdict
        if final_boss_result.verdict == FinalBossVerdict.PASS:
            print(f"  VERDICT: PASS by {final_boss_result.model}", file=sys.stderr)
        elif final_boss_result.verdict == FinalBossVerdict.REFINE:
            print(f"  VERDICT: REFINE by {final_boss_result.model}", file=sys.stderr)
            print("  Concerns to address:", file=sys.stderr)
            for concern_text in final_boss_result.concerns[:3]:
                print(f"    - {concern_text[:80]}...", file=sys.stderr)
            # Add UX concerns to final list
            for concern_text in final_boss_result.concerns:
                ux_concerns.append(Concern(
                    adversary="ux_architect",
                    text=concern_text,
                    severity="high",
                ))
        elif final_boss_result.verdict == FinalBossVerdict.RECONSIDER:
            print(f"  VERDICT: RECONSIDER by {final_boss_result.model}", file=sys.stderr)
            print(f"  Reason: {final_boss_result.reconsider_reason}", file=sys.stderr)
            print("  Alternate approaches to evaluate:", file=sys.stderr)
            for alt in final_boss_result.alternate_approaches[:3]:
                print(f"    - {alt[:80]}...", file=sys.stderr)
            # Add a meta-concern about needing reconsideration
            ux_concerns.append(Concern(
                adversary="ux_architect",
                text=f"RECONSIDER VERDICT: {final_boss_result.reconsider_reason}. "
                     f"Alternates: {'; '.join(final_boss_result.alternate_approaches[:2])}",
                severity="critical",
            ))

    # Final concerns = technical + UX
    final_concerns = technical_concerns + ux_concerns

    total_time = time.time() - start_time
    total_cost = cost_tracker.total_cost

    print(file=sys.stderr)
    print("=== Gauntlet Complete ===", file=sys.stderr)
    print(f"Duration: {total_time:.1f}s", file=sys.stderr)
    if dropped_concerns:
        print(f"Filtered out: {len(dropped_concerns)} (previously addressed)", file=sys.stderr)
    print(f"Final concerns requiring revision: {len(final_concerns)}", file=sys.stderr)
    print(f"Total cost: ${total_cost:.4f}", file=sys.stderr)

    # Expand clustered evaluations back to member concerns for adversary attribution stats.
    evaluations = expand_clustered_evaluations(clustered_evaluations, cluster_members)

    result = GauntletResult(
        concerns=post_filter_concerns,  # Post-filtering concerns before clustering
        evaluations=evaluations,
        rebuttals=rebuttals,
        final_concerns=final_concerns,
        adversary_model=adversary_model,
        eval_model=", ".join(eval_models),  # Show all eval models used
        total_time=total_time,
        total_cost=total_cost,
        final_boss_result=final_boss_result,
        raw_concerns=raw_concerns,  # All concerns before filtering
        dropped_concerns=dropped_concerns,  # Concerns dropped by filtering
        spec_hash=spec_hash,
        adversary_timing=adversary_timing,  # Time per adversary
        big_picture=big_picture,  # Holistic synthesis
        clustered_concerns=clustered_concerns,
        clustered_evaluations=clustered_evaluations,
        cluster_members=cluster_members,
    )

    # Auto-save dismissed concerns to resolved database (for future filtering)
    # Only save dismissals with substantive reasoning (> 100 chars)
    saved_count = 0
    for e in dismissed:
        if len(e.reasoning) > 100:
            # Extract a short pattern from the concern
            pattern = e.concern.text[:100].strip()
            if pattern:
                add_resolved_concern(
                    pattern=pattern,
                    explanation=e.reasoning[:500],  # Cap explanation length
                    adversary=e.concern.adversary,
                    spec_hash=spec_hash,
                    confidence=0.85,  # Start with good confidence
                )
                saved_count += 1

    if saved_count > 0:
        print(f"Saved {saved_count} dismissal explanations for future filtering", file=sys.stderr)

    # Update adversary statistics for continuous improvement
    update_adversary_stats(result)

    # Save full run log for analysis and debugging
    run_file = save_gauntlet_run(result, spec)
    run_id = Path(run_file).stem  # e.g., "20260129_090522_abc123"
    print(f"Run log saved: {run_file}", file=sys.stderr)

    # Calculate and save medal awards (only for 6+ adversary runs)
    medals = calculate_medals(result, spec_hash, run_id)
    if medals:
        medal_file = save_medal_reports(medals)
        print(f"Medals awarded: {len(medals)} (saved to {medal_file})", file=sys.stderr)
        # Store medals in result for display
        result.medals = medals  # type: ignore[attr-defined]

    return result


def format_gauntlet_report(result: GauntletResult) -> str:
    """Format a human-readable gauntlet report."""
    lines = [
        "=== Adversarial Gauntlet Report ===",
        "",
        f"Adversary model: {result.adversary_model}",
        f"Eval model: {result.eval_model}",
        f"Duration: {result.total_time:.1f}s",
        f"Total cost: ${result.total_cost:.4f}",
        "",
    ]

    # Phase 1 summary
    phase1_concerns = result.raw_concerns if result.raw_concerns is not None else result.concerns
    by_adversary: dict[str, int] = {}
    for c in phase1_concerns:
        by_adversary[c.adversary] = by_adversary.get(c.adversary, 0) + 1

    lines.append("Phase 1 - Attack Generation:")
    for adv, count in sorted(by_adversary.items()):
        lines.append(f"  {adv}: {count} concerns")
    lines.append(f"  Total: {len(phase1_concerns)} raw concerns")
    lines.append(f"  Post-filter concerns: {len(result.concerns)}")
    if result.clustered_concerns is not None:
        merged = len(result.concerns) - len(result.clustered_concerns)
        lines.append(f"  Clustered for evaluation: {len(result.clustered_concerns)} ({max(0, merged)} merged)")
    lines.append("")

    # Phase 4 summary
    phase4_evals = result.clustered_evaluations if result.clustered_evaluations is not None else result.evaluations
    dismissed = [e for e in phase4_evals if e.verdict == "dismissed"]
    accepted = [e for e in phase4_evals if e.verdict == "accepted"]
    acknowledged = [e for e in phase4_evals if e.verdict == "acknowledged"]
    deferred = [e for e in phase4_evals if e.verdict == "deferred"]

    lines.append(f"Phase 4 - Evaluation ({result.eval_model}):")
    lines.append(f"  Dismissed: {len(dismissed)} (with justification)")
    lines.append(f"  Accepted: {len(accepted)} (spec revision needed)")
    lines.append(f"  Acknowledged: {len(acknowledged)} (valid but out of scope)")
    lines.append(f"  Deferred: {len(deferred)} (need more context)")
    if result.clustered_evaluations is not None and len(result.evaluations) != len(result.clustered_evaluations):
        lines.append(f"  Attributed evaluations for stats: {len(result.evaluations)}")
    lines.append("")

    # Phase 5 summary
    if result.rebuttals:
        sustained = [r for r in result.rebuttals if r.sustained]
        lines.append("Phase 5 - Rebuttals:")
        lines.append(f"  Challenges: {len(sustained)} (of {len(result.rebuttals)} dismissals)")
        lines.append("")

    # Phase 7 summary (Final Boss)
    if result.final_boss_result:
        lines.append(f"Phase 7 - Final Boss UX Review ({result.final_boss_result.model}):")
        verdict = result.final_boss_result.verdict
        if verdict == FinalBossVerdict.PASS:
            lines.append("  VERDICT: PASS - User story is sound")
            first_line = result.final_boss_result.response.split("\n")[0][:80]
            lines.append(f"  {first_line}")
        elif verdict == FinalBossVerdict.REFINE:
            lines.append(f"  VERDICT: REFINE - {len(result.final_boss_result.concerns)} concerns to address")
            for concern in result.final_boss_result.concerns[:3]:
                text = concern[:70] + "..." if len(concern) > 70 else concern
                lines.append(f"    - {text}")
        elif verdict == FinalBossVerdict.RECONSIDER:
            lines.append("  VERDICT: RECONSIDER - Fundamental issues detected")
            lines.append(f"  Reason: {result.final_boss_result.reconsider_reason[:80]}")
            lines.append("  Alternate approaches to evaluate:")
            for alt in result.final_boss_result.alternate_approaches[:3]:
                text = alt[:70] + "..." if len(alt) > 70 else alt
                lines.append(f"    - {text}")

        # Dismissal review telemetry
        stats = result.final_boss_result.dismissal_review_stats
        if stats and stats.dismissed_simplifications_reviewed > 0:
            lines.append(f"  Dismissal Review: {stats.dismissed_simplifications_reviewed} simplifications reviewed")
            lines.append(f"    Invalid dismissals found: {stats.dismissals_flagged_invalid}")
            yield_pct = stats.review_yield_rate * 100
            if yield_pct > 0:
                lines.append(f"    Yield rate: {yield_pct:.0f}% (>20% suggests dismissal process needs audit)")
            else:
                lines.append("    Yield rate: 0% (consider skipping dismissal review to save tokens)")

        # Meta-reports for process improvement
        if result.final_boss_result.process_meta_report:
            lines.append("")
            lines.append("  --- Process Meta-Report ---")
            lines.append(f"  {result.final_boss_result.process_meta_report[:200]}")
        if result.final_boss_result.self_meta_report:
            lines.append("")
            lines.append("  --- Self Meta-Report ---")
            lines.append(f"  {result.final_boss_result.self_meta_report[:200]}")
        lines.append("")

    # Final verdict
    ux_concerns = [c for c in result.final_concerns if c.adversary == "ux_architect"]
    technical_concerns = [c for c in result.final_concerns if c.adversary != "ux_architect"]

    lines.append("Final Verdict:")
    if technical_concerns:
        lines.append(f"  Technical concerns: {len(technical_concerns)}")
        for c in technical_concerns:
            text = c.text[:80] + "..." if len(c.text) > 80 else c.text
            lines.append(f"    - [{c.adversary}] {text}")

    if ux_concerns:
        lines.append(f"  UX concerns: {len(ux_concerns)}")
        for c in ux_concerns:
            text = c.text[:80] + "..." if len(c.text) > 80 else c.text
            lines.append(f"    - [{c.adversary}] {text}")

    if not result.final_concerns:
        lines.append("  No concerns - spec is ready for implementation!")

    # Medal awards (if any were given during this run)
    if hasattr(result, 'medals') and result.medals:
        lines.append(format_medals_for_display(result.medals))

    return "\n".join(lines)


# =============================================================================
# CLI ENTRY POINT
# =============================================================================


def main():
    """CLI entry point for standalone gauntlet runs."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run adversarial gauntlet on a specification"
    )
    parser.add_argument(
        "--adversaries",
        default="all",
        help="Comma-separated list of adversaries or 'all' (default: all)",
    )
    parser.add_argument(
        "--adversary-model",
        help="Model for adversary attacks (default: auto-select free)",
    )
    parser.add_argument(
        "--attack-models",
        help="Comma-separated models for adversary attacks (overrides --adversary-model)",
    )
    parser.add_argument(
        "--eval-model",
        help="Model for evaluation (default: auto-select frontier)",
    )
    parser.add_argument(
        "--no-rebuttals",
        action="store_true",
        help="Skip rebuttal phase",
    )
    parser.add_argument(
        "--attack-codex-reasoning",
        default="low",
        choices=["minimal", "low", "medium", "high", "xhigh"],
        help="Codex reasoning effort for attacks (default: low, saves tokens)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout per model call in seconds (default: 300)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--list-adversaries",
        action="store_true",
        help="List available adversaries and exit",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show adversary performance statistics and exit",
    )
    parser.add_argument(
        "--list-runs",
        type=int,
        nargs="?",
        const=10,
        metavar="N",
        help="List recent gauntlet runs (default: 10) and exit",
    )
    parser.add_argument(
        "--show-run",
        metavar="FILENAME",
        help="Show details of a specific run by filename",
    )
    parser.add_argument(
        "--pre-gauntlet",
        action="store_true",
        help="Run pre-gauntlet compatibility checks before adversary attacks",
    )
    parser.add_argument(
        "--doc-type",
        choices=["prd", "tech", "debug"],
        default="tech",
        help="Document type for pre-gauntlet checks (default: tech)",
    )
    parser.add_argument(
        "--spec-file",
        metavar="PATH",
        help="Read spec from file instead of stdin",
    )
    parser.add_argument(
        "--report-path",
        metavar="PATH",
        help="Path to save pre-gauntlet report (default: .adversarial-spec/pre_gauntlet_report.json)",
    )

    args = parser.parse_args()

    if args.stats:
        print(get_adversary_leaderboard())
        return

    if args.list_runs is not None:
        print(list_gauntlet_runs(args.list_runs))
        return

    if args.show_run:
        run_data = load_gauntlet_run(args.show_run)
        if run_data:
            print(json.dumps(run_data, indent=2))
        else:
            print(f"Run not found: {args.show_run}", file=sys.stderr)
            sys.exit(1)
        return

    if args.list_adversaries:
        print("Available adversaries:\n")
        for name, adversary in ADVERSARIES.items():
            first_line = adversary.persona.strip().split("\n")[0][:60]
            print(f"  {name:20} {first_line}...")
        return

    # Read spec from file or stdin
    if args.spec_file:
        try:
            with open(args.spec_file, "r") as f:
                spec = f.read().strip()
        except FileNotFoundError:
            print(f"Error: Spec file not found: {args.spec_file}", file=sys.stderr)
            sys.exit(1)
    else:
        spec = sys.stdin.read().strip()

    if not spec:
        print("Error: No spec provided", file=sys.stderr)
        sys.exit(1)

    # Run pre-gauntlet if requested
    if args.pre_gauntlet:
        try:
            from pathlib import Path

            from pre_gauntlet import (
                PreGauntletStatus,
                get_exit_code,
                run_pre_gauntlet,
                save_report,
            )

            print("=== Pre-Gauntlet Compatibility Check ===", file=sys.stderr)

            pre_result = run_pre_gauntlet(
                spec_text=spec,
                doc_type=args.doc_type,
                repo_root=Path.cwd(),
                interactive=sys.stdin.isatty(),
            )

            # Save report
            report_path = Path(args.report_path) if args.report_path else Path(".adversarial-spec/pre_gauntlet_report.json")
            save_report(pre_result, report_path)
            print(f"Pre-gauntlet report saved: {report_path}", file=sys.stderr)

            # Print summary
            print(f"Status: {pre_result.status.value}", file=sys.stderr)
            print(f"Concerns: {len(pre_result.concerns)} ({len(pre_result.get_blockers())} blockers)", file=sys.stderr)
            print(f"Timings: git={pre_result.timings.git_ms}ms, build={pre_result.timings.build_ms}ms, total={pre_result.timings.total_ms}ms", file=sys.stderr)

            # Check if we should proceed
            if pre_result.status != PreGauntletStatus.COMPLETE:
                print("\nPre-gauntlet did not complete successfully. Exiting.", file=sys.stderr)
                sys.exit(get_exit_code(pre_result.status))

            # Use the context-enriched spec for gauntlet
            spec = pre_result.context_markdown
            print("\nProceeding to adversarial gauntlet...\n", file=sys.stderr)

        except ImportError as e:
            print(f"Warning: Pre-gauntlet module not available: {e}", file=sys.stderr)
            print("Proceeding without pre-gauntlet checks.", file=sys.stderr)

    # Parse adversaries
    adversaries = None
    if args.adversaries != "all":
        adversaries = [a.strip() for a in args.adversaries.split(",")]

    attack_models = None
    if args.attack_models:
        attack_models = [m.strip() for m in args.attack_models.split(",") if m.strip()]

    legacy_attack_model = args.adversary_model
    if attack_models is not None:
        legacy_attack_model = None

    # Run gauntlet
    result = run_gauntlet(
        spec=spec,
        adversaries=adversaries,
        adversary_model=legacy_attack_model,
        attack_models=attack_models,
        eval_models=[args.eval_model] if args.eval_model else None,
        allow_rebuttals=not args.no_rebuttals,
        timeout=args.timeout,
        attack_codex_reasoning=args.attack_codex_reasoning,
    )

    # Output
    if args.json:
        output = {
            "concerns": [
                {
                    "id": c.id,
                    "adversary": c.adversary,
                    "source_model": c.source_model,
                    "text": c.text,
                }
                for c in result.concerns
            ],
            "evaluations": [
                {
                    "concern": {
                        "id": e.concern.id,
                        "adversary": e.concern.adversary,
                        "source_model": e.concern.source_model,
                        "text": e.concern.text,
                    },
                    "verdict": e.verdict,
                    "reasoning": e.reasoning,
                }
                for e in result.evaluations
            ],
            "final_concerns": [
                {"adversary": c.adversary, "text": c.text} for c in result.final_concerns
            ],
            "adversary_model": result.adversary_model,
            "eval_model": result.eval_model,
            "total_time": result.total_time,
            "total_cost": result.total_cost,
        }
        if result.clustered_concerns is not None:
            output["clustered_concerns"] = [
                {
                    "id": c.id,
                    "adversary": c.adversary,
                    "source_model": c.source_model,
                    "text": c.text,
                }
                for c in result.clustered_concerns
            ]
        print(json.dumps(output, indent=2))
    else:
        print()
        print(format_gauntlet_report(result))


if __name__ == "__main__":
    main()
