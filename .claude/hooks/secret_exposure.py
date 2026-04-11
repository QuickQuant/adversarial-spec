#!/usr/bin/env python3
"""
Hook: secret_exposure
Practice: Section 1 - Absolute Secret-Handling Rules
Version: flexible=1.0.0, strict=1.0.0
Hash: See practices_registry.json

Scans code written by Claude for potential secret exposure patterns.
Runs on PostToolUse for Write|Edit|MultiEdit operations.

CRITICAL: This is a HARD CONSTRAINT with no exceptions.
Both flexible and strict modes BLOCK on violation.
"""

import json
import re
import sys
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
MODE = CONFIG.get("secret_exposure_mode", CONFIG.get("mode", "flexible"))

# -----------------------------------------------------------------------------
# Secret exposure patterns - ALWAYS BLOCK (this is a hard constraint)
# -----------------------------------------------------------------------------

# Environment variable names that typically contain secrets
SECRET_ENV_VARS = [
    r"API_KEY",
    r"API_SECRET",
    r"SECRET_KEY",
    r"PRIVATE_KEY",
    r"PASSWORD",
    r"BEARER_TOKEN",
    r"ACCESS_TOKEN",
    r"REFRESH_TOKEN",
    r"DATABASE_URL",
    r"DB_PASSWORD",
    r"SIGNING_KEY",
    r"ENCRYPTION_KEY",
    r"AUTH_TOKEN",
    r"CLIENT_SECRET",
    r"WEBHOOK_SECRET",
]

# Patterns that indicate secret exposure
EXPOSURE_PATTERNS_FLEXIBLE = [
    # Direct printing of secrets
    (r"print\s*\(\s*os\.getenv\s*\(\s*['\"](" + "|".join(SECRET_ENV_VARS) + r")['\"]", "Direct print of secret env var"),
    (r"print\s*\(\s*['\"].*\{.*(" + "|".join(SECRET_ENV_VARS).lower() + r").*\}.*['\"]", "F-string with secret variable"),
    (r"print\s*\(\s*config", "Print of config object (may contain secrets)"),

    # Logging secrets
    (r"log(ger)?\.(?:info|debug|warn|error)\s*\([^)]*(" + "|".join(SECRET_ENV_VARS).lower() + r")", "Logging secret variable"),
    (r"log(ger)?\.(?:info|debug|warn|error)\s*\(\s*f['\"].*\{.*(?:key|secret|token|password).*\}", "Logging f-string with secret"),

    # Console.log (JavaScript/TypeScript)
    (r"console\.log\s*\([^)]*(?:apiKey|apiSecret|password|token|secret)", "console.log with secret"),
]

EXPOSURE_PATTERNS_STRICT = EXPOSURE_PATTERNS_FLEXIBLE + [
    # Even more conservative patterns
    (r"print\s*\(\s*\w*config\w*\s*\)", "Print of any config-like object"),
    (r"print\s*\(\s*\w*settings\w*\s*\)", "Print of settings object"),
    (r"print\s*\(\s*\w*credentials\w*\s*\)", "Print of credentials object"),
    (r"JSON\.stringify\s*\([^)]*(?:config|settings|credentials)", "JSON.stringify of sensitive object"),
]

# Patterns that are ACCEPTABLE (for reference/documentation)
ACCEPTABLE_PATTERNS = [
    r"if\s+not\s+os\.getenv",  # Checking if env var exists
    r"bool\s*\(\s*os\.getenv",  # Boolean check
    r"print\s*\(['\"]Missing",  # Reporting missing vars
    r"print\s*\(['\"].*is present",  # Confirming var is set
    r"print\s*\(['\"].*configured",  # Configuration status
]

# ALWAYS BLOCK for secrets - this is non-negotiable
EXIT_BEHAVIOR = {
    "flexible": {"on_violation": 2, "action": "block"},  # BLOCK even in flexible
    "strict": {"on_violation": 2, "action": "block"},
}

# =============================================================================
# HOOK LOGIC
# =============================================================================

def get_exposure_patterns():
    if MODE == "strict":
        return EXPOSURE_PATTERNS_STRICT
    return EXPOSURE_PATTERNS_FLEXIBLE

def is_acceptable_pattern(line: str) -> bool:
    """Check if the line matches an acceptable secret-handling pattern."""
    for pattern in ACCEPTABLE_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False

def scan_for_secret_exposure(content: str, filepath: str) -> list[tuple[int, str, str]]:
    """Returns list of (line_number, line_content, violation_reason) tuples."""
    violations = []
    lines = content.split('\n')

    # Only check code files
    code_extensions = ['.py', '.ts', '.js', '.tsx', '.jsx', '.sh', '.bash']
    if not any(filepath.endswith(ext) for ext in code_extensions):
        return violations

    patterns = get_exposure_patterns()

    for i, line in enumerate(lines, 1):
        # Skip if it matches an acceptable pattern
        if is_acceptable_pattern(line):
            continue

        for pattern, reason in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                violations.append((i, line.strip()[:100], reason))
                break  # One violation per line is enough

    return violations

def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    tool_response = input_data.get("tool_response", {})

    # Get file path and content
    filepath = tool_input.get("file_path", tool_input.get("path", ""))
    content = tool_input.get("content", tool_input.get("file_text", ""))

    # For Edit operations, we might need to check the result
    if not content and tool_response:
        content = tool_response.get("result", "")

    if not content or not filepath:
        sys.exit(0)

    violations = scan_for_secret_exposure(content, filepath)

    if violations:
        behavior = EXIT_BEHAVIOR[MODE]

        print("🚨 SECRET EXPOSURE DETECTED - BLOCKING", file=sys.stderr)
        print("", file=sys.stderr)
        print("This is a HARD CONSTRAINT violation. The following code may expose secrets:", file=sys.stderr)
        print(f"File: {filepath}", file=sys.stderr)
        print("", file=sys.stderr)

        for line_num, line_content, reason in violations[:5]:
            print(f"  Line {line_num}: {reason}", file=sys.stderr)
            print(f"    {line_content}", file=sys.stderr)
            print("", file=sys.stderr)

        if len(violations) > 5:
            print(f"  ... and {len(violations) - 5} more violations", file=sys.stderr)

        print("", file=sys.stderr)
        print("ACCEPTABLE alternatives:", file=sys.stderr)
        print("  ✓ Check if var exists: if not os.getenv('API_KEY'): print('Missing API_KEY')", file=sys.stderr)
        print("  ✓ Boolean validation: print(f'Configured: {bool(api_key)}')", file=sys.stderr)
        print("  ✓ Report missing vars: print(f'Missing: {missing_vars}')", file=sys.stderr)
        print("", file=sys.stderr)
        print("Revise the code to use acceptable patterns.", file=sys.stderr)

        sys.exit(behavior["on_violation"])

    sys.exit(0)

if __name__ == "__main__":
    main()
