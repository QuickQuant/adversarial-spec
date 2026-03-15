### Step 5.5: Gauntlet Review (Optional)

After consensus is reached but before finalization, offer the adversarial gauntlet:

> "All models have agreed on the spec. Would you like to run the adversarial gauntlet for additional stress testing? This puts the spec through attack by specialized personas (security, oncall, QA, etc.)."

**If user accepts gauntlet:**

1. Ask which adversary personas to use (or use 'all'):
   ```bash
   python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet-adversaries
   ```

   **Adversary Quick Reference (exact CLI names):**

   | Prefix | CLI Name | Role |
   |--------|----------|------|
   | COMP | `existing_system_compatibility` | Codebase compatibility (pre-gauntlet) |
   | PARA | `paranoid_security` | Security threats |
   | BURN | `burned_oncall` | Operational failure modes |
   | LAZY | `lazy_developer` | Unnecessary complexity |
   | PEDA | `pedantic_nitpicker` | Edge cases |
   | ASSH | `asshole_loner` | Design flaws |
   | PREV | `prior_art_scout` | Existing code reuse |
   | AUDT | `assumption_auditor` | Unverified assumptions |
   | FLOW | `information_flow_auditor` | Architecture flow gaps |
   | ARCH | `architect` | Code structure, data flow, component boundaries |
   | UXAR | `ux_architect` | User story coherence (final boss) |

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
   - `gemini-cli/gemini-3-pro-preview` — Gemini 3 Pro (free via CLI)
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

   **`--codex-reasoning` is GLOBAL** — it applies to attacks AND evaluations equally.
   There is no way to use xhigh for attacks and medium for evaluation (or vice versa).

   **Reasoning level guidance:**

   | Level | When to use | Trade-off |
   |-------|------------|-----------|
   | `medium` | **Default for gauntlet runs.** Attack quality at medium is still high — adversary system prompts are well-crafted and do the heavy lifting. Eval quality at medium is fine because it's advisory (Claude does final evaluation). | Best cost/value ratio |
   | `high` | User explicitly requests deeper analysis, or spec is unusually complex (>30 sections, multiple interacting systems) | 2-3× more quota than medium |
   | `xhigh` | Almost never for gauntlet. 60 calls at xhigh will burn through Codex 5h queue in minutes. Only if user explicitly requests it AND understands the cost. | Can exhaust daily quota in one run |
   | `low` | Quick exploratory gauntlet, draft specs, when you just want a rough signal | Fast but may miss subtle issues |

   **Always pass `--codex-reasoning medium` unless the user explicitly requests otherwise.**

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

5. Run the gauntlet with armed briefings.

   **Gemini Rate Limit Staggering (REQUIRED):**
   When using Gemini CLI models as attack models, do NOT launch all adversaries simultaneously. Gemini's free tier has a **4 requests per minute** rate limit that causes 429 errors and returns 0 structured concerns if exceeded.

   - **Max 4 Gemini calls per 60-second window**
   - Launch up to 4 adversaries at once, wait 61s, then launch the next batch
   - All batches run in background — do NOT block-wait for Batch 1 to finish before launching Batch 2
   - After launching each batch, do a quick `TaskOutput(block=false)` check at ~45s to catch quota errors early
   - Collect all results AFTER all batches are launched

   **Example launch order** (8 adversaries, Gemini attack model):
   ```
   Batch 1: PARA, BURN, LAZY, PEDA (launch together)
   sleep 61s
   Batch 2: ASSH, PREV, AUDT, FLOW (launch together)
   Collect all 8 results
   ```

