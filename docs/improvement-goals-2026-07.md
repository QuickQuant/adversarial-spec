# Improvement Goals — July 2026 (post-Fable hardening)

*Drafted 2026-07-04 from a five-way investigation: `.architecture/` corpus audit,
session artifacts + all six process-failure reports, raw Claude JSONL transcripts
(adversarial-spec, prediction-prime, BracketBattleAI, wavelets), codex/gemini/GLM
workhorse logs, and Fizzy board history. Hand any goal back via `/goal <G-id>`.*

**Standing constraints (Jason, 2026-07-03):**
- Optimize for all four axes: post-Fable operability, V-model gap, dispatch reliability, debate efficiency.
- Fizzy repo is in full scope.
- **Dogfood the pipeline**: judgment-heavy design goes through an adversarial-spec session, not plan mode.
- All work on git branches for easy undo.
- No expensive multi-subagent ops (mapcodebase etc.) without per-instance OK.
- **~3 days of Fable access remain.** Spend Fable on design/debate/gauntlet judgment;
  implementation (codex/gemini workers) can outlive Fable.

---

## The evidence in one paragraph

The Phase 8 loop now works (liveness-gate wave: 22/22 cards, 3 agents, real review
catches, 891 green). The remaining failure mass sits in five classes:
(1) **verification theater at the seams** — components green while the end-to-end
path fails (prediction-prime "2 days and it's not up"; gateway 25-bug ledger); no
phase owns the executable system spine, no ascending V-model arm;
(2) **attest-instead-of-derive gates** — fizzy-side halves of the 12 seam holes still
open; (3) **debate inefficiency** — 12 rounds on card 5715, two false convergences,
derived-artifact drift; (4) **dispatch fragility** — thousands of timeouts/429s/stale
model names per big run, triple litellm pathway, dual CLI surfaces, two drifting
model registries; (5) **honor-system gates + 90K phase docs** that assume a frontier
conductor — the biggest post-Fable risk.

Key sources: `adversarial-spec-process-failure-report-pipeline-seams-20260530.md`,
`2026-05-30-vmodel-pipeline-shortcomings.md`,
`docs/reports/process-retrospectives/2026-06-18-gateway-live-execution-process-study.md`,
`docs/reports/process-retrospectives/2026-06-18-card-5715-process-study.md`,
`.adversarial-spec/sessions/adv-spec-202606151042-liveness-gate-test-ladder.decisions.log`,
`.architecture/concerns.md` (CON-001…009).

---

## G1 — Post-Fable operability: mechanize the honor system  *(highest leverage)*

**Problem.** Gate enforcement is explicitly "LLM-enforced, not runtime-validated"
(07-execution.md); phase docs have ballooned (04 = 90K, 07 = 76K, 03 = 54K) and
assume a conductor that can hold and faithfully apply all of it. Post-Fable
conductors (Opus/Sonnet) will drop prescriptions silently — the transcript history
shows even Fable-class conductors skipped steps until hooks/gates forced them.

**Deliverables.**
1. **Gate inventory + mechanization pass**: enumerate every MUST/gate in phases
   01–09; classify each as (a) already code-enforced, (b) mechanizable → write the
   check (extend `gauntlet_check_cli.py` / authoring-lint family, fizzy-side gate,
   or hook), (c) irreducibly judgment → distill into a short checkable rubric with a
   golden-eval fixture (per the 3-tier verification convention).
2. **Phase-doc restructure**: split each oversized phase doc into a lean operating
   spine (what to do, in order, with exact commands) + on-demand reference
   appendices. Target: conductor-critical path per phase readable in one context
   load. Origin-story rationale moves to reference files.
3. **Conductor competence harness**: a golden-eval set of "given this session state,
   what is the next action?" fixtures runnable against a candidate conductor model,
   so degradation is measured, not discovered mid-session.

**Success**: every phase gate either fires in code or has a named rubric+fixture;
no phase spine doc over ~25K; competence harness runs green under Sonnet/Opus.

## G2 — V-model ascending arm: own the executable system spine

**Problem.** Router goes execution → implementation → complete with only per-card
component verification. Declared-but-unrun REAL-DATA/critical-seam tests are treated
as backlog, not failing gates; nothing owns operator→…→exchange→…→UI end-to-end.
This is the class behind both the prediction-prime and gateway failures.

**Deliverables (design via dogfooded session — this is the judgment-heavy core).**
1. **System-spine phase(s)**: subsystem-verification and system-verification steps
   after Phase 8 sweep, gated on the TMR registry — a card set derived from
   `tmr-registry.json` entries whose `maturity` < concrete or whose
   `live_or_induced` evidence is missing on critical seams.
2. **Pseudo→real promotion gate**: a spec cannot finalize while critical-seam TMRs
   hold only declared (unrun) evidence — promotion to run-evidence is a blocking
   lane, not a follow-up.
