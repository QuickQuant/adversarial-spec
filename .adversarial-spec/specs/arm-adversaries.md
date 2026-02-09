# Arm Adversaries: Context Readiness Audit & Per-Adversary Briefings

**Status:** Post-debate (Codex reviewed, merged)
**Date:** 2026-02-09
**Debated with:** codex/gpt-5.3-codex (medium reasoning)
**Scope:** Changes to adversarial-spec skill phases (03-debate.md, 04-gauntlet.md) and optional tooling support

---

## Problem Statement

Gauntlet adversaries currently receive ONLY the spec text. Adversaries like `existing_system_compatibility` (COMP) and `prior_art_scout` (PREV) explicitly state "You need CODEBASE ACCESS to do your job" in their persona prompts — but they never receive any. The `information_flow_auditor` (FLOW) audits architecture diagrams without seeing the architecture docs. Security and operations adversaries (PARA, BURN) make generic recommendations because they don't know what defenses already exist.

Meanwhile, the infrastructure to collect codebase context already exists:
- Pre-gauntlet system (`pre_gauntlet/`) collects git state, build health, schema snapshots
- Context addition protocol (`reference/context-addition-protocol.md`) describes per-round extraction
- `.architecture/` docs provide high-level system overviews

These systems are disconnected from the gauntlet adversary pipeline. The pre-gauntlet output gets mixed into spec markdown rather than structured per-adversary. The context-addition-protocol covers debate rounds but not gauntlet attacks. Architecture docs are never injected.

### Secondary Problem: Flying Blind

Even if we could deliver context to adversaries, we may not HAVE the context they need. There's no step in the current process that audits what's available vs what's needed. Gaps like "no test coverage report exists" or "no monitoring data available" are discovered by adversaries at attack time — wasting an adversary turn on "you didn't give me what I need" instead of finding real problems.

---

## Decision

Introduce two new structured steps in the workflow:

1. **Context Readiness Audit** — runs between debate Round 1 (requirements) and Round 2 (architecture). Inventories available context, discovers gaps, spawns tasks for actionable gaps.

2. **Arm Adversaries** — runs after debate consensus, before gauntlet. Assembles per-adversary briefing documents from the context inventory. Reports token counts.

---

## Getting Started

### Prerequisites
- Python 3.14+, `uv`, project dependencies installed
- Git repository with readable history
- Access to spec draft and local codebase
- Optional: `.architecture/` docs, test suite, dependency manifests

### First-Run Workflow

1. Start normal debate flow and complete **Round 1 (requirements)**
2. Run **Context Readiness Audit** (automatic — happens between R1 and R2)
3. Review audit output. Choose: generate gaps, skip, or pick which
4. Continue debate (Round 2+), using audit inventory as context source
5. After debate consensus, run **Arm Adversaries** (automatic — before gauntlet)
6. Review token report. Proceed to gauntlet with armed briefings
7. Confirm at least one context-dependent adversary (COMP/FLOW/PREV) references provided context in its findings

### User Journey

| User | Experience |
|------|-----------|
| New | Runs debate R1, sees audit output, learns what context exists in their repo |
| Intermediate | Resolves high-value gaps (coverage, docs, build status) before continuing debate |
| Productive | Runs armed gauntlet, receives context-grounded adversary findings |
| Advanced | Tunes relevance filters and token budgets per spec type |

---

## Design

### Step A: Context Readiness Audit

**When:** Between debate Round 1 and Round 2.

**Why here:** Round 1 validates requirements (no codebase context needed). Round 2 debates architecture (codebase context critical). This is the natural inflection point. Gaps discovered here have time to be addressed — tasks can complete while debate rounds proceed.

**Who executes:** Claude as orchestrator, using its existing tools (Read, Grep, Glob, Bash).

**Process:**

1. **Parse spec for references.** Identify:
   - File paths, module names, table names, function names mentioned in spec
   - External services/APIs the spec integrates with
   - The "blast zone" — files/modules the spec will likely modify

