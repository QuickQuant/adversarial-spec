# Checkpoint Safeguards And Cadence For Auto-Compact Resilience

## Summary

Strengthen adversarial-spec so checkpoints preserve the process loop, not just session pointers. The goal is to survive compaction without losing the phase-specific operating discipline:

- **Debate** must resume at the right artifact, round, and transition point.
- **Implementation** must resume with the review-first / pick-next-card / sync-Trello / sync-`.handoff.md` / TodoWrite-tail loop intact.

Because the LLM does **not** have a reliable "context remaining until auto-compact" meter, the system should use **heuristic danger gates** plus an explicit **checkpoint mode**:
- `interactive`: strict, block on missing safeguard data
- `overnight`: recovery mode, degrade gracefully and continue

## Key Changes

### 1. Add explicit checkpoint mode and resume-guard state

Extend adversarial-spec session state and checkpoint workflow with a persisted resume guard.

Persist:
- In pointer/session:
  - `checkpoint_mode`: `interactive | overnight`
- In session `extended_state.resume_guard`:
  - `phase`
  - `mode`
  - `must_do_first`
  - `loop_invariant`
  - `checkpoint_reason`
  - `compact_signals`
  - `recovery_required`
  - `recovery_steps`
  - phase-specific state payload

Phase-specific payloads:

- Debate:
  - `latest_artifact_path`
  - `artifact_kind` (`spec`, `roadmap`, `target_architecture`, `gauntlet_input`, `execution_plan`)
  - `current_round_or_stage`
  - `active_model_set`
  - `pending_transition`
  - `persisted_outputs` summary

- Implementation:
  - `active_card_or_work_item`
  - `review_queue_head`
  - `owned_files`
  - `handoff_path`
  - `trello_state_summary`
  - `todo_tail_rule`
  - `next_pickup_rule`

Checkpoint markdown should gain new required sections:
- `## Resume Guard`
- `## Compact Signals`
- `## Recovery Protocol`

### 2. Make checkpoint validation phase-aware

Upgrade the checkpoint workflow from generic persistence checks to phase-specific safeguard checks.

Interactive mode:
- Fail checkpoint if required resume-guard fields are missing.
- Fail checkpoint if phase-specific coordination invariants are not satisfied.

Overnight mode:
- Do not fail the checkpoint for missing noncritical guard data.
- Write checkpoint with `recovery_required: true`.
- Record exactly what is missing and what recovery steps must run on resume.
- Still fail on hard corruption only:
  - missing active session
  - invalid JSON
  - missing required persisted artifact path for the current phase's main deliverable

Phase-specific validation:

- Debate:
  - latest artifact exists on disk
  - current round/stage is explicit
  - next transition or next round is explicit
  - TodoWrite is current
  - if a fresh spec/roadmap/architecture draft was written, checkpoint must occur before gauntlet/finalize transition

- Implementation:
  - TodoWrite is current
  - Trello state has been synced
  - `.handoff.md` has been synced when parallel agents are active
  - review queue has been checked before new pickup
  - TodoWrite tail preserves the loop:
    - sync state
    - pick next card or checkpoint

### 3. Put the "infinite loop" rule into persisted state

Codify the implementation loop so it survives compaction.

Implementation resume invariant:
- first action on resume:
  - read `.handoff.md`
  - check review queue first
  - sync Trello state
  - rebuild/update TodoWrite
- TodoWrite last item must always be:
  - "Pick up next card, sync Trello, sync `.handoff.md`, and leave this loop item as the final task"

Persist this invariant in the resume guard and render it prominently at startup/resume.

Debate gets an analogous loop:
- first action on resume:
  - open latest artifact
  - verify current stage/round
  - continue `next_action`, not a fresh round
- final TodoWrite item:
  - persist artifact, update next transition, checkpoint at the next natural gate

### 4. Add startup recovery protocol

When a session resumes and `extended_state.resume_guard.recovery_required == true`, do not continue directly into the phase.

