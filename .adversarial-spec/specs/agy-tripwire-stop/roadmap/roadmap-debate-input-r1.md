# Roadmap: AGY Tripwire Stop — critic safety contract repair

Session `adv-spec-202609240523-agy-tripwire-stop` · card 21616 · altitude **system** ·
complexity **complex** (score 15 = 4 user types + 7 feature groups + 0 external integrations + 4 open unknowns).
Requirements: `../requirements.md` (confirmed 2026-09-24; U-2 and U-3 decided by operator).
Tests (canonical): `../tests-pseudo.md`.

### Goals
- G-1 A real critic mutation is still detected, its evidence is captured, the critic-owned delta is restored, and the run halts.
- G-2 No writer's bytes are destroyed on the strength of a timing guess. A delta that cannot be structurally attributed to the critic is preserved, recorded as `unattributed`, and halts the round fail-closed (U-2).
- G-3 A STOP is terminal. It triggers no retry, synthesis, round checkpoint, or sibling spawn, and no further Antigravity dispatch, preflight included. That holds in the stopping process and in any fresh process against the same watched repository, until an explicit operator clear (U-3).
- G-4 An offline regression suite proves G-1..G-3 with paired negative oracles. It needs no network and no live critic.
- G-5 Landing on the user-owned dirty live tree is a named, operator-approved gate, and that gate proves no user hunk is overwritten.

### Non-Goals
- Resuming, mutating, or completing `adv-spec-202607060132-post-fable-hardening-skill`, or anything in the Brainquarters Jev session.
- Editing `/home/jason/PycharmProjects/adversarial-spec`, `~/.claude/skills/adversarial-spec`, deploying, committing or pushing without explicit integration approval.
- Any Antigravity dispatch (preflight included) before the repaired contract lands and the operator clears it.
- Weakening real-mutation containment, hiding attribution uncertainty, string-matching as the sole stop protocol, broad model-routing changes, secrets/config edits, global process kills.
- Repairing fizzy-pipeline-mcp's own agy runner (U-6; recorded as residue for that repo).

### Milestone 0: Getting Started (Bootstrap)
**User Stories:**
- US-0: As a maintainer, I want one offline command that runs the agy-safety regression suite against a fake critic so that I can verify the contract without network, credentials, or a live Antigravity dispatch.

**Success Criteria (Natural Language):**
- [ ] One documented command runs the suite from a clean checkout in under 5 minutes.
- [ ] The suite refuses to run if the real `agy` binary would be reached (fake-critic guard).
- [ ] The failure output names the scenario (SC-n) that broke.

**Test Cases:** TC-0.0 (spine), TC-0.1. **Dependencies:** None

### Milestone 1: STOP is terminal inside one process
**User Stories:**
- US-1: As the operator, I want a STOP raised during a debate critique to end that round with a distinct outcome, with no retry and no synthesis, so that no critic dispatch follows a STOP-class event.
- US-2: As the operator, I want a STOP in any gauntlet attack or later gauntlet-internal phase to block every not-yet-started Antigravity spawn in that run and record a stop status, so that parallel siblings cannot keep dispatching.
- US-3: As the operator, I want the preflight ping treated as a real dispatch. It must honour the round's working directory, obey the stop latch, and surface a STOP as a STOP, so that the "cheap" ping cannot bypass the contract.

**Success Criteria:**
- [ ] After a STOP, the fake critic's spawn count stays at the pre-STOP value on every path (retry, sibling, later phase, preflight).
- [ ] Non-mutation failures (non-zero exit, empty output, clean timeout) keep today's bounded retry.
- [ ] Stop handling does not depend on matching message text.

**Test Cases:** TC-1.0 (spine) … TC-3.3. **Dependencies:** M0

### Milestone 2: STOP survives the process
**User Stories:**
- US-4: As the operator, I want a fresh process against the same watched repository to refuse any Antigravity dispatch, preflight included, until I clear the recorded STOP, so that restarting a script cannot silently resume dispatch.

**Success Criteria:**
- [ ] A STOP leaves a durable record inside the watched repository that references its incident evidence.
- [ ] Every entry point checks the record before spawning and refuses while it is present.
- [ ] Only an explicit, recorded operator act clears it. Clearing never deletes the incident evidence.
- [ ] A different repository is not blocked (U-3 scope).

