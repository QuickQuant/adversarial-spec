# SS-W0 Component Verification

Task: Shared hardening substrate

Acceptance criteria:
- every MW candidate lands as its own verified component
- adverse suite green over the real substrate

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests -q`

Evidence: pytest output showing collected+run tests for the named files; invariants n/a; concerns n/a.