2. **Check context sources against a checklist:**

   | Context Source | Check Method | Who Benefits |
   |---------------|-------------|--------------|
   | Architecture docs | `[ -f .architecture/manifest.json ]` | ALL (base context) |
   | Schema/type definitions | Grep for table/interface names in blast zone | PEDA, COMP |
   | Test coverage | Check for pytest-cov config or recent coverage report | PEDA, COMP |
   | Dependency inventory | Read pyproject.toml / package.json | LAZY, PREV, PARA |
   | Git recent changes | `git log --oneline -10 -- <blast zone files>` | COMP, PREV |
   | Build/test status | `uv run pytest --tb=short` (or equivalent) | COMP |
   | Monitoring/metrics | Check for alerting config, dashboards, SLIs | BURN |
   | Error handling patterns | Grep for try/except, circuit breaker, retry in blast zone | BURN |
   | Auth/authz patterns | Grep for auth, permission, token in blast zone | PARA |
   | External API docs | Check for SDK, cached docs, Context7 availability | AUDT, FLOW |
   | Legacy/archive dirs | `find . -type d -name "_legacy" -o -name "deprecated"` | PREV |
   | Design rationale (ADRs) | Check for decision docs, spec history | ASSH |
   | Existing similar features | Grep for feature keywords across codebase | PREV, LAZY |

3. **Classify each source:**
   - `AVAILABLE` — exists, can be extracted
   - `PARTIAL` — exists but incomplete (e.g., tests exist but no coverage report)
   - `NOT_AVAILABLE` — doesn't exist
   - `NOT_APPLICABLE` — irrelevant for this project/spec (e.g., no monitoring for a CLI tool)

4. **For PARTIAL sources, determine if gap is actionable:**
   - Can we generate a coverage report right now? → Suggest task
   - Can we fetch API docs via Context7? → Suggest task
   - Can we run a dependency audit? → Suggest task
   - Is this a fundamental gap that the spec SHOULD address? → Note for debate Round 2+

5. **Present audit results to user:**

   ```
   Context Readiness Audit
   ═══════════════════════════════════════
   Blast zone: 5 files, 3 modules

   ✓ AVAILABLE (6)
     Architecture docs, schema definitions, type definitions,
     dependency inventory, git history, build status

   ⚠ GAPS (2)
     Test coverage — no pytest-cov configured
       → Can generate now (spawns 30s task)
     External API docs — spec references FooAPI, no local docs
       → Can fetch via Context7 (spawns task)

   ✗ NOT AVAILABLE (1)
     Monitoring data — no alerting configured
       → This is a design gap. Debate Round 3 should address it.

   ─ NOT APPLICABLE (1)
     Incident reports — not relevant for CLI tool

   [Generate available gaps] [Proceed without] [Choose which]
   ```

6. **Cache inventory.** Store the audit results in session state so:
   - Debate rounds can draw from it (per context-addition-protocol)
   - Arm Adversaries phase can reuse it without re-extracting
   - Staleness can be detected (if commits land during debate)

**Output:** A `ContextInventoryV1` object stored in session state:

```json
{
  "schema_version": "1.0",
  "audit_timestamp": "2026-02-09T14:30:00Z",
  "git_hash": "e94ebfe",
  "blast_zone": ["execution_planner/__init__.py", "scripts/debate.py"],
  "sources": {
    "architecture_docs": {
      "status": "available",
      "path": ".architecture/overview.md",
      "summary": "70-line system overview with component map",
      "est_tokens": 1200
    },
    "test_coverage": {
      "status": "partial",
      "summary": "Tests exist for 4/11 modules, no coverage report",
      "est_tokens": 0,
      "actionable": true,
      "task_id": "task-42"
    }
  },
  "total_available_tokens": 8500,
  "gaps_noted": ["No monitoring data — design gap for Round 3"]
}
```

**Compatibility rules:** Unknown fields are ignored on read. Missing required fields (`schema_version`, `audit_timestamp`, `git_hash`, `blast_zone`, `sources`) fail validation with a clear error message prompting re-run.

### Step B: Arm Adversaries

**When:** After debate consensus, before gauntlet attack generation.

**Why here:** Adversaries attack a finished spec. They need context assembled for their specific lens. The audit has already inventoried what's available and filled actionable gaps.

**Who executes:** Claude as orchestrator.

**Process:**

1. **Refresh stale context.** Check if commits landed since the audit:
   ```bash
   git rev-parse --short HEAD  # Compare to audit git_hash
   ```
   If HEAD changed, re-extract blast zone artifacts that were modified.

2. **Assemble base context (all adversaries get this):**
   - Architecture excerpt — relevant subsection of `.architecture/overview.md` (NOT the whole thing)
   - Files in blast zone — file paths with one-line descriptions
   - Recent git activity — last 5 commits touching blast zone files
   - Budget: ~800 tokens

