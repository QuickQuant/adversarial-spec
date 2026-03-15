# Target Architecture Phase — Adversarial Spec Skill Upgrade

**Version:** v2.1 (post-Round 1 debate + integration feedback)
**Date:** 2026-03-05
**Scope:** Changes to the adversarial-spec skill. Integration points with mapcodebase and gemini-bundle are DESCRIBED (so the design accounts for them) but IMPLEMENTED in their respective projects.

## Problem Statement

The adversarial-spec workflow produces product specs and execution plans but has no mechanism for defining **how the code is structured internally**. The spec describes *what* systems exist; the execution plan breaks the spec into tasks. Neither defines shared patterns, data flow architecture, component boundaries, or caching strategies.

This caused systemic architectural debt in BracketBattleAI: 50 tasks each built their own plumbing (independent Supabase clients, no cached fetchers, no loading skeletons, no state persistence). The root cause: no shared architecture was defined before execution began.

See: `/home/jason/PycharmProjects/BracketBattleAI/.adversarial-spec/issues/process-failure-missing-target-architecture.md`

## Goals

1. **Catch cross-cutting architecture flaws before execution planning** by introducing a Target Architecture phase that defines shared patterns.
2. **Make architectural decisions auditable** via a Decision Journal that records what was decided, rejected, and deferred.
3. **Strengthen the gauntlet** by feeding architecture context to ALL adversary personas during the arming stage.
4. **Support iterative refinement** — the architecture debate may reveal spec gaps that require spec revision.
5. **Preserve backward compatibility** with existing v1.3 sessions.

## Non-Goals

1. Rewriting the debate engine or provider architecture.
2. Mandating mapcodebase or gemini-bundle as hard dependencies.
3. Replacing the gauntlet scoring/medal system.
4. Changing the existing debate phase for spec-only critique.

## Phase Sequencing (CRITICAL DESIGN DECISION)

### Current flow
```
requirements → roadmap → debate (spec) → gauntlet → finalize → execution → implementation
```

### New flow
```
requirements → roadmap → debate (spec converges) →
  TARGET ARCHITECTURE (categorize + research + draft) →
    debate rounds on architecture (may adjust spec) →
      gauntlet (spec + architecture) → finalize → execution → implementation
```

### Why this order

1. **Architecture requires a solid spec.** You can't determine "this is a hybrid SSR/CSR app that needs cached fetchers" until the spec defines what the app does, what stack it uses, and what user stories it must support.
2. **Architecture gets debated too.** The Target Architecture phase includes its own internal debate sub-loop using `debate.py critique --doc-type architecture`. This is NOT a linear handoff — architecture debate may reveal spec gaps.
3. **The gauntlet receives the complete package.** All adversary personas (PARA, BURN, LAZY, PEDA, ASSH, AUDT, FLOW, ARCH) attack the combined spec + architecture. Architecture context is fed during the pre-gauntlet arming stage, giving every persona new attack surface.
4. **Debate is non-linear.** The word "debate" appears multiple times in the workflow. The spec debate (Phase 3) runs until convergence. The architecture debate (within Phase 4) runs until architecture + spec are mutually consistent. Only then does the gauntlet run.

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

Projects enter the adversarial-spec workflow at different points depending on their state. The Target Architecture phase must handle all of these.

### Entry Point 1: Greenfield (no code exists)

```
requirements → roadmap → debate (spec) → TARGET ARCHITECTURE (draft from scratch) →
  debate architecture → gauntlet → execution (with Wave 0) → implementation
```

- mapcodebase: not applicable (no code to map)
- gemini-bundle: not applicable (no code to bundle)
- Target Architecture: categorize based on spec, research best practices, draft from scratch

### Entry Point 2: Existing codebase, new major feature

```
mapcodebase → (optional: gemini-bundle for external review) →
  adversarial-spec: debate (spec) → TARGET ARCHITECTURE (REFINE existing patterns) →
    debate architecture → gauntlet → execution → implementation
```

- mapcodebase: already ran, `.architecture/` exists with `patterns[]` (if v3+)
- gemini-bundle: may have run, findings available as additional context
- Target Architecture: starts from existing architecture docs + patterns, AUGMENTS rather than creates from scratch. Focuses on: "what new patterns does this feature need?" and "do existing patterns need adjustment?"

### Entry Point 3: Existing codebase, architecture health check (NO adversarial-spec)

