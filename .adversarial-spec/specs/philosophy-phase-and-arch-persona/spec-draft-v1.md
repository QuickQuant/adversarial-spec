# Process Failure: Missing Target Architecture Phase Between Spec and Execution

**Date:** 2026-03-05
**Severity:** High — caused systemic architectural debt across all frontend pages, requiring retroactive rework
**Discovered during:** Adding top navigation bar to BracketBattleAI; navigation between pages revealed 3-second load times and destroyed client-side state

## What Happened

After implementing a navigation bar, switching between pages (bracket, leaderboard, compare, groups) took ~3 seconds each, and unsaved bracket picks were lost on every navigation. Investigation revealed:

1. **Every page independently creates a Supabase client, fetches auth, then fetches all its data** — no shared data layer, no caching, no request deduplication. Five sequential `await` calls before any HTML renders.
2. **All bracket state lives in React `useState` only** — no persistence layer between navigations. The bracket editor is a client component that initializes from server-fetched props. Navigate away, state is destroyed. Navigate back, full server re-fetch, client component remounts from scratch.
3. **No `loading.tsx` files existed** — users saw a completely frozen screen during the 3-second server-side data fetching.

This is not a bug in any single page. It's a **systemic pattern** — every page was built the same way because no shared architecture was defined before execution began. The pattern was established in W1-5 (Landing Page + Auth Flow UI) and then copied verbatim into every subsequent page across Waves 2-7.

## Root Cause Analysis

### The immediate cause: no "Target Architecture" document

The adversarial-spec workflow has these phases:

```
Research → Brainstorm → Spec → Gauntlet → Execution Plan → Implementation
```

The **spec** (Sections 7-8) describes service topology:
> "Services: Cloudflare CDN → Railway (Next.js web + Node.js workers) → Supabase PostgreSQL/Auth → Railway Redis."

And component design:
> "Node.js (frontend/): Web App (Next.js 15 App Router — SSR, client bracket editor via bracketry.js, /api/v1/ routes)"

But neither section describes **how the frontend works internally:**
- How pages share data (auth state, tournament data, user profile)
- Where the server/client component boundary sits
- What caching/deduplication strategy applies to Supabase calls
- How client-side state survives navigation
- What loading/streaming pattern to use

The **execution plan** breaks the spec into 50 tasks. Each task is self-contained:
- "W1-5: Landing Page + Auth Flow UI" — build a page
- "W2-6: Basic Leaderboard" — build another page
- "W3-5: Share Cards + OG Images" — build another page

No task says: "Establish the shared data fetching pattern that all pages will use." No task says: "Define the server/client component boundary." No task says: "Set up React `cache()` wrappers for common queries."

### The structural cause: spec describes *what* systems exist, not *how* they compose

The spec correctly identifies all the pieces:
- Next.js 15 App Router
- Supabase for auth and data
- Server-side rendering
- Client components for interactivity

But it never describes the **data flow architecture** — the pattern by which data moves from Supabase, through server components, into client components, and back. This is the difference between a **system topology** (boxes and arrows) and a **target architecture** (how the code is actually structured).

Analogy: the spec is a city map showing where the buildings are. The target architecture is the building code that says how thick the walls must be, where the plumbing runs, and how the electrical connects. Without building code, every contractor builds their own way. That's what happened — 50 tasks, each building their own plumbing.

### The process cause: adversarial-spec skips the "categorize and research" step

The adversarial-spec workflow jumps from "what does this product do?" (spec) directly to "what tasks do we execute?" (execution plan). It never pauses to ask:

1. **What category of application is this?** — A multi-page SPA with server-side data fetching, real-time updates, and authenticated routes. This is a well-understood category with established patterns.
2. **What are the known best practices for this category in our chosen stack?** — Next.js App Router has specific patterns for shared layouts, streaming, `cache()`, `unstable_cache`, middleware-based auth, and Suspense boundaries.
3. **What does a "golden path" implementation look like?** — The Next.js docs, Supabase Next.js guides, and Vercel templates all demonstrate recommended data fetching patterns. None of them show "every page independently creates its own client and fetches its own auth."
4. **What shared infrastructure must exist before page-level tasks begin?** — Auth middleware, cached data fetchers, loading skeletons, error boundaries.

This is the missing phase: **philosophy**. Before planning tasks, categorize the program, research best practices for the category, and define a target architecture that all tasks must conform to.

### The multi-agent cause: no shared code review for cross-cutting patterns

The two-agent workflow (Claude + Codex) uses a card-by-card review process. The review question is: "Does this card's implementation work correctly?" It is NOT: "Is this card's implementation consistent with a healthy overall architecture?"

When Codex built W1-5 (Landing Page) with independent Supabase calls, the review said "LGTM — page works." When Codex built W2-5 (AI Bracket Viewer) with the same pattern, the review said "LGTM — page works." By W3-3 (Real-Time Leaderboard), the pattern was cemented. No review ever asked "should all these pages share a data layer?"

This is the classic **local optima** problem in multi-agent systems. Each agent optimizes for their card. No agent optimizes for the system.

## Compounding Failure: The Process Doesn't Track Its Own Decisions

Investigation into whether architecture was ever considered during planning revealed a deeper problem: **the adversarial-spec workflow does not record process-level decisions, only events.**

### What the session tracking actually records

The session file (`.adversarial-spec/sessions/adv-spec-20260302-bracketbattleai-product.json`) has a `journey` array with 278 timestamped events. These record **what happened:**

```json
{"time": "2026-03-02T06:50:00Z", "event": "Debate Round 3: Open questions + scoring systems", "type": "debate"}
{"time": "2026-03-03T13:53:00Z", "event": "Execution plan v1 complete — 43 tasks across 6 waves", "type": "milestone"}
```

But they do not record **what was decided or rejected:**
- No entry says: "Architecture coverage deemed sufficient by spec sections 7-8"
- No entry says: "Considered architecture review phase, deferred due to timeline"
- No entry says: "Frontend data flow patterns left to implementation-time decisions"

Checkpoints (11 in `.adversarial-spec/checkpoints/`) are state snapshots — "here's where we are" — not decision logs — "here's what we chose and why."

### The consequence: we cannot distinguish between "decided not to" and "never considered"

When investigating this failure, the first question was: "Did we consider architecture and decide the spec was sufficient, or did we never think about it?"

The answer is: **we literally cannot tell.** The tracking system treats both identically — as silence. There is no negative space in the journey log. Unconsidered options leave no trace.

This matters because the remediation is different:
- If we **considered and rejected** architecture planning, we need to understand why the rejection criteria were wrong
- If we **never considered** it, we need to understand why the workflow didn't prompt for it

Based on the evidence, it's almost certainly "never considered." The adversarial-spec skill defines 7 phases in `/adversarial-spec/skills/adversarial-spec/phases/`:

```
01-init-and-requirements.md
02-roadmap.md
03-debate.md
04-gauntlet.md
05-finalize.md
06-execution.md
07-implementation.md
```

There is no `XX-architecture.md` or `XX-philosophy.md` phase file. The workflow literally does not have this step. It's not that we skipped it — it was never a defined option. The assembly line has no station for this work.

### The gauntlet didn't catch it either

The gauntlet stress-tests the spec using 7 adversary personas: PARA (security), BURN (assumption destroyer), LAZY (deadline pressure), PEDA (teacher), ASSH (antagonist), AUDT (auditor), FLOW (UX). None of these personas is an architect. None asks:

