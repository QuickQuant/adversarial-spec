#!/usr/bin/env python3
"""
Hook: unverified_claims
Practice: Section 4 - Documentation-First API Integration (enforcement layer)
Version: flexible=1.0.0, strict=1.0.0
Hash: See practices_registry.json

Detects when Claude makes claims about features/capabilities without evidence
of actually checking documentation or code first.

This catches the dangerous failure mode of CONFIDENT HALLUCINATION - where
Claude states something as fact without hedging (so assumption_detection
doesn't catch it) but also without verification.
"""

import sys
import json
import re
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

def load_config():
    config_path = Path(__file__).parent / "hook_config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {"mode": "flexible"}

CONFIG = load_config()
MODE = CONFIG.get("unverified_claims_mode", CONFIG.get("mode", "flexible"))

# -----------------------------------------------------------------------------
# Patterns that suggest claims about features/docs/APIs
# -----------------------------------------------------------------------------

CLAIM_PATTERNS_FLEXIBLE = [
    r"doesn't have\b",
    r"doesn't support\b",
    r"there's no way to\b",
    r"isn't available\b",
    r"not supported\b",
    r"not possible\b",
    r"can't do\b",
    r"cannot do\b",
    r"no .{0,30} feature\b",
    r"no .{0,30} option\b",
    r"no .{0,30} hook\b",
    r"no .{0,30} API\b",
    r"only way is\b",
    r"only option is\b",
    r"your only .{0,30} is\b",
]

CLAIM_PATTERNS_STRICT = CLAIM_PATTERNS_FLEXIBLE + [
    r"you can't\b",
    r"it won't\b",
    r"there isn't\b",
    r"doesn't exist\b",
    r"no longer available\b",
    r"has been removed\b",
    r"was deprecated\b",
    r"is deprecated\b",
]

# -----------------------------------------------------------------------------
# Domains where claims REQUIRE verification
# If claim is about one of these AND no lookup evidence, flag it
# -----------------------------------------------------------------------------

DOMAINS_REQUIRING_LOOKUP = [
    r"\bclaude\b",
    r"\banthropic\b",
    r"\bAPI\b",
    r"\bhook[s]?\b",
    r"\bMCP\b",
    r"\bVS\s?Code\b",
    r"\bcursor\b",
    r"\bwindsurf\b",
    r"\blangchain\b",
    r"\bopenai\b",
    r"\bconvex\b",
    r"\bpolymarket\b",
    r"\bkalshi\b",
    # Add project-specific domains here
]

# -----------------------------------------------------------------------------
# Tool names that indicate actual lookup happened
# -----------------------------------------------------------------------------

LOOKUP_TOOLS = [
    "web_search",
    "WebSearch",
    "WebFetch",
    "web_fetch",
    "Read",
    "View",
    "Bash",  # could be checking docs/running commands
    "mcp",
]

EXIT_BEHAVIOR = {
    "flexible": {"on_violation": 0, "action": "warn"},
    "strict": {"on_violation": 2, "action": "block"},
}

# =============================================================================
# HOOK LOGIC
# =============================================================================

def get_claim_patterns():
    if MODE == "strict":
        return CLAIM_PATTERNS_STRICT
    return CLAIM_PATTERNS_FLEXIBLE

def has_doc_claims(text: str) -> list[str]:
    """Check if response makes claims about features/capabilities."""
    found = []
    for pattern in get_claim_patterns():
        matches = re.findall(pattern, text, re.IGNORECASE)
        found.extend(matches)
    return found

def is_domain_claim(text: str) -> bool:
    """Check if the text involves domains that require verification."""
    text_lower = text.lower()
    for domain in DOMAINS_REQUIRING_LOOKUP:
        if re.search(domain, text_lower):
            return True
    return False

def has_lookup_evidence(transcript_lines: list[str]) -> bool:
    """Check if transcript shows Claude actually looked something up."""
    for line in transcript_lines:
        try:
            entry = json.loads(line)
            
            # Check for direct tool use
            tool_name = entry.get("tool_name", "")
            if any(lookup.lower() in tool_name.lower() for lookup in LOOKUP_TOOLS):
                return True
            
            # Check message content for tool_use blocks
            msg = entry.get("message", {})
            content = msg.get("content", [])
            
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "tool_use":
                            name = block.get("name", "")
                            if any(lookup.lower() in name.lower() for lookup in LOOKUP_TOOLS):
                                return True
                        if block.get("type") == "tool_result":
                            return True  # There was a tool result in context
                            
        except json.JSONDecodeError:
            continue
    
    return False

def get_last_assistant_response(lines: list[str]) -> str:
    """Extract the last assistant response from transcript lines."""
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
    return ""

def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)
    
    transcript_path = input_data.get("transcript_path", "")
    if not transcript_path:
        sys.exit(0)
    
    try:
        with open(transcript_path, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading transcript: {e}", file=sys.stderr)
        sys.exit(0)
    
    last_response = get_last_assistant_response(lines)
    if not last_response:
        sys.exit(0)
    
    claims = has_doc_claims(last_response)
    
    if claims and is_domain_claim(last_response) and not has_lookup_evidence(lines):
        behavior = EXIT_BEHAVIOR[MODE]
        
        print(f"🚨 UNVERIFIED CLAIM DETECTED [{MODE.upper()} MODE]", file=sys.stderr)
        print("", file=sys.stderr)
        print("You made claims about features/capabilities without checking first:", file=sys.stderr)
        
        for claim in claims[:5]:
            print(f"  ❌ \"{claim}\"", file=sys.stderr)
        
        if len(claims) > 5:
            print(f"  ... and {len(claims) - 5} more", file=sys.stderr)
        
        print("", file=sys.stderr)
        print("No evidence of lookup found in this session (web_search, Read, etc.)", file=sys.stderr)
        
        if behavior["action"] == "block":
            print("", file=sys.stderr)
            print("Search the docs or codebase before stating what is/isn't possible.", file=sys.stderr)
            print("If you're uncertain, say so explicitly rather than stating as fact.", file=sys.stderr)
        
        sys.exit(behavior["on_violation"])
    
    sys.exit(0)

if __name__ == "__main__":
    main()
