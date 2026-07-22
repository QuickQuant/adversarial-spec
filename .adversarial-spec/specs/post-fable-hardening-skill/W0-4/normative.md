# W0-4 Component Mini-Spec

Title: MW-002 DurableStateStore + StateTransaction

state_store.py: persistent-identity fcntl sidecar locks, expected-hash CAS, atomic single-file writes, repo-scoped .txn/ coordinator with leases, canonical bytewise lock order, PREPARED/PUBLISHING/COMMITTED roll-forward recovery, reader release-recover-retry, transaction-corrupt terminal quarantine (non-waivable), reachability-only GC.

Acceptance criteria:
- DF-6 completeness matrix green (reversed-lock-order, held-lock timeout, sidecar attacks, GC-vs-lease)
- crash at every protocol boundary recovers or quarantines, never mixed state
- readers never observe two generations

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task W0-4.
Implementation status: greenfield — gauntlet/persistence.py:74-152 protects single files only; no coordinator exists