- "How do your server components share data?"
- "What's your caching strategy for repeated auth calls?"
- "How does client state survive navigation?"

The gauntlet generated 155 concerns. Zero were about frontend data flow architecture. The concern space was shaped by the personas, and no persona was designed to think about internal code structure.

### Proposed fix: Decision Journal

In addition to the journey event log, the session should maintain a **decision journal** — an append-only log of explicit decisions AND explicit non-decisions:

```json
{
  "time": "2026-03-03T14:00:00Z",
  "type": "decision",
  "topic": "Architecture review phase",
  "decision": "skip",
  "rationale": "Spec sections 7-8 cover system topology. Internal patterns left to implementation.",
  "revisit_trigger": "If multiple pages show inconsistent data fetching patterns"
}
```

The key fields:
- **`decision`**: What was chosen (`skip`, `adopt`, `defer`, `reject`)
- **`rationale`**: Why — even one sentence prevents "we can't tell what happened" later
- **`revisit_trigger`**: Under what conditions this decision should be reconsidered

This applies to process decisions (which phases to run), content decisions (which options to pick), and scope decisions (what to defer). The journal should be prompted at every phase transition: "Before moving to the next phase, are there any decisions or deferrals to record?"

### Proposed fix: Architect persona in the gauntlet

Add an **ARCH** persona to the gauntlet adversary set:

```
ARCH (Architect): Challenges internal code structure, data flow patterns,
component boundaries, caching strategies, and state management. Asks:
"How does data actually flow through the system at the code level?
Where are the shared abstractions? What happens when a user navigates
between pages? How does state persist?"
```

With philosophy placed BEFORE the gauntlet (see Change 1 below), the ARCH persona has actual architecture to attack. Without philosophy, ARCH would only be able to say "you don't have architecture" — useful but shallow. With the Target Architecture document in the gauntlet input, ARCH can critique specific decisions: "Your `cache()` wrapper strategy doesn't account for per-user cache invalidation on sign-out" or "Your localStorage persistence will conflict with SSR hydration."

The other existing personas also benefit from seeing the architecture:
- **PARA** (security): "Your middleware sets `x-user-id` in headers — can a client spoof that header?"
- **BURN** (assumption destroyer): "You assume React `cache()` deduplicates across parallel server components — does it?"
- **FLOW** (UX): "Your loading skeleton for the bracket page doesn't match the actual layout — users will see a jarring shift"
- **AUDT** (auditor): "Your localStorage keys include tournament IDs — what happens when a user has brackets from multiple tournaments?"

This is the key insight: **the gauntlet gets more powerful when it has more surface area to attack.** Adding the architecture document to the gauntlet input doesn't just enable ARCH — it gives every persona new attack vectors they couldn't reach before.

## What the Process Should Have Caught

### Phase gap: "Philosophy" between Spec and Execution Plan

Before writing the execution plan, the workflow should include a phase that:

1. **Categorizes the application** by its runtime characteristics
2. **Researches established patterns** for that category in the chosen stack
3. **Produces a Target Architecture document** that defines shared patterns
4. **Generates architectural "guardrail" tasks** that must precede feature tasks

### Categorization framework

Every web application falls into a taxonomy that determines which architectural patterns apply:

| Dimension | Options | BracketBattleAI |
|-----------|---------|-----------------|
| **Rendering** | Static / SSR / CSR / Hybrid | Hybrid (SSR pages + CSR interactive components) |
| **Navigation** | MPA / SPA / Hybrid | SPA with server component pages (Next.js App Router) |
| **Auth** | Anonymous / Session / Token | Session-based (Supabase auth cookies) |
| **Data freshness** | Static / Stale-while-revalidate / Real-time | Mixed (static tournament structure + real-time scores) |
| **State management** | Server-only / Client-only / Hybrid | Hybrid (server-fetched props + client-side editor state) |
| **Multi-page data sharing** | None / Context / Cache / URL | None (this is the bug) |
| **User interaction depth** | Read-heavy / Write-heavy / Interactive | Interactive (bracket editor with complex cascading picks) |

Once categorized, the target architecture follows from established patterns for that combination.

### What the Target Architecture document should contain

For BracketBattleAI specifically, a target architecture phase would have produced:

#### 1. Data Fetching Pattern

```
Decision: Use React `cache()` to deduplicate Supabase calls within a single request.
Rationale: Multiple server components in the same render tree (layout + page + nested
components) often need the same data (auth user, tournament, teams). React `cache()`
ensures each unique query executes once per request, regardless of how many components
call it.

Implementation:
- `lib/supabase/cached.ts` exports cached versions of common queries
- `getAuthUser()` wraps `supabase.auth.getUser()` with `cache()`
- `getActiveTournament()` wraps tournament query with `cache()`
- All page server components import from `cached.ts`, never call Supabase directly
```

#### 2. Auth Pattern

```
Decision: Extract auth to Next.js middleware. Set user ID in request headers.
Rationale: Every authenticated page currently makes its own auth call (~200ms each).
Middleware runs once per request, before any server component. Pages read the header
instead of making a network call.

Alternative considered: Supabase's `getUser()` with cookie-based sessions.
Why rejected for sole use: Adds 200ms latency to every page, even when auth state
hasn't changed. Middleware can short-circuit with cached session validation.
```

#### 3. Server/Client Component Boundary

```
Decision: Server components own data fetching. Client components own interactivity.
The boundary is at the "editor" or "interactive widget" level.

Rules:
- Pages and layouts are always server components
- Data is fetched in server components and passed as props to client components
- Client components never call `fetch()` for initial data (only for mutations and
  real-time updates)
- The bracket editor is a client component that receives initial state as props
  and manages its own state for user interactions

Exception: Real-time features (SSE leaderboard, countdown timers) use client-side
`useEffect` with event sources.
```

#### 4. Client State Persistence

```
Decision: Interactive editors persist draft state to localStorage.
Rationale: The bracket editor holds complex cascading state (63 picks with
dependency pruning). Users will navigate away and back. Server components remount
on every navigation. Without client-side persistence, all unsaved work is lost.

Implementation:
- Key: `bba-draft-{tournamentId}-{window}`
- Save: On every pick change via `useEffect`
- Restore: On mount, if localStorage has more picks than server-provided initial state
- Clear: After successful save to database
```

#### 5. Navigation and Loading Pattern

```
Decision: Every route segment with async data fetching gets a `loading.tsx`.
Rationale: Next.js App Router automatically wraps pages in <Suspense> when
`loading.tsx` exists. Without it, navigation freezes until the server component
finishes rendering. With it, users see an animated skeleton immediately.

Implementation:
- `app/bracket/loading.tsx` — bracket skeleton
- `app/leaderboard/loading.tsx` — table rows skeleton
- `app/compare/loading.tsx` — comparison grid skeleton
- `app/groups/loading.tsx` — card grid skeleton
```

#### 6. Shared Layout Data

```
Decision: Root layout contains the nav bar (server component). Nav reads auth once.
Rationale: Root layouts persist across navigation in App Router. Auth state read
once in the layout propagates to the nav without re-fetching on every page change.
Page-specific data is fetched in page server components only.

Implication: The nav's auth state may be stale if the user signs in/out in another
tab. This is acceptable — the next navigation will re-render the layout only if
Next.js determines the layout's dependencies changed.
```

### How this integrates into the execution plan

The execution plan currently starts with Wave 1 Task 1: "Project Scaffold + Monorepo Structure." The target architecture should appear as **Wave 0: Architecture Foundation** — a set of tasks that establish shared patterns before any feature page is built.

