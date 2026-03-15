# Checkpoint: Target Architecture Phase — Debate Converged

**Date:** 2026-03-05
**Session:** adv-spec-202603051555-philosophy-phase-and-arch-persona
**Phase:** debate → ready for implementation

## What happened

Debated a proposal to add a Target Architecture phase to the adversarial-spec skill, arising from a process failure in BracketBattleAI where 50 implementation tasks each built their own plumbing (independent Supabase clients, no shared fetchers, no loading skeletons, no state persistence).

### Debate participants
- Gemini 3 Pro (via CLI)
- Codex GPT-5.3 (via CLI)
- Claude Opus 4.6 (active participant)

### Rounds
- **Round 1:** Both models critiqued heavily (bootstrap, user journey, scale adaptation, API contracts, security, SLAs). Neither agreed. User provided critical clarifications on phase sequencing and naming.
- **Round 2:** Both models still critiqued (same operational themes). Core design converged. Accepted: entry IDs, flexible taxonomy, context truncation. Rejected: formal API contracts, error codes, feature flags, SLAs as over-engineering for skill tooling.

### Key decisions made
1. **Phase sequencing:** Target Architecture after spec debate convergence, before gauntlet
2. **Naming:** "Target Architecture" (not "Philosophy")
3. **Arming:** ALL adversaries get architecture during pre-gauntlet arming, not just ARCH
4. **Entry points:** Greenfield, brownfield new feature, health check (no adv-spec), major refactor
5. **Taxonomy:** Flexible dimensions[] array, not hardcoded fields
6. **Decision Journal IDs:** entry_id format: dj-YYYYMMDD-<6 char random>
7. **Context truncation:** If combined > 80% context window, summarize architecture

## Deliverables on disk
- Spec v1: `.adversarial-spec/specs/philosophy-phase-and-arch-persona/spec-draft-v1.md` (1324 lines, original process failure report)
- Spec v2: `.adversarial-spec/specs/philosophy-phase-and-arch-persona/spec-draft-v2.md` (535 lines, post-Round 1)
- Spec v3: `.adversarial-spec/specs/philosophy-phase-and-arch-persona/spec-draft-v3.md` (433 lines, FINAL)
- Round 1 critiques: `.adversarial-spec-checkpoints/round-1-critiques.json`
- Round 2 critiques: `.adversarial-spec-checkpoints/round-2-critiques.json`

## Next: Implementation

Build the 7 changes from spec v3:
1. New phase file: `04-target-architecture.md`
2. ARCH persona in `adversaries.py`
3. Decision Journal schema (v1.4)
4. `--doc-type architecture` in debate.py + prompts.py
5. Gauntlet input expansion in `05-gauntlet.md`
6. Architecture Spine + Wave 0 in `07-execution.md`
7. SKILL.md updates (router, transitions, language mapping, renumbering)
