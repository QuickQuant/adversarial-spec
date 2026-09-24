# Roadmap: AGY Tripwire Stop — critic safety contract repair

> v3, 2026-09-24. This version redoes the attribution mechanism. At G1 the operator redirected it to OS-level isolation (bwrap).
> v2 (debate R1 rulings) is superseded where noted. Sources: `roadmap-debate-r1-synthesis.md` and the session decisions log.

Session `adv-spec-202609240523-agy-tripwire-stop` · card 21616 · altitude **system** · complexity **complex**
(score 16: 4 user types + 7 feature groups + 1 external integration ×2 [Antigravity CLI] + 3 open unknowns).
Requirements: `../requirements.md`. Tests (canonical): `../tests-pseudo.md`.

### Mechanism (operator decision, 2026-09-24)
Every Antigravity dispatch, preflight included, runs inside a bubblewrap sandbox. The whole filesystem is bound read-only.
The only writable paths are a fresh per-dispatch workspace and the agy config/auth directories (`~/.antigravity`, `~/.gemini`).
The prompt and inputs are bind-mounted read-only into the workspace. The critic therefore cannot write to any repository,
so attribution is structural and never timing-based. Evidence: `bwrap --ro-bind / / … --bind <ws> <ws>` turned a repo write
into `Read-only file system`, while a workspace write succeeded. The operator tested this and the conductor re-verified it
on 2026-09-24 (bwrap 0.6.1, unprivileged userns + Landlock enabled). agy's own `--sandbox` is not a boundary
(`skills/adversarial-spec/scripts/models.py:868`).

### Personas
- **Operator (Jason).** The only person who can clear a STOP. Needs to learn that a STOP happened, see what the critic wrote or which part of the boundary failed, and clear it deliberately.
- **Orchestrator agent.** The Claude/Codex/Gemini seat running a round. It writes into the same worktree while critics run. Its bytes must never be lost, blamed, or treated as halting.
- **Co-tenant session owner.** Another session in the same repository. It must not be halted by someone else's writes. When someone else's STOP refuses its dispatch, the refusal must name the incident.
- **Maintainer.** Must not be able to reopen the retry path or an unsandboxed path by adding a catch site or a flag. Runs the offline suite.

### Goals
- G-1 A critic write is contained by construction. Its only writable surface is its own workspace. After every dispatch the workspace is inspected, its contents are captured as evidence, and it is discarded. No restore is needed. Any write the critic makes beyond the read-only inputs is a critic-attributed mutation and ends in a STOP.
- G-2 A shared-tree delta during an agy window belongs to a co-tenant. It is preserved, recorded as `co-tenant`, and never halts the round. A fail-closed STOP fires only on evidence that the boundary itself failed: a change to a path only the critic could have written, the in-sandbox write probe succeeding, or bwrap setup failing.
- G-3 A critic-attributed mutation or a boundary failure is a terminal STOP. Nothing follows it: no retry, no synthesis, no round checkpoint, no sibling spawn, and no further Antigravity dispatch (preflight included). This holds in the stopping process and in any fresh process against any worktree of the same repository (U-7 narrowed, U-8), until an explicit, recorded operator clear.
- G-4 If bwrap, or the kernel features it needs, is unavailable, the dispatch refuses before spawning. There is never an unsandboxed fallback.
- G-5 An offline regression suite proves G-1..G-4 with paired negative oracles. It runs the real bwrap boundary against a scripted fake critic, with no network and no live critic.
- G-6 Landing on the user-owned dirty live tree goes through a named, operator-approved gate. The gate is bound to the current live snapshot and proves no user hunk is overwritten. The first live dispatch after landing is a supervised canary with its own approval. It carries the live-proof residue (U-1, U-10, U-11).

**If agy cannot run inside the sandbox** (the canary fails to read its bound prompt, or agy refuses a read-only home): G-1 does not
degrade to the old tripwire. Antigravity dispatch stays refused. The Google-family seat is unavailable until the sandbox profile
is amended and a new canary passes.

### Non-Goals
- Resuming, mutating or completing `adv-spec-202607060132-post-fable-hardening-skill`, or anything in the Brainquarters Jev session.
- Editing `/home/jason/PycharmProjects/adversarial-spec` or `~/.claude/skills/adversarial-spec`, deploying, or pushing/merging without explicit integration approval. Local commits are allowed only on `adv-spec/agy-tripwire-stop-20260924` and per-candidate branches off it; nothing is pushed or merged before integration approval (operator ruling 2026-09-24, relaxes handoff line 42).
- Any Antigravity dispatch, preflight included, before the repaired contract lands and the operator clears the canary.
- Weakening containment, hiding attribution uncertainty, using string-matching as the sole stop protocol, broad model-routing changes, secrets/config edits, or global process kills.
- Repairing fizzy-pipeline-mcp's own agy runner (U-6, residue for that repo).

### Milestone 0: Getting Started (Bootstrap)
- US-0: As a maintainer, I want one offline command that runs the agy-safety suite against a scripted fake critic inside the real sandbox, so that I can verify the contract without network, credentials, or a live Antigravity dispatch.

Success criteria:
- [ ] One documented command runs the suite from a clean checkout in under 5 minutes on the dev workstation.
- [ ] Dispatch timeout and retry delay are injectable, so timeout and retry cases run in seconds.
- [ ] The suite refuses to run if the real `agy` binary would be reached. If bwrap is unavailable on the test host, the sandbox cases report `unsupported` and are never silently skipped.

Tests: TC-0.0 (spine) … TC-0.2. **Dependencies:** none.

