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
    cat spec.md | python3 debate.py critique --models codex/gpt-5.2-codex --gauntlet
"""

from __future__ import annotations

import concurrent.futures
import json
import sys
import time
from dataclasses import dataclass
from typing import Optional

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
# ADVERSARY PERSONAS
# =============================================================================
# These are intentionally aggressive and may be wrong. That's the point.

ADVERSARIES = {
    "paranoid_security": """You see threats EVERYWHERE. Every input is malicious. Every
dependency will be compromised. Every user is trying to hack the system. You assume
the absolute worst about everything. Most of your concerns are overblown, but
occasionally you catch something everyone else missed because they weren't paranoid enough.

Find security holes. Assume attackers are clever and persistent.

Output your concerns as a numbered list. For each concern:
- State the threat clearly
- Explain the attack vector
- Note potential impact""",
    "burned_oncall": """You've been paged at 3am too many times. You're OBSESSED with
failure modes. "What happens when Redis goes down?" "What if this times out?"
"Where's the circuit breaker?" You don't trust anything to stay up. You've seen
too much.

Find operational gaps. Assume every dependency will fail at the worst time.

Output your concerns as a numbered list. For each concern:
- State the failure mode
- Explain how operators will find out (or won't)
- Note the blast radius""",
    "lazy_developer": """This is too complicated. Why can't we just use X? Do we REALLY
need all this? You push back on complexity because you're the one who'll have to
maintain this crap. Sometimes you're just being lazy, but sometimes you catch
genuine overengineering.

Find unnecessary complexity. Assume simpler solutions exist.

Output your concerns as a numbered list. For each concern:
- Quote the complex part
- Suggest a simpler alternative
- Explain why simpler would work""",
    "pedantic_nitpicker": """You find edge cases nobody thought of. What if the string
is empty? What if there are exactly 2^31 items? What about Unicode? What about leap
seconds? Annoying but thorough. Most of your concerns don't matter, but some do.

Find edge cases. Assume every boundary condition will be hit.

Output your concerns as a numbered list. For each concern:
- State the edge case
- Explain how it could occur in production
- Note the consequence""",
    "asshole_loner": """You are a complete asshole antisocial engineer who usually works
alone and is annoyed to have to work in a team. You frequently jump to conclusions
on how a design is bad. You have a lot of experience and can point out flaws that
others miss, but you aren't really THAT careful and focus instead on creating a
problem. When shown good reasoning, you don't raise issues just to do so, but you
are blunt when you see any weakness.

Find design flaws. Trust logic, not authority or process.

Output your concerns as a numbered list. Be blunt and direct.
- State what's broken
- Explain why it's broken
- Don't sugarcoat it""",
}

# =============================================================================
# FINAL BOSS ADVERSARY (runs after all others, uses Opus 4.5)
# =============================================================================

FINAL_BOSS = {
    "ux_architect": """You are a Senior High-Level Full Stack and UX Engineer, Tester, and
User-Story Architect with 20+ years of experience shipping products that users love.

You're reviewing this spec AFTER it has already passed through security review, operational
review, complexity review, edge case analysis, and design review. All technical concerns
have been addressed. All models are in agreement.

Your job is to step back and ask: **Did we lose the forest for the trees?**

Consider these questions deeply:

1. USER STORY: What is the actual user story here? What problem are we solving?
   Is the user genuinely better off after this change? Or did we just add complexity
   that doesn't serve them?

2. EXPERIENCE DELTA: How does the user's experience change after this spec is implemented?
   Walk through it step by step. Is this actually an improvement they'll notice and appreciate?

3. DEVELOPER EXPERIENCE: If this affects other developers, is their experience improved?
   Will they understand this? Will it make their lives easier or harder?

4. MEASUREMENT: Do we have the logging, metrics, and testing set up to know if these
   changes are actually helping? How will we know if this was a success or failure?
   What's the rollback plan if users hate it?

5. COHERENCE: Does this tie into the broader product direction? Does it unlock future
   improvements or paint us into a corner? Are we building foundations or technical debt?

6. LOST IN THE WEEDS: Did the technical debates distract from the actual goal? Are we
   implementing something clever that doesn't actually matter to users? Would a user
   look at this and say "who asked for this?"

You should RARELY find issues at this stage - that's the whole point of the gauntlet!
But if the spec has fundamental UX problems that got lost in technical discussions,
NOW is the time to catch them before implementation.

Output format:
- If no concerns: "APPROVED: [brief explanation of why the user story is sound]"
- If concerns exist: List them with:
  - The user impact (not technical impact)
  - Why this matters to real humans
  - Suggested reconsideration (not necessarily a fix - maybe the whole approach is wrong)"""
}