**Test Cases:** TC-4.0 (spine) … TC-4.4. **Dependencies:** M1

### Milestone 3: Structural attribution and non-destructive containment
**User Stories:**
- US-5: As an orchestrator agent, I want my own writes, Codex's writes, and the tool's checkpoint writes into the shared worktree during an agy window never deleted or overwritten, and never labelled as critic-authored, so that concurrent work survives and the incident record is truthful.
- US-6: As the operator, I want a critic write inside its own dispatch-private surface to be captured, restored, and turned into a STOP labelled `critic`, including when the dispatch times out, so that genuine mutations stay contained.
- US-7: As the operator, I want tool-owned scratch never reported as a mutation and never visible inside a sibling dispatch's window. That covers oversized-prompt files, incident evidence, and partial checkpoints. I want this so that concurrent dispatches cannot blame or delete each other's files.

**Success Criteria:**
- [ ] The shared-tree sensor only records. It never unlinks, overwrites, or runs `git checkout` on a watched path.
- [ ] Each incident record states its attribution (`critic` or `unattributed`) and carries pre-state and post-state bytes sufficient to restore by hand.
- [ ] The timeout path runs the same check as the return path, and does so before the timeout is reported.

**Test Cases:** TC-5.0 (spine) … TC-7.3. **Dependencies:** M1 (STOP type), independent of M2

### Milestone 4: Deliberate integration
**User Stories:**
- US-8: As the operator, I want a reconciliation plan that lands the repair onto the dirty `bounded-pipeline-reform` tree through an explicit approval gate, and that proves every pre-existing user hunk survives, so that no unrelated user change is overwritten.

**Success Criteria:**
- [ ] The plan names the gate, the approver, the exact order of operations, and the before/after hunk-preservation check.
- [ ] Nothing is applied to the live tree before approval.

**Test Cases:** TC-8.0 (spine), TC-8.1. **Dependencies:** M1–M3 green

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

### Architecture impact
`extends_existing`. All new contracts live inside the existing models/providers, debate/session, and gauntlet components; there is no new layer or service. The new contracts are a typed stop signal, a dispatch latch, a per-repo stop record, and an incident attribution field. See `manifest.json#architecture_impact`.

### Open unknowns carried into debate
U-1 (agy reading a prompt from a non-git private workspace cannot be proven live while dispatch is forbidden), U-4 (siblings already running at STOP time), U-5 (landing order onto the dirty tree), U-6 (fizzy runner residue), and the operator-clear UX left open by U-3.


---

# Appendix A — RequirementsSummary

# RequirementsSummary — AGY Tripwire Stop

Session `adv-spec-202609240523-agy-tripwire-stop` · card 21616 · altitude `system` · doc `spec/technical`.
Input authority: operator handoff `orchestration/handoff-agy-tripwire-repair.md`; evidence from the
Brainquarters incident (2026-09-24) and the two read-only review reports. Interview: not run —
the handoff is the operator's requirements statement; gaps are listed as unknowns below.

## Problem (evidence)
- Attribution is timing-only: every dirty/untracked delta in the caller's git root during an agy
  window is blamed on the critic (`scripts/models.py:645-663`), reverted by overwrite or `unlink`
  (`:691-703`). Incident: the orchestrator's own 2,519-byte critique was deleted.
- STOP is an ordinary `RuntimeError` (`:706-713`); the agy branch of `call_single_model` catches every
  `Exception` and re-dispatches up to `MAX_RETRIES` (`:1161-1174`). Incident: attempt 2 ran after STOP.
- After retries the STOP survives only as `ModelResponse.error` text; `debate.py:1184-1191` warns and
  continues to synthesis/checkpoint writes. Preflight swallows it into a string (`models.py:1312-1313`)
  and `debate.py:1665-1667` does not forward `--cwd`.
- Tool writes inside the window (`_save_partial_result`, `models.py:1391-1426`) and co-tenant Codex
  (`workspace-write`, same cwd) are indistinguishable from critic writes.