Example tasks that would have prevented this failure:

```
### Task W0-1: Data Fetching Infrastructure
- Create `lib/supabase/cached.ts` with React `cache()` wrappers
- `getAuthUser()`, `getActiveTournament()`, `getTeams(tournamentId)`
- All subsequent page tasks must import from this module

### Task W0-2: Auth Middleware
- Next.js middleware that validates Supabase session
- Sets `x-user-id` and `x-user-email` headers
- Redirects unauthenticated requests to `/` for protected routes

### Task W0-3: Loading Skeleton Pattern
- Create `app/loading.tsx` (root) with generic skeleton
- Document the pattern: every new page route gets a `loading.tsx`
- Add to task template: "Acceptance criteria: loading.tsx exists"

### Task W0-4: Client State Persistence Pattern
- Create `lib/local-draft.ts` with `saveDraft()` / `loadDraft()` / `clearDraft()`
- Document the pattern: interactive editors use this for unsaved state
- Bracket editor task (W2-1) must use this
```

These W0 tasks become **blockers** for all page-level tasks. The execution plan's dependency graph would show:

```
W0-1 (cached fetchers) ──┬── W1-5 (landing page)
W0-2 (auth middleware)  ──┤── W2-5 (AI bracket viewer)
W0-3 (loading skeletons) ┤── W2-6 (leaderboard)
W0-4 (state persistence) ┘── W3-5 (share cards)
                               ... every page task
```

## Proposed Changes to the Adversarial-Spec Workflow

### Change 1: Add "Philosophy" phase BEFORE the Gauntlet

New phase sequence:

```
Research → Brainstorm → Spec → Philosophy → Gauntlet → Execution Plan → Implementation
```

**Critical ordering decision:** Philosophy must come BEFORE the gauntlet, not after it. The gauntlet stress-tests the combined spec + architecture. If philosophy comes after the gauntlet, the adversaries never see the architecture — they can only attack the product spec. By placing philosophy before the gauntlet:

1. The gauntlet's 7+ adversary personas attack the **complete system** — product design AND architecture
2. The ARCH persona (proposed below) has architecture to critique instead of empty space
3. Architecture decisions get the same multi-round adversarial pressure as product decisions
4. Weak architectural patterns are caught before they enter the execution plan

This also means the gauntlet input document (`gauntlet-input.md`) expands from "spec + roadmap" to "spec + roadmap + target architecture." The adversaries receive the full picture.

**The Philosophy phase may require multiple rounds.** Unlike the spec (which is primarily a product document), the target architecture requires:
- Round 1: Categorize and draft initial architecture
- Round 2: Research best practices, refine with actual framework documentation
- Round 3: Dry-run a representative page through the architecture to verify it works end-to-end

Only after these rounds is the architecture ready for the gauntlet.

The Philosophy phase produces a **Target Architecture** document by:

**Step 1: Categorize the application**
- Use the taxonomy table above (rendering, navigation, auth, data freshness, state management, multi-page sharing, interaction depth)
- This is a 10-minute exercise that determines which patterns apply
- The categorization is debatable — run it through the adversarial debate system with `--doc-type decision`

**Step 2: Research best practices for the category**
- For each dimension, look up the established pattern in the chosen stack
- Next.js App Router: consult the official docs on data fetching, caching, streaming, and middleware
- Supabase + Next.js: consult the Supabase SSR guide
- General patterns: consult the React server components RFC and Vercel's architecture guides
- This is where `docmaster` shines — exact API signatures and recommended patterns
- Minimum research per dimension: 2 sources (official docs + community guide)

**Step 3: Produce Target Architecture document**
- One section per dimension from the taxonomy
- Each section: Decision, Rationale, Alternative considered, Implementation sketch
- Include code snippets for shared infrastructure (cached fetchers, middleware, persistence helpers)
- This document becomes a **reference** for all implementation tasks

**Step 4: Dry-run a representative user flow through the architecture**
- Pick the most complex user-facing flow (for BracketBattleAI: "user logs in, fills bracket, navigates to leaderboard, comes back, picks are still there")
- Walk through the architecture document step by step: which component renders, what data is fetched where, what state is created, what happens on navigation
- If the dry-run reveals gaps ("wait, how does the bracket state survive navigation?"), revise the architecture before proceeding
- The dry-run is the **proof that the architecture is complete** — if you can't trace a full user flow through it, it's not done

**Step 5: Feed into gauntlet**
- Append the Target Architecture document to the gauntlet input alongside the spec and roadmap
- The ARCH adversary persona (and all other personas) now have architecture to attack
- Multiple gauntlet rounds may iterate on both the spec and the architecture simultaneously

**Step 6: Generate Wave 0 tasks (post-gauntlet)**
- For each section of the target architecture, create a task that establishes the shared pattern
- These tasks block all feature tasks that depend on the pattern
- Estimate effort: typically S-M per task, 4-8 tasks total, 1-2 days
- Wave 0 tasks go into the execution plan, which is written AFTER the gauntlet (unchanged)

### Change 2: Add "Architecture Spine" section to the Execution Plan

The execution plan currently has:
- Summary
- Scope Assessment
- Waves 1-7 (tasks)
- Test Strategy
- Open Questions

Add a new section between Scope Assessment and Wave 1:

```markdown
## Architecture Spine

Cross-cutting patterns that all tasks must follow. Established in Wave 0.
See Target Architecture document for full rationale.

### Data Fetching
- **Pattern:** React `cache()` wrappers in `lib/supabase/cached.ts`
- **Rule:** Pages never create Supabase clients directly
- **Reference:** Target Architecture §1, Task W0-1

### Authentication
- **Pattern:** Middleware extracts auth, pages read headers
- **Rule:** Pages never call `auth.getUser()` directly
- **Reference:** Target Architecture §2, Task W0-2

### Loading States
- **Pattern:** Every async page route has `loading.tsx`
- **Rule:** New page tasks include loading.tsx in acceptance criteria
- **Reference:** Target Architecture §5, Task W0-3

### Client State Persistence
- **Pattern:** Interactive editors persist drafts to localStorage
- **Rule:** Editors use `lib/local-draft.ts`, never raw useState for persistent data
- **Reference:** Target Architecture §4, Task W0-4

### Server/Client Boundary
- **Pattern:** Server components fetch, client components interact
- **Rule:** Client components receive data as props, never call fetch() for initial load
- **Reference:** Target Architecture §3
```

This section serves as a **quick reference** during implementation. When an agent picks up a task, they check the Architecture Spine for applicable patterns. When a reviewer reviews a commit, they check compliance with the spine.

### Change 3: Add architecture compliance to the review checklist

The current review process (`.coordination/PROTOCOL.md`) checks:
- Does the code work?
- Do tests pass?
- Is the Trello card updated?

Add:
- **Does this code follow the Architecture Spine patterns?**
  - Data fetching: uses cached wrappers, not raw Supabase?
  - Loading: has `loading.tsx` if it's a new page?
  - Auth: reads from middleware, not direct `getUser()`?
  - State: interactive state persisted to localStorage?

This prevents the "local optima" problem where each card looks correct in isolation but the system-level architecture degrades.

### Change 4: Architecture retro checkpoint

Add a mandatory checkpoint after Wave 1 (or the first wave that produces multiple pages):

```
After Wave 1: Architecture Retro
- Are all pages following the Architecture Spine patterns?
- Is any pattern proving impractical? Revise the Target Architecture.
- Are new patterns emerging that should be added to the spine?
- Run a 10-page smoke test: does navigation between all pages feel instant?
```

