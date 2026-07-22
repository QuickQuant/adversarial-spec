# C-2 Component Mini-Spec

Title: Debate node registry: snapshot + hash-chained event log

Versioned envelope snapshot (payload.nodes[] settled/volatile/derived) + hash-chained debate-nodes.events.jsonl under one StateTransaction; canonical leaf-heading extraction; checkpoint/resume lifecycle with durable manifest reference + fail-closed chain validation; round-metrics accumulation (KPI-7 baseline).

Acceptance criteria:
- chain break detected (TC-12.3)
- corrupt artifacts preserved in place with named quarantine status
- resume restores the settled/volatile/derived split exactly

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task C-2.
Implementation status: greenfield — no node registry exists
