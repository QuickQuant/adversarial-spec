# B-6 Component Mini-Spec

Title: Promotion remote sequence + authority-committed inheritance

Wire the canonical runtime sequence (local eval -> REMOTE snapshot registration -> intent -> prepare -> commit) via MW-007/MW-011; successor derivation from authority commit record at required read-version; startup reconciliation gate; mirror materialization under StateTransaction with LocalReconciliationResult states; local-mirror-stale blocking + idempotent rematerialization; failure-ownership table.

Acceptance criteria:
- prepare without registered snapshot rejected (TC-8.10)
- parent completion never observable without transfer facts (TC-8.13)
- rematerialization path green (TC-8.14)
- retention/GC protection (TC-8.15)

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task B-6.
Implementation status: greenfield — no remote promotion sequence exists
