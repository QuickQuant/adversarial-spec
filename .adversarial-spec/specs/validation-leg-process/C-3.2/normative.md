# C-3.2 Component Mini-Spec

Title: assemble-digest
Altitude: component
Parent: SS-3
Children: none
Realizes refs: US-6
Requirement ID: C-R302

## Requirement Statement

The component shall satisfy the approved assemble digest acceptance criteria.

## Scope

- Implementation status: greenfield
- Behavior change: true
- Verification mode: automated-unit
- Verification scope: targeted
- Strategy: test-first
- Surface scope: cli_command, outbound_integration

## Traceability

- Architecture refs: .architecture/structured/components/harness-hooks.md, .architecture/structured/components/providers.md, .architecture/patterns.md
- Concern refs: DD-1, RC-3, SEC-4, FM-9, OP-5, OP-9
- Invariant refs: INV-4, INV-10, INV-12, INV-A6
- Test refs: TC-3.1, TC-1.5, TC-G9

## Acceptance Criteria

- Pure assembly (reset removed - DD-1); only result==null active rows (delta); refuses missing/empty/type-mismatched/hash-mismatched/reset-stale evidence (INV-4/12)
- Refuses while non-terminal batch exists; snapshots conops/row/evidence hashes; writes part files to validation-digests/, records sha256s (RC-3, A6)
- 3500 UTF-8 byte/part split at row boundaries, (part i/k) labels; secret deny-pattern lint blocks assembly; row prose escaped; narrative rows marked (SEC-4, FM-9)
- Zero pending -> exit 0 NOTHING_TO_DIGEST

## Verification Summary

Automated evidence is the declared pytest command passing with mapped TC coverage.
