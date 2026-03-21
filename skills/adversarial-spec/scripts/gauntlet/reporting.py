"""Reporting and display formatting for the gauntlet pipeline.

Extracted from gauntlet_monolith.py — adversary leaderboard, synergy
analysis, and the final gauntlet report. No phase logic lives here.
"""

from __future__ import annotations

from typing import Any

from gauntlet.core_types import (
    FinalBossVerdict,
    GauntletResult,
)
from gauntlet.medals import format_medals_for_display
from gauntlet.persistence import load_adversary_stats

# =============================================================================
# ADVERSARY LEADERBOARD
# =============================================================================


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
# ADVERSARY SYNERGY
# =============================================================================


def get_adversary_synergy(result: GauntletResult) -> dict[str, dict]:
    """Calculate synergy between adversary pairs for a single run.

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


# =============================================================================
# RUN MANIFEST
# =============================================================================


def format_run_manifest(manifest: dict[str, Any]) -> str:
    """Format a run manifest for human-readable CLI output."""
    phases = manifest.get("phases", [])
    lines = [
        "=== Gauntlet Run Manifest ===",
        f"Spec hash: {manifest.get('spec_hash', 'unknown')}",
        f"Status: {manifest.get('status', 'unknown')}",
        f"Created: {manifest.get('created_at', 'unknown')}",
        f"Updated: {manifest.get('updated_at', 'unknown')}",
    ]

    if manifest.get("path"):
        lines.append(f"Path: {manifest['path']}")

    if not phases:
        lines.append("")
        lines.append("No phase metrics recorded.")
        return "\n".join(lines)

    total_duration = sum(phase.get("duration_seconds", 0.0) for phase in phases)
    total_input = sum(phase.get("input_tokens", 0) for phase in phases)
    total_output = sum(phase.get("output_tokens", 0) for phase in phases)

    lines.append("")
    lines.append(
        f"Totals: {len(phases)} phases, {total_duration:.1f}s, "
        f"{total_input} input tokens, {total_output} output tokens"
    )
    lines.append("")

    for phase in phases:
        models = ", ".join(phase.get("models_used", [])) or "-"
        lines.append(
            f"[{phase.get('phase_index', '?')}] {phase.get('phase', 'unknown')} "
            f"status={phase.get('status', 'unknown')} "
            f"duration={phase.get('duration_seconds', 0.0):.1f}s "
            f"tokens={phase.get('input_tokens', 0)}/{phase.get('output_tokens', 0)}"
        )
        lines.append(f"  Models: {models}")
        if phase.get("error"):
            lines.append(f"  Error: {phase['error']}")

    return "\n".join(lines)


# =============================================================================
# GAUNTLET REPORT
# =============================================================================


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