### Milestone 1: STOP is terminal inside one process
- US-1: As the operator, I want a STOP raised during a debate critique to end that round with a distinct outcome, with no retry and no synthesis, so that no critic dispatch follows a STOP-class event.
- US-2: As the operator, I want a STOP in any gauntlet attack, or in a later gauntlet-internal phase, to block every not-yet-started Antigravity spawn in that run and record a stop status. Siblings that are already running finish, are inspected, and have their output quarantined (U-4). This way parallel dispatch cannot continue past a STOP.
- US-3: As the operator, I want the preflight ping treated as a real dispatch, so that the cheap ping cannot bypass the contract. It must be sandboxed, honour the round's working directory, obey the latch and the stop record, and surface a STOP as a STOP.

Success criteria:
- [ ] After a STOP, the fake critic's spawn count stays at its pre-STOP value on every path: retry, queued sibling, later phase, preflight.
- [ ] Non-mutation failures (non-zero exit, empty output, clean timeout) keep today's bounded retry.
- [ ] Stop handling does not depend on message text (proven with a randomised message).

Tests: TC-1.0 … TC-3.3. **Dependencies:** M0.

### Milestone 2: STOP survives the process
- US-4: As a co-tenant session owner, I want a fresh process against any worktree of the same repository to refuse Antigravity dispatch before spawning, preflight included, and to name the stop record and the incident, so that I know why and do not retry blindly.

Success criteria:
- [ ] Every critic-mutation or boundary-failure STOP leaves a durable record in the repository's git common dir. The record references its incident evidence.
- [ ] Every entry point checks the record under an admission lock before spawning. A present record refuses. A corrupt record also refuses.
- [ ] Other repositories are not blocked. Sibling worktrees of the same repository are blocked.

Tests: TC-4.0 … TC-4.7. **Dependencies:** M1.

### Milestone 3: Sandbox boundary and truthful attribution
- US-5: As an orchestrator agent, I want my writes, Codex's writes and the tool's writes into the shared worktree during an agy window left untouched, recorded as `co-tenant`, and never halting, so that concurrent work survives and nobody blames the critic for it.
- US-6: As the operator, I want any critic write inside its workspace captured byte-exact before the workspace is discarded and turned into a STOP labelled `critic`, including on the timeout path, so that genuine mutations stay visible and stop the run.
- US-7: As the operator, I want boundary failure detected and treated as a terminal STOP, and a missing sandbox to refuse dispatch, so that containment never silently degrades. Boundary failure means bwrap setup fails, the in-sandbox write probe succeeds, or a critic-only sentinel changes.
- US-11: As the operator, I want the prompt and inputs delivered read-only inside the dispatch workspace from a dispatch root outside every repository, so that oversized prompts never touch a repository and siblings never see each other's scratch.

Success criteria:
- [ ] No code path unlinks, overwrites, or runs `git checkout` on any path in a watched repository.
- [ ] Every incident states its class (`critic` | `boundary_failure`) and carries the captured workspace bytes and the critic streams. Co-tenant deltas appear in the window log, never as an incident.
- [ ] The timeout path inspects the workspace before it reports the timeout. The sandbox process tree dies with its parent, and only this process's own child is signalled.

Tests: TC-5.0 … TC-7.4, TC-11.0 … TC-11.2. **Dependencies:** M1. Independent of M2.

### Milestone 4: Operator recovery
- US-9: As the operator, I want the STOP output and incident record to tell me what the critic wrote or which boundary check failed, and where the evidence is, so that I can decide without re-running anything.
- US-10: As the operator, I want an explicit clear act that names the incident being cleared and records who cleared it, when and why, without deleting evidence, so that dispatch resumes only by my deliberate choice.

Success criteria:
- [ ] The captured workspace evidence reproduces the critic's written bytes exactly.
- [ ] The clear refuses without the matching incident identifier. A retry, a new round, or a flag default is never a clear.

Tests: TC-9.0 … TC-10.2. **Dependencies:** M2, M3.

### Milestone 5: Deliberate integration and supervised canary
- US-8: As the operator, I want a reconciliation plan that lands the repair onto the dirty `bounded-pipeline-reform` tree through an explicit approval gate, then runs one supervised live canary dispatch under its own approval, so that no user change is overwritten and the sandbox is proven live before routine use. The gate is bound to the candidate diff hash and the current live snapshot hash.

Success criteria:
- [ ] The plan names the gate, the approver, the exact order, the rollback, and the content-based hunk-preservation check.
- [ ] Apply refuses without a matching approval and snapshot hash. Nothing touches the live tree before approval.
- [ ] The canary records the U-1 read path, U-10 (no out-of-sandbox helper) and U-11 (agy runtime byproducts), and each result decides whether dispatch is re-enabled.

Tests: TC-8.0 … TC-8.3. **Dependencies:** M1–M4 green.

### Scenario → story map (handoff acceptance criterion 2)
| Scenario | Outcome | Story | Spine / variant |
|---|---|---|---|
| SC-1 real critic mutation | captured, workspace discarded, STOP `critic`, durable record | US-6 | TC-6.0 |
| SC-2 non-critic shared write | preserved, recorded `co-tenant`, no halt | US-5 | TC-5.0 |
| SC-3 timeout | workspace inspected first; mutation → STOP, clean → ordinary retryable timeout | US-6 | TC-6.2 |
| SC-4 parallel/sibling | separate workspaces; queued siblings blocked; running siblings finish + quarantine | US-2, US-11 | TC-2.0, TC-2.1, TC-11.2 |
| SC-5 oversized-prompt scratch | lives in dispatch root outside every repo, read-only bind; removed after | US-11 | TC-11.1 |
| SC-6 preflight | sandboxed, round cwd, latch + record honoured, STOP surfaced as STOP | US-3 | TC-3.0 |
| SC-7 fresh process after STOP | refused before spawn in every worktree of the repo until operator clear | US-4 | TC-4.0 |