This catches drift early, before 50 tasks cement the wrong pattern.

### Change 5: Cross-System Integration — mapcodebase + adversarial-spec + gemini-bundle

The fixes above (Philosophy phase, ARCH persona, Architecture Spine) address the adversarial-spec workflow in isolation. But the tooling already has three systems that should work together on this problem:

1. **mapcodebase** — generates architecture documentation from code (descriptive)
2. **adversarial-spec** — stress-tests documents via multi-model debate (prescriptive)
3. **gemini-bundle** — packages code + architecture for external model review (cross-check)

Today these are disconnected. mapcodebase produces docs, adversarial-spec debates the spec, and gemini-bundle sends code to Gemini for critique. The architecture problem fell through because no system bridges the gap between "describe the code" and "evaluate whether the code patterns are correct."

#### 5a. mapcodebase enhancement: Pattern Analysis phase

mapcodebase v2.3 detects problems at the **component level** — per-file perf issues, concurrency hazards, partial implementations. It caught "Feature flags queried per-request with no caching" (one file) but missed "auth queried per-page with no caching" (12 files, same pattern).

The gap: mapcodebase analyzes components in isolation. It never compares similar files to each other.

**Add Phase 5: Pattern Analysis** to mapcodebase, after the existing Phase 4 (Reality Check + Hazard Detection):

```
Phase 5: Cross-Cutting Pattern Analysis

Input: All page entry points, all component files of the same type
Method:
  1. Group files by role (all page.tsx, all route.ts, all components/*.tsx)
  2. For each group, extract the repeated structural pattern:
     - What imports does every file use?
     - What setup code does every file repeat?
     - What could be shared but isn't?
  3. Compare the repeated pattern against known best practices for the stack
  4. Flag: "N files repeat pattern X — established best practice is Y"

Output: New manifest section `patterns[]` with:
  - pattern_id: descriptive name
  - files: list of files exhibiting the pattern
  - description: what the pattern does
  - concern: why it may be problematic (or null if fine)
  - best_practice: what the framework/stack recommends instead
  - severity: info | warning | error
  - category: data-fetching | auth | state-management | loading | error-handling
```

For BracketBattleAI, this would have produced:

```json
{
  "pattern_id": "per-page-auth",
  "files": ["app/bracket/page.tsx", "app/leaderboard/page.tsx", "app/compare/page.tsx",
            "app/groups/page.tsx", "app/groups/[groupId]/page.tsx", "app/ai/[modelSlug]/page.tsx"],
  "description": "Each page independently calls getSupabaseServerClient() + auth.getUser()",
  "concern": "Redundant auth network call on every page navigation (~200ms each). Next.js App Router supports React cache() deduplication or middleware-based auth.",
  "best_practice": "Wrap auth in React cache() for per-request deduplication, or extract to middleware",
  "severity": "warning",
  "category": "auth"
},
{
  "pattern_id": "missing-loading-skeletons",
  "files": ["app/bracket/", "app/leaderboard/", "app/compare/", "app/groups/"],
  "description": "No loading.tsx files in any page route with async data fetching",
  "concern": "Navigation freezes until server component finishes. Next.js shows no UI during server render without loading.tsx.",
  "best_practice": "Every route segment with async server components should have a loading.tsx",
  "severity": "warning",
  "category": "loading"
},
{
  "pattern_id": "ephemeral-editor-state",
  "files": ["components/bracket-editor.tsx"],
  "description": "Complex interactive state (63 bracket picks with cascading dependencies) stored only in React useState",
  "concern": "State destroyed on navigation. No localStorage/sessionStorage backup. User loses unsaved work.",
  "best_practice": "Persist draft state to localStorage, restore on remount",
  "severity": "warning",
  "category": "state-management"
}
```

This is the detection that was missing. The feature-flag warning (line 197 of `manifest.json`) proves mapcodebase can detect per-request-no-caching issues — it just needs to generalize from single-file detection to cross-file pattern detection.

#### 5b. Adversarial-spec integration: debate the patterns

mapcodebase's pattern analysis produces *findings*. But findings from a single model (Claude) have blind spots — exactly the problem adversarial-spec was built to solve. The pattern analysis output should be **debatable**.

During the Philosophy phase (Change 1), after mapcodebase runs Pattern Analysis:

1. Extract the `patterns[]` array from the manifest
2. Format it as a debate input document: "Here are the cross-cutting patterns detected in the codebase. For each pattern flagged as warning/error, evaluate: Is this actually a problem? Is the suggested best practice correct for our constraints? Are there better alternatives?"
3. Run through `debate.py critique --doc-type architecture` (or the proposed `debate.py decide` mode)
4. Codex and Gemini attack the findings:
   - "The per-page auth pattern is actually fine if you use Supabase's session caching"
   - "The missing loading.tsx is a real problem — but streaming with Suspense boundaries is better than static loading.tsx"
   - "localStorage for bracket state introduces SSR hydration mismatches — consider a different persistence strategy"
5. Synthesize: which patterns are genuine problems, which are acceptable tradeoffs, and what the actual fix should be

This converts mapcodebase's unilateral findings into adversarially-verified architectural decisions.

#### 5c. gemini-bundle integration: external cross-check

The gemini-bundle skill (plan: `~/.claude/plans/streamed-sparking-parrot.md`) already packages architecture docs for Gemini and asks it to critique gaps. The integration point is the **Architecture Review Request** in the instructions file (Phase 3, section 7).

Currently the gemini-bundle instructions ask Gemini to:
- Identify gaps in the architecture documentation
- Flag source code patterns not captured in the docs
- Note contradictions between docs and code
- Suggest improvements to documentation structure

**Extend this to include pattern analysis critique:**

```markdown
## Architecture Review Request

### Documentation Completeness (existing)
[... existing review questions ...]

### Cross-Cutting Pattern Review (new)
The architecture manifest includes a `patterns[]` array identifying repeated
code patterns across the codebase. For each pattern:

1. Is this pattern correctly identified? Does the code actually do this?
2. Is the flagged concern valid for this application's scale and requirements?
3. Is the suggested best practice the right one, or is there a better approach?
4. Are there patterns the analysis MISSED that you can see in the source code?
5. For any pattern marked "info" (not flagged as concerning) — should it be?

Pay special attention to patterns that cross component boundaries (e.g., auth
patterns used in every page, data fetching patterns repeated across routes).
These are the hardest for single-component analysis to catch.
```

This makes Gemini a third reviewer of the pattern analysis — independent from Claude (who generated the findings) and Codex/Gemini-CLI (who debated them during the Philosophy phase). The gemini-bundle review happens on the actual bundled source code, not just the architecture docs, so Gemini can verify the findings against reality.

#### The feedback loop

These three systems form a continuous improvement cycle:

```
mapcodebase (detect)
    │
    ├── Pattern Analysis: "12 pages repeat independent auth calls"
    │
    ▼
adversarial-spec (debate)
    │
    ├── Philosophy phase: Codex + Gemini debate the findings
    ├── "Is this actually a problem? What's the right fix?"
    │
    ▼
gemini-bundle (cross-check)
    │
    ├── External model reviews source + architecture + patterns
    ├── "Your analysis missed X" or "Pattern Y is fine, here's why"
    │
    ▼
mapcodebase (improve)
    │
    ├── Gemini's findings feed back as mapcodebase enhancements
    ├── New pattern detectors, refined severity, better best-practice suggestions
    │
    └── (cycle repeats on next run)
```

