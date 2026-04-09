# Checkpoint: concern-remediation-cr0-cr7-complete

- **Timestamp (UTC):** 2026-03-23T03:53:56Z
- **Session:** `adv-spec-202603230138-concern-remediation-plan`
- **Context:** Concern Remediation Plan
- **Phase:** implementation
- **Step:** CR-0 through CR-7 all committed and Trello cards moved to Done. CR-8 (remove clustering) created in Backlog.

## Current Spec Content
- Spec file: `/home/jason/PycharmProjects/adversarial-spec/.adversarial-spec/specs/concern-remediation-plan/spec-final.md`

```markdown
# Plan: Architecture Concern Remediation (FINAL)

## Context

mapcodebase 3.1 identified 8 actionable concerns (CON-001 through CON-008). Exploration revealed **CON-002 (dead code) is invalid** — all three files (`scope.py`, `knowledge_service.py`, `gauntlet_monolith.py`) are actively used. The underlying findings (FIND-001, FIND-002, FIND-007) were wrong. This plan addresses the 7 valid concerns and corrects the false positive.

## Debate History

```

## Completed Work
CR-0: CON-002 invalidated with audit trail. CR-1: pydantic dep declared. CR-2: sys.path hacks removed from 17 test files. CR-3: FileLock canonical mutation path with 12 tests. CR-4: PROGRAMMING_BUGS re-raise guard across 5 phase files with 14 tests. CR-5: phase 2 inline dispatch replaced with call_model. CR-6: 9 prompts extracted to gauntlet/prompts.py. CR-7: CLI flag aliases added. All 442 tests passing. CR-8 created for clustering removal based on user feedback about v1 synthesis failure.

## Next Action
1. Pick up CR-8 (remove clustering step) or move to Adversary Redesign work stream. 2. Deploy skill files to ~/.claude/skills/adversarial-spec/. 3. Run /mapcodebase --update to refresh architecture docs with resolved concerns.

## Manifest Status
- Roadmap/spec manifest: missing
- Architecture manifest: exists (status: success, classification: caution)
  - schema version: `2.0`
  - accessor layer: primer.md=yes, access-guide.md=yes
  - freshness: `fresh`
  - generated hash: `c3b5f8c`
  - current hash: `39cba1e`
  - dirty worktree at scan: `True`
  - trust note: Fresh = current HEAD with no relevant drift
  - trust note: Worktree has untracked files but no changes to mapped source files
  - advisory: architecture docs are usable with caution; review drift before relying on them

## Roadmap Sync
- Result: `not_applicable`

## CLAUDE.md Review
- Next review: `2026-04-11`

## Open Questions
1. CR-8 (remove clustering) — should this be done before or after the Adversary Redesign work stream?
