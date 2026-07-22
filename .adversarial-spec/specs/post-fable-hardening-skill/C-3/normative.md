# C-3 Component Mini-Spec

Title: Freeze enforcement: debate.py payload assembly seam

debate.py payload assembly excludes frozen nodes (one-line stub: node_id + settled round + hash); payload diffable against freeze list; changed frozen-node hash blocks dispatch until reopened by named concern; unresolvable critique anchors block freezing.

Acceptance criteria:
- frozen-bytes mutation blocks dispatch (TC-11.3)
- real parser on induced fragments (TC-11.4)
- round N+1 carries exactly the volatile surface

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task C-3.
Implementation status: partial — debate.py exists (payload assembly debate.py:1086-1227); zero freeze logic (grep frozen|freeze = 0, verified)
