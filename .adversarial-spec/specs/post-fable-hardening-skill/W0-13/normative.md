# W0-13 Component Mini-Spec

Title: MW-010 TmrRegistryWriter + sole-writer lint

tmr_registry_writer.py: the single Session-TMR-registry persistence path (read revision, validate preconditions, write under canonical lock order, bump revision); stale expected-revision rejected; classifier-relevant change invalidates dependent evidence in the same transaction; authoring-lint fails any outside write-open call site.

Acceptance criteria:
- DF-7 stale-revision + same-txn invalidation green
- sole-writer lint catches a violating fixture module
- serves both mutation-kind owners

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task W0-13.
Implementation status: greenfield — tmr_compile_step/provenance_journal write the roadmap-level registry; Session-TMR writer absent