### Risks and mitigations
| Risk | Mitigation |
|---|---|
| agy cannot read a read-only bound prompt or needs a writable home (U-1) | No fallback. Dispatch stays refused. The canary proves the path before re-enable (TC-8.3) |
| agy delegates file writes to a helper process outside the sandbox, so writes appear as `co-tenant` (U-10) | New PID/IPC namespaces, die-with-parent. The canary checks for out-of-sandbox helper processes. Residue until proven |
| agy writes runtime byproducts into its cwd, so every dispatch STOPs (U-11) | The canary observes this. If benign, the profile moves the runtime dir to a config bind (operator amendment), never an allowlist in the workspace |
| Critic persists behaviour changes in the writable config dirs (U-12) | Config-dir change manifest recorded per dispatch as evidence. Policy decided in D0/debate |
| A new catch site reopens retry | The typed stop cannot be absorbed by ordinary-error handlers (TC-1.3) and does not depend on message text (TC-1.4) |
| Admission race between processes | Admission check and record write serialized under a lock in the git common dir (TC-4.7) |
| Landing overwrites user hunks on the dirty live tree | Snapshot-bound approval gate, content-based hunk check, rollback (US-8) |

### Architecture impact
`extends_existing`. The contracts are: a sandboxed dispatch launcher (a new module inside the models layer), the typed stop signal
and dispatch latch, the git-common-dir stop record with admission lock and clear, and incident classes. All of them
sit inside the existing models/providers, debate/session and gauntlet components. No new service. See `manifest.json#architecture_impact`.

### Open unknowns carried into decomposition
U-5 (landing order onto the dirty tree), U-6 (fizzy runner residue), U-10 / U-11 (canary residue), U-12 (config-dir write policy).
U-1 is resolved by design through the sandbox; its live proof is canary residue.


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
- U-1 **Resolved by design (G1 redirect):** prompt and inputs are bind-mounted read-only into the sandbox workspace. The live
  proof is the supervised post-landing canary (residue). If agy cannot run that way, agy dispatch stays refused.
- U-2 ~~halt unattributed~~ **Superseded (operator G1 redirect, 2026-09-24):** attribution is structural via bwrap
  (repo read-only to the critic). A shared-tree delta is `co-tenant`: preserved, recorded, never halting. A fail-closed STOP
  happens only on boundary-failure evidence.
- U-3 **Decided:** the stop record is per repository and lives in the git common dir (U-8). Every worktree of the repo is blocked.
- U-4 **Decided:** siblings already running at STOP time finish, are inspected, and are quarantined.
- U-7 **Decided (narrowed at G1):** the durable operator-clear STOP applies only to critic mutation or boundary failure.
- No-fallback **Decided:** if bwrap is unavailable, dispatch refuses. Never unsandboxed.
- Commits **Decided:** local commits are allowed on the session branch and on per-candidate branches off it. Nothing is pushed
  or merged before integration approval (this relaxes handoff line 42).
- Full decision trail: `.adversarial-spec/sessions/adv-spec-202609240523-agy-tripwire-stop.decisions.log`.
- U-5 Landing path: live tree `bounded-pipeline-reform` carries dirty overlapping hunks in `models.py`,
  `debate.py`, gauntlet files, `tests/test_models.py`; exact reconciliation order.
- U-6 fizzy-pipeline-mcp has its own agy runner; out of this worktree → recorded as residue, not fixed here.

## Out of scope
Post-Fable session, Brainquarters Jev session/records, live source, deployment, model-routing changes,
secrets/config, global process control.


---

# Appendix B — Test pseudocode (canonical)

# Test Pseudocode — AGY Tripwire Stop

> v3 — 2026-09-24 (G1 redirect: bwrap OS isolation replaces snapshot attribution; co-tenant deltas non-halting;
> STOP only for critic mutation / boundary failure; no unsandboxed fallback; +US-11). Supersedes v2.
> v2 — 2026-09-24 (roadmap R1 sync). v1 — 2026-09-24 (roadmap).
> Canonical source of truth for tests; `roadmap/manifest.json` links here.
> There is one active `spine: true` per user story (TC-X.0). Variants cite `spine_of` + `spine_step_ref`.
> Maturity: every case is `nl` with named accessors. Each is a candidate for `acceptance` after debate; none is concrete.
>
> Project meaning of REAL-DATA: the case runs against a real temp git repo (real `git status`, real bytes, real linked
> worktrees) and the **real bwrap sandbox**, through the real dispatch/debate/gauntlet code paths. Only the critic is replaced:
> a scripted fake `agy` executable does the scripted side effects *inside the real sandbox* (write, sleep, exit code,
> stdout). Every write attempt it makes is therefore judged by the real kernel boundary.
> **Liveness technique (MOCK-EXTERNAL cases):** the scripted fake-critic executable induces the fault. The boundary it acts against
> is real. No case counts a mock echo as liveness.
> Paired negative oracle: each positive case names the observable that MUST NOT happen. It also has a sibling case in which the
> trigger is absent and the STOP MUST NOT fire.

Accessor vocabulary (observable surfaces, not implementation names):
- `spawns` counts fake-critic process starts. The fake binary writes the count to a counter file bound writable only for the test.
- `incident` is the incident evidence directory under the git common dir. It holds the class, captured workspace bytes, and critic streams.
- `window_log` is the per-dispatch record of co-tenant deltas. It is non-halting.
- `stop_record` is the durable stop record in the repository's git common dir (U-8). `clear_log` records operator clears.
- `exit_code` and `stderr` are the process outcome of `debate.py` or the gauntlet CLI. `round_artifacts` are the round checkpoint and critique files.
- `tree_bytes(path)` is the bytes on disk for a path in the watched repo.

