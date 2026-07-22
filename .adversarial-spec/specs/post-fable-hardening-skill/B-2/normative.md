# B-2 Component Mini-Spec

Title: verification_cards.py deterministic emitter + board upsert

One card per qualifying TMR keyed (session_id, tmr_uid, obligation_revision, obligation_policy_version); registry_hash as provenance snapshot never key; supersede obsolete cards; pipeline_load upsert with stable local key + expected board revision; lost response resolved by authority query; board-ahead = local-mirror-stale.

Acceptance criteria:
- identity stable across registry churn, zero duplicates (TC-7.4)
- empty selection emits no-op artifact with registry path+hash
- DF-7 stateful board fixture green

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task B-2.
Implementation status: greenfield — verification_cards.py absent (verified)
