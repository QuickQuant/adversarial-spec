# A-3 Component Mini-Spec

Title: Judgment-gate corpus (rubrics + fixtures)

rubrics/<gate_id>.md (<=~40 lines) + >=1 golden fixture per judgment gate under fixtures/conductor-competence/<gate_id>/; fixture schema validator consumed by BOOT-HARNESS.

Acceptance criteria:
- every judgment row in gates.json has rubric + fixture
- fixtures schema-valid (TC-3.2)

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task A-3.
Implementation status: greenfield — no rubrics/ or fixtures/ dirs exist (verified)
