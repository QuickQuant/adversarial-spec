# A-2 Component Verification

Task: Hook-plane dispatcher + conformance fixtures

Acceptance criteria:
- duplicate handler detected + cross-surface fixture agreement (TC-2.4)
- internal failure becomes DENY for safety dispatchers
- async/exit-1/raise/malformed classifier cases never skip later blockers

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_hook_dispatcher_conformance.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-011; concerns DD-2.
