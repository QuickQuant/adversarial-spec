# Checkpoint: orphaned-features-wired-medal-system-fixed

- **Timestamp (UTC):** 2026-04-09T19:55:06Z
- **Session:** `adv-spec-202604021743-phase4-architecture-rewrite`
- **Context:** Phase 4 Architecture Rewrite
- **Phase:** None
- **Step:** Wired orphaned debate.py features into pipeline, fixed dead medal system, moved severity assessment to Phase 4 eval

## Current Spec Content
- Spec file: `/home/jason/PycharmProjects/adversarial-spec/.adversarial-spec/specs/phase4-architecture-rewrite/spec-output.md`

```markdown
# Phase 4: Target Architecture — Spec Draft v11

> Gauntlet synthesis (v10→v11): 65 concerns from 7 adversaries (PARA, BURN, MINI, PEDA, ASSH, AUDT, FLOW × Gemini 3 Flash). 18 accepted, 4 acknowledged, ~20 dismissed. Key fixes: fingerprint concatenation delimiter (CB-1), architecture_fingerprint nullable (CB-2), realtime concern_category (CB-3), decision journal rationale in idempotency key (CB-4), framework_profile discriminator (CB-5), failed_checks explicit empty list (CB-6), stale lock TOCTOU fix + reduced threshold (RC-1/FM-2), artifact staging directory (FM-1), slug-in-manifest requirement (FM-3), volatile metadata stripping (FM-4), decision reversal invalidation (FM-5), same-directory temp files (SEC-1), spec_fingerprint back-link (OP-1), skip_rationale in JSON (OP-2), research snapshot requirement (DD-1), component-prefixed matrix columns (DD-2), canonical_json algorithm specified (US-1).

## Overview

Phase 4 is a file-based, AI-agent-driven state machine that runs after spec debate convergence (Phase 3) and before the gauntlet (Phase 5). It converts a converged product spec into deterministic architecture artifacts. There is no external HTTP API — the normative interfaces are the artifacts and session-state mutations this phase produces.

```

## Completed Work
Card 189 (Wire Orphaned Features): (1) Wired adversary-stats, adversary-versions, medal-leaderboard into 05-gauntlet.md as required pre/post-gauntlet steps. (2) Fixed medal similarity threshold 0.3→0.10 (old was unreachable, max observed 0.289). (3) Moved severity assessment from attack prompt (Phase 1) to eval prompt (Phase 4) — root cause of 99.2% medium severity was CLI models never asked for severity. (4) Added severity field to Evaluation dataclass with fallback for legacy runs. (5) Deprecated export-tasks. (6) Fixed Fizzy board ID in CLAUDE.md. (7) Committed large accumulated delta (112 files) from Apr 2-9 sessions. 3 commits total: d346f01, 64d880b, faa9423.

## Next Action
Next gauntlet run will produce real severity distribution and medal awards. Consider running adversary-stats to view 138 runs of historical data. Card 189 can be closed on Fizzy.

## Manifest Status
- Roadmap/spec manifest: missing
- Architecture manifest: exists (status: success, classification: caution)
  - schema version: `2.0`
  - accessor layer: primer.md=yes, access-guide.md=yes
  - freshness: `fresh`
  - generated hash: `c3b5f8c`
  - current hash: `faa9423`
  - dirty worktree at scan: `True`
  - trust note: Fresh = current HEAD with no relevant drift
  - trust note: Worktree has untracked files but no changes to mapped source files
  - advisory: architecture docs are usable with caution; review drift before relying on them

## Roadmap Sync
- Result: `not_applicable`

## CLAUDE.md Review
- Next review: `2026-04-25`

## Open Questions
1. None.
