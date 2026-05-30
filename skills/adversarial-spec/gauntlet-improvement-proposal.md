# Gauntlet Improvement Proposal: Latent-Knowledge Priming

> Authored: 2026-04-20 | Source session: `adv-spec-202604191856-account-balance-display`
> Status: Proposed revision to `~/.claude/skills/adversarial-spec/phases/05-gauntlet.md`

## Problem

The current gauntlet pipeline (phases/05-gauntlet.md) produces 200-500 raw adversarial concerns, which Claude then synthesizes into an accept/acknowledge/dismiss verdict with a proposed fix for each accept. The synthesis pass is authoritative per the phase doc:

> "Pipeline verdicts are advisory, not authoritative. Opus reads ALL concerns — accepted, dismissed, acknowledged, AND deferred."

But the synthesis pass has its own failure mode that is **not documented** in the current phase file: **Claude proposes plausible-sounding fixes that are actually hallucinations when the real fix requires context outside the briefing** (codebase specifics, user domain knowledge, session history in MEMORY.md / do_not_ask, existing patterns Claude hasn't re-read).

### Observed evidence from Account Balance Display gauntlet (2026-04-20)

During the 533-concern synthesis, Claude wrote 64 "accept" verdicts with proposed fixes. After user probing on one specific concern (CB-10, Kalshi identity model), a re-scan with explicit "latent-knowledge lens" turned up **8 findings where the synthesis had proposed a hallucinated or under-verified fix**:

| Finding | Synthesis-proposed fix | Actual fix after retrieval |
|---------|------------------------|----------------------------|
| CB-10 / UN-1 | "Add `Kalshi account` fallback when both email+subaccount absent" | Kalshi identity = API access-key UUID (always present). Found in MEMORY.md do_not_ask. |
| FM-5 | "Trigger refresh off `ordersPlaced`/`ordersCancelled` Convex tables" | Those tables don't exist. Real fix: subscribe to `api.orders.queries.getMyOpenOrders` which already exists and is used by PortfolioOrders. |
| CB-3 | "Use positionsEnrichment.ts for mid-market" | Directionally right, but the file computes per-position value, not sum-by-exchange. Real fix needs the `readCurrentPrice` pattern applied inside a per-exchange loop. |
| OP-1/OP-2 | "Use appendGatewayLog JSONL sink" | Right sink, but the logger has structured `GW_*` families; fix should name a new `GW_BALANCE` family rather than generic JSONL. |
| SEC-5 | "Snapshot identity-only, not full auth" | Correct — but only discoverable after recognizing CB-2 (connectors already hold decrypted auth at startup). The dependency chain between CB-2 and SEC-5 wasn't surfaced until the re-scan. |
| DD-1 | "Use ts-morph differently" | Actual fix: symlink `src/shared/balances-contract.ts` → `gateway/src/connectors/balances-types.ts`. Node resolves symlinks, TS type-only imports don't pull Zod into gateway runtime. Required build-system knowledge. |
| RC-3 | "Keep structuredClone, it narrows the window" | Correct framing, but the sharper claim — `writeGatewayConfig` already uses `temp + rename` atomic replace, so the read-during-write race is already mitigated at the write side — required reading `config.ts`. |
| CB-6/CB-7 | "Keep portfolioValue alongside OR rename" | Still not settled. This one requires user domain judgment about operator expectations for `total`. Flagged for user. |

**Roll-up**: 8 of 64 accepts (12.5%) had Claude-hallucinated or Claude-incomplete fixes that the synthesis step did not flag as low-confidence.

### Why the synthesis step misses this

The existing Step 6b says:

> "Read ALL extracted concerns in one pass. Your additional context:
> - Your own codebase knowledge — architecture docs, blast zone files, implementation state
> - Spec context — what's already addressed, what's intentional, what's out of scope
> - Pipeline verdicts — as advisory signal, not as filter"

It does NOT instruct Claude to:
- Scan MEMORY.md for facts that bear on the concerns (session-specific domain knowledge)
- Read the session `do_not_ask` list (which often contains the exact answers to "what does X mean in this project")
- Verify that proposed fixes reference files/functions/tables that actually exist
- Annotate each verdict with a **confidence level** + **retrieval source**

Claude does some of this opportunistically but not systematically. When there are 500+ concerns, the synthesis naturally pattern-matches to plausible fixes at speed — which is exactly when hallucinations leak through.

## Proposed revision

Insert a new **Step 6a.5: Latent-Knowledge Priming** between concern extraction (6a) and synthesis (6b), and modify Step 6b + 6c to carry retrieval annotations through to the user-facing report.

### Step 6a.5: Latent-Knowledge Priming (NEW — REQUIRED)

Before writing a single verdict, Claude performs a structured retrieval pass:

1. **Read MEMORY.md in full.** Note every feedback / project / reference entry that might bear on the spec's domain. Specifically look for `do_not_ask` / session extended_state facts that answer questions the adversaries raised.

2. **Read the session's `do_not_ask` list.** These are load-bearing facts that were explicitly surfaced during earlier phases. Any adversary concern that overlaps a `do_not_ask` entry has a known answer.

3. **For each of the top-30 concerns by adversary volume** (concerns raised by 3+ adversaries are high-signal):
   - Scan blast-zone code for the files/functions/tables the concern names.
   - Verify whether the concern's premise is accurate against current code.
   - Verify whether Claude has a concrete fix or is pattern-matching.

4. **Produce a `retrieval-notes.md` artifact** with structured entries per theme:
   ```
   ## Theme: Kalshi identity model
   Adversary signals: AUDT-2a9fe8d2, AUDT-96f7404b, ASSH-d27f4a72
   Code verified: grep for /user/me in gateway/src/connectors/kalshi.ts → not present
   MEMORY.md hit: do_not_ask "Kalshi access key identity already surfaced as 3d116f6b-..."
   Retrieved answer: identity = API access-key UUID (always present)
   Confidence: HIGH (memory + code confirm)
   ```
   Entries with no MEMORY hit and no code confirmation are marked `Confidence: LOW — user input required`.

5. **Time budget:** 5-10 min. This is cheaper than the entire Phase 4 eval.

### Step 6b modification: carry confidence through synthesis

Each verdict in the synthesis output includes:
- `confidence: high | medium | low`
- `retrieval_source: memory | code | adversary-proposal | user-needed | pattern-match`

Pattern-match verdicts (no memory hit, no code verified, not in a do_not_ask) are flagged explicitly — the report lists them separately for user review.

### Step 6c modification: "Almost-There Review" subsection

The findings report presented to the user adds a dedicated subsection:

```
## Almost-There Findings (fixes pending retrieval)

These concerns are correctly diagnosed by adversaries, but Claude's
synthesis could not confidently propose a fix from existing context.

| ID | Concern | What I need |
|----|---------|-------------|
| CB-10 | Kalshi identity undefined fallback | Does Kalshi have an accessKeyId we already surface? |
| FM-5 | Order-cancel doesn't trigger refresh | Name the Convex table/query for order status changes |
| DD-1 | ts-morph is a tax | Is there a simpler sharing pattern (shared package, symlink)? |

[User answer each] [Skip - proceed with best-guess] [Defer to implementation]
```

The user answers these BEFORE Step 7 (revise spec). Answers feed back into the synthesis doc as high-confidence verdicts.

### Dispatch hook (optional, Step 4 enhancement)

When arming adversaries, the per-adversary briefing can include a "PROJECT LATENT KNOWLEDGE" section that summarizes the MEMORY.md + do_not_ask facts that might shape their attack. Adversaries STILL raise concerns, but they attack from a baseline that matches what the team has already settled — reducing noise concerns ("what IS Kalshi identity?" becomes "given identity is accessKeyId, does the spec handle key rotation?").

This is a cheaper version of the post-hoc retrieval and complements rather than replaces Step 6a.5.

## Why this is better than status quo

- **Surfaces "Claude doesn't know" explicitly.** Currently that category is invisible — every verdict looks equally confident.
- **Costs ~5 min of synthesis time.** Trivial against the 30-60 min gauntlet runtime.
- **Reuses existing retrieval surfaces.** MEMORY.md and do_not_ask already exist; Step 6a.5 just makes them mandatory inputs to synthesis.
- **User reviews only the unknowns.** Step 6c's current "Proceed to spec revision" button doesn't discriminate high-vs-low confidence verdicts. The revised flow tells the user which 5-10 of 64 need attention.
- **Preserves "one Opus pass" discipline.** The retrieval + synthesis still happen in one coherent judgment act; 6a.5 just adds an explicit pre-read.

## Implementation

Modify `~/.claude/skills/adversarial-spec/phases/05-gauntlet.md`:

1. **Add Step 6a.5** between existing "Step 6a: Extract Concerns with Code" and "Step 6b: Synthesize in One Pass."
2. **Update Step 6b's "Evaluation process"** bullet list:
   - Add: *"Before proposing a fix, classify your confidence (high/medium/low). For each MEDIUM or LOW confidence verdict, either (a) retrieve the answer from MEMORY.md / do_not_ask / code, (b) mark it `user-needed` and surface in the Almost-There subsection, or (c) explicitly dismiss if the uncertainty means the concern itself is speculative."*
3. **Update Step 6c's presentation template** to include the "Almost-There Findings" subsection.
4. **Add to TodoWrite template** at top of 05-gauntlet.md: `{content: "Latent-knowledge priming (MEMORY + do_not_ask + code scan)", status: "pending", activeForm: "Priming latent knowledge for synthesis"}` between "Extract concerns" and "Synthesize findings."
5. **Optionally modify Step 4's Arm Adversaries** to include MEMORY/do_not_ask excerpts in per-adversary briefings.

## Did we do this too late?

**Yes — by one step.** In the Account Balance Display session:
- Step 6a (extract): 533 concerns → compact text file. Correct.
- Step 6b (synthesize): Claude wrote 64 verdicts with proposed fixes. Some hallucinated.
- Step 6c (present): User saw the report, spotted one anomaly (CB-10), and that triggered the whole retrieval + re-scan exercise.
- Step 7 (revise): Would have carried hallucinated fixes into the spec if the user hadn't probed.

The retrieval pass should have happened **between 6a and 6b**, not AFTER the user caught an anomaly in 6c. Everything after 6b is costly to unwind — the report is already written, Claude has committed to verdicts, and the user has to re-read to find the errors. Worse, some hallucinations might not look anomalous enough to probe ("add a fallback for the missing identity" sounds totally reasonable unless you already know what the real identity IS), so they'd slip into the spec uncaught.

So this proposal is **a retrospective correction** applied to the gauntlet skill: next time, 6a.5 runs first, and the report the user sees already separates "high-confidence fix" from "needs your input."

## Meta-note: this proposal itself is subject to the same pattern

I wrote this proposal with latent-knowledge retrieval engaged (I just finished the re-scan). Tomorrow, reviewing it cold, I might propose fixes to this proposal that are ALSO pattern-matched hallucinations. The proposed Step 6a.5 should apply recursively to its own review.