---

## US-0: Offline agy-safety suite (M0)

### TC-0.0: Suite runs offline against the fake critic inside the real sandbox [spine: US-0]
**Data Strategy: REAL-DATA**. The suite uses real temp git repos, real bwrap and real subprocesses. No network is needed by construction.
spine_steps: S1 invoke suite command, S2 fake critic resolved first on PATH, S3 every SC case reports by id
accessors: exit_code, spawns
```
given: clean checkout; bwrap available; no agy credentials used
when:  the documented suite command runs
then:  SC-1..SC-7 execute against the fake critic inside real bwrap
assert: exit 0; report lists SC-1..SC-7; wall time < 5 min (injected timeouts/retry delays)
negative: the spawn log contains only the fake path; the real agy binary never starts
```

### TC-0.1: Fake-critic guard refuses a real agy [spine_of: TC-0.0, spine_step_ref: S2]
**Data Strategy: SYNTHETIC**. The test manufactures a PATH where the fake is absent. That cannot happen in a normal suite run.
```
given: PATH resolves `agy` to a non-fake binary
assert: suite aborts before any dispatch, names the resolved path; spawns == 0
```

### TC-0.2: Sandbox unavailability is reported, never skipped silently [spine_of: TC-0.0, spine_step_ref: S3]
**Data Strategy: SYNTHETIC**. The test manufactures a host with no bwrap by setting a PATH that has no bwrap.
```
assert: sandbox-dependent cases report "unsupported: bwrap not found"; suite exit != 0 unless explicitly run in report-only mode
```

## US-1: Debate critique STOP is terminal (M1)

### TC-1.0: Critic mutation ends the round with a distinct outcome [spine: US-1]
**Data Strategy: MOCK-EXTERNAL**. Scope: the Antigravity critic process (real sandbox).
**why_impossible_to_reproduce_live:** live agy dispatch is forbidden by operator ruling until this repair lands and the canary is approved. A real critic's decision to write also cannot be forced deterministically.
spine_steps: S1 critic writes in its workspace, S2 STOP raised, S3 round ends with STOP outcome, S4 nothing downstream runs
accessors: spawns, exit_code, stderr, round_artifacts, incident, stop_record
```
given: temp repo R; debate critique with one fake agy critic that writes a file into its workspace
when:  debate critique runs with round cwd = R
then:  the round ends with the STOP outcome (distinct exit code; incident path on stderr)
assert: spawns == 1; exit_code == STOP; incident.class == critic; stop_record written; no synthesis; no round checkpoint containing the round
negative: no "Retrying" line; spawns never reaches 2
```

### TC-1.1: Non-mutation failure keeps bounded retry [spine_of: TC-1.0, spine_step_ref: S2]
**Data Strategy: MOCK-EXTERNAL**. Scope: Antigravity exit status. why_impossible_to_reproduce_live: same operator dispatch ban.
```
given: fake agy exits non-zero with empty stdout and writes nothing
assert: spawns == MAX_RETRIES; exit_code != STOP; no incident; no stop_record
```

### TC-1.2: Sibling non-agy critique in a stopped round is preserved, not synthesized [spine_of: TC-1.0, spine_step_ref: S4]
**Data Strategy: MOCK-EXTERNAL**. Scope: Codex and Antigravity critics. why_impossible_to_reproduce_live: operator dispatch ban. Codex is also replaced by a fake so the ordering is deterministic.
```
given: fake codex returns a valid critique first; fake agy then writes in its workspace
assert: exit_code == STOP; no combined round checkpoint; codex partial preserved byte-identical as evidence
```

### TC-1.3: Stop survives a generic catch site [spine_of: TC-1.0, spine_step_ref: S2]
**Data Strategy: SYNTHETIC**. The test deliberately wraps dispatch in a broad handler. That cannot occur in a normal run.
```
given: a caller wraps dispatch in "catch any ordinary error and continue"
assert: the critic-mutation STOP still reaches the round boundary (exit_code == STOP; spawns == 1)
negative: the same wrapper DOES absorb a non-mutation failure (proves the wrapper is live)
```

### TC-1.4: STOP behaviour is independent of message text [spine_of: TC-1.0, spine_step_ref: S2]
**Data Strategy: SYNTHETIC**. The randomised message text exists to falsify string matching.
```
given: the STOP's human-readable message is replaced by a random string (type unchanged)
assert: identical outcome to TC-1.0
negative: an ordinary error whose text contains "AGY_MUTATION_DETECTED" is retried like any other error
```

## US-2: Gauntlet STOP blocks siblings and later phases (M1)

### TC-2.0: STOP in one attack blocks unstarted siblings [spine: US-2]
**Data Strategy: MOCK-EXTERNAL**. Scope: Antigravity attack critics. why_impossible_to_reproduce_live: operator dispatch ban.
spine_steps: S1 first agy attack writes in its workspace, S2 latch set, S3 queued siblings refuse before spawn, S4 run records stop status
```
given: gauntlet with 3 agy adversaries; #1 writes in its workspace; #2 and #3 not yet spawned
assert: spawns == 1; run status == stop; exit_code == STOP; no gauntlet-internal phase after attacks runs
```

### TC-2.1: Already-running sibling finishes, is inspected, and is quarantined (U-4) [spine_of: TC-2.0, spine_step_ref: S3]
**Data Strategy: MOCK-EXTERNAL**. Scope: two overlapping agy critics. why_impossible_to_reproduce_live: operator dispatch ban.
```
given: #2 is already running (sleeps 2s and writes nothing) when #1 trips
assert: #2 is not signalled; its workspace inspection runs; its output is quarantined and never synthesized; no spawn after #1's STOP
paired: if #2 also wrote in its workspace, a second incident (class critic) is recorded; still one STOP outcome
```

