## Round 2 critique

The v3 roadmap is much stronger than v2. The bwrap redirect removes the root cause, which was timing-based attribution, instead of patching it. But the redirect left stale material behind, one goal contradicts itself, and the operator and agent journeys still stop too early. I'm not agreeing yet.

### Critical

**C1. The appendices contradict the v3 roadmap.**
- **Appendix A is still v2.**
  - SC-1 still says "critic-owned delta restored". SC-2 still labels deltas "unattributed". F-5 and F-6 still describe snapshot attribution and "never revert".
  - U-8 is used as a decision everywhere but never defined in the unknowns list.
- **Appendix C cites things that no longer exist.**
  - The allowlist (row 1) and "every STOP writes the record" (row 2) are gone.
  - "Restore" (rows 3 and 11) is gone.
  - Tests TC-5.4, TC-5.5, TC-6.5 and TC-6.6, and the "network-deny" part of TC-0.2, don't exist in v3.

Anyone reading only the appendices would build the wrong system. Every superseded row needs an explicit supersession marker.

**C2. G-1 is false as written.** It says the critic's "only writable surface is its own workspace". The mechanism section makes `~/.antigravity` and `~/.gemini` writable too.

These directories are also shared:
- across parallel siblings
- with the operator's own interactive agy use
- across dispatches over time

So a critic can persist changes that affect later dispatches or the operator's own tooling. U-12 defers the policy, but the goal can't claim containment it doesn't provide. Fix: state the goal honestly, require a per-dispatch config-dir manifest (already listed as a risk mitigation) as a success criterion with a test, and keep the policy as U-12.

**C3. An agent can defeat the operator-only clear with `rm`.**
- The orchestrator agent is a named persona, and it has filesystem access to the git common dir.
- Deleting `stop_record` restores dispatch without any clear. Nothing in the spec detects this.
- This is exactly the "maintainer/agent reopens the path" failure the personas section warns about.

Fix: admission refuses if *any* incident directory lacks a matching `clear_log` entry. The record becomes a fast-path index, and the incident directory becomes the authority. Add a story and a test (US-12 and TC-10.3 below).

**C4. There is no journey for the agent that receives the STOP.**
- The orchestrator is the first to see stderr, and today it is the actor most likely to "work around" a STOP: retrying, swapping flags, re-running the round.
- Nothing says what the agent must do or how the operator learns about the STOP when not watching the terminal.

Fix: add a story (US-12 below). The STOP outcome must be machine-distinguishable, give the agent explicit "report and halt" guidance, and not give retry advice.

### High

**H1. The journey after a clear is missing.** US-10 ends at "dispatch resumes". G-3 forbids a round checkpoint for the stopped round, but nothing says how the Session continues. Fix: add a success criterion that after a clear, the stopped round re-runs from the last good checkpoint with no manual state repair.

**H2. The journey when the Google seat is unavailable is missing.** If the canary fails, agy stays refused. What happens to rounds that name an agy critic? Do they:
- fail loudly?
- run without the seat?
- silently drop it?

"Silently drop it" would hide lost debate diversity. Fix: the round refuses before any dispatch and names the seat and the reason. Substituting a model is an explicit operator choice; no automatic routing change, which is consistent with the non-goal.

**H3. Attempted repo writes are invisible.** TC-6.1 and decision-table row 3 treat a critic's attempted write into the repo (EROFS) as "no delta, no STOP, nothing recorded". Containment holds, but a critic that *tried* to mutate a repo is exactly what the operator wants to know. The non-goal "hiding attribution uncertainty" applies here. Fix:
- Record what can be observed without halting: the critic streams that mention the write failure, plus the response.
- Carry out-of-band detection as residue U-13.
- Change TC-6.1's assertion from "nothing" to "no halt; streams retained in the window log".