## User types
- **Orchestrator agent** (Claude/Codex/Gemini seat running a debate or gauntlet) — writes into the same
  worktree while critics run; must never lose bytes or be blamed.
- **Operator (Jason)** — sole authority to clear a STOP; needs evidence sufficient to decide.
- **Consuming projects** (Brainquarters, fizzy-pipeline-mcp, …) — dirty shared worktrees with other
  sessions' in-flight work.
- **Future maintainers** — must not be able to reopen the retry path by adding a new catch site.

## Scenario outcomes (each becomes a spec requirement with a paired negative oracle)
| ID | Scenario | Required outcome |
|---|---|---|
| SC-1 | Real critic mutation (critic writes its own workspace or the watched tree) | evidence captured; critic-owned delta restored; STOP raised; no further agy dispatch |
| SC-2 | Non-critic write to the shared worktree during the window | bytes never deleted or overwritten; evidence captured; outcome labelled unattributed, never "critic" |
| SC-3 | Timeout | the mutation check runs before the timeout is reported; timeout+mutation = STOP; clean timeout = ordinary failure |
| SC-4 | Parallel/sibling agy dispatches | a STOP in one blocks new spawns in all; siblings never attribute or delete each other's scratch/evidence |
| SC-5 | Oversized-prompt scratch | never reported as a mutation; removed afterwards; never visible to a sibling window |
| SC-6 | Preflight | preflight ping is a dispatch: obeys the stop latch, honors `--cwd`, surfaces STOP as STOP |
| SC-7 | Fresh process after a prior STOP | no agy dispatch (preflight included) until an explicit operator clear |

## Features (functional)
- F-1 Typed, terminal STOP signal that generic `except Exception` handlers cannot absorb.
- F-2 In-process dispatch latch: once set, every agy entry point refuses before spawning.
- F-3 Durable stop record consulted by every process before any agy dispatch; cleared only by an
  explicit operator act that is itself recorded.
- F-4 Terminal handlers: debate critique exits with a distinct code, no synthesis, no round checkpoint
  containing the stopped round; gauntlet records a stop status and exits; preflight propagates STOP.
- F-5 Structural attribution: critic-owned workspace per dispatch; shared-tree deltas captured
  non-destructively as unattributed.
- F-6 Tool-owned write classes (partial checkpoints, incident evidence, prompt scratch) never count as
  mutations and are never reverted.
- F-7 Non-mutation failures (rc≠0, empty output, clean timeout) keep today's bounded retry.

## Non-functional
- NF-1 Regression suite runs offline: no network, no live critic; fake agy via subprocess side effects.
- NF-2 Tests assert observable behavior with paired negative oracles; no mock echoes or source-text pins.
- NF-3 STOP message stays human-readable, but no control flow depends on string matching.
- NF-4 Integration onto the user-owned dirty live tree only through a named, operator-approved gate
  that proves no user hunk is overwritten.

## Integrations (internal)
`scripts/models.py` (dispatch, tripwire, retry, preflight, parallel save), `scripts/debate.py`
(critique round, preflight wiring, exit codes), `scripts/gauntlet/*` (model dispatch + 8 generic catch
sites + orchestrator stop handling), `scripts/session.py` (checkpoint dir), tests under
`scripts/tests/` / `tests/`.

## Unknowns (to resolve in roadmap/debate, not assumed)
- U-1 Does agy read an absolute-path prompt from a non-git temp workspace? (live proof forbidden while
  the defect is open → offline-provable design or explicit residue).
- U-2 **Decided (operator, 2026-09-24):** an unattributed shared-tree delta halts the round
  fail-closed with `attribution=unattributed`; bytes are preserved, never reverted.
- U-3 **Decided (operator, 2026-09-24):** the durable stop record is scoped per watched repository;
  the operator-clear UX remains open.
- U-4 Already-running siblings at STOP time: let them finish and quarantine output, or terminate by PID.
- U-5 Landing path: live tree `bounded-pipeline-reform` carries dirty overlapping hunks in `models.py`,
  `debate.py`, gauntlet files, `tests/test_models.py`; exact reconciliation order.
- U-6 fizzy-pipeline-mcp has its own agy runner; out of this worktree → recorded as residue, not fixed here.