### TC-2.2: Clean gauntlet with agy is unaffected [spine_of: TC-2.0, spine_step_ref: S1]
**Data Strategy: MOCK-EXTERNAL**. Scope: Antigravity attack critics. why_impossible_to_reproduce_live: operator dispatch ban.
```
assert: 3 fake agy adversaries that write nothing → spawns == 3; exit 0; no incident; no stop_record
```

## US-3: Preflight is a real dispatch (M1)

### TC-3.0: Preflight is sandboxed and honours the round cwd [spine: US-3]
**Data Strategy: REAL-DATA**. Two real temp repos and the real sandbox.
spine_steps: S1 critique invoked with a round cwd, S2 preflight dispatch runs sandboxed for that cwd, S3 preflight outcome reported
```
given: process cwd = repo A; round cwd = repo B; fake agy preflight attempts writes into A and B by absolute path, then writes in its workspace
assert: A and B unchanged (EROFS); incident filed under B's git common dir with class critic; nothing filed for A
```

### TC-3.1: Preflight STOP surfaces as STOP, not "preflight failed" [spine_of: TC-3.0, spine_step_ref: S3]
**Data Strategy: MOCK-EXTERNAL**. Scope: Antigravity preflight ping. why_impossible_to_reproduce_live: operator dispatch ban.
```
assert: exit_code == STOP; no critique dispatch follows; stderr names the incident
negative: a dead-auth style preflight failure (rc != 0, no write) exits with the ordinary preflight error code
```

### TC-3.2: Preflight refuses when the stop record is present [spine_of: TC-3.0, spine_step_ref: S2]
**Data Strategy: REAL-DATA**. Real stop record on disk.
```
assert: stop_record present for B → spawns == 0; exit_code == STOP-blocked
```

### TC-3.3: --skip-preflight does not skip the stop check [spine_of: TC-3.0, spine_step_ref: S2]
**Data Strategy: REAL-DATA**. Real stop record on disk.
```
assert: stop_record present; --skip-preflight → spawns == 0 for the critique dispatch too
```

## US-4: STOP survives the process (M2)

### TC-4.0: Fresh process refuses until operator clear [spine: US-4]
**Data Strategy: REAL-DATA**. Real sequential processes against one real repo; the stop record is real on-disk state.
spine_steps: S1 process 1 STOPs and exits, S2 process 2 starts, S3 process 2 refuses before spawn naming record + incident, S4 operator clear, S5 process 3 dispatches
```
assert: spawns(process 2) == 0; exit_code == STOP-blocked; stderr names stop_record + incident
then:  after the explicit clear, spawns(process 3) == 1 and the incident evidence is byte-identical
```

### TC-4.1: Other repository is not blocked [spine_of: TC-4.0, spine_step_ref: S3]
**Data Strategy: REAL-DATA**. Two real repos.
```
assert: stop_record in R1; critique targeting R2 → spawns == 1
```

### TC-4.2: Record and incident live outside every working tree (U-8) [spine_of: TC-4.0, spine_step_ref: S1]
**Data Strategy: REAL-DATA**. A real repo with a linked worktree.
```
assert: stop_record and incident are under `git rev-parse --git-common-dir`; `git status --porcelain -uall` of every worktree shows neither
```

### TC-4.3: Corrupt stop record fails closed [spine_of: TC-4.0, spine_step_ref: S3]
**Data Strategy: SYNTHETIC**. Record corruption does not occur in a normal run.
```
assert: unparseable stop_record → spawns == 0; error names the record path
```

### TC-4.4: Co-tenant STOP-free window writes no stop record [spine_of: TC-4.0, spine_step_ref: S1]
**Data Strategy: REAL-DATA**. A real co-tenant write during a real window.
```
assert: TC-5.0 setup → no stop_record; the next process dispatches (spawns == 1)
```

### TC-4.6: Sibling worktree of the same repository is blocked [spine_of: TC-4.0, spine_step_ref: S3]
**Data Strategy: REAL-DATA**. A real `git worktree add` pair.
```
assert: STOP from W1 of R; critique targeting W2 of R → spawns == 0; refusal names record + incident
```

### TC-4.7: Admission race — STOP between check and spawn [spine_of: TC-4.0, spine_step_ref: S3]
**Data Strategy: SYNTHETIC**. A barrier forces the interleaving, which is rare in a normal run.
```
given: process A passes admission and holds before spawn; process B records a STOP under the admission lock
assert: no dispatch starts after B's record is durable; A either refuses (spawns_A == 0) or was admitted strictly before and is listed in B's incident as "in-flight at stop" and quarantined
```

## US-5: Co-tenant writes are untouched, recorded, non-halting (M3)

### TC-5.0: Orchestrator write during the window is preserved and recorded co-tenant [spine: US-5]
**Data Strategy: REAL-DATA**. This replays the 2026-09-24 incident shape: a real file is written into the real watched repo mid-window. The fake critic only sleeps.
spine_steps: S1 window opens, S2 co-tenant writes, S3 window closes, S4 delta recorded co-tenant, S5 round continues
```
given: repo with dirty tracked D and untracked U (another session's work)
when:  during the fake critic's sleep, another writer creates N (2,519 bytes), edits D, deletes a dirty file E
assert: tree_bytes(N), tree_bytes(D) are the writer's bytes; E stays deleted; U untouched; window_log lists N, D, E as co-tenant
assert: round completes normally (critic response returned); no incident; no stop_record
negative: no unlink/overwrite/git-checkout on any watched path; nothing labelled critic
```

