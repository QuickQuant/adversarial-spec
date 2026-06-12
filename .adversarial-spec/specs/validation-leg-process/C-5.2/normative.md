# C-5.2 Component Mini-Spec

Title: doc-08-implementation-close-algo
Altitude: component
Parent: SS-5
Children: none
Realizes refs: US-8
Requirement ID: C-R502

## Requirement Statement

The component shall satisfy the approved doc 08 implementation close algo acceptance criteria.

## Scope

- Implementation status: partial
- Behavior change: false
- Verification mode: static-check
- Verification scope: static
- Strategy: spike
- Surface scope: cli_command

## Traceability

- Architecture refs: .architecture/filesystem-map.md, .architecture/structured/components/debate-engine.md
- Concern refs: DD-2, FM-8, CB-5, US-4-correction
- Invariant refs: INV-5, INV-A6
- Test refs: TC-0.2
- Exemption reason: Phase-8 close-algorithm doc; verified by TC-0.2 static grep asserting all 8 gate reject codes appear with documented responses - no runtime behavior of its own.

## Acceptance Criteria

- "Validation leg (system altitude)" close section = the ?8 close algorithm verbatim (single normative ordering, every step idempotent, re-entry at step 1; DD-2)
- ?10 error-code playbook: all 8 gate rejects + local codes each with documented conductor response (TC-0.2)
- Re-entry routing: NOTHING_TO_DIGEST + failed rows -> remediation, never emission (CB-5); self-check before MCP (INV-5); MCP wiring concrete (FM-8)

## Verification Summary

Inspection/static evidence is the declared grep or pytest static check passing.
