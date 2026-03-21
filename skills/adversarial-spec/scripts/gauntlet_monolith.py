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

# run_gauntlet() has moved to gauntlet/orchestrator.py
from gauntlet.orchestrator import run_gauntlet  # noqa: F401,E402


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
