"""Gauntlet orchestrator — phase sequencing, resume, unattended mode.

Extracted from gauntlet_monolith.py. Owns `run_gauntlet()` — the primary
API entry point that sequences all 7 phases and handles cross-cutting
concerns: config construction, model validation, checkpointing, manifests.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Optional

import token_tracking
from adversaries import ADVERSARIES, resolve_adversary_name
from gauntlet.core_types import (
    Concern,
    ExplanationMatch,
    FinalBossResult,
    FinalBossVerdict,
    GauntletConfig,
    GauntletExecutionError,
    GauntletResult,
    PhaseMetrics,
    Rebuttal,
)
from gauntlet.medals import calculate_medals, save_medal_reports
from gauntlet.model_dispatch import (
    _validate_model_name,
    get_available_eval_models,
    select_adversary_model,
    select_eval_model,
)
from gauntlet.persistence import (
    add_resolved_concern,
    get_config_hash,
    get_spec_hash,
    load_partial_run,
    save_checkpoint,
    save_gauntlet_run,
    update_adversary_stats,
    update_run_manifest,
)
from gauntlet.phase_1_attacks import check_phase1_quality, generate_attacks
from gauntlet.phase_2_synthesis import generate_big_picture_synthesis
from gauntlet.phase_3_filtering import (
    _track_dedup_stats,
    expand_clustered_evaluations,
    filter_concerns_with_explanations,
)
from gauntlet.phase_4_evaluation import (
    evaluate_concerns,
    evaluate_concerns_multi_model,
)
from gauntlet.phase_5_rebuttals import run_rebuttals
from gauntlet.phase_6_adjudication import final_adjudication
from gauntlet.phase_7_final_boss import run_final_boss_review

PHASE_INDEXES = {
    "phase_1": 1,
    "phase_2": 2,
    "phase_3": 3,
    "phase_3_5": 4,
    "phase_4": 5,
    "phase_5": 6,
    "phase_6": 7,
    "phase_7": 8,
}


def _start_phase_capture() -> tuple[float, int, int]:
    """Capture timing and token counters at phase start."""
    return (
        time.time(),
        token_tracking.tracker.total_input_tokens,
        token_tracking.tracker.total_output_tokens,
    )


def _build_phase_metrics(
    phase: str,
    started_at: float,
    input_before: int,
    output_before: int,
    models_used: list[str],
    config: GauntletConfig,
    spec_hash: str,
    *,
    status: str = "completed",
    error: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build a manifest payload with the full PhaseMetrics contract."""
    metrics = PhaseMetrics(
        phase=phase,
        phase_index=PHASE_INDEXES[phase],
        status=status,
        duration_seconds=max(0.0, time.time() - started_at),
        input_tokens=max(0, token_tracking.tracker.total_input_tokens - input_before),
        output_tokens=max(0, token_tracking.tracker.total_output_tokens - output_before),
        models_used=list(models_used),
        config_snapshot=dict(config.__dict__),
        error=error,
        spec_hash=spec_hash,
    )
    payload = dict(metrics.__dict__)
    if extra:
        payload.update(extra)
    return payload


def _load_approved_prompts(
    gauntlet_dir: Path,
    spec_hash: str,
) -> Optional[dict[str, Any]]:
    """Load approved-prompts.json and validate spec_hash.

    Returns None if file doesn't exist (static fallback).
    Raises ValueError on hash mismatch or corrupt file (FM-1).
    """
    prompts_file = gauntlet_dir / "approved-prompts.json"
    if not prompts_file.exists():
        return None

    try:
        data = json.loads(prompts_file.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"Failed to load approved-prompts.json: {exc}") from exc

    stored_hash = data.get("spec_hash", "")
    if stored_hash != spec_hash:
        raise ValueError(
            f"Approved prompts are stale (spec changed since generation). "
            f"Stored hash: {stored_hash}, current: {spec_hash}. "
            f"Re-run Arm Adversaries to regenerate prompts, or pass "
            f"--force-static-fallback to proceed with static personas."
        )

    return data