### TC-5.1: Partial-checkpoint writer is co-tenant and harmless [spine_of: TC-5.0, spine_step_ref: S4]
**Data Strategy: REAL-DATA**. The real partial-result writer runs during a real window.
```
assert: fake codex returns first, its partial result lands in R mid-window → recorded co-tenant; no STOP; file intact
```

### TC-5.2: Co-tenant Codex write is never critic [spine_of: TC-5.0, spine_step_ref: S4]
**Data Strategy: MOCK-EXTERNAL**. Scope: Codex CLI side effect. why_impossible_to_reproduce_live: a live Codex write's timing is non-deterministic; the fake reproduces the incident ordering exactly.
```
assert: file preserved; window_log class co-tenant; no STOP
```

## US-6: Critic write captured, workspace discarded, STOP (M3)

### TC-6.0: Critic workspace write is captured byte-exact, discarded, STOP critic [spine: US-6]
**Data Strategy: MOCK-EXTERNAL**. Scope: Antigravity file-edit tool acting inside the real sandbox. why_impossible_to_reproduce_live: operator dispatch ban; a live critic's write cannot be forced.
spine_steps: S1 critic writes in its workspace, S2 inspection finds a delta beyond the read-only inputs, S3 evidence captured, S4 workspace discarded, S5 STOP
```
assert: incident.class == critic; captured bytes == written bytes; critic stdout/stderr captured; workspace path gone; stop_record written; exit_code == STOP
```

### TC-6.1: Critic write attempt into a repository fails at the kernel [spine_of: TC-6.0, spine_step_ref: S1]
**Data Strategy: MOCK-EXTERNAL**. Scope: Antigravity absolute-path write attempt (real sandbox). why_impossible_to_reproduce_live: operator dispatch ban.
```
given: the fake critic writes into R by absolute path, then exits 0 with a response
assert: tree_bytes unchanged in R (EROFS); no co-tenant delta recorded for that path; no STOP (workspace unchanged); response returned
```

### TC-6.2: Timeout path inspects the workspace first [spine_of: TC-6.0, spine_step_ref: S2]
**Data Strategy: MOCK-EXTERNAL**. Scope: Antigravity hang after write. why_impossible_to_reproduce_live: operator dispatch ban.
```
given: the fake critic writes in its workspace, then sleeps past the injected timeout
assert: STOP (not "timed out"); spawns == 1; the sandbox process tree is gone; only this process's own child was signalled
negative: sleep past timeout WITHOUT writing → ordinary timeout, retried (spawns == MAX_RETRIES), no incident
```

### TC-6.3: Clean critic run is unaffected [spine_of: TC-6.0, spine_step_ref: S2]
**Data Strategy: MOCK-EXTERNAL**. Scope: Antigravity critic. why_impossible_to_reproduce_live: operator dispatch ban.
```
assert: response returned; no incident; no stop_record; workspace removed
```

### TC-6.4: Evidence capture failure still STOPs and says so [spine_of: TC-6.0, spine_step_ref: S3]
**Data Strategy: SYNTHETIC**. The evidence location is made unwritable on purpose.
```
assert: STOP raised with "evidence incomplete"; workspace is NOT discarded (left for the operator); if the stop_record also cannot be written, the process exits with STOP naming both failures
```

## US-7: Boundary failure is terminal; no sandbox, no dispatch (M3)

### TC-7.0: Missing bwrap refuses dispatch, never falls back [spine: US-7]
**Data Strategy: SYNTHETIC**. A PATH without bwrap is manufactured.
spine_steps: S1 availability check before spawn, S2 refusal, S3 boundary self-probe inside sandbox, S4 boundary-failure STOP
```
assert: spawns == 0; distinct refusal naming "sandbox unavailable"; no incident; no stop_record
negative: no code path invokes agy outside bwrap (spawn log shows bwrap as parent of every fake-critic start across the whole suite)
```

### TC-7.1: bwrap setup failure is a boundary-failure STOP [spine_of: TC-7.0, spine_step_ref: S3]
**Data Strategy: SYNTHETIC**. The sandbox profile is forced to fail setup (e.g. a bind source that does not exist).
```
assert: spawns == 0 (critic never started); incident.class == boundary_failure; stop_record written; exit_code == STOP
```

### TC-7.2: In-sandbox write probe succeeding is a boundary-failure STOP [spine_of: TC-7.0, spine_step_ref: S3]
**Data Strategy: SYNTHETIC**. A deliberately broken profile binds the repo writable.
```
assert: the launcher's pre-exec probe write into the repo succeeds → critic never starts; probe file removed; incident.class == boundary_failure; STOP
paired: the correct profile → probe gets EROFS and the critic starts (TC-6.3)
```

### TC-7.3: Critic-only sentinel change is a boundary-failure STOP [spine_of: TC-7.0, spine_step_ref: S4]
**Data Strategy: SYNTHETIC**. A deliberately broken profile makes the read-only sentinel writable.
```
given: a per-dispatch sentinel outside the workspace, bound read-only and known only to that dispatch
when:  the fake critic modifies it
assert: incident.class == boundary_failure; STOP; stop_record
```

### TC-7.4: Missing kernel feature (no unprivileged userns) refuses [spine_of: TC-7.0, spine_step_ref: S1]
**Data Strategy: SYNTHETIC**. The availability probe is forced to report userns unavailable.
```
assert: spawns == 0; refusal names the missing feature; no fallback
```

## US-8: Deliberate integration and supervised canary (M5)

