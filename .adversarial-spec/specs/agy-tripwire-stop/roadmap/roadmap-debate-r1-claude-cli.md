**Critique — Round 1**

The roadmap is strong on containment mechanics and weak on the humans in the loop. The stories cover the machine; the operator's journey after a STOP, and the orchestrator's routine round, are not covered. Two of the gaps are goal-alignment contradictions.

**CRITICAL 1 — Fail-closed unattributed halt fires on routine writes (G-2 vs G-1/usability).**
The watched surface is "every dirty/untracked delta in the caller's git root". This worktree's own git status right now shows `.claude/session-activity.jsonl` modified; Claude Code hooks append to it on every tool call, and `session-state.json` is rewritten by the skill mid-round. Under decision table row 4 each such append during an agy window is a shared-tree delta → T4 → STOPPED → durable record → every fresh process refuses until the operator clears. Implemented exactly as written, US-5 succeeds and the debate never completes. U-2 (halt fail-closed) is an operator decision and stands; what the roadmap does not do is (a) enumerate the routine writer classes that must be structurally excluded so the halt is rare, and (b) state a false-positive criterion. F-6 lists three tool-owned classes only. Nothing tests "a normal round with hook activity does not halt". Add a story, an exact-path exclusion registry (tested like TC-7.3), and a paired test.

**CRITICAL 2 — Round halt vs durable repo latch for `unattributed` is ambiguous.**
G-2 says the unattributed delta "halts the round". T4 says "write record" and T7 says a fresh process refuses. TC-5.0 asserts a halt but not a `stop_record`; TC-6.1 asserts a `stop_record` for the same attribution value. The two cases are indistinguishable by construction (that is the whole point of "unattributed"), so the design must pick one behaviour and say so. This is an unrecorded unknown, not a decided one. Record it as U-7 with a recommendation and get a ruling before debate closes.

**CRITICAL 3 — The operator's journey ends at the STOP.**
The operator persona is "sole authority to clear; needs evidence sufficient to decide". There is no story for: learning that a STOP happened (stderr of a background gauntlet driven by an agent is read by nobody; the Telegram bridge exists and is unmentioned), reading the evidence, restoring by hand, or performing the clear. TC-4.2 asserts "a clear entry is recorded" without defining what the act is. "Flag default" is named as a non-operator path but an explicit flag is not distinguished from it. "Evidence sufficient to restore by hand" is a success criterion with no oracle — no test ever restores from an incident record and checks bytes. Add US-9 (clear), US-10 (notification/evidence), TC-4.5 (restore-from-evidence round-trip).

**CRITICAL 4 — "Per watched repository" is undefined in a worktree ecosystem.**
This session runs in `adversarial-spec.worktrees/agy-tripwire-fix`. Git worktrees share a common dir. Does a STOP in one worktree block a sibling worktree? U-3 says per repo; the tests use one flat temp repo each and never a worktree. TC-4.1 must gain a worktree variant and the record location must be defined (toplevel vs common dir). Record as U-8.

**HIGH — Test with two outcomes.** TC-2.1 says "quarantined … (or terminated by PID)". A test cannot have an "or". U-4 must be ruled before roadmap acceptance, or TC-2.1 is marked `blocked_on: U-4` with both variants written.

**HIGH — 5-minute suite budget contradicts the timeout tests.** TC-6.2 negative needs MAX_RETRIES timeouts; TC-2.1 needs an overlapping sleep. Unless the dispatch timeout is injectable the suite cannot meet US-0. State the injectability as an M0 success criterion.

**HIGH — "No control flow depends on string matching" has no oracle.** TC-1.3 proves the STOP survives a broad catch; nothing proves independence from message text. Add TC-1.4: the fake critic's STOP message is randomised per run; behaviour unchanged.

