# A-1 Component Verification

Task: gate_inventory.py + gates.json + doclint

Acceptance criteria:
- TC-1.0 inventory completeness incl. canonical Phases 1-8 + owned subflow units
- unmapped MUST marker fails doclint with file+line (TC-1.2)
- unclassified gate fails check

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_gate_inventory.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-001, INV-010, INV-013; concerns DD-3, US-3-theme.