```
mapcodebase → gemini-bundle → (review findings, maybe file issues)
```

- adversarial-spec: **not involved**. Not every mapcodebase run triggers a full adversarial-spec cycle.
- Target Architecture phase: not triggered. This is just diagnostic.
- Findings may LATER feed into an adversarial-spec session if issues warrant it.

### Entry Point 4: Existing codebase, major refactor

```
mapcodebase → gemini-bundle → adversarial-spec (full flow with architecture context) →
  TARGET ARCHITECTURE (heavily informed by patterns[] and gemini findings) →
    debate → gauntlet → execution → implementation
```

### Integration with mapcodebase

The Target Architecture phase CONSUMES mapcodebase output when available:
- `.architecture/overview.md` — loaded as base context (already in SKILL.md startup)
- `.architecture/manifest.json` `patterns[]` — if present, each flagged pattern must be addressed in the architecture
- `.architecture/structured/components/*.md` — specific component docs relevant to the spec's blast zone

**mapcodebase is never a hard dependency.** If `.architecture/` doesn't exist, the Target Architecture phase works without it (relying on spec + research alone). If it does exist, it accelerates the phase significantly.

### Integration with gemini-bundle

gemini-bundle packages code + architecture docs for Gemini review. Its output is Gemini's critique/findings. The Target Architecture phase can consume these findings as additional context:

- **Input path:** gemini-bundle findings are typically returned as Gemini's text response, not a structured file. If findings are saved (e.g., as `.adversarial-spec/issues/gemini-review-*.md`), pass them as `--context` during architecture debate.
- **Not required.** gemini-bundle is an optional external cross-check, not a prerequisite.
- **Timing:** gemini-bundle runs before adversarial-spec starts (it needs mapcodebase first). By the time Target Architecture runs, gemini findings should already be available if they were generated.

### Integration with the arming stage

When the gauntlet runs (Phase 5), its pre-gauntlet arming stage assembles context for each adversary persona. The target architecture document is added to the context pool during arming, giving ALL adversaries (not just ARCH) access to architecture decisions. This is described in Change 2 below.

## Change 1: New Phase — `04-target-architecture.md`

### Prerequisites
- Spec debate (Phase 3) has converged — all models agreed on the product spec.
- Roadmap with user stories exists.

### Inputs
- Converged spec draft (from Phase 3 output)
- Roadmap / user stories
- `.architecture/manifest.json` patterns[] (optional — from mapcodebase if available)
- Framework documentation (via Context7 / docmaster / web)

### Steps

#### Step 1: Scale Check (Gate)

Not every project needs a formal Target Architecture. Check project scale:

```
Scale Assessment
───────────────────────────────────────
Spec scope: [number of user stories / features]
Codebase: [greenfield / existing with N files]
Stack complexity: [single runtime / multi-service / distributed]

Recommended: [Full architecture | Lightweight architecture | Skip]
```

**Criteria for skipping:**
- Fewer than 3 user stories AND single-file scope
- CLI tool with no persistent state or multi-page UI
- Pure library/package with no application layer

**If skip recommended:** Ask user. If confirmed, log `decision_journal` entry with `decision: "skip"`, `rationale`, and `revisit_trigger`. Transition directly to gauntlet.

**If user overrides skip recommendation (wants architecture anyway):** Proceed normally.

#### Step 2: Assess Starting Point (Greenfield vs Brownfield)

**If greenfield** (no existing code):
- Architecture is drafted from scratch based on the spec and research (Steps 3-4)
- No mapcodebase patterns to consume
- Taxonomy classification is the primary input

**If brownfield** (existing codebase):
- Load `.architecture/overview.md` and relevant component docs
- If `patterns[]` exists in manifest.json, list all `warning` and `error` patterns — these are the starting point for the architecture
- If gemini-bundle findings exist, load them as additional context
- The architecture document AUGMENTS existing patterns rather than replacing them
- Focus on: "what new patterns does this spec need?" and "which existing patterns need adjustment?"

#### Step 2b: Categorize the Application

Classify the application along dimensions relevant to its type. The taxonomy is NOT a fixed table — it adapts to the project category.

**For web applications:**
- Rendering (Static / SSR / CSR / Hybrid)
- Navigation (MPA / SPA / Hybrid)
- Auth (Anonymous / Session / Token / None)
- Data freshness (Static / SWR / Real-time / Mixed)
- State management (Server-only / Client-only / Hybrid)
- Multi-page data sharing (None / Context / Cache / URL state)

