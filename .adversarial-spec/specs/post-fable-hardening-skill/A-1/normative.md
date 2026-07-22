# A-1 Component Mini-Spec

Title: gate_inventory.py + gates.json + doclint

Maintain gates.json (classification enum, enforcement, owner, contract_id, violation_modes); normalized semantic form; doclint mapping phase-doc markers to gate_id; phase_docs_hash staleness; negative-test execution harness; hosts the authoring-lint family.

Acceptance criteria:
- TC-1.0 inventory completeness incl. canonical Phases 1-8 + owned subflow units
- unmapped MUST marker fails doclint with file+line (TC-1.2)
- unclassified gate fails check

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task A-1.
Implementation status: greenfield — gate_inventory.py absent (verified)
