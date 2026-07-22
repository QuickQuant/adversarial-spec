# B-4 Component Mini-Spec

Title: criticality_classifier.py resolution extension

Extend existing classifier: resolution action recording rule version + source-artifact hash + architecture link for any false resolution; null preserved or resolved true otherwise; operator receipt-bound resolution decisions recorded by this sole writer; writes via TmrRegistryWriter.

Acceptance criteria:
- sole-writer enforced by lint + runtime (TC-7.5)
- never defaults to false
- resolution records carry rule version + source hash

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task B-4.
Implementation status: partial — criticality_classifier.py EXISTS (60 lines; spec: already the sole writer today); resolution-record path new
