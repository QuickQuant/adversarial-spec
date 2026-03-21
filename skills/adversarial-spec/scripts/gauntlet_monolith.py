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
from typing import Optional

from gauntlet.core_types import (  # noqa: E402
    BigPictureSynthesis,
    CheckpointMeta,
    Concern,
    DismissalReviewStats,
    Evaluation,
    ExplanationMatch,
    FinalBossResult,
    FinalBossVerdict,
    GauntletClusteringError,
    GauntletConfig,
    GauntletExecutionError,
    GauntletResult,
    Medal,
    PhaseMetrics,
    Rebuttal,
    normalize_verdict,
)
from gauntlet.model_dispatch import (  # noqa: E402
    _get_model_provider,
    _validate_model_name,
    call_model,
    get_available_eval_models,
    get_rate_limit_config,
    running_in_claude_code,
    select_adversary_model,
    select_eval_model,
    select_gauntlet_models,
)
from gauntlet.medals import (  # noqa: E402
    _concerns_are_similar,
    _get_concern_keywords,
    calculate_medals,
    format_medals_for_display,
    generate_medal_report,
    get_medal_leaderboard,
    save_medal_reports,
)
from gauntlet.reporting import (  # noqa: E402
    format_gauntlet_report,
    format_synergy_report,
    get_adversary_leaderboard,
    get_adversary_synergy,
)
from gauntlet.phase_1_attacks import generate_attacks  # noqa: E402
from gauntlet.phase_2_synthesis import (  # noqa: E402
    BIG_PICTURE_PROMPT,
    generate_big_picture_synthesis,
)
from gauntlet.phase_3_filtering import (  # noqa: E402
    _normalize_concern_text,
    _track_dedup_stats,
    choose_clustering_model,
    cluster_concerns_with_provenance,
    expand_clustered_evaluations,
    filter_concerns_with_explanations,
    find_matching_explanation,
)
from gauntlet.phase_4_evaluation import (  # noqa: E402
    evaluate_concerns,
    evaluate_concerns_multi_model,
)
from gauntlet.phase_5_rebuttals import (  # noqa: E402
    REBUTTAL_PROMPT,
    run_rebuttals,
)
from gauntlet.phase_6_adjudication import final_adjudication  # noqa: E402
from gauntlet.phase_7_final_boss import run_final_boss_review  # noqa: E402
from gauntlet.persistence import (  # noqa: E402
    CONFIDENCE_ACCEPT_THRESHOLD,
    CONFIDENCE_NOTE_THRESHOLD,
    RESOLVED_CONCERNS_FILE,
    RUNS_DIR,
    STATS_DIR,
    STATS_FILE,
    add_resolved_concern,
    calculate_explanation_confidence,
    get_spec_hash,
    list_gauntlet_runs,
    load_adversary_stats,
    load_gauntlet_run,
    load_resolved_concerns,
    record_explanation_match,
    save_adversary_stats,
    save_gauntlet_run,
    save_resolved_concerns,
    update_adversary_stats,
    verify_explanation,
)

from adversaries import (
    ADVERSARIES,
    FINAL_BOSS,
    generate_concern_id,
)
from models import (
    cost_tracker,
)
from providers import (
    CODEX_AVAILABLE,
    DEFAULT_CODEX_REASONING,
    GEMINI_CLI_AVAILABLE,
)

try:
    from litellm import completion  # noqa: F401 — used by phase functions still in monolith
except ImportError:
    print(
        "Error: litellm package not installed. Run: pip install litellm",
        file=sys.stderr,
    )
    sys.exit(1)


# Phase functions imported from gauntlet.phase_*.py modules.
# Orchestrator (run_gauntlet) and CLI (main) remain below.

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

    # QUOTA BURN FIX 1: Build GauntletConfig once from CLI params.
    config = GauntletConfig(
        timeout=timeout,
        attack_codex_reasoning=attack_codex_reasoning,
    )

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
    raw_concerns, adversary_timing, attack_raw_responses = generate_attacks(
        spec, adversaries, attack_models, config,
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

    # Persist raw LLM responses so parsing errors are recoverable
    if attack_raw_responses:
        raw_file = gauntlet_dir / f"raw-responses-{spec_hash[:8]}.json"
        with open(raw_file, 'w') as f:
            json.dump(attack_raw_responses, f, indent=2)
        print(f"  Raw responses saved: {raw_file}", file=sys.stderr)

    # Phase 2: Big Picture Synthesis
    print("Phase 2: Big picture synthesis...", file=sys.stderr)
    big_picture = generate_big_picture_synthesis(
        concerns,
        primary_attack_model,
        config,
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
            config=config,
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
        config,
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
            config,
        )
    else:
        clustered_evaluations = evaluate_concerns(
            spec,
            evaluation_concerns,
            eval_models[0],
            config,
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
        rebuttals = run_rebuttals(clustered_evaluations, primary_attack_model, config)
        sustained = sum(1 for r in rebuttals if r.sustained)
        print(f"  Challenges: {sustained} of {len(rebuttals)}", file=sys.stderr)

    # Phase 6: Final Adjudication
    surviving_challenges: list[Concern] = []
    primary_eval_model = eval_models[0] if eval_models else select_eval_model()
    if rebuttals:
        challenged = [r for r in rebuttals if r.sustained]
        if challenged:
            print("Phase 6: Final adjudication...", file=sys.stderr)
            surviving_challenges = final_adjudication(spec, rebuttals, primary_eval_model, config)
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
            config=config,
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
