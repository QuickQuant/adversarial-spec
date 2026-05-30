#!/usr/bin/env python3
"""
Hook: uv_run_check
Practice: Section 2b - Environment and Tooling (Python 3.14 + uv)
Version: flexible=1.0.0, strict=1.0.0
Hash: See practices_registry.json

Checks that Python commands use `uv run` instead of direct `python` calls.
Runs on PostToolUse for Write|Edit|MultiEdit operations (documentation/scripts).
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
MODE = CONFIG.get("uv_run_check_mode", CONFIG.get("mode", "flexible"))

# -----------------------------------------------------------------------------
# Wrong patterns - direct python without uv run
# -----------------------------------------------------------------------------

WRONG_PATTERNS_FLEXIBLE = [
    (r"^python\s+\w+\.py", "Use 'uv run python script.py' instead of 'python script.py'"),
    (r"^python3\s+\w+\.py", "Use 'uv run python script.py' instead of 'python3 script.py'"),
    (r"^python\s+-m\s+", "Use 'uv run python -m <module>' instead of 'python -m <module>'"),
    (r"^pip\s+install\b", "Use 'uv add <package>' for dependencies, not 'pip install'"),
]

WRONG_PATTERNS_STRICT = WRONG_PATTERNS_FLEXIBLE + [
    (r"^pip\s+", "All pip commands should use uv equivalents"),
    (r"requirements\.txt", "Use pyproject.toml as source of truth, not requirements.txt"),
    (r"^pytest\b(?!\s)", "Use 'uv run pytest' instead of bare 'pytest'"),
    (r"^ruff\b(?!\s)", "Use 'uvx ruff' instead of bare 'ruff'"),
]

# Patterns that are OK (don't flag these)
ACCEPTABLE_PATTERNS = [
    r"uv run python",
    r"uv run pytest",
    r"uvx ruff",
    r"uvx ty",
    r"uv add",
    r"uv sync",
    r"uv pip",  # uv pip is OK
]

EXIT_BEHAVIOR = {
    "flexible": {"on_violation": 0, "action": "warn"},
    "strict": {"on_violation": 2, "action": "block"},
}

# =============================================================================
# HOOK LOGIC
# =============================================================================

def get_wrong_patterns():
    if MODE == "strict":
        return WRONG_PATTERNS_STRICT
    return WRONG_PATTERNS_FLEXIBLE

def is_acceptable(line: str) -> bool:
    """Check if the line uses acceptable patterns."""
    for pattern in ACCEPTABLE_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False

def scan_for_wrong_python_usage(content: str, filepath: str) -> list[tuple[int, str, str]]:
    """Returns list of (line_number, line_content, suggestion) tuples."""
    violations = []
    lines = content.split('\n')
    
    # Check in markdown, shell scripts, and documentation
    relevant_extensions = ['.md', '.sh', '.bash', '.rst', '.txt']
    is_relevant = any(filepath.endswith(ext) for ext in relevant_extensions)
    
    # Also check code blocks in any file
    in_code_block = False
    
    patterns = get_wrong_patterns()
    
    for i, line in enumerate(lines, 1):
        # Track code blocks
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            continue
        
        # Skip if line is acceptable
        if is_acceptable(line):
            continue
        
        # Only check in code blocks or relevant files
        if not (in_code_block or is_relevant):
            continue
        
        # Check each wrong pattern
        stripped = line.strip()
        for pattern, suggestion in patterns:
            if re.search(pattern, stripped, re.IGNORECASE):
                violations.append((i, stripped[:80], suggestion))
                break
    
    return violations

def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)
    
    tool_input = input_data.get("tool_input", {})
    
    filepath = tool_input.get("file_path", tool_input.get("path", ""))
    content = tool_input.get("content", tool_input.get("file_text", ""))
    
    if not content or not filepath:
        sys.exit(0)
    
    violations = scan_for_wrong_python_usage(content, filepath)
    
    if violations:
        behavior = EXIT_BEHAVIOR[MODE]
        
        print(f"⚠️ PYTHON ENVIRONMENT VIOLATION [{MODE.upper()} MODE]", file=sys.stderr)
        print("", file=sys.stderr)
        print("This project uses uv for Python dependency management.", file=sys.stderr)
        print(f"File: {filepath}", file=sys.stderr)
        print("", file=sys.stderr)
        
        for line_num, line_content, suggestion in violations[:5]:
            print(f"  Line {line_num}: {line_content}", file=sys.stderr)
            print(f"    → {suggestion}", file=sys.stderr)
            print("", file=sys.stderr)
        
        if len(violations) > 5:
            print(f"  ... and {len(violations) - 5} more", file=sys.stderr)
        
        print("", file=sys.stderr)
        print("Correct commands:", file=sys.stderr)
        print("  uv run python script.py", file=sys.stderr)
        print("  uv run python -m <module>", file=sys.stderr)
        print("  uv run pytest", file=sys.stderr)
        print("  uvx ruff check --fix", file=sys.stderr)
        
        sys.exit(behavior["on_violation"])
    
    sys.exit(0)

if __name__ == "__main__":
    main()
