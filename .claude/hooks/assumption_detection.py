#!/usr/bin/env python3
"""
Hook: assumption_detection
Practice: Section 6 - Assumption Detection – Banned Language
Version: flexible=1.1.0, strict=1.1.0
Hash: See practices_registry.json

Scans Claude's response for banned "fuzzy" language that hides unknowns.
"""

import sys
import json
import re
from pathlib import Path

# =============================================================================
# CONFIGURATION - Edit these for flexible vs strict modes
# =============================================================================

# Load mode from environment or config
def load_config():
    config_path = Path(__file__).parent / "hook_config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {"mode": "flexible"}  # default

CONFIG = load_config()
MODE = CONFIG.get("assumption_detection_mode", CONFIG.get("mode", "flexible"))

# -----------------------------------------------------------------------------
# FLEXIBLE MODE: Warn but don't block
# STRICT MODE: Block and require revision
# -----------------------------------------------------------------------------

BANNED_PATTERNS_FLEXIBLE = [
    (r"(?<!without\s)\bassuming\b", "uncertainty"),
    (r"\bprobably\b", "uncertainty"),
    (r"\blikely\b", "uncertainty"),
    (r"\bshould be\b", "uncertainty"),
    (r"\btypically\b", "uncertainty"),
    (r"\busually\b", "uncertainty"),
    (r"\bI think\b", "uncertainty"),
    (r"\bseems like\b", "uncertainty"),
    (r"\bmay not\b", "uncertainty"),
    (r"\bmight\b", "uncertainty"),
    (r"\bcould be\b", "uncertainty"),
    (r"\bperhaps\b", "uncertainty"),
]

# Strict mode adds additional patterns
BANNED_PATTERNS_STRICT = BANNED_PATTERNS_FLEXIBLE + [
    (r"\bmaybe\b", "uncertainty"),
    (r"\bI believe\b", "uncertainty"),
    (r"\bI assume\b", "uncertainty"),
]

ADVISORY_MESSAGE = (
    "You've used a word indicating uncertainty with your analysis. "
    "If there is anything you need to run, web search you need to make, "
    "documentation to read, or architecture you need to explore to come up "
    "with a better answer, you may take the time to do so if you believe "
    "that coming up with a more accurate answer will help the user. "
    "If the user expected you to be guessing or otherwise indicated that you "
    "were supposed to give some attempt at an answer without being robust, "
    "you may ignore this."
)

# Exit behavior. Exit 2 on Stop sends stderr back to the model.
EXIT_BEHAVIOR = {
    "flexible": {"on_violation": 2, "action": "advise"},
    "strict": {"on_violation": 2, "action": "block"},
}

# =============================================================================
# HOOK LOGIC
# =============================================================================

def get_banned_patterns():
    if MODE == "strict":
        return BANNED_PATTERNS_STRICT
    return BANNED_PATTERNS_FLEXIBLE

def scan_for_assumptions(text: str) -> list[tuple[str, str, str]]:
    """Returns list of (matched_text, pattern, suggestion) tuples."""
    violations = []
    patterns = get_banned_patterns()
    
    for pattern, suggestion in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            # Get surrounding context (up to 50 chars each side)
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end].replace('\n', ' ')
            violations.append((match.group(), context, suggestion))
    
    return violations

def get_last_assistant_response(transcript_path: str) -> str:
    """Concatenate every text block from the most recent assistant turn.

    A turn spans all assistant entries since the last user entry. Each entry
    can contain thinking/text/tool_use blocks across separate JSONL lines, so
    a single reverse-iterated entry is not enough — earlier code returned the
    first hit, which was empty when the latest entry was tool_use or thinking.
    """
    try:
        with open(transcript_path, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading transcript: {e}", file=sys.stderr)
        return ""

    texts = []
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        entry_type = entry.get("type")
        content = entry.get("message", {}).get("content", "")
        if entry_type == "user":
            # Real user message = string content, or a list with no tool_result.
            # Tool result echoes are also type=user but only carry tool_result blocks.
            if isinstance(content, str) and content.strip():
                break
            if isinstance(content, list) and not any(
                isinstance(b, dict) and b.get("type") == "tool_result" for b in content
            ):
                break
            continue
        if entry_type != "assistant":
            continue
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    texts.append(block.get("text", ""))

    texts.reverse()
    return " ".join(t for t in texts if t)

def main():
    # Read hook payload from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)  # No input, nothing to check
    
    transcript_path = input_data.get("transcript_path", "")
    if not transcript_path:
        sys.exit(0)
    
    response = get_last_assistant_response(transcript_path)
    if not response:
        sys.exit(0)
    
    violations = scan_for_assumptions(response)
    
    if violations:
        behavior = EXIT_BEHAVIOR[MODE]
        matched_phrases = sorted({v[0].lower() for v in violations})

        print(ADVISORY_MESSAGE, file=sys.stderr)
        print("", file=sys.stderr)
        print(f"Triggered by: {', '.join(repr(p) for p in matched_phrases)}", file=sys.stderr)

        if behavior["action"] == "block":
            print("", file=sys.stderr)
            print("Strict mode: revise before stopping.", file=sys.stderr)

        sys.exit(behavior["on_violation"])

    sys.exit(0)

if __name__ == "__main__":
    main()
