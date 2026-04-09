"""Core data types for the gauntlet pipeline.

Extracted from gauntlet_monolith.py — all dataclasses, enums, and verdict
normalization live here. No side effects, no I/O, no imports from other
gauntlet modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from adversaries import ADVERSARIES, generate_concern_id

# =============================================================================
# ERROR CLASSIFICATION
# =============================================================================

# Programming bugs that must NEVER be swallowed by except-Exception blocks.
# These indicate real code defects, not transient operational failures.
# Excludes ValueError and KeyError — those often come from malformed API responses.
PROGRAMMING_BUGS = (TypeError, NameError, AttributeError, ImportError, SyntaxError, AssertionError)

# =============================================================================
# SYNTHESIS TAXONOMY
# =============================================================================


SYNTHESIS_CATEGORIES: list[str] = [
    "Correctness Bugs",
    "Race Conditions",
    "Failure Modes",
    "Security",
    "Operability",
    "Scalability",
    "Design Debt",
    "Underspecification",
]


# =============================================================================
# ENUMS
# =============================================================================


class FinalBossVerdict(str, Enum):
    """Verdict from the Final Boss review."""
    PASS = "pass"           # Proceed to implementation
    REFINE = "refine"       # Address concerns, then proceed
    RECONSIDER = "reconsider"  # Re-evaluate approach before proceeding


# =============================================================================
# VERDICT NORMALIZATION
# =============================================================================


_VERDICT_NORMALIZE = {
    "dismiss": "dismissed",
    "dismissed": "dismissed",
    "reject": "dismissed",
    "accept": "accepted",
    "accepted": "accepted",
    "acknowledge": "acknowledged",
    "acknowledged": "acknowledged",
    "defer": "deferred",
    "deferred": "deferred",
}


def normalize_verdict(raw: str) -> str:
    """Map raw verdict strings to canonical forms."""
    return _VERDICT_NORMALIZE.get(raw.lower().strip(), "deferred")


# =============================================================================
# CORE DATACLASSES
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
    severity: str = ""  # high, medium, low — assigned by eval model, not attack model

    def __post_init__(self):
        self.verdict = normalize_verdict(self.verdict)
        if self.severity not in ("high", "medium", "low"):
            self.severity = self.concern.severity  # fallback to attack-assigned


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


@dataclass
class ExplanationMatch:
    """Result of matching a concern against resolved explanations."""
    explanation: dict
    confidence: float
    reason: str
    action: str  # "accept", "note", "ignore"


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
    final_boss_result: Optional[FinalBossResult] = None  # Phase 7 result
    raw_concerns: Optional[list[Concern]] = None  # Pre-filtering concerns (all generated)
    dropped_concerns: Optional[list[Concern]] = None  # Concerns dropped by filtering
    spec_hash: Optional[str] = None  # Hash of the spec that was reviewed
    adversary_timing: Optional[dict[str, float]] = None  # Time per adversary in seconds
    big_picture: Optional[BigPictureSynthesis] = None  # Holistic concern analysis
    clustered_concerns: Optional[list[Concern]] = None  # Concerns evaluated after dedup
    clustered_evaluations: Optional[list[Evaluation]] = None  # One evaluation per cluster representative
    cluster_members: Optional[dict[str, list[Concern]]] = None  # representative concern id -> member concerns
    concerns_path: Optional[str] = None  # Path to saved concerns JSON

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

            # Concern length stats
            concern_lengths = [len(c.text) for c in adv_concerns]
            avg_concern_length = sum(concern_lengths) / len(concern_lengths) if concern_lengths else 0

            # Rebuttal success by severity
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
            d = {
                "concern": concern_to_dict(e.concern),
                "verdict": e.verdict,
                "reasoning": e.reasoning,
            }
            if e.severity:
                d["severity"] = e.severity
            return d

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

        if self.concerns_path:
            result["concerns_path"] = self.concerns_path

        return result


# =============================================================================
# NEW: Configuration and error types (QUOTA BURN FIXES)
# =============================================================================


@dataclass
class GauntletConfig:
    """Central configuration object passed to every phase function.

    Replaces 13 hardcoded timeout/reasoning defaults scattered across the monolith.
    Built once at the top of run_gauntlet() from CLI parameters.

    QUOTA BURN FIX 1: This is the primary fix for ignored CLI flags.
    """
    timeout: int = 300
    attack_codex_reasoning: str = "low"
    eval_codex_reasoning: str = "xhigh"
    auto_checkpoint: bool = False
    resume: bool = False
    unattended: bool = False


class GauntletClusteringError(Exception):
    """Raised when Phase 3 clustering fails after retry.

    Halts pipeline — NO silent fallback to singleton clusters.
    QUOTA BURN FIX 2.
    """
    pass


class GauntletExecutionError(Exception):
    """Raised when any phase fails in a way that should halt with exit code 3."""
    pass


@dataclass
class CheckpointMeta:
    """Metadata envelope for checkpoint files."""
    schema_version: int = 2
    spec_hash: str = ""
    config_hash: str = ""
    phase: str = ""
    created_at: str = ""
    data_hash: str = ""


@dataclass
class PhaseMetrics:
    """Per-phase telemetry for the run manifest.

    Replaces the write-only dedup-stats.json.
    QUOTA BURN FIX 4.
    """
    phase: str
    phase_index: int
    status: str  # "completed" | "failed" | "skipped_resume"
    duration_seconds: float
    input_tokens: int
    output_tokens: int
    models_used: list[str]
    config_snapshot: dict
    error: Optional[str] = None
    spec_hash: str = ""
