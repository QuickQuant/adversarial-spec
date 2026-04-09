# Test Pseudocode: Phase 4 Architecture Rewrite

## US-1: Debate critiques across 6 focus areas

### TC-1.1: All focus areas receive at least one critique (happy path)
```
given: spec-draft-v1.md with 6 debate focus areas defined
when: debate round completes with 2+ opponent models
then: synthesis contains critique addressing each focus area
assert: len(focus_areas_with_critiques) == 6
```

### TC-1.2: Debate produces actionable revisions (happy path)
```
given: round 1 critiques from opponent models
when: synthesis is performed
then: at least 1 revision is proposed per focus area with surviving critiques
assert: spec-draft-v2 differs from v1 in sections flagged by critiques
```

### TC-1.3: No model consensus after 2 rounds (error case)
```
given: opponent models disagree on a focus area after round 2
when: convergence check runs
then: disagreement is surfaced to user with both positions
assert: user is asked to decide, not silently resolved
```

## US-2: Adversary stress test

### TC-2.1: Gauntlet covers cross-cutting concern completeness (happy path)
```
given: finalized spec with 9 base + 2 triggered cross-cutting concern categories
when: BURN adversary attacks observability section
then: attack identifies specific gaps or confirms coverage
assert: each in-scope concern category receives at least 1 adversary attack
```

### TC-2.2: Gauntlet catches brownfield scoping issues (error case)
```
given: brownfield-feature flow with blast-zone scoping
when: LAZY adversary tests "can I skip a concern by claiming it's out of scope"
then: the fitness assessment table forces explicit adequate/needs-extension/missing verdict
assert: no concern can be silently omitted
```

## US-3: Finalize and implement

### TC-3.1: 04-target-architecture.md contains all three modes (happy path)
```
given: finalized spec after debate + gauntlet
when: written to skills/adversarial-spec/phases/04-target-architecture.md
then: file contains greenfield, brownfield-feature, and brownfield-debug sections
assert: grep -c "Greenfield\|Brownfield Feature\|Brownfield Debug" == 3
```

### TC-3.2: Cross-references are valid (error case prevention)
```
given: updated 04-target-architecture.md
when: 02-roadmap, 05-gauntlet, 07-execution reference Phase 4 outputs
then: all referenced outputs (invariants, target-architecture.md, decision journal) are defined in Phase 4
assert: no dangling references to removed Phase 4 concepts
```
