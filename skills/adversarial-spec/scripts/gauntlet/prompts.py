"""Centralized prompt constants for the gauntlet pipeline.

All prompt text used across gauntlet phases lives here. Phase files import
these constants instead of defining prompts inline.

Convention:
- Plain strings for prompts with no interpolation
- str.format() templates for prompts with runtime variables (marked with {var})
- Keep this file in sync with mcp_tasks/server.py:_mutate_tasks cross-ref style
"""

# =============================================================================
# Phase 1: Adversarial Attacks
# =============================================================================

ATTACK_SYSTEM_PROMPT = """You are an adversarial reviewer with this persona:

{persona}

Your job is to find problems with the specification below. Be aggressive.
Output a numbered list of concerns. Each concern should be a potential problem
you've identified. Don't hold back - even if you're not 100% sure, raise it."""

ATTACK_USER_PROMPT = """Review this specification and identify all potential problems:

{spec}

Output your concerns as a numbered list. Be specific and cite parts of the spec."""

ATTACK_USER_PROMPT_JSON = """Review this specification and identify all potential problems:

{spec}

Output your concerns as a JSON object with this exact schema:
{{"concerns": [{{"text": "description of the concern"}}]}}

Be specific and cite parts of the spec. Focus on finding problems, not rating them."""

# =============================================================================
# Phase 2: Big Picture Synthesis
# =============================================================================

SYNTHESIS_SYSTEM_PROMPT = "You are an expert at pattern recognition and synthesis."

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

# =============================================================================
# Phase 3: Filtering & Clustering
# =============================================================================

EXPLANATION_MATCHING_PROMPT = """You are checking if a concern has already been addressed.

Compare the NEW CONCERN against the EXISTING EXPLANATIONS.

STRICT MATCHING RULES:
1. Only match if the explanation DIRECTLY and COMPLETELY addresses the concern
2. Partial matches = NO_MATCH (the concern has aspects not covered)
3. Vague explanations = NO_MATCH (can't verify they apply)
4. Consider the confidence level shown - low confidence means be MORE skeptical

Output ONLY ONE of:
- "MATCH: [index]" - The explanation at [index] FULLY addresses this exact concern
- "NO_MATCH" - No explanation fully covers this concern"""

# =============================================================================
# Phase 4: Evaluation
# =============================================================================

EVALUATION_SYSTEM_PROMPT = """You are a senior engineer evaluating concerns raised by adversarial reviewers.

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

SEVERITY ASSESSMENT (for accepted/acknowledged concerns):
Rate each non-dismissed concern relative to the others in this batch:
- HIGH: Breaks a core invariant, causes data loss, or creates a security hole. Would block implementation.
- MEDIUM: Real problem that needs fixing but has workarounds. Would cause bugs or confusion.
- LOW: Valid but minor — naming issues, edge cases unlikely in practice, cosmetic inconsistencies.
Use the full range. If everything is "medium," you aren't differentiating. Dismissed concerns don't need severity.

Output your evaluation as JSON with this structure:
{{
  "evaluations": [
    {{"concern_index": 0, "verdict": "dismissed|accepted|acknowledged|deferred", "severity": "high|medium|low", "reasoning": "..."}},
    ...
  ]
}}"""

# =============================================================================
# Phase 5: Rebuttals
# =============================================================================

REBUTTAL_SYSTEM_TEMPLATE = """You are an adversarial reviewer with this persona:

{persona}

You raised a concern that was dismissed. Evaluate the dismissal LOGICALLY.

You have two options:

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

REBUTTAL_USER_TEMPLATE = """Your original concern:
{concern_text}

The dismissal reasoning:
{dismissal_reasoning}

Evaluate this dismissal. Output either:
ACCEPTED: [brief acknowledgment] if the reasoning is valid
CHALLENGED: [counter-evidence or logical flaw] if the reasoning is flawed"""

# =============================================================================
# Phase 6: Adjudication
# =============================================================================

ADJUDICATION_SYSTEM_PROMPT = """You are making final decisions on challenged dismissals.

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

# =============================================================================
# Phase 7: Final Boss
# =============================================================================

FINAL_BOSS_ALTERNATE_SECTION_TEMPLATE = """
## ALTERNATE APPROACHES SUGGESTED (ACCEPTED)

The following concerns suggested alternate implementations:

{approaches}

Consider whether these alternates would sidestep many of the other concerns.
"""

FINAL_BOSS_DISMISSED_SECTION_TEMPLATE = """
## DISMISSED SIMPLIFICATION CONCERNS (REVIEW THESE!)

The following {num_reviewed} concerns suggested simpler approaches but were DISMISSED.
**Critically evaluate whether these dismissals properly addressed the alternative:**

{items}

A dismissal is INVALID if it just says "we need X" without proving the simpler approach can't do X.

**If any dismissals are invalid, list them in your output as:**
INVALID DISMISSALS: D1, D3 (etc.)
"""

FINAL_BOSS_USER_TEMPLATE = """## SPECIFICATION TO REVIEW

{spec}

## GAUNTLET RESULTS

This spec has passed through the adversarial gauntlet:

{gauntlet_summary}

## CONCERN DISTRIBUTION BY ADVERSARY

{concern_analysis}

Total accepted concerns: {num_accepted}
{alternate_section}{dismissed_section}
## YOUR TASK

Step back from the technical details. Consider:

1. **USER STORY**: Is this user actually better off?
2. **CONCERN VOLUME**: With {num_accepted} accepted concerns, is this spec trying to do too much?
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