## Out of scope
Post-Fable session, Brainquarters Jev session/records, live source, deployment, model-routing changes,
secrets/config, global process control.


---

# Appendix B — Test pseudocode (canonical)

# Test Pseudocode — AGY Tripwire Stop

> v1 — 2026-09-24 (roadmap). Canonical source of truth for tests; `roadmap/manifest.json` links here.
> One active `spine: true` per user story (TC-X.0). Variants cite `spine_of` + `spine_step_ref`.
> Maturity: every case is `nl` with named accessors, a candidate for `acceptance` after debate. None are concrete.
> Project meaning of REAL-DATA: a real temporary git repository with real `git status` and real bytes on disk,
> exercised through the real dispatch/tripwire/debate code paths.
> The critic is the only thing replaced. A fake `agy` executable placed first on `PATH` performs scripted
> side effects (write, sleep, exit code, stdout).
> **Liveness technique (all MOCK-EXTERNAL cases):** the fault is induced with that fake-critic executable. Each case
> records the technique; no case counts a mock echo as liveness.
> Paired negative oracle: every positive case names the observable that MUST NOT happen, and it has a sibling
> case in which the triggering condition is absent and the stop MUST NOT fire.

Accessor vocabulary (observable surfaces, not implementation names):
- `spawns` — count of fake-critic process starts (written by the fake binary to a counter file outside the repo)
- `incident` — the incident record directory (attribution, mutated paths, pre/post bytes, critic streams)
- `stop_record` — the durable per-repo stop record
- `exit_code`, `stderr` — process-level outcome of `debate.py` / gauntlet CLI
- `round_artifacts` — round checkpoint / critiques files written by the critique flow
- `tree_bytes(path)` — bytes on disk for a path in the watched repo

---

## US-0: Offline agy-safety suite (M0)

### TC-0.0: Suite runs offline against the fake critic [spine: US-0]
**Data Strategy: REAL-DATA** — real temp git repos, real subprocesses; network is not needed by construction.
spine_steps: S1 invoke suite command, S2 fake critic resolved first on PATH, S3 all SC cases report pass/fail by id
accessors: exit_code, spawns
```
given: clean checkout, network namespace unavailable or unset proxy, no real agy credentials
when:  the documented suite command runs
then:  every SC-n case executes against the fake critic
assert: exit 0; report lists SC-1..SC-7; wall time < 5 min
negative: no process named the real agy binary path is ever started (spawn log contains only the fake path)
```

### TC-0.1: Fake-critic guard refuses a real agy [spine_of: TC-0.0, spine_step_ref: S2]
**Data Strategy: SYNTHETIC** — manufacture PATH where the fake is absent; this cannot occur in a normal suite run.
accessors: exit_code, stderr
```
given: PATH resolves `agy` to a non-fake binary
when:  the suite starts
then:  it aborts before any dispatch with a message naming the resolved path
assert: exit != 0; spawns == 0
```

## US-1: Debate critique STOP is terminal (M1, SC-1 consequences)

### TC-1.0: STOP ends the round with a distinct outcome [spine: US-1]
**Data Strategy: MOCK-EXTERNAL** — scope: Antigravity critic process.
**why_impossible_to_reproduce_live:** live agy dispatch is forbidden by operator ruling until this defect is repaired and cleared, and a real critic's decision to write a file cannot be forced deterministically.
spine_steps: S1 critic mutates during window, S2 STOP raised, S3 round ends with stop outcome, S4 nothing downstream runs
accessors: spawns, exit_code, stderr, round_artifacts, incident
```
given: temp repo; debate critique with one fake agy critic that writes inside its dispatch-private surface
when:  debate critique runs
then:  the round ends with the STOP outcome (distinct exit code, incident path on stderr)
assert: spawns == 1; exit_code == STOP code; no synthesis output; no round checkpoint containing the stopped round
negative: no "Retrying" line; spawns never reaches 2
```

### TC-1.1: Non-mutation failure keeps bounded retry [spine_of: TC-1.0, spine_step_ref: S2]
**Data Strategy: MOCK-EXTERNAL** — scope: Antigravity critic exit status. why_impossible_to_reproduce_live: same operator dispatch ban as TC-1.0.
accessors: spawns, exit_code
```
given: fake agy exits non-zero with empty stdout, writes nothing
when:  debate critique runs
then:  the call is retried up to MAX_RETRIES and the round reports an ordinary model error
assert: spawns == MAX_RETRIES; exit_code != STOP code; no incident record; no stop_record
```