**H4. There are no outcome KPIs.** Every success criterion checks a test. None measures whether the repair works in use. Add:
- zero lost co-tenant bytes
- the false-STOP rate over the first N live dispatches (target 0; any non-zero rate forces a profile review)
- time from STOP to informed operator decision

### Medium

**M1. Boundary-failure severity may over-halt.** Under T5, a bwrap setup failure *before the critic ever starts* (TC-7.1) is a durable STOP that needs an operator clear. Under T6, a missing bwrap is just a refusal. In both cases nothing ran, so nothing escaped. This was an operator ruling, so I keep it. But I flag it as risk R-8: a transient setup error could halt every worktree in the repo. The operator should confirm.

**M2. Minor gaps.**
- There is no non-functional requirement for sandbox overhead (latency per dispatch, disk per workspace).
- TC-4.5 is a numbering gap; mark it retired so it isn't read as a missing test.

[SPEC]
# Roadmap: AGY Tripwire Stop — critic safety contract repair

> v4, 2026-09-24. Round 2 revisions:
> - G-1 is restated honestly; the config dirs are writable.
> - Tamper-resistant clear (the incident directory is the authority).
> - New stories: US-12 (agent that receives a STOP) and US-13 (seat unavailable).
> - Post-clear resume.
> - Attempted-write recording (U-13).
> - Outcome KPIs.
> - Appendix supersession fixed.
>
> v3 was the G1 redirect to OS-level isolation (bwrap). v2 (debate R1 rulings) is superseded where marked in Appendix C.

Session `adv-spec-202609240523-agy-tripwire-stop` · card 21616 · altitude **system** · complexity **complex**. The score is 16:

| Driver | Points |
|---|---|
| User types | 4 |
| Feature groups | 7 |
| External integration (Antigravity CLI), counted ×2 | 2 |
| Open unknowns | 3 |

Requirements: `../requirements.md`. Tests (canonical): `../tests-pseudo.md`.

### Mechanism (operator decision, 2026-09-24)
**The rule.** Every Antigravity dispatch, preflight included, runs inside a bubblewrap sandbox.
- The whole filesystem is bound read-only.
- The only writable paths are a fresh per-dispatch workspace and the agy config/auth directories (`~/.antigravity`, `~/.gemini`).
- The prompt and inputs are bind-mounted read-only into the workspace.
- The critic cannot write to any repository, so repo attribution is structural and never timing-based.
- The config dirs remain a writable surface outside the workspace. They are governed by the per-dispatch manifest (G-1) and the U-12 policy.

**Evidence.** `bwrap --ro-bind / / … --bind <ws> <ws>` turned a repo write into `Read-only file system`, while a workspace write succeeded. The operator tested this and the conductor re-verified it on 2026-09-24 (bwrap 0.6.1, unprivileged userns + Landlock enabled).

agy's own `--sandbox` is not a boundary (`skills/adversarial-spec/scripts/models.py:868`).

### Personas
- **Operator (Jason).** The only person who can clear a STOP. Needs to:
  - learn that a STOP happened, including when not watching the terminal
  - see what the critic wrote or which part of the boundary failed
  - clear the STOP deliberately
  - resume the stopped work
- **Orchestrator agent.** The Claude/Codex/Gemini seat running a round. It writes into the same worktree while critics run.
  - Its bytes must never be lost, blamed, or treated as halting.
  - It is also the first to receive a STOP, and it must neither work around the STOP nor clear it.
- **Co-tenant session owner.** Another session in the same repository.
  - It must not be halted by someone else's writes.
  - When someone else's STOP refuses its dispatch, the refusal must name the incident.
- **Maintainer.** Runs the offline suite. Must not be able to reopen the retry path, an unsandboxed path, or a clear-free resume path by:
  - adding a catch site
  - adding a flag
  - deleting a file

### Goals
**G-1 Critic writes to repositories are impossible by construction, and every other critic write is visible.**
- The critic has two writable surfaces: its own per-dispatch workspace and the agy config dirs.
- After every dispatch:
  - The workspace is inspected, its contents are captured as evidence, and it is discarded. No restore is needed.
  - A config-dir change manifest is recorded.