**For CLI tools / data pipelines:**
- Execution model (One-shot / Long-running / Daemon)
- State management (Stateless / File-based / Database)
- Concurrency (Sequential / Parallel / Async)
- Input/output (Stdin/stdout / File / API / Queue)

**For APIs / services:**
- Transport (REST / GraphQL / gRPC / WebSocket)
- Auth (Token / Session / mTLS / None)
- Data layer (SQL / NoSQL / File / In-memory)
- Scaling (Single-instance / Horizontal / Serverless)

**For any project:** Identify which dimensions apply. Don't force web-app dimensions onto a CLI tool.

Present the classification to the user for confirmation before proceeding.

#### Step 3: Research Best Practices

For each dimension in the taxonomy:
1. Look up the established pattern for the chosen stack
2. Minimum: 2 sources (official docs + community guide/template)
3. Use Context7 MCP tools if available for exact API signatures
4. Note where the framework provides a built-in solution vs. where a custom pattern is needed

Record sources in the architecture document.

#### Step 4: Draft Target Architecture Document

Produce `specs/<slug>/target-architecture.md` with one section per key architectural pattern. Each section:

```markdown
### [Pattern Name] (e.g., Data Fetching, Auth, State Persistence)

**Decision:** [What pattern we're using]
**Rationale:** [Why this pattern, referencing research sources]
**Alternative considered:** [What else was evaluated and why not chosen]
**Implementation sketch:** [Concrete code snippets or file structure]
**Applies to:** [Which user stories / features depend on this pattern]
```

If mapcodebase `patterns[]` data is available, address each flagged pattern:
- If severity is `warning` or `error`: the architecture MUST have a section resolving it
- If severity is `info`: note it and confirm current approach is intentional

#### Step 5: Debate the Architecture

Run the architecture through multi-model debate:

```bash
cat specs/<slug>/target-architecture.md | \
  python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --models MODEL_LIST --doc-type architecture --round N \
  --context specs/<slug>/spec-draft-latest.md \
  $CONTEXT_FLAGS
```

The `--doc-type architecture` system prompt focuses models on:
1. Are the chosen patterns appropriate for the application's category and scale?
2. Are there framework features being overlooked?
3. Will these patterns compose well across all features?
4. Are any "decisions" just restating framework defaults without evaluating alternatives?
5. Does the architecture actually enable the spec's user stories?

**If architecture debate reveals spec gaps:**
- Note the gap
- Revise the spec
- Re-run a spec debate round to confirm the change
- Resume architecture debate

Continue until architecture converges.

#### Step 6: Dry-Run Verification

Select the most complex user flow from the spec. Walk through it step-by-step against the architecture:
- Which component renders at each step?
- What data is fetched, by whom, via what mechanism?
- What state is created, where does it live, what happens on navigation?
- What happens on error at each step?

If the dry-run reveals gaps, revise the architecture and re-debate the specific change.

**The dry-run is the proof that the architecture is complete.** If you can't trace a full user flow through it, it's not done.

#### Step 7: Record Decisions

Before transitioning to gauntlet, record all architectural decisions in the Decision Journal (see Change 3 below).

### Outputs
- `specs/<slug>/target-architecture.md` — Target Architecture document
- Updated session state with Decision Journal entries
- Architecture taxonomy classification (stored in session state)

### Completion Criteria
- All taxonomy dimensions have a decided pattern with rationale
- At least one user flow dry-run completed without gaps
- Architecture debated via at least one converged round
- Decision Journal records the categorization and each pattern decision

### Phase Transition
On completion, sync both session files per Phase Transition Protocol:
- Detail file: set `current_phase: "gauntlet"`, set `target_architecture_path` to the architecture doc
- Pointer file: update accordingly
- The gauntlet input assembly (Phase 5) includes the target architecture document

## Change 2: New Adversary Persona — ARCH

Add to `adversaries.py` (the adversary definitions in scripts/):

```
ARCH — Architect
Role: Challenges internal code structure, data flow, and component boundaries
Perspective: Cares about how code is ACTUALLY organized — not just what services exist,
  but how data flows between components, how state is managed, and how shared patterns
  emerge or fragment
Attack style: Traces data flow through the system. Asks "what happens when..." for
  common user paths. Identifies missing shared abstractions.
Key questions:
- How does data flow from database through server components to client components?
- What shared infrastructure exists for auth, data fetching, caching, error handling?
- What happens to client state when a user navigates between pages?
- Where is the server/client component boundary and is it consistent?
- Are there patterns repeated across files that should be centralized?
- How will the first implementation's pattern propagate to subsequent implementations?
```

