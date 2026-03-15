## Target Architecture (Phase 4)

After spec debate converges, define the shared architecture patterns before the gauntlet.

**Prerequisites:**
- Spec debate (Phase 3) has converged
- Roadmap with user stories exists

**Inputs:**
- Converged spec draft
- Roadmap / user stories
- `.architecture/manifest.json` patterns[] (optional — from `/mapcodebase`)
- Framework documentation (via Context7 / web)
- gemini-bundle findings (optional)

---

### Step 1: Scale Check (Gate)

Not every project needs formal architecture. Assess:

```
Scale Assessment
───────────────────────────────────────
Spec scope: [user story count]
Codebase: [greenfield / existing with N files]
Stack complexity: [single runtime / multi-service]

Recommended: [Full architecture | Lightweight | Skip]
```

**Skip criteria:** <3 user stories AND single-file scope, or pure library with no app layer.

If skip: log Decision Journal entry with `decision: "skip"`, transition directly to gauntlet.

---

### Step 2: Assess Starting Point

**Greenfield (no code exists):**
Architecture drafted from scratch (Steps 3-5).

**Brownfield (existing codebase):**
1. Load `.architecture/overview.md` and relevant component docs
2. List all `warning`/`error` patterns from `manifest.json` `patterns[]`
3. Load gemini-bundle findings if available
4. Focus: "what new patterns does this spec need?" + "which existing patterns need adjustment?"

---

### Step 3: Categorize the Application

Classify along dimensions relevant to the project type. The taxonomy adapts to the category — don't force web-app dimensions onto a CLI tool.

**Schema (flexible dimensions array):**
```json
{
  "architecture_taxonomy": {
    "category": "web-app | cli | api-service | library | data-pipeline | mobile | other",
    "dimensions": [
      {
        "name": "rendering",
        "value": "hybrid-ssr-csr",
        "rationale": "SSR for initial load, CSR for interactive editors",
        "source_refs": ["Next.js App Router docs", "spec §7"]
      }
    ],
    "confirmed_by_user": true,
    "confirmed_at": "ISO8601"
  }
}
```

**Typical dimensions by category:**
- **Web apps:** Rendering, Navigation, Auth, Data freshness, State management, Multi-page sharing
- **CLIs:** Execution model, State, Concurrency, I/O
- **APIs:** Transport, Auth, Data layer, Scaling
- **Libraries:** API surface, Error handling, Extensibility

Present classification to user for confirmation before proceeding.

---

### Step 4: Research Best Practices

For each dimension:
1. Look up established pattern for the chosen stack
2. Minimum 2 sources (official docs + community/template)
3. Use Context7 if available for exact API signatures
4. Note where the framework provides built-in solutions

---

### Step 5: Draft Target Architecture Document

Produce `specs/<slug>/target-architecture.md`:

```markdown
### [Pattern Name]
**Decision:** [pattern chosen]
**Rationale:** [why, with source references]
**Alternative considered:** [what else was evaluated]
**Implementation sketch:** [code snippets or file structure]
**Applies to:** [which user stories / features]
```

If `patterns[]` available from mapcodebase: each `warning`/`error` pattern gets a corresponding section explaining how it's addressed.

---

### Step 6: Debate the Architecture

Run architecture-specific critique rounds:

```bash
cat specs/<slug>/target-architecture.md | \
  uv run python ~/.claude/skills/adversarial-spec/scripts/debate.py critique \
  --models MODEL_LIST --doc-type architecture --round N \
  --context specs/<slug>/spec-draft-latest.md \
  $CONTEXT_FLAGS
```

**If debate reveals spec gaps:** Revise spec → run spec debate round → resume architecture debate.

Continue until convergence.

---

### Step 7: Dry-Run Verification

Walk the most complex user flow through the architecture step-by-step:
- Which component renders / handles the request?
- What data is fetched, by whom, via what mechanism?
- What state is created, where, what happens on navigation?
- What happens on error?

**The dry-run is the proof the architecture is complete.**

If gaps found: revise architecture, re-debate the change.

---

### Step 8: Record Decisions

Log all architecture decisions to the Decision Journal in the session detail file.

**Decision Journal schema:**
```json
{
  "decision_journal": [
    {
      "entry_id": "dj-YYYYMMDD-<6 char random>",
      "time": "ISO8601",
      "phase": "target-architecture",
      "topic": "auth-pattern",
      "decision": "adopt",
      "choice": "Middleware-based auth with cached fallback",
      "rationale": "Eliminates per-page auth calls",
      "alternatives_considered": ["Per-page getUser()", "React cache() only"],
      "revisit_trigger": "If middleware latency exceeds 50ms",
      "reverses_entry_id": null
    }
  ]
}
```

**Decision types:** `adopt`, `reject`, `defer`, `skip`, `reversed`

**Rules:**
- Append-only — never edit or delete entries
- `reversed` entries must set `reverses_entry_id` pointing to the original
- Required fields: `entry_id`, `time`, `phase`, `topic`, `decision`, `choice`, `rationale`
- Optional fields: `alternatives_considered`, `revisit_trigger`, `reverses_entry_id`

---

### Outputs
- `specs/<slug>/target-architecture.md`
- Decision Journal entries in session detail file
- Architecture taxonomy in session detail file

### Completion Criteria
- All taxonomy dimensions decided with rationale
- At least one dry-run completed without gaps
- Architecture debated through at least one converged round
- Decision Journal records categorization + each pattern decision

### Phase Transition

**Detail file** (`sessions/<id>.json`):
- Set `current_phase: "gauntlet"`
- Set `target_architecture_path` to the architecture doc path
- Append journey: `{"time": "ISO8601", "event": "Phase transition: target-architecture → gauntlet", "type": "transition"}`

**Pointer file** (`session-state.json`):
- Update `current_phase`, `current_step`, `next_action`, `updated_at`
