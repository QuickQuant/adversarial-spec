# W0-10 Component Mini-Spec

Title: MW-011 DurableOperationJournal

operation_journal.py (imports no transport): operation_id + contract id + behavior fingerprint + canonical request hash journaled + fsynced BEFORE dispatch; intent-durable/in-flight/uncertain/resolved state machine; PromotionSequenceResult derivation from record absence; restart recovery.

Acceptance criteria:
- crash before vs after dispatch distinguished by record presence (TC-8.12)
- same-id different-bytes retry = intent-mismatch
- DF-11 failure-injection table asserts owner/action/state

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task W0-10.
Implementation status: greenfield — no operation journal exists
