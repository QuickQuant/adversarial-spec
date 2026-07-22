# B-1 Component Mini-Spec

Title: TMR keystone-first schema extension (obligation fields)

KEYSTONE-FIRST: add obligation_revision, obligation_policy_version, tmr_record_hash (+ required_liveness_class/required_environment/required_tier if absent) to Brainquarters/shared-context/test-maturity-record-schema.md FIRST, then mirror into tmr_schema.py with schema_sha256 drift tripwire. Resolves the 11 tests-spec SCHEMA GAP carries.

Acceptance criteria:
- keystone edited before mirror (provable commit order)
- strict schema round-trip green
- obligation-identity projection hash stable under evidence-field changes

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task B-1.
Implementation status: greenfield — grep for all three fields = 0 in keystone AND tmr_schema.py (verified 2026-07-21)
