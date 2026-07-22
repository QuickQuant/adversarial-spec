# W0-12 Component Mini-Spec

Title: MW-007 RemoteAuthorityClient

remote_authority.py: snapshot upload/finalize, prepare, commit, status reconciliation, signed challenge-response probes (+ negative probes), behavior-fingerprint pinning, over injected transports; never dispatches a recoverable mutation without a durable MW-011 intent; OR-4 recovery split (uncertain prepare replays prepare; uncertain commit uses commit-status keyed by operation_id + receipt hash).

Acceptance criteria:
- success tokens are real values, never exception-shaped (TC-8.11)
- fingerprint drift detected as state-stale (DF-3)
- recorded-fixture probes for all 9 consumed contracts (hermetic)

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task W0-12.
Implementation status: greenfield — models.py / gauntlet model_dispatch are LLM transports, not authority contracts (CON-009 counter-pattern)
