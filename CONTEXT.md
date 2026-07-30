# adversarial-spec

> Shared ecosystem terms (Phase, Card, Session, Context, …) are canonical in
> `~/PycharmProjects/Brainquarters/shared-context/GLOSSARY.md` (auto-loaded into every
> session). This file is the richer, project-flavored source the shared entries derive from.

The domain language of the adversarial-spec skill — a Claude Code skill that refines
specs through multi-model adversarial debate and drives them through a phased pipeline
(requirements → roadmap → debate → target-architecture → gauntlet → finalize →
execution → implementation).

## Language

### Testing

**Happy-Path Spine** (`spine: true`, `spine_steps`, `spine_of`, `spine_step_ref`):
The single primary-success test designation for a user story. It anchors the main
journey and gives branch/failure tests named steps to hang from. Always qualify the
term as **happy-path spine** in prose to avoid collision with the Phase 7
**Architecture Spine**. Machine tokens (`spine`, `spine_of`, `spine_steps`,
`spine_step_ref`, `orphaned_spine`, `SpineCoverageChecker`) keep their exact names.
_Avoid_: unqualified "happy-path spine" shorthand in prose; use the full term
unless the text is a machine token.

**Test Maturity Record** (`TMR`, `tmr-registry.json`):
The schema-validated record for one test case: identity (`tmr_uid`), current
coordinates (`test_id`, `user_story`), happy-path spine designation, maturity,
data/liveness classification, binding status, run evidence, and lineage. The local
system of record is `tmr-registry.json`; `tests-pseudo.md` is a prose view.
_Avoid_: treating Markdown test prose as authoritative once a TMR registry exists.

**Maturity Ladder** (`maturity`):
The lifecycle of a TMR: `nl` (natural-language intent) → `acceptance` (testable
contract with named accessors/observations) → `concrete` (bound implementation plus
green run evidence where required). The ladder is about evidence maturity, not
implementation priority.
_Avoid_: "stage" for this concept unless qualifying as "maturity stage".

**Liveness** (`live_or_induced`, `run_evidence`):
Proof that a critical seam has been exercised with real data or with a named,
constructible live/fault-induced technique. A mock is supplementary; it is not
liveness evidence unless the behavior is induced and the technique is recorded.
_Avoid_: counting unit-green or owner-written pass/fail prose as liveness.

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

**Test-Case Maturity Stage** (`stage:` field on a test case):
Legacy display wording for the Maturity Ladder on roadmap TC lines. Scoped to the
`(stage: …)` parenthetical; canonical TMR records use the `maturity` field.
_Avoid_: numbering these as bare "Stage 1/2/3" in prose — say "maturity stage `nl`" etc.

### Problems & feedback

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

**User-story morph** (`user-story morph`):
A spec revision (debate critique, gauntlet fold, arch reconcile, lookup resolution,
operator fork, cross-spec split) that **deletes / relocates / externalizes / absorbs /
splits / reframes** a capability, moving a user story's center of gravity while its
**anchor artifacts** (scope statement, coverage-map row, **happy-path spine test**) keep
pointing at the old center. The leak is *semantic, not lexical* — the orphaned
happy-path spine names the moved behavior, not any deleted identifier, so a plain
grep misses it. Fates: `Intact` / `Re-centered` / `Absorbed-Dissolved` / `Split`.
The canonical resolution flow + the `orphaned_spine` TCOV oracle live in
`reference/morph-reconciliation.md`.
_Avoid_: "stale test" (that is a stale *field name*; a morph is a stale *subject*).

### Debate & Gauntlet

**Debate**:
Phase 3 — the collaborative consensus loop: Opponents critique the spec in numbered
Rounds (R1, R2, …) until all models agree.
_Avoid_: "gauntlet" for this (the Gauntlet is hostile and is Phase 5).

**Critique**:
One Opponent's structured response within a debate Round; also the `debate.py` action
that runs a Round.
_Avoid_: "critique" for gauntlet output (that is a Concern); "attack" for debate
feedback.

**Opponent**:
A model participating in a Debate — a collaborative critic driving toward convergence.
_Avoid_: "adversary" for debate participants.

**Gauntlet**:
Phase 5 — the adversarial stress-test: Adversaries attack the spec and the surviving
output is Concerns. Implemented in the `gauntlet/` package; its seven *internal*
processing steps are historically named `phase_1_attacks` … `phase_7_final_boss` in
code — in prose, qualify as "gauntlet-internal phase N", never bare "Phase N" (which
is reserved for the pipeline).

**Adversary**:
A named hostile persona (e.g. PEDA, ASSH) that attacks the spec in the Gauntlet.
_Avoid_: "opponent" for gauntlet personas.

**Attack**:
A single Adversary run against the spec within the Gauntlet.
_Avoid_: "attack" for debate-round feedback (that is a Critique).

**debate.py**:
The multi-model dispatch CLI. Runs both the `critique` action (a debate Round) and the
`gauntlet` action; the name is historical — gauntlet logic lives in the `gauntlet/`
package, while the critique engine lives in the file itself.

### Pipeline structure

**Phase**:
One of the 8 pipeline phases: requirements → roadmap → debate → target-architecture →
gauntlet → finalize → execution → implementation. Reserved exclusively for the pipeline.
_Avoid_: "stage" or "step" for a pipeline phase; bare "phase" for the gauntlet's
internal processing steps (qualify: "gauntlet-internal phase N").

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

