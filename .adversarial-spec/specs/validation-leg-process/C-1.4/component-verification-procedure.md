# C-1.4 Component Verification

Verification kind: verification
Altitude obligation: component
Verification mode: automated-unit
Verification scope: targeted

## What Runs

- `uv run pytest scripts/tests/test_validation_emission.py -k "path or bounds" -q`

## Evidence Required

Automated evidence is the declared pytest command passing with mapped TC coverage.

## Mapped Tests

- Test refs: TC-2.6, TC-1.4
- Test files: scripts/tests/test_validation_emission.py

## Acceptance Criteria Covered

- Subcommands resolve artifact paths under spec root via realpath; symlinks/escapes rejected (SEC-9)
- Input bounds enforced: reply 16KB, justification 2KB, ledger 5MB, ConOps 1MB -> structured exit-2 (SEC-10)
- row_id global uniqueness incl. superseded; duplicate manifest story ids -> exit 2

## Traceability

- Architecture refs: .architecture/structured/components/session.md, .architecture/patterns.md
- Concern refs: SEC-9, SEC-10, OP-3
- Invariant refs: INV-A3
