## Context Addition Protocol

### Purpose

Opponent models only see what is piped to them via stdin. Without codebase context, they can only critique internal coherence of the spec. With targeted context, they can validate the spec against real code artifacts -- catching mismatches between what the spec proposes and what actually exists.

This protocol defines WHEN and HOW the orchestrating agent (Claude) should enrich spec documents with codebase context before sending them to opponent models.

**Relationship to existing mechanisms:**
- `--context` flag: Passes whole files. Good for static docs, bad for extracting targeted snippets.
- Pre-gauntlet `ContextBuilder`: Collects git position, build health, schema snapshots. Runs before gauntlet, not during debate rounds.
- This protocol: Fills the gap between those two -- targeted extraction during debate rounds, scoped to what the current round needs.

---

### 1. When to Add Context

Context extraction has a cost: tokens, latency, and noise. Only add it when it will change the quality of critique.

| Round | Focus | Add Context? | Rationale |
|-------|-------|:------------:|-----------|
| **Round 1** | Requirements validation | **No** | Requirements are about user value and story coverage. Code artifacts add noise. Exception: if the spec references existing behavior ("maintain backward compatibility with X"), extract X's interface. |
| **Round 2** | Architecture and design | **Yes** | This is the primary round for context. Models need to see real schema, real types, real function signatures to validate proposed architecture against what exists. |
| **Round 3** | Implementation details | **Yes (selective)** | Add only artifacts directly referenced by the round's concerns. If Round 2 already included the schema, do not re-include it. Add new artifacts only (e.g., a specific function body if the critique questions an algorithm). |
| **Round 4+** | Refinement | **Rarely** | Only if a specific concern requires verification against code. Most refinement rounds are about spec coherence, not code alignment. |

**Decision rule:** Before extracting context, ask: "Would an engineer reviewing this spec open a specific file to validate a claim?" If yes, extract that artifact. If the spec is self-contained for this round's focus, skip context.

---

### 2. What to Extract

**Always extract (when adding context at all):**
- Schema definitions (`schema.ts`, `schema.prisma`, `models.py`, etc.)
- TypeScript/Python type definitions and interfaces referenced in the spec
- Function signatures (name, params, return type) for functions the spec modifies or wraps
- Key constants and configuration shapes (e.g., `config.ts` exports)
- Enum definitions that define state machines or status flows

**Extract when relevant to the round:**
- Existing API route signatures (request/response types) when the spec proposes new or modified endpoints
- Database table definitions when the spec proposes schema changes
- Test file structure (file names only, not test bodies) when the spec proposes a testing strategy
- Error type definitions when the spec proposes error handling changes

**Never extract:**
- Full file contents (use targeted snippets, not `cat file.ts`)
- Implementation bodies of functions (signatures are enough; bodies waste tokens)
- Node modules, lock files, or generated code
- `.env` files, credentials, secrets, or config values containing keys
- Git history or diffs (the pre-gauntlet handles this)
- Test assertion bodies (opponent models do not need to review test logic)

---

### 3. How to Extract

The orchestrating agent (Claude) performs extraction directly using its available tools. There is no separate script for this -- the agent uses Grep, Read, and Glob during the synthesis step between debate rounds.

**Extraction workflow (between rounds, before sending to opponents):**

```
1. Identify spec claims that reference codebase artifacts
   - Look for: table names, function names, type names, file paths, module names
   - Example: "Extend the `orders` table with a `status` field" -> extract orders table definition

2. Extract targeted artifacts using tools:
   - Grep: Find where a type/function is defined
     grep -n "export interface Order" convex/
   - Read: Pull the specific lines (not the whole file)
     Read convex/schema.ts lines 45-72
   - Glob: Find related files
     glob "convex/**/*order*"

3. Format as appendix (see Section 4)

4. Verify size budget (see Section 5)

5. Attach appendix to spec before piping to opponents
```

**Extraction commands (examples):**

```bash
# Schema definitions
grep -A 30 "orders:" convex/schema.ts

# Function signatures (just the export line + params)
grep -A 5 "export.*function.*placeOrder" worker/src/

# Type definitions
grep -A 20 "export interface OrderRequest" worker/src/types.ts

# Constants and config shape
grep -A 10 "export const" worker/src/lib/config.ts

# Existing API routes
grep "httpRouter\|\.route(" convex/http.ts
```

