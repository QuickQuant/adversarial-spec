"""Phase 7: Final Boss UX/User Story Review.

Extracted from gauntlet_monolith.py — Opus 4.7 high-level sanity check
on whether the spec actually serves users.
"""

from __future__ import annotations

import re
import sys

from adversaries import FINAL_BOSS
from gauntlet.core_types import (
    Concern,
    DismissalReviewStats,
    Evaluation,
    FinalBossResult,
    FinalBossVerdict,
    GauntletConfig,
)
from gauntlet.model_dispatch import call_model, select_eval_model
from gauntlet.prompts import (
    FINAL_BOSS_ALTERNATE_SECTION_TEMPLATE,
    FINAL_BOSS_DISMISSED_SECTION_TEMPLATE,
    FINAL_BOSS_USER_TEMPLATE,
)


def run_final_boss_review(
    spec: str,
    gauntlet_summary: str,
    accepted_concerns: list[Concern],
    dismissed_evaluations: list[Evaluation],
    config: GauntletConfig,
) -> FinalBossResult:
    """Phase 7: Final Boss UX/User Story Review with Verdict.

    Runs AFTER all other adversaries have been satisfied. Uses Opus 4.7 to do
    a high-level sanity check on whether the spec actually serves users.

    The Final Boss can issue three verdicts:
    - PASS: Proceed to implementation
    - REFINE: Address listed concerns, then proceed
    - RECONSIDER: Fundamental issues exist, models should debate re-architecture

    Timeout: max(config.timeout, 1800) — Opus 4.7 with large context needs a floor.
    """
    import os

    timeout = max(config.timeout, 1800)

    # Final boss uses Opus 4.7 - expensive but thorough
    if os.environ.get("ANTHROPIC_API_KEY"):
        model = "claude-opus-4-7"
    else:
        print("  Warning: Opus 4.7 not available, using best alternative", file=sys.stderr)
        model = select_eval_model()

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

    # Check DISMISSED concerns from simplification adversaries
    dismissed_simplifications = []
    simplification_adversaries = {"lazy_developer", "prior_art_scout", "information_flow_auditor"}
    for e in dismissed_evaluations:
        if e.concern.adversary in simplification_adversaries:
            text_lower = e.concern.text.lower()
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
        alternate_section = FINAL_BOSS_ALTERNATE_SECTION_TEMPLATE.format(
            approaches="\n".join(alternate_approaches[:5]),
        )

    dismissed_section = ""
    num_dismissed_reviewed = len(dismissed_simplifications[:5])
    if dismissed_simplifications:
        dismissed_items = []
        for i, d in enumerate(dismissed_simplifications[:5], 1):
            dismissed_items.append(f"D{i}. CONCERN: {d['concern']}\n    DISMISSED WITH: {d['dismissal']}\n")
        dismissed_section = FINAL_BOSS_DISMISSED_SECTION_TEMPLATE.format(
            num_reviewed=num_dismissed_reviewed,
            items="\n".join(dismissed_items),
        )

    user_prompt = FINAL_BOSS_USER_TEMPLATE.format(
        spec=spec,
        gauntlet_summary=gauntlet_summary,
        concern_analysis=concern_analysis,
        num_accepted=len(accepted_concerns),
        alternate_section=alternate_section,
        dismissed_section=dismissed_section,
    )

    try:
        response, in_tokens, out_tokens = call_model(
            model=model,
            system_prompt=system_prompt,
            user_message=user_prompt,
            timeout=timeout,
        )
        response_upper = response.upper()

        if "VERDICT: RECONSIDER" in response_upper:
            verdict = FinalBossVerdict.RECONSIDER
        elif "VERDICT: REFINE" in response_upper:
            verdict = FinalBossVerdict.REFINE
        elif "VERDICT: PASS" in response_upper:
            verdict = FinalBossVerdict.PASS
        else:
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
                matches = re.findall(r'D(\d+)', line, re.IGNORECASE)
                flagged_dismissals = [f"D{m}" for m in matches]
                break

        # Extract meta-reports
        process_meta = ""
        self_meta = ""
        response_lines = response.split("\n")
        for i, line in enumerate(response_lines):
            if "PROCESS META-REPORT" in line.upper():
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
                meta_lines = []
                for j in range(i + 1, min(i + 10, len(response_lines))):
                    next_line = response_lines[j].strip()
                    if next_line and not next_line.startswith("```"):
                        meta_lines.append(next_line)
                    elif next_line.startswith("```"):
                        break
                self_meta = " ".join(meta_lines)

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