FINAL_BOSS_RESPONSE_PROTOCOL = {
    "ux_architect": {
        "valid_dismissal": """
The ux_architect's concern may be dismissed IF:
- The user impact is clearly documented and accepted as a tradeoff
- The concern conflates user impact with developer preference
- The measurement strategy is already defined elsewhere
- The concern assumes a user journey that doesn't match reality
""",
        "invalid_dismissal": """
Do NOT dismiss ux_architect's concern with:
- "Users won't notice" (how do you know?)
- "It's technically correct" (correctness != good UX)
- "We can fix it later" (UX debt is real debt)
- "The spec says X" (specs can be wrong about what users want)
""",
        "rule": "If you can't explain the user benefit in one sentence, reconsider.",
    }
}


# =============================================================================
# RESPONSE PROTOCOLS
# =============================================================================
# Evaluation criteria so the frontier model knows how to properly adjudicate.

ADVERSARY_RESPONSE_PROTOCOLS = {
    "paranoid_security": {
        "valid_dismissal": """
You may dismiss paranoid_security's concern IF you can cite specifically:
- "This attack is prevented by [feature] at [file:line]"
- "This requires [physical access / internal network / admin creds] which is out of scope"
- "The attack surface doesn't exist because [specific architectural reason]"
""",
        "invalid_dismissal": """
Do NOT accept these as valid dismissals:
- "It's unlikely" (how unlikely? what's the impact if it happens?)
- "We'll fix it later" (when? what's the trigger?)
- "That's paranoid" (that's literally their job)
""",
        "valid_acceptance": """
Accept paranoid_security's concern IF:
- No existing mitigation can be cited
- The attack vector is plausible given the deployment context
- Impact would be significant (data breach, privilege escalation, etc.)
""",
        "rule": "If you cannot cite a specific mitigation, the concern stands.",
    },
    "burned_oncall": {
        "valid_dismissal": """
You may dismiss burned_oncall's concern IF:
- "Existing [circuit breaker / retry / fallback] handles this at [location]"
- "This service is not on-call critical (batch job, async, etc.)"
- "Failure here degrades gracefully to [fallback behavior]"
""",
        "invalid_dismissal": """
Do NOT accept these as valid dismissals:
- "It should be fine" (how do you know?)
- "We'll add monitoring later" (when?)
- "That service never goes down" (famous last words)
""",
        "valid_acceptance": """
Accept burned_oncall's concern IF:
- No existing error handling for external dependency
- Silent failures that won't be detected
- Missing observability on critical path
""",
        "rule": "If dismissing, explain how operators WILL know when this fails.",
    },
    "lazy_developer": {
        "valid_dismissal": """
You may dismiss lazy_developer's concern IF:
- "Complexity is necessary because [specific requirement that demands it]"
- "Simpler approach was tried and failed because [specific reason]"
- "This complexity is encapsulated in [module] and won't leak"
""",
        "invalid_dismissal": """
Do NOT accept these as valid dismissals:
- "We might need it later" (YAGNI)
- "It's the standard way" (doesn't mean it's needed here)
- "It's not that complex" (complexity is relative to need)
""",
        "valid_acceptance": """
Accept lazy_developer's concern IF:
- Cannot articulate WHY the complexity is needed
- "We might need it later" (YAGNI violation)
- Complexity serves only one use case
""",
        "rule": "If you can't justify the complexity in one sentence, simplify.",
    },
    "pedantic_nitpicker": {
        "valid_dismissal": """
You may dismiss pedantic_nitpicker's concern IF:
- "Edge case impact is [X], fix cost is [Y], not worth it. Add log instead."
- "This is handled by [framework/library] automatically at [location]"
- "Probability is [N], blast radius is [M users], acceptable risk"
""",
        "invalid_dismissal": """
Do NOT accept these as valid dismissals:
- "That'll never happen" (it will)
- "Users won't do that" (they will)
- "It's too unlikely" (quantify it or accept)
""",
        "valid_acceptance": """
Accept pedantic_nitpicker's concern IF:
- Data corruption possible -> always fix
- Security implication -> always fix
- Simple fix (< 10 lines) -> usually fix
""",
        "rule": "Propose proportional response: sometimes 'add a log' beats 'handle elegantly'.",
    },
    "asshole_loner": {
        "valid_dismissal": """
You may dismiss asshole_loner's concern IF:
- Show the reasoning they missed: "Actually, [X] handles this because [Y]"
- They respect LOGIC, not process. Show your work.
- Cite specific code or design decisions that address their point
""",
        "invalid_dismissal": """
Do NOT accept these as valid dismissals:
- "That's not how we do things here" (appeal to convention)
- "The team decided" (appeal to authority)
- "It's the standard practice" (not relevant if it doesn't work)
""",
        "valid_acceptance": """
Accept asshole_loner's concern IF:
- The logical flaw they identified is real
- The design decision cannot be justified with reasoning
- Their experience-based intuition reveals a real gap
""",
        "rule": "They accept good reasoning without argument. Just prove it.",
    },
}


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