- Any workspace write beyond the read-only inputs is a critic-attributed mutation and ends in a STOP.
- Config-dir changes are recorded as evidence. Whether they halt is decided by U-12.

**G-2 A shared-tree delta during an agy window belongs to a co-tenant.**
- It is preserved, recorded as `co-tenant`, and never halts the round.
- A fail-closed STOP fires only on evidence that the boundary itself failed:
  - a critic-only sentinel changes
  - the in-sandbox write probe succeeds
  - bwrap setup fails (see R-8)

**G-3 A critic-attributed mutation or a boundary failure is a terminal STOP.**
- Nothing follows it: no retry, no synthesis, no round checkpoint, no sibling spawn, and no further Antigravity dispatch (preflight included).
- This holds in the stopping process and in any fresh process against any worktree of the same repository.
- It lasts until an explicit, recorded operator clear.
- Deleting the stop record is not a clear. Admission also refuses on any incident that has no matching clear entry.

**G-4 No sandbox, no dispatch.** If bwrap, or the kernel features it needs, is unavailable, the dispatch refuses before spawning. There is never an unsandboxed fallback.

**G-5 Offline proof.** An offline regression suite proves G-1..G-4 with paired negative oracles. It runs the real bwrap boundary against a scripted fake critic, with no network and no live critic.

**G-6 Deliberate landing.**
- Landing on the user-owned dirty live tree goes through a named, operator-approved gate.
- The gate is bound to the candidate diff hash and the current live snapshot hash, and it proves no user hunk is overwritten.
- The first live dispatch after landing is a supervised canary with its own approval. It carries the live-proof residue (U-1, U-10, U-11).

**If agy cannot run inside the sandbox**, G-1 does not degrade to the old tripwire. This covers two cases: the canary cannot read its bound prompt, or agy refuses a read-only home.
- Antigravity dispatch stays refused.
- The Google-family seat is unavailable, handled as in US-13, until the sandbox profile is amended and a new canary passes.

### Non-Goals
- Resuming, mutating or completing `adv-spec-202607060132-post-fable-hardening-skill`, or anything in the Brainquarters Jev session.
- Editing `/home/jason/PycharmProjects/adversarial-spec` or `~/.claude/skills/adversarial-spec`, deploying, or pushing/merging without explicit integration approval.
  - Local commits are allowed only on `adv-spec/agy-tripwire-stop-20260924` and on per-candidate branches off it.
  - This operator ruling (2026-09-24) relaxes handoff line 42.
- Any Antigravity dispatch, preflight included, before the repaired contract lands and the operator clears the canary.
- Weakening containment, hiding attribution uncertainty, or using string-matching as the sole stop protocol.
- Automatic model substitution when the agy seat is unavailable, and broad model-routing changes.
- Secrets/config edits and global process kills.
- Repairing fizzy-pipeline-mcp's own agy runner. That is U-6, residue for that repo.

### Milestone 0: Getting Started (Bootstrap)
- **US-0:** As a maintainer, I want one offline command that runs the agy-safety suite against a scripted fake critic inside the real sandbox, so that I can verify the contract without network, credentials, or a live Antigravity dispatch.

Success criteria:
- [ ] One documented command runs the suite from a clean checkout in under 5 minutes on the dev workstation.
- [ ] Dispatch timeout and retry delay are injectable, so timeout and retry cases run in seconds.
- [ ] The suite refuses to run if the real `agy` binary would be reached.
- [ ] If bwrap is unavailable on the test host, the sandbox cases report `unsupported`. They are never silently skipped.

Tests: TC-0.0 (spine) … TC-0.2. **Dependencies:** none.