The key insight from the gemini-bundle plan: *"Gemini identifies gaps → we improve mapcodebase → better architecture docs for all projects."* This is already the stated design intent. The pattern analysis phase makes the feedback loop concrete — Gemini isn't just reviewing prose documentation, it's reviewing structured pattern findings that can be directly improved in mapcodebase's detection logic.

#### Timing in the workflow

```
Research → Brainstorm → Spec
    │
    ▼
Philosophy (NEW)
    ├── Step 1: Run mapcodebase with Pattern Analysis (if codebase exists)
    ├── Step 2: Categorize application taxonomy
    ├── Step 3: Research best practices per category
    ├── Step 4: Debate pattern findings via adversarial-spec
    ├── Step 5: Produce Target Architecture document
    ├── Step 6: Dry-run a user flow through the architecture
    │
    ▼
Gauntlet (receives spec + target architecture + pattern analysis)
    ├── ARCH persona attacks architecture decisions
    ├── All personas get expanded attack surface
    │
    ▼
gemini-bundle (optional, pre-execution cross-check)
    ├── Bundle code + architecture + patterns for external review
    ├── Gemini verifies pattern findings against actual source
    │
    ▼
Execution Plan (Wave 0 + Architecture Spine)
    │
    ▼
Implementation
```

For greenfield projects (no codebase yet), the Philosophy phase skips Step 1 (mapcodebase) and relies on Steps 2-6 (taxonomy, research, debate, document, dry-run). For existing codebases being refactored, Step 1 provides the starting point: "here's what the code does today, here are the patterns we found."

## Impact on Current Project (BracketBattleAI)

### Immediate fixes applied (this session)
1. Added `loading.tsx` skeletons for bracket, leaderboard, compare, groups pages
2. Added localStorage draft persistence to the bracket editor
3. Both are band-aids — they treat symptoms, not the root cause

### Root cause fix needed (future session)
1. Create `lib/supabase/cached.ts` with `cache()` wrappers for `getAuthUser()`, `getActiveTournament()`, `getTeams()`
2. Refactor all pages to use cached fetchers instead of raw Supabase calls
3. Consider auth middleware to eliminate per-page `getUser()` calls entirely
4. Parallelize remaining sequential queries with `Promise.all()` where dependencies allow

### Estimated rework
- Cached fetchers: S (1-2hr) — create the module, it's ~50 lines
- Refactor all pages: M (3-4hr) — ~12 pages, mechanical find-and-replace of Supabase calls
- Auth middleware: M (2-3hr) — middleware + update all pages to read headers
- Total: ~6-9 hours of rework that would have been 2-3 hours of upfront architecture

## Lessons for Future Projects

1. **The spec answers "what does this product do?" The target architecture answers "how does the code do it."** Both are required before execution. They are different documents answering different questions, and the second cannot be derived from the first.
2. **Application categories predict architectural needs.** A multi-page SSR app with auth will always need shared data fetching, loading states, and client state persistence. These are properties of the category, not surprises. A 10-minute taxonomy exercise would have predicted every issue we hit.
3. **Multi-agent execution amplifies architectural omissions.** A solo developer might notice the pattern degrading and self-correct. Two agents executing cards in parallel will each build their own local solution. Without a shared architecture reference, divergence is guaranteed.
4. **The first page sets the template.** Whatever pattern W1-5 establishes will be copied by every subsequent page task. If W1-5 does independent Supabase calls, every page will. If W1-5 uses cached fetchers, every page will. This makes "get the first page right" an architectural decision, not just a feature task.
5. **Card-by-card review cannot catch system-level patterns.** The review must include a cross-cutting checklist, or architectural drift becomes invisible until a user-facing symptom appears (like 3-second page loads).
6. **Architecture must be stress-tested by the same adversarial process as the product spec.** Placing philosophy before the gauntlet means architecture gets the same multi-round, multi-persona pressure that catches product issues. If the architecture is only reviewed by the person who wrote it, blind spots survive.
7. **A workflow that doesn't track its own decisions is a workflow that can't learn from its own mistakes.** The absence of a decision journal meant we couldn't even diagnose whether architecture was considered and rejected, or never considered at all. Process improvement requires process observability.
8. **Dry-run a real user flow through the architecture before writing tasks.** Abstract architecture documents miss concrete gaps. Walking through "user logs in → fills bracket → navigates to leaderboard → comes back" would have immediately surfaced "wait, what happens to the bracket state?" The dry-run is the proof that the architecture is complete.

## Files Referenced

### Symptom files (code)
- `frontend/src/app/layout.tsx` — root layout (modified to add SiteNav)
- `frontend/src/app/bracket/page.tsx` — bracket page with independent Supabase calls
- `frontend/src/app/leaderboard/page.tsx` — leaderboard page with same pattern
- `frontend/src/app/compare/page.tsx` — compare page with same pattern
- `frontend/src/app/groups/page.tsx` — groups page with same pattern
- `frontend/src/components/bracket-editor.tsx` — bracket editor with useState-only state

### Process gap files
- `.adversarial-spec/specs/bracketbattleai/spec-draft-v4.md` §7-8 — architecture/component sections (gap: no internal data flow)
- `.adversarial-spec/specs/bracketbattleai/execution-plan.md` — execution plan (gap: no Wave 0, no architecture spine)
- `.coordination/PROTOCOL.md` — review protocol (gap: no architecture compliance check)

### Process tracking files (evidence of tracking gap)
- `.adversarial-spec/sessions/adv-spec-20260302-bracketbattleai-product.json` — 278 journey events, none recording architecture decisions
- `.adversarial-spec/session-state.json` — snapshot only, no decision history
- `.adversarial-spec/checkpoints/*.md` — state snapshots, not decision logs

### Workflow definition files (evidence of missing phase)
- `adversarial-spec/skills/adversarial-spec/phases/01-init-and-requirements.md`
- `adversarial-spec/skills/adversarial-spec/phases/02-roadmap.md`
- `adversarial-spec/skills/adversarial-spec/phases/03-debate.md`
- `adversarial-spec/skills/adversarial-spec/phases/04-gauntlet.md`
- `adversarial-spec/skills/adversarial-spec/phases/05-finalize.md`
- `adversarial-spec/skills/adversarial-spec/phases/06-execution.md`
- `adversarial-spec/skills/adversarial-spec/phases/07-implementation.md`
- (No `XX-philosophy.md` or `XX-architecture.md` exists)

### Architecture documentation (mapcodebase output)
- `.architecture/manifest.json` — warnings[] caught feature-flag caching but missed auth/data-fetching pattern; no patterns[] section exists yet
- `.architecture/overview.md` — "Non-Obvious Things" section documents gotchas but doesn't evaluate patterns
- `.architecture/structured/components/frontend-ui.md` — describes per-page Supabase pattern as fact, doesn't flag it
- `.architecture/structured/components/auth-system.md:78` — explicitly states "no custom auth middleware" but doesn't evaluate whether there should be

### Cross-system integration files
- `~/.claude/plans/streamed-sparking-parrot.md` — gemini-bundle skill plan (architecture review request in Phase 3 §7 is the integration point)
- mapcodebase skill definition (Phase 4A/4B detect problems; proposed Phase 5 adds cross-cutting pattern analysis)

