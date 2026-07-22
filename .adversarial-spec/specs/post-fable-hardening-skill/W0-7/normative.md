# W0-7 Component Mini-Spec

Title: MW-004 ReceiptVerifier + TrustPolicy

receipts.py + trust_policy.py: trusted-key lookup from launcher config, exact-byte ed25519 verification (domain prefix || JCS minus signature), THEN purpose-scoped TrustPolicy authorization under immutable policy identity + hash; purpose-preserving chained keyset rotation; full 5.4 rejection-set semantics.

Acceptance criteria:
- wrong-purpose key rejected across all receipt kinds (TC-15.8)
- DF-2 rotation/wrong-root/epoch-chain cases green
- signature validity without purpose authorization never authorizes

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task W0-7.
Implementation status: greenfield — no signature verification exists in skill runtime (cryptography: packaging only)
