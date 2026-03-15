# Adversary Request: Existing System Compatibility Auditor

**Date:** 2026-01-24
**Requesting Project:** prediction-prime
**Issue Discovered During:** Order Execution implementation (Phase 3)

---

## Executive Summary

During implementation of the order-execution spec (which passed through the full adversarial gauntlet with 179 concerns identified), we discovered that **the codebase itself was not deployable** due to pre-existing schema/data drift unrelated to our changes. None of the 5+ adversarial LLMs that reviewed the spec caught this because they operated on the spec document in isolation, without grounding their review in the actual codebase.

This document requests a new adversary type that focuses specifically on **compatibility between proposed changes and the existing system state**.

---

## The Incident

### What We Were Doing

Implementing Phase 3 of the order-execution spec: adding `placeDma` action with risk management. This required:
- Adding `user_risk_state` table to schema
- Adding `balance_cache` table to schema
- Creating mutations for order placement with exposure reservation

### What Happened

When we ran `npx convex dev --once` to verify the build, it failed with schema validation errors:

```
Schema validation failed.
Document with ID "js7002306cp0jb8ndk1m4203s97ymxap" in table "matchPairs"
does not match the schema: Object contains extra field `matchConfidence`
that is not in the validator.
```

The errors continued for multiple tables:
- `matchPairs` had legacy fields (matchConfidence, matchType, reasoning, differencesSummary, differencesAnalyzedAt)
- `workers` had legacy fields (canTakeMore, currentCount, lastHeartbeat, updatedAt, workerId) and status "dead"

### Root Cause

Previous PRs had modified the schema to refactor these tables:
- **PR #170** (Jan 17): Split matchPairs metadata to matchPairs_meta table
- **Earlier commits**: Simplified workers table for new lifecycle model

These schema changes were merged **without accompanying data migrations**. The production/dev Convex deployment had data that no longer matched the schema. This drift existed for days/weeks before we discovered it.

### Why the Gauntlet Missed It

The adversarial spec process ran 5+ LLMs against the order-execution spec. They generated 179 concerns across categories:
- ASSH (Conditions Not Addressed)
- BURN (Spec Allows Harmful Behavior)
- PEDA (Spec is Pedantic/Ambiguous)
- PARA (Paranoid Edge Cases)
- LAZY (Missing Validation)

**Not a single concern asked:**
- "Does the current schema deploy cleanly?"
- "What is the actual state of `schema.ts` right now?"
- "Are there existing tables or fields that conflict with our proposed additions?"
- "Have there been recent schema changes that might affect deployability?"

The adversaries reviewed the **proposed spec** but never looked at the **existing implementation**.

---

## The Missing Adversary

### Adversary Name
`existing-system-compatibility` or `codebase-grounding-auditor`

### Adversary Role
Ground the spec in the actual codebase. Verify that proposed changes are compatible with existing:
- Schema definitions and current data
- Naming conventions and patterns
- Build/deployment state
- Recent changes that may cause drift

### Adversary Persona
> "I don't trust that this spec was written with full knowledge of what actually exists in the codebase. Before we debate the merits of the proposed design, I need to verify that the implementation environment is even ready for these changes. Show me the code."

### Key Questions This Adversary Must Ask

#### 1. Baseline Deployability
- "Does `npx convex dev --once` (or equivalent build command) succeed right now, before any spec changes?"
- "Are there any existing schema validation errors or TypeScript errors?"
- "If the baseline doesn't build, what must be fixed first?"

#### 2. Schema Compatibility
- "What tables already exist in `schema.ts`? Do any proposed table names conflict?"
- "What field naming conventions are used? Does the spec follow them?"
- "Are there existing fields that serve similar purposes to what the spec proposes?"
- "Will adding these tables require migrations for existing data?"

#### 3. Pattern Consistency
- "How do existing similar features handle this? (e.g., if we're adding risk limits, how do existing limits work?)"
- "Are there existing utility functions the spec should reuse instead of creating new ones?"
- "Does the spec's error code format match existing error codes?"

#### 4. Recent Change Awareness
- "What PRs have been merged to schema.ts in the last 30 days?"
- "Are there any pending migrations that haven't been run?"
- "Is there known technical debt or drift that affects this area?"

#### 5. Integration Points
- "What existing code will call the new functions? Does it exist yet?"
- "What existing code will the new functions call? Is it stable?"
- "Are there feature flags or environment variables that affect this area?"

### Tools/Capabilities This Adversary Needs