### TC-1.2: Sibling non-agy critic output in a stopped round is not synthesized [spine_of: TC-1.0, spine_step_ref: S4]
**Data Strategy: MOCK-EXTERNAL** — scope: Codex + Antigravity critics. why_impossible_to_reproduce_live: operator dispatch ban; Codex also replaced by a fake executable so that ordering is deterministic.
accessors: round_artifacts, exit_code
```
given: fake codex returns a valid critique first; fake agy then mutates
when:  debate critique runs with both
then:  the round ends with STOP; the codex critique is preserved as evidence but not synthesized into a round result
assert: exit_code == STOP code; no combined round checkpoint; codex partial preserved byte-identical
```

### TC-1.3: Stop handling survives a generic catch site [spine_of: TC-1.0, spine_step_ref: S2]
**Data Strategy: SYNTHETIC** — needs a deliberately added generic handler around the dispatch; cannot occur in a normal run.
accessors: spawns, exit_code
```
given: a caller wraps dispatch in a broad "catch any ordinary error and continue" block
when:  the critic mutates
then:  the STOP still reaches the round boundary
assert: exit_code == STOP code; spawns == 1
negative: identical run with a non-mutation failure IS absorbed by that block (proves the block is live)
```

## US-2: Gauntlet STOP blocks siblings and later phases (M1, SC-4)

### TC-2.0: STOP in one attack blocks unstarted siblings [spine: US-2]
**Data Strategy: MOCK-EXTERNAL** — scope: Antigravity attack critics. why_impossible_to_reproduce_live: operator dispatch ban.
spine_steps: S1 first agy attack mutates, S2 latch set, S3 queued siblings refuse before spawn, S4 run records stop status
accessors: spawns, exit_code, incident
```
given: gauntlet with 3 agy adversaries; attack #1 mutates; #2, #3 not yet spawned
when:  gauntlet runs
then:  #2 and #3 are never spawned; the run records a stop status and exits with the STOP code
assert: spawns == 1; manifest/status == stop; no gauntlet-internal phase after attacks runs
```

### TC-2.1: Already-running sibling at STOP time is handled per U-4 ruling [spine_of: TC-2.0, spine_step_ref: S3]
**Data Strategy: MOCK-EXTERNAL** — scope: two overlapping agy critics. why_impossible_to_reproduce_live: operator dispatch ban.
accessors: spawns, incident, round_artifacts
```
given: attack #2 already running (fake sleeps) when #1 trips
when:  #2 returns
then:  its output is quarantined, not synthesized (or it is terminated by PID — outcome fixed by debate on U-4)
assert: no concern extracted from #2; no new spawn after #1's STOP
```

### TC-2.2: Clean gauntlet with agy is unaffected [spine_of: TC-2.0, spine_step_ref: S1]
**Data Strategy: MOCK-EXTERNAL** — scope: Antigravity attack critics. why_impossible_to_reproduce_live: operator dispatch ban.
accessors: spawns, exit_code
```
given: 3 agy adversaries that write nothing
when:  gauntlet runs
then:  all 3 spawn; no stop status; later phases run
assert: spawns == 3; exit_code == 0; no incident, no stop_record
```

## US-3: Preflight is a real dispatch (M1, SC-6)

### TC-3.0: Preflight honours the round cwd [spine: US-3]
**Data Strategy: REAL-DATA** — two real temp repos; the observable is which repo the check watches.
spine_steps: S1 critique invoked with a round cwd, S2 preflight runs against that cwd, S3 preflight outcome reported
accessors: incident, tree_bytes
```
given: process cwd = repo A; round cwd = repo B; fake agy preflight writes into B
when:  debate critique runs with preflight enabled
then:  the incident is recorded for repo B, not A
assert: incident under B's evidence location; A untouched
```