**MEDIUM — Persona coverage.** Four user types listed, stories exist for two and a half. "Future maintainers … must not be able to reopen the retry path" has a test (TC-1.3) but no story. "Consuming projects" is a deployment context; the real person is the co-tenant session owner whose dispatch gets refused by someone else's STOP. They need the refusal to name the incident so they do not retry blindly (TC-4.0 asserts it; no story owns it).

**MEDIUM — No Risks section, no post-repair endpoint.** The roadmap has neither risks nor mitigations. The journey's "productive user" endpoint — the operator lifting the dispatch ban after the landed repair — is out of scope but must be named as a handoff with the evidence the operator will need (U-1 residue included), otherwise M4 delivers a document into a void.

**LOW — Complexity score says 0 external integrations.** The Antigravity CLI is an external binary and U-1 exists precisely because its behaviour is unknown. Count it as 1; the score moves to 16 and stays `complex`.

Non-goals, scope, and the remaining stories are well formed. Revised roadmap follows; Appendix A carries forward unchanged by reference.

[SPEC]
# Roadmap: AGY Tripwire Stop — critic safety contract repair

Session `adv-spec-202609240523-agy-tripwire-stop` · card 21616 · altitude **system** ·
complexity **complex** (score 16 = 4 user types + 7 feature groups + 1 external integration (Antigravity CLI, behaviour unproven per U-1) + 4 open unknowns).
Requirements: `../requirements.md` (confirmed 2026-09-24; U-2 and U-3 decided by operator).
Tests (canonical): `../tests-pseudo.md` (v2; see Appendix B delta).

### Goals
- G-1 A real critic mutation is still detected, its evidence is captured, the critic-owned delta is restored, and the run halts.
- G-2 No writer's bytes are destroyed on the strength of a timing guess. A delta that cannot be structurally attributed to the critic is preserved, recorded as `unattributed`, and halts the round fail-closed (U-2).
- G-3 A STOP is terminal. It triggers no retry, synthesis, round checkpoint, or sibling spawn, and no further Antigravity dispatch, preflight included. That holds in the stopping process and in any fresh process against the same watched repository, until an explicit operator clear (U-3).
- G-4 An offline regression suite proves G-1..G-3 with paired negative oracles. It needs no network and no live critic.
- G-5 Landing on the user-owned dirty live tree is a named, operator-approved gate, and that gate proves no user hunk is overwritten.
- G-6 A normal round is not halted by the tool's own routine writes. Every writer class the skill, its hooks, or its checkpoint machinery produces during a window is structurally excluded by exact path, and a realistic round with that activity completes with zero unattributed halts.
- G-7 The operator can act on a STOP without reading source: they are told it happened, can read the evidence, can restore bytes from it, and can clear it with one recorded act.

### Non-Goals
- Resuming, mutating, or completing `adv-spec-202607060132-post-fable-hardening-skill`, or anything in the Brainquarters Jev session.
- Editing `/home/jason/PycharmProjects/adversarial-spec`, `~/.claude/skills/adversarial-spec`, deploying, committing or pushing without explicit integration approval.
- Any Antigravity dispatch (preflight included) before the repaired contract lands and the operator clears it. Lifting that ban is a separate operator act; this session delivers the evidence for it (see "Handoff at completion"), not the act.
- Weakening real-mutation containment, hiding attribution uncertainty, string-matching as the sole stop protocol, broad model-routing changes, secrets/config edits, global process kills.
- Repairing fizzy-pipeline-mcp's own agy runner (U-6; recorded as residue for that repo).
- Overturning U-2 or U-3. This roadmap refines their consequences (U-7, U-8); it does not reopen them.

### Personas
- **Operator (Jason)** — sole clearing authority. Works from a phone or a different terminal much of the time; learns of STOPs via the Telegram bridge or the next command's refusal, not by watching stderr.
- **Orchestrator agent** — the Claude/Codex/Gemini seat running a debate or gauntlet. Writes critiques, session state, and partial results into the same worktree while critics run. Its hooks append to `.claude/session-activity.jsonl` on every tool call.
- **Co-tenant session owner** — another Claude Code session with in-flight work in the same watched repository. Gets refused by a STOP it did not cause; needs to know why.
- **Future maintainer** — adds code around dispatch later and must not be able to reopen the retry path by accident.