3. **Assemble per-adversary supplements:**

   | Adversary | Supplement Sources | Budget |
   |-----------|-------------------|--------|
   | PARA (paranoid_security) | Auth/authz patterns, input validation boundaries, dependency audit results, API surface area | ~350 tok |
   | BURN (burned_oncall) | External dependency list with timeout configs, existing error handling patterns, monitoring status (or explicit "none exists" note) | ~280 tok |
   | LAZY (lazy_developer) | Installed SDK capabilities, platform features, existing utility functions, framework builtins that overlap with spec proposals | ~420 tok |
   | PEDA (pedantic_nitpicker) | Type definitions, enum values, schema constraints, validation rules, test coverage report (if generated) | ~380 tok |
   | ASSH (asshole_loner) | Design rationale / ADRs, known tech debt markers (TODO/FIXME/HACK in blast zone), broader architecture context | ~200 tok |
   | COMP (existing_system) | Full build/test status, current vs proposed schema diff, naming conventions, pending migrations, duplicate file analysis | ~1,100 tok |
   | PREV (prior_art_scout) | Legacy/archive search results, dependency inventory, keyword search results, existing similar pattern analysis | ~650 tok |
   | AUDT (assumption_auditor) | External API doc excerpts, SDK type definitions, existing integration code showing actual behavior | ~300 tok |
   | FLOW (info_flow_auditor) | FULL architecture overview (not excerpt), data flow docs, external API capabilities (REST/WS/webhook), existing latency data if available | ~900 tok |

4. **Apply relevance filter.** Not every adversary needs every supplement every time:
   - Spec adds an API endpoint? → PARA gets auth patterns, FLOW gets data flow
   - Spec changes data model? → PEDA gets constraints, COMP gets schema diff
   - Spec integrates external service? → AUDT gets API docs, PREV gets existing integrations
   - Spec is internal refactor? → LAZY gets utility inventory, ASSH gets design rationale
   - If a supplement source was NOT_AVAILABLE or NOT_APPLICABLE, skip it and note why

5. **Format briefings.** Each adversary's context is prepended to the spec in a structured block:

   ```markdown
   ## ADVERSARY BRIEFING: [adversary_name]

   > This briefing contains codebase context extracted for your review.
   > Extraction: 2026-02-09T15:00:00Z | Git: e94ebfe | Branch: main

   ### Base Context
   [architecture excerpt, blast zone files, git activity]

   ### Your Specific Context
   [per-adversary supplement]

   ### Known Gaps
   [anything we couldn't provide, e.g., "No monitoring data — CLI tool"]

   ---

   ## SPECIFICATION TO REVIEW

   [spec text]
   ```

6. **Report token counts.** After assembly, present a `BriefingBundleV1`:

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

   Machine-readable form stored in session:
   ```json
   {
     "schema_version": "1.0",
     "generated_at": "2026-02-09T15:00:00Z",
     "git_hash": "e94ebfe",
     "adversaries": {
       "paranoid_security": {
         "base_tokens": 800,
         "supplement_tokens": 350,
         "spec_tokens": 1400,
         "total_tokens": 2550,
         "gaps": []
       },
       "burned_oncall": {
         "base_tokens": 800,
         "supplement_tokens": 280,
         "spec_tokens": 1400,
         "total_tokens": 2480,
         "gaps": ["No monitoring data — CLI tool"]
       }
     }
   }
   ```

7. **UX_ARCHITECT (Final Boss) is NOT armed here.** The final boss runs AFTER the gauntlet and receives the full concern summary from all adversaries plus the spec. Its context is the gauntlet output itself.

### Integration with Existing Systems

**Context-Addition-Protocol (debate rounds):**
The audit inventory serves as the context cache that the protocol draws from. Instead of Claude re-extracting snippets each round, it pulls from the inventory and checks for staleness. The protocol's format (appendix with A0, A1, A2 labels) remains unchanged. Token tracking extends to debate round appendices too.

**Pre-Gauntlet System (`pre_gauntlet/`):**
The audit subsumes what pre-gauntlet does (git state, build health). Pre-gauntlet's alignment mode (blocking on build failures, schema drift) still applies — if the audit discovers the build is broken, it should STOP just like pre-gauntlet does. Over time, pre-gauntlet collectors could be refactored into audit checklist items.

