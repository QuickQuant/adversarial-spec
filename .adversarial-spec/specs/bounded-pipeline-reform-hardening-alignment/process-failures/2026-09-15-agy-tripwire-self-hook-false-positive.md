---
date: 2026-09-15
session: adv-spec-202609150549-bounded-reform-hardening-align
card: 21537
phase: roadmap (Phase 2 debate round 1)
would_have_used: agy tripwire path allowlist for hook-owned logs; debate.py abort-on-tripwire instead of retry
severity: medium
---

# AGY mutation tripwire fired on a hook-owned log; debate.py retried anyway

## What broke
During roadmap debate round 1, `call_antigravity_model` raised `AGY_MUTATION_DETECTED` for the
`antigravity/gemini-3.8-flash-high` seat. Evidence dir:
`.adversarial-spec/incidents/agy-mutation-20260915-010558`. `mutated-paths.txt` names exactly one
path: `.claude/session-activity.jsonl`.

## Mechanism
That file is appended by `.claude/hooks/session_activity_logger.py` on this Claude Code session's own
tool events. Two read-only Bash checks ran in this session during the agy dispatch window
(~01:05 local), the hook appended lines, and the worktree snapshot diff attributed the write to agy.
agy runs sandboxed and does not execute Claude Code hooks. Diagnosis: false positive, self-inflicted.
The tripwire's `git checkout --` reverted the appended log lines (minor activity-log loss).

## Two defects
1. The tripwire has no allowlist for hook-owned append logs, so any conductor tool call during a
   dispatch trips it. Fix candidate: exclude `.claude/session-activity.jsonl` (and other declared
   hook sinks) from `_agy_porcelain_paths`, or snapshot only paths agy could reach.
2. `debate.py` treated the tripwire as a transient failure and retried ("attempt 1/3 … Retrying in
   1.0s") even though the error text says STOP EVERYTHING. The operator ruling (2026-07-20) is
   first-firing = halt and Jason reviews. Fix candidate: tripwire errors are non-retryable and abort
   the round with the incident path.

## Short-term workaround
Round 1 results were kept (both seats returned). No further agy dispatch until Jason rules. Reported
via Telegram with the incident dir.

## Permanent fix
Carded post-finalize as a W-task under this session (skill edits ship only as pipeline tasks).