### Operator journey (STOP to productive)
1. A STOP fires in a debate or gauntlet run. The run exits with the STOP code and names the incident path.
2. The operator is told (Telegram bridge when configured; otherwise the next dispatch attempt refuses and names the incident).
3. The operator reads the incident record: attribution, mutated paths, pre/post bytes, critic streams.
4. If bytes must be restored, the operator restores from the record and verifies.
5. The operator performs the one documented clear act; the act is recorded with who/when/which incident; evidence is untouched.
6. Dispatch resumes in that repository only.

### Milestone 0: Getting Started (Bootstrap)
**User Stories:**
- US-0: As a maintainer, I want one offline command that runs the agy-safety regression suite against a fake critic so that I can verify the contract without network, credentials, or a live Antigravity dispatch.

**Success Criteria:**
- [ ] One documented command runs the suite from a clean checkout in under 5 minutes.
- [ ] The suite refuses to run if the real `agy` binary would be reached. The fake-critic guard checks a marker the fake emits, not the binary's name.
- [ ] The dispatch timeout and MAX_RETRIES are injectable for tests, so timeout scenarios fit the budget.
- [ ] The failure output names the scenario (SC-n) that broke.

**Test Cases:** TC-0.0 (spine), TC-0.1, TC-0.2. **Dependencies:** None

### Milestone 1: STOP is terminal inside one process
**User Stories:**
- US-1: As the operator, I want a STOP raised during a debate critique to end that round with a distinct outcome, with no retry and no synthesis, so that no critic dispatch follows a STOP-class event.
- US-2: As the operator, I want a STOP in any gauntlet attack or later gauntlet-internal phase to block every not-yet-started Antigravity spawn in that run and record a stop status, so that parallel siblings cannot keep dispatching.
- US-3: As the operator, I want the preflight ping treated as a real dispatch. It must honour the round's working directory, obey the stop latch, and surface a STOP as a STOP, so that the "cheap" ping cannot bypass the contract.
- US-11: As a future maintainer, I want a STOP to be a signal that a generic "catch any error and continue" block cannot absorb, so that adding a new catch site later cannot reopen the retry path.

**Success Criteria:**
- [ ] After a STOP, the fake critic's spawn count stays at the pre-STOP value on every path (retry, sibling, later phase, preflight).
- [ ] Non-mutation failures (non-zero exit, empty output, clean timeout) keep today's bounded retry.
- [ ] Stop handling does not depend on message text: randomising the STOP message per run changes nothing observable except the message.
- [ ] Already-running siblings at STOP time behave per the U-4 ruling, which is recorded before this milestone's tests are promoted to `acceptance`.

**Test Cases:** TC-1.0 (spine) … TC-3.3, plus TC-1.4. **Dependencies:** M0; U-4 ruled

### Milestone 2: STOP survives the process
**User Stories:**
- US-4: As the operator, I want a fresh process against the same watched repository to refuse any Antigravity dispatch, preflight included, until I clear the recorded STOP, so that restarting a script cannot silently resume dispatch.
- US-9: As the operator, I want one documented clear act that records who, when, and which incident, and that never deletes evidence, so that clearing is deliberate, auditable, and cheap enough that I do not work around it.
- US-10: As a co-tenant session owner, I want a refusal caused by someone else's STOP to name the incident, the record path, and the clear act, so that I do not retry blindly or delete the record to get unstuck.

