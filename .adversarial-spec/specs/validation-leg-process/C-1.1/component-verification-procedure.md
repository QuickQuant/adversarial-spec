# C-1.1 Component Verification

Verification kind: verification
Altitude obligation: component
Verification mode: automated-unit
Verification scope: targeted

## What Runs

- `uv run pytest scripts/tests/test_validation_emission.py -k envelope -q`

## Evidence Required

Automated evidence is the declared pytest command passing with mapped TC coverage.

## Mapped Tests

- Test refs: TC-3.9
- Test files: scripts/tests/test_validation_emission.py, uv run pytest scripts/tests/test_validation_emission.py -k envelope -q

## Acceptance Criteria Covered

- argparse dispatch for all 13 subcommands; unknown subcommand -> exit 2 envelope
- Every invocation prints exactly one stdout JSON envelope {status,code,issues:[{code,row_id,detail}],data}; warnings to stderr only (FM-5)
- Exit-code contract 0/2/3 wired at CLI boundary; global issues carry row_id:null
- schema_version + module_version (__version__ + git short hash) stamped on JSON artifacts (OP-4, DD-6); all timestamps UTC RFC3339 Z (OP-3)

## Traceability

- Architecture refs: .architecture/structured/components/emission-toolchain.md, .architecture/structured/components/debate-engine.md, .architecture/patterns.md
- Concern refs: FM-5, OP-3, OP-4, OP-11
- Invariant refs: INV-A3
