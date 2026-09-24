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