### Cards & tasks

**Task**:
A unit of planned work in an execution plan (`task_id: W0-1`), materialized 1:1 into a
Task Card at `pipeline_load`. Qualify as "plan task" only where the pre/post-load
distinction matters. fizzy's `*_task` tool names (`pipeline_do_next_task`,
`pipeline_complete_task`, …) are contract terms meaning Task Cards — never to be
"fixed."
_Avoid_: "task" for a TodoWrite item.

**Card**:
A Fizzy board object. Four contract kinds (`card_type`): **Session Card** (tracks one
Session through the lanes), **Task Card** (one plan task), and the middleware pair
(`middleware_impl`, `middleware_judge`). Bare "card" only where the kind is
unambiguous from context.

**TodoWrite item**:
The in-conversation checklist unit the skill uses for phase gates and progress
tracking.
_Avoid_: "task" or "todo task" for these — the skill's existing usage ("TodoWrite
item") is already uniform; keep it that way.

### Work identity

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

### Projects & infrastructure (MIRRORED VOCAB — canonical copy)

<!-- MIRRORED VOCAB: adversarial-spec ⟷ fizzy-pipeline-mcp. This section is
duplicated verbatim in fizzy-pipeline-mcp/CONTEXT.md. Conflicts resolve
definitively, never fork. Edits land HERE first (ownership ruling 2026-07-30:
adversarial-spec owns spec-system contracts; f-p-mcp mirrors). -->

**Fizzy** (`fizzy`):
The Rails board application itself — the browser-rendered UI at localhost:3001:
boards, cards, lanes, columns, and its REST API.
_Avoid_: bare "fizzy" for gates, MCP tools, sessions, or pipeline machinery (that is
fizzy-pipeline-mcp). "Fizzy board" stays legal for the board a pipeline runs on.

**fizzy-pipeline-mcp** (`f-p-mcp`):
The MCP server + pipeline FSM + v6 gates layered on Fizzy's REST API — the
enforcement arm of the adversarial-spec workflow.
_Avoid_: "fizzy's gates" / "fizzy tools" — the gates and tools belong to
fizzy-pipeline-mcp, not the board app.

### The "spec" family (MIRRORED VOCAB — canonical copy)

<!-- MIRRORED VOCAB: adversarial-spec ⟷ fizzy-pipeline-mcp; duplicated verbatim in
fizzy-pipeline-mcp/CONTEXT.md; edits land here first. -->

**Spec** (unqualified):
The session's normative specification — the artifact the pipeline is refining. Safe
unqualified only when context names the session.
_Avoid_: "the spec" for the gauntlet bundle, the target-architecture doc, or
requirements docs when more than one is in play.

**System spec** (`system-spec.md`):
The SYSTEM-altitude specification (numbered sections, completion contract,
supersession ledger); becomes a spec.v1 claims-registry document once the
spec-record format ships.

**Spec-as-gauntleted**:
The byte-pinned bundle a gauntlet fleet actually consumed — briefing + spec +
imports, hash-named (e.g. `spec-as-gauntleted-5d86227c.md`). Findings attribute to
the bundle, not the spec file.
_Avoid_: "the spec" for this bundle.

**Spec draft vN** (`spec-draft-v3.md`):
Debate-phase iteration artifacts, pre-finalize.

**Spec record** (`SPEC-CLAIM`):
One normative unit under the spec.v1 keystone contract: strict JSON metadata header
+ exact prose body. Post-adoption vocabulary.

### Work modes (MIRRORED VOCAB — canonical copy)

**Brainstorm**:
The out-of-pipeline hard-think mode: free-form written argument between models —
position, critique, and synthesis files exchanged on disk in the invoking project
(e.g. `orchestration/brainstorm-spec-structure/`) until convergence. No session
machinery, no protocol, no personas; "adversarial" is an attitude, not a structure.
Stays open until the work it governs ships, or closes at pipeline-entry when its
output becomes a session's requirements input.
_Avoid_: "debate" for a brainstorm (implies Phase-3 session machinery); "brainstorm"
for Phase 3 (undersells its gates and rounds).

### Postponement family (MIRRORED VOCAB — canonical copy)

**Exemption** (operator exemption):
An attested gate bypass: operator ruling + incident ref, recorded loudly in the gate
payload and card metadata; the gate's check is acknowledged-but-overridden this once.
Every use is an incident by convention.
_Avoid_: "exemption" for a deferral — a deferral bypasses nothing.

**Deferral**:
A recorded postponement with a named owner-phase: the obligation stays live and lands
somewhere specific later (e.g. seam deferral to Phase 8).
_Avoid_: "deferred" for watch-only items that carry no obligation.

**Residue**:
An explicitly carried unproven item riding forward INSIDE an artifact (e.g.
UNVALIDATED_ORACLE residue, RESIDUE-1), visible to every downstream consumer.
_Avoid_: "residue" for items parked outside the artifact.

**Watchlist**:
Watch-only: an observed gap recorded for pattern-forming, carrying NO obligation;
promoted to real work only on accumulated evidence or operator ruling.
_Avoid_: "watchlisted" for anything with an actual obligation attached.

Rule of thumb: exemption weakens a gate once; deferral schedules debt; residue labels
the product; watchlist just remembers.
