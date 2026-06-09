# adversarial-spec

The domain language of the adversarial-spec skill — a Claude Code skill that refines
specs through multi-model adversarial debate and drives them through a phased pipeline
(requirements → roadmap → debate → target-architecture → gauntlet → finalize →
execution → implementation).

## Language

**Test Strategy** (`test_strategy`):
A Phase 7 per-task choice of testing approach: `test-first`, `test-after`, `spike`
(ship with no automated-test commitment), or `refactor` (restructure existing code,
behavior unchanged). Decoupled from whether tests are actually enforced — that is the
job of `verification_mode`.
_Avoid_: bare "strategy" (collides with Data Strategy); "skip" (not a valid value — use
`spike` for no-test tasks).

**Data Strategy** (`data_strategy`):
A Phase 2 per-test-case classification of *what data* a test exercises: `REAL-DATA`,
`REAL-DATA + PROPERTY`, `SYNTHETIC`, `MOCK`, `MOCK-EXTERNAL`, `FRONTEND`, `STATIC`.
The gauntlet flags violations as the concern category `data_strategy_mismatch`.
_Avoid_: bare "strategy" (collides with Test Strategy).

**Concern** (`concern`):
A problem the **gauntlet** surfaces via adversary attack. Carries an ID (`CB-1`, `RC-2`,
`FM-3`, …), one of the 8 taxonomy categories, and a severity. The unit the gauntlet
funnels and the spec is revised against.
_Avoid_: "finding" (that is the architecture-diagnosis term); "hole".

**Finding** (`finding`):
A problem **architecture diagnosis** surfaces; lives in `.architecture/findings.md`
(produced by mapcodebase / diagnosecodebase / treatcodebase). Distinct from a gauntlet
Concern — different producer, different artifact.
_Avoid_: "finding" for gauntlet output — say "gauntlet concern".

**Hole**:
Informal for a gap or defect. Prefer the precise term: **Concern** (gauntlet) or
**seam defect** (pipeline/process reports).
_Avoid_: "hole" as a standalone noun — *except* the coined compound below.

**Phantom-hole** (`phantom-hole`):
A purported gap that turns out to be already-built or already-specified — a false
Concern that must become a verify/port task, not a from-scratch build (Phase 7
`implementation_status` gate; pipeline-seams #6).

**Correction**:
A problem a **debater** raises against a claim or test classification during debate
(e.g., "promote this test to REAL-DATA"). Distinct from a *human correction point*
(Gate V4), where the user overrides an LLM classification.

**Phase**:
One of the 8 pipeline phases: requirements → roadmap → debate → target-architecture →
gauntlet → finalize → execution → implementation. Reserved exclusively for the pipeline.
_Avoid_: "stage" or "step" for a pipeline phase.

**Step**:
A numbered sub-unit *within* a Phase (e.g., Step 2.5, Step 9b; Gates V1–V4 are named
steps). Note: fizzy card *steps* (`get_card_steps`, `pipeline_attest_steps`) are a
separate, scoped checklist concept — always say "card steps" for those.
_Avoid_: "stage" for a sub-unit of a phase.

**Stage** (qualified only — e.g., `depth-triage Stage 1`):
A milestone of a named implementation roadmap, not part of the pipeline. The active
numbering is the **depth-triage-overhaul** roadmap (defined in
fizzy-pipeline-mcp's design corpus): Stages 1–5 are fizzy-side, Stage 7 is this
skill's mini-spec emission. Stage 6 (system validation) was deliberately deferred and
de-numbered; the numbering intentionally skips 6 — do not reuse it.
_Avoid_: bare "Stage N" (collides with Phase/Step numbering and with maturity stages).

**Test-Case Maturity Stage** (`stage:` field on a test case):
The lifecycle of a test case through the workflow: `nl` (natural language, roadmap
creation) → `acceptance` (post-debate) → `concrete` (implementation). Scoped to the
`(stage: …)` parenthetical on TC lines.
_Avoid_: numbering these as bare "Stage 1/2/3" in prose — say "maturity stage `nl`" etc.

**Session**:
One adversarial-spec workflow instance: `adv-spec-<timestamp>-<slug>`, owning a phase,
step, spec, and pipeline card; stacked, parked, or completed in `session-state.json`.
When meaning a terminal conversation instead, always qualify: "Claude Code session".
_Avoid_: bare "session" for a terminal conversation.

**Context**:
The named work identity a Session belongs to — the `context_name` field (e.g.
"Dispatch & Cost-Tracker Unification"). What `/context-switch` switches between.
_Avoid_: "work stream" (deprecated alias from the retired Tasks MCP); "context" for the
token/context-window sense (general programming vocabulary, qualify as "context window").

**Workstream**:
A parallel task grouping *inside one execution plan*: independent streams of tasks
(e.g. "Stream A (Backend)") with merge points, sized at decomposition. Exists only
within Phase 7/8.
_Avoid_: "workstream" for a Context — a workstream is intra-plan, a Context is the
work identity itself.
