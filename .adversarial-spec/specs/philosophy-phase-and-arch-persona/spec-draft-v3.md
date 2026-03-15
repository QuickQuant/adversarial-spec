# Target Architecture Phase — Adversarial Spec Skill Upgrade

**Version:** v3 (final — post-debate, pre-implementation)
**Date:** 2026-03-05
**Debated with:** Gemini 3 Pro, Codex GPT-5.3, Claude Opus 4.6 (2 rounds)
**Scope:** Changes to the adversarial-spec skill. Integration points with mapcodebase and gemini-bundle are described but implemented in their respective projects.

## Problem Statement

The adversarial-spec workflow produces product specs and execution plans but has no mechanism for defining **how the code is structured internally**. The spec describes *what* systems exist; the execution plan breaks them into tasks. Neither defines shared patterns, data flow architecture, component boundaries, or caching strategies.

This caused systemic architectural debt in BracketBattleAI: 50 tasks each built their own plumbing. Root cause: no shared architecture was defined before execution began. See: `process-failure-missing-target-architecture.md` in the BracketBattleAI project.

## Goals

1. Catch cross-cutting architecture flaws before execution planning.
2. Make architectural decisions auditable via a Decision Journal.
3. Strengthen the gauntlet by feeding architecture context to ALL adversary personas during arming.
4. Support iterative refinement — architecture debate may reveal spec gaps requiring revision.
5. Preserve backward compatibility with existing v1.3 sessions.

## Non-Goals

1. Rewriting the debate engine or provider architecture.
2. Mandating mapcodebase or gemini-bundle as hard dependencies.
3. Replacing the gauntlet scoring/medal system.
4. Changing the existing debate phase for spec-only critique.

## Phase Sequencing

### Current
```
requirements → roadmap → debate (spec) → gauntlet → finalize → execution → implementation
```

### New
```
requirements → roadmap → debate (spec converges) →
  TARGET ARCHITECTURE (categorize + research + draft) →
    debate rounds on architecture (may adjust spec) →
      gauntlet (spec + architecture) → finalize → execution → implementation
```

### Why this order

1. **Architecture requires a solid spec.** You can't determine the architecture until the spec defines what the app does.
2. **Architecture gets debated too.** The Target Architecture phase includes its own debate sub-loop using `debate.py critique --doc-type architecture`. Architecture debate may reveal spec gaps.
3. **The gauntlet receives the complete package.** All adversary personas attack the combined spec + architecture. Architecture context is fed during the pre-gauntlet arming stage.
4. **Debate is non-linear.** The spec debate runs until convergence. The architecture debate runs until architecture + spec are mutually consistent. Only then does the gauntlet run.

### Phase file numbering

```
01-init-and-requirements.md     (unchanged)
02-roadmap.md                   (unchanged)
03-debate.md                    (unchanged — spec debate)
04-target-architecture.md       ← NEW
05-gauntlet.md                  ← was 04
06-finalize.md                  ← was 05
07-execution.md                 ← was 06
08-implementation.md            ← was 07
```

## Entry Points and Cross-Skill Integration

### Entry Point 1: Greenfield (no code exists)
Full flow. Target Architecture drafted from scratch based on spec + research.

### Entry Point 2: Existing codebase, new major feature
```
mapcodebase → (optional: gemini-bundle) →
  adversarial-spec: debate (spec) → TARGET ARCHITECTURE (refine existing) →
    debate architecture → gauntlet → execution → implementation
```
Starts from `.architecture/` docs + `patterns[]`. AUGMENTS rather than creates from scratch.

### Entry Point 3: Architecture health check (no adversarial-spec)
```
mapcodebase → gemini-bundle → (review findings)
```
Target Architecture phase NOT triggered. Not every mapcodebase run needs adversarial-spec.

### Entry Point 4: Major refactor
Full flow with architecture context heavily informed by `patterns[]` and gemini findings.