| Capability | Purpose |
|------------|---------|
| `Read schema.ts` | Understand existing table definitions |
| `Run build command` | Verify baseline deployability |
| `Git log --oneline -20 -- <file>` | See recent changes to relevant files |
| `Grep for patterns` | Find existing conventions and similar code |
| `Read existing similar features` | Understand established patterns |

### Output Format

This adversary should produce concerns in the standard format, but with a new prefix:

**COMP-{hash8}** - Compatibility/Codebase concerns

Example concerns this adversary would have raised for order-execution:

```
COMP-a1b2c3d4: Schema Baseline Not Verified
The spec proposes adding 5 new tables but does not verify that the current
schema deploys cleanly. Pre-existing schema/data drift could block all
implementation work.

Mitigation: Add "Phase 0: Verify `npx convex dev --once` succeeds" to
execution plan.

COMP-e5f6g7h8: matchPairs Table Has Undocumented Drift
Recent PR #170 moved metadata fields to matchPairs_meta but data was not
migrated. 847 documents still have legacy fields. This must be resolved
before any new schema changes can deploy.

Mitigation: Create and run data migration before Phase 1.

COMP-i9j0k1l2: workers Table Schema/Data Mismatch
The workers table schema expects status in ["active", "shutdown", "timeout"]
but production data includes status="dead" from legacy code. 3 documents
affected.

Mitigation: Add "dead" to validator or migrate documents to "timeout".
```

---

## Integration Recommendations

### When This Adversary Should Run

1. **Before other adversaries** - It establishes whether the implementation environment is even ready
2. **With read access to codebase** - Unlike pure spec-review adversaries, this one needs file access
3. **With ability to run commands** - Build verification requires execution

### Interaction With Other Adversaries

This adversary's findings should be available to other adversaries. For example:
- If COMP adversary finds existing risk tracking, BURN adversary can ask "why not extend existing system?"
- If COMP adversary finds build failures, all other concerns are deprioritized until baseline is fixed

### Execution Plan Integration

The execution planner (FR-5) should:
1. Check for any COMP concerns that indicate blocked deployment
2. Generate "Phase 0: Baseline Fix" tasks before any implementation phases
3. Add migration tasks if schema/data drift is detected

---

## Appendix: Actual Schema Drift Found

### matchPairs Table

**Schema expects:**
```typescript
matchPairs: defineTable({
  marketAId: v.id("markets"),
  marketBId: v.id("markets"),
  exchangeA: v.optional(exchangeValidator),
  exchangeB: v.optional(exchangeValidator),
  closeDateA: v.optional(v.number()),
  closeDateB: v.optional(v.number()),
  isActive: v.boolean(),
  matchGroupId: v.optional(v.id("matchGroups")),
  updatedAt: v.number(),
})
```

**Data contains:**
```json
{
  "matchConfidence": 0.93,
  "matchType": "direct",
  "reasoning": "Phase 1 normalization shows...",
  "differencesSummary": "...",
  "differencesAnalyzedAt": 1767844293350
}
```

**Cause:** PR #170 moved these fields to `matchPairs_meta` but didn't migrate data.

### workers Table

**Schema expects:**
```typescript
workers: defineTable({
  exchange: exchangeValidator,
  status: v.union(
    v.literal("active"),
    v.literal("shutdown"),
    v.literal("timeout")
  ),
  maxCapacity: v.number(),
  allocatedCapacity: v.optional(v.number()),
  expiredAt: v.optional(v.number()),
  workerName: v.optional(v.string()),
})
```

**Data contains:**
```json
{
  "canTakeMore": false,
  "currentCount": 100,
  "lastHeartbeat": 1767588829676,
  "status": "dead",
  "updatedAt": 1767588829676,
  "workerId": "polymarket-1767588829676-8b9d6"
}
```

**Cause:** Worker lifecycle refactor changed schema but didn't migrate old worker documents.

---

## Conclusion

The adversarial spec process is valuable but incomplete without an adversary that grounds the review in the actual codebase. The current adversaries are excellent at finding logical flaws, race conditions, and edge cases in proposed designs. But they assume the implementation environment is ready for changes, which is not always true.

Adding a `existing-system-compatibility` adversary would catch issues like:
- Schema/data drift that blocks deployment
- Naming conflicts with existing code
- Missed opportunities to extend existing features
- Required migrations before implementation can begin

This adversary should run first, with codebase access, and its findings should inform all other adversary reviews.
