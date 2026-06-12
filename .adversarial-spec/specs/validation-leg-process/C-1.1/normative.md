# C-1.1 Component Mini-Spec

Title: module-skeleton-envelope
Altitude: component
Parent: SS-1
Children: none
Realizes refs: US-0
Requirement ID: C-R101

## Requirement Statement

The component shall satisfy the approved module skeleton envelope acceptance criteria.

## Scope

- Implementation status: greenfield
- Behavior change: true
- Verification mode: automated-unit
- Verification scope: targeted
- Strategy: test-first
- Surface scope: cli_command

## Traceability

- Architecture refs: .architecture/structured/components/emission-toolchain.md, .architecture/structured/components/debate-engine.md, .architecture/patterns.md
- Concern refs: FM-5, OP-3, OP-4, OP-11
- Invariant refs: INV-A3
- Test refs: TC-3.9

## Acceptance Criteria

- argparse dispatch for all 13 subcommands; unknown subcommand -> exit 2 envelope
- Every invocation prints exactly one stdout JSON envelope {status,code,issues:[{code,row_id,detail}],data}; warnings to stderr only (FM-5)
- Exit-code contract 0/2/3 wired at CLI boundary; global issues carry row_id:null
- schema_version + module_version (__version__ + git short hash) stamped on JSON artifacts (OP-4, DD-6); all timestamps UTC RFC3339 Z (OP-3)

## Verification Summary

Automated evidence is the declared pytest command passing with mapped TC coverage.