### TC-3.1: Preflight STOP surfaces as STOP, not "preflight failed" [spine_of: TC-3.0, spine_step_ref: S3]
**Data Strategy: MOCK-EXTERNAL** — scope: Antigravity preflight ping. why_impossible_to_reproduce_live: operator dispatch ban.
accessors: exit_code, spawns, round_artifacts
```
given: fake agy mutates during the preflight ping
then:  exit_code == STOP code; no critique dispatch follows; stderr names the incident
negative: a preflight with a dead-auth style failure (rc!=0, no write) exits with the ordinary preflight error code
```

### TC-3.2: Preflight refuses when the latch or stop record is set [spine_of: TC-3.0, spine_step_ref: S2]
**Data Strategy: REAL-DATA** — real stop record on disk.
accessors: spawns, exit_code
```
given: stop_record present in repo B
when:  debate critique with preflight runs against B
assert: spawns == 0; exit_code == STOP-blocked code
```

### TC-3.3: Skip-preflight does not skip the stop check [spine_of: TC-3.0, spine_step_ref: S2]
**Data Strategy: REAL-DATA** — real stop record on disk.
```
given: stop_record present; --skip-preflight
assert: spawns == 0 for the critique dispatch as well
```

## US-4: STOP survives the process (M2, SC-7)

### TC-4.0: Fresh process refuses until operator clear [spine: US-4]
**Data Strategy: REAL-DATA** — two real sequential processes against one real repo; stop record is real on-disk state.
spine_steps: S1 process 1 trips and exits, S2 process 2 starts, S3 process 2 refuses before spawn, S4 operator clear, S5 process 3 dispatches
accessors: stop_record, spawns, exit_code, incident
```
given: process 1 ends with STOP in repo R
when:  process 2 runs debate critique with an agy critic against R
then:  process 2 refuses before any spawn and names the stop record + incident
assert: spawns(process 2) == 0; exit_code == STOP-blocked code
when:  the operator clear is performed; process 3 runs
assert: spawns(process 3) == 1; incident evidence still present byte-identical
```

### TC-4.1: Other repository is not blocked [spine_of: TC-4.0, spine_step_ref: S3]
**Data Strategy: REAL-DATA** — two real repos.
```
given: stop_record in R1
when:  a critique targets R2
assert: dispatch proceeds in R2 (spawns == 1)
```

### TC-4.2: Clearing requires an explicit recorded operator act [spine_of: TC-4.0, spine_step_ref: S4]
**Data Strategy: REAL-DATA** — real record lifecycle.
```
when:  a non-operator path (retry, new round, flag default) attempts to proceed
assert: record unchanged; still refused
when:  the explicit clear is performed
assert: a clear entry is recorded (who/when/which incident); incident dir untouched
```

### TC-4.3: Corrupt or unreadable stop record fails closed [spine_of: TC-4.0, spine_step_ref: S3]
**Data Strategy: SYNTHETIC** — record corruption cannot occur in a normal run.
```
given: stop_record present but unparseable
assert: dispatch refused (spawns == 0), error names the record path
```

### TC-4.4: Stop record is not itself a watched mutation [spine_of: TC-4.0, spine_step_ref: S1]
**Data Strategy: REAL-DATA** — real sibling window overlapping record creation.
```
given: two overlapping dispatches; one trips and writes the record
assert: the other dispatch's check does not attribute the record or incident dir as a mutation
```

## US-5: Non-critic writes are never destroyed or blamed (M3, SC-2)

### TC-5.0: Orchestrator write during the window is preserved and labelled unattributed [spine: US-5]
**Data Strategy: REAL-DATA** — replays the 2026-09-24 incident shape: a real file written into the real watched repo mid-window. The fake critic only sleeps and writes nothing.
spine_steps: S1 window opens, S2 non-critic writer writes a new file, S3 check sees shared-tree delta, S4 evidence recorded non-destructively, S5 round halts fail-closed
accessors: tree_bytes, incident, exit_code, spawns
```
given: temp repo with pre-existing dirty tracked file D and untracked file U (other session's work)
when:  during the fake critic's sleep, a separate writer creates N (2,519 bytes) and edits D
then:  N and D keep the writer's bytes; U untouched; incident.attribution == "unattributed"; round halts
assert: tree_bytes(N) == written bytes; tree_bytes(D) == edited bytes; incident has pre+post bytes for N, D
negative: incident never says "critic"/"agy modified"; no unlink, no overwrite, no git checkout on any watched path
```

