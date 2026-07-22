# W0-1 Component Mini-Spec

Title: Scaffold hardening package + Python 3.14 floor

Create skills/adversarial-spec/scripts/hardening/ per the target-architecture component tree; bump requires-python to >=3.14; pin rfc8785==0.1.4 + cryptography==49.0.0; clean-env wheel-install test. No upward import from gauntlet.

Acceptance criteria:
- hardening package imports cleanly on 3.14
- uv run adversarial-spec --help still works (symlink bridge preserved)
- clean-env wheel-install test green

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task W0-1.
Implementation status: greenfield — no hardening/ dir exists (ls -> ENOENT, verified 2026-07-21)