3. **ConOps validation step**: a scripted operator walkthrough of the happy-path
   spine against the live system before session close (the manual live-fill gate
   generalized).
4. Node-registry / spine artifacts as recommended by both process studies.

**Success**: a session structurally cannot reach `complete` with unrun critical-seam
tests; the gateway-study failure replayed against the new pipeline is caught at the
promotion gate.

## G3 — Fizzy contract reconciliation (other half of shipped contracts)

**Problem.** Fizzy still mirrors skill ~v4; skill shipped v12. Open fizzy-side debt:
v9–v12 TMR deltas (tmr_uid, status, supersedes-array, technical_constraint,
run_evidence-union, live_or_induced tagged union, DR-8) per
`HANDOVER-reconcile-v4-to-skill-v12.md`; SEC-1 F-prime gauntlet-entry gate; seam
holes #1, #2, #5, #8, #10 (+ first-class `skip`/`deferred` enum). New seam found
2026-07-03: `pipeline_do_next_task` playbook names `next_call: pipeline_finalize`,
a tool that does not exist on the MCP surface (plain `pipeline_advance` is what
works) — audit playbook strings against the actual tool registry.

**Deliverables**: implement the handover in the fizzy repo; close the derive-not-
attest holes (`mapcodebase_fresh` derived from manifest-hash==HEAD, lane gates on
patch_state, concern-ID matching fix); playbook↔tool-surface parity check in fizzy CI.

**Success**: skill v12 and fizzy schemas byte-agree on the TMR contract; a
`pipeline_load`/`validate_plan` parity test exists; no playbook references a
nonexistent tool.

## G4 — Dispatch reliability: one pathway, one registry, graceful quota death

**Problem.** Biggest raw-volume friction. Triple `litellm.completion()` pathway with
divergent defaults (CON-001/FIND-001); two CLI surfaces with drifting flags/timeouts
(CON-007/FIND-017); two model registries (skill `providers.py` vs fizzy `agents.py`)
that Jason punted unifying ("no time", R9) and which caused the R9 404 outage;
quota deaths (gemini 21h, codex reset, haiku bookkeeper 429) each handled ad hoc;
`prompts.py` shadow collision (CON-009) already bit a live session.

**Deliverables**: single low-level `call_model` wrapper (kills FIND-014 duplication);
unify/alias the two CLI surfaces; one model registry consumed by both skill and
fizzy (or a generated mirror with a drift test); declarative fallback policy per
critic-family (quota-dead → named substitute, never claude-from-claude, flash
stub-AGREE handling); fix the prompts.py shadow (rename or package properly —
folds in CON-006 sys.path cleanup).

**Success**: one completion pathway; registry drift test in CI; a simulated
quota-death mid-debate resolves by policy without conductor improvisation.

## G5 — Debate efficiency: settle, freeze, reconcile deterministically

**Problem.** Card-5715: 12 rounds, spec grew 597→1181 lines, two false convergences
(R3, R7), settled principles re-litigated, derived artifacts (tests-pseudo) silently
drifted from the v9 schema causing R8/R11 rework.

**Deliverables**: (1) settled/frozen packet — converged sections marked frozen and
excluded from re-critique unless a new concern names them; (2) durable node
registry for debate topics (what's settled, what's volatile, what's derived);
(3) deterministic derived-artifact reconciliation gate — on every spec version bump,
diff derived artifacts (tests-pseudo, TMR registry, architecture invariants) against
the new version mechanically before the next round; (4) false-convergence guard —
convergence claims require the anti-bare-AGREE press plus a derived-artifact clean
diff, not just quorum.

**Success**: next full session converges in materially fewer rounds with zero
derived-artifact drift reaching the gauntlet.

---

## Execution shape (dogfooded)

- **One adversarial-spec session, two coordinated spec slices** (mirrors the
  liveness-gate pattern): *skill-side* (G1+G2+G5) and *fizzy-side* (G3), with G4
  as a mostly-mechanical workstream inside the skill slice (debated at contract
  level only — wrapper API, registry shape, fallback policy).
- **Fable-days plan**: Day 1 requirements/roadmap/debate; Day 2 gauntlet + finalize
  + Phase 7 execution plan; Day 3 begin Phase 8 with codex/gemini workers. The
  execution plan and TMR registry are the durable artifacts — Phase 8 can finish
  post-Fable, which is itself the first live test of G1.
- **Branching**: session work on `spec/post-fable-hardening` (skill repo) and a
  matching branch in fizzy; every card commits scoped per P8-2.
- **Deferred, needs explicit OK**: mapcodebase+diagnosecodebase refresh at HEAD
  (corpus is 50 commits stale; the TMR/F-prime/validation-emission wave is
  unmapped — worth running before the debate so opponents get fresh context).