### Integration with mapcodebase
- Consumes `.architecture/overview.md`, `manifest.json patterns[]`, component docs
- **Never a hard dependency.** If missing, phase works from spec + research alone.
- If present, each `warning`/`error` pattern must be addressed in the architecture.

### Integration with gemini-bundle
- Optional findings passed as `--context` during architecture debate.
- gemini-bundle runs before adversarial-spec (it needs mapcodebase first).
- Not required.

## Change 1: New Phase — `04-target-architecture.md`

### Prerequisites
- Spec debate (Phase 3) has converged.
- Roadmap with user stories exists.

### Inputs
- Converged spec draft
- Roadmap / user stories
- `.architecture/manifest.json` patterns[] (optional)
- Framework documentation (via Context7 / web)
- gemini-bundle findings (optional)

### Steps

#### Step 1: Scale Check (Gate)

Not every project needs formal architecture. Check:

```
Scale Assessment
───────────────────────────────────────
Spec scope: [user story count]
Codebase: [greenfield / existing with N files]
Stack complexity: [single runtime / multi-service]

Recommended: [Full architecture | Lightweight | Skip]
```

**Skip criteria:** <3 user stories AND single-file scope, or pure library with no app layer.

If skip: log `decision_journal` entry with `decision: "skip"`, transition to gauntlet.

#### Step 2: Assess Starting Point

**Greenfield:** Architecture drafted from scratch (Steps 3-4).

**Brownfield:**
- Load `.architecture/overview.md` and relevant component docs
- List all `warning`/`error` patterns from `patterns[]`
- Load gemini-bundle findings if available
- Focus: "what new patterns does this spec need?" + "which existing patterns need adjustment?"

#### Step 3: Categorize the Application

Classify along dimensions relevant to the project type. The taxonomy adapts to the category — don't force web-app dimensions onto a CLI tool.

**Schema (flexible dimensions array):**
```json
{
  "architecture_taxonomy": {
    "category": "web-app | cli | api-service | library | data-pipeline | mobile | other",
    "dimensions": [
      {
        "name": "rendering",
        "value": "hybrid-ssr-csr",
        "rationale": "SSR for initial load, CSR for interactive editors",
        "source_refs": ["Next.js App Router docs", "spec §7"]
      }
    ],
    "confirmed_by_user": true,
    "confirmed_at": "ISO8601"
  }
}
```

**Web apps:** Rendering, Navigation, Auth, Data freshness, State management, Multi-page sharing.
**CLIs:** Execution model, State, Concurrency, I/O.
**APIs:** Transport, Auth, Data layer, Scaling.

Present classification to user for confirmation.

#### Step 4: Research Best Practices

For each dimension:
1. Look up established pattern for the chosen stack
2. Minimum 2 sources (official docs + community/template)
3. Use Context7 if available for exact API signatures
4. Note where the framework provides built-in solutions

#### Step 5: Draft Target Architecture Document

Produce `specs/<slug>/target-architecture.md`:

```markdown
### [Pattern Name]
**Decision:** [pattern chosen]
**Rationale:** [why, with source references]
**Alternative considered:** [what else was evaluated]
**Implementation sketch:** [code snippets or file structure]
**Applies to:** [which user stories / features]
```

If `patterns[]` available: each `warning`/`error` pattern gets a corresponding section.

#### Step 6: Debate the Architecture

```bash
cat specs/<slug>/target-architecture.md | \
  python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --models MODEL_LIST --doc-type architecture --round N \
  --context specs/<slug>/spec-draft-latest.md \
  $CONTEXT_FLAGS
```

If debate reveals spec gaps: revise spec → run spec debate round → resume architecture debate.

Continue until convergence.

#### Step 7: Dry-Run Verification

Walk the most complex user flow through the architecture step-by-step:
- Which component renders?
- What data is fetched, by whom, via what mechanism?
- What state is created, where, what happens on navigation?
- What happens on error?