@dataclass
class Evaluation:
    """Frontier model's evaluation of a concern."""

    concern: Concern
    verdict: str  # dismissed, accepted, deferred
    reasoning: str


@dataclass
class Rebuttal:
    """Adversary's response to a dismissal."""

    evaluation: Evaluation
    response: str
    sustained: bool  # True if challenge was successful


@dataclass
class GauntletResult:
    """Complete result of running the gauntlet."""

    concerns: list[Concern]  # Post-filtering concerns that were evaluated
    evaluations: list[Evaluation]
    rebuttals: list[Rebuttal]
    final_concerns: list[Concern]  # Concerns that survived (technical + UX)
    adversary_model: str
    eval_model: str
    total_time: float
    total_cost: float
    final_boss_result: Optional["FinalBossResult"] = None  # Phase 5 result
    raw_concerns: Optional[list[Concern]] = None  # Pre-filtering concerns (all generated)
    dropped_concerns: Optional[list[Concern]] = None  # Concerns dropped by filtering
    spec_hash: Optional[str] = None  # Hash of the spec that was reviewed

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
            dismissed = len([e for e in adv_evals if e.verdict == "dismissed"])
            deferred = len([e for e in adv_evals if e.verdict == "deferred"])
            rebuttals_won = len([r for r in adv_rebuttals if r.sustained])
            rebuttals_lost = len([r for r in adv_rebuttals if not r.sustained])

            total = len(adv_concerns)
            acceptance_rate = accepted / total if total > 0 else 0.0

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

            stats[adv] = {
                "concerns_raised": total,
                "accepted": accepted,
                "dismissed": dismissed,
                "deferred": deferred,
                "acceptance_rate": round(acceptance_rate, 3),
                "rebuttals_won": rebuttals_won,
                "rebuttals_lost": rebuttals_lost,
                "dismissal_effort": round(dismissal_effort, 0),  # avg chars
                "signal_score": round(signal_score, 3),
            }

        return stats

    def to_dict(self) -> dict:
        """Serialize the gauntlet result to a dictionary for JSON storage."""

        def concern_to_dict(c: Concern) -> dict:
            return {"adversary": c.adversary, "text": c.text, "severity": c.severity}

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
        }

        if self.final_boss_result:
            result["final_boss"] = {
                "approved": self.final_boss_result.approved,
                "response": self.final_boss_result.response,
                "concerns": self.final_boss_result.concerns,
                "model": self.final_boss_result.model,
                "tokens_used": self.final_boss_result.tokens_used,
            }

        return result


# =============================================================================
# ADVERSARY STATS PERSISTENCE
# =============================================================================

