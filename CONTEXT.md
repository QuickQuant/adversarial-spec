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
