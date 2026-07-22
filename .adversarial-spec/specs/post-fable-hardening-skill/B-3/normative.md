# B-3 Component Mini-Spec

Title: record_verification_evidence.py write-back + maturity authority

The ONLY path from completed card to promotion-eligible evidence: validates card binding, evidence class, artifact hash, tmr_uid before registry update via TmrRegistryWriter; sole authorized writer of nl|acceptance -> concrete atomically with write-back.

Acceptance criteria:
- card completion without registry update cannot count promotion-ready
- concurrency conflict retries from fresh read
- green-but-wrong evidence rejected (TC-8.4)

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task B-3.
Implementation status: greenfield — script absent (verified); spec names it as new sole writer
