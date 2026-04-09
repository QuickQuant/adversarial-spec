# Test Specification: Phase 4 Architecture Rewrite

> Promoted from tests-pseudo.md. Schema refs validated against spec-draft-v11.md.

## US-1: Debate critiques across 6 focus areas

### TC-1.1: All focus areas receive at least one critique (happy path)
```
given: spec-draft-v1.md with 6 debate focus areas defined
  - framework fit (version-accurate)
  - surface completeness (including realtime_streaming when applicable)
  - cache consistency semantics
  - invariant verifiability
  - brownfield compatibility
  - requirement traceability
when: debate round completes with 2+ opponent models via debate.py critique
then: synthesis contains critique addressing each focus area
assert: len(focus_areas_with_critiques) == 6
schema_refs: debate_state.round_N_synthesis in session detail file
```

### TC-1.2: Debate produces actionable revisions (happy path)
```
given: round 1 critiques from opponent models (codex/gpt-5.4, gemini-cli/gemini-3.1-pro-preview)
when: synthesis is performed by Claude
then: at least 1 revision is proposed per focus area with surviving critiques
assert: spec-draft-v2.md differs from v1 in sections flagged by critiques
assert: debate_state.round increments
schema_refs: debate_state in session detail file, spec-draft-vN.md file naming
```

### TC-1.3: No model consensus after 2 rounds (error case)
```
given: opponent models disagree on a focus area after round 2
when: convergence check runs (Section 9: "Debate rounds default to a maximum of 3")
then: disagreement is surfaced to user with both positions
assert: user is asked to decide, not silently resolved
assert: at round 5, explicit user approval required to continue (Section 9)
schema_refs: debate_state.round, journey[] event for debate round
```

## US-2: Adversary stress test

### TC-2.1: Gauntlet covers cross-cutting concern completeness (happy path)
```
given: finalized spec with 9 base + 3 triggered cross-cutting concern categories
  - base: enforcement, sot, error_handling, validation, config, caching, observability (Concerns 1-9)
  - triggered: security, integration, realtime (Concerns 10-12)
  - concern_category enum: enforcement | sot | error_handling | validation | config | caching | observability | security | integration | realtime
when: BURN adversary attacks observability section
then: attack identifies specific gaps or confirms coverage
assert: each in-scope concern_category receives at least 1 adversary attack
schema_refs: concern_category enum (Section 0), Section 6 concern list
```

### TC-2.2: Gauntlet catches brownfield scoping issues (error case)
```
given: brownfield_feature flow with blast-zone scoping (Section 12)
when: adversary tests "can I skip a concern by claiming it's out of scope"
then: fitness assessment forces explicit verdict per concern:
  adequate | needs_extension | missing | conflicts (Section 12, step 3)
assert: no concern can be silently omitted
assert: existing debt flag raised when concern has "now" severity (Section 12, step 3)
schema_refs: context_mode enum, Section 12 brownfield feature flow
```

## US-3: Finalize and implement

### TC-3.1: target-architecture.md contains all three context modes (happy path)
```
given: finalized spec after debate + gauntlet
when: written to specs/<slug>/target-architecture.md
then: file contains sections for all three context_mode values:
  - greenfield (Section 7: full draft flow)
  - brownfield_feature (Section 12: blast-zone scoped)
  - brownfield_debug (Section 13: traversal path scoped)
assert: YAML header contains context_mode field
assert: required headers present (Section 7): schema_version, spec_slug, phase_mode,
  context_mode, framework, framework_version, surfaces, roadmap_path,
  tests_pseudo_path, architecture_fingerprint
schema_refs: Section 7 Required Headers, context_mode enum
```

### TC-3.2: Cross-references are valid (error case prevention)
```
given: updated 04-target-architecture.md deployed to ~/.claude/skills/adversarial-spec/phases/
when: 02-roadmap.md, 05-gauntlet.md, 07-execution.md reference Phase 4 outputs
then: all referenced outputs are defined in Phase 4:
  - architecture-invariants.json (Section 8.2, normative schema)
  - target-architecture.md (Section 7, draft format + required headers)
  - decision_journal[] (Section 11, normative schema)
  - dry-run-results.json (Section 10.3, normative schema)
  - phase4_bootstrap (Section 0, bootstrap contract)
  - tests-pseudo.md invariant tests (Section 8.3, marker protocol)
assert: no dangling references to removed Phase 4 concepts
schema_refs: Section 22 (Phase Interactions), Section 20 (Migration Plan)
```

## Coverage Matrix

| User Story | Test Cases | Sections Exercised |
|-----------|------------|-------------------|
| US-1 | TC-1.1, TC-1.2, TC-1.3 | 9 |
| US-2 | TC-2.1, TC-2.2 | 6, 12, 22 |
| US-3 | TC-3.1, TC-3.2 | 7, 19, 20, 22 |

All user stories have ≥1 test. All tests map to a user story. No orphan tests.