If gaps found: revise architecture, re-debate the change.

**The dry-run is the proof the architecture is complete.**

#### Step 8: Record Decisions

Log all decisions to the Decision Journal. This is the primary decision-recording point.

### Outputs
- `specs/<slug>/target-architecture.md`
- Decision Journal entries in session state
- Architecture taxonomy in session state

### Completion Criteria
- All taxonomy dimensions decided with rationale
- At least one dry-run completed without gaps
- Architecture debated through at least one converged round
- Decision Journal records categorization + each pattern decision

### Phase Transition
Detail file: set `current_phase: "gauntlet"`, set `target_architecture_path`
Pointer file: update accordingly

## Change 2: ARCH Adversary Persona

Add to `adversaries.py`:

```python
ARCH = AdversaryPersona(
    code="ARCH",
    name="Architect",
    role="Challenges internal code structure, data flow, and component boundaries",
    perspective="How code is ACTUALLY organized — data flow, state management, shared patterns",
    attack_style="Traces data flow. Asks 'what happens when...' for user paths. Identifies missing abstractions.",
    key_questions=[
        "How does data flow from database through server components to client components?",
        "What shared infrastructure exists for auth, data fetching, caching, error handling?",
        "What happens to client state when a user navigates between pages?",
        "Where is the server/client component boundary and is it consistent?",
        "Are there patterns repeated across files that should be centralized?",
        "How will the first implementation's pattern propagate to subsequent ones?",
    ]
)
```

**ARCH participates in ALL gauntlet rounds.** Architectural concerns cross all documents.

**All adversaries receive architecture context during arming.** The pre-gauntlet arming stage adds `target-architecture.md` to the context pool. Every persona can attack architecture from their angle:
- PARA: security implications of auth patterns
- BURN: assumptions about framework behavior
- FLOW: UX implications of loading/state patterns
- AUDT: consistency and auditability of architecture decisions

## Change 3: Decision Journal

### Schema (in session detail file)

```json
{
  "decision_journal": [
    {
      "entry_id": "dj-20260305-a1b2c3",
      "time": "2026-03-05T16:00:00Z",
      "phase": "target-architecture",
      "topic": "auth-pattern",
      "decision": "adopt",
      "choice": "Middleware-based auth with cached fallback",
      "rationale": "Eliminates per-page auth calls",
      "alternatives_considered": ["Per-page getUser()", "React cache() only"],
      "revisit_trigger": "If middleware latency exceeds 50ms",
      "reverses_entry_id": null
    }
  ]
}
```

**Decision types:** `adopt`, `reject`, `defer`, `skip`, `reversed`

**Rules:**
- Append-only — never edit or delete entries
- `reversed` entries must set `reverses_entry_id` pointing to the original entry
- `entry_id` format: `dj-YYYYMMDD-<6 char random>`
- Required fields: `entry_id`, `time`, `phase`, `topic`, `decision`, `choice`, `rationale`
- Optional fields: `alternatives_considered`, `revisit_trigger`, `reverses_entry_id`

### When to prompt

Prompt for decisions when:
- Target Architecture phase completes (always — primary source)
- User explicitly defers or rejects something
- Gauntlet raises concerns leading to design changes
- A phase is explicitly skipped

NOT at every routine phase transition (too much friction).

### Session schema: v1.3 → v1.4

New fields:
- `decision_journal`: `[]` (default)
- `architecture_taxonomy`: `null | object`

Migration: missing fields default silently. No destructive changes.

## Change 4: `debate.py --doc-type architecture`

Add `architecture` to `--doc-type` choices.

### System prompt (in prompts.py)

