### Step 5.5: Gauntlet Review (Optional)

After consensus is reached but before finalization, offer the adversarial gauntlet:

> "All models have agreed on the spec. Would you like to run the adversarial gauntlet for additional stress testing? This puts the spec through attack by specialized personas (security, oncall, QA, etc.)."

**If user accepts gauntlet:**

1. Ask which adversary personas to use (or use 'all'):
   ```bash
   python3 ~/.claude/skills/adversarial-spec/scripts/debate.py gauntlet-adversaries
   ```

2. **Arm Adversaries** (REQUIRED before running gauntlet). See below.

3. Run the gauntlet with armed briefings.

4. Review the gauntlet report:
   - Phase 1: Adversary attacks (parallel, with per-adversary briefings)
   - Phase 2: Frontier model evaluates each attack
   - Phase 3: Rebuttals from dismissed adversaries
   - Phase 4: Summary report with accepted concerns

5. Optionally run Phase 5 Final Boss (expensive but thorough UX review)

6. Integrate accepted concerns into the spec:
   - Add mitigations for high-severity concerns
   - Update relevant sections
   - Save concerns JSON for execution planning: `gauntlet-concerns-YYYY-MM-DD.json`

7. If significant changes were made, consider running another debate round with the updated spec

**If user declines gauntlet:**
- Proceed directly to Step 6

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
- **Files in blast zone** — file paths with one-line descriptions of what each does
- **Recent git activity** — last 5 commits touching blast zone files

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
