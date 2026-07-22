# W0-2 Component Verification

Task: MW-001 StrictArtifactCodec + canonical_sets

Acceptance criteria:
- byte-level conformance suite (DF-1) green incl. signed-bytes and profile cases
- provisional vs committed deferral facts hash differently
- duplicate set members rejected, never deduplicated

Verify commands:
- `uv run pytest skills/adversarial-spec/scripts/tests/test_strict_artifact_codec.py skills/adversarial-spec/scripts/tests/test_canonical_sets.py -q`

Evidence: pytest output showing collected+run tests for the named files; invariants INV-002, INV-005, INV-020, INV-023; concerns CB-2, SEC-1.