**ARCH participates in ALL gauntlet rounds**, not architecture-specific rounds. Architectural concerns cross all documents.

**All adversaries receive architecture context during arming.** The pre-gauntlet arming stage (04-gauntlet.md, now 05-gauntlet.md) already assembles per-adversary context. Add `target-architecture.md` to the context pool so every persona can attack it from their angle:
- PARA: "Your middleware sets x-user-id in headers — can a client spoof that?"
- BURN: "You assume React cache() deduplicates across parallel components — does it?"
- FLOW: "Your loading skeleton doesn't match the actual layout — jarring shift"
- AUDT: "Your localStorage keys include tournament IDs — what about multiple tournaments?"

## Change 3: Decision Journal

### Purpose
An append-only log in the session state tracking explicit decisions AND explicit non-decisions. Prevents the "we can't tell if this was considered or never thought of" problem.

### Schema (added to session detail file)

```json
{
  "decision_journal": [
    {
      "time": "ISO8601",
      "phase": "target-architecture",
      "topic": "auth-pattern",
      "decision": "adopt",
      "choice": "Middleware-based auth with cached fallback",
      "rationale": "Eliminates per-page auth calls, 200ms savings per navigation",
      "alternatives_considered": ["Per-page getUser()", "React cache() only"],
      "revisit_trigger": "If middleware latency exceeds 50ms"
    }
  ]
}
```

**Decision types:** `adopt`, `reject`, `defer`, `skip`, `reversed`

**Validation rules:**
- `decision_journal` is append-only — never edit or delete entries
- `reversed` entries must reference the original entry's `topic` and `time`
- All fields except `alternatives_considered` and `revisit_trigger` are required

### When to prompt

