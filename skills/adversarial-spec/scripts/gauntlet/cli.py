"""CLI entry point for standalone gauntlet runs.

Extracted from gauntlet_monolith.py. Adds new flags:
--unattended, --resume, --eval-codex-reasoning, --show-manifest.
"""

from __future__ import annotations

import json
import sys


def main():
    """CLI entry point for standalone gauntlet runs."""
    import argparse

    from adversaries import ADVERSARIES
    from gauntlet.orchestrator import run_gauntlet
    from gauntlet.persistence import (
        list_gauntlet_runs,
        load_gauntlet_run,
        load_run_manifest,
    )
    from gauntlet.reporting import (
        format_gauntlet_report,
        get_adversary_leaderboard,
    )

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
        "--eval-codex-reasoning",
        default="xhigh",
        choices=["minimal", "low", "medium", "high", "xhigh"],
        help="Codex reasoning effort for evaluation/adjudication (default: xhigh)",
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
        "--show-manifest",
        metavar="HASH",
        nargs="?",
        const="",
        help="Show run manifest for a spec hash (default: most recent)",
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
    parser.add_argument(
        "--unattended",
        action="store_true",
        help="Run without stdin prompts + enable auto-checkpoint after expensive phases",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint files if available (no-op if no valid checkpoint)",
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

    if args.show_manifest is not None:
        hash_prefix = args.show_manifest or None
        manifest = load_run_manifest(hash_prefix)
        if manifest:
            print(json.dumps(manifest, indent=2))
        else:
            label = f"for hash {hash_prefix}" if hash_prefix else "(most recent)"
            print(f"No manifest found {label}", file=sys.stderr)
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
            report_path = (
                Path(args.report_path)
                if args.report_path
                else Path(".adversarial-spec/pre_gauntlet_report.json")
            )
            save_report(pre_result, report_path)
            print(f"Pre-gauntlet report saved: {report_path}", file=sys.stderr)

            # Print summary
            print(f"Status: {pre_result.status.value}", file=sys.stderr)
            print(
                f"Concerns: {len(pre_result.concerns)} "
                f"({len(pre_result.get_blockers())} blockers)",
                file=sys.stderr,
            )
            print(
                f"Timings: git={pre_result.timings.git_ms}ms, "
                f"build={pre_result.timings.build_ms}ms, "
                f"total={pre_result.timings.total_ms}ms",
                file=sys.stderr,
            )

            # Check if we should proceed
            if pre_result.status != PreGauntletStatus.COMPLETE:
                print(
                    "\nPre-gauntlet did not complete successfully. Exiting.",
                    file=sys.stderr,
                )
                sys.exit(get_exit_code(pre_result.status))

            # Use the context-enriched spec for gauntlet
            spec = pre_result.context_markdown
            print("\nProceeding to adversarial gauntlet...\n", file=sys.stderr)

        except ImportError as e:
            print(
                f"Warning: Pre-gauntlet module not available: {e}",
                file=sys.stderr,
            )
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
        eval_codex_reasoning=args.eval_codex_reasoning,
        resume=args.resume,
        unattended=args.unattended,
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
                {"adversary": c.adversary, "text": c.text}
                for c in result.final_concerns
            ],
            "adversary_model": result.adversary_model,
            "eval_model": result.eval_model,
            "total_time": result.total_time,
            "total_cost": result.total_cost,
        }
        if result.concerns_path:
            output["concerns_path"] = result.concerns_path
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
