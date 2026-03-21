"""Phase 2: Big Picture Synthesis.

Extracted from gauntlet_monolith.py — holistic concern analysis before
evaluation. Uses inline litellm dispatch (not call_model).
"""

from __future__ import annotations

import sys

from gauntlet.core_types import BigPictureSynthesis, Concern, GauntletConfig
from models import (
    call_claude_cli_model,
    call_codex_model,
    call_gemini_cli_model,
    cost_tracker,
)

try:
    from litellm import completion
except ImportError:
    print(
        "Error: litellm package not installed. Run: pip install litellm",
        file=sys.stderr,
    )
    raise


# =============================================================================
# PROMPT
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
    config: GauntletConfig,
) -> BigPictureSynthesis:
    """Generate a holistic analysis of all concerns before evaluation.

    Synthesizes insights by looking at the full picture:
    - What are the real issues across all concerns?
    - Hidden connections between different adversaries' concerns
    - What's missing - blind spots no one caught
    - The meta-concern that ties everything together
    """
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
        # Use inline dispatch (not call_model) — extract as-is per spec
        if model.startswith("codex/"):
            response, in_tokens, out_tokens = call_codex_model(
                model=model.replace("codex/", ""),
                system_prompt="You are an expert at pattern recognition and synthesis.",
                user_message=prompt,
                timeout=config.timeout,
            )
        elif model.startswith("gemini-cli/"):
            response, in_tokens, out_tokens = call_gemini_cli_model(
                model=model.replace("gemini-cli/", ""),
                system_prompt="You are an expert at pattern recognition and synthesis.",
                user_message=prompt,
                timeout=config.timeout,
            )
        elif model.startswith("claude-cli/"):
            response, in_tokens, out_tokens = call_claude_cli_model(
                system_prompt="You are an expert at pattern recognition and synthesis.",
                user_message=prompt,
                model=model,
                timeout=config.timeout,
            )
        else:
            result = completion(
                model=model,
                messages=[
                    {"role": "system", "content": "Expert at pattern recognition."},
                    {"role": "user", "content": prompt},
                ],
                timeout=config.timeout,
            )
            response = result.choices[0].message.content
            in_tokens = result.usage.prompt_tokens if result.usage else 0
            out_tokens = result.usage.completion_tokens if result.usage else 0

        cost_tracker.add(model, in_tokens, out_tokens)

        def extract_list(marker: str) -> list[str]:
            items = []
            if marker in response:
                start = response.find(marker) + len(marker)
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