### TC-5.1: Checkpoint writer is tool-owned, not a mutation [spine_of: TC-5.0, spine_step_ref: S3]
**Data Strategy: REAL-DATA** — the real partial-result writer in the real watched repo during a real window.
```
given: fake codex returns first; its partial result is saved under the watched repo during the agy window
assert: no incident; no stop; partial result file intact
negative: a non-tool file written at the same moment DOES produce an unattributed halt (TC-5.0)
```

### TC-5.2: Co-tenant Codex write is unattributed, never critic [spine_of: TC-5.0, spine_step_ref: S4]
**Data Strategy: MOCK-EXTERNAL** — scope: Codex CLI side effect. why_impossible_to_reproduce_live: a live Codex call is allowed but its write timing is non-deterministic; the fake reproduces the incident ordering exactly.
```
assert: file preserved; attribution == "unattributed"
```

### TC-5.3: Deletion of a dirty file by a non-critic is recorded, not reverted [spine_of: TC-5.0, spine_step_ref: S4]
**Data Strategy: REAL-DATA** — real deletion in the real repo.
```
given: dirty tracked file D deleted by the non-critic writer mid-window
assert: D stays deleted (no resurrection); incident holds D's pre-state bytes for manual restore
```

## US-6: Real critic mutation stays contained (M3, SC-1, SC-3)

### TC-6.0: Critic write inside its private surface is captured, restored, and STOPs [spine: US-6]
**Data Strategy: MOCK-EXTERNAL** — scope: Antigravity file-edit tool. why_impossible_to_reproduce_live: operator dispatch ban; a live critic's write cannot be forced deterministically.
spine_steps: S1 critic writes in its private surface, S2 check attributes to critic, S3 evidence captured, S4 surface restored, S5 STOP raised
accessors: incident, spawns, exit_code
```
given: fake agy edits and creates files in its dispatch-private surface
then:  incident.attribution == "critic"; pre/post bytes + critic stdout/stderr captured; surface restored; STOP
assert: spawns == 1; stop_record written; exit_code == STOP code
```

### TC-6.1: Critic write through an absolute path into the shared tree still halts [spine_of: TC-6.0, spine_step_ref: S2]
**Data Strategy: MOCK-EXTERNAL** — scope: Antigravity absolute-path write. why_impossible_to_reproduce_live: operator dispatch ban.
```
given: fake agy writes into the watched repo by absolute path
then:  halt with attribution "unattributed" (structural attribution cannot prove authorship); bytes preserved
assert: STOP; stop_record written; file bytes preserved; evidence sufficient to restore by hand
```

### TC-6.2: Timeout path runs the same check first [spine_of: TC-6.0, spine_step_ref: S1]
**Data Strategy: MOCK-EXTERNAL** — scope: Antigravity hang after write. why_impossible_to_reproduce_live: operator dispatch ban.
```
given: fake agy writes in its private surface then sleeps past the timeout
then:  STOP (not "timed out"); no retry
assert: spawns == 1; incident present; exit_code == STOP code
negative: fake agy sleeps past timeout WITHOUT writing → ordinary timeout, retried (spawns == MAX_RETRIES)
```

### TC-6.3: Clean critic run is unaffected [spine_of: TC-6.0, spine_step_ref: S2]
**Data Strategy: MOCK-EXTERNAL** — scope: Antigravity critic. why_impossible_to_reproduce_live: operator dispatch ban.
```
assert: response returned; no incident; no stop_record; private surface removed afterwards
```

## US-7: Tool-owned scratch never trips a window (M3, SC-4, SC-5)

### TC-7.0: Oversized prompt is never a mutation and is removed [spine: US-7]
**Data Strategy: SYNTHETIC** — needs a prompt just above the inline limit; boundary control required.
spine_steps: S1 oversized prompt spilled, S2 critic reads pointer, S3 check runs, S4 scratch removed
accessors: incident, tree_bytes
```
given: prompt of inline_max + 1 bytes [BVA]
assert: no incident; scratch absent after return; watched repo porcelain unchanged
paired: prompt of exactly inline_max bytes stays inline (no scratch created) [BVA]
```

