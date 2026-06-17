# Test Maturity Record (TMR) schema — MOVED (single source of truth)

The canonical cross-project TMR / guardrail-finding / provenance-journal contract now lives in the
shared-context repo, referenced by both the adversarial-spec skill spec (Fizzy card 5715) and the
fizzy-pipeline-mcp spec:

    /home/jason/PycharmProjects/Brainquarters/shared-context/test-maturity-record-schema.md

Do NOT re-add a copy here. Divergence of this contract is the exact failure this work exists to
prevent (US-1: both repos reference the SAME source of truth). Edit the canonical above; fizzy P0
validation is what guarantees the two implementations match it.