Run a mandatory recovery checklist first.

Debate recovery:
1. Read latest checkpoint
2. Read latest artifact file
3. Confirm current round/stage from resume guard or journey
4. Rebuild TodoWrite with persisted tail rule
5. Reconfirm next transition before new debate/gauntlet work

Implementation recovery:
1. Read `.handoff.md`
2. Summarize live Trello state via subagent
3. Reconstruct current/next card and review queue head
4. Rebuild TodoWrite with persisted tail rule
5. Only then resume work

Startup UI / path context should display:
- checkpoint mode
- must-do-first
- loop invariant
- recovery required yes/no
- next action

## Checkpoint Cadence

### 1. Use heuristic danger gates, not a token meter

Assume no exact auto-compact visibility. Use stacked signals instead.

Signals to accumulate:
- wrote or materially revised a major artifact
  - spec draft
  - roadmap
  - target architecture
  - gauntlet output synthesis
  - execution plan
- completed a full debate round or large gauntlet batch
- ran large-output commands or long tool runs
- switched phase or workstream
- spent significant time since last checkpoint
- cleared a review batch / finished a commit batch / finished a wave boundary sync
- overnight mode is active

### 2. Define checkpoint thresholds

Interactive mode:
- prompt for checkpoint when 2-3 signals stack
- checkpoint immediately at hard gates:
  - before debate -> gauntlet
  - before gauntlet -> finalize after a full batch
  - after writing final deliverables
  - before leaving the session
  - before risky context/workstream switch

Overnight mode:
- checkpoint opportunistically at every natural durable milestone
- if no natural milestone appears, checkpoint roughly every 45-60 minutes of active work
- do not stop the session just because some guard fields are incomplete; write a recovery-mode checkpoint instead

### 3. Add phase-specific natural checkpoint points

Debate:
- after each persisted spec/roadmap/architecture version
- after each full round synthesis
- before gauntlet
- after gauntlet batch synthesis
- after execution plan write

Implementation:
- after commit batches
- after review batches
- after wave boundary syncs when pausing or switching
- after large root-cause audits
- before handing off to another agent
- before overnight continuation if current state is only in chat/TodoWrite

## Files To Change

Update:
- `skills/adversarial-spec/SKILL.md`
  - add checkpoint mode, resume guard schema, startup recovery behavior, heuristic cadence rules
- `skills/adversarial-spec/phases/03-debate.md`
  - add debate-specific resume guard requirements and checkpoint gates
- `skills/adversarial-spec/phases/08-implementation.md`
  - add implementation loop persistence, TodoWrite tail rule, review-first invariant, checkpoint cadence
- `~/.codex/skills/checkpoint-workflow/SKILL.md`
  - require checkpoint mode and phase resume-guard inputs
- `~/.codex/skills/checkpoint-workflow/scripts/run_checkpoint.py`
  - persist `checkpoint_mode`
  - persist `extended_state.resume_guard`
  - write new checkpoint sections
  - enforce interactive vs overnight verification behavior
  - print recovery warnings in the final summary

## Test Plan

Add or update tests for:

- Interactive checkpoint blocks when required phase guard fields are missing
- Overnight checkpoint succeeds with `recovery_required: true`
- Checkpoint markdown contains `Resume Guard`, `Compact Signals`, and `Recovery Protocol`
- Pointer/session persist `checkpoint_mode`
- Session persists `extended_state.resume_guard`
- Startup/resume logic displays and respects recovery mode
- Debate resume flow restores artifact/round/transition correctly
- Implementation resume flow restores review-first / TodoWrite-tail loop correctly

## Assumptions

- The LLM cannot reliably inspect "remaining context before auto-compact," so cadence must be heuristic.
- `checkpoint_mode` is explicitly set, not inferred from time or user silence.
- Overnight sessions must keep moving; therefore overnight mode degrades into recovery mode instead of hard-blocking.
- Interactive sessions should fail fast when the process loop would otherwise be lost.
