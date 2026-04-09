# Roadmap: Phase 4 Architecture Rewrite

## Goals
- Debate and stress-test spec-draft-v1 until consensus
- Finalize and implement as the new 04-target-architecture.md

## Non-Goals
- Rewriting the spec from scratch (v1 is comprehensive)
- Implementing downstream tool integrations (future work)

## Milestone 1: Debate spec-draft-v1
**User Stories:**
- US-1: As a spec author, I want opponent models to critique the Phase 4 rewrite across the 6 focus areas so I can find gaps before committing to it

**Success Criteria:**
- [ ] Spec debated through at least 2 rounds with opponent models
- [ ] All 6 debate focus areas addressed
- [ ] Critiques synthesized and spec revised to v2

**Dependencies:** None

## Milestone 2: Gauntlet stress test
**User Stories:**
- US-2: As a spec author, I want adversary personas to try to break the spec so I know it holds up under hostile scrutiny

**Success Criteria:**
- [ ] Gauntlet run with full adversary roster
- [ ] Surviving concerns addressed or explicitly accepted
- [ ] Pass/refine verdict achieved

**Dependencies:** M1

## Milestone 3: Finalize & Implement
**User Stories:**
- US-3: As a spec author, I want the finalized spec written to 04-target-architecture.md and deployed so the new workflow is live

**Success Criteria:**
- [ ] 04-target-architecture.md rewritten with finalized spec
- [ ] Cross-references updated in 02-roadmap, 05-gauntlet, 07-execution
- [ ] Deployed to ~/.claude/skills/adversarial-spec/

**Dependencies:** M2
