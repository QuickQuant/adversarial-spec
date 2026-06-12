# C-5.3 Component Mini-Spec

Title: dogfood-validation-this-session
Altitude: component
Parent: SS-5
Children: none
Realizes refs: US-10
Requirement ID: C-R503

## Requirement Statement

The component shall satisfy the approved dogfood validation this session acceptance criteria.

## Scope

- Implementation status: greenfield
- Behavior change: false
- Verification mode: manual-ux
- Verification scope: manual
- Strategy: spike
- Surface scope: cli_command, outbound_integration

## Traceability

- Architecture refs: .architecture/primer.md, .architecture/structured/components/harness-hooks.md, .architecture/overview.md
- Concern refs: ACK-4, OP-10, US-10
- Invariant refs: INV-A1, INV-A2, INV-A3, INV-A4, INV-A5, INV-A6, INV-A7
- Test refs: TC-4.1
- Exemption reason: Dogfood close: requires the real fizzy gate accepting on first call AND Jason's intent-level acceptance of the process experience (mobile-sufficient digest, unambiguous reply/re-prompt). Human-gated; cannot assert programmatically (NG3, ACK-4 bootstrap circularity acknowledged).

## Acceptance Criteria

- Card 5604 system_validation_complete == true; Finalization->Completed advance succeeds (TC-4.1)
- Dogfood rows covering US-0/US-6/US-7/US-9 carry Jason's pass with intent-level oracles (not "the gate accepted")
- Dogfood metrics record local retries/re-prompts/re-emissions before first MCP call + <30 min bootstrap timing (OP-10) ## Coverage Summary

## Verification Summary

Manual evidence is Jason's dogfood acceptance for TC-4.1.