from pathlib import Path
from datetime import datetime

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

    # Update model stats
    for model, role in [(result.adversary_model, "adversary"), (result.eval_model, "evaluation")]:
        if model not in stats["models"]:
            stats["models"][model] = {
                "role": role,
                "runs": 0,
                "total_cost": 0.0,
            }
        stats["models"][model]["runs"] += 1
        stats["models"][model]["total_cost"] += result.total_cost

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
        lines.append(
            f"     {rate:.0f}% accepted ({accepted}/{total}), {effort:.0f} chars avg dismissal"
        )

    # Acceptance rate for comparison
    lines.append("")
    lines.append("By Acceptance Rate (raw % of concerns that were valid):")

    sorted_acceptance = sorted(
        stats["adversaries"].items(),
        key=lambda x: x[1].get("acceptance_rate", 0),
        reverse=True,
    )

    for i, (adv, data) in enumerate(sorted_acceptance, 1):
        rate = data.get("acceptance_rate", 0) * 100
        total = data.get("concerns_raised", 0)
        accepted = data.get("accepted", 0)
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
# FINAL BOSS REVIEW (Phase 5)
# =============================================================================

@dataclass
class FinalBossResult:
    """Result from the final boss UX review."""
    approved: bool
    response: str
    concerns: list[str]  # Empty if approved
    model: str
    tokens_used: int