---

### 4. Format

Context is appended as a clearly separated appendix at the end of the spec, AFTER the `[/SPEC]` tag's content but still within the heredoc sent to the debate script. This prevents opponents from confusing context with spec content.

```markdown
[SPEC]
... spec content ...
[/SPEC]

---

## APPENDIX: Codebase Context (Round N)

> This appendix contains real code artifacts extracted from the codebase.
> Use these to validate the spec's claims against what actually exists.
> Extraction timestamp: 2026-02-09T14:30:00Z | Git: abc1234 (branch: feature-x)

### A1. Schema: convex/schema.ts (lines 45-72)

```typescript
orders: defineTable({
  exchange: v.string(),
  exchangeOrderId: v.string(),
  side: v.union(v.literal("buy"), v.literal("sell")),
  price: v.number(),
  quantity: v.number(),
  status: v.string(),
  // ...
})
```

### A2. Interface: worker/src/types.ts (lines 12-28)

```typescript
export interface OrderRequest {
  exchange: "kalshi" | "polymarket";
  ticker: string;
  side: "buy" | "sell";
  price: number;
  quantity: number;
}
```

### A3. Function Signature: worker/src/connectors/kalshi.ts (line 89)

```typescript
export async function placeOrder(
  credentials: ExchangeCredentials,
  order: OrderRequest
): Promise<OrderResponse>
```
```

**Formatting rules:**
- Each artifact gets a numbered label (`A1`, `A2`, ...) for easy reference in critiques
- Include the source file path and line numbers
- Use the correct language tag on code fences
- Keep each artifact self-contained -- an opponent model should understand it without reading the full file
- Add a one-line note if the artifact has been truncated (e.g., "// ... 15 more fields omitted")

---

### 5. Size Budget

**Hard limit: 200 lines for the appendix.** This keeps the appendix under ~25% of a typical spec, avoiding the failure mode where context drowns out the document being reviewed.

| Artifact Type | Typical Size | Budget Guideline |
|---------------|:------------:|:----------------:|
| Schema table definition | 10-30 lines | 2-3 tables max |
| Interface/type definition | 5-20 lines | 3-5 types max |
| Function signature | 3-8 lines | 5-8 signatures max |
| Constants/enums | 5-15 lines | 2-3 max |
| Architecture overview excerpt | 15-30 lines | 1 max |

**If the appendix exceeds 200 lines:**
1. Prioritize artifacts that the spec directly modifies over artifacts it merely references
2. Trim function signatures to just the export line (omit param docs)
3. Truncate large schemas to only the tables/fields mentioned in the spec
4. Remove architecture overview (opponents can infer architecture from types and signatures)

**If the appendix is under 50 lines:** You are probably under-extracting. Check if the spec references artifacts you have not included.

---

### 6. Architecture Docs

The `.architecture/` directory (when it exists) contains high-level system overviews. These are useful but expensive in tokens.

**Include `.architecture/overview.md` (or equivalent) when:**
- Round 2 is the first round with context (opponents have no prior codebase knowledge)
- The spec proposes a new component that interacts with multiple existing components
- The spec changes data flow between existing components

**Skip architecture docs when:**
- Round 3+ (opponents already saw it in Round 2)
- The spec modifies a single, isolated component
- The schema and type definitions already tell the story
- The architecture overview exceeds 40 lines (extract only the relevant subsection instead)

**How to include:**
- Extract only the section relevant to the spec's scope, not the full overview
- Place it as `A0` (before code artifacts) since it provides the framing
- Example: if the spec is about order execution, extract only the "Order Flow" or "Trading Pipeline" section from the architecture overview

```markdown
### A0. Architecture Context: .architecture/overview.md (lines 34-58)

> Extracted subsection: "Order Execution Pipeline"

The worker receives order requests via the Convex HTTP action `placeOrder`,
routes them through exchange-specific connectors, and writes results back
to the `orders` table via mutation...
```

---

### 7. Staleness Warning

Codebase context can become stale between the time it is extracted and when opponent models read it. Always mark extraction provenance.

**Required header on every appendix:**

```markdown
> Extraction timestamp: 2026-02-09T14:30:00Z | Git: abc1234 (branch: feature-x)
```

