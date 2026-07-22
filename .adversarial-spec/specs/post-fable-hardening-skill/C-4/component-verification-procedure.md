# C-4 Component Verification

Task: False-convergence guard: quorum, press, Phase 4 exit gate

Acceptance criteria:
- card-5715 R3/R7 replays flagged (TC-14.2)
- failed press excludes AGREE from quorum (TC-14.4)
- DF-15 induced round registries green

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_convergence_guard.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-013; concerns DD-1.