def run_final_boss_review(
    spec: str,
    gauntlet_summary: str,
    timeout: int = 600,
) -> FinalBossResult:
    """
    Phase 5: Final Boss UX/User Story Review.

    Runs AFTER all other adversaries have been satisfied. Uses Opus 4.5 to do
    a high-level sanity check on whether the spec actually serves users.

    Args:
        spec: The specification being reviewed
        gauntlet_summary: Summary of what the gauntlet found and how it was addressed
        timeout: Timeout (longer for Opus)

    Returns:
        FinalBossResult with approval status and any concerns
    """
    import os

    # Final boss uses Opus 4.5 - expensive but thorough
    # Check for Claude Code first (uses subscription)
    if os.environ.get("ANTHROPIC_API_KEY"):
        model = "claude-opus-4-5-20250514"
    else:
        # Fall back to best available
        print("  Warning: Opus 4.5 not available, using best alternative", file=sys.stderr)
        if CODEX_AVAILABLE:
            model = "codex/gpt-5.2-codex"
        elif os.environ.get("OPENAI_API_KEY"):
            model = "gpt-4o"
        else:
            model = select_eval_model()

    system_prompt = FINAL_BOSS["ux_architect"]

    user_prompt = f"""## SPECIFICATION TO REVIEW

{spec}

## GAUNTLET RESULTS

This spec has already passed through the adversarial gauntlet:

{gauntlet_summary}

All technical concerns have been addressed. All models reached consensus.

## YOUR TASK

Step back from the technical details. Consider the USER EXPERIENCE.

1. What is the user story? Is this user actually better off?
2. How does their experience change? Walk through it.
3. Do we have measurement in place to know if this helps?
4. Did we get lost in technical weeds and forget the user?

If everything looks good: "APPROVED: [brief reason]"
If you have concerns: List them with user impact and suggested reconsideration."""

    try:
        response, in_tokens, out_tokens = call_model(
            model=model,
            system_prompt=system_prompt,
            user_message=user_prompt,
            timeout=timeout,
        )
        cost_tracker.add(model, in_tokens, out_tokens)

        # Parse response
        response_upper = response.upper()
        approved = "APPROVED:" in response_upper

        concerns = []
        if not approved:
            # Extract concerns from response
            for line in response.split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-") or line.startswith("•")):
                    text = line.lstrip("0123456789.-•) ").strip()
                    if text and len(text) > 20:  # Filter out headers
                        concerns.append(text)

        return FinalBossResult(
            approved=approved,
            response=response.strip(),
            concerns=concerns,
            model=model,
            tokens_used=in_tokens + out_tokens,
        )

    except Exception as e:
        print(f"  Warning: Final boss review failed: {e}", file=sys.stderr)
        # On failure, don't block - just note it
        return FinalBossResult(
            approved=True,
            response=f"Review failed: {e}. Proceeding with caution.",
            concerns=[],
            model=model,
            tokens_used=0,
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
        models.append("codex/gpt-5.2-codex")
    if GEMINI_CLI_AVAILABLE:
        models.append("gemini-cli/gemini-3-pro-preview")

    # Only add paid API models if we need more models for consensus
    # We want 2-3 models for good consensus, but free is better
    if len(models) < 2:
        if os.environ.get("OPENAI_API_KEY"):
            models.append("gpt-4o")
        if len(models) < 2 and os.environ.get("ANTHROPIC_API_KEY"):
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
    Phase 2: Evaluate concerns using MULTIPLE models in parallel.

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

    # Last resort
    if os.environ.get("OPENAI_API_KEY"):
        return "gpt-4o-mini"

    raise RuntimeError(
        "No model available for adversaries. Install Gemini CLI (free) or set an API key."
    )


def select_eval_model() -> str:
    """
    Select model for evaluation (Phase 2 & 4).
    Priority: FREE frontier CLI tools, then strongest API.

    Evaluation needs to be rigorous - use the best available.
    """
    # Codex CLI is free with ChatGPT subscription and is frontier quality
    if CODEX_AVAILABLE:
        return "codex/gpt-5.2-codex"

    # Gemini CLI Pro is also frontier quality
    if GEMINI_CLI_AVAILABLE:
        return "gemini-cli/gemini-3-pro-preview"

    # Fall back to strongest available API
    import os

    if os.environ.get("OPENAI_API_KEY"):
        return "gpt-4o"
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
    model: str,
    timeout: int = 300,
) -> list[Concern]:
    """
    Phase 1: Generate attacks from all adversary personas in parallel.

    Args:
        spec: The specification to attack
        adversaries: List of adversary keys to use
        model: Model to use for attack generation
        timeout: Timeout per adversary call

    Returns:
        List of Concern objects
    """
    concerns: list[Concern] = []

    def run_adversary(adversary_key: str) -> list[Concern]:
        persona = ADVERSARIES.get(adversary_key)
        if not persona:
            print(f"Warning: Unknown adversary '{adversary_key}'", file=sys.stderr)
            return []

        system_prompt = f"""You are an adversarial reviewer with this persona:

{persona}

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
            )
            cost_tracker.add(model, in_tokens, out_tokens)

            # Parse concerns from response
            local_concerns = []
            for line in response.split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-")):
                    # Remove leading number/dash
                    text = line.lstrip("0123456789.-) ").strip()
                    if text:
                        local_concerns.append(
                            Concern(adversary=adversary_key, text=text)
                        )

            return local_concerns

        except Exception as e:
            print(
                f"Warning: Adversary {adversary_key} failed: {e}",
                file=sys.stderr,
            )
            return []

    # Run adversaries in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(adversaries)) as executor:
        futures = {
            executor.submit(run_adversary, adv): adv for adv in adversaries
        }
        for future in concurrent.futures.as_completed(futures):
            concerns.extend(future.result())

    return concerns


# =============================================================================
# PHASE 2: STRUCTURED EVALUATION
# =============================================================================


def evaluate_concerns(
    spec: str,
    concerns: list[Concern],
    model: str,
    timeout: int = 300,
) -> list[Evaluation]:
    """
    Phase 2: Evaluate each concern using the frontier model.

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

    # Build response protocol reference
    protocols_text = ""
    for adv_key in set(c.adversary for c in concerns):
        protocol = ADVERSARY_RESPONSE_PROTOCOLS.get(adv_key, {})
        protocols_text += f"\n### When evaluating {adv_key}:\n"
        protocols_text += f"Valid dismissal: {protocol.get('valid_dismissal', 'Use your judgment')}\n"
        protocols_text += f"Invalid dismissal: {protocol.get('invalid_dismissal', 'Be careful of handwaving')}\n"
        protocols_text += f"Rule: {protocol.get('rule', 'Be rigorous')}\n"

    system_prompt = f"""You are a senior engineer evaluating concerns raised by adversarial reviewers.

For each concern, you must decide:
- DISMISS: The concern is not valid (must cite specific evidence)
- ACCEPT: The concern is valid (spec needs revision)
- DEFER: Need more context to decide

RESPONSE PROTOCOLS:{protocols_text}

CRITICAL RULES:
1. No emotional language - just logic and evidence
2. For DISMISS: You MUST cite specific reasons from the spec or architecture
3. For ACCEPT: Briefly note what needs to change
4. For DEFER: Note what information is missing

Output your evaluation as JSON with this structure:
{{
  "evaluations": [
    {{"concern_index": 0, "verdict": "dismissed|accepted|deferred", "reasoning": "..."}},
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
    Phase 3: Allow adversaries to rebut dismissals.

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
        persona = ADVERSARIES.get(adversary_key, "")

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
    Phase 4: Final adjudication of challenged dismissals.

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
    eval_models: Optional[list[str]] = None,
    allow_rebuttals: bool = True,
    use_multi_model: bool = True,
    skip_filtering: bool = False,
    run_final_boss: bool = False,
    timeout: int = 300,
) -> GauntletResult:
    """
    Run the full adversarial gauntlet on a specification.

    Args:
        spec: The specification to review
        adversaries: List of adversary keys (default: all)
        adversary_model: Model for adversaries (default: auto-select free)
        eval_models: Models for evaluation (default: auto-select multiple)
        allow_rebuttals: Whether to run rebuttal phase
        use_multi_model: Use multiple models for evaluation consensus
        skip_filtering: Skip filtering against resolved concerns
        run_final_boss: Run Phase 5 Final Boss UX review (expensive, uses Opus 4.5)
        timeout: Timeout per model call

    Returns:
        GauntletResult with all phases' outputs
    """
    start_time = time.time()
    spec_hash = get_spec_hash(spec)

    # Select models
    if adversary_model is None:
        adversary_model = select_adversary_model()

    if eval_models is None:
        if use_multi_model:
            eval_models = get_available_eval_models()[:3]  # Up to 3 models
        else:
            eval_models = [select_eval_model()]

    # Default to all adversaries
    if adversaries is None:
        adversaries = list(ADVERSARIES.keys())

    print(f"=== Adversarial Gauntlet ===", file=sys.stderr)
    print(f"Adversaries: {', '.join(adversaries)}", file=sys.stderr)
    print(f"Attack model: {adversary_model}", file=sys.stderr)
    print(f"Eval models: {', '.join(eval_models)}", file=sys.stderr)
    print(file=sys.stderr)

    # Phase 1: Attack Generation (parallel)
    print("Phase 1: Generating attacks...", file=sys.stderr)
    raw_concerns = generate_attacks(spec, adversaries, adversary_model, timeout)
    print(f"  Generated {len(raw_concerns)} raw concerns", file=sys.stderr)

    # Save raw concerns before any filtering
    concerns = raw_concerns  # Will be replaced if filtering is enabled

    # Persist concerns immediately so they survive crashes
    gauntlet_dir = Path(".adversarial-spec-gauntlet")
    gauntlet_dir.mkdir(exist_ok=True)
    concerns_file = gauntlet_dir / f"concerns-{spec_hash[:8]}.json"
    with open(concerns_file, 'w') as f:
        json.dump([{"adversary": c.adversary, "text": c.text, "severity": c.severity} for c in concerns], f, indent=2)
    print(f"  Concerns saved: {concerns_file}", file=sys.stderr)

    # Phase 1.5: Self-Filtering (NEW)
    dropped_concerns: list[Concern] = []
    noted_concerns: list[tuple[Concern, ExplanationMatch]] = []

    if not skip_filtering:
        print("Phase 1.5: Filtering against resolved concerns...", file=sys.stderr)
        concerns, dropped_concerns, noted_concerns = filter_concerns_with_explanations(
            concerns,
            adversary_model,  # Use cheap model for filtering
            spec_hash,
            timeout=60,
        )
        if dropped_concerns:
            print(f"  Dropped: {len(dropped_concerns)} (already addressed)", file=sys.stderr)
        if noted_concerns:
            print(f"  Noted: {len(noted_concerns)} (has explanation but re-verifying)", file=sys.stderr)
        print(f"  Proceeding with: {len(concerns)} concerns", file=sys.stderr)

    # Phase 2: Multi-Model Evaluation (batched, parallel)
    print("Phase 2: Evaluating concerns...", file=sys.stderr)
    if use_multi_model and len(eval_models) >= 2:
        evaluations = evaluate_concerns_multi_model(spec, concerns, eval_models, timeout=timeout)
    else:
        evaluations = evaluate_concerns(spec, concerns, eval_models[0], timeout)

    dismissed = [e for e in evaluations if e.verdict == "dismissed"]
    accepted = [e for e in evaluations if e.verdict == "accepted"]
    deferred = [e for e in evaluations if e.verdict == "deferred"]
    print(
        f"  Dismissed: {len(dismissed)}, Accepted: {len(accepted)}, Deferred: {len(deferred)}",
        file=sys.stderr,
    )

    # Persist evaluations immediately so they survive crashes
    evals_file = gauntlet_dir / f"evaluations-{spec_hash[:8]}.json"
    with open(evals_file, 'w') as f:
        eval_data = [
            {
                "concern": {"adversary": e.concern.adversary, "text": e.concern.text, "severity": e.concern.severity},
                "verdict": e.verdict,
                "justification": e.justification,
            }
            for e in evaluations
        ]
        json.dump(eval_data, f, indent=2)
    print(f"  Evaluations saved: {evals_file}", file=sys.stderr)

    # Print intermediate summary (so results visible even if later phases crash)
    print(f"\n=== Phase 2 Summary (accepted concerns) ===", file=sys.stderr)
    for e in accepted[:10]:
        print(f"  [{e.concern.adversary}] {e.concern.text[:80]}...", file=sys.stderr)
    if len(accepted) > 10:
        print(f"  ... and {len(accepted) - 10} more", file=sys.stderr)
    print(file=sys.stderr)

    # Phase 3: Rebuttals (parallel)
    rebuttals: list[Rebuttal] = []
    if allow_rebuttals and dismissed:
        print("Phase 3: Running rebuttals...", file=sys.stderr)
        rebuttals = run_rebuttals(evaluations, adversary_model, timeout)
        sustained = sum(1 for r in rebuttals if r.sustained)
        print(f"  Challenges: {sustained} of {len(rebuttals)}", file=sys.stderr)

    # Phase 4: Final Adjudication
    surviving_challenges: list[Concern] = []
    primary_eval_model = eval_models[0] if eval_models else select_eval_model()
    if rebuttals:
        challenged = [r for r in rebuttals if r.sustained]
        if challenged:
            print("Phase 4: Final adjudication...", file=sys.stderr)
            surviving_challenges = final_adjudication(spec, rebuttals, primary_eval_model, timeout)
            print(f"  Overturned: {len(surviving_challenges)}", file=sys.stderr)

    # Compile technical concerns (accepted + deferred + surviving challenges)
    technical_concerns = (
        [e.concern for e in accepted]
        + [e.concern for e in deferred]
        + surviving_challenges
    )

    # Print full summary BEFORE Final Boss prompt (survives crashes/EOFError)
    print(f"\n=== Gauntlet Summary (Phases 1-4) ===", file=sys.stderr)
    print(f"Total concerns: {len(concerns)} generated, {len(dropped_concerns)} filtered", file=sys.stderr)
    print(f"Verdicts: {len(accepted)} accepted, {len(dismissed)} dismissed, {len(deferred)} deferred", file=sys.stderr)
    if surviving_challenges:
        print(f"Rebuttals: {len(surviving_challenges)} overturned", file=sys.stderr)
    print(f"Technical concerns requiring revision: {len(technical_concerns)}", file=sys.stderr)
    print(f"Checkpoint files: {gauntlet_dir}/", file=sys.stderr)
    print(file=sys.stderr)

    # Phase 5: Final Boss UX Review (optional, expensive)
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
        print("Phase 5: Final Boss UX Review (Opus 4.5)...", file=sys.stderr)

        # Build summary of what the gauntlet found
        gauntlet_summary = f"""Technical review results:
