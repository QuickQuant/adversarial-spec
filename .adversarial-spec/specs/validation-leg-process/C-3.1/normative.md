# C-3.1 Component Mini-Spec

Title: record-evidence
Altitude: component
Parent: SS-3
Children: none
Realizes refs: US-13
Requirement ID: C-R301

## Requirement Statement

The component shall satisfy the approved record evidence acceptance criteria.

## Scope

- Implementation status: greenfield
- Behavior change: true
- Verification mode: automated-unit
- Verification scope: targeted
- Strategy: test-first
- Surface scope: cli_command

## Traceability

- Architecture refs: .architecture/structured/components/emission-toolchain.md, .architecture/structured/components/gauntlet.md
- Concern refs: FM-2, FM-4, DD-9, OP-2
- Invariant refs: INV-4, INV-9, INV-12
- Test refs: TC-3.7, TC-G4

## Acceptance Criteria

- Scaffolds validation-evidence/<row_id>/evidence.md canonical front-matter (hashes stamped by module, FM-2); exact keys/order, distinct codes for missing/malformed/hash-mismatch
- Records conductor evidence_summary into ledger row (mutating); binds row_hash+story_hash+commit (INV-9, INV-12)
- Per-story binding: editing one story invalidates only that story's evidence (FM-3/G4)

## Verification Summary

Automated evidence is the declared pytest command passing with mapped TC coverage.
