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
# DATA CLASSES — imported from gauntlet.core_types
# =============================================================================





from pathlib import Path




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
        elif model.startswith("claude-cli/"):
            response, in_tokens, out_tokens = call_claude_cli_model(
                system_prompt="You are an expert at pattern recognition and synthesis.",
                user_message=prompt,
                model=model,
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


def evaluate_concerns_multi_model(
    spec: str,
    concerns: list[Concern],
    models: list[str],
    batch_size: int = 15,
    timeout: int = 300,
) -> list[Evaluation]:
    """
    Phase 4: Evaluate concerns using MULTIPLE models in parallel.

    Runs all batches for each model concurrently (respecting per-provider rate limits),
    and runs different models in parallel with each other. This is much faster than the
    old sequential approach which waited for all models to finish one batch before starting
    the next.

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

    # -------------------------------------------------------------------------
    # Run all batches per model concurrently, respecting per-provider rate limits.
    # Different models run fully in parallel with each other since they have
    # independent rate limits.
    # -------------------------------------------------------------------------

    def run_all_batches_for_model(model: str) -> dict[int, list[Evaluation]]:
        """Run all batches for a single model, respecting its rate limit."""
        rate_batch_size, rate_delay = get_rate_limit_config(model)
        results: dict[int, list[Evaluation]] = {}

        # Group batches into rate-limited waves
        for wave_start in range(0, len(batches), rate_batch_size):
            wave_end = min(wave_start + rate_batch_size, len(batches))
            wave_batches = list(range(wave_start, wave_end))

            if wave_start > 0:
                print(
                    f"  {model}: rate limit pause {rate_delay}s before wave "
                    f"{wave_start // rate_batch_size + 1}...",
                    file=sys.stderr,
                )
                time.sleep(rate_delay)

            # Run all batches in this wave concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(wave_batches)) as wave_executor:
                future_to_idx = {}
                for batch_idx in wave_batches:
                    future = wave_executor.submit(
                        evaluate_concerns, spec, batches[batch_idx], model, timeout
                    )
                    future_to_idx[future] = batch_idx

                for future in concurrent.futures.as_completed(future_to_idx):
                    batch_idx = future_to_idx[future]
                    try:
                        evals = future.result()
                        results[batch_idx] = evals
                        print(
                            f"  {model}: batch {batch_idx + 1}/{len(batches)} done "
                            f"({len(evals)} evals)",
                            file=sys.stderr,
                        )
                    except Exception as e:
                        print(
                            f"  Warning: {model} batch {batch_idx + 1} failed: {e}",
                            file=sys.stderr,
                        )
                        results[batch_idx] = []

        return results

    # Launch all models in parallel — each manages its own rate limiting internally
    model_all_results: dict[str, dict[int, list[Evaluation]]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(eval_models)) as model_executor:
        model_futures = {
            model_executor.submit(run_all_batches_for_model, m): m
            for m in eval_models
        }
        for future in concurrent.futures.as_completed(model_futures):
            model = model_futures[future]
            try:
                model_all_results[model] = future.result()
                total_evals = sum(len(v) for v in model_all_results[model].values())
                print(f"  {model}: all batches complete ({total_evals} evals)", file=sys.stderr)
            except Exception as e:
                print(f"  Warning: {model} failed entirely: {e}", file=sys.stderr)
                model_all_results[model] = {}

    # -------------------------------------------------------------------------
    # Build consensus across models for each concern
    # -------------------------------------------------------------------------
    all_evaluations: list[Evaluation] = []
    disagreements = 0

    for batch_idx, batch in enumerate(batches):
        for i, concern in enumerate(batch):
            verdicts = {}
            reasonings = {}

            for model in eval_models:
                batch_results = model_all_results.get(model, {}).get(batch_idx, [])
                if i < len(batch_results):
                    eval_item = batch_results[i]
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
# MODEL DISPATCH — imported from gauntlet.model_dispatch
# =============================================================================


# =============================================================================
# PHASE 1: ATTACK GENERATION
# =============================================================================


def generate_attacks(
    spec: str,
    adversaries: list[str],
    models: list[str] | str,
    timeout: int = 300,
    codex_reasoning: str = "low",
) -> tuple[list[Concern], dict[str, float], dict[str, str]]:
    """
    Phase 1: Generate attacks from all adversary personas in parallel.

    Args:
        spec: The specification to attack
        adversaries: List of adversary keys to use
        models: Model(s) to use for attack generation
        timeout: Timeout per adversary call
        codex_reasoning: Reasoning effort for Codex attacks (default: "low" to conserve tokens)

    Returns:
        Tuple of (List of Concern objects, dict of adversary@model -> elapsed time in seconds,
                  dict of adversary@model -> raw LLM response text)
    """
    if isinstance(models, str):
        models = [models]
    models = [m.strip() for m in models if m and m.strip()]
    if not models:
        raise ValueError("At least one attack model is required")

    concerns: list[Concern] = []
    timing: dict[str, float] = {}  # Track time per adversary@model
    raw_responses: dict[str, str] = {}  # Track raw LLM responses for debugging

    def run_adversary_with_model(adversary_key: str, model: str) -> tuple[list[Concern], float, str]:
        """Run one adversary with one model and return concerns with timing."""
        start = time.time()
        adversary = ADVERSARIES.get(adversary_key)
        if not adversary:
            print(f"Warning: Unknown adversary '{adversary_key}'", file=sys.stderr)
            return [], 0.0, ""

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
                elif current_concern_lines:
                    # Continuation prose — append to current concern
                    current_concern_lines.append(line)
                # Only truly ignore lines before the first numbered item

            # Flush final concern
            flush_concern()

            # Warn if concerns look like bare quotes (possible parse issue)
            for c in local_concerns:
                if len(c.text) < 80 and ("quote" in c.text.lower() or c.text.startswith('"')):
                    print(
                        f"Warning: Concern from {adversary_key} looks like a bare quote "
                        f"(possible parse issue): {c.text[:60]}...",
                        file=sys.stderr,
                    )

            elapsed = time.time() - start
            return local_concerns, elapsed, response

        except Exception as e:
            print(
                f"Warning: Adversary {adversary_key} failed: {e}",
                file=sys.stderr,
            )
            return [], time.time() - start, ""

    # Run adversary/model pairs in batches, respecting provider rate limits.
    # Group pairs by provider so we can batch same-provider calls together.
    pairs = [(adv, model) for adv in adversaries for model in models]

    # Group by provider for rate limiting
    from collections import defaultdict
    by_provider: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for adv, model in pairs:
        by_provider[_get_model_provider(model)].append((adv, model))

    def collect_result(future, adv_key, model):
        adv_concerns, elapsed, raw_response = future.result()
        concerns.extend(adv_concerns)
        timing[f"{adv_key}@{model}"] = elapsed
        if raw_response:
            raw_responses[f"{adv_key}@{model}"] = raw_response

    # Process each provider's pairs in rate-limited batches, but run
    # different providers concurrently since they have independent limits.
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, len(pairs) or 1)) as executor:
        for provider, provider_pairs in by_provider.items():
            batch_size, batch_delay = get_rate_limit_config(provider_pairs[0][1])

            for batch_idx in range(0, len(provider_pairs), batch_size):
                batch = provider_pairs[batch_idx:batch_idx + batch_size]
                if batch_idx > 0:
                    # Stagger batches for the same provider
                    print(
                        f"  Rate limit pause: {batch_delay}s before {provider} batch "
                        f"{batch_idx // batch_size + 1}/{(len(provider_pairs) + batch_size - 1) // batch_size}...",
                        file=sys.stderr,
                    )
                    time.sleep(batch_delay)

                batch_futures = {
                    executor.submit(run_adversary_with_model, adv, model): (adv, model)
                    for adv, model in batch
                }
                # Wait for this batch to complete before submitting next batch
                # for the same provider (rate limit enforcement)
                for future in concurrent.futures.as_completed(batch_futures):
                    adv_key, model = batch_futures[future]
                    collect_result(future, adv_key, model)

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

    return concerns, timing, raw_responses


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
    raw_concerns, adversary_timing, attack_raw_responses = generate_attacks(
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
        timeout=timeout,
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
            timeout=timeout,
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
        timeout=timeout,
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
            timeout=max(timeout, 600),  # Final Boss needs at least 600s (Opus 4.6 + large context)
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