### Milestone 1: STOP is terminal inside one process
- **US-1:** As the operator, I want a STOP raised during a debate critique to end that round with a distinct outcome, with no retry and no synthesis, so that no critic dispatch follows a STOP-class event.
- **US-2:** As the operator, I want a STOP in any gauntlet attack, or in a later gauntlet-internal phase, to block every not-yet-started Antigravity spawn in that run and record a stop status, so that parallel dispatch cannot continue past a STOP.
  - Siblings that are already running finish, are inspected, and have their output quarantined (U-4).
- **US-3:** As the operator, I want the preflight ping treated as a real dispatch, so that the cheap ping cannot bypass the contract. The preflight must:
  - be sandboxed
  - honour the round's working directory
  - obey the latch and the stop record
  - surface a STOP as a STOP

Success criteria:
- [ ] After a STOP, the fake critic's spawn count stays at its pre-STOP value on every path: retry, queued sibling, later phase, preflight.
- [ ] Non-mutation failures (non-zero exit, empty output, clean timeout) keep today's bounded retry.
- [ ] Stop handling does not depend on message text (proven with a randomised message).

Tests: TC-1.0 … TC-3.3. **Dependencies:** M0.

### Milestone 2: STOP survives the process, and only a clear ends it
- **US-4:** As a co-tenant session owner, I want a fresh process against any worktree of the same repository to refuse Antigravity dispatch before spawning, preflight included, and to name the stop record and the incident, so that I know why and do not retry blindly.

Success criteria:
- [ ] Every critic-mutation or boundary-failure STOP leaves two durable items in the repository's git common dir: an incident directory and a stop record that references it.
- [ ] Every entry point checks admission under an admission lock before spawning. Admission refuses on any of these:
  - a present record
  - a corrupt record
  - any incident directory without a matching `clear_log` entry, even when the record is absent
- [ ] Other repositories are not blocked. Sibling worktrees of the same repository are blocked.

Tests: TC-4.0 … TC-4.7 (TC-4.5 retired). **Dependencies:** M1.

### Milestone 3: Sandbox boundary and truthful attribution
- **US-5:** As an orchestrator agent, I want my writes, Codex's writes and the tool's writes into the shared worktree during an agy window left untouched, recorded as `co-tenant`, and never halting, so that concurrent work survives and nobody blames the critic for it.
- **US-6:** As the operator, I want any critic write inside its workspace captured byte-exact before the workspace is discarded and turned into a STOP labelled `critic`, including on the timeout path, so that genuine mutations stay visible and stop the run.
- **US-7:** As the operator, I want boundary failure detected and treated as a terminal STOP, and a missing sandbox to refuse dispatch, so that containment never silently degrades.
  - Boundary failure means any of: bwrap setup fails, the in-sandbox write probe succeeds, or a critic-only sentinel changes.
- **US-11:** As the operator, I want the prompt and inputs delivered read-only inside the dispatch workspace from a dispatch root outside every repository, so that oversized prompts never touch a repository and siblings never see each other's scratch.

Success criteria:
- [ ] No code path unlinks, overwrites, or runs `git checkout` on any path in a watched repository.
- [ ] Every incident states its class (`critic` | `boundary_failure`) and carries the captured workspace bytes and the critic streams.
- [ ] Co-tenant deltas appear in the window log, never as an incident.
- [ ] Every dispatch records a config-dir change manifest (paths plus before/after hashes) as evidence (U-12).
- [ ] When the critic attempts a write that the kernel refuses, nothing halts. The critic streams and response are retained in the window log so that the attempt stays visible (U-13).
- [ ] The timeout path inspects the workspace before it reports the timeout.
- [ ] The sandbox process tree dies with its parent, and only this process's own child is signalled.

Tests: TC-5.0 … TC-7.4, TC-11.0 … TC-11.2, TC-6.5 (new, below). **Dependencies:** M1. Independent of M2.

