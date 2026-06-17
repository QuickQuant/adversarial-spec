# ConOps: Liveness Gate + Test Ladder (adversarial-spec slice)

## Operational narrative
Session: adv-spec-202606151042-liveness-gate-test-ladder
This ConOps is derived deterministically from roadmap manifest milestones and user stories.

## User stories (intent register)
### US-15: US-15
As an operator, I want a documented first-run path so I can bootstrap the liveness gate + test ladder and verify a gate locally in minutes.
Milestone: Getting Started / bootstrap

### US-1: US-1
As a spec author and fizzy, I want one agreed TMR field set + enums so the skill's emission and fizzy's validation never drift.
Milestone: Shared TMR schema contract (keystone, schema-first)

### US-2: US-2
As a spec author, I want exactly one happy-path spine (TC-0) per user story with named steps, and every failure test anchored to a spine step.
Milestone: Happy-path-spine authoring + strict MOCK

### US-3: US-3
As a spec author, I want every MOCK to name the live/induced technique (or be promoted to REAL-DATA).
Milestone: Happy-path-spine authoring + strict MOCK

### US-4: US-4
As a spec author, I want tests tracked nl->acceptance->concrete at phase-appropriate rigor.
Milestone: Happy-path-spine authoring + strict MOCK

### US-5: US-5
As the orchestrator, I want each guardrail to run as a parallel subagent emitting structured, test/US-keyed findings.
Milestone: Guardrail rearchitecture: structured output + parallel subagents

### US-6: US-6
As a spec author, I want TRACE to flag a user story with no happy-path spine as ORPHANED.
Milestone: Guardrail rearchitecture: structured output + parallel subagents

### US-7: US-7
As a spec author, I want TCOV to promote nl->acceptance, ingest ALL owner test files, apply strict data_strategy_mismatch, and flag missing_liveness_test.
Milestone: Guardrail rearchitecture: structured output + parallel subagents

### US-8: US-8
As the operator, I want a deterministic gate that blocks gauntlet entry unless every user story has a phase-appropriate-maturity happy-path spine test, with a logged override.
Milestone: Deterministic spine-coverage gate (F-prime)

### US-9: US-9
As the operator, I want an append-only journal of test-maturity transitions (with drivers) to replay each user story's test journey.
Milestone: Decision provenance journal

### US-10: US-10
As the operator, I want altitude-triage transitions journaled (created->reclassifications->close altitude_fit) to measure triage accuracy and the altitude distribution.
Milestone: Decision provenance journal

### US-11: US-11
As the operator, I want critical-seam/spine tests promoted to real and RUN green (at the right tier) before implementation closes.
Milestone: Phase-8 pseudo->real promotion + version-fence

### US-12: US-12
As the operator, I want the new gates fenced to new specs so in-flight sessions aren't retroactively failed.
Milestone: Phase-8 pseudo->real promotion + version-fence

### US-13: US-13
As a future author, I want the new vocabulary and the cross-repo scope decision recorded so terms don't collide and decisions are durable.
Milestone: Glossary / ADR / document-types

### US-14: US-14
As the operator, I want every deliverable classified by verification tier so this skill's own work is verified appropriately.
Milestone: Cross-cutting: verification tiers