**`generate_attacks()` in gauntlet.py:**
Currently takes `spec: str`. After this change, it should accept an optional `briefings: dict[str, str]` where keys are adversary names and values are the assembled briefing+spec documents. Rules:
- If `briefings` is None: every adversary receives `spec` (backward compatible, no change)
- If `briefings` provided: adversary gets `briefings[adversary_name]` if present, else falls back to `spec`

### Token Budget Guidelines

| Component | Budget | Rationale |
|-----------|--------|-----------|
| Base context (per adversary) | 600–1,000 tok | Architecture excerpt + blast zone + git. Enough for orientation, not drowning. |
| Per-adversary supplement | 200–1,200 tok | Varies by adversary. COMP/FLOW need more (they audit structure). ASSH needs less (attacks logic). |
| Total per adversary | 800–2,200 tok over spec-only | Never more than 2x the spec size in added context. |
| Total increase across all adversaries | < 100% | Doubling input tokens is the upper bound. If context exceeds this, prioritize by adversary relevance. |

**If budget is exceeded:**
1. Trim base context — use shorter architecture excerpt
2. Drop supplements for adversaries where spec doesn't touch their domain
3. Truncate large artifacts (schema diffs, dependency lists) with `... N more items`

### What This Does NOT Change

- Adversary personas remain in `adversaries.py` (no changes)
- Gauntlet evaluation pipeline (Phase 2-6) is unchanged
- Debate rounds 1-4+ flow is unchanged (context-addition-protocol handles debate context)
- Model selection for adversaries is unchanged (still free/cheap models)
- Final Boss (UX_ARCHITECT) flow is unchanged

---

## Implementation Plan

### Phase 1: Document Updates (orchestrator instructions)

Both the audit and arming phases are instructions for Claude-as-orchestrator, not Python code. The extraction uses tools Claude already has.

1. **Update 03-debate.md:** Add "Step 1.5: Context Readiness Audit" between Round 1 and Round 2. Include the checklist, classification scheme, gap reporting format, and inventory caching instructions.

2. **Update 04-gauntlet.md:** Add "Step 0: Arm Adversaries" before attack generation. Include the assembly process, per-adversary supplement table, relevance filter, briefing format, and token reporting.

3. **Update context-addition-protocol.md:** Add section on drawing from the audit inventory instead of re-extracting. Add token tracking to round appendices.

### Phase 2: Code Changes (optional, for structured support)

1. **Modify `generate_attacks()` signature** to accept optional `briefings: dict[str, str] | None = None`. Backward compatible — if not provided, uses raw spec.

2. **Add token estimation utility.** Simple function: `estimate_tokens(text: str) -> int` using `len(text) // 4` approximation. Used for reporting only, not enforcement.

### Phase 3: Refinement (after real-world usage)

1. Track whether armed adversaries produce higher-quality concerns than unarmed ones (compare medal counts, signal scores)
2. Tune token budgets based on actual usage data
3. Consider caching briefings across gauntlet runs for the same spec (if spec hash unchanged)

---

## Validation

The design is validated when:
- [ ] Context Readiness Audit runs between Round 1 and Round 2 and surfaces actionable gaps
- [ ] Arm Adversaries assembles per-adversary briefings with token counts reported
- [ ] COMP receives codebase context and no longer raises "I need codebase access" as first concern
- [ ] FLOW receives full architecture docs and audits actual component connections
- [ ] PREV receives dependency inventory and legacy search results
- [ ] Token overhead stays under 100% increase vs spec-only baseline
- [ ] Gap report spawns at least one useful task in a real session
- [ ] Adversary quality improves (measured by medal counts / signal scores pre vs post)

---

## Open Questions

1. **Should the audit inventory be persisted to disk or kept in session state?** Disk persistence survives context compression but adds file I/O. Session state is simpler but may be lost in long sessions.

2. **Should armed adversaries get different system prompts?** Currently all adversaries get the same "find problems with this specification" framing. With context, we could say "find problems with this specification GIVEN the codebase context below." This is a small but potentially impactful change.

3. **Should we skip arming for adversaries whose supplement is < 100 tokens?** Below a threshold, the context adds noise without value. But even "NOTE: No monitoring data exists" is useful signal.

4. **Pre-gauntlet deprecation path.** The audit subsumes pre-gauntlet functionality. Should pre-gauntlet be deprecated in favor of the audit, or kept as a separate fast-path for users who skip debate?