**Success Criteria:**
- [ ] A STOP leaves a durable record inside the watched repository that references its incident evidence. The record's location is defined for plain checkouts and for git worktrees (U-8), and it is excluded from the repo's tracked set.
- [ ] Every entry point checks the record before spawning and refuses while it is present, and the refusal message names record, incident, and the clear act.
- [ ] Only the explicit, recorded operator act clears it. A flag default, a retry, or a new round does not. Clearing never deletes the incident evidence.
- [ ] The incident record is sufficient to restore bytes by hand: a test restores from it and gets byte-identical files.
- [ ] A different repository is not blocked (U-3 scope). Worktree behaviour matches the U-8 ruling.

**Test Cases:** TC-4.0 (spine) … TC-4.4, plus TC-4.5, TC-4.6. **Dependencies:** M1; U-7 and U-8 ruled

### Milestone 3: Structural attribution and non-destructive containment
**User Stories:**
- US-5: As an orchestrator agent, I want my own writes, Codex's writes, and the tool's checkpoint writes into the shared worktree during an agy window never deleted or overwritten, and never labelled as critic-authored, so that concurrent work survives and the incident record is truthful.
- US-6: As the operator, I want a critic write inside its own dispatch-private surface to be captured, restored, and turned into a STOP labelled `critic`, including when the dispatch times out, so that genuine mutations stay contained.
- US-7: As the operator, I want tool-owned scratch never reported as a mutation and never visible inside a sibling dispatch's window. That covers oversized-prompt files, incident evidence, and partial checkpoints. I want this so that concurrent dispatches cannot blame or delete each other's files.
- US-12: As an orchestrator agent, I want a normal round, with hook log appends and session-state rewrites happening while the critic runs, to complete without an unattributed halt, so that the safety contract does not make the debate unusable.

**Success Criteria:**
- [ ] The shared-tree sensor only records. It never unlinks, overwrites, or runs `git checkout` on a watched path.
- [ ] Each incident record states its attribution (`critic` or `unattributed`) and carries pre-state and post-state bytes sufficient to restore by hand.
- [ ] The timeout path runs the same check as the return path, and does so before the timeout is reported.
- [ ] Tool-owned exclusions are an explicit exact-path registry covering at least: partial checkpoints, incident evidence, prompt scratch, the stop record, `session-state.json`, and the hook activity log. Lookalike paths are not excluded.
- [ ] The delta oracle is defined (status-set diff plus content hash of pre-dirty files) so that an edit to an already-dirty file is detected and an unchanged dirty file is not.
- [ ] A realistic round with background hook and session-state writes produces zero halts; the same round with one non-registry write produces exactly one unattributed halt.

**Test Cases:** TC-5.0 (spine) … TC-7.3, plus TC-5.4, TC-7.4. **Dependencies:** M1 (STOP type), independent of M2

### Milestone 4: Deliberate integration
**User Stories:**
- US-8: As the operator, I want a reconciliation plan that lands the repair onto the dirty `bounded-pipeline-reform` tree through an explicit approval gate, and that proves every pre-existing user hunk survives, so that no unrelated user change is overwritten.

