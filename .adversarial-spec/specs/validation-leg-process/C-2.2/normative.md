# C-2.2 Component Mini-Spec

Title: normalize-rows
Altitude: component
Parent: SS-2
Children: none
Realizes refs: US-3
Requirement ID: C-R202

## Requirement Statement

The component shall satisfy the approved normalize rows acceptance criteria.

## Scope

- Implementation status: greenfield
- Behavior change: true
- Verification mode: automated-unit
- Verification scope: targeted
- Strategy: test-first
- Surface scope: cli_command

## Traceability

- Architecture refs: .architecture/structured/components/emission-toolchain.md, .architecture/structured/components/gauntlet.md
- Concern refs: CB-7, DD-4
- Invariant refs: INV-A1, INV-12
- Test refs: TC-G11

## Acceptance Criteria

- Sole producer of row_hash/story_hash (CB-7); conductor never writes hex
- Stamps schema fields; validates row_id format r-US<n>-<k> + global uniqueness + story-prefix match
- Mutating subcommand - holds lock, atomic write (INV-A2)

## Verification Summary

Automated evidence is the declared pytest command passing with mapped TC coverage.
