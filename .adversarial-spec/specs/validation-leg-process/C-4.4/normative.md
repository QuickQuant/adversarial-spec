# C-4.4 Component Mini-Spec

Title: emit-system-validation
Altitude: component
Parent: SS-4
Children: none
Realizes refs: US-8
Requirement ID: C-R404

## Requirement Statement

The component shall satisfy the approved emit system validation acceptance criteria.

## Scope

- Implementation status: greenfield
- Behavior change: true
- Verification mode: automated-unit
- Verification scope: targeted
- Strategy: test-first
- Surface scope: cli_command

## Traceability

- Architecture refs: .architecture/structured/components/emission-toolchain.md, .architecture/structured/cross-references.md
- Concern refs: CB-2, CB-3, CB-12, DD-3, FM-3, PARA-ledger-hash
- Invariant refs: INV-1, INV-8, INV-A1
- Test refs: TC-INV-A1, TC-3.4, TC-3.6

## Acceptance Criteria

- Read-only projection of judged rows into ?6.4 (ledger untouched); result==null ? judgment==null (CB-2); na->not-applicable (CB-12)
- Refuses: any active row unjudged/failed; provenance missing on non-null result (INV-1); fresh-ConOps mismatch scoped by story_hashes (FM-3)
- test_targets preserved (anti-relabeling parity SEC-7); ledger_hash binds artifact to exact ledger state (PARA); single artifact (OQ-1, DD-3) with Appendix-A contingency
- Single N/A rule: na rows appear but don't count toward coverage; every story needs >=1 pass (TC-3.6)

## Verification Summary

Automated evidence is the declared pytest command passing with mapped TC coverage.