**NOT at every phase transition** (too much friction). Instead, prompt when:
- The Target Architecture phase completes (always — it's the primary source of decisions)
- The user explicitly defers or rejects something during any phase
- The gauntlet raises concerns that lead to design changes
- A phase transition involves a non-obvious choice (e.g., skipping a phase)

The prompt is:
```
Decision Journal
───────────────────────────────────────
Record decisions made during [phase]:

Decisions to log:
• [auto-detected from conversation context]

[Confirm] [Edit] [Add more] [Skip]
```

Auto-detection: scan conversation for patterns like "we decided," "let's go with," "deferring X," "rejected because."

### Schema version

Session state schema: v1.3 → v1.4

New fields:
- `decision_journal`: `[]` (default, append-only)
- `architecture_taxonomy`: `null | object` (set during Target Architecture phase)

**Migration:** On session load, if fields are missing, default to `[]` and `null`. No destructive changes. Existing v1.3 sessions continue to work.

## Change 4: debate.py — Add `--doc-type architecture`

### What changes
Add `architecture` as a valid `--doc-type` choice in debate.py's argument parser.

### System prompt for architecture critique

```
You are reviewing a Target Architecture document for a software project.

The document defines shared patterns that all implementation tasks must follow:
data fetching, auth, state management, caching, component boundaries, etc.

Focus your critique on:
1. Are the chosen patterns appropriate for the application's category and scale?
2. Are there framework-specific features or patterns being overlooked?
3. Will these patterns compose well across all pages/routes/features?
4. Are there missing patterns that this category of application typically needs?
5. Does the dry-run user flow work through the architecture without gaps?
6. Are any "decisions" just restating framework defaults without evaluation?
7. Is the architecture consistent with the product spec's requirements?

Be specific. Reference framework documentation. Propose concrete alternatives.
```

### Implementation location
- `prompts.py`: Add system prompt for `architecture` doc type
- `debate.py`: Add `architecture` to `--doc-type` choices
- Tests: Add test for architecture doc type selection

## Change 5: Gauntlet Input Expansion

### Current gauntlet input
The gauntlet assembles input from: spec + roadmap

### New gauntlet input
Assemble from: spec + roadmap + target architecture document

In `05-gauntlet.md` (renumbered), update the input assembly step to include:
```markdown
## Target Architecture (from Phase 4)
[Full target architecture document]
[Architecture taxonomy classification]
```

The pre-gauntlet arming stage adds `target-architecture.md` to the context pool. Every adversary persona receives it alongside the spec.

**If no target architecture exists** (legacy sessions, or Phase 4 was skipped): Gauntlet proceeds without it. Advisory note: "No target architecture available — architecture-level concerns may be underrepresented."

## Change 6: Execution Plan — Architecture Spine and Wave 0

### Architecture Spine
Add to the execution plan template (in `07-execution.md`, renumbered from 06) a new section between Scope Assessment and Wave 1:

```markdown
## Architecture Spine

Cross-cutting patterns from the Target Architecture. All tasks must follow these.

### [Pattern Name]
- **Pattern:** [one-line description]
- **Rule:** [what implementers must do / must not do]
- **Reference:** Target Architecture §[N], Wave 0 Task [ID]
```

### Wave 0: Architecture Foundation
The execution plan MUST include Wave 0 tasks that establish shared infrastructure before feature tasks begin:

- For each pattern in the Target Architecture, create a task establishing the shared abstraction
- Wave 0 tasks are blockers for all feature tasks that depend on the pattern
- Typical size: 4-8 tasks, S-M effort each

Example:
```
W0-1: Data Fetching Infrastructure → blocks all page tasks
W0-2: Auth Middleware → blocks all authenticated page tasks
W0-3: Loading Skeleton Pattern → blocks all async page tasks
W0-4: Client State Persistence → blocks interactive editor tasks
```

**If no target architecture exists:** Skip Wave 0 and Architecture Spine. Note in execution plan that architecture was not defined.

## Change 7: SKILL.md Updates

### Phase Router table
Update to include `target-architecture` phase:

```
| target-architecture | phases/04-target-architecture.md |
```

### Phase Transition Protocol
Add artifact path field:

```
| debate → target-architecture | (no new artifact path — spec already tracked) |
| target-architecture → gauntlet | target_architecture_path | Path to target-architecture.md |
```

### User Language → Phase Mapping
Add:

```
| "architecture," "target architecture," "how should we build it" | target-architecture |
```

### All phase number references
Search and update any hardcoded references to phases 04-07 throughout SKILL.md, reference docs, and session state handling.

## Testing Strategy

### Unit tests
1. `--doc-type architecture` selects correct system prompt
2. Decision journal append-only enforcement (reject in-place edits)
3. Schema v1.4 migration (v1.3 sessions get default values)
4. ARCH persona definition loads correctly
5. Scale check heuristic (small project → skip recommended)

### Integration tests
1. Full phase transition path with renumbered files
2. Gauntlet input assembly includes target architecture
3. Execution plan emits Architecture Spine + Wave 0 when architecture exists
4. Execution plan works without architecture (graceful degradation)

### Migration tests
1. Load v1.3 session → auto-upgrade → preserve all existing data
2. Load v1.4 session with empty decision_journal → no errors
3. Phase router resolves old and new phase numbers correctly

## Migration Plan

1. **Release v1.4 readers first** — session loading code accepts both v1.3 and v1.4 schemas.
2. **Missing fields get defaults** — `decision_journal: []`, `architecture_taxonomy: null`.
3. **Phase renumbering** — update all references in SKILL.md, reference docs, and phase files.
4. **Existing sessions past gauntlet** — skip Target Architecture retroactively. Log `skip` in decision journal: "Phase added post-session."
5. **No feature flags needed** — this is internal tooling used by one team. Deploy directly.

## Open Questions

1. Should the architecture debate rounds count as "debate phase" rounds (affecting convergence metrics), or are they tracked separately?
2. Should the taxonomy classification be debatable itself (run through critique), or is it a user-confirmed classification?
3. How should architecture drift during implementation be handled? Options: (a) manual edit + re-debate, (b) automatic architecture retro checkpoint after Wave 1, (c) both.
4. Should mapcodebase `patterns[]` eventually become required input (once available), or always optional?
5. Should gemini-bundle findings have a structured output format (JSON) that the Target Architecture phase can parse, or is free-text sufficient?
6. For brownfield projects: should the Target Architecture phase offer to UPDATE the existing `.architecture/` docs (feeding back into mapcodebase), or only produce its own `target-architecture.md`?
7. When re-entering adversarial-spec for a follow-up feature on the same codebase, should the previous session's `target-architecture.md` carry forward, or start fresh each time?