def _resolve_and_filter_adversaries(
    adversaries: list[str],
    approved_prompts: Optional[dict[str, Any]],
) -> tuple[list[str], Optional[dict[str, str]]]:
    """Resolve aliases, deduplicate, validate, filter skipped, extract prompts.

    Returns (filtered_adversary_list, prompts_dict_or_none).
    Raises ValueError on unknown adversary (CB-5) or zero remaining (§1.7).
    """
    # Resolve aliases and deduplicate (preserving first-seen order)
    seen: set[str] = set()
    resolved: list[str] = []
    for name in adversaries:
        canonical = resolve_adversary_name(name)
        if canonical not in seen:
            seen.add(canonical)
            resolved.append(canonical)

    # Validate all resolved names exist in registry (CB-5/US-3)
    for name in resolved:
        if name not in ADVERSARIES:
            raise ValueError(
                f"Unknown adversary '{name}' after alias resolution. "
                f"Valid adversaries: {sorted(ADVERSARIES.keys())}"
            )

    # Filter skipped adversaries and extract prompts dict
    prompts: Optional[dict[str, str]] = None
    if approved_prompts is not None:
        prompts_section = approved_prompts.get("prompts", {})
        filtered: list[str] = []
        prompts = {}
        for name in resolved:
            entry = prompts_section.get(name, {})
            if entry.get("status") == "skipped":
                continue
            filtered.append(name)
            if entry.get("full_persona"):
                prompts[name] = entry["full_persona"]
        resolved = filtered

    if not resolved:
        raise ValueError(
            "Zero adversaries remain after filtering skipped entries. "
            "At least one adversary must be active."
        )

    return resolved, prompts


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
    timeout: int = 1800,
    attack_codex_reasoning: str = "low",
    eval_codex_reasoning: str = "xhigh",
    resume: bool = False,
    unattended: bool = False,
) -> GauntletResult:
    """Run the full adversarial gauntlet on a specification.

    Args:
        spec: The specification to review
        adversaries: List of adversary keys (default: all)
        adversary_model: Legacy single-model override for adversaries
        attack_models: Model list for adversary attacks (default: auto-select)
        eval_models: Models for evaluation (default: auto-select multiple)
        allow_rebuttals: Whether to run rebuttal phase
        use_multi_model: Use multiple models for evaluation consensus
        skip_filtering: Skip filtering against resolved concerns
        run_final_boss: Run Phase 7 Final Boss UX review (expensive)
        timeout: Timeout per model call
        attack_codex_reasoning: Reasoning effort for Codex in attack phase
        eval_codex_reasoning: Reasoning effort for Codex in eval/adjudication
        resume: Resume from checkpoint files if available
        unattended: Forbid input() + enable auto-checkpoint

    Returns:
        GauntletResult with all phases' outputs
    """
    start_time = time.time()
    spec_hash = get_spec_hash(spec)

    # ── Step 1: Build config (QUOTA BURN FIX 1) ──
    config = GauntletConfig(
        timeout=timeout,
        attack_codex_reasoning=attack_codex_reasoning,
        eval_codex_reasoning=eval_codex_reasoning,
        auto_checkpoint=unattended,
        resume=resume,
        unattended=unattended,
    )

    # ── Step 2: Resolve models ──
    # Flag precedence: attack_models > adversary_model > auto-select
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
            eval_models = get_available_eval_models()[:3]
        else:
            eval_models = [select_eval_model()]

    # Default to all adversaries
    if adversaries is None:
        adversaries = list(ADVERSARIES.keys())

    # ── Step 3: Early model validation (G-6: fail fast) ──
    for m in attack_models + eval_models:
        _validate_model_name(m)

    # ── Step 4: Unattended enforcement (G-4) ──
    original_input = None
    if config.unattended:
        import builtins
        original_input = builtins.input
        builtins.input = lambda *a, **kw: (_ for _ in ()).throw(
            RuntimeError("input() called in unattended mode")
        )

    gauntlet_dir = Path(".adversarial-spec-gauntlet")
    gauntlet_dir.mkdir(exist_ok=True)

    # ── Step 4.5: Load approved prompts + resolve/filter adversaries ──
    approved_prompts = _load_approved_prompts(gauntlet_dir, spec_hash)
    adversaries, dynamic_prompts = _resolve_and_filter_adversaries(
        adversaries, approved_prompts,
    )
    if approved_prompts:
        print(f"Dynamic prompts: loaded ({len(dynamic_prompts or {})} overrides)", file=sys.stderr)
    else:
        print("Dynamic prompts: none (using static personas)", file=sys.stderr)
    manifest_path: Optional[str] = None
    config_hash = get_config_hash(
        config,
        attack_models=attack_models,
        eval_models=eval_models,
        adversaries=adversaries,
    )

    try:
        # ── Step 5: Resume loader (QUOTA BURN FIX 3) ──
        partial: dict[str, dict[str, Any]] = {}
        if config.resume:
            partial = load_partial_run(
                spec_hash, config,
                attack_models=attack_models,
                eval_models=eval_models,
                adversaries=adversaries,
            )
            if not partial:
                print("No valid checkpoint found, starting fresh", file=sys.stderr)
            else:
                phases = ", ".join(sorted(partial.keys()))
                print(f"Resuming from checkpoint: {phases}", file=sys.stderr)

        print("=== Adversarial Gauntlet ===", file=sys.stderr)
        print(f"Adversaries: {', '.join(adversaries)}", file=sys.stderr)
        print(f"Attack models: {', '.join(attack_models)}", file=sys.stderr)
        print(f"Eval models: {', '.join(eval_models)}", file=sys.stderr)
        if config.resume:
            print("Resume: enabled", file=sys.stderr)
        if config.unattended:
            print("Unattended: enabled (auto-checkpoint on)", file=sys.stderr)
        print(file=sys.stderr)

        # ── Phase 1: Attack Generation ──
        phase_1_started_at, phase_1_input, phase_1_output = _start_phase_capture()
        phase_1_status = "completed"
        print("Phase 1: Generating attacks...", file=sys.stderr)
        if "phase_1" in partial:
            raw_concerns = partial["phase_1"]["concerns"]
            adversary_timing = partial["phase_1"]["timing"]
            attack_raw_responses = partial["phase_1"]["raw_responses"]
            # Check which adversaries already ran
            completed_advs = {c.adversary for c in raw_concerns}
            missing_advs = [a for a in adversaries if a not in completed_advs]
            if missing_advs:
                print(f"  Resuming: {len(completed_advs)} done, {len(missing_advs)} remaining", file=sys.stderr)
                new_concerns, new_timing, new_raw = generate_attacks(
                    spec, missing_advs, attack_models, config,
                    prompts=dynamic_prompts,
                )
                raw_concerns.extend(new_concerns)
                adversary_timing.update(new_timing)
                attack_raw_responses.update(new_raw)
            else:
                phase_1_status = "skipped_resume"
                print(f"  Resumed {len(raw_concerns)} concerns from checkpoint", file=sys.stderr)
        else:
            raw_concerns, adversary_timing, attack_raw_responses = generate_attacks(
                spec, adversaries, attack_models, config,
                prompts=dynamic_prompts,
            )
        print(f"  Generated {len(raw_concerns)} raw concerns", file=sys.stderr)

        # Save raw concerns before any filtering
        concerns = raw_concerns

        # Persist concerns (always, regardless of auto_checkpoint)
        save_checkpoint(
            "concerns", "phase_1", concerns, spec_hash, config_hash,
        )
        print("  Concerns checkpointed", file=sys.stderr)

        # Persist raw LLM responses so parsing errors are recoverable
        if attack_raw_responses:
            raw_file = gauntlet_dir / f"raw-responses-{spec_hash[:8]}.json"
            with open(raw_file, 'w') as f:
                json.dump(attack_raw_responses, f, indent=2)

        # ── Phase 1 Quality Gate ──
        parse_failures = check_phase1_quality(concerns, attack_raw_responses)
        if parse_failures:
            for fail in parse_failures:
                print(
                    f"  PARSE FAILURE: {fail['adversary']}@{fail['model']}: "
                    f"{fail['response_length']} chars, 0 concerns parsed",
                    file=sys.stderr,
                )
            raise GauntletExecutionError(
                f"Phase 1 parse failure: {len(parse_failures)} adversary×model pair(s) "
                f"returned non-empty responses but 0 concerns were parsed. "
                f"Raw responses saved to {gauntlet_dir / f'raw-responses-{spec_hash[:8]}.json'}. "
                f"Review and re-run."
            )

        manifest_path = update_run_manifest(
            manifest_path,
            _build_phase_metrics(
                "phase_1",
                phase_1_started_at,
                phase_1_input,
                phase_1_output,
                [] if phase_1_status == "skipped_resume" else attack_models,
                config,
                spec_hash,
                status=phase_1_status,
                extra={
                    "concerns_generated": len(raw_concerns),
                    "attack_models": attack_models,
                    "adversaries": adversaries,
                    "parse_failures": len(parse_failures),
                },
            ),
        )

        # ── Phase 2: Big Picture Synthesis ──
        phase_2_started_at, phase_2_input, phase_2_output = _start_phase_capture()
        print("Phase 2: Big picture synthesis...", file=sys.stderr)
        big_picture = generate_big_picture_synthesis(
            concerns, primary_attack_model, config,
        )
        if big_picture.real_issues:
            print(f"  Real issues: {len(big_picture.real_issues)}", file=sys.stderr)
            for issue in big_picture.real_issues[:2]:
                print(f"    \u2022 {issue[:70]}...", file=sys.stderr)
        if big_picture.meta_concern:
            print(f"  Meta-concern: {big_picture.meta_concern[:80]}...", file=sys.stderr)
        if big_picture.high_signal:
            n = len(big_picture.high_signal)
            print(f"  High-signal: {n} concerns flagged", file=sys.stderr)

        manifest_path = update_run_manifest(
            manifest_path,
            _build_phase_metrics(
                "phase_2",
                phase_2_started_at,
                phase_2_input,
                phase_2_output,
                [primary_attack_model],
                config,
                spec_hash,
                extra={
                    "real_issues": len(big_picture.real_issues) if big_picture.real_issues else 0,
                    "high_signal": len(big_picture.high_signal) if big_picture.high_signal else 0,
                },
            ),
        )

        # ── Phase 3: Self-Filtering ──
        phase_3_started_at, phase_3_input, phase_3_output = _start_phase_capture()
        dropped_concerns: list[Concern] = []
        noted_concerns: list[tuple[Concern, ExplanationMatch]] = []

        if not skip_filtering:
            print("Phase 3: Filtering against resolved concerns...", file=sys.stderr)
            concerns, dropped_concerns, noted_concerns = filter_concerns_with_explanations(
                concerns,
                primary_attack_model,
                spec_hash,
                config=config,
            )
            if dropped_concerns:
                print(f"  Dropped: {len(dropped_concerns)} (already addressed)", file=sys.stderr)
            if noted_concerns:
                print(f"  Noted: {len(noted_concerns)} (has explanation but re-verifying)", file=sys.stderr)
            print(f"  Proceeding with: {len(concerns)} concerns", file=sys.stderr)

        manifest_path = update_run_manifest(
            manifest_path,
            _build_phase_metrics(
                "phase_3",
                phase_3_started_at,
                phase_3_input,
                phase_3_output,
                [primary_attack_model] if not skip_filtering else [],
                config,
                spec_hash,
                extra={
                    "post_filter": len(concerns),
                    "dropped": len(dropped_concerns),
                },
            ),
        )

        # Preserve post-filter concerns for adversary-level stats before clustering.
        post_filter_concerns = concerns

        # ── Phase 3.5: Skip clustering (pass-through) ──
        # Clustering was removed: intermediate LLM dedup lost content (same failure
        # class as v1 synthesis — haiku subagents missed 48% of concerns). Adversary
        # scope design handles overlap upstream instead. See CR-8.
        clustered_concerns = concerns
        cluster_members: dict[str, list] = {}
        print(f"Phase 3.5: Skipped clustering ({len(concerns)} concerns passed through)", file=sys.stderr)

        _track_dedup_stats(
            spec_hash=spec_hash,
            raw_count=len(raw_concerns),
            post_filter_count=len(post_filter_concerns),
            post_cluster_count=len(concerns),
            cluster_deduped=0,
            reduction_pct=0.0,
            attack_models=attack_models,
            clustering_model="none",
        )

        # ── Phase 4: Multi-Model Evaluation ──
        phase_4_started_at, phase_4_input, phase_4_output = _start_phase_capture()
        phase_4_status = "completed"
        print("Phase 4: Evaluating concerns...", file=sys.stderr)
        evaluation_concerns = clustered_concerns

        if "phase_4" in partial:
            # Validate concern set alignment before reusing
            saved_concern_ids = {e.concern.id for e in partial["phase_4"]["evaluations"]}
            current_concern_ids = {c.id for c in clustered_concerns}
            if saved_concern_ids == current_concern_ids:
                clustered_evaluations = partial["phase_4"]["evaluations"]
                phase_4_status = "skipped_resume"
                print(f"  Resumed {len(clustered_evaluations)} evaluations from checkpoint", file=sys.stderr)
            else:
                print("  Concern set changed since checkpoint, re-evaluating", file=sys.stderr)
                if use_multi_model and len(eval_models) >= 2:
                    clustered_evaluations = evaluate_concerns_multi_model(
                        spec, evaluation_concerns, eval_models, config,
                    )
                else:
                    clustered_evaluations = evaluate_concerns(
                        spec, evaluation_concerns, eval_models[0], config,
                    )
        else:
            if use_multi_model and len(eval_models) >= 2:
                clustered_evaluations = evaluate_concerns_multi_model(
                    spec, evaluation_concerns, eval_models, config,
                )
            else:
                clustered_evaluations = evaluate_concerns(
                    spec, evaluation_concerns, eval_models[0], config,
                )

        dismissed = [e for e in clustered_evaluations if e.verdict == "dismissed"]
        accepted = [e for e in clustered_evaluations if e.verdict == "accepted"]
        acknowledged = [e for e in clustered_evaluations if e.verdict == "acknowledged"]
        deferred = [e for e in clustered_evaluations if e.verdict == "deferred"]
        print(
            f"  Dismissed: {len(dismissed)}, Accepted: {len(accepted)}, "
            f"Acknowledged: {len(acknowledged)}, Deferred: {len(deferred)}",
            file=sys.stderr,
        )

        # Auto-checkpoint evaluations
        if config.auto_checkpoint:
            save_checkpoint(
                "evaluations", "phase_4", clustered_evaluations, spec_hash, config_hash,
            )
            print("  Evaluations checkpointed", file=sys.stderr)

        manifest_path = update_run_manifest(
            manifest_path,
            _build_phase_metrics(
                "phase_4",
                phase_4_started_at,
                phase_4_input,
                phase_4_output,
                [] if phase_4_status == "skipped_resume" else eval_models,
                config,
                spec_hash,
                status=phase_4_status,
                extra={
                    "dismissed": len(dismissed),
                    "accepted": len(accepted),
                    "acknowledged": len(acknowledged),
                    "deferred": len(deferred),
                },
            ),
        )

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

        # ── Phase 5: Rebuttals ──
        phase_5_started_at, phase_5_input, phase_5_output = _start_phase_capture()
        rebuttals: list[Rebuttal] = []
        if allow_rebuttals and dismissed:
            print("Phase 5: Running rebuttals...", file=sys.stderr)
            rebuttals = run_rebuttals(clustered_evaluations, primary_attack_model, config)
            sustained = sum(1 for r in rebuttals if r.sustained)
            print(f"  Challenges: {sustained} of {len(rebuttals)}", file=sys.stderr)

        manifest_path = update_run_manifest(
            manifest_path,
            _build_phase_metrics(
                "phase_5",
                phase_5_started_at,
                phase_5_input,
                phase_5_output,
                [primary_attack_model] if allow_rebuttals and dismissed else [],
                config,
                spec_hash,
                extra={
                    "rebuttals": len(rebuttals),
                    "sustained": sum(1 for r in rebuttals if r.sustained),
                },
            ),
        )

        # ── Phase 6: Final Adjudication ──
        phase_6_started_at, phase_6_input, phase_6_output = _start_phase_capture()
        surviving_challenges: list[Concern] = []
        primary_eval_model = eval_models[0] if eval_models else select_eval_model()
        challenged: list[Rebuttal] = []
        if rebuttals:
            challenged = [r for r in rebuttals if r.sustained]
            if challenged:
                print("Phase 6: Final adjudication...", file=sys.stderr)
                surviving_challenges = final_adjudication(
                    spec, rebuttals, primary_eval_model, config,
                )
                print(f"  Overturned: {len(surviving_challenges)}", file=sys.stderr)

        manifest_path = update_run_manifest(
            manifest_path,
            _build_phase_metrics(
                "phase_6",
                phase_6_started_at,
                phase_6_input,
                phase_6_output,
                [primary_eval_model] if challenged else [],
                config,
                spec_hash,
                extra={"overturned": len(surviving_challenges)},
            ),
        )

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
        print(
            f"Verdicts: {len(accepted)} accepted, {len(dismissed)} dismissed, "
            f"{len(deferred)} deferred",
            file=sys.stderr,
        )
        if surviving_challenges:
            print(f"Rebuttals: {len(surviving_challenges)} overturned", file=sys.stderr)
        print(f"Technical concerns requiring revision: {len(technical_concerns)}", file=sys.stderr)
        print(f"Checkpoint files: {gauntlet_dir}/", file=sys.stderr)
        print(file=sys.stderr)

        # ── Phase 7: Final Boss UX Review (optional, expensive) ──
        phase_7_started_at, phase_7_input, phase_7_output = _start_phase_capture()
        phase_7_status = "completed"
        final_boss_result: Optional[FinalBossResult] = None
        ux_concerns: list[Concern] = []

        # Check for resumed Final Boss result
        if "phase_7" in partial and run_final_boss:
            final_boss_result = partial["phase_7"]["final_boss_result"]
            phase_7_status = "skipped_resume"
            print("Phase 7: Resumed Final Boss result from checkpoint", file=sys.stderr)
        else:
            # Determine whether to run Final Boss
            do_final_boss = run_final_boss
            if not do_final_boss:
                try:
                    do_final_boss = (
                        input("Run Final Boss UX review? (y/n): ")
                        .strip().lower().startswith('y')
                    )
                except (EOFError, RuntimeError):
                    print(
                        "  Skipping Final Boss (no stdin available, use --final-boss to enable)",
                        file=sys.stderr,
                    )
                    do_final_boss = False

            if do_final_boss:
                print("Phase 7: Final Boss UX Review (Opus 4.7)...", file=sys.stderr)

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
                    for c in technical_concerns[:5]:
                        gauntlet_summary += f"- [{c.adversary}] {c.text[:100]}...\n"

                accepted_concerns = [e.concern for e in accepted]

                final_boss_result = run_final_boss_review(
                    spec=spec,
                    gauntlet_summary=gauntlet_summary,
                    accepted_concerns=accepted_concerns,
                    dismissed_evaluations=dismissed,
                    config=config,
                )

                # Auto-checkpoint Final Boss result
                if config.auto_checkpoint and final_boss_result:
                    save_checkpoint(
                        "final-boss", "phase_7", final_boss_result,
                        spec_hash, config_hash,
                    )

        # Handle Final Boss verdict
        if final_boss_result:
            if final_boss_result.verdict == FinalBossVerdict.PASS:
                print(f"  VERDICT: PASS by {final_boss_result.model}", file=sys.stderr)
            elif final_boss_result.verdict == FinalBossVerdict.REFINE:
                print(f"  VERDICT: REFINE by {final_boss_result.model}", file=sys.stderr)
                print("  Concerns to address:", file=sys.stderr)
                for concern_text in final_boss_result.concerns[:3]:
                    print(f"    - {concern_text[:80]}...", file=sys.stderr)
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
                ux_concerns.append(Concern(
                    adversary="ux_architect",
                    text=f"RECONSIDER VERDICT: {final_boss_result.reconsider_reason}. "
                         f"Alternates: {'; '.join(final_boss_result.alternate_approaches[:2])}",
                    severity="critical",
                ))

        phase_7_models = (
            [final_boss_result.model] if final_boss_result and final_boss_result.model else []
        )
        manifest_path = update_run_manifest(
            manifest_path,
            _build_phase_metrics(
                "phase_7",
                phase_7_started_at,
                phase_7_input,
                phase_7_output,
                phase_7_models,
                config,
                spec_hash,
                status=phase_7_status,
                extra={
                    "verdict": final_boss_result.verdict.value if final_boss_result else "skipped",
                },
            ),
        )

        # ── Build result ──
        final_concerns = technical_concerns + ux_concerns

        total_time = time.time() - start_time
        total_cost = token_tracking.tracker.total_cost

        print(file=sys.stderr)
        print("=== Gauntlet Complete ===", file=sys.stderr)
        print(f"Duration: {total_time:.1f}s", file=sys.stderr)
        if dropped_concerns:
            print(f"Filtered out: {len(dropped_concerns)} (previously addressed)", file=sys.stderr)
        print(f"Final concerns requiring revision: {len(final_concerns)}", file=sys.stderr)
        print(f"Total cost: ${total_cost:.4f}", file=sys.stderr)

        # Expand clustered evaluations back to member concerns for adversary attribution stats.
        evaluations = expand_clustered_evaluations(clustered_evaluations, cluster_members)

        concerns_path = str(gauntlet_dir / f"concerns-{spec_hash[:8]}.json")

        result = GauntletResult(
            concerns=post_filter_concerns,
            evaluations=evaluations,
            rebuttals=rebuttals,
            final_concerns=final_concerns,
            adversary_model=adversary_model,
            eval_model=", ".join(eval_models),
            total_time=total_time,
            total_cost=total_cost,
            final_boss_result=final_boss_result,
            raw_concerns=raw_concerns,
            dropped_concerns=dropped_concerns,
            spec_hash=spec_hash,
            adversary_timing=adversary_timing,
            big_picture=big_picture,
            clustered_concerns=clustered_concerns,
            clustered_evaluations=clustered_evaluations,
            cluster_members=cluster_members,
            concerns_path=concerns_path,
        )

        # Auto-save dismissed concerns to resolved database (for future filtering)
        saved_count = 0
        for e in dismissed:
            if len(e.reasoning) > 100:
                pattern = e.concern.text[:100].strip()
                if pattern:
                    add_resolved_concern(
                        pattern=pattern,
                        explanation=e.reasoning[:500],
                        adversary=e.concern.adversary,
                        spec_hash=spec_hash,
                        confidence=0.85,
                    )
                    saved_count += 1

        if saved_count > 0:
            print(f"Saved {saved_count} dismissal explanations for future filtering", file=sys.stderr)

        # Update adversary statistics for continuous improvement
        update_adversary_stats(result)

        # Save full run log for analysis and debugging
        run_file = save_gauntlet_run(result, spec)
        run_id = Path(run_file).stem
        print(f"Run log saved: {run_file}", file=sys.stderr)

        # Calculate and save medal awards (only for 6+ adversary runs)
        medals = calculate_medals(result, spec_hash, run_id)
        if medals:
            medal_file = save_medal_reports(medals)
            print(f"Medals awarded: {len(medals)} (saved to {medal_file})", file=sys.stderr)
            result.medals = medals  # type: ignore[attr-defined]

        # Finalize manifest
        update_run_manifest(manifest_path, {"status": "completed"})

        return result

    except KeyboardInterrupt:
        if manifest_path:
            update_run_manifest(manifest_path, {"status": "interrupted"})
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)

    finally:
        # Restore input() if we monkey-patched it
        if original_input is not None:
            import builtins
            builtins.input = original_input
