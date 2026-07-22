# C-5 Component Verification

Task: Critic-runner stdout contract + provenance-coupled salvage

Acceptance criteria:
- DF-17 parser edge fixtures green
- crash-injected salvage never exposes artifact without provenance record
- salvaged report recorded as violation evidence, never raw return

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_critic_output_contract.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-015; concerns DD-4.
