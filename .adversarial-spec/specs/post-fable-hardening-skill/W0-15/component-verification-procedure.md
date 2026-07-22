# W0-15 Component Verification

Task: Executable adverse suite (Phase 4 residual obligation)

Acceptance criteria:
- all 13 R5 cases red-green against real modules
- R4 canonical-sequence traversal incl. snapshot registration
- suite runs under the standard runner

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/adverse/test_adverse_suite.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-008, INV-017, INV-020, INV-021; concerns RC-1, RC-2, RC-3, SEC-3, SEC-4.
