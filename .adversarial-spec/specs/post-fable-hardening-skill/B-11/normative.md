# B-11 Component Mini-Spec

Title: Phase 8 verification-subflow migration (OR-3 / DF-20)

Atomic migration current_phase: verification -> {current_phase: implementation, current_step: verification} preserving artifacts + board state; idempotent single phase8_subflow_migration journey event; post-migration rejection of new current_phase: verification writes; canonical-order validator normalizes historical implementation -> verification transitions as legacy subflow events; SKILL.md canonical order updated.

Acceptance criteria:
- all four DF-20 guarantees red-green
- resume checker passes implementation -> (subflow) -> complete journey
- migrated session resumes cleanly

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task B-11.
Implementation status: greenfield — the mismatch exists today (SKILL.md:75-108 vs phases/09-verification.md:184-198; .architecture FIND-002)
