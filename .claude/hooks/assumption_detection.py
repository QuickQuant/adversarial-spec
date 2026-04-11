#!/usr/bin/env python3
"""
Hook: assumption_detection
Practice: Section 6 - Assumption Detection – Banned Language
Version: flexible=1.0.0, strict=1.0.0
Hash: See practices_registry.json

Scans Claude's response for banned "fuzzy" language that hides unknowns.
"""

import json
import re
import sys
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
    (r"\bassuming\b", "Look up the answer in documentation or code"),
    (r"\bprobably\b", "Ask the user or verify with concrete evidence"),
    (r"\blikely\b", "Find an existing pattern or tested example"),
    (r"\bshould be\b", "Verify with concrete tests or logs"),
    (r"\btypically\b", "Anchor behavior in explicit specs or configs"),
    (r"\busually\b", "Anchor behavior in explicit specs or configs"),
    (r"\bI think\b", "Verify or ask user for clarification"),
    (r"\bseems like\b", "Verify or ask user for clarification"),
]

# Strict mode adds additional patterns
BANNED_PATTERNS_STRICT = BANNED_PATTERNS_FLEXIBLE + [
    (r"\bmaybe\b", "Determine definitively or ask"),
    (r"\bmight\b", "Verify the condition explicitly"),
    (r"\bcould be\b", "Test or verify the assumption"),
    (r"\bperhaps\b", "Resolve the uncertainty before proceeding"),
    (r"\bI believe\b", "Cite source or verify"),
    (r"\bI assume\b", "Never assume - look it up"),
]

# Exit behavior
EXIT_BEHAVIOR = {
    "flexible": {"on_violation": 0, "action": "warn"},      # warn only
    "strict": {"on_violation": 2, "action": "block"},       # block and revise
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
    """Extract the last assistant response from transcript."""
    try:
        with open(transcript_path, 'r') as f:
            lines = f.readlines()

        for line in reversed(lines):
            try:
                entry = json.loads(line)
                if entry.get("type") == "assistant":
                    msg = entry.get("message", {})
                    content = msg.get("content", "")

                    if isinstance(content, str):
                        return content
                    elif isinstance(content, list):
                        return " ".join(
                            block.get("text", "")
                            for block in content
                            if isinstance(block, dict) and block.get("type") == "text"
                        )
            except json.JSONDecodeError:
                continue
    except Exception as e:
        print(f"Error reading transcript: {e}", file=sys.stderr)

    return ""

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

        print(f"🚨 ASSUMPTION DETECTION [{MODE.upper()} MODE]", file=sys.stderr)
        print(f"Found {len(violations)} banned phrase(s):", file=sys.stderr)
        print("", file=sys.stderr)

        for matched, context, suggestion in violations[:5]:  # Limit output
            print(f"  ❌ \"{matched}\"", file=sys.stderr)
            print(f"     Context: ...{context}...", file=sys.stderr)
            print(f"     → {suggestion}", file=sys.stderr)
            print("", file=sys.stderr)

        if len(violations) > 5:
            print(f"  ... and {len(violations) - 5} more", file=sys.stderr)

        if behavior["action"] == "block":
            print("", file=sys.stderr)
            print("Revise your response: Replace vague language with concrete lookups,", file=sys.stderr)
            print("explicit questions to the user, or clear 'I don't know' statements.", file=sys.stderr)

        sys.exit(behavior["on_violation"])

    sys.exit(0)

if __name__ == "__main__":
    main()
