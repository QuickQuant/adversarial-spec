# C-2.1 Component Mini-Spec

Title: derive-conops
Altitude: component
Parent: SS-2
Children: none
Realizes refs: US-1
Requirement ID: C-R201

## Requirement Statement

The component shall satisfy the approved derive conops acceptance criteria.

## Scope

- Implementation status: greenfield
- Behavior change: true
- Verification mode: automated-unit
- Verification scope: targeted
- Strategy: test-first
- Surface scope: cli_command

## Traceability

- Architecture refs: .architecture/structured/components/emission-toolchain.md, .architecture/structured/components/session.md, .architecture/patterns.md
- Concern refs: DD-7, CB-11, FM-3, SEC-9
- Invariant refs: INV-2, INV-8
- Test refs: TC-1.1, TC-1.2, TC-1.3, TC-G13

## Acceptance Criteria

- Deterministic template derivation from manifest id/title/story + milestone context only; never invents stories (DD-7)
- Every US-\d+ appears as ### US-n heading; stray-id lint (TC-G13: "replaces US-99" -> exit 2, CB-11); duplicate ids -> exit 2
- Records full conops_hash + per-section story_hashes map (FM-3); re-derive refuses without --force when a ledger references prior hash

## Verification Summary

Automated evidence is the declared pytest command passing with mapped TC coverage.
