# C-3 Component Verification

Task: Freeze enforcement: debate.py payload assembly seam

Acceptance criteria:
- frozen-bytes mutation blocks dispatch (TC-11.3)
- real parser on induced fragments (TC-11.4)
- round N+1 carries exactly the volatile surface

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_freeze_payload_assembly.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-013; concerns n/a.
