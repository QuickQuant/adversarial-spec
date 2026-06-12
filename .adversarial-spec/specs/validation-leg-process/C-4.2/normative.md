# C-4.2 Component Mini-Spec

Title: telegram-trust-boundary
Altitude: component
Parent: SS-4
Children: none
Realizes refs: US-7
Requirement ID: C-R402

## Requirement Statement

The component shall satisfy the approved telegram trust boundary acceptance criteria.

## Scope

- Implementation status: greenfield
- Behavior change: true
- Verification mode: automated-unit
- Verification scope: targeted
- Strategy: test-first
- Surface scope: outbound_integration

## Traceability

- Architecture refs: .architecture/structured/components/harness-hooks.md, .architecture/structured/components/providers.md
- Concern refs: SEC-1, SEC-2, SEC-3, OP-1, US-1
- Invariant refs: INV-15, INV-A4
- Test refs: TC-INV-A4, TC-G3, TC-G7

## Acceptance Criteria

- --source telegram reads RAW --update-file; module extracts sender/message/text; --sender-id ignored for telegram (SEC-1, TC-G3)
- Sender checked vs registry allowed_sender_ids (!= chat_id, SEC-2); missing/malformed registry -> ALLOWLIST_CONFIG_INVALID fail-closed
- Non-allowlisted -> DISCARDED, exit 2 SENDER_NOT_ALLOWLISTED + hashed-sender security event, zero mutations (INV-15, OP-1)
- No hardcoded chat/sender literal in source (static grep, TC-INV-A4); terminal source asserts identity + transcript reply_ref (SEC-3, TC-G7)

## Verification Summary

Automated evidence is the declared pytest command passing with mapped TC coverage.