6. **Post-Gauntlet Synthesis (REQUIRED — this is where real evaluation happens).**

   The pipeline's automated evaluation (Phases 2-4) is a useful first pass, but **Claude is the
   final evaluator**. The pipeline generates concerns; Claude judges them. This is intentional —
   Claude has full codebase context, spec history, and architectural understanding that the
   pipeline's eval models do not.

   **Step 6a: Parse Sanity Check**

   After the pipeline completes, check that the parser accurately captured all model responses.

   **Why:** Some models (especially Gemini) output structured markdown (`### 1. Title` with
   sub-bullets) instead of plain numbered lists (`1. Concern text`). The parser expects
   `line[0].isdigit()` so `### 1.` lines are silently dropped — entire high-quality responses
   can parse to 0 concerns.

   **Process:**
   - Check the gauntlet output for any adversary×model combinations with 0 concerns
   - If any exist, read the raw responses file (`.adversarial-spec-gauntlet/raw-responses-*.json`)
   - Launch a **haiku subagent** to read the raw responses for 0-concern entries and report:
     "N responses had substantive content but 0 parsed concerns. Summaries: [one-line each]"
   - If mismatches found, YOU read the raw responses directly — they're part of your evaluation input

   **Common parse failure patterns:**
   - `### N. Title` (Gemini markdown headers) — parser expects `N.` at line start
   - Structured sub-bullets without a plain numbered parent line
   - Concerns formatted as prose paragraphs without numbering

   **Cost:** One haiku call (~2K input tokens). Prevents losing entire model perspectives.

   **Step 6b: Synthesize ALL Inputs**

   Your evaluation inputs are:
   1. **Pipeline verdicts** (Phase 4 output) — accepted, dismissed, acknowledged, deferred
   2. **Raw responses for parse failures** — concerns the pipeline never evaluated
   3. **Your own codebase knowledge** — architecture docs, blast zone files, implementation state
   4. **Spec context** — what's already addressed, what's intentional, what's out of scope

   **Evaluation process:**
   - Start with pipeline-accepted concerns — these already passed automated review. Quickly
     confirm they're real (the pipeline is usually right on accepts).
   - Check pipeline-dismissed concerns for false negatives — did the eval model dismiss something
     valid? Skim the reasoning. Focus on dismissals where the eval said "spec already handles this"
     but you know the spec doesn't.
   - Read raw responses from parse failures. These are often the highest-signal concerns because
     they came from a different model perspective (Gemini vs GPT).
   - **Deduplicate across sources.** The same concern often appears from multiple adversaries and
     both parsed + unparsed responses. Group by theme, not by source.
   - Classify each unique concern:
     - **Accept** — spec needs revision. Note what changes.
     - **Acknowledge** — valid point, won't address (out of scope, known tradeoff). Credit the adversary.
     - **Dismiss** — not valid. One sentence why.

   **Step 6c: Present Findings**

   Present a consolidated concern report (not the raw pipeline dump):
   ```
   Gauntlet Findings
   ═══════════════════════════════════════
   Sources: N pipeline-evaluated + M from parse recovery
   After dedup: X unique concerns

   ACCEPTED (spec changes needed):
   1. [theme] — [one-line summary] (sources: PARA×GPT, BURN×Gemini)
   2. ...

   ACKNOWLEDGED (valid, won't address):
   1. [theme] — [one-line summary + why not addressing]
   2. ...

   DISMISSED: Y concerns (noise/already covered)

   [Proceed to spec revision] [Discuss specific concerns]
   ```