- {len(concerns)} concerns raised by adversaries
- {len(dropped_concerns)} filtered out (already addressed)
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

        final_boss_result = run_final_boss_review(spec, gauntlet_summary, timeout=600)

        if final_boss_result.approved:
            print(f"  APPROVED by {final_boss_result.model}", file=sys.stderr)
        else:
            print(f"  UX CONCERNS from {final_boss_result.model}:", file=sys.stderr)
            for concern_text in final_boss_result.concerns[:3]:
                print(f"    - {concern_text[:80]}...", file=sys.stderr)
            # Add UX concerns to final list
            for concern_text in final_boss_result.concerns:
                ux_concerns.append(Concern(
                    adversary="ux_architect",
                    text=concern_text,
                    severity="high",  # UX concerns at this stage are serious
                ))

    # Final concerns = technical + UX
    final_concerns = technical_concerns + ux_concerns

    total_time = time.time() - start_time
    total_cost = cost_tracker.total_cost

    print(file=sys.stderr)
    print(f"=== Gauntlet Complete ===", file=sys.stderr)
    print(f"Duration: {total_time:.1f}s", file=sys.stderr)
    if dropped_concerns:
        print(f"Filtered out: {len(dropped_concerns)} (previously addressed)", file=sys.stderr)
    print(f"Final concerns requiring revision: {len(final_concerns)}", file=sys.stderr)
    print(f"Total cost: ${total_cost:.4f}", file=sys.stderr)

    result = GauntletResult(
        concerns=concerns,  # Post-filtering concerns that were evaluated
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
    print(f"Run log saved: {run_file}", file=sys.stderr)

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
    by_adversary: dict[str, int] = {}
    for c in result.concerns:
        by_adversary[c.adversary] = by_adversary.get(c.adversary, 0) + 1

    lines.append("Phase 1 - Attack Generation:")
    for adv, count in sorted(by_adversary.items()):
        lines.append(f"  {adv}: {count} concerns")
    lines.append(f"  Total: {len(result.concerns)} raw concerns")
    lines.append("")

    # Phase 2 summary
    dismissed = [e for e in result.evaluations if e.verdict == "dismissed"]
    accepted = [e for e in result.evaluations if e.verdict == "accepted"]
    deferred = [e for e in result.evaluations if e.verdict == "deferred"]

    lines.append(f"Phase 2 - Evaluation ({result.eval_model}):")
    lines.append(f"  Dismissed: {len(dismissed)} (with justification)")
    lines.append(f"  Accepted: {len(accepted)} (spec revision needed)")
    lines.append(f"  Deferred: {len(deferred)} (need more context)")
    lines.append("")

    # Phase 3 summary
    if result.rebuttals:
        sustained = [r for r in result.rebuttals if r.sustained]
        lines.append("Phase 3 - Rebuttals:")
        lines.append(f"  Challenges: {len(sustained)} (of {len(result.rebuttals)} dismissals)")
        lines.append("")

    # Phase 5 summary (Final Boss)
    if result.final_boss_result:
        lines.append(f"Phase 5 - Final Boss UX Review ({result.final_boss_result.model}):")
        if result.final_boss_result.approved:
            lines.append("  APPROVED - User story is sound")
            # Show first line of approval reason
            first_line = result.final_boss_result.response.split("\n")[0][:80]
            lines.append(f"  {first_line}")
        else:
            lines.append(f"  UX CONCERNS: {len(result.final_boss_result.concerns)}")
            for concern in result.final_boss_result.concerns[:3]:
                text = concern[:70] + "..." if len(concern) > 70 else concern
                lines.append(f"    - {text}")
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
        "--eval-model",
        help="Model for evaluation (default: auto-select frontier)",
    )
    parser.add_argument(
        "--no-rebuttals",
        action="store_true",
        help="Skip rebuttal phase",
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
        for name, desc in ADVERSARIES.items():
            first_line = desc.strip().split("\n")[0][:60]
            print(f"  {name:20} {first_line}...")
        return

    # Read spec from stdin
    spec = sys.stdin.read().strip()
    if not spec:
        print("Error: No spec provided via stdin", file=sys.stderr)
        sys.exit(1)

    # Parse adversaries
    adversaries = None
    if args.adversaries != "all":
        adversaries = [a.strip() for a in args.adversaries.split(",")]

    # Run gauntlet
    result = run_gauntlet(
        spec=spec,
        adversaries=adversaries,
        adversary_model=args.adversary_model,
        eval_model=args.eval_model,
        allow_rebuttals=not args.no_rebuttals,
        timeout=args.timeout,
    )

    # Output
    if args.json:
        output = {
            "concerns": [
                {"adversary": c.adversary, "text": c.text} for c in result.concerns
            ],
            "evaluations": [
                {
                    "concern": {"adversary": e.concern.adversary, "text": e.concern.text},
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
        print(json.dumps(output, indent=2))
    else:
        print()
        print(format_gauntlet_report(result))


if __name__ == "__main__":
    main()
