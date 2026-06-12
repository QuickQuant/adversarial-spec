# C-3.3 Component Mini-Spec

Title: record-send-cancel-batch
Altitude: component
Parent: SS-3
Children: none
Realizes refs: US-6
Requirement ID: C-R303

## Requirement Statement

The component shall satisfy the approved record send cancel batch acceptance criteria.

## Scope

- Implementation status: greenfield
- Behavior change: true
- Verification mode: automated-unit
- Verification scope: targeted
- Strategy: test-first
- Surface scope: cli_command, outbound_integration

## Traceability

- Architecture refs: .architecture/structured/components/harness-hooks.md, .architecture/structured/components/emission-toolchain.md
- Concern refs: RC-2, FM-6, FM-12, OP-7
- Invariant refs: INV-16, INV-A6
- Test refs: TC-G1

## Acceptance Criteria

- record-send records per-part delivery + message_id; flips batch to sent only when ALL parts sent (RC-2)
- cancel-batch requires --reason; rows return to delta pool; audit-logged; cancellation notice if parts were sent (FM-12)
- Bulk verdicts gated on sent status (INV-16)

## Verification Summary

Automated evidence is the declared pytest command passing with mapped TC coverage.
