# Roadmap: Post-Fable Hardening — Skill Slice (G1 + G2 + G5)

> Draft v1 — 2026-07-07. Session `adv-spec-202607060132-post-fable-hardening-skill`, card 5857.
> Source: `docs/improvement-goals-2026-07.md` + confirmed RequirementsSummary (amended 2026-07-07).
> Root altitude: **system** (declared) — changes cut through phase docs, gates, debate engine, and registries.
> R1 debate revisions applied 2026-07-08 (Jason: all four): waiver story US-15, expanded personas,
> global KPIs (codex-style; gemini's ≤15KB context target REJECTED — contradicts no-size-caps amendment),
> G3 contract-boundary guardrail US-16, user-journey section.

### Personas

- **Jason — Lead Operator**: approves gates, grants waivers, redirects phases; remote-first via Telegram. Pain: manually auditing transcripts to see whether gates actually ran.
- **Integrator / New Maintainer** (human): sets up the toolchain, updates fixtures/schemas, evaluates candidate models. Pain: no first-run path from checkout to "verified ready."
- **Reviewer / Triager** (human or LLM): decides whether a blocked gate is valid; inspects evidence and waivers. Pain: reconstruction-from-transcript archaeology.
- **Conductor LLM** (Fable now; Opus/Sonnet post-Fable): runs phases from spine units; must stay competent on slimmer docs + mechanized gates.
- **Worker LLM** (codex/gemini/haiku): consumes cards, phase units, TMR registry; needs lean scoped context.
- **Candidate conductor models**: subjects of the M3 competence harness.

### User Journey (first mile → verified close)

1. A new maintainer clones the repo and runs the bootstrap command → ready / degraded / broken with named remediation (M0).
2. They run the competence harness against their candidate conductor before any live session (M3).
3. Mid-session, the conductor hits a mechanized gate violation → hard block with the gate id and fix; if genuinely exceptional, Jason grants a logged waiver (M1/US-15).
4. As debate sections converge they freeze; rounds shrink to the volatile surface (M7); every spec bump mechanically reconciles derived artifacts (M8).
5. After the Phase 8 sweep, verification cards derive from the TMR registry (M4); the promotion gate holds completion until run evidence lands (M5); Jason walks the ConOps script against the live system and the session closes with durable spine artifacts (M6).

### Global KPIs

- 100% of phase 01–09 gates inventoried and classified; **0 honor-system gates remain**.
- 100% of mechanized gates carry a failing-case test; 100% of judgment gates carry ≥1 golden fixture.
- 0 sessions reach `complete` with unrun critical-seam evidence absent an explicit logged waiver.
- 0 dirty derived-artifact diffs reach the gauntlet.
- Replay falsification: card-5715 R3/R7 both rejected; gateway-study replay blocked at the promotion gate.
- Frozen-section re-litigation occurs only with a named concern (registry-auditable).
- Debate-round reduction: baseline measured on this session; target set after baseline (no arbitrary % up front).
- Competence harness green under Sonnet and Opus baselines with a defined regression threshold.

### Goals

- **G1 Post-Fable operability**: every phase gate fires in code or has a named rubric+fixture; phase docs decomposed into discrete, well-organized units where each task loads exactly what it needs (no arbitrary size caps — Jason amendment 2026-07-07); conductor competence is measured by harness, not discovered mid-session.
- **G2 V-model ascending arm**: the pipeline owns the executable system spine — subsystem/system verification after the Phase 8 sweep, a pseudo→real promotion gate, and a ConOps walkthrough; a session structurally cannot reach `complete` with unrun critical-seam tests.
- **G5 Debate efficiency**: converged sections freeze, derived artifacts reconcile deterministically on every spec bump, and convergence claims survive a false-convergence guard — materially fewer rounds, zero derived-artifact drift reaching the gauntlet.

### Non-Goals

- **G3 fizzy-side contract reconciliation** — separate coordinated spec in the fizzy repo; this roadmap only *names* the contract deltas it depends on (see M4/M5 dependencies).
- **G4 dispatch reliability** — excluded entirely (Jason, alignment gate 2026-07-08). Gets its own session later; the confirmed RequirementsSummary is the scope contract.
- **mapcodebase/diagnosecodebase refresh** — deferred (Jason 2026-07-05); architecture-impact is assessed against the stale f198887 corpus with that caveat recorded.
- **Byte-count targets for phase docs** — explicitly amended out; organization quality is the criterion.

---

### Milestone 0: Getting Started (Bootstrap)

**User Stories:**
- US-0: As a post-Fable conductor LLM (or Jason), I want one bootstrap command that verifies the hardening toolchain — gate checks runnable, competence harness discoverable, reconciliation CLI present — so that I can confirm the environment works before a session starts.

**Success Criteria (Natural Language):**
- [ ] Single documented command; runs clean on a fresh clone in < 5 minutes
- [ ] Missing prerequisites produce named, actionable errors (which tool, which path)
- [ ] Exit code distinguishes ready / degraded / broken

**Test Cases:**
- TC-0.1: Bootstrap on healthy checkout reports ready, exit 0 (stage: nl) [happy-path spine seed]
- TC-0.2: Bootstrap with a missing harness fixture dir names the missing path, nonzero exit (stage: nl)

**Dependencies:** None (lands early, extended as M1/M3/M8 tools appear)

---

### Milestone 1: Gate Inventory & Mechanization (G1-F1)

**User Stories:**
- US-1: As Jason, I want every MUST/gate in phases 01–09 enumerated and classified — (a) already code-enforced, (b) mechanizable, (c) irreducibly judgment — so that no gate silently relies on conductor honor.
- US-2: As a conductor LLM, I want every class-(b) gate to fire in code (authoring-lint family, fizzy-side gate, or hook) so that I cannot skip it even under context pressure.
- US-3: As Jason, I want each class-(c) judgment gate distilled to a short checkable rubric with a golden-eval fixture so that judgment gates are auditable per the 3-tier verification convention.

**Success Criteria (Natural Language):**
- [ ] Inventory artifact lists every gate with classification + enforcement pointer (file:check or rubric id)
- [ ] Zero gates classified "honor-system" remain; each (b) gate has a failing-case test proving it fires
- [ ] Each (c) rubric has ≥1 golden fixture

**Test Cases:**
- TC-1.1: Inventory covers phases 01–09 with no unclassified gate (stage: nl) [happy-path spine seed]
- TC-1.2: A deliberately-violated mechanized gate blocks with a named error (stage: nl)
- TC-1.3: A judgment gate's fixture scores a known-bad transcript as fail (stage: nl)

- US-15: As Jason, I want an authorized waiver mechanism for any blocking gate (mechanized gate, promotion gate, ConOps close) — recording authority, justification, and affected evidence — so that exceptional sessions can proceed without re-legalizing the honor system.

**Success Criteria (Natural Language)** *(US-15 additions)*:
- [ ] Waiver requires named authority (Jason) + written justification; recorded durably with the gate id and affected artifacts
- [ ] Waivers are reviewable after the fact (audit trail); an unwaived block cannot be bypassed by any conductor action
- [ ] Waiver events surface in session close reports (no silent waivers)

**Test Cases** *(US-15 additions)*:
- TC-15.1: Waived gate proceeds with durable waiver record (stage: nl)
- TC-15.2: Conductor attempt to bypass without waiver is blocked and logged (stage: nl)

**Dependencies:** None

---

### Milestone 2: Phase-Doc Decomposition (G1-F2, amended)

**User Stories:**
- US-4: As a conductor LLM, I want each phase's operating spine decomposed into discrete, well-organized units — each loading exactly what the current task needs, no more, no less — so that I execute the critical path correctly without holding monolithic docs.
- US-5: As a worker LLM, I want on-demand reference units (rationale, origin stories, edge protocols) separated from the spine so that my card-scoped context stays lean.

**Success Criteria (Natural Language):**
- [ ] Every phase has a spine unit whose content is only orders-of-operation + exact commands + gate pointers
- [ ] Every extracted reference unit is reachable from the spine by explicit pointer (no orphaned content, verified mechanically)
- [ ] A conductor executing a phase touches only the units its current step names (spot-audited via transcript)
- [ ] No content deleted without a decision-log entry (moved ≠ deleted)

**Test Cases:**
- TC-2.1: Doclint proves spine↔reference pointer closure — no orphans, no dangling pointers (stage: nl) [happy-path spine seed]
- TC-2.2: A phase execution transcript shows only step-named units loaded (stage: nl)

**Dependencies:** M1 (inventory tells us which prescriptions are load-bearing before we move them)

---

### Milestone 3: Conductor Competence Harness (G1-F3)

**User Stories:**
- US-6: As Jason, I want a golden-eval set of "given this session state, what is the next action?" fixtures runnable against a candidate conductor model so that post-Fable degradation is measured before a live session, not discovered mid-session.

**Success Criteria (Natural Language):**
- [ ] Fixture set covers each phase's entry, gate, and failure-recovery decisions
- [ ] Harness runs against a named candidate model and emits a scored report
- [ ] Sonnet/Opus baseline runs recorded; regression threshold defined

**Test Cases:**
- TC-3.1: Harness scores a candidate model across all fixtures and emits report (stage: nl) [happy-path spine seed]
- TC-3.2: A fixture with a known-wrong next-action answer scores as fail (stage: nl)

**Dependencies:** M1 (rubrics for judgment gates become fixtures), M2 (spine units define the correct next actions)

---

### Milestone 4: System-Spine Verification Phases (G2-F1)

**User Stories:**
- US-7: As Jason, I want subsystem-verification and system-verification steps after the Phase 8 sweep, with a card set derived mechanically from `tmr-registry.json` (maturity < concrete, or missing `live_or_induced` evidence on critical seams), so that end-to-end seams are exercised before completion.

**Success Criteria (Natural Language):**
- [ ] Verification card set is derived by code from the TMR registry — never attested into existence
- [ ] Canonical phase order extended (or steps embedded in implementation) per resolved unknown U1
- [ ] Cards carry the seam, the TMR uid, and the required evidence class

**Test Cases:**
- TC-4.1: Registry with 3 sub-concrete critical-seam TMRs yields exactly 3 verification cards (stage: nl) [happy-path spine seed]
- TC-4.2: Registry with all-concrete/live TMRs yields an empty verification set and a recorded no-op (stage: nl)

- US-16: As an integration owner, I want every fizzy-side dependency of M4/M5 expressed as a named, versioned contract this slice *consumes* — never implements — so that scope cannot silently leak into the G3 slice.

**Success Criteria (Natural Language)** *(US-16 additions)*:
- [ ] A contract-boundary artifact names each required fizzy-side delta (lane, gate, schema field) with its G3 tracking pointer
- [ ] No task in this slice's execution plan touches the fizzy repo

**Test Cases** *(US-16 additions)*:
- TC-16.1: Contract-boundary artifact enumerates all fizzy deltas M4/M5 reference; execution-plan lint finds zero fizzy-repo file scopes (stage: nl)

**Dependencies:** M1 (gate classification); fizzy-side G3 contract for lanes (named via US-16, not built here)

---

### Milestone 5: Pseudo→Real Promotion Gate (G2-F2)

**User Stories:**
- US-8: As Jason, I want finalize/complete structurally blocked while critical-seam TMRs hold declared-only (unrun) evidence, so that promotion to run-evidence is a blocking lane, not a follow-up.

**Success Criteria (Natural Language):**
- [ ] Gate derives its verdict from `run_evidence` in the TMR registry — owner-written pass/fail prose does not count
- [ ] The gateway-study failure, replayed against the new pipeline, is caught at this gate
- [ ] Skip/deferred semantics defined (resolved unknown U2) with named authority to grant them

**Test Cases:**
- TC-5.1: Session with one declared-only critical-seam TMR cannot advance past finalize; gate names the TMR (stage: nl) [happy-path spine seed]
- TC-5.2: Same session after run-evidence lands advances cleanly (stage: nl)
- TC-5.3: Gateway 25-bug-ledger replay is blocked at the gate (stage: nl)

**Dependencies:** M4 (verification cards produce the run evidence the gate consumes)

---

### Milestone 6: ConOps Validation + Durable Spine Artifacts (G2-F3, G2-F4)

**User Stories:**
- US-9: As Jason (operator), I want a scripted walkthrough of the happy-path spine against the live system before session close — the manual live-fill gate generalized — so that operator-visible behavior is proven, not attested.
- US-10: As a worker LLM, I want durable node-registry / spine artifacts (per both process studies) so that fresh agents can locate the executable spine without transcript archaeology.

**Success Criteria (Natural Language):**
- [ ] Walkthrough script form defined (resolved unknown U3): steps, expected observations, captured evidence
- [ ] Session close blocked until walkthrough evidence recorded or explicitly waived by operator
- [ ] Spine artifacts survive session close and are consumed by the next session's bootstrap

**Test Cases:**
- TC-6.1: Completed walkthrough writes evidence artifact; session closes (stage: nl) [happy-path spine seed]
- TC-6.2: Missing walkthrough evidence blocks close with actionable message (stage: nl)

**Dependencies:** M5 (runs after promotion gate passes)

---

### Milestone 7: Settle/Freeze + Debate Node Registry (G5-F1, G5-F2)

**User Stories:**
- US-11: As a conductor LLM, I want converged spec sections marked frozen and excluded from re-critique unless a new concern names them, so that settled principles are not re-litigated (card-5715: 12 rounds, settled points reopened).
- US-12: As a conductor LLM, I want a durable debate node registry (settled / volatile / derived) so that round N+1 dispatches carry exactly the volatile surface.

**Success Criteria (Natural Language):**
- [ ] Freeze granularity + unfreeze trigger + enforcement point defined (resolved unknown U4)
- [ ] Round dispatch payload provably excludes frozen sections unless a named concern reopens them
- [ ] Registry persists across checkpoints and sessions

**Test Cases:**
- TC-7.1: Frozen section absent from round N+1 dispatch payload (stage: nl) [happy-path spine seed]
- TC-7.2: New concern naming a frozen section reopens exactly that section, with registry event (stage: nl)

**Dependencies:** None (debate-engine scoped)

---

### Milestone 8: Deterministic Reconciliation + False-Convergence Guard (G5-F3, G5-F4)

**User Stories:**
- US-13: As a conductor LLM, I want every spec version bump to mechanically re-diff derived artifacts (tests-pseudo, TMR registry, architecture invariants) before the next round, so that drift like the v9-schema tests-pseudo incident (R8/R11 rework) cannot reach the gauntlet.
- US-14: As Jason, I want convergence claims to require the anti-bare-AGREE press **plus** a clean derived-artifact diff — not just quorum — so that R3/R7-style false convergences are caught mechanically (resolved unknown U5).

**Success Criteria (Natural Language):**
- [ ] Reconciliation is code, not LLM judgment; a dirty diff blocks the next round with a named artifact
- [ ] Convergence with a dirty derived diff is rejected as false convergence
- [ ] Card-5715 R3 and R7 transcripts, replayed, are both flagged

**Test Cases:**
- TC-8.1: Spec bump with stale tests-pseudo blocks round dispatch, names the drifted artifact (stage: nl) [happy-path spine seed]
- TC-8.2: Quorum-AGREE with dirty derived diff is rejected as false convergence (stage: nl)
- TC-8.3: Card-5715 R3/R7 replay flags both false convergences (stage: nl)

**Dependencies:** M7 (node registry supplies the derived-artifact list)

---

### Architecture Impact

```json
{
  "architecture_impact": {
    "verdict": "new_components",
    "rationale": "The slice adds new component classes to the skill itself: a conductor-competence harness (golden-eval runner, no existing analog), a debate node registry with freeze/settle semantics consumed by the Debate Engine, a deterministic derived-artifact reconciliation gate, and TMR-derived verification-card emission. M2 restructures the phase-doc corpus (content architecture, not runtime). Existing Debate Engine, Gauntlet, and Emission Toolchain are extended, not replaced.",
    "new_components": [
      {"name": "conductor-competence harness", "kind": "cli", "extends": "new layer (golden-eval runner over fixtures/)"},
      {"name": "debate node registry", "kind": "model", "extends": "new persistent artifact class consumed by debate.py"},
      {"name": "derived-artifact reconciliation gate", "kind": "cli", "extends": "authoring-lint / gauntlet_check_cli.py family"},
      {"name": "verification-card derivation", "kind": "cli", "extends": "mini_spec_emission.py emission family, reads tmr-registry.json"},
      {"name": "gate inventory + mechanized checks", "kind": "cli", "extends": "authoring-lint family + .claude/hooks/"}
    ],
    "new_middleware": [],
    "new_vars_into_existing_middleware": [
      {"variable": "frozen-section exclusion set", "target_middleware": "debate.py round dispatch payload assembly", "purpose": "Exclude settled packets from re-critique (G5-F1)"},
      {"variable": "derived-diff clean flag", "target_middleware": "convergence check in debate.py", "purpose": "False-convergence guard requires clean reconciliation (G5-F4)"},
      {"variable": "promotion-gate verdict", "target_middleware": "finalize/complete advance path (pipeline_advance gates)", "purpose": "Block completion on declared-only critical-seam TMRs (G2-F2)"}
    ],
    "assessed_at": "2026-07-08T00:00:00Z",
    "assessed_against": "f198887 (STALE — corpus 50 commits behind b31f8fd; TMR/F-prime/validation-emission wave unmapped; refresh deferred per Jason 2026-07-05)"
  }
}
```

### Dependency Graph (summary)

M0 → (extended by M1/M3/M8 tooling)
M1 → M2 → M3
M1 → M4 → M5 → M6
M7 → M8
Cross-slice: M4/M5 name fizzy-side (G3) lane/contract deltas — coordinate, don't build.