### TC-8.0: Reconciliation dry-run proves every user hunk survives [spine: US-8]
**Data Strategy: REAL-DATA**. The real dirty live tree is read only; the repair is applied to a throwaway copy.
spine_steps: S1 snapshot live dirty diff + untracked list + hash, S2 apply repair to a copy, S3 compare user hunks, S4 approval gate, S5 supervised canary
```
assert: every pre-existing user hunk and untracked file is present by content in the copy
negative: live tree and ~/.claude/skills path unchanged (mtime + hash)
```

### TC-8.1: Apply refuses without a matching approval [spine_of: TC-8.0, spine_step_ref: S4]
**Data Strategy: REAL-DATA**. The real apply procedure runs against a throwaway copy.
```
assert: no approval, or approval for another candidate diff hash → refuses before writing; copy unchanged
```

### TC-8.2: Live snapshot drift invalidates the approval [spine_of: TC-8.0, spine_step_ref: S4]
**Data Strategy: REAL-DATA**. Real live tree, hashed read-only.
```
assert: approval bound to snapshot H; live tree now hashes H' → apply refuses and names the drift
```

### TC-8.3: Supervised canary proves the live residue [spine_of: TC-8.0, spine_step_ref: S5]
**Data Strategy: REAL-DATA**. One real agy dispatch under its own operator approval, after landing.
```
assert: agy read the bound prompt (response references a canary nonce present only in the prompt) — U-1
assert: no agy-owned process outside the sandbox PID namespace during the window — U-10
assert: workspace delta after a no-write prompt is empty, or the observed byproducts are recorded for an operator profile decision — U-11
negative: without the canary approval record, the canary step refuses
```

## US-9: Operator inspects evidence (M4)

### TC-9.0: Incident evidence reproduces what the critic wrote [spine: US-9]
**Data Strategy: MOCK-EXTERNAL**. Scope: Antigravity critic mutation (real sandbox). why_impossible_to_reproduce_live: operator dispatch ban.
spine_steps: S1 STOP output names incident, class, path count, record, clear procedure, S2 operator reads evidence
```
assert: for every workspace path the critic created or changed, the captured bytes equal the bytes written; the input files are listed as read-only inputs, not deltas
```

### TC-9.1: STOP output is self-sufficient [spine_of: TC-9.0, spine_step_ref: S1]
**Data Strategy: MOCK-EXTERNAL**. Scope: Antigravity critic mutation. why_impossible_to_reproduce_live: operator dispatch ban.
```
assert: stderr names incident path, class, number of paths, stop_record path, clear procedure; no instruction to retry
```

## US-10: Explicit operator clear (M4)

### TC-10.0: Clear names the incident and is recorded; evidence stays [spine: US-10]
**Data Strategy: REAL-DATA**. Real record lifecycle.
spine_steps: S1 operator issues clear with incident id + name + reason, S2 clear recorded, S3 record removed, S4 evidence untouched
```
assert: clear_log has {incident, operator, reason, time}; stop_record absent; incident dir byte-identical
```

### TC-10.1: Clear with a mismatched incident id refuses [spine_of: TC-10.0, spine_step_ref: S1]
**Data Strategy: REAL-DATA**.
```
assert: record unchanged; refusal names the expected incident
```

### TC-10.2: Retries, new rounds, and flag defaults are never a clear [spine_of: TC-10.0, spine_step_ref: S1]
**Data Strategy: REAL-DATA**.
```
assert: retry, new round, --skip-preflight, every critique flag default → refused; stop_record and clear_log unchanged
```

## US-11: Inputs delivered read-only from outside every repository (M3)

### TC-11.0: Prompt is bound read-only inside the workspace [spine: US-11]
**Data Strategy: MOCK-EXTERNAL**. Scope: Antigravity prompt read (real sandbox). why_impossible_to_reproduce_live: operator dispatch ban; the live read path is canary residue (TC-8.3).
spine_steps: S1 dispatch root created outside every repo, S2 prompt + inputs bound read-only into workspace, S3 critic reads, S4 dispatch root removed
```
assert: the fake critic reads the prompt bytes exactly; its attempt to modify the bound prompt fails (EROFS); no path under any watched repo created
```

### TC-11.1: Oversized prompt never touches a repository and is removed [spine_of: TC-11.0, spine_step_ref: S2]
**Data Strategy: SYNTHETIC**. Needs a prompt exactly at and just above the inline limit.
```
given: prompt of inline_max + 1 bytes [BVA]
assert: prompt file lives under the dispatch root (outside every repo); R porcelain unchanged; dispatch root absent after return, after rc != 0, after timeout, after STOP
paired: prompt of exactly inline_max bytes → same delivery path or inline per design; no repo path either way [BVA]
```

### TC-11.2: Sibling dispatches never see each other's inputs or workspaces [spine_of: TC-11.0, spine_step_ref: S1]
**Data Strategy: REAL-DATA**. Two real overlapping sandboxed dispatches.
```
assert: distinct dispatch roots with owner-only permissions; each critic's view contains only its own inputs/workspace as writable/bound paths; no co-tenant delta recorded from sibling scratch
```

---

