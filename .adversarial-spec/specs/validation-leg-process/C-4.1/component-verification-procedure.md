# C-4.1 Component Verification

Verification kind: verification
Altitude obligation: component
Verification mode: automated-unit
Verification scope: targeted

## What Runs

- `uv run pytest scripts/tests/test_validation_emission.py -k "parse_reply or grammar" -q`

## Evidence Required

Automated evidence is the declared pytest command passing with mapped TC coverage.

## Mapped Tests

- Test refs: TC-3.2, TC-3.5, TC-G2, TC-G6, TC-G8
- Test files: scripts/tests/test_validation_emission.py

## Acceptance Criteria Covered

- Block grammar: per_row / bulk_pass (+ fixed natural-alias list) / pass_rest; case-insensitive keywords, exact-case row ids (TG-G2/G8)
- fail+na REQUIRE justification (FM-10); explicit per-row applies before bulk (CB-9); duplicate verdicts invalid; typo'd continuation -> parse error
- Idempotent by reply_ref (processed_reply_refs); edited messages ignored (INV-17, RC-4); invalid/partial -> ZERO mutations + re-prompt quoting truncated untrusted text (INV-A3)
- Owns the locked judgment mutation; writes provenance block (INV-1)

## Traceability

- Architecture refs: .architecture/structured/components/emission-toolchain.md, .architecture/patterns.md
- Concern refs: CB-9, FM-10, RC-4, OP-6, SEC-6-reject
- Invariant refs: INV-1, INV-16, INV-17, INV-A3
