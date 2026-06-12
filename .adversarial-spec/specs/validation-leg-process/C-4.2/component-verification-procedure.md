# C-4.2 Component Verification

Verification kind: verification
Altitude obligation: component
Verification mode: automated-unit
Verification scope: targeted

## What Runs

- `uv run pytest scripts/tests/test_validation_emission.py -k "sender or telegram or allowlist" -q`

## Evidence Required

Automated evidence is the declared pytest command passing with mapped TC coverage.

## Mapped Tests

- Test refs: TC-INV-A4, TC-G3, TC-G7
- Test files: scripts/tests/test_validation_emission.py

## Acceptance Criteria Covered

- --source telegram reads RAW --update-file; module extracts sender/message/text; --sender-id ignored for telegram (SEC-1, TC-G3)
- Sender checked vs registry allowed_sender_ids (!= chat_id, SEC-2); missing/malformed registry -> ALLOWLIST_CONFIG_INVALID fail-closed
- Non-allowlisted -> DISCARDED, exit 2 SENDER_NOT_ALLOWLISTED + hashed-sender security event, zero mutations (INV-15, OP-1)
- No hardcoded chat/sender literal in source (static grep, TC-INV-A4); terminal source asserts identity + transcript reply_ref (SEC-3, TC-G7)

## Traceability

- Architecture refs: .architecture/structured/components/harness-hooks.md, .architecture/structured/components/providers.md
- Concern refs: SEC-1, SEC-2, SEC-3, OP-1, US-1
- Invariant refs: INV-15, INV-A4