### Milestone 4: Operator and agent recovery
- **US-9:** As the operator, I want the STOP output and incident record to tell me what the critic wrote or which boundary check failed, and where the evidence is, so that I can decide without re-running anything.
- **US-10:** As the operator, I want an explicit clear act that names the incident being cleared and records who cleared it, when and why, without deleting evidence, so that dispatch resumes only by my deliberate choice.
  - After the clear, I want to re-run the stopped round from the last good checkpoint without repairing any state by hand.
- **US-12:** As an orchestrator agent that receives a STOP, I want a machine-distinguishable outcome and explicit "report to the operator and halt" guidance with no retry advice, so that I surface the incident instead of working around it, and the operator learns about it even when not at the terminal.
- **US-13:** As an orchestrator agent whose round names an agy critic while agy is refused, I want the round to refuse before any dispatch and name the unavailable seat and the reason, so that debate diversity is never silently lost and any substitute model is the operator's explicit choice.

Success criteria:
- [ ] The captured workspace evidence reproduces the critic's written bytes exactly.
- [ ] The clear refuses without the matching incident identifier. None of these is ever a clear:
  - a retry
  - a new round
  - a flag default
  - deleting the stop record
- [ ] After a clear, re-running the stopped round succeeds from the last good checkpoint.
- [ ] A STOP has a distinct exit code. Its stderr carries the incident path and an operator-notification line in the project's established notification format. It never suggests a retry.
- [ ] A round that needs an unavailable agy seat refuses with spawns == 0 for every model, and names the seat and the reason.

Tests: TC-9.0 … TC-10.4, TC-12.0, TC-13.0 (new, below). **Dependencies:** M2, M3.

### Milestone 5: Deliberate integration and supervised canary
- **US-8:** As the operator, I want a reconciliation plan that lands the repair onto the dirty `bounded-pipeline-reform` tree through an explicit approval gate, then runs one supervised live canary dispatch under its own approval, so that no user change is overwritten and the sandbox is proven live before routine use.
  - The gate is bound to the candidate diff hash and the current live snapshot hash.

Success criteria:
- [ ] The plan names the gate, the approver, the exact order, the rollback, and the content-based hunk-preservation check.
- [ ] Apply refuses without a matching approval and snapshot hash. Nothing touches the live tree before approval.
- [ ] The canary records three results, and each one decides whether dispatch is re-enabled:
  - the U-1 read path
  - U-10: no out-of-sandbox helper
  - U-11: agy runtime byproducts
- [ ] The canary also records the config-dir manifest, to inform the U-12 policy.

Tests: TC-8.0 … TC-8.3. **Dependencies:** M1–M4 green.

### Outcome metrics (post-landing)
| KPI | Target | Measured by |
|---|---|---|
| Co-tenant bytes lost or overwritten during agy windows | 0 | window_log vs. tree hashes, first 30 live dispatches |
| False STOP rate (a STOP whose evidence shows no critic write or boundary failure) | 0. Any occurrence forces a profile review before further dispatch | incident review |
| STOPs followed by any spawn before a clear | 0 | spawn log vs. clear_log |
| Operator time from STOP to informed decision | No re-run needed to decide (qualitative, per incident) | clear_log reason field |
| Added dispatch overhead from the sandbox | < 2 s per dispatch at the median | launcher timing in the window log |

### Non-functional
- **NF-1 Offline suite.** The regression suite runs offline: no network, no live critic.
- **NF-2 Real oracles.** Tests assert observable behaviour with paired negative oracles. No mock echoes or source-text pins.
- **NF-3 Readable, not parsed.** STOP messages are human-readable, but no control flow depends on their text.
- **NF-4 Bounded overhead.**
  - Sandbox overhead stays under 2 s per dispatch at the median.
  - The per-dispatch workspace and dispatch root are removed on every exit path except the evidence-capture failure in TC-6.4.