### Related process failure
- `.adversarial-spec/issues/process-failure-technical-decisions.md` — debate.py lacks `--doc-type decision` mode (related: architecture decisions couldn't have been debated even if the phase existed)

---

## Appendix A: Implementation Guide — mapcodebase Skill (Brainquarters Project)

This appendix provides file-level implementation details for adding Pattern Analysis to the mapcodebase skill. The mapcodebase skill lives in the **Brainquarters** project.

### Skill Location and Structure

```
/home/jason/PycharmProjects/Brainquarters/skills/mapcodebase/
├── SKILL.md                          # Skill definition (phases, quality checks, output format)
├── prompts/
│   ├── explore-control-flow.md       # Explorer subagent prompt: control flow analysis
│   ├── explore-data-flow.md          # Explorer subagent prompt: data flow tracing
│   ├── explore-error-handling.md     # Explorer subagent prompt: error handling patterns
│   └── explore-entry-exit.md         # Explorer subagent prompt: entry/exit point mapping
└── templates/
    ├── overview-template.md          # Template for .architecture/overview.md
    ├── component-template.md         # Template for .architecture/structured/components/*.md
    └── index-template.md             # Template for .architecture/INDEX.md
```

### Current Phase Structure (SKILL.md)

The skill defines 6 phases:

| Phase | Name | Purpose |
|-------|------|---------|
| 1 | Discovery | Glob/grep to inventory all source files, package configs, entry points |
| 2 | Parallel Exploration | Launch 4 explorer subagents (one per prompt) in parallel |
| 3 | Synthesis | Merge subagent outputs into structured architecture docs |
| 4A | Reality Check | Verify documented claims against actual code (catches stale/wrong docs) |
| 4B | Hazard Detection | Identify security, performance, and reliability hazards per-component |
| 5 | Quality Gate | Run 14+ quality checks, produce manifest.json with warnings[] and hazards[] |
| 6 | Output | Write all files to `.architecture/`, update manifest.json with git hash |

### Where to Add Pattern Analysis

**Insert Phase 5: Pattern Analysis** between the current Phase 4B (Hazard Detection) and Phase 5 (Quality Gate). Renumber existing Phase 5 → Phase 6, Phase 6 → Phase 7.

New phase sequence:
```
Phase 1: Discovery
Phase 2: Parallel Exploration
Phase 3: Synthesis
Phase 4A: Reality Check
Phase 4B: Hazard Detection
Phase 5: Pattern Analysis    ← NEW
Phase 6: Quality Gate        ← was Phase 5
Phase 7: Output              ← was Phase 6
```

### Files to Modify

#### 1. `SKILL.md` — Add Phase 5 definition

Add the new phase between Phase 4B and the current Phase 5. Match the existing phase format:

```markdown
### Phase 5: Cross-Cutting Pattern Analysis

**Input:** All files inventoried in Phase 1, structured components from Phase 3
**Method:**

1. **Group files by role:**
   - Page entry points (e.g., `app/**/page.tsx`, `pages/**/*.py`, `routes/**/*.go`)
   - API route handlers
   - Components/widgets of the same type
   - Configuration files
   - Test files (check for pattern consistency with source)

2. **For each group, extract the repeated structural pattern:**
   - Common imports across all files in the group
   - Setup/boilerplate code repeated in every file
   - Data fetching patterns (how data enters the file)
   - Error handling patterns (how errors are caught/propagated)
   - Authentication patterns (how auth state is accessed)

3. **Compare against best practices for the detected stack:**
   - Use framework documentation (via docmaster if available) to identify recommended patterns
   - Flag patterns where N files repeat code that the framework provides a centralized solution for
   - Flag patterns where shared abstractions exist but aren't being used

4. **Produce `patterns[]` array for manifest**

**Quality threshold:** At least 2 pattern groups analyzed. If the codebase has <5 files, skip this phase (too small for cross-cutting analysis).
```

Update the Quality Gate phase to add pattern-related checks:
```markdown
### Phase 6: Quality Gate (updated)

Existing checks (14+) remain unchanged. Add:

- [ ] `patterns[]` array present in manifest (may be empty if Phase 5 skipped)
- [ ] Each pattern entry has all required fields (pattern_id, files, description, severity, category)
- [ ] Patterns with severity "warning" or "error" have non-null `concern` and `best_practice` fields
- [ ] No pattern references files not in the Phase 1 inventory
```

#### 2. New file: `prompts/explore-patterns.md` — Explorer subagent prompt

Create a new explorer prompt following the existing format. Existing explorer prompts share this structure:

```markdown
# Explorer: [Name]

## Objective
[What this explorer is looking for]

## Instructions
1. [Step-by-step investigation approach]
2. [What to look for in each file]
3. [How to structure findings]

## Output Format
[Structured output that Phase 3 Synthesis can consume]
```

The pattern analysis prompt should:

```markdown
# Explorer: Cross-Cutting Patterns

## Objective
Identify repeated code patterns across files of the same type. Find patterns that
indicate missing shared abstractions or framework features not being used.

## Instructions
1. Group all source files by role (page routes, API handlers, components, utilities)
2. For each group with 3+ files:
   a. Read the first 50 lines of each file
   b. Identify the common "setup block" — imports, client creation, auth checks, data fetching
   c. Note what varies between files (only the business logic) vs. what is identical boilerplate
   d. Assess whether the repeated code could be centralized per the framework's documented patterns
3. For the authentication pattern specifically:
   a. How many files independently fetch auth state?
   b. Is there a middleware, shared hook, or cached wrapper?
   c. What does the framework recommend?
4. For data fetching:
   a. How many files create their own database/API clients?
   b. Are queries deduplicated across components in the same request?
   c. Are loading states handled consistently?

## Output Format
For each detected pattern:
- **pattern_id**: `kebab-case-name`
- **files**: List of file paths exhibiting this pattern
- **description**: What the code does (neutral, factual)
- **concern**: Why this might be problematic (null if acceptable)
- **best_practice**: What the framework/stack recommends instead (null if current approach is correct)
- **severity**: `info` (observed, no concern) | `warning` (suboptimal, should fix) | `error` (will cause user-facing issues)
- **category**: `data-fetching` | `auth` | `state-management` | `loading` | `error-handling` | `configuration`
```

#### 3. `templates/` — Add pattern analysis output template

Create `templates/patterns-template.md`:

```markdown
# Cross-Cutting Pattern Analysis

> Generated by mapcodebase Phase 5 — compares repeated code patterns against
> framework best practices.

## Patterns Detected

### [pattern_id]
- **Files:** [N files]
  - `path/to/file1.ext`
  - `path/to/file2.ext`
- **Description:** [what the code does]
- **Severity:** [info|warning|error]
- **Category:** [category]
- **Concern:** [why problematic, or "None — pattern is appropriate"]
- **Recommended:** [best practice, or "Current approach is correct"]

---
[Repeat for each pattern]

## Summary
- **Total patterns detected:** N
- **Info:** N | **Warning:** N | **Error:** N
- **Top concern:** [most impactful pattern to address]
```

#### 4. Manifest schema addition

The manifest (`manifest.json`) currently has `warnings[]` and `hazards[]` at the top level. Add `patterns[]` alongside them.

Current manifest structure:
```json
{
  "version": "2.3",
  "git_hash": "abc123",
  "generated": "2026-03-04T...",
  "components": [...],
  "entry_points": [...],
  "warnings": [
    {"code": "PERF: ...", "file": "path", "line": 42}
  ],
  "hazards": [
    {"type": "security", "description": "...", "files": [...]}
  ]
}
```

Add:
```json
{
  "patterns": [
    {
      "pattern_id": "per-page-auth",
      "files": ["app/bracket/page.tsx", "app/leaderboard/page.tsx"],
      "description": "Each page independently calls auth.getUser()",
      "concern": "Redundant network call per navigation",
      "best_practice": "React cache() wrapper or middleware",
      "severity": "warning",
      "category": "auth"
    }
  ]
}
```

### Key Design Notes for the Implementing Agent

1. **Phase 5 runs AFTER Phase 4B** — it needs the component analysis from Phase 3 to know what roles files play, and the hazard detection from 4B to avoid duplicating per-file issues.

2. **The explorer prompt (`explore-patterns.md`) launches as a subagent** — same pattern as the other 4 explorers. It can run in parallel with nothing (Phase 2 already completed), or it can be added to the Phase 2 parallel batch if Phase 5 is moved earlier.

3. **Best-practice lookup should use docmaster when available** — the prompt should instruct the explorer to check framework docs for recommended patterns. If docmaster isn't configured for the target project, fall back to the explorer's training knowledge.

4. **Empty `patterns[]` is valid** — small codebases or codebases with good abstractions may produce no patterns. The quality gate should accept `patterns: []` without failing.

5. **The `patterns[]` output feeds into two downstream consumers:**
   - The gemini-bundle skill (includes pattern findings in the Architecture Review Request)
   - The adversarial-spec Philosophy phase (debates pattern findings with multiple models)
   - Both consumers read `manifest.json` — no special output format needed beyond the manifest

---

## Appendix B: Implementation Guide — adversarial-spec Skill

This appendix provides file-level implementation details for the adversarial-spec skill changes proposed in this document. The adversarial-spec skill lives in its own project.

### Skill Location and Structure

```
/home/jason/PycharmProjects/adversarial-spec/
├── skills/adversarial-spec/
│   ├── SKILL.md                    # Main skill definition
│   └── phases/
│       ├── 01-init-and-requirements.md
│       ├── 02-roadmap.md
│       ├── 03-debate.md
│       ├── 04-gauntlet.md
│       ├── 05-finalize.md
│       ├── 06-execution.md
│       └── 07-implementation.md
├── adversaries/
│   ├── personas.md                 # 7 adversary persona definitions (PARA, BURN, LAZY, PEDA, ASSH, AUDT, FLOW)
│   └── briefing-supplements/
│       └── *.md                    # Per-persona supplements
├── debate.py                       # CLI for running debates (codex/gemini invocation)
├── session-state-schema.md         # Session state JSON schema (v1.3)
└── ...
```

### Changes Required

#### Change 1: New Phase File — `phases/04-philosophy.md`

Insert a new phase between `03-debate.md` and `04-gauntlet.md`. Renumber all subsequent phases:

```
01-init-and-requirements.md     (unchanged)
02-roadmap.md                   (unchanged)
03-debate.md                    (unchanged)
04-philosophy.md                ← NEW
05-gauntlet.md                  ← was 04
06-finalize.md                  ← was 05
07-execution.md                 ← was 06
08-implementation.md            ← was 07
```

The phase file format follows the convention of existing phases. Each phase file contains:
- **Phase name and number**
- **Prerequisites** (what must be complete before this phase starts)
- **Inputs** (what documents/artifacts feed into this phase)
- **Steps** (numbered, actionable instructions for the agent)
- **Outputs** (what documents/artifacts this phase produces)
- **Completion criteria** (how to know when to move to next phase)

Content for `04-philosophy.md`:

```markdown
# Phase 4: Philosophy — Target Architecture

## Prerequisites
- Spec draft complete (Phase 3 output)
- Roadmap complete (Phase 2 output)

## Inputs
- Spec draft document
- Roadmap document
- `.architecture/manifest.json` (if codebase exists — from mapcodebase)
  - Specifically: `patterns[]` array if mapcodebase v3+ with Pattern Analysis
- Framework documentation (via docmaster or web)

## Steps

### Round 1: Categorize and Draft
1. Categorize the application using the taxonomy framework:
   - Rendering (Static / SSR / CSR / Hybrid)
   - Navigation (MPA / SPA / Hybrid)
   - Auth (Anonymous / Session / Token)
   - Data freshness (Static / SWR / Real-time)
   - State management (Server-only / Client-only / Hybrid)
   - Multi-page data sharing (None / Context / Cache / URL)
   - User interaction depth (Read-heavy / Write-heavy / Interactive)
2. For each dimension, propose the target pattern for the chosen stack
3. Draft the Target Architecture document (one section per key pattern)
4. If mapcodebase `patterns[]` exist, address each flagged pattern in the architecture

### Round 2: Research and Refine
5. For each pattern decision, research the framework's recommended approach
   - Minimum: 2 sources (official docs + community/template)
   - Use docmaster if available for exact API signatures
6. Run the categorization AND the draft through debate:
   ```
   debate.py critique --doc-type architecture --input target-architecture-draft.md
   ```
7. Incorporate debate feedback into the architecture document

### Round 3: Dry-Run Verification
8. Select the most complex user flow from the spec
9. Walk through the flow step-by-step against the architecture:
   - Which component renders at each step?
   - What data is fetched, by whom, via what mechanism?
   - What state is created, where does it live, what happens on navigation?
10. Document any gaps discovered during the dry-run
11. Revise the architecture to close gaps
12. Record all decisions in the Decision Journal (see session state changes below)

## Outputs
- `specs/<project>/target-architecture.md` — Target Architecture document
- Updated session state with Decision Journal entries
- Architecture taxonomy classification (stored in session state)

## Completion Criteria
- All taxonomy dimensions have a decided pattern with rationale
- At least one user flow dry-run completed without gaps
- Architecture debated via at least one round of `debate.py critique --doc-type architecture`
- Decision Journal records the categorization and each pattern decision
```

#### Change 2: New Adversary Persona — ARCH

Add to `adversaries/personas.md`. Existing persona format:

```markdown
### [CODE] — [Name]
**Role:** [one-line description]
**Perspective:** [what this persona cares about]
**Attack style:** [how they challenge the document]
**Key questions:**
- [question 1]
- [question 2]
- ...
```

Add ARCH persona:

```markdown
### ARCH — Architect
**Role:** Challenges internal code structure, data flow, and component boundaries
**Perspective:** Cares about how the code is ACTUALLY organized — not just what services exist, but how data flows between components, how state is managed, and how shared patterns emerge or fragment
**Attack style:** Traces data flow through the system. Asks "what happens when..." for common user paths. Identifies missing shared abstractions and copied-instead-of-shared code.
**Key questions:**
- How does data flow from the database through server components to client components?
- What shared infrastructure exists for auth, data fetching, caching, and error handling?
- What happens to client state when a user navigates between pages?
- Where is the server/client component boundary and is it consistent across pages?
- Are there patterns repeated across multiple files that should be centralized?
- What does the caching strategy look like — per-request, per-session, global?
- How will the first page's implementation pattern propagate to subsequent pages?
```

Optionally create `adversaries/briefing-supplements/arch-supplement.md` for framework-specific attack vectors.

#### Change 3: Update Gauntlet Phase — Expanded Input

Modify `phases/05-gauntlet.md` (renumbered from 04) to include the Target Architecture document in the gauntlet input assembly:

Current gauntlet input assembly step (paraphrased):
> Assemble gauntlet input from: spec draft + roadmap

Update to:
> Assemble gauntlet input from: spec draft + roadmap + target architecture document

The gauntlet input document (`gauntlet-input.md`) should include a new section:
```markdown
## Target Architecture (from Philosophy phase)
[Include the full target architecture document]
[Include the architecture taxonomy classification]
[If mapcodebase ran: include pattern findings summary from patterns[]]
```

#### Change 4: Session State Schema Changes

The session state schema (`session-state-schema.md`, currently v1.3) needs two additions:

**Decision Journal array:**
```json
{
  "decision_journal": [
    {
      "time": "ISO8601",
      "phase": "philosophy",
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

Decision types: `adopt` (chose this approach), `reject` (considered and declined), `defer` (postpone to later phase), `skip` (explicitly chose not to address).

**Architecture taxonomy:**
```json
{
  "architecture_taxonomy": {
    "rendering": "hybrid",
    "navigation": "spa-server-components",
    "auth": "session-cookie",
    "data_freshness": "mixed",
    "state_management": "hybrid",
    "multi_page_sharing": "react-cache",
    "interaction_depth": "interactive"
  }
}
```

Bump schema version to v1.4.

#### Change 5: debate.py — Add `--doc-type architecture`

The `debate.py` CLI currently supports doc-types for `spec`, `roadmap`, and (proposed) `decision`. Add `architecture` as a doc-type.

The `--doc-type` flag determines the system prompt given to the debating models. For `architecture`:

```
You are reviewing a Target Architecture document for a software project.

Focus your critique on:
1. Are the chosen patterns appropriate for the application's category and scale?
2. Are there framework-specific features or patterns being overlooked?
3. Will these patterns compose well across all pages/routes in the application?
4. Are there missing patterns that this category of application typically needs?
5. Does the dry-run user flow actually work through the described architecture without gaps?
6. Are any "decisions" actually just restating the framework defaults without evaluating alternatives?

Be specific. Reference framework documentation. Propose concrete alternatives when you disagree.
```

#### Change 6: Phase Transition Decision Journal Prompt

At every phase transition (when moving from one phase to the next), add a standard prompt to record decisions. This should be in `SKILL.md`'s general instructions section:

```markdown
### Phase Transition Protocol
Before moving to the next phase, record in the Decision Journal:
1. What key decisions were made in this phase?
2. What alternatives were considered and rejected? Why?
3. What was deferred to a later phase? Under what conditions should it be revisited?
4. Were there any topics that were NOT considered that arguably should have been?

Each entry must have: time, phase, topic, decision, rationale, and revisit_trigger.
```

### Key Design Notes for the Implementing Agent

1. **File renumbering**: All phases 04-07 shift to 05-08. Any references to phase numbers in `SKILL.md`, session state, checkpoints, or the journey log must be updated. Search for phase number references across the project.

2. **Backward compatibility**: Existing sessions in progress (session state v1.3) don't have `decision_journal` or `architecture_taxonomy`. The schema migration should treat both as optional arrays that default to `[]` and `null` respectively if missing.

3. **Philosophy phase is optional for existing specs**: If an adversarial-spec session was already past the gauntlet when this change lands, don't force a retroactive Philosophy phase. Add a note to the session that philosophy was skipped (pre-change), and record this in the decision journal.

4. **The ARCH persona participates in ALL gauntlet rounds**, not just an architecture-specific round. ARCH should attack the spec, roadmap, and architecture simultaneously — architectural concerns cross all documents.

5. **debate.py `--doc-type architecture`**: The architecture system prompt should be longer/more detailed than spec or roadmap prompts because architecture has more concrete technical content to evaluate. The debating models need enough context to assess whether patterns are framework-appropriate.

6. **The decision journal is append-only** — never edit or delete entries. If a decision is reversed, add a new entry with `decision: "reversed"` referencing the original entry's topic and time.

---

## Appendix C: Integration Points Between Skills

This appendix maps the data flow between mapcodebase, adversarial-spec, and gemini-bundle.

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ mapcodebase (Brainquarters)                                 │
│                                                             │
│ Phase 5: Pattern Analysis                                   │
│   Output: manifest.json { patterns: [...] }                 │
│           .architecture/patterns.md (human-readable)        │
│                                                             │
│   Consumers:                                                │
│     → adversarial-spec Philosophy phase reads patterns[]    │
│     → gemini-bundle slot 1 includes patterns.md             │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ adversarial-spec (adversarial-spec project)                 │
│                                                             │
│ Phase 4: Philosophy                                         │
│   Input: spec + roadmap + manifest.json patterns[]          │
│   Process:                                                  │
│     - Categorize application taxonomy                       │
│     - Research best practices per category                  │
│     - Draft Target Architecture addressing each pattern     │
│     - debate.py critique --doc-type architecture            │
│     - Dry-run user flow                                     │
│   Output: target-architecture.md                            │
│           decision_journal entries in session state          │
│                                                             │
│ Phase 5: Gauntlet                                           │
│   Input: spec + roadmap + target-architecture.md            │
│   ARCH persona attacks architecture alongside all others    │
│   Output: gauntlet findings (may revise architecture)       │
│                                                             │
│ Phase 7: Execution Plan                                     │
│   Input: finalized spec + target architecture               │
│   Output: execution plan with Wave 0 + Architecture Spine   │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ gemini-bundle (Brainquarters — plan in progress)            │
│                                                             │
│ Slot 1: architecture.md                                     │
│   Includes: overview + INDEX + components + patterns.md     │
│                                                             │
│ Last slot: instructions.md                                  │
│   Section 7: Architecture Review Request                    │
│   Subsection 7a (existing): Documentation completeness      │
│   Subsection 7b (new): Cross-cutting pattern review         │
│     → "For each pattern in patterns[], verify against       │
│        actual source code. Flag missed patterns."           │
│                                                             │
│ Output: Gemini's findings feed back to mapcodebase          │
│   → New pattern detectors, severity adjustments,            │
│     best-practice refinements                               │
└─────────────────────────────────────────────────────────────┘
```

### File Paths That Connect the Systems

| Artifact | Producer | Location | Consumers |
|----------|----------|----------|-----------|
| `manifest.json` with `patterns[]` | mapcodebase Phase 5 | `.architecture/manifest.json` | adversarial-spec Philosophy, gemini-bundle slot 1 |
| `patterns.md` (human-readable) | mapcodebase Phase 5 | `.architecture/patterns.md` | gemini-bundle slot 1 (merged into architecture bundle) |
| `target-architecture.md` | adversarial-spec Philosophy | `.adversarial-spec/specs/<project>/target-architecture.md` | adversarial-spec Gauntlet, Execution Plan |
| `decision_journal` | adversarial-spec (all phases) | `.adversarial-spec/sessions/<session>.json` | Process retrospectives, debugging |
| Architecture Review findings | gemini-bundle (Gemini output) | External (Gemini response) | mapcodebase improvements (manual) |

### Implementation Order

These changes can be implemented independently — no circular dependencies:

1. **mapcodebase Pattern Analysis** (Brainquarters) — can ship immediately, no dependency on adversarial-spec changes. Produces `patterns[]` that downstream consumers read when ready.

2. **adversarial-spec Philosophy phase + ARCH persona + Decision Journal** (adversarial-spec project) — can ship independently. If `patterns[]` doesn't exist in manifest yet, the Philosophy phase skips pattern-based analysis and proceeds with taxonomy + research only.

3. **gemini-bundle pattern review extension** (Brainquarters) — can ship independently. If `patterns[]` doesn't exist, the cross-cutting pattern review section notes "No pattern analysis available — recommend running mapcodebase with Pattern Analysis phase."

Each skill gracefully degrades when upstream data isn't available yet. Full integration happens when all three are updated.
