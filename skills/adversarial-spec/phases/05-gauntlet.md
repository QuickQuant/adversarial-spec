> **FIRST ACTION upon entering this phase:** Create this TodoWrite immediately.
> Do NOT read further until the TodoWrite is active.
> Every `[GATE]` item must be marked completed before proceeding past it.

```
TodoWrite([
  {content: "Review adversary leaderboard + versions, select personas and attack models", status: "in_progress", activeForm: "Reviewing adversary stats and selecting personas"},
  {content: "Present cost estimate to user", status: "pending", activeForm: "Presenting cost estimate"},
  {content: "Arm Adversaries — scope classification + briefings [GATE]", status: "pending", activeForm: "Arming adversaries with scope briefings"},
  {content: "Run gauntlet (respect Gemini rate limits)", status: "pending", activeForm: "Running gauntlet attacks"},
  {content: "Extract concerns with code (jq/Python, NOT LLM)", status: "pending", activeForm: "Extracting concerns with code"},
  {content: "Synthesize findings — one Opus pass, 8-category taxonomy", status: "pending", activeForm: "Synthesizing gauntlet findings"},
  {content: "Revise spec with accepted concerns", status: "pending", activeForm: "Revising spec with accepted concerns"},
  {content: "Run CONS guardrail on revised spec [GATE]", status: "pending", activeForm: "Running CONS guardrail on revised spec"},
  {content: "Display adversary leaderboard + medal standings", status: "pending", activeForm: "Displaying adversary performance results"},
  {content: "Update session state with gauntlet_concerns_path", status: "pending", activeForm: "Updating session state"},
])
```

Mark each step `completed` as you finish it. Mark the current step `in_progress`.

---

### Step 5.5: Gauntlet Review (Optional)

After consensus is reached but before finalization, offer the adversarial gauntlet:

> "All models have agreed on the spec. Would you like to run the adversarial gauntlet for additional stress testing? This puts the spec through attack by specialized personas (security, oncall, QA, etc.)."

**If user accepts gauntlet:**

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
   - `codex/gpt-5.4` — GPT-5.4 via Codex CLI (free, token-efficient)
   - `gemini-cli/gemini-3.1-pro-preview` — Gemini 3 Pro (free via CLI)
   - `claude-cli/claude-sonnet-4-6` — Claude Sonnet 4.6 (free via CLI)

   These become `--gauntlet-attack-models` (comma-separated). The frontier evaluation model is selected automatically.

3. **Understand the cost model BEFORE launching.**

   The gauntlet pipeline makes many LLM calls. Know the math before choosing flags:

   ```
   Phase 1 (attacks):     N adversaries × M attack models = N×M calls
   Phase 2 (synthesis):   1 call (first eval model)
   Phase 3 (filtering):   1 call (cheap model)
   Phase 3.5 (clustering): 1 call (cheap model)
   Phase 4 (evaluation):  ceil(remaining_concerns / 15) batches × E eval models
                           EACH batch re-sends the full spec
   ```

   **Example (real numbers from a username spec gauntlet):**
   8 adversaries × 2 attack models = 16 Phase 1 calls → 331 raw concerns.
   After filtering/dedup: ~300 concerns remain.
   Phase 4: ceil(300/15) = 20 batches × 2 eval models = **40 eval calls**.
   Total: 16 + 2 + 2 + 40 = **60 calls**, each with ~11K token spec as input.

   **Phase 1 is where external models add value** (diverse perspectives finding different issues).
   **Phase 4 is where cost explodes** — and it's advisory, because YOU (Claude) are the final
   evaluator when synthesizing results into spec changes.

   **Reasoning levels are now split** — attacks and evaluations have independent controls:
   - `--codex-reasoning low` (default) — controls attack reasoning effort
   - `--eval-codex-reasoning xhigh` (default) — controls evaluation/adjudication reasoning effort

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

   **Step 6c: Present Findings**

   Present a consolidated concern report using the standard taxonomy:
   ```
   Gauntlet Findings
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
   - Save the full concern report as `gauntlet-concerns-YYYY-MM-DD.json`
   - **Run checkpoint guardrails (CONS) after incorporating the batch of fixes** — gauntlet fix incorporation can introduce cross-section contradictions. Run CONS to catch them. SCOPE and TRACE are not needed here (gauntlet fixes are evaluated by Claude, not automated scope additions).
   - If CONS finds issues, fix and re-run (max 2 attempts, then defer to user)
   - If significant changes were made, consider running another debate round

**[GATE] TodoWrite: Mark "Run CONS guardrail on revised spec" completed before proceeding to Step 8 or phase transition.**

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
- **Target Architecture** — if `specs/<slug>/target-architecture.md` exists (from Phase 4), include it in full. This is the primary architecture context for ALL adversaries. If missing (Phase 4 skipped or legacy session), note: "No target architecture available — architecture-level concerns may be underrepresented."
- **Files in blast zone** — file paths with one-line descriptions of what each does
- **Recent git activity** — last 5 commits touching blast zone files

**Context truncation:** If combined spec + roadmap + target architecture exceeds 80% of the target model's context window, summarize the architecture document before feeding to gauntlet. Preserve all Decision/Rationale sections; truncate Implementation sketches.

#### 3. Assemble Per-Adversary Supplements

Each adversary has a specific lens. Give them ammunition for that lens:

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

---

## SPECIFICATION TO REVIEW

[spec text]
```

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
   - Append journey: `{"time": "ISO8601", "event": "Gauntlet complete, N concerns accepted", "type": "transition"}`
2. **Pointer file** (`session-state.json`): set `current_phase: "finalize"`, `current_step`, `next_action`, `updated_at`