```
You are reviewing a Target Architecture document for a software project.

The document defines shared patterns that all implementation tasks must follow:
data fetching, auth, state management, caching, component boundaries, etc.

Focus your critique on:
1. Are the chosen patterns appropriate for the application's category and scale?
2. Are there framework-specific features or patterns being overlooked?
3. Will these patterns compose well across all pages/routes/features?
4. Are there missing patterns that this category typically needs?
5. Does the dry-run user flow work through the architecture without gaps?
6. Are any "decisions" just restating framework defaults without evaluation?
7. Is the architecture consistent with the product spec's requirements?

Be specific. Reference framework documentation. Propose concrete alternatives.
```

### Implementation
- `prompts.py`: add system prompt for `architecture` doc type
- `debate.py`: add `architecture` to `--doc-type` choices enum
- Tests: verify prompt selection for `architecture`

## Change 5: Gauntlet Input Expansion

Update `05-gauntlet.md` (renumbered) input assembly to include target architecture.

**If target architecture exists:** Include in gauntlet input bundle + arming context pool.

**If target architecture missing** (legacy sessions, Phase 4 skipped): Proceed without. Advisory: "No target architecture available — architecture-level concerns may be underrepresented."

**Context truncation:** If combined spec + roadmap + architecture exceeds 80% of target model's context window, summarize the architecture document before feeding to gauntlet. Preserve all Decision/Rationale sections; truncate Implementation sketches.

## Change 6: Execution Plan — Architecture Spine + Wave 0

Update `07-execution.md` (renumbered):

### Architecture Spine section
Between Scope Assessment and Wave 1:

```markdown
## Architecture Spine
Cross-cutting patterns from the Target Architecture. All tasks must follow.

### [Pattern Name]
- **Pattern:** [one-line description]
- **Rule:** [what implementers must / must not do]
- **Reference:** Target Architecture §[N], Task W0-[N]
```

### Wave 0: Architecture Foundation
Tasks establishing shared infrastructure before feature tasks:
- One task per pattern in the Target Architecture
- Wave 0 tasks block all feature tasks depending on the pattern
- Typical: 4-8 tasks, S-M effort

If no target architecture: skip Wave 0 and Architecture Spine.

## Change 7: SKILL.md Updates

### Phase Router
Add: `| target-architecture | phases/04-target-architecture.md |`

### Phase Transition Protocol
Add artifact field: `| target-architecture → gauntlet | target_architecture_path |`

### User Language Mapping
Add: `| "architecture," "target architecture," "how should we build it" | target-architecture |`

### Phase number references
Update all hardcoded references to 04-07 → 05-08 throughout SKILL.md and reference docs.

### Phase routing compatibility
For one release, accept both old and new phase numbers in session state:
- `gauntlet` maps to `05-gauntlet.md` (new) or `04-gauntlet.md` (old reference)
- Phase name string (`"gauntlet"`) is canonical, not the number

## Testing Strategy

### Unit
- `--doc-type architecture` selects correct system prompt
- Decision journal append-only enforcement
- Schema v1.4 migration (v1.3 gets defaults)
- ARCH persona definition loads correctly
- Scale check logic
- Entry ID generation and reversal reference validation

### Integration
- Full phase transition: debate → target-architecture → gauntlet
- Gauntlet input assembly includes target architecture
- Execution plan emits Architecture Spine + Wave 0
- Graceful degradation without target architecture

### Migration
- v1.3 session load → auto-upgrade → preserve data
- Empty decision_journal → no errors
- Phase router resolves both old and new phase numbers

## Migration Plan

1. Session loading accepts v1.3 and v1.4 (missing fields default silently).
2. Phase renumbering across all skill files.
3. Existing past-gauntlet sessions: log `skip` in decision journal.
4. No feature flags — direct deployment to `~/.claude/skills/adversarial-spec/`.

## Open Questions (Deferred)

1. Architecture debate convergence tracking: separate from spec debate metrics?
2. Architecture drift during implementation: manual edit, auto-retro checkpoint, or both?
3. Should previous session's target-architecture.md carry forward for follow-up features?
4. Should gemini-bundle findings have structured output for programmatic ingestion?
5. Should mapcodebase `patterns[]` eventually become required?
