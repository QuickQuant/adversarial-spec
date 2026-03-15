#!/usr/bin/env python3
"""
Hook: <HOOK_NAME>
Practice: Section X - <Practice Name>
Version: flexible=1.0.0, strict=1.0.0
Hash: See practices_registry.json

<Description of what this hook detects and why>

Hook Type: <Stop|PreToolUse|PostToolUse>
Matcher: <matcher pattern or empty>
"""

import sys
import json
import re
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

def load_config():
    """Load hook configuration from hook_config.json."""
    config_path = Path(__file__).parent / "hook_config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {"mode": "flexible"}

CONFIG = load_config()
# Replace <HOOK_NAME> with actual hook name (e.g., "assumption_detection")
MODE = CONFIG.get("<HOOK_NAME>_mode", CONFIG.get("mode", "flexible"))

# -----------------------------------------------------------------------------
# Detection Patterns
# -----------------------------------------------------------------------------

# Patterns for flexible mode (minimum set)
PATTERNS_FLEXIBLE = [
    # Format: (regex_pattern, message/suggestion)
    # Example: (r"\bprobably\b", "Verify instead of assuming"),
]

# Patterns for strict mode (superset of flexible)
PATTERNS_STRICT = PATTERNS_FLEXIBLE + [
    # Additional patterns only checked in strict mode
]

# Patterns that are acceptable (bypass detection)
ACCEPTABLE_PATTERNS = [
    # Patterns that look like violations but are actually OK
]

# Exit behavior by mode
EXIT_BEHAVIOR = {
    "flexible": {"on_violation": 0, "action": "warn"},   # 0 = warn only
    "strict": {"on_violation": 2, "action": "block"},    # 2 = block, feed to Claude
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_patterns():
    """Get patterns based on current mode."""
    if MODE == "strict":
        return PATTERNS_STRICT
    return PATTERNS_FLEXIBLE

def is_acceptable(text: str) -> bool:
    """Check if text matches an acceptable pattern (false positive prevention)."""
    for pattern in ACCEPTABLE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

# =============================================================================
# FOR STOP HOOKS: Reading transcript
# =============================================================================

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
    except Exception:
        pass
    
    return ""

# =============================================================================
# FOR POST/PRE TOOL USE HOOKS: Reading tool data
# =============================================================================

def get_tool_content(input_data: dict) -> tuple[str, str]:
    """
    Extract filepath and content from tool use payload.
    Returns (filepath, content) tuple.
    """
    tool_input = input_data.get("tool_input", {})
    tool_response = input_data.get("tool_response", {})
    
    filepath = tool_input.get("file_path", tool_input.get("path", ""))
    content = tool_input.get("content", tool_input.get("file_text", ""))
    
    # For Edit operations, content might be in response
    if not content and tool_response:
        content = tool_response.get("result", "")
    
    return filepath, content

# =============================================================================
# DETECTION LOGIC
# =============================================================================

def detect_violations(text: str) -> list[tuple[str, str]]:
    """
    Scan text for violations.
    Returns list of (matched_text, message) tuples.
    """
    violations = []
    patterns = get_patterns()
    
    for pattern, message in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            matched = match.group()
            # Skip if this matches an acceptable pattern
            if not is_acceptable(matched):
                violations.append((matched, message))
    
    return violations

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    # Read hook payload from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)  # No input, nothing to check
    
    # ---------------------------------------------------------------------
    # CHOOSE ONE: Uncomment the appropriate section based on hook type
    # ---------------------------------------------------------------------
    
    # --- FOR STOP HOOKS ---
    # transcript_path = input_data.get("transcript_path", "")
    # if not transcript_path:
    #     sys.exit(0)
    # text_to_check = get_last_assistant_response(transcript_path)
    
    # --- FOR POST/PRE TOOL USE HOOKS ---
    # filepath, text_to_check = get_tool_content(input_data)
    # if not text_to_check:
    #     sys.exit(0)
    
    # ---------------------------------------------------------------------
    # DETECTION
    # ---------------------------------------------------------------------
    
    # Placeholder - replace with actual text source
    text_to_check = ""
    
    if not text_to_check:
        sys.exit(0)
    
    violations = detect_violations(text_to_check)
    
    if violations:
        behavior = EXIT_BEHAVIOR[MODE]
        
        # Output to stderr (shown to user, fed to Claude if exit 2)
        print(f"🚨 <HOOK_NAME> VIOLATION [{MODE.upper()} MODE]", file=sys.stderr)
        print("", file=sys.stderr)
        
        for matched, message in violations[:5]:  # Limit output
            print(f"  ❌ \"{matched}\"", file=sys.stderr)
            print(f"     → {message}", file=sys.stderr)
            print("", file=sys.stderr)
        
        if len(violations) > 5:
            print(f"  ... and {len(violations) - 5} more", file=sys.stderr)
        
        if behavior["action"] == "block":
            print("", file=sys.stderr)
            print("Revise to address these violations.", file=sys.stderr)
        
        sys.exit(behavior["on_violation"])
    
    # No violations
    sys.exit(0)

if __name__ == "__main__":
    main()