### Scenario → story map (handoff acceptance criterion 2)
| Scenario | Outcome | Story | Spine / variant |
|---|---|---|---|
| SC-1 real critic mutation | captured, workspace discarded, STOP `critic`, durable record | US-6 | TC-6.0 |
| SC-2 non-critic shared write | preserved, recorded `co-tenant`, no halt | US-5 | TC-5.0 |
| SC-3 timeout | workspace inspected first; mutation → STOP, clean → ordinary retryable timeout | US-6 | TC-6.2 |
| SC-4 parallel/sibling | separate workspaces; queued siblings blocked; running siblings finish + quarantine | US-2, US-11 | TC-2.0, TC-2.1, TC-11.2 |
| SC-5 oversized-prompt scratch | lives in a dispatch root outside every repo, read-only bind; removed after | US-11 | TC-11.1 |
| SC-6 preflight | sandboxed, round cwd, latch + record honoured, STOP surfaced as STOP | US-3 | TC-3.0 |
| SC-7 fresh process after STOP | refused before spawn in every worktree of the repo until operator clear; record deletion doesn't bypass | US-4, US-10 | TC-4.0, TC-10.3 |
| SC-8 agent receives STOP | reports and halts, never retries | US-12 | TC-12.0 |
| SC-9 agy seat unavailable | round refuses before dispatch, names seat | US-13 | TC-13.0 |

### Risks and mitigations
| # | Risk | Mitigation |
|---|---|---|
| R-1 | agy cannot read a read-only bound prompt, or needs a writable home (U-1) | No fallback. Dispatch stays refused (US-13). The canary proves the path before re-enable (TC-8.3). |
| R-2 | agy delegates file writes to a helper process outside the sandbox, so writes appear as `co-tenant` (U-10) | New PID/IPC namespaces and die-with-parent. The canary checks for out-of-sandbox helper processes. Residue until proven. |
| R-3 | agy writes runtime byproducts into its cwd, so every dispatch STOPs (U-11) | The canary observes this. If the byproducts are benign, an operator amendment moves the runtime dir to a config bind. Never an allowlist in the workspace. |
| R-4 | Critic persists behaviour changes in the writable config dirs (U-12), which are shared with siblings and the operator's own agy | Per-dispatch config-dir manifest as evidence (M3 criterion). Policy decided in D0/debate. |
| R-5 | A new catch site reopens retry | The typed stop cannot be absorbed by ordinary-error handlers (TC-1.3) and does not depend on message text (TC-1.4). |
| R-6 | Admission race between processes | Admission check and record write are serialized under a lock in the git common dir (TC-4.7). |
| R-7 | Landing overwrites user hunks on the dirty live tree | Snapshot-bound approval gate, content-based hunk check, rollback (US-8). |
| R-8 | A transient bwrap setup failure (before the critic starts) becomes a durable, repo-wide STOP and over-halts | Keeps the operator ruling (G-2). Flagged for the operator to confirm. The alternative is to reclassify pre-exec setup failure as a T6-style refusal. |
| R-9 | An agent or maintainer deletes the stop record to resume | Admission treats any incident without a matching clear as blocking (TC-10.3). |
| R-10 | Critic attempts a repo write that is contained silently, so the attempt stays invisible (U-13) | Streams retained in the window log (TC-6.5). Out-of-band detection is residue. |

### Architecture impact
`extends_existing`. The contracts are:
- a sandboxed dispatch launcher (a new module inside the models layer)
- the typed stop signal and the dispatch latch
- the git-common-dir incident directory, stop record, admission lock and clear
- the incident classes
- the STOP and seat-unavailable exit codes

All of them sit inside the existing models/providers, debate/session and gauntlet components. No new service. See `manifest.json#architecture_impact`.

### Open unknowns carried into decomposition
- **Carried:**
  - U-5: landing order onto the dirty tree.
  - U-6: fizzy runner residue.
  - U-10 / U-11: canary residue.
  - U-12: config-dir write policy.
  - U-13 (new): detecting attempted critic writes that the kernel refused.
  - R-8: operator confirmation of the setup-failure severity.
