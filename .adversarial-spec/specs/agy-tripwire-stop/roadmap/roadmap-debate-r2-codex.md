Not ready for approval. The document has meaningful user stories and strong incident evidence, but several acceptance criteria permit behavior that violates its stated goals.

This review assesses the supplied requirements. The historical incident and workstation demonstration are reported evidence, not independently reproduced here.

1. **CRITICAL — The journey from first use to productive use is incomplete.**  
   M0 describes maintainer verification; M5 describes integration. Neither defines where a new maintainer discovers the procedure, how the operator determines whether dispatch is available, or how unsupported hosts, authentication failure, STOP clearance, and canary approval differ. The recovery journey also ends prematurely for corrupt records or incomplete evidence. Add one connected journey with an outcome and next actor at each refusal.

2. **CRITICAL — G-1 contradicts the writable configuration exception.**  
   G-1 says the critic’s only writable surface is its workspace. The mechanism also permits writes to persistent `~/.antigravity` and `~/.gemini`. US-6 can therefore succeed while persistent behavior changes escape its inspection and STOP rules. Moving runtime byproducts into these directories does not resolve this conflict. U-12 is a release-blocking product decision, not a detail safely deferred to decomposition.

3. **CRITICAL — Structural attribution is asserted before the complete boundary is established.**  
   The demonstrated read-only repository mount establishes a narrower property than “the critic cannot cause repository writes.” Bubblewrap’s documentation explicitly warns that exposed host service sockets can permit commands outside the sandbox. PID/IPC isolation and observing no new external helper do not establish that an existing service cannot perform a write. That is an inference from the documented boundary limitations, not an observed exploit here. [Bubblewrap security guidance](https://github.com/containers/bubblewrap#limitations)

   US-11 has a related gap: binding the host root read-only can leave sibling directories readable. Owner-only permissions do not separate critics operating as the same host user. TC-11.2 must attempt sibling reads, not merely confirm different writable paths. [Bubblewrap 0.6.1 documentation](https://github.com/containers/bubblewrap/blob/v0.6.1/README.md#sandboxing)

4. **CRITICAL — Durable STOP is not guaranteed on the specified failure path.**  
   TC-6.4 allows exit when neither evidence nor the stop record can be written. A later process can then encounter no record and dispatch, violating G-3. Unexpected termination before inspection creates the same unanswered question. Admission must remain recoverably blocked after an interrupted or unrecordable outcome. This need not falsely classify uncertainty as critic misconduct.

5. **CRITICAL — The admission-race oracle weakens the no-spawn guarantee.**  
   TC-4.7 permits a dispatch “admitted strictly before” STOP to count as in flight, although it may not have started. G-3 prohibits a new spawn after STOP. Admission and actual start must have unambiguous ordering; reservation alone cannot create an exception. Clear also needs defined behavior while earlier siblings remain active or produce additional incidents.

6. **HIGH — Final workspace inspection cannot establish “any write.”**  
   A critic can create and delete a file, or change and restore content, leaving no final delta. TC-6.0 only tests retained changes. Either explicitly narrow G-1 through an operator-approved amendment or retain the stronger requirement and add transient-mutation acceptance cases. Likewise, “byte-exact evidence” must distinguish retained content from historical bytes that were never captured.

7. **HIGH — Operator recovery lacks authority and concurrency rules.**  
   Supplying an operator name is attribution, not proof of operator approval. US-10 also does not address multiple incidents, a corrupt incident identifier, clear racing with a new STOP, or interruption between recording the clear and reopening admission. A clear must apply to the complete current incident set and require verifiable operator authorization.

8. **HIGH — Several requirements and negative oracles conflict.**

   - TC-7.2 removes a probe file from a repository; M3 prohibits safety code from unlinking any watched repository path.
   - TC-11.1 requires dispatch-root removal after every STOP; TC-6.4 requires retaining recoverable evidence after capture failure.
   - G-3 says “nothing follows,” while necessary sibling inspection, quarantine, and incident persistence must follow.
   - Appendix A still requires restoration and `unattributed` classification; v3 requires disposable workspaces and `co-tenant`.
   - A no-write canary that produces unexpected byproducts is unresolved or failed—not a passing alternative merely because those byproducts were recorded.

9. **HIGH — Integration preservation and release readiness remain underspecified.**  
   Finding old hunk text in a copy does not establish preservation of deletions, renames, permissions, binary changes, or untracked contents. Snapshot validation also needs protection against changes during application and rollback. Because source edits are immediately live, routine dispatch must remain disabled throughout landing and canary evaluation.

10. **MEDIUM — Product requirements and implementation design are mixed together.**  
    The technical depth is intentional, as Appendix C explains. Retain that material in its technical companion, but provide a product contract covering user outcomes, dependencies, availability, recovery, and release metrics. The current suite has useful targets; it still needs explicit acceptance for the missing failure paths above.

[SPEC]

**AGY Tripwire Stop — proposed revised product requirements**

Session: `adv-spec-202609240523-agy-tripwire-stop`  
Card: `21616`  
Scope: system-level repair of Antigravity dispatch safety.

This revision preserves the operator’s decisions to require bubblewrap, prohibit unsandboxed fallback, coordinate STOP across repository worktrees, and require separate integration and canary approvals.

The configuration policy below is a **proposed resolution of U-12 requiring operator ratification**. This document grants no integration, dispatch, deployment, push, or merge approval.

**Executive summary.** Antigravity critiques must preserve concurrent work, contain critic mutations, and stop affected runs without retrying or producing a completed result. A confirmed safety incident blocks subsequent Antigravity dispatches across all worktrees of the repository until an authorized operator clear. Unsupported or unresolved safety conditions refuse dispatch with an actionable explanation.

Success means operators can distinguish a usable critique, an ordinary model failure, an unavailable sandbox, an unresolved safety condition, and a confirmed STOP without rerunning the critic.

**Problem and evidence.** The supplied incident report describes a timing-based attribution mechanism that deleted the orchestrator’s 2,519-byte critique, followed by a retry after STOP. It also reports paths that reduced STOP to ordinary error text and continued toward synthesis.

These reports establish the repair’s motivation. They do not establish how frequently the failures occur across consuming projects. Release validation must reproduce the incident shapes through observable behavior.

**Target users.**

| Persona | Context and need |
|---|---|
| Operator, Jason | Owns integration, canary, and clear decisions; needs sufficient evidence and a precise next action. |
| Orchestrator agent | Runs debates or gauntlets while writing legitimate work; needs preserved output and unmistakable terminal outcomes. |
| Co-tenant session owner | Works concurrently in the same repository; needs uninterrupted ordinary work and an explanation when a repository STOP blocks Antigravity. |
| Maintainer | Develops the repair without live credentials or critic access; needs a documented, reproducible safety suite and stable acceptance rules. |

**Goals.**

- **G-1 — Containment:** Critics cannot change repository contents or persistent host configuration through the supported dispatch environment. Unexpected critic workspace mutations produce STOP. Any permitted runtime writes have an explicit, approved policy.
- **G-2 — Preservation and truthful attribution:** Safety handling never restores, deletes, or overwrites co-tenant work. Shared-tree changes are non-halting `co-tenant` observations when the boundary remains established; uncertainty is never presented as proven attribution.
- **G-3 — Terminal, durable STOP:** Confirmed critic mutation or boundary failure ends the affected run and blocks subsequent Antigravity starts across the repository until authorized clearance.
- **G-4 — Safe refusal:** Missing prerequisites or unresolved safety state prevent dispatch. There is no unsandboxed fallback.
- **G-5 — Reproducible verification:** An offline suite exercises the real containment boundary and production dispatch paths with a scripted critic and paired negative oracles.
- **G-6 — Deliberate release:** Integration preserves existing user changes, and routine dispatch remains unavailable until the approved live canary passes.
- **G-7 — Usable operation:** A new maintainer can find the verification procedure; an operator can understand availability, inspect incidents, and recover without rerunning the failed critic.

**Scope and non-goals.** In scope are Antigravity dispatches through this project’s debate, gauntlet, retry, parallel-dispatch, and preflight paths; repository-wide STOP coordination; evidence; recovery; offline validation; and controlled integration.

Out of scope are:

- The post-Fable and Brainquarters Jev sessions.
- The independent Antigravity runner in `fizzy-pipeline-mcp`.
- Broad model-routing changes, credential editing, global process control, and general protection against a malicious host administrator.
- Live-tree edits, deployment, pushing, or merging without the existing explicit approval requirements.

Local commits remain limited to `adv-spec/agy-tripwire-stop-20260924` and its candidate branches.

**User journey.**

1. **Discover and verify.** Existing project usage documentation and CLI help link to one safety runbook. A new maintainer runs its documented offline command. It reports pass, failure, or unsupported prerequisites, with the responsible next actor. A passing run is the maintainer’s first value.
2. **Prepare release.** The maintainer produces a validated candidate, a reconciliation preview, and preservation evidence. Routine Antigravity dispatch remains disabled.
3. **Approve integration.** Jason reviews the exact candidate and live snapshot. Application proceeds only under matching approval and preservation conditions.
4. **Run the supervised canary.** A separate approval permits exactly the identified canary dispatch. Approval does not bypass an outstanding STOP. Failed or inconclusive checks leave routine dispatch disabled.
5. **Use productively.** After all approved canary criteria pass, a normal critique returns usable output. Concurrent repository changes survive unchanged.
6. **Handle failure.** Ordinary model failures retain bounded retries. Safety incidents stop the run. Unsupported prerequisites or unresolved safety state refuse dispatch with a distinct outcome.
7. **Recover.** Jason inspects existing evidence, resolves the named condition, and authorizes clearance of the current incident set. A stopped round is not retroactively completed; subsequent work starts explicitly.

Authentication failure remains an ordinary availability problem when containment and inspection are healthy. The runbook directs the operator to the existing authentication procedure; the repair does not edit credentials.

**User stories and goal alignment.**

| ID | User story | Goals |
|---|---|---|
| US-0 | As a maintainer, I want one documented offline verification command so that I can validate the contract without live credentials or a live critic. | G-5, G-7 |
| US-1 | As the operator, I want a debate STOP to terminate the round distinctly so that retries, synthesis, and completion artifacts cannot follow it. | G-3 |
| US-2 | As the operator, I want unstarted sibling dispatches blocked and already-running siblings inspected and quarantined so that parallel work cannot evade STOP. | G-1, G-3 |
| US-3 | As the operator, I want preflight to obey the same safety and repository rules as a critique so that a preliminary ping cannot bypass protection. | G-1, G-3, G-4 |
| US-4 | As a co-tenant session owner, I want blocked dispatches to identify the repository incident so that I understand the refusal without retrying blindly. | G-3, G-7 |
| US-5 | As an orchestrator agent, I want concurrent repository changes preserved and recorded accurately so that legitimate work is never reverted or blamed on the critic. | G-2 |
| US-6 | As the operator, I want successful critic workspace mutations detected and their available evidence preserved so that even transient mutations stop the run. | G-1, G-3 |
| US-7 | As the operator, I want unavailable containment to refuse dispatch and confirmed boundary failure to STOP so that protection never silently degrades. | G-1, G-4 |
| US-8 | As the operator, I want snapshot-bound integration and a separately approved canary so that the repair preserves user work and proves live compatibility. | G-6 |
| US-9 | As the operator, I want self-contained incident evidence so that I can assess the failure without rerunning the critic. | G-3, G-7 |
| US-10 | As the operator, I want an authorized clear bound to the current incident set so that stale or automated actions cannot reopen dispatch. | G-3 |
| US-11 | As the operator, I want immutable inputs and private dispatch workspaces so that prompt delivery cannot modify a repository or expose sibling scratch. | G-1 |
| US-12 | As a new maintainer, I want prerequisite and first-run guidance so that I can reach a meaningful verification result without discovering setup requirements through failures. | G-4, G-5, G-7 |
| US-13 | As the operator, I want recovery guidance for interrupted inspection, corrupt state, and incomplete evidence so that uncertainty remains blocked without becoming a permanent unexplained dead end. | G-3, G-4, G-7 |
| US-14 | As the operator, I want runtime state isolated from persistent host configuration so that a critique cannot alter future dispatch behavior. | G-1 |

These stories do not authorize repository restoration, automatic clearance, persistent configuration changes, or live dispatch before the release gates.

**Functional requirements — containment and input delivery.**

Every Antigravity entry point, including preflight, uses the operator-mandated bubblewrap boundary. Failure to establish the supported boundary prevents the critic from starting.

The critic receives the intended repository context and immutable prompt inputs. Large prompts follow the same protection rules as small prompts. Prompt preparation and scratch do not modify watched repositories.

Sibling isolation includes inability to read another dispatch’s private inputs, scratch, or retained evidence. Different directory names or permissions alone are insufficient acceptance evidence.

The supported environment must prevent critic access to host-control channels that could perform repository writes outside containment. A canary process inventory supplements this requirement; it does not replace it.

Safety self-checks must not modify user repository paths, including when checking a broken boundary.

**Functional requirements — configuration policy, proposed U-12 resolution.**

Persistent host configuration and authentication state remain non-writable to the critic. Necessary mutable runtime state is disposable and private to the dispatch. It is never automatically copied back into persistent host configuration.

Before enabling live dispatch, the operator approves the permitted runtime-write purposes and their evidence requirements. Ordinary critic workspace writes remain STOP events; runtime exceptions cannot become a general workspace allowlist.

Unexpected runtime behavior leaves release disabled until reviewed. If Antigravity cannot operate under the approved policy, its seat remains unavailable. Adopting persistent writable configuration instead requires an explicit amendment to the containment goal and its acceptance criteria.

**Functional requirements — outcomes and attribution.**

| Observation | Required outcome |
|---|---|
| Clean successful dispatch | Return the response; complete inspection and cleanup. |
| Nonzero exit, empty output, or timeout with verified clean safety state | Preserve today’s bounded retry behavior. |
| Co-tenant repository change with boundary intact | Preserve the change; record `co-tenant`; do not STOP. |
| Repository write attempt denied by the boundary, with no successful mutation | Record the denial when observable; do not classify it as a successful mutation. |
| Successful critic workspace mutation | STOP `critic`, including when the critic later removes or reverses the change. |
| Confirmed boundary failure | STOP `boundary_failure`. |
| Sandbox prerequisite unavailable before launch | Refuse as unavailable; no critic start and no fabricated incident. |
| Inspection or durable safety state unresolved | Refuse further admission pending reconciliation; do not invent attribution. |
| Existing repository STOP | Refuse and identify its incident set and recovery procedure. |

Evidence must distinguish retained final content, observed mutation activity, and unavailable historical content. The system must never claim complete byte capture when it only possesses a final snapshot.

**Functional requirements — terminal behavior and concurrency.**

A STOP prohibits retries, new critic starts in the affected run, synthesis, later processing, and artifacts representing the stopped round as complete.

Necessary safety finalization remains permitted: stopping the dispatch’s own timed-out children, inspecting already-running siblings, recording incidents, preserving partial output, and quarantining results.

No Antigravity process may start after the repository STOP cutoff. An earlier admission reservation does not count as a started process.

Already-running siblings follow their original deadlines; STOP does not extend them. They are inspected and their output quarantined. Additional mutations produce additional linked incidents.

Pre-existing partial results remain available as evidence. They are not synthesized into a successful stopped round.

**Functional requirements — durable state and recovery.**

STOP scope is the repository across all linked worktrees. Other repositories remain unaffected. The approved git-common-directory location remains the operator-visible coordination and evidence location.

Dispatch may start only when durable recovery of its safety outcome is possible. An interrupted inspection, failed incident write, unreadable record, or incomplete state transition must not make a later process infer that dispatch is clear.

A STOP remains effective even if detailed evidence capture fails. The operator receives all available references and an explicit completeness status. Uncaptured recoverable content is retained.

Clear requires:

- Authorization through the project’s trusted operator-approval procedure; a supplied name is insufficient.
- Identification of the complete current incident set.
- Completion or reconciliation of affected in-flight dispatches.
- Recorded operator identity, time, reason, and authorization reference.
- Preservation of incident evidence.

A new incident invalidates an earlier clear request. Interrupted clearance cannot reopen dispatch without its completed audit record.

Corrupt or unidentified state receives a distinct recovery reference and procedure. Recovery must not require guessing an incident identifier or manually deleting evidence. An unresolved condition is not automatically labelled critic misconduct.

**Functional requirements — operator communication.**

Every STOP or refusal identifies the outcome, repository, affected run or dispatch, incident or recovery reference, evidence location, evidence completeness, and next responsible actor.

The message distinguishes:

- Repairing prerequisites.
- Reviewing a confirmed incident.
- Reconciling interrupted safety state.
- Authorizing a clear.
- Approving a canary.

No safety message advises blind retry. Control flow does not depend on message wording.

**Functional requirements — integration and canary.**

The reconciliation preview accounts for existing additions, modifications, deletions, renames, file modes, binary contents, and untracked file contents. Overlapping changes must appear in the exact candidate reviewed by the operator.

Integration approval binds the candidate and current live snapshot. Concurrent changes cannot slip between validation and application. Drift invalidates approval.

Rollback preserves work created after integration; it must refuse an unsafe reversal rather than overwrite that work.

Routine Antigravity dispatch remains disabled during landing. The separately approved canary has explicit pass criteria:

- The real critic reads the intended immutable prompt.
- The approved containment and host-helper restrictions remain established.
- No unexpected workspace or runtime mutations occur.
- Inspection, evidence handling, and cleanup complete successfully.

Unexpected byproducts, incomplete observations, or a STOP are not a passing canary. Any changed containment policy requires renewed offline validation and a newly approved canary.

**Non-functional requirements.**

- Safety handling never deletes, restores, or overwrites co-tenant repository content.
- All entry points expose stable, distinguishable outcomes for ordinary failure, STOP, STOP-blocked, unavailable prerequisites, and unresolved safety state.
- Evidence capture is bounded. Budget exhaustion reports incomplete evidence, preserves recoverable material, and cannot become an ordinary retry.
- Supported deadlines and capture limits are documented before release.
- Incident evidence is private to authorized local operators and excluded from routine synthesis.
- Claims of complete evidence require verified capture; cleanup does not destroy uncaptured recoverable content.
- The supported operating environment and required capabilities are documented. Unsupported hosts are reported explicitly.

**Success metrics and acceptance.**

| Measure | Release target |
|---|---|
| Offline suite duration | Under five minutes on the documented development workstation, after prerequisites are installed. |
| External critic and credential use during offline validation | Zero. |
| Unsupported mandatory sandbox cases | Explicit failure or unsupported result; never a green release result. |
| Co-tenant content damage in acceptance scenarios | Zero overwritten, restored, or deleted user changes. |
| Antigravity starts after repository STOP cutoff | Zero, including preflight, retries, queued siblings, and fresh processes. |
| Required mutation and boundary cases | Every case produces its specified outcome, with a corresponding non-trigger case. |
| Invalid or stale clear requests | Zero successful clears. |
| Evidence claims | Every claim of complete capture verified; every shortfall explicitly reported. |
| Live release | All offline gates pass and every approved canary criterion passes. |
| First-use usability | A maintainer unfamiliar with the repair reaches a verification result using the runbook alone. |

These are release acceptance targets, not claims that a finite suite proves every possible execution safe.

The canonical acceptance suite retains SC-1 through SC-7 and adds transient mutations, sibling read attempts, host-service delegation, interrupted inspection, failed durable writes, corrupt-state recovery, multiple incidents, clear races, and unsafe rollback refusal.

Tests must exercise observable behavior against the actual production boundary. Any harness-only permissions must be identified and must not invalidate the property being tested.

**Dependencies.**

- A supported bubblewrap and kernel environment.
- Reliable repository identity across worktrees and recoverable safety-state storage.
- Existing operator-approval records for integration, canary, and clear.
- Resolution of U-12 and approval of permitted runtime behavior.
- A reconciled candidate for the dirty `bounded-pipeline-reform` tree.
- Live compatibility evidence for U-1, U-10, and U-11.
- A synchronized technical companion and acceptance catalog.

U-6 remains a named limitation: this release does not repair the independent `fizzy-pipeline-mcp` runner.

**Risks and mitigations.**

| Risk | Mitigation |
|---|---|
| Antigravity requires incompatible filesystem behavior | Keep its seat unavailable; amend the policy explicitly and repeat validation. |
| Runtime state changes future behavior | Use approved disposable runtime state; prohibit automatic persistence. |
| Existing host services bypass filesystem containment | Deny applicable control channels and test delegation attempts. |
| Inspection or persistence fails | Preserve an unresolved admission block and recoverable evidence. |
| Multiple processes race with STOP or clear | Require observable ordering and incident-set-bound clearance. |
| Evidence volume exhausts resources | Apply documented bounds; report incompleteness without retrying or losing recoverable content. |
| Integration or rollback overwrites concurrent work | Validate complete content state and reject drift during either operation. |
| Historical requirements reintroduce restoration or unsafe cleanup | Synchronize all normative documents before implementation acceptance. |

**Delivery and document authority.** Retain the existing milestone order: offline bootstrap; terminal behavior; durable STOP; containment and attribution; recovery; integration and canary. These milestones describe delivery organization, not permission to enable incomplete safety behavior.

Before implementation acceptance, the technical companion must resolve the admission ordering, durable recovery, clear authorization, evidence lifecycle, and containment details required above.

Appendix A must remove superseded restoration and attribution requirements. Appendix B must replace contradictory race, probe, cleanup, and canary oracles. Appendix C remains historical context. Conflicting acceptance documents block release.

[/SPEC]