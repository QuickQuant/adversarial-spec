# ConOps: Validation-Leg Production Process

## Operational narrative
Session: adv-spec-202606110339-validation-leg-process
This ConOps is derived deterministically from roadmap manifest milestones and user stories.

## User stories (intent register)
### US-0: US-0
As a conductor agent entering Phase 7 of a system-altitude session, I want a single documented entry point so that I can run the validation leg end-to-end without reading fizzy source code.
Milestone: Getting Started (Bootstrap)

### US-1: US-1
As a conductor at Phase 7, I want to derive roadmap/conops.md from the roadmap manifest (user stories + operational narrative) so that validation binds to refreshed, post-debate intent.
Milestone: ConOps Derivation & Emission

### US-2: US-2
As the validator, I want the ConOps to read as operational intent, not a test inventory, so that my pass/fail judgments anchor on what was wanted.
Milestone: ConOps Derivation & Emission

### US-3: US-3
As a conductor at Phase 7 (pre-implementation), I want to draft >=1 validation row per user story (conops_ref, scenario, oracle, evidence_type) so that the gate's row schema is satisfiable and scenarios precede hindsight.
Milestone: Validation-Row Drafting (Phase 7)

### US-4: US-4
As the validator, I want every oracle to state how I judge pass/fail FROM INTENT (observable user-level outcome, never 'tests pass') so that rows cannot degrade into checkbox prose.
Milestone: Validation-Row Drafting (Phase 7)

### US-5: US-5
As a conductor, I want an evidence-type taxonomy (agent-walkthrough-transcript / artifact-demo / narrative) with per-type minimum bar and required per-row selection rationale, so that evidence matches what each scenario is of without requiring synchronous human participation (R1b gemini: renamed from live-walkthrough to make async explicit).
Milestone: Validation-Row Drafting (Phase 7)

### US-6: US-6
As the validator, I want one batched Telegram digest (scenario + oracle + evidence summary per row) so that I can judge the whole session from mobile in one interaction.
Milestone: Phase 8 Gate & Close

### US-7: US-7
As a conductor, I want a defined digest reply grammar (pass all | fail US-n: reason | na <row-id>: justification | mixed lines) parsed deterministically; N/A accepted only from Jason with justification, and ONLY at row level — an active ConOps story still requires >=1 passing row (coverage-gate constraint); removing a story is a ConOps edit + re-hash, never an N/A.
Milestone: Phase 8 Gate & Close

### US-8: US-8
As a conductor, I want to write system_validation.json and call mark_system_validation_complete with every gate error code mapped to a documented response, so that close is mechanical once judgments exist.
Milestone: Phase 8 Gate & Close

### US-9: US-9
As a conductor, I want fail results to spawn a remediation loop (cards -> fix -> re-exercise -> regenerate rows -> re-gate) so that failed validation blocks completion until resolved.
Milestone: Phase 8 Gate & Close

### US-10: US-10
As the project owner, I want THIS session (card 5604) to V-close through the new process so that it is proven on itself before any other session depends on it.
Milestone: Dogfood Close-Out

### US-11: US-11
As a conductor, I want a local self-check mirroring the gate's reject codes so that artifacts fail fast before any MCP call (dry-run/load symmetry).
Milestone: Phase 8 Gate & Close

### US-12: US-12
As a conductor, I want a controlled scenario-refresh rule — refresh only before Jason's final judgment or after a HUMAN-APPROVED remediation/scope decision (an agent may never approve its own scope reduction — R1b gemini); allowed reasons enumerated (approved story change, removed story, replaced workflow serving same intent, duplicate coverage); disallowed reasons enumerated (implementation failed, evidence missing, scenario inconvenient, prior negative judgment); superseded rows kept in an audit section with reason/approver/timestamp/replacement-id — so that legitimately obsolete Phase 7 rows can be replaced without hindsight rewriting (T1 resolution, R1 codex).
Milestone: Validation-Row Drafting (Phase 7)

### US-13: US-13
As a conductor at Phase 8 (post-implementation), I want to EXECUTE each drafted scenario and compile the captured evidence into a per-row evidence artifact BEFORE digest assembly, so that the digest is backed by real execution data, never mock assumptions or narrative-only filler (R1b gemini — closes the M2->M3 gap).
Milestone: Phase 8 Gate & Close
