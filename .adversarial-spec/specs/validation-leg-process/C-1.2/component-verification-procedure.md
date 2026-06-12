# C-1.2 Component Verification

Verification kind: verification
Altitude obligation: component
Verification mode: automated-unit
Verification scope: targeted

## What Runs

- `uv run pytest scripts/tests/test_validation_emission.py -k "lock or corrupt or atomic" -q`

## Evidence Required

Automated evidence is the declared pytest command passing with mapped TC coverage.

## Mapped Tests

- Test refs: TC-3.9
- Test files: scripts/tests/test_validation_emission.py

## Acceptance Criteria Covered

- filelock.FileLock 10s timeout -> exit 3 LEDGER_BUSY with owner-pid/lock-age when readable
- Every mutation read->mutate->atomic tmp+rename INSIDE the lock; crash mid-write leaves prior ledger intact, no .tmp litter (TC-3.9c)
- Malformed ledger -> exit 3 LEDGER_CORRUPT; corrupt bytes copied to validation-rows.json.corrupt-<ts> first; never auto-repaired
- Single mutation helper requiring the lock; read-only subcommands have no write path (INV-A2)

## Traceability

- Architecture refs: .architecture/structured/flows.md, .architecture/structured/components/gauntlet.md, .architecture/patterns.md
- Concern refs: FM-7, DD-6, US-8(filelock-semantics), DIS-1(10s-noted)
- Invariant refs: INV-A2
