# Guardrail Prompt Source

[adversaries.py](../scripts/adversaries.py) is the only editable source for checkpoint guardrail prompts (`GUARDRAILS`). Read the canonical persona there; do not maintain a prompt mirror in this reference.

Order from `guardrail_orchestration.py::GUARDRAIL_ORDER`:

| Order | Prefix | Canonical name |
|---|---|---|
| 1 | CONS | `consistency_auditor` |
| 2 | SCOPE | `scope_creep_detector` |
| 3 | TRACE | `requirements_tracer` |
| 4 | CANON | `canonical_type_auditor` |
| 5 | TCOV | `test_coverage_auditor` |

Use [Phase 3 checkpoint guardrails](../phases/03-debate.md#checkpoint-guardrails-after-each-round-incorporation) for shared invocation and [Phase 6](../phases/06-finalize.md#final-guardrail-delta) for finalization's stricter gate.
