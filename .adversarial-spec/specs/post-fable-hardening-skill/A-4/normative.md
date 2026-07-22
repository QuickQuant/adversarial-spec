# A-4 Component Mini-Spec

Title: competence_harness.py + baselines + coverage manifest

Harness runner: strict-JSON answer scoring (required subset next subset allowed; forbidden empty; exact citation equality; critical => >=1 required); exact arithmetic; bounded retry with attempt evidence + not-comparable threshold; coverage manifest; immutable identity-keyed baselines incl. environment fingerprint; waivable pre-session gate with MAX_PHASE_REGRESSION_POINTS=10.

Acceptance criteria:
- vacuous [] fails critical fixtures (TC-6.4)
- missing/incompatible baseline blocks (TC-6.5)
- 2-pass/2-fail scores exactly 50
- fingerprint drift => not-comparable (DF-12)

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task A-4.
Implementation status: greenfield — competence_harness.py absent (verified)
