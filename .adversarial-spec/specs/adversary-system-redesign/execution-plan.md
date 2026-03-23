# Plan: Add TodoWrite Enforcement to All Adversarial-Spec Phases

## Context

The adversarial-spec skill has critical process steps (roadmap, CONS/SCOPE/TRACE guardrails, Arm Adversaries) documented as REQUIRED but routinely skipped. Only Phase 03 (debate) has TodoWrites, and even those are incomplete — guardrails are missing from all of them. Phases 01, 02, 05, 06, and 07 have zero TodoWrites despite containing mandatory gates.

TodoWrites act as visible enforcers — when a step is in the checklist, Claude is far more likely to do it than when it's buried in prose. This change adds one master TodoWrite to every phase, with `[GATE]` markers at critical points, plus inline back-references at gate locations in the doc body.

## Design Principles

1. **ONE master TodoWrite per phase** at the very top, before any other instructions
2. **`[GATE]` tags** on items that must be completed before proceeding — referenced inline at gate points
3. **6-10 items max** per phase — enforce gates, not granular sub-steps
4. **Remove fragment TodoWrites** in Phase 03 (currently 3 separate competing blocks)
5. **Guardrails are explicit line items** wherever they're required (debate rounds, post-gauntlet, finalize)

## Enforcement Pattern (applied to every phase)

Each phase doc starts with:
```markdown
> **FIRST ACTION upon entering this phase:** Create this TodoWrite immediately.
> Do NOT read further until the TodoWrite is active.
> Every `[GATE]` item must be marked completed before proceeding past it.
```

At each gate point in the doc body, add a one-line back-reference:
```markdown
**[GATE] TodoWrite: Mark "Step X" completed before proceeding.**
```

## Files to Modify

All in `skills/adversarial-spec/phases/`:

### 1. `03-debate.md` (highest priority — remove 3 fragments, add consolidated master)

**Remove:** Fragment TodoWrites at lines ~4, ~308, ~379

**Add at top:** Master TodoWrite (10 items):
```
Verify roadmap exists [GATE]
Load roadmap user stories
Load or generate initial document
Select opponent models
Assemble context files (technical/full)
Round 1: Run debate + synthesize
Round 1: Run SCOPE + TRACE guardrails [GATE]
Context Readiness Audit (technical/full) [GATE]
Round 2: Run debate + synthesize
Round 2: Run CONS + SCOPE + TRACE guardrails [GATE]
```

Key: Round 1 gets SCOPE+TRACE only (first-draft CONS exemption). Round 2+ gets all three. Dynamic rounds instruction: add 2 items per additional round (debate + guardrails).

**Add gate back-references at:**
- After roadmap verification (Step 1)
- After each round's guardrail section
- After Context Readiness Audit section

### 2. `05-gauntlet.md` (Arm Adversaries + post-gauntlet CONS)

**Add at top:** Master TodoWrite (9 items):
```
Select adversary personas and attack models
Present cost estimate to user
Arm Adversaries — scope classification + briefings [GATE]
Run gauntlet (respect Gemini rate limits)
Extract concerns with code (jq/Python, NOT LLM)
Synthesize findings — one Opus pass, 8-category taxonomy
Revise spec with accepted concerns
Run CONS guardrail on revised spec [GATE]
Update session state with gauntlet_concerns_path
```

**Add gate back-references at:**
- Before "Run gauntlet" section (Arm Adversaries gate)
- After spec revision section (CONS gate)

### 3. `06-finalize.md` (final guardrail pass — 3 separate items)

**Add at top:** Master TodoWrite (7 items):
```
Run final CONS guardrail [GATE]
Run final SCOPE guardrail [GATE]
Run final TRACE guardrail [GATE]
Quality verification (completeness, consistency, clarity, actionability)
Write final spec to disk
Present to user for review [GATE]
Update session state with spec_path and manifest_path
```

Three separate guardrail items prevents "I ran CONS, guardrails done" shortcuts.

**Add gate back-reference after guardrail section.**

### 4. `07-execution.md` (plan persistence gate)

**Add at top:** Master TodoWrite (9 items):
```
Load finalized spec and gauntlet concerns
Scope assessment — present to user
Load target architecture and build Architecture Spine (if exists)
Decompose into tasks with gauntlet concern linkage
Assign test strategies (test-first/test-after)
Over-decomposition guard check
Present plan to user for approval [GATE]
Write execution plan to disk [GATE]
Verify plan file exists and update session state
```

**Add gate back-references at:**
- After "Present Final Plan" step (user approval gate)
- After "Persist Execution Plan" step (disk write gate)

### 5. `02-roadmap.md` (artifact verification gates)

**Add at top:** Master TodoWrite (8 items):
```
Build RequirementsSummary and assess complexity
Draft roadmap with user stories and milestones
Roadmap debate round (medium/complex only)
User confirms roadmap [GATE]
Persist roadmap artifacts to disk
Verify artifacts exist on disk [GATE]
Create milestone and user story MCP Tasks
Update session state with roadmap_path
```

**Add gate back-references at:**
- After user confirmation step
- After verification bash block

### 6. `01-init-and-requirements.md` (requirements confirmation gate)

**Add at top:** Master TodoWrite (6 items):
```
Determine document type and depth
Identify starting point (file or concept)
Offer interview mode (spec only)
Conduct interview — cover all 8 topics
Build RequirementsSummary (user_types, features, integrations, unknowns)
User confirms requirements before roadmap [GATE]
```

**Add gate back-reference before roadmap transition.**

### 7. `04-target-architecture.md` (scale check + dry-run gates)

**Add at top:** Master TodoWrite (8 items):
```
Scale check — assess if architecture phase needed [GATE]
Assess starting point (greenfield vs brownfield)
Categorize application and confirm with user
Research best practices for each dimension
Draft target-architecture.md
Debate architecture until convergence
Dry-run verification of most complex flow [GATE]
Record decisions in Decision Journal
```

## Implementation Order

1. Phase 03 (debate) — most complex, highest value
2. Phase 05 (gauntlet) — Arm Adversaries is the most-skipped gate
3. Phase 06 (finalize) — final guardrail pass gets skipped
4. Phase 07 (execution) — plan persistence bug
5. Phase 02 (roadmap) — artifact persistence
6. Phase 01 (init) — requirements confirmation
7. Phase 04 (target-architecture) — scale check and dry-run

## Verification

1. `uv run pytest` — ensure no tests break (tests don't parse phase docs, but sanity check)
2. Read each modified file to verify TodoWrite syntax is correct
3. Spot-check: search for any remaining fragment TodoWrites in 03-debate.md (should be 0)
4. Verify `[GATE]` items in TodoWrites have matching back-references in the doc body
5. Deploy: files are symlinked, so changes are live immediately