**Success Criteria:**
- [ ] The plan names the gate, the approver, the exact order of operations, rollback, and the before/after hunk-preservation check.
- [ ] Nothing is applied to the live tree before approval.
- [ ] The plan states where the patch lives until approval (this worktree's branch) and what the operator needs in hand to lift the dispatch ban afterwards (see handoff).

**Test Cases:** TC-8.0 (spine), TC-8.1. **Dependencies:** M1–M3 green

### Handoff at completion
This session ends with: the patch on this worktree, the green offline suite, the reconciliation plan, and a residue list (U-1, U-6). Lifting the Antigravity dispatch ban is the operator's act, taken after the landed repair, using a first live dispatch against a throwaway repo as the U-1 probe. That act is outside this session and is named here so the journey has an end.

### Scenario → story map (handoff acceptance criterion 2)
| Scenario | Story | Spine / variant |
|---|---|---|
| SC-1 real critic mutation | US-6 | TC-6.0 |
| SC-2 non-critic shared write | US-5 | TC-5.0 |
| SC-3 timeout | US-6 | TC-6.2 (spine_of TC-6.0, step S1) |
| SC-4 parallel/sibling | US-2, US-7 | TC-2.0, TC-7.2 |
| SC-5 oversized-prompt scratch | US-7 | TC-7.0 |
| SC-6 preflight | US-3 | TC-3.0 |
| SC-7 fresh process after STOP | US-4 | TC-4.0 |
| SC-8 routine tool writes in a normal round (new) | US-12 | TC-5.4 |
| SC-9 operator clear and restore (new) | US-9, US-10 | TC-4.5, TC-4.6 |

### Success metrics
- Destroyed non-critic bytes across the suite: 0.
- Spawns after any STOP, on any path: 0.
- Unattributed halts in the realistic-round test (TC-5.4 positive): 0; in its paired negative: exactly 1.
- Restore-from-evidence round-trip: byte-identical.
- Suite wall time from clean checkout: under 5 minutes, offline.

### Risks and mitigations
| Risk | Effect | Mitigation |
|---|---|---|
| False-positive halts from routine writers brick the pipeline | Operator clears constantly or bypasses the contract | G-6, exact-path registry, TC-5.4 with realistic hook activity |
| Unattributed halt scoped wrongly (round vs repo) | Either too weak (critic via absolute path resumes) or too strong (every co-tenant write latches the repo) | U-7 ruling before M2; both variants in tests until ruled |
| Worktree scoping ambiguity | STOP in one worktree silently blocks or fails to block siblings | U-8 ruling; TC-4.6 |
| Agy cannot read a prompt from a non-git private workspace (U-1) | Private-surface design unprovable offline | Residue with a named live probe in the handoff |
| Landing onto dirty live tree conflicts | User hunks lost | M4 gate, TC-8.0 on a copy |
| Timeout tests blow the suite budget | US-0 fails | Injectable timeout/MAX_RETRIES (M0) |

### Architecture impact
`extends_existing`. All new contracts live inside the existing models/providers, debate/session, and gauntlet components; there is no new layer or service. The new contracts are a typed stop signal, a dispatch latch, a per-repo stop record with a defined location rule, an incident attribution field, and a tool-owned path registry. See `manifest.json#architecture_impact`.

### Open unknowns carried into debate
- U-1 agy reading a prompt from a non-git private workspace cannot be proven live while dispatch is forbidden.
- U-4 siblings already running at STOP time: quarantine output or terminate by PID. Must be ruled before M1 tests promote.
- U-5 landing order onto the dirty tree.
- U-6 fizzy runner residue.
- U-7 (new) does an `unattributed` halt write the durable per-repo stop record, or only halt the round and set the in-process latch? Recommendation: durable, because TC-6.1 (critic via absolute path) is indistinguishable from TC-5.0 and is the real threat; make false positives rare via G-6 and the clear act cheap via US-9. Operator ruling required.
- U-8 (new) "watched repository" for git worktrees: scope by worktree toplevel or by common dir? Recommendation: common dir, since the critic's cwd-relative writes can land in any checkout of the same repo only via absolute path, but the operator's mental model is "this repo". Operator ruling required.
- U-9 (new) operator notification channel for a STOP in an agent-driven background run: Telegram bridge when configured, else refusal-on-next-dispatch only.
- Operator-clear UX (from U-3): now carried by US-9; the concrete act (command vs file) is decided in debate.

---

# Appendix B — Test pseudocode delta (v2)

All TC-x.y from v1 carry forward unchanged unless listed here. New accessors: `notify` (bridge message log, fake), `registry` (tool-owned exact-path list).

### TC-0.2: Timeout and retry bounds are injectable [spine_of: TC-0.0, spine_step_ref: S1]
**Data Strategy: REAL-DATA** — real suite run with injected 2s timeout.
```
given: suite run with timeout=2s, MAX_RETRIES=2
assert: TC-6.2 and TC-2.1 complete; total wall time < 5 min
negative: with the production timeout the same two cases are skipped with a named reason, never silently passed
```

### TC-1.4: STOP does not depend on message text [spine_of: TC-1.0, spine_step_ref: S2]
**Data Strategy: MOCK-EXTERNAL** — scope: Antigravity critic. why_impossible_to_reproduce_live: operator dispatch ban.
```
given: the STOP message is randomised per run (unique token, no "STOP"/"mutation" substrings)
when:  the critic mutates
assert: exit_code == STOP code; spawns == 1; stderr contains the token
negative: a non-mutation failure whose stderr contains the literal text of a real STOP message is retried normally
```

### TC-2.1: Already-running sibling at STOP time [spine_of: TC-2.0, spine_step_ref: S3] — REVISED
`blocked_on: U-4`. Two variants written; exactly one is active after the ruling.
```
variant Q (quarantine): #2 returns; output stored under incident, not synthesized; no concern extracted
variant K (kill):       #2 terminated by its own PID only; no other process signalled; its partial output stored under incident
both: no new spawn after #1's STOP
```

### TC-4.5: Restore from evidence is sufficient [spine_of: TC-4.0, spine_step_ref: S4]
**Data Strategy: REAL-DATA** — real incident record produced by TC-5.0/TC-6.1.
```
given: an incident record with pre/post bytes for N and D
when:  the documented restore procedure is followed using only the record
assert: tree_bytes(N), tree_bytes(D) == pre-state bytes, byte-identical
negative: a record with a missing pre-state file is reported as insufficient, not silently partial
```

### TC-4.6: Worktree scoping per U-8 [spine_of: TC-4.0, spine_step_ref: S3]
**Data Strategy: REAL-DATA** — one real repo with two real `git worktree add` checkouts.
```
given: stop_record produced in worktree W1
when:  a critique targets worktree W2 of the same repo
assert: per U-8 ruling — common-dir: spawns == 0; toplevel: spawns == 1. Exactly one branch is active after the ruling.
```

### TC-4.0 addendum — refusal names the clear act
```
assert: process 2's stderr names the record path, the incident path, and the documented clear command
```

### TC-4.2 addendum — explicit flag vs flag default
```
when:  the clear flag is passed explicitly with an incident id → clear recorded
when:  the flag's default value is in effect → refused
```

### TC-5.4: Routine tool writes never halt a normal round [spine_of: TC-5.0, spine_step_ref: S3]
**Data Strategy: REAL-DATA** — real repo with a real dirty `.claude/session-activity.jsonl` and `session-state.json`; a background writer appends to the log and rewrites session state every 200 ms during the fake critic's sleep.
```
given: registry contains both paths exactly
when:  debate critique runs with a clean fake critic
assert: response returned; no incident; no stop_record; exit_code == 0
negative: same run plus one write to a path not in the registry → exactly one unattributed halt (TC-5.0 outcome)
```

### TC-7.4: Registry is exact and enumerated [spine_of: TC-7.0, spine_step_ref: S3]
**Data Strategy: STATIC** — registry inspection plus TC-7.3 behaviour.
```
assert: registry lists partial checkpoints, incident evidence, prompt scratch, stop record, session-state.json, hook activity log
assert: a path that prefix-matches a registry entry but differs by suffix is treated as unattributed (TC-7.3)
```

### State Transition Table — additions
| # | From | Event | To | Action | Test |
|---|---|---|---|---|---|
| T4 | CLEAR | shared-tree delta | STOPPED (per U-7) | capture, NO revert, STOP unattributed, record per U-7 | TC-5.0, TC-6.1 |
| T5 | CLEAR | registry-path write only | CLEAR | ignore | TC-5.1, TC-5.4, TC-7.0 |
| T10 | STOPPED | dispatch from sibling worktree | per U-8 | refuse or proceed | TC-4.6 |
[/SPEC]