> **FIRST ACTION upon entering this phase:** Create this TodoWrite immediately.
> Do NOT read further until the TodoWrite is active.
> Every `[GATE]` item must be marked completed before proceeding past it.

```
TodoWrite([
  {content: "Drift gate: diff spec vs target-architecture [GATE]", status: "in_progress", activeForm: "Running spec vs target-architecture drift gate"},
  {content: "SCOUT solo pass: arm + dispatch spec_coroner, triage verdict [GATE]", status: "pending", activeForm: "Running SCOUT solo pass and triaging verdict"},
  {content: "Review adversary leaderboard + versions, select personas and attack models", status: "pending", activeForm: "Reviewing adversary stats and selecting personas"},
  {content: "Present cost estimate to user", status: "pending", activeForm: "Presenting cost estimate"},
  {content: "Arm Adversaries — scope classification + briefings [GATE]", status: "pending", activeForm: "Arming adversaries with scope briefings"},
  {content: "Run gauntlet (respect Gemini rate limits)", status: "pending", activeForm: "Running gauntlet attacks"},
  {content: "Extract concerns with code (jq/Python, NOT LLM)", status: "pending", activeForm: "Extracting concerns with code"},
  {content: "Synthesize concerns — one Opus pass, 8-category taxonomy", status: "pending", activeForm: "Synthesizing gauntlet concerns"},
  {content: "Revise spec with accepted concerns", status: "pending", activeForm: "Revising spec with accepted concerns"},
  {content: "Run CONS guardrail on revised spec [GATE]", status: "pending", activeForm: "Running CONS guardrail on revised spec"},
  {content: "Run conditional CANON/TCOV guardrails on revised spec/tests [GATE]", status: "pending", activeForm: "Running conditional contract and test guardrails"},
  {content: "Display adversary leaderboard + medal standings", status: "pending", activeForm: "Displaying adversary performance results"},
  {content: "Update session state with gauntlet_concerns_path", status: "pending", activeForm: "Updating session state"},
])
```

Mark each step `completed` as you finish it. Mark the current step `in_progress`.

---

### Gauntlet Entry Gate 1 — Spec ↔ Target-Architecture Drift Gate (REQUIRED, deterministic)

**Why this gate exists (incident 2026-07-21, agent-presence-emitters):** spec-v7 was
finalized at debate convergence; Phase 4 then materially revised the architecture
(three real debate rounds reversed the delivery model), and the canonical order defers
the spec rewrite to finalize — AFTER the gauntlet. The fleet was dispatched against a
known-stale spec, and ~60% of 558 concerns were seven adversaries independently
re-deriving the drift we had already decided. Phase 4 is designed as formalization
("introduces no new architecture"); when it behaves like a debate phase instead, the
spec must be reconciled BEFORE the fleet buys attention.

**Mechanics (run before anything else in this phase):**

1. If no `target-architecture.md` exists (skip-mode stub only), the gate passes
   trivially — record that and continue.
2. Compare freshness and cross-references:
   ```bash
   SPEC=$(jq -r '.spec_path' .adversarial-spec/sessions/<id>.json)
   TA=.adversarial-spec/specs/<slug>/target-architecture.md
   # (a) Which is newer?
   [ "$TA" -nt "$SPEC" ] && echo "TA is NEWER than spec"
   # (b) Does the TA demand a spec revision the spec doesn't have?
   grep -niE "must produce spec-v[0-9]+|supersede|removed for the pilot|Required spec-.* Changes" "$TA"
   # (c) Do the TA's revision notes name spec sections that still exist unchanged?
   #     Spot-check each "Required spec Changes" item against the spec text.
   ```
3. **Decision rule:** if the TA is newer than the spec AND contains revision-demand
   language (a "Required spec Changes" section, "must produce spec-vN", superseded
   delivery/auth/locking contracts), the gate FAILS.
4. **On failure — STOP. Do not arm anything.** Present to the operator:
   ```
   Drift Gate FAILED
   ───────────────────────────────────────
   Spec: <spec_path> (vN, mtime ...)
   Target architecture: newer, demands: <quoted revision-demand lines>

   Options:
   [Reconcile first] — produce spec-vN+1 folding the TA deltas, then re-enter the gauntlet
   [Waiver] — proceed anyway; waiver + rationale recorded in decisions.log (the fleet
              WILL spend most of its attention re-deriving the drift)
   ```
   Never proceed silently. A waiver is an operator decision, logged with rationale.

### Gauntlet Entry Gate 2 — SCOUT Solo Pass (REQUIRED, staged dispatch)

After the drift gate passes (or is waived), dispatch ONE scout adversary —
`spec_coroner` (prefix SCOUT, registry `SCOUT_GAUNTLET` in `adversaries.py`) — BEFORE
arming or dispatching the fleet.

**The SCOUT dispatch is a real gauntlet dispatch, not a debate round.** The full-context
debate rounds are already done; what the scout tests is exactly the fleet's condition:
*adversary context only, plus the two artifacts.* It therefore doubles as a dry run of
the briefing itself — if the scout can't tell which document wins, neither can the fleet.

- **Arming:** assemble the SCOUT briefing with the SAME Part A/Part B machinery as any
  fleet adversary (base context, architecture primer, target-architecture in full,
  lookup log, blast-zone files, git activity, known gaps) plus the spec — the identical
  `## ADVERSARY BRIEFING` + `## SPECIFICATION TO REVIEW` document structure. Respect the
  same argv-size guard as fleet briefings.
- **Dispatch:** through the SAME channel as fleet attacks (the Fizzy pipeline gauntlet
  dispatch tools when the session has a card — the pipeline-card fence applies to the
  scout too). Model: **codex, max effort** (e.g., `codex/gpt-5.6-sol` at max/xhigh) —
  the scout is one call; buy the best judgment available.
- **Extraction:** same code-based (jq/Python) concern extraction as the fleet. The scout
  outputs ≤12 ranked concerns in standard format plus a mandatory `VERDICT:` block.
- **Stats:** SCOUT results are tracked under its own prefix; never merged into fleet
  adversary leaderboards.

**Triage (main-context agent decides, informed by — not bound by — the scout's verdict):**

| Outcome | When | Then |
|---------|------|------|
| **Major rewrite / synthesis** | Structural contradiction between artifacts, superseded delivery/auth/locking model, fictional load-bearing components (the 2026-07-21 case) | Produce the reconciled spec revision first; re-run the drift gate; then return here |
| **Minor rewrite** | A few sections stale/self-contradictory, cascade bounded | Patch those sections in place, note in decisions.log, then arm the fleet |
| **Continue with notes** | Faults real but bounded; fleet attention still worth buying now | Fold the scout's findings into every fleet briefing as pre-identified terrain ("do not re-derive; attack past these"), then dispatch |
| **Continue as-is** (rare) | Scout finds nothing structural | Dispatch the fleet |

Record the triage decision + one-line rationale in `sessions/<id>.decisions.log`
(`[gauntlet-scout]` tag). The scout's concerns are carried into the final synthesis
regardless of outcome — they are gauntlet concerns like any other.

**[GATE] TodoWrite: Mark both entry-gate items completed (drift gate + SCOUT triage) before proceeding to Step 5.5.**

---

### Step 5.5: Gauntlet Review (Optional)

After consensus is reached but before finalization, offer the adversarial gauntlet:

> "All models have agreed on the spec. Would you like to run the adversarial gauntlet for additional stress testing? This puts the spec through attack by specialized personas (security, oncall, QA, etc.)."

**If user accepts gauntlet:**

### Permanent ground-truth protocol

The gauntlet has two separate roles:

- **Seats** are read-only reviewers. They inspect the supplied artifacts, file
  concerns and self-contained `GT-REQUEST` records, and must not execute the
  system under review. A seat that needs an observation asks the broker.
- **The neutral broker** collects, de-duplicates, triages, investigates, and
  answers requests. Its records are `GT-REQUEST`, `GT-INVESTIGATION`,
  `GT-RESPONSE`, and `ROUND-TELEMETRY`. The broker is the source of observed
  behavior; a seat's expected answer is not ground truth.

Every request declares its fixture requirements and outcomes. If the required
fixture is unavailable, the broker records `BLOCKED` plus the unblock
requirements. A mocked result is authoritative only for the logic and fixture
it actually exercised; it must not be promoted to a browser, wire, permission,
or credential claim. The response must state its execution scope and claim
ceiling.

The broker returns the full response set to every seat, including seats that
filed no request. An unrequested broker observation is recorded as `BYCATCH`
and is the primary observed value of sharing; a response to another seat's
request is `CROSS_SEAT_RESPONSE` and is a secondary, selective benefit. Future
rounds measure reach, intent yield, noise, follow-up requests, and broker cost
separately. No-request termination, fixture novelty, blocked-question
decomposition, and at least one pre-registered refutation are recorded as
telemetry; a zero-request round alone is not sufficient convergence evidence.

The project may provide a more specific governing document (for example,
`orchestration/governing/BROKER-ROUNDS-v1-DRAFT.md`), but it may not weaken
these evidence-boundary rules.

**Step 0: Size the gauntlet (HUMAN DECIDES, LLM ASKS).**

Before selecting adversaries or models, decide how *big* the gauntlet should be. This is a human call, not an LLM call — Claude does not have enough context about the operator's threat model, deploy surface, or "what's at stake if this ships buggy" to make this decision autonomously. Past sessions have defaulted to the full 9-adversary slate on features that did not warrant it, burning hours of synthesis time on concerns the spec will never need to absorb. **Ask, present options with rough guidance, let the human pick.**

**Variables that shape the right size (surface these to the user):**

- **Blast radius if a bug ships.** Single-operator local tool vs. shared infrastructure vs. real money flow.
- **External-library / SDK surface.** Any `node_modules/<lib>` the spec builds on top of is an adversary-proof channel for hallucinated field names and misread semantics — the gauntlet's AUDT persona flags *that a claim is unverified* but cannot actually verify it. See the mandatory SDK pass below.
- **Network exposure and trust boundary.** 127.0.0.1-only tool that only the operator's own browser hits → PARA is usually noise. Public HTTP endpoint or untrusted input → PARA becomes mandatory.
- **Concurrency surface.** Flighting, coalescing, retry, burst, or cross-tab state → BURN/FLOW/TRAF start earning their keep.
- **How well the existing architecture is documented.** Stale or missing `.architecture/` docs inflate the value of ARCH + FLOW + AUDT; good docs shrink it.
- **Reversibility.** Feature you can hotfix in an hour vs. a schema migration in prod.

**Canned starting points (examples, NOT a hard rule — every app is different):**

| Shape | Typical adversary set | Rough rationale |
|-------|-----------------------|-----------------|
| Solo local feature, no money, SDKs touched | `assumption_auditor,architect` + SDK pass | AUDT + ARCH catch code drift and structural issues; PARA/BURN are usually noise at this scale. Mandatory SDK pass covers the external-library blind spot. |
| Touches shared infrastructure or long-lived contracts | `assumption_auditor,architect,paranoid_security,burned_oncall` | Add PARA once trust boundaries appear; add BURN once ops visibility and failure-mode cost rises. |
| Real money flow, concurrency, or hot path | Full slate (all 9) | Every persona earns its keep on money-flow code. |
| Already-in-production incident follow-up | Full slate + FINAL-BOSS | Everything plus holistic UX review; stakes are already proven. |

**The LLM's job in this step:** present the variables above, suggest a starting point based on what the spec declares about scope (blast radius, file scope, SDK imports, deploy target), and **ask the human to confirm, expand, or shrink**. Do NOT auto-select. Do NOT default to "all" just because picking is hard. If the user wants to think about it, wait — the cost of spending 5 extra minutes on adversary selection is far smaller than the cost of a 6-hour synthesis on concerns that don't belong in the spec.

**Mandatory regardless of size — post-gauntlet SDK verification pass.** For every external library, SDK, or `.d.ts` the spec references, a human-initiated read of the actual type definitions / documentation MUST happen before the gauntlet's synthesized concerns are promoted into spec text. The gauntlet can only flag SDK assumptions as "unverified"; it cannot check them. Past sessions have accepted adversary-hallucinated field names (`/user/me`, `reserved_amount`, wrong Σ formulas) into a spec because the gauntlet flagged them as risky but no one actually read the SDK. This step is ~10 minutes of manual reading per library and catches the class of bug the gauntlet structurally cannot.
Use Docmaster if the SDK is covered in docmaster. Ask the user to add in any docs that are not covered if there is a gap. This is a one-time addition that is blocking.
After sizing is agreed, proceed to step 1 below.

---

1. Review adversary versions and performance before selecting:
   ```bash
   # Show version history of adversary personas
   python3 ~/.claude/skills/adversarial-spec/scripts/debate.py adversary-versions

   # Show performance leaderboard from all previous gauntlet runs
   python3 ~/.claude/skills/adversarial-spec/scripts/debate.py adversary-stats

   # List available adversary personas
   python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet-adversaries
   ```

   Use the leaderboard to inform adversary selection — high signal-score adversaries find more valuable concerns. Consider dropping consistently low-performing adversaries to save quota.

   **Gauntlet Adversary Quick Reference (exact CLI names):**

   | Prefix | CLI Name | Role |
   |--------|----------|------|
   | PARA | `paranoid_security` | Security threats |
   | BURN | `burned_oncall` | Operational failure modes + recovery |
   | MINI | `minimalist` | Unnecessary complexity + prior art (merged LAZY+PREV) |
   | PEDA | `pedantic_nitpicker` | Data-level correctness (types, encoding, boundaries) |
   | ASSH | `asshole_loner` | Design-level correctness (abstractions, contracts) |
   | AUDT | `assumption_auditor` | Unverified assumptions |
   | FLOW | `information_flow_auditor` | Architecture flow gaps |
   | ARCH | `architect` | Code structure, data flow, component boundaries |
   | TRAF | `traffic_engineer` | Scalability, throughput, concurrency limits |

   **Not available via `--gauntlet-adversaries`:**

   | Prefix | CLI Name | Role | How to invoke |
   |--------|----------|------|---------------|
   | COMP | `existing_system_compatibility` | Codebase compatibility | Pre-gauntlet only (Step 4) |
   | SCOUT | `spec_coroner` | Artifact-pair fitness triage | Entry Gate 2 only (solo, before the fleet — never in fleet selections) |
   | UXAR | `ux_architect` | User story coherence | Final boss only (Step 8) |

   **Legacy aliases:** `lazy_developer` → `minimalist`, `prior_art_scout` → `minimalist`

   **NEVER invent adversary names.** If `gauntlet-adversaries` crashes, read its output carefully — it prints valid names before any traceback. Use those exact names.

2. **Select gauntlet attack models.** Present available models using AskUserQuestion with multiSelect:

   ```
   question: "Which models should run adversary attacks? (cheap/free models recommended — they find holes, frontier model evaluates)"
   header: "Attack models"
   multiSelect: true
   options: [build from available providers, prioritize free/cheap models]
   ```

   **Recommended lineup (if available):**
   - `codex/gpt-5.6-luna` — GPT-5.6 Luna via Codex CLI (free, xhigh effort)
   - `antigravity/gemini-3.7-flash-high` — Gemini 3.7 Flash High via Antigravity (the standalone Gemini CLI is RETIRED — `gemini-cli/...` model strings fail in `_doSetupUser`; observed 2026-08-27)
   - `claude-cli/claude-sonnet-4-6` — Claude Sonnet 4.6 (free via CLI)

   These become `--gauntlet-attack-models` (comma-separated). The frontier evaluation model is selected automatically.

3. **Understand the cost model BEFORE launching.**

   The gauntlet pipeline makes many LLM calls. Know the math before choosing flags:

   ```
   Phase 1 (attacks):     N adversaries × M attack models = N×M calls
   Phase 2 (synthesis):   1 call (first eval model)
   Phase 3 (filtering):   1 call (cheap model)
   Phase 3.5 (clustering): 1 call (cheap model, deterministic Jaccard)
   Phase 4 (evaluation):  depends on --eval-tier-strategy (see below)
                           EACH batch re-sends the full spec — that re-send
                           is ~85% of input cost, NOT the per-concern text
   ```

   **Example (real numbers from a username spec gauntlet):**
   8 adversaries × 2 attack models = 16 Phase 1 calls → 331 raw concerns.
   After filtering/dedup: ~300 concerns remain.
   Phase 4 (default tiering): roughly 9 + 11 + 9 = ~29 batches × 2 eval models = **~58 eval calls**.
   Total: 16 + 2 + 1 + 58 = **~77 calls**, each with ~11K token spec as input.
   (For comparison: the historical flat-15 strategy would have produced
   `ceil(300/15) = 20 batches × 2 eval models = 40 calls`. Tiering trades a
   few extra calls for substantially better attention quality on the gnarly
   ~10% of concerns — the trade is worth it; see below.)

   **Phase 1 is where external models add value** (diverse perspectives finding different issues).
   **Phase 4 is where cost dominates** — and it's advisory, because YOU (Claude) are the final
   evaluator when synthesizing results into spec changes.

   **Reasoning levels are now split** — attacks and evaluations have independent controls:
   - `--codex-reasoning low` (default) — controls attack reasoning effort
   - `--eval-codex-reasoning xhigh` (default) — controls evaluation/adjudication reasoning effort

   **Phase 4 batching strategy (`--eval-tier-strategy`):**

   | Strategy | When to use | Behavior |
   |----------|-------------|----------|
   | `power_law_length` (DEFAULT) | Always — this is the right answer for ≥30 concerns | Tiers concerns into easy/med/hard by text length (cuts at p60/p90, batch sizes 75/30/12). Long structural concerns (typically ARCH/FLOW prose with multi-section refs) get isolated 12-at-a-time attention; easy concerns batch 75-at-a-time to amortize the spec re-send. Auto-falls-back to flat when N < `--eval-tier-min-concerns` (default 30) since tiering 12 concerns into 75/30/12-sized batches is identical to one flat batch. |
   | `flat` | A/B comparison runs; known-good fallback when tiering grades poorly on a specific run | Single fixed batch size (`--eval-flat-batch-size`, default 15). Historical behavior; use only when you specifically want it. |

   **Why power-law is the default:** the spec re-send is a fixed cost per call.
   At batch=15 you re-send the spec 20× for 300 concerns; at batch=75 you re-send
   it 4×. But cranking the flat size to 75 makes the gnarly ~10% of concerns
   (long FLOW/ARCH prose) get diluted in a 75-mixed batch and grade sloppily.
   Tiering breaks the trade-off: easy concerns ride the big batch, hard ones get
   a 12-batch with full attention. Lower call count *and* better verdicts on
   the highest-stakes items.

   **When to override to `flat`:**
   - Side-by-side comparison of strategies for a post-mortem.
   - Specific run where tiering grades poorly (rare; if it happens, capture
     the run and tune the percentile cuts or tier batch sizes).
   - Spec shape that doesn't match the tier defaults (e.g. ≤30 concerns —
     though the auto-fallback handles this for you).

   **Tunables (rarely needed):**
   - `--eval-flat-batch-size N` — flat batch size (default 15).
   - `--eval-tier-min-concerns N` — fallback threshold (default 30).

   **Additional flags:**
   - `--gauntlet-resume` — resume from checkpoint (reuse Phase 1 concerns, skip re-eval)
   - `--unattended` — no stdin prompts + auto-checkpoint after expensive phases

   **Reasoning level guidance:**

   | Level | When to use | Trade-off |
   |-------|------------|-----------|
   | `low` (attack default) | Adversary attacks — system prompts do the heavy lifting | Fast, good enough for concern generation |
   | `medium` | Balanced option for either attack or eval | 2× attack cost, decent eval quality |
   | `xhigh` (eval default) | Evaluation/adjudication — verdict quality matters | Expensive but accurate verdicts |

   **Always use defaults** (`--codex-reasoning low --eval-codex-reasoning xhigh`) unless the user explicitly requests otherwise.

   Present the cost estimate before launching:
   ```
   Gauntlet Cost Estimate
   ═══════════════════════════════════════
   Adversaries: 8 × 2 attack models = 16 Phase 1 calls
   Estimated concerns: ~200-400 (typical for detailed specs)
   Phase 4 eval: ~20-30 batches × 2 eval models = 40-60 calls
   Total calls: ~60-80
   Reasoning: medium (recommended)

   [Launch] [Adjust reasoning] [Reduce adversaries]
   ```

4. **Arm Adversaries** (REQUIRED before running gauntlet). See below.

**[GATE] TodoWrite: Mark "Arm Adversaries — scope classification + briefings" completed before proceeding to Step 5.**

5. Run the gauntlet with armed briefings.

   **Gemini Rate Limit Staggering (REQUIRED):**
   When using Gemini CLI models as attack models, do NOT launch all adversaries simultaneously. Gemini's free tier has a **4 requests per minute** rate limit that causes 429 errors and returns 0 structured concerns if exceeded.

   - **Max 4 Gemini calls per 60-second window**
   - Launch up to 4 adversaries at once, wait 61s, then launch the next batch
   - All batches run in background — do NOT block-wait for Batch 1 to finish before launching Batch 2
   - After launching each batch, do a quick `TaskOutput(block=false)` check at ~45s to catch quota errors early
   - Collect all results AFTER all batches are launched

   **Example launch order** (9 adversaries, Gemini attack model):
   ```
   Batch 1: PARA, BURN, MINI, PEDA (launch together)
   sleep 61s
   Batch 2: ASSH, AUDT, FLOW, ARCH (launch together)
   sleep 61s
   Batch 3: TRAF (launch)
   Collect all 9 results
   ```

6. **Post-Gauntlet Synthesis (REQUIRED — this is where real evaluation happens).**

   The pipeline's automated evaluation (Phases 2-4) is a useful first pass, but **Claude is the
   final evaluator**. The pipeline generates concerns; Claude judges them. This is intentional —
   Claude has full codebase context, spec history, and architectural understanding that the
   pipeline's eval models do not.

   **Cardinal rules** (from [process failure report](process-failure-gauntlet-synthesis-v1-vs-v2.md)):
   1. **Never use LLM subagents for JSON extraction.** Use `jq` or Python. LLMs add latency, lossy compression, arithmetic errors, and hallucination risk to a task that is pure data extraction.
   2. **Never pre-filter by pipeline verdicts.** Opus reads ALL concerns — accepted, dismissed, acknowledged, AND deferred. Pipeline verdicts are advisory, not authoritative. "Deferred" ≠ "not important."
   3. **Always use the 8-category taxonomy.** No ad-hoc theming. Categories: Correctness Bugs, Race Conditions, Failure Modes, Security, Operability, Scalability, Design Debt, Underspecification.
   4. **One Opus pass, not N subagent passes.** Synthesis is one coherent act of judgment. Splitting it across agents fragments the reasoning and drops concerns.

   **Step 6a: Extract Concerns with Code**

   Extract all concerns from gauntlet output into a single compact file using code (NOT LLM subagents):

   ```python
   # Extract from evaluations JSON — adapt path from manifest.gauntlet.checkpoint_files.evaluations
   import json
   evals = json.load(open(".adversarial-spec-gauntlet/evaluations-HASH.json"))
   for e in evals:
       c = e["concern"]
       print(f'[{c["id"]}] ({c["severity"]}) {c["adversary"]} | verdict={e["verdict"]}')
       print(f'  {c["text"][:200]}')
       print()
   ```

   Or use `jq`:
   ```bash
   jq -r '.[] | "[" + .concern.id + "] (" + .concern.severity + ") " + .concern.adversary + " | verdict=" + .verdict + "\n  " + (.concern.text[:200])' evaluations-*.json
   ```

   **Also check for parse failures:** Look for any adversary×model combinations with 0 concerns in the gauntlet output. If any exist, read the raw responses file (`.adversarial-spec-gauntlet/raw-responses-*.json`) directly. Common parse failure: Gemini outputs `### N. Title` headers instead of `N.` at line start.

   The goal: ONE file or context block containing ALL concerns (typically 10-15K tokens for ~200 concerns). This is your synthesis input.

   **Step 6b: Synthesize in One Pass**

   Read ALL extracted concerns in one pass. Your additional context:
   - Your own codebase knowledge — architecture docs, blast zone files, implementation state
   - Spec context — what's already addressed, what's intentional, what's out of scope
   - Pipeline verdicts — as advisory signal, not as filter

   **Evaluation process:**
   - Read every concern. Do not skip deferred or dismissed concerns — the pipeline may be wrong.
   - Classify each unique concern into one of the 8 standard categories:
     **Correctness Bugs** | **Race Conditions** | **Failure Modes** | **Security** | **Operability** | **Scalability** | **Design Debt** | **Underspecification**
   - For each concern, verdict:
     - **Accept** — spec needs revision. Note what changes.
     - **Acknowledge** — valid point, won't address (out of scope, known tradeoff). Credit the adversary.
     - **Dismiss** — not valid. One sentence why.
   - Deduplicate by theme within categories, not by source adversary.

   **Step 6c: Present Concerns**

   Present a consolidated concern report using the standard taxonomy:
   ```
   Gauntlet Concerns
   ═══════════════════════════════════════
   Total concerns evaluated: N (all verdicts, not just accepted)
   After dedup: X unique concerns

   CORRECTNESS BUGS
     CB-1: [one-line summary] — Accept (sources: PEDA×Gemini, ASSH×GPT)
     CB-2: [one-line summary] — Acknowledge (known tradeoff: ...)

   RACE CONDITIONS
     RC-1: ...

   SECURITY
     SEC-1: ...

   [... remaining categories with concerns ...]

   Summary: A accepted | K acknowledged | D dismissed
   [Proceed to spec revision] [Discuss specific concerns]
   ```

   Categories with zero concerns may be omitted.

7. **Revise spec with accepted concerns.**
   - Add mitigations for accepted concerns
   - Update relevant sections (don't summarize or reduce existing content)
   - **Morph gate-in (REQUIRED — `reference/morph-reconciliation.md`).** Any accepted concern
     whose fix **deletes, relocates, externalizes, absorbs, splits, or reframes** a named
     capability can morph a user story — moving its center of gravity while leaving its spine
     test, scope statement, and coverage-map row pointing at the old (now-deleted) behavior. A
     plain grep for the deleted identifier will NOT catch this (the orphaned spine names the
     behavior, not the dead symbol). Run the morph-reconciliation procedure (migration ledger →
     fate classification → artifact reconcile → lineage record → `orphaned_spine` verify) for
     each such fix before saving the revision. *(Canonical incident: `DR-5` deleted
     `TestInputCollector` and orphaned US-7's spine `TC-7.0`.)*
   - Save the full concern report as `gauntlet-concerns-YYYY-MM-DD.json`
   - **Run checkpoint guardrails after incorporating the batch of fixes.** CONS is always required because gauntlet fix incorporation can introduce cross-section contradictions. Run CANON if any accepted concern changes named types/enums, formulas, parameter causality, payload meanings, UI/display claims, or active-vs-legacy classifications. Run TCOV if any accepted concern adds, removes, weakens, or relies on tests-pseudo/tests-spec. SCOPE and TRACE are not normally needed here because gauntlet fixes are evaluated by Claude, not automated scope additions; run them only if a fix expands user-visible scope or changes requirement coverage.
   - If CONS finds issues, fix and re-run (max 2 attempts, then defer to user)
   - If TCOV finds weak or missing oracles, strengthen tests before finalize or explicitly defer the uncovered semantic claim with user approval
   - If significant changes were made, consider running another debate round

**[GATE] TodoWrite: Mark "Run CONS guardrail on revised spec" and "Run conditional CANON/TCOV guardrails on revised spec/tests" completed before proceeding to Step 8 or phase transition. If CANON/TCOV are not applicable, mark the conditional item completed with a note explaining why.**

8. **Display adversary leaderboard and medal standings** (REQUIRED after every gauntlet run).

   ```bash
   # Updated leaderboard with this run's results
   python3 ~/.claude/skills/adversarial-spec/scripts/debate.py adversary-stats

   # Medal awards (runs with 6+ adversaries)
   python3 ~/.claude/skills/adversarial-spec/scripts/debate.py medal-leaderboard
   ```

   Present the leaderboard to the user. Note any adversaries whose signal score dropped below -0.1 — recommend tuning or replacing them. Note any adversaries that earned gold medals — their unique catches justify their continued inclusion.

9. Optionally run Final Boss (UX Architect review — expensive but thorough)

**If user declines gauntlet:**
- Proceed directly to finalize phase

---

### Arm Adversaries (before gauntlet attack generation)

Adversaries produce higher-quality findings when they have codebase context AND scope-aware prompts, not just the spec text. This step has two parts: (A) classify scope and generate dynamic prompts, and (B) assemble per-adversary briefing documents.

**Part A0: Size the roster from `session_altitude` (reference/altitude.md §6/§6.1)**

Read `session_altitude` off the session card BEFORE arming. The pipeline enforces
`ALTITUDE_GAUNTLET_INTENSITY[alt]` at `pipeline_mark_gauntlet_complete` from the
run manifest — an under-sized run is rejected AFTER the adversaries have already
run (fail-closed, full cost wasted):

| session_altitude | min adversaries | min distinct families | min foci | tier (advisory) |
|---|---|---|---|---|
| component | 1 | 1 | 1 | fast |
| subsystem | 2 | 2 | 2 | frontier |
| system | 2 | 2 | 3 | frontier |

Adversary = distinct attacker model; family diversity is registry-checked
(claimed families must match `agents.validate_debate_model(model).family` — the
manifest cannot forge diversity). `tier` guides model choice only: `fast` legal
for component (`gemini-3-flash`); `frontier` advised above (`gemini-3.6-flash-high`,
`codex/gpt-5.6-sol max`). `None` altitude (grandfathered) ⇒ legacy behavior, no
intensity gate.

**Part A: Scope Classification + Dynamic Prompt Generation**

Before assembling briefings, classify the spec's scope and generate scope-aware prompts:

1. **Classify scope** using `VALID_SCOPE_KEYS` from `adversaries.py`:
   ```
   Scope Classification
   ═══════════════════════════════════════
   exposure: public-internet
   domain: user-facing-api
   risk_signals: auth, payments
   stack: python, fastapi
   ```

2. **For each adversary in `ADVERSARY_TEMPLATES`**, generate a dynamic prompt:
   - Start with the template's fixed `tone`
   - Select relevant `scope_guidelines` based on scope classification
   - Generate 2-4 sentences of spec-specific focus
   - Assemble into full persona string

3. **Present all generated prompts to user for review** (see spec §1.4 for format)

4. **User approves / edits / skips individual adversaries**

5. **Write approved prompts** to `.adversarial-spec-gauntlet/approved-prompts.json` with `spec_hash` (generated via `sha256sum <spec-file> | cut -c1-12`)

6. **Skipping adversaries by scope** — some adversaries become irrelevant for certain scopes (e.g., PARA for local-only CLI tools). Skipping is always a user decision, not automatic. Claude recommends skips with reasoning; user confirms.

If `ADVERSARY_TEMPLATES` is empty (templates not yet populated), fall back to static personas from `ADVERSARIES` dict. Note this to the user: "Dynamic prompts not available — using static personas."

**Part B: Context Briefing Assembly**

Assemble per-adversary briefing documents from the Context Readiness Audit inventory (built during debate — see 03-debate.md) and report token overhead.

**Process:**

#### 1. Check for Context Inventory

The Context Readiness Audit (between debate Round 1 and Round 2) should have produced a `ContextInventoryV1` in session state.

- **If inventory exists:** Check staleness — compare `git_hash` in inventory to current `git rev-parse --short HEAD`. If HEAD changed, re-extract only modified blast zone artifacts.
- **If inventory is missing** (audit was skipped or session is new): Run a lightweight version now — check architecture docs, blast zone files, and git state. Skip the full checklist but get enough for base context.

#### 2. Assemble Base Context (all adversaries)

Every adversary gets a feature briefing (~800 tokens):

- **Architecture primer** — include `.architecture/primer.md` in full when present. If no architecture docs exist, note this as a gap.
- **Architecture excerpt** — relevant subsection of `.architecture/overview.md` (NOT the whole file) when the adversary needs deeper system narrative.
- **Target Architecture** — if `.adversarial-spec/specs/<slug>/target-architecture.md` exists (from Phase 4), include it in full. This is the primary architecture context for ALL adversaries. The briefing must explicitly surface:
  - framework profile + execution surface map from `04-target-architecture.md`
  - concern + triggered-concern decisions and the concern x surface matrix from `04-target-architecture.md` §6 (normative source)
  - invariant set from `04-target-architecture.md` §8 (normative source)
  If missing (Phase 4 skipped or legacy session), note: "No target architecture available — architecture-level concerns may be underrepresented."
- **Lookup log** — include `.adversarial-spec/specs/<slug>/lookup-log.md` when
  present (resolved-by-lookup register from the debate rounds) so adversaries
  do not re-attack already-answered assumptions; any UNRESOLVED entries are
  explicitly flagged as fair-game attack surface.
- **Files in blast zone** — file paths with one-line descriptions of what each does
- **Recent git activity** — last 5 commits touching blast zone files

**Context truncation:** If combined spec + roadmap + target architecture exceeds 80% of the target model's context window, summarize the architecture document before feeding to gauntlet. Preserve all Decision/Rationale sections; truncate Implementation sketches.

#### 3. Assemble Per-Adversary Supplements

Each adversary has a specific lens. Give them ammunition for that lens:

**Phase 4 concern-routing rule:** `04-target-architecture.md` §6 is the normative source for concern definitions, triggered concerns, and the concern x surface matrix. `04-target-architecture.md` §8 is the normative source for invariants. Use those sections to route emphasis by adversary:

| Adversary | Phase 4 concern emphasis |
|-----------|--------------------------|
| **PARA** | Enforcement, auth, security, and trust-boundary concerns from §6 |
| **BURN** | Observability and realtime concerns from §6, plus the invariants in §8 that protect recovery and delivery semantics |
| **LAZY** (legacy alias now routed to **MINI**) | Enforcement-bypass opportunities from the §6 concern x surface matrix; use §8 invariants to show where shortcuts would violate the architecture |
| **COMP** | Source-of-truth and brownfield compatibility concerns from §6, cross-checked against §8 invariants guarding existing-system behavior |

| Adversary | Supplement | Budget |
|-----------|-----------|--------|
| **PARA** (paranoid_security) | Auth/authz patterns in blast zone, input validation boundaries, dependency audit results, API surface area | ~350 tok |
| **BURN** (burned_oncall) | External dependency list with timeout configs, existing error handling patterns (retry, circuit breaker), monitoring status or explicit "none exists" note | ~280 tok |
| **MINI** (minimalist) | Installed SDK capabilities, platform features already available, existing utility functions, framework builtins, prior art search results | ~500 tok |
| **PEDA** (pedantic_nitpicker) | Type definitions, enum values, schema constraints (nullable, unique, defaults), validation rules, test coverage report if available | ~380 tok |
| **ASSH** (asshole_loner) | Design rationale / ADRs, known tech debt markers (TODO/FIXME/HACK in blast zone), broader architecture context beyond excerpt | ~200 tok |
| **COMP** (existing_system) | Full build/test status, current vs proposed schema diff, naming conventions in area, pending migrations, duplicate file analysis (pre-gauntlet only) | ~1,100 tok |
| **AUDT** (assumption_auditor) | External API doc excerpts, SDK type definitions, existing integration code showing how external systems actually behave | ~300 tok |
| **FLOW** (info_flow_auditor) | FULL architecture overview (not just excerpt), data flow docs from `.architecture/structured/flows.md`, external API capabilities (REST/WS/webhook), existing latency data if available | ~900 tok |
| **ARCH** (architect) | FULL target architecture doc (not just excerpt), component docs from `.architecture/structured/components/`, existing shared patterns/utilities inventory, first-feature propagation analysis | ~1,000 tok |
| **TRAF** (traffic_engineer) | Expected traffic patterns, concurrency limits, queue/pool configs, existing rate limiter settings, load test results if available | ~400 tok |

**Test pseudocode supplement (when `tests_pseudo_path` exists in session):**

| Adversary | Gets test pseudocode? | Why |
|-----------|----------------------|-----|
| **PEDA** | YES — full `tests-pseudo.md` | Schema constraint validation, assertion completeness |
| **COMP** | YES — full `tests-pseudo.md` | Coverage analysis, integration test gaps |
| **BURN** | YES — full `tests-pseudo.md` | Boundary/error case identification, timeout/retry gaps |
| **PARA** | Relevant sections only | Auth-related test cases |
| Others | NO | Not their lens |

New test cases identified by adversaries get **appended** to `tests-pseudo.md` with adversary attribution: `Source: BURN-<concern-hash>`.

#### 4. Apply Relevance Filter

Not every adversary needs every supplement for every spec:

- Spec adds an API endpoint? → PARA gets auth patterns, FLOW gets data flow
- Spec changes a data model? → PEDA gets constraints, COMP gets schema diff (pre-gauntlet)
- Spec integrates external service? → AUDT gets API docs, MINI gets existing integrations
- Spec is internal refactor? → MINI gets utility inventory, ASSH gets design rationale
- Spec expects high traffic? → TRAF gets load patterns, BURN gets timeout configs
- Spec has test pseudocode? → PEDA/COMP/BURN get `tests-pseudo.md`, others get nothing
- If a supplement source was `NOT_AVAILABLE` or `NOT_APPLICABLE` in the audit, skip it and include a one-line note in the "Known Gaps" section of the briefing

#### 5. Format Briefings

Each adversary's context is prepended to the spec in a structured block:

```markdown
## ADVERSARY BRIEFING: [adversary_name]

> This briefing contains codebase context extracted for your review.
> Use it to validate the spec's claims against what actually exists.
> Extraction: 2026-02-09T15:00:00Z | Git: e94ebfe | Branch: main

### Base Context
[architecture excerpt, blast zone files, git activity]

### Your Specific Context
[per-adversary supplement — tailored to this adversary's lens]

### Known Gaps
[anything we couldn't provide and why]
- No monitoring data — this is a CLI tool, no production metrics exist
- Test coverage report not generated — tests exist but no pytest-cov configured

### How to word every concern

Avoid intention-assuming language — phrasing that assigns a hostile actor or
their goal. Describe where data comes from and where it goes in this system. For
provenance: "unexpected external input," "an origin that arrives from outside the
trusted list," "a value the operator did not configure." For reachability:
reaches, is copied into, is retained by, is constructed with, returns, is not
evaluated, is accepted without checking.

This is framing, not softening — keep the violated obligation, the oracle, and
the mechanism exactly as sharp as they are.

---

## SPECIFICATION TO REVIEW

[spec text]
```

**Why the wording rule is in the briefing** (incident 2026-07-31, fizzy-pipeline-mcp):
concern records are fragments — dense noun phrases with no surrounding sentences
establishing that this is test planning for the operator's own system. Surface
features carry all the weight, so a few intention-assuming lines sitting next to
each other are enough on their own for a model asked to author or process them to
decline. Note this applies to any doc *teaching* the rule as well — state the
positive form, do not list disfavored phrasings in a column. Process vocabulary
(gauntlet, adversary, attack) is unaffected; this governs the text inside the
concern fields.

#### 6. Report Token Counts

Present the token overhead before proceeding:

```
Adversary Briefings — Token Report
═══════════════════════════════════════

                          Base   Spec   Supplement   TOTAL
Adversary
──────────────────────────────────────────────────────────
PARA  paranoid_security    800   1,400     350       2,550
BURN  burned_oncall        800   1,400     280       2,480
MINI  minimalist           800   1,400     500       2,700
PEDA  pedantic_nitpicker   800   1,400     380       2,580
ASSH  asshole_loner        800   1,400     200       2,400
AUDT  assumption_auditor   800   1,400     300       2,500
FLOW  info_flow_auditor    800   1,400     900       3,100
ARCH  architect            800   1,400   1,000       3,200
TRAF  traffic_engineer     800   1,400     400       2,600
──────────────────────────────────────────────────────────
TOTALS                   7,200  12,600   4,580      24,380
Previous (spec only):                               12,600
Increase:                                          +11,780  (+93%)

Cost at current adversary model (gemini-3-flash): +$0.0009
```

Token estimation: `len(text) // 4` (approximate, for reporting only).

Store the bundle in session state as `BriefingBundleV1`:
```json
{
  "schema_version": "1.0",
  "generated_at": "ISO-8601",
  "git_hash": "short hash",
  "adversaries": {
    "adversary_name": {
      "base_tokens": 800,
      "supplement_tokens": 350,
      "spec_tokens": 1400,
      "total_tokens": 2550,
      "gaps": ["description of what was missing"]
    }
  }
}
```

#### 7. Run Gauntlet with Briefings

Instead of piping raw spec to all adversaries, pass each adversary its assembled briefing:

```bash
# Each adversary gets its own briefing document via the debate.py gauntlet command
# The briefings are assembled above and passed as the spec input
# If generate_attacks() accepts a briefings dict, use it; otherwise pipe per-adversary
cat briefing-PARA.md | python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet \
  --gauntlet-adversaries paranoid_security
```

In practice, Claude assembles the briefings in memory and passes them to the gauntlet. The `generate_attacks()` function accepts an optional `briefings: dict[str, str]` parameter — if provided, each adversary gets its specific briefing instead of raw spec. If not provided, falls back to spec-only (backward compatible).

**UX_ARCHITECT (Final Boss) is NOT armed here.** The final boss runs AFTER the gauntlet phases and receives the full concern summary. Its context is the gauntlet output itself.

#### 7.5 Write the run-manifest intensity fields (REQUIRED for v4+ altitude sessions)

`pipeline_mark_gauntlet_complete` reads these off the run manifest (additive to
`spec_hash`) and rejects the gauntlet without them — see reference/altitude.md §6.1:

```jsonc
{
  "spec_hash": "<sha256-12>",
  "session_altitude": "system",                       // echo of the card value
  "adversaries": [                                     // one entry per attacker MODEL
    {"model": "gemini-3.6-flash-high", "family": "gemini"},  // family must match the registry
    {"model": "gpt-5.6-luna",  "family": "codex"}
  ],
  "foci": ["auth", "storage", "rollout"]              // distinct attack foci covered
}
```

- `foci` unit today = distinct system-spec sections attacked. On a re-gauntlet
  after `load_plan` with `concern_refs_schema_version: 2`, every tree node ≤
  session altitude must appear (manifest focus or concern `node_id`).
- Reject codes: `GAUNTLET_INTENSITY_UNMET` (short dimension named),
  `GAUNTLET_ADVERSARY_FAMILY_MISMATCH` / `MODEL_REGISTRY_UNKNOWN` (anti-lying),
  `GAUNTLET_ARTIFACTS_INCOMPLETE` (fields missing on a v4+ altitude session).

#### Token Budget Guidelines

| Component | Budget | Rationale |
|-----------|--------|-----------|
| Base context (per adversary) | 600–1,000 tok | Architecture excerpt + blast zone + git. Orientation, not drowning. |
| Per-adversary supplement | 200–1,200 tok | COMP/FLOW need more (audit structure). ASSH needs less (attacks logic). |
| Total per adversary | 800–2,200 tok added | Never more than 2x the spec size in added context. |
| Test pseudocode (per adversary) | 150–400 tok | PEDA/COMP get full; BURN gets boundary tests only; others skip. |
| Total across all adversaries | < 100% increase | Doubling total input is the upper bound. |

**If budget is exceeded:**
1. Trim base context — shorter architecture excerpt
2. Drop supplements for adversaries where spec doesn't touch their domain
3. Truncate large artifacts with `... N more items`

---

### Phase Transition: gauntlet → finalize

After gauntlet concerns are integrated into the spec, sync both session files per the Phase Transition Protocol (SKILL.md):

1. **Detail file** (`sessions/<id>.json`):
   - Set `current_phase: "finalize"`, `current_step: "Gauntlet complete, spec updated with accepted concerns"`
   - Set `gauntlet_concerns_path` to the saved concerns JSON (e.g., `".adversarial-spec/gauntlet-concerns-2026-02-10.json"`)
   - Append to journey log (`sessions/<id>.journey.log`, JSONL): `{"time": "ISO8601", "event": "Gauntlet complete, N concerns accepted", "type": "transition"}`
2. **Pointer file** (`session-state.json`): set `current_phase: "finalize"`, `current_step`, `next_action`, `updated_at`