### State Transition Table — dispatch safety state (per repository, git common dir scope)
| # | From | Event | To | Action | Test |
|---|---|---|---|---|---|
| T1 | CLEAR | dispatch, workspace unchanged | CLEAR | return response, discard workspace | TC-6.3, TC-2.2 |
| T2 | CLEAR | non-mutation failure / clean timeout | CLEAR | bounded retry | TC-1.1, TC-6.2(neg) |
| T3 | CLEAR | critic workspace delta | STOPPED | capture, discard, STOP critic, write record | TC-6.0, TC-6.2 |
| T4 | CLEAR | co-tenant shared-tree delta | CLEAR | record in window_log, no halt | TC-5.0, TC-5.1, TC-5.2 |
| T5 | CLEAR | bwrap setup fails / probe write succeeds / sentinel changes | STOPPED | STOP boundary_failure, write record | TC-7.1, TC-7.2, TC-7.3 |
| T6 | CLEAR | sandbox unavailable | CLEAR | refuse before spawn, no record | TC-7.0, TC-7.4 |
| T7 | STOPPED | any dispatch attempt (same process) | STOPPED | refuse before spawn | TC-1.0, TC-2.0 |
| T8 | STOPPED | any dispatch attempt (fresh process, any worktree) | STOPPED | refuse, name record + incident | TC-4.0, TC-4.6, TC-3.2 |
| T9 | STOPPED | explicit operator clear naming the incident | CLEAR | record clear, keep evidence | TC-10.0 |
| T10 | STOPPED | wrong incident / retry / flag default | STOPPED | refuse | TC-10.1, TC-10.2 |
| T11 | STOPPED | corrupt record read | STOPPED | refuse, name record | TC-4.3 |

### Decision Table — delta classification
| # | Where the change is | Class | Halts? | Test |
|---|---|---|---|---|
| 1 | critic workspace (beyond read-only inputs) | critic | STOP + record | TC-6.0 |
| 2 | watched repository | co-tenant | no (window_log) | TC-5.0 |
| 3 | watched repository via critic absolute path | impossible (EROFS) → no delta | no | TC-6.1 |
| 4 | per-dispatch read-only sentinel | boundary_failure | STOP + record | TC-7.3 |
| 5 | in-sandbox probe write succeeded | boundary_failure | STOP + record | TC-7.2 |
| 6 | bwrap setup failed | boundary_failure | STOP + record | TC-7.1 |
| 7 | none | — | no | TC-6.3 |


---

# Appendix C — R1 synthesis (for context; v3 supersedes several dispositions)

# Roadmap debate R1 — synthesis

Critics: `codex/gpt-6-astra` (xhigh) and `claude-cli/claude-fable-5-1`. Raw output: `roadmap-debate-r1.json`, `roadmap-debate-r1-{codex,claude-cli}.md`.
Neither critic agreed; the author seat (Claude) accepted the findings listed below. There was also an aborted first attempt
(`roadmap-debate-r1-aborted-opus-relcwd.*`). That attempt put Opus in a critic seat, which is banned, and passed a relative
`--cwd`, which codex then resolved a second time. It produced no critique and none was used.

| # | Finding (source) | Disposition |
|---|---|---|
| 1 | Routine writers such as hooks and session-state make a fail-closed halt fire on every round (fable C1) | **Operator ruling:** a per-repo exact-path allowlist. Changes to allowlisted paths are recorded but do not halt. Tool-owned outputs are hash-verified, so bytes the tool did not write count as an ordinary delta (US-5, TC-5.4, TC-5.5) |
| 2 | Unattributed halt vs durable record is ambiguous (fable C2) | **Operator ruling U-7:** every STOP, attributed or not, writes the durable record. G-2, T4 and TC-5.0 updated |
| 3 | The operator journey ends at the STOP, and there is no clear act and no restore oracle (fable C3, astra 1) | Accepted: added US-9 (inspect evidence, restore) and US-10 (explicit clear), TC-9.0 (restore round-trip) and TC-10.x |
| 4 | "Per watched repo" is undefined for worktrees (fable C4) | **Operator ruling U-8:** the record lives in the git common dir. TC-4.1 gains a worktree variant, TC-4.6 |
| 5 | A test has two outcomes, TC-2.1 (fable H) | **Operator ruling U-4:** let the sibling finish, check it, quarantine its output. TC-2.1 is now single-outcome |
| 6 | The 5-minute budget conflicts with the timeout tests (fable H) | Accepted: an injectable dispatch timeout and retry delay are now M0 success criteria |
| 7 | Nothing proves independence from string matching (fable H) | Accepted: added TC-1.4, which randomises the STOP message |
| 8 | Persona coverage: the co-tenant session owner (fable M) | Accepted: added persona; the refusal must name the record and the incident (TC-4.0) |
| 9 | No Risks section and no post-repair endpoint (fable M, astra 8) | Accepted: added Risks, and made the post-landing supervised canary a named handoff with U-1 as residue |
| 10 | Integrations count (fable L) | Accepted: the agy CLI counts as an external integration, so the score is 16 and the tier stays complex |
| 11 | Restoring on location alone is unsafe; exclusive ownership is required (astra 2) | Accepted: restore happens only inside a surface created exclusively for that dispatch (TC-6.4) |
| 12 | Races (check vs spawn), evidence-write failure, failed restore, interrupted persistence (astra 3) | Accepted: added TC-4.7 (admission race), TC-6.5 (evidence write fails → no restore, still STOP), TC-6.6 (failed restore still STOPs) |
| 13 | Exact tool paths can hide mutations (astra 4) | Accepted: tool-owned outputs are content-hash verified (TC-5.4) |
| 14 | Offline proof is not live compatibility (astra 5) | Accepted: U-1 is a named release limitation, and the first live dispatch after landing is a supervised canary behind operator approval (US-8, TC-8.2) |
| 15 | Integration approval can go stale (astra 6) | Accepted: the gate binds candidate diff hash + live snapshot hash, and drift invalidates it (TC-8.2). Hunk preservation is defined by content |
| 16 | Network isolation, static gate proof, underspecified variants (astra 7) | Accepted: the network-deny run is optional-but-recorded (TC-0.2). TC-8.1 is now behavioural (the apply step refuses without a matching approval). Variants gained setup lines |
| 17 | Wants a product PRD rather than a technical roadmap (astra 8) | Partially accepted: added operator journey, personas and risks. Depth stays `technical` per the session doc depth, and the pseudocode stays in the companion tests-pseudo |