7. **Revise spec with accepted concerns.**
   - Add mitigations for accepted concerns
   - Update relevant sections (don't summarize or reduce existing content)
   - Save the full concern report as `gauntlet-concerns-YYYY-MM-DD.json`
   - If significant changes were made, consider running another debate round

8. Optionally run Final Boss (UX Architect review — expensive but thorough)

**If user declines gauntlet:**
- Proceed directly to finalize phase

---

### Arm Adversaries (before gauntlet attack generation)

Adversaries produce higher-quality findings when they have codebase context, not just the spec text. This step assembles per-adversary briefing documents from the Context Readiness Audit inventory (built during debate — see 03-debate.md) and reports token overhead.

**Process:**

#### 1. Check for Context Inventory

The Context Readiness Audit (between debate Round 1 and Round 2) should have produced a `ContextInventoryV1` in session state.

- **If inventory exists:** Check staleness — compare `git_hash` in inventory to current `git rev-parse --short HEAD`. If HEAD changed, re-extract only modified blast zone artifacts.
- **If inventory is missing** (audit was skipped or session is new): Run a lightweight version now — check architecture docs, blast zone files, and git state. Skip the full checklist but get enough for base context.

#### 2. Assemble Base Context (all adversaries)

Every adversary gets a feature briefing (~800 tokens):

- **Architecture excerpt** — relevant subsection of `.architecture/overview.md` (NOT the whole file). If no architecture docs exist, note this as a gap.
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
| **LAZY** (lazy_developer) | Installed SDK capabilities, platform features already available, existing utility functions, framework builtins that overlap with spec proposals | ~420 tok |
| **PEDA** (pedantic_nitpicker) | Type definitions, enum values, schema constraints (nullable, unique, defaults), validation rules, test coverage report if available | ~380 tok |
| **ASSH** (asshole_loner) | Design rationale / ADRs, known tech debt markers (TODO/FIXME/HACK in blast zone), broader architecture context beyond excerpt | ~200 tok |
| **COMP** (existing_system) | Full build/test status, current vs proposed schema diff, naming conventions in area, pending migrations, duplicate file analysis | ~1,100 tok |
| **PREV** (prior_art_scout) | Legacy/archive search results, dependency inventory (installed but unused SDKs), keyword search results across codebase, existing similar pattern analysis | ~650 tok |
| **AUDT** (assumption_auditor) | External API doc excerpts, SDK type definitions, existing integration code showing how external systems actually behave | ~300 tok |
| **FLOW** (info_flow_auditor) | FULL architecture overview (not just excerpt), data flow docs from `.architecture/structured/flows.md`, external API capabilities (REST/WS/webhook), existing latency data if available | ~900 tok |
| **ARCH** (architect) | FULL target architecture doc (not just excerpt), component docs from `.architecture/structured/components/`, existing shared patterns/utilities inventory, first-feature propagation analysis | ~1,000 tok |

#### 4. Apply Relevance Filter

Not every adversary needs every supplement for every spec:

- Spec adds an API endpoint? → PARA gets auth patterns, FLOW gets data flow
- Spec changes a data model? → PEDA gets constraints, COMP gets schema diff
- Spec integrates external service? → AUDT gets API docs, PREV gets existing integrations
- Spec is internal refactor? → LAZY gets utility inventory, ASSH gets design rationale
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
LAZY  lazy_developer       800   1,400     420       2,620
PEDA  pedantic_nitpicker   800   1,400     380       2,580
ASSH  asshole_loner        800   1,400     200       2,400
COMP  existing_system      800   1,400   1,100       3,300
PREV  prior_art_scout      800   1,400     650       2,850
AUDT  assumption_auditor   800   1,400     300       2,500
FLOW  info_flow_auditor    800   1,400     900       3,100
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
cat briefing-COMP.md | python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet \
  --gauntlet-adversaries existing_system_compatibility
```

In practice, Claude assembles the briefings in memory and passes them to the gauntlet. The `generate_attacks()` function accepts an optional `briefings: dict[str, str]` parameter — if provided, each adversary gets its specific briefing instead of raw spec. If not provided, falls back to spec-only (backward compatible).

**UX_ARCHITECT (Final Boss) is NOT armed here.** The final boss runs AFTER the gauntlet phases and receives the full concern summary. Its context is the gauntlet output itself.

#### Token Budget Guidelines

| Component | Budget | Rationale |
|-----------|--------|-----------|
| Base context (per adversary) | 600–1,000 tok | Architecture excerpt + blast zone + git. Orientation, not drowning. |
| Per-adversary supplement | 200–1,200 tok | COMP/FLOW need more (audit structure). ASSH needs less (attacks logic). |
| Total per adversary | 800–2,200 tok added | Never more than 2x the spec size in added context. |
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
