# Backtrack: Completed-Unmapped → Finalization to permit pipeline_load

**Date:** 2026-07-22 · **Session:** adv-spec-202607060132-post-fable-hardening-skill · **Card:** 5857

At finalize→execution (2026-07-21) the board FSM had no execution lane, so the
session card was walked Gauntlet→Reconciliation→Finalization→Completed-Unmapped
with the note "pipeline_load maps tasks". pipeline_load (v5) in fact requires
the session card to sit in **Finalization** (`SESSION_NOT_FINALIZED`). This
backtrack moves the card one lane backward, with no gate state changed by hand,
so the approved 43-node schema-3 plan (validate_plan valid:true, plan
sha256:cb2cbc64efe09bd4) can load. Not a process rework — a lane-shape
correction; the earlier walk-forward was the misstep.