- **Resolved by design:** U-1, through the sandbox. Its live proof is canary residue.
- **Decided (defined here so the references resolve):** U-8. The stop record, incidents and clear_log live under `git rev-parse --git-common-dir`.

---

## Appendix changes required by v4 (apply to `requirements.md` / `tests-pseudo.md`)

**Appendix A (RequirementsSummary): align it with v3/v4.**
- **SC-1:** "evidence captured; critic workspace discarded (no restore); STOP raised; no further agy dispatch".
- **SC-2:** "bytes never deleted or overwritten; recorded `co-tenant`; never halting".
- **F-5:** "Structural attribution via bwrap: the repo is read-only to the critic, and the critic has a per-dispatch workspace. Shared-tree deltas are `co-tenant`."
- **F-6:** "Tool-owned writes are co-tenant deltas: recorded, never reverted, never halting."
- **Unknowns:** add U-8 (as defined above), U-12 and U-13.

**Appendix C (R1 synthesis): add a "v3/v4 status" column.**

| Row | Status |
|---|---|
| 1 (allowlist) | SUPERSEDED by the G1 redirect: the co-tenant class makes the allowlist unnecessary. TC-5.4/5.5 retired. |
| 2 (every STOP writes the record) | SUPERSEDED: narrowed U-7. Only critic or boundary_failure STOPs write the record. |
| 3 (restore) | Restore SUPERSEDED: nothing to restore, because the workspace is discarded. US-9/US-10 retained. TC-9.0 is now an evidence round-trip. |
| 11–13 | SUPERSEDED: no restore, no allowlist. TC-6.5/6.6 from v2 retired; the TC-6.5 id is reused below. |
| 16 | The network-deny run is dropped. TC-0.2 is now bwrap-unavailable reporting. |
| All others | Carried. |

**New and changed tests.**
- **TC-4.5:** marked `retired (v2 id, not reused)`.
- **TC-6.1 (changed).** Unchanged: the assertions on tree bytes, EROFS, and "no STOP". Added assertion: the critic streams and response are retained in the window log for that dispatch, which makes U-13 visible.
- **TC-6.5 (new) [spine_of: TC-6.0, S2]. REAL-DATA.**
  - Given: the fake critic modifies a file under the bound config dir.
  - Assert: the manifest lists the path with before/after hashes. No STOP pending the U-12 policy.
  - Negative: a config dir that is not touched gives an empty manifest.
- **TC-10.3 (new) [spine_of: TC-10.0, S1]. REAL-DATA.**
  - Given: a STOP, after which `stop_record` is deleted by hand with no clear.
  - Assert: the next process refuses (spawns == 0) and names the uncleared incident.
  - Paired: after a proper clear, the process dispatches.
- **TC-10.4 (new) [spine_of: TC-10.0, S4]. REAL-DATA.**
  - Given: a clear of the incident that stopped round N.
  - Assert: re-running round N from the last good checkpoint completes, with no manual state edits.
- **TC-12.0 [spine: US-12]. MOCK-EXTERNAL** (operator dispatch ban).
  - Assert: the STOP exit code is distinct from every other code, and stderr contains the incident path and a notification line.
  - Negative: stderr contains no retry or rerun suggestion.
- **TC-13.0 [spine: US-13]. SYNTHETIC** (agy refused via missing bwrap).
  - Given: a round with an agy critic and a codex critic.
  - Assert: spawns == 0 for both; the error names the agy seat and the reason.
  - Negative: the round does not proceed with codex alone.

**State transition table: add two rows.**
- **T12:** STOPPED → dispatch attempt with the record deleted and the incident not cleared → STOPPED (refuse). Test: TC-10.3.
- **T13:** CLEAR, agy seat refused (sandbox unavailable) → round refuses before any dispatch. Test: TC-13.0.
[/SPEC]