# A-6 Component Mini-Spec

Title: Waiver flow: challenge, receipt acceptance, audit cache

Blocking-checker challenge creation (immutable block_id, one-time nonce request, local-derived challenge envelope); receipt acceptance via MW-004 (challenge-byte binding, nonce-consumption receipt, authorization_kind precedence, non-waivable class rejection, consumption at protected transitions); nonces.jsonl audit cache; issuance idempotency by operation_id; surfacing in close report/checkpoint/card.

Acceptance criteria:
- full 5.4 rejection set green (TC-15.x)
- wrong-block/reused-nonce replay rejected (TC-15.4)
- lost response returns original receipt by operation_id (TC-15.7)

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task A-6.
Implementation status: greenfield — no waiver machinery exists (telegram_bot.py is transport only)