### TC-7.1: Oversized prompt on the error and timeout paths is removed [spine_of: TC-7.0, spine_step_ref: S4]
**Data Strategy: MOCK-EXTERNAL** — scope: Antigravity failure. why_impossible_to_reproduce_live: operator dispatch ban.
```
assert: scratch absent after rc!=0, after timeout, and after STOP
```

### TC-7.2: Sibling windows never see each other's scratch or evidence [spine_of: TC-7.0, spine_step_ref: S3]
**Data Strategy: REAL-DATA** — two real overlapping dispatches against one real repo.
```
given: dispatch A spills a prompt and dispatch B trips (incident + stop_record) while A's window is open
assert: A's check attributes nothing to A's critic from B's files; nothing of B's is unlinked by A
```

### TC-7.3: Tool-owned exclusions are exact, not prefix-greedy [spine_of: TC-7.0, spine_step_ref: S3]
**Data Strategy: SYNTHETIC** — lookalike paths do not occur naturally.
```
given: a non-tool writer creates a lookalike path (e.g. a sibling of the incident dir with a similar prefix)
assert: it is treated as a shared-tree delta (unattributed halt), not excluded
```

## US-8: Deliberate integration (M4)

### TC-8.0: Reconciliation dry-run proves every user hunk survives [spine: US-8]
**Data Strategy: REAL-DATA** — the real dirty live tree read-only, applied to a throwaway copy.
spine_steps: S1 snapshot live dirty diff + untracked list, S2 apply repair to a copy, S3 compare user hunks, S4 approval gate
accessors: hunk-preservation report
```
given: a byte copy of the live tree (never the tree itself)
when:  the repair is applied to the copy per the plan
assert: every pre-existing user hunk and untracked file is present byte-identical in the copy
negative: no write to the live tree or ~/.claude/skills path (mtime + hash unchanged)
```

### TC-8.1: No apply before approval [spine_of: TC-8.0, spine_step_ref: S4]
**Data Strategy: STATIC** — plan document inspection.
```
assert: plan names approver, gate, order, rollback; the live apply step is gated on explicit approval text
```

---

### State Transition Table — dispatch safety state (per watched repo)
| # | From | Event | To | Action | Test |
|---|---|---|---|---|---|
| T1 | CLEAR | dispatch, no delta | CLEAR | return response | TC-6.3, TC-2.2 |
| T2 | CLEAR | non-mutation failure | CLEAR | bounded retry | TC-1.1, TC-6.2(neg) |
| T3 | CLEAR | critic-surface delta | STOPPED | capture, restore surface, STOP, write record | TC-6.0 |
| T4 | CLEAR | shared-tree delta | STOPPED | capture, NO revert, STOP unattributed, write record | TC-5.0, TC-6.1 |
| T5 | CLEAR | tool-owned write only | CLEAR | ignore | TC-5.1, TC-7.0 |
| T6 | STOPPED | any dispatch attempt (same process) | STOPPED | refuse before spawn | TC-1.0, TC-2.0 |
| T7 | STOPPED | any dispatch attempt (fresh process) | STOPPED | refuse before spawn | TC-4.0, TC-3.2 |
| T8 | STOPPED | explicit operator clear | CLEAR | record clear, keep evidence | TC-4.0, TC-4.2 |
| T9 | STOPPED | corrupt record read | STOPPED | refuse, name record | TC-4.3 |

### Decision Table — delta attribution
| # | Delta location | Writer class | Result | Test |
|---|---|---|---|---|
| 1 | critic private surface | any | critic, restore, STOP | TC-6.0 |
| 2 | shared tree, tool-owned exact path | tool | ignore | TC-5.1, TC-7.0 |
| 3 | shared tree, lookalike of tool path | any | unattributed, keep bytes, STOP | TC-7.3 |
| 4 | shared tree, other path | orchestrator/Codex/other | unattributed, keep bytes, STOP | TC-5.0, TC-5.2 |
| 5 | shared tree, other path | critic via absolute path | unattributed, keep bytes, STOP | TC-6.1 |
| 6 | none | — | no incident | TC-6.3 |