**The orchestrating agent must capture:**
- Timestamp of extraction (ISO 8601)
- Current git HEAD short hash (first 7 chars)
- Current branch name

**Staleness rules:**
- If the appendix was extracted in a previous round and no relevant commits have landed since, reuse it with a note: `(reused from Round N, no relevant changes)`
- If new commits have landed that touch files in the appendix, re-extract those specific artifacts
- If the working tree is dirty (uncommitted changes to files in the appendix), add a warning: `WARNING: Uncommitted changes exist in [file]. Extracted content may not match working state.`

**How to capture git info:**

```bash
# Short hash
git rev-parse --short HEAD

# Branch name
git branch --show-current

# Check if specific files have uncommitted changes
git diff --name-only -- convex/schema.ts worker/src/types.ts
```

---

### Integration with Debate Flow

This protocol slots into **Step 4** of `03-debate.md` (Send to Opponent Models). The modified flow:

1. (Existing) Revise spec based on previous round's feedback
2. **(New) Context extraction decision:** Based on the round number and focus, decide whether to add/update the appendix
3. **(New) Extract and format:** If adding context, run the extraction workflow from Section 3
4. **(New) Assemble payload:** Combine spec + appendix into the heredoc
5. (Existing) Send to debate script via stdin

The appendix is **not part of the spec itself**. When extracting the `[SPEC]...[/SPEC]` content for persistence or checkpointing, strip the appendix. The appendix is ephemeral -- it exists only in the payload sent to opponents.

### Integration with `--context` Flag

The `--context` flag and this protocol serve different purposes and can be used together:

| Mechanism | What it sends | Who decides | Scope |
|-----------|---------------|-------------|-------|
| `--context` flag | Whole files | User | Static across all rounds |
| This protocol | Targeted snippets | Orchestrating agent | Per-round, evolves with debate |

If the user passes `--context ./schema.sql`, do not duplicate that content in the appendix. Reference it: `(See --context file: schema.sql for full schema. Relevant excerpt below.)`

### Integration with Context Readiness Audit

The Context Readiness Audit (see `03-debate.md`, runs between Round 1 and Round 2) produces a `ContextInventoryV1` cached in session state. This inventory is the **source of truth** for what context is available.

**How this protocol uses the inventory:**

1. **Round 2 (first round with context):** Instead of extracting artifacts from scratch, check the inventory for `AVAILABLE` sources. Extract from the paths and line ranges recorded there. This avoids redundant Grep/Read calls.

2. **Round 3+:** Check if inventory `git_hash` matches current HEAD. If stale, re-extract only modified artifacts. If current, reuse with note: `(reused from Round N, no relevant changes)`.

3. **Token tracking:** When assembling the appendix, estimate tokens for each artifact (`len(text) // 4`) and include a total in the appendix header:

   ```markdown
   > Extraction timestamp: 2026-02-09T14:30:00Z | Git: abc1234 (branch: feature-x)
   > Context tokens: ~1,180 (A0: 400, A1: 350, A2: 280, A3: 150)
   ```

4. **Gap awareness:** If the inventory has `NOT_AVAILABLE` sources relevant to this round's focus, note them at the end of the appendix:

   ```markdown
   ### Context Gaps (from audit)
   - Test coverage: No pytest-cov configured. Tests exist but coverage unknown.
   - Monitoring: No alerting configured (CLI tool).
   ```

   This gives opponent models visibility into what they CAN'T validate.

**If no inventory exists** (audit was skipped, or the debate started without it): Fall back to the extraction workflow in Section 3 above. The inventory is a cache optimization, not a hard dependency.

### Integration with Arm Adversaries

The same inventory feeds the Arm Adversaries step (see `04-gauntlet.md`) which assembles per-adversary briefings before the gauntlet. The key difference:

| This protocol (debate rounds) | Arm Adversaries (gauntlet) |
|-------------------------------|---------------------------|
| Same appendix for all opponent models | Per-adversary briefings with unique supplements |
| Targeted snippets (200-line budget) | Larger context packages (up to 2x spec size) |
| Evolves per round | One-shot assembly before attack generation |
| Claude extracts manually | Claude assembles from inventory + fresh extraction |

Both draw from the same inventory. Neither should re-extract what the other already has.
