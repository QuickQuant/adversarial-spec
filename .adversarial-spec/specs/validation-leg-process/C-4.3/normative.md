# C-4.3 Component Mini-Spec

Title: reset-failed-supersede
Altitude: component
Parent: SS-4
Children: none
Realizes refs: US-12
Requirement ID: C-R403

## Requirement Statement

The component shall satisfy the approved reset failed supersede acceptance criteria.

## Scope

- Implementation status: greenfield
- Behavior change: true
- Verification mode: automated-unit
- Verification scope: targeted
- Strategy: test-first
- Surface scope: cli_command

## Traceability

- Architecture refs: .architecture/structured/components/emission-toolchain.md, .architecture/structured/components/gauntlet.md
- Concern refs: CB-1, DD-1, FM-1, FM-4, DD-10
- Invariant refs: INV-3, INV-13, INV-14, INV-A7
- Test refs: TC-2.5, TC-3.8, TC-G5

## Acceptance Criteria

- reset-failed: judged-fail result->history (append-only INV-14), nulls result/judgment, renames evidence .invalidated-<ts> (FM-4); --remediation-ref REQUIRED, conductor-verified assertion (FM-1)
- supersede-row: legal from ANY state incl judged-pass (CB-1/INV-13); full snapshot to superseded; transactional replacement in one invocation (no coverage gap, INV-7); approval_ref always required (INV-3)
- Allowed-reason enum enforced; disallowed (impl failed / evidence missing / prior negative judgment) -> REFRESH_DISALLOWED (TC-2.5b/G5)

## Verification Summary

Automated evidence is the declared pytest command passing with mapped TC coverage.
