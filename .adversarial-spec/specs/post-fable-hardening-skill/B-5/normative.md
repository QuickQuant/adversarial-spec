# B-5 Component Mini-Spec

Title: promotion_gate.py local evaluation + intent construction

Local promotion evaluation over MW-005/MW-009; finalize-transition check (registry validity + plan, NO run evidence - deadlock rule); completion-gate quantifier over critical_seam != false; JCS promotion intent binding the complete spec-9 field list; pre-dispatch local generation re-read.

Acceptance criteria:
- end-to-end local/remote split proven (TC-8.2)
- gateway replay blocked (TC-8.3)
- null-seam records cannot escape the quantifier
- successor_transfer_set byte-identical to provisional plan or intent-mismatch

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task B-5.
Implementation status: greenfield — promotion_gate.py absent (verified)
