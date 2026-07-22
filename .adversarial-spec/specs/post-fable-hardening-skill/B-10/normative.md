# B-10 Component Mini-Spec

Title: Regime lifecycle (spec 18): attestation, backfill, cross-regime transfer

Regime materialization comparing authority-attested creation time against validated hardening-rollout-policy-v1 (binding policy identity+hash+keyset epoch); mirror validation against signed attestation; epoch-zero pre-rollout immutability; legacy materialization only for pre-contract sessions via historical lookup; creation-unprovable operator disposition; cross-regime deferral solely via obligation-transfer-v1 with conductor-produced provenance cap.

Acceptance criteria:
- regime branch distinguishes by attestation never absence (TC-0.4)
- epoch-zero provisioning + immutable pre-rollout (TC-0.10)
- DF-10 regime-pair transfer matrix green
- local timestamp/manifest rewrite cannot decide regime

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task B-10.
Implementation status: greenfield — no regime machinery exists
