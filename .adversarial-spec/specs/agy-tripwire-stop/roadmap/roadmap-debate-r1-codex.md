Significant revisions needed. User stories exist and the incident provides concrete motivation, but the operator journey and several safety guarantees remain incomplete. Incident claims below come from the supplied document; they were not independently verified.

1. **CRITICAL — The user journey stops at running tests.** M0 gives maintainers a useful first action, but operators lack a complete path through discovery, repository selection, STOP inspection, recovery, explicit clearing, and starting a new run. The clear operation is essential product behavior, not an optional UX detail.

2. **CRITICAL — Attribution requirements conflict with the goals.** G-1 and SC-1 broadly promise restoration of real critic mutations, while TC-6.1 correctly preserves a critic’s shared-tree write as `unattributed`. Additionally, the decision table classifies *any* writer in the private surface as `critic`; that could violate US-5 if exclusive ownership is lost. Restoration must require proven exclusive critic ownership. A path’s location alone cannot establish authorship.

3. **CRITICAL — Terminal STOP is underspecified under concurrency and failure.** Checking before spawning does not define what happens when another process stops between that check and the spawn. U-4 leaves already-running siblings unresolved. There is also no complete behavior for evidence-write failure, failed restoration, interrupted stop persistence, concurrent incidents, or clearing while old work remains active. These gaps directly affect G-1 through G-3.

4. **MAJOR — Tool-owned exclusions could conceal mutations.** Exact paths are safer than prefixes, but an exact tool path is not proof that the tool produced its current contents. Unexpected changes to an excluded artifact need an explicit outcome. Otherwise US-7 can succeed while weakening G-1.

5. **MAJOR — Offline safety and live compatibility are conflated.** A fake critic can prove the application’s safety behavior; it cannot establish that Antigravity reads the required prompt and project context from the proposed working environment. U-1 needs a named release limitation and subsequent authorization boundary. A clean response without the intended context is not a successful critique.

6. **MAJOR — Integration approval is vulnerable to stale evidence.** TC-8.0 validates a copy, but the live tree can change before application. The gate needs a specific candidate, a current target snapshot, invalidation on drift, and explicit handling of overlapping edits. “Every hunk survives byte-identical” also needs a content-based definition that accommodates moved lines while preserving edits and intentional deletions.

7. **MAJOR — Acceptance evidence is incomplete.** Queued-sibling tests do not establish behavior for competing processes or dispatch admission races. An unset proxy does not prove network isolation. Static inspection of an approval plan does not prove application is gated. Several variants contain assertions without sufficient setup or action to reproduce them. The five-minute target also needs a defined environment.

8. **MAJOR — This is a technical roadmap rather than a stakeholder-ready PRD.** Its technical designation explains the implementation material, but it does not satisfy the requested product document. Missing elements include a complete operator journey, actionable recovery requirements, explicit risks and mitigations, and release decisions. “Consuming projects” should become a human persona with responsibilities. Technical mechanisms and detailed pseudocode should remain companion artifacts.

[SPEC]
# PRD: AGY Tripwire Stop — Critic Safety Contract Repair

Adversarial-spec session: `adv-spec-202609240523-agy-tripwire-stop`  
Card: 21616  
Status: Revised proposal for stakeholder review

U-2 and U-3 remain confirmed operator decisions. This revision proposes bounded handling of running siblings and an operator-clear journey; these proposals do not constitute authorization to integrate, clear a STOP, or dispatch Antigravity.

## Executive Summary

Repair Antigravity critic safety so that suspected mutations stop affected work without destroying concurrent user or agent changes.

The product must preserve evidence, distinguish provable critic ownership from uncertainty, prevent further dispatch after STOP across processes, and provide a deliberate operator recovery path. Maintainers must demonstrate these behaviors offline before requesting integration into the dirty live tree.

## Problem Statement / Opportunity

The supplied incident account reports that:

- A concurrent orchestrator critique of 2,519 bytes was deleted after being attributed to Antigravity based on timing.
- A second critic attempt ran after STOP.
- STOP could become an ordinary error, allowing downstream synthesis or checkpoint activity.
- Concurrent agent work and tool artifacts could be mistaken for critic mutations.

These are reported incident facts, not independently verified results of this review. The source reports remain the supporting evidence.

The user pain is loss of unfinished work, unreliable incident attribution, and inability to trust that stopping or restarting a process prevents further critic activity.

Success restores confidence in containment and recovery. It does not eliminate all possible critic writes or establish a security sandbox against malicious local processes.

## Goals and Non-Goals

### Goals

- **G-1 — Contain attributable mutations.** Detect mutations within an exclusively critic-owned surface, preserve evidence, restore the attributable changes, and stop the affected run. Report failed evidence capture or restoration as incomplete containment; never report success when either failed.
- **G-2 — Preserve uncertain changes.** Never automatically undo changes whose ownership cannot be established structurally. Preserve shared-tree changes, label them `unattributed`, capture available evidence, and stop.
- **G-3 — Make STOP terminal.** Prevent retries, new sibling work, synthesis, and completed-round checkpoints in the stopped run. Prevent further Antigravity dispatch against the same watched repository across processes until an explicit operator clear.
- **G-4 — Prove the application contract offline.** Exercise real application behavior with controlled substitute critics and paired negative cases, without network access, credentials, or live model calls.
- **G-5 — Integrate without losing existing work.** Require a named operator-approved gate tied to a specific repair candidate and current live-tree state, with evidence that pre-existing user changes survive.
- **G-6 — Make recovery understandable.** Let operators identify the affected repository, understand the incident and remaining uncertainty, inspect evidence, and deliberately authorize future work.

### Non-Goals

- Resuming or modifying `adv-spec-202607060132-post-fable-hardening-skill` or the Brainquarters Jev session.
- Editing the live source, the deployed skill, deploying, committing, or pushing without explicit integration approval.
- Any live Antigravity dispatch, including preflight, before the repair lands and the operator explicitly clears the prohibition.
- Repairing fizzy-pipeline-mcp’s independent Antigravity runner.
- Broad model-routing changes, secrets/configuration changes, or global process control.
- Automatically restoring uncertain shared-tree changes.
- Automatically resuming a stopped run after clearing.
- Treating offline regression results as proof of live Antigravity compatibility.

## Target Users / Personas

| Persona | Situation and responsibility | Primary need |
|---|---|---|
| Operator, Jason | Oversees concurrent work and owns integration and clear decisions | Understand the incident and authorize recovery without losing work |
| Orchestrator agent | Runs debate or gauntlet work while other writers share the repository | Receive an unmistakable terminal outcome and preserve concurrent work |
| Consuming-project maintainer | Runs critics against a dirty project with unfinished changes | Know which repository is protected and what remains outside this repair |
| Future maintainer | Changes dispatch and error handling without firsthand incident knowledge | Run a reproducible safety suite and recognize contract regressions |

## User Journey

1. **Discover the repair.** Repository documentation and debate/gauntlet help link to one safety guide explaining STOP, its repository scope, and the current Antigravity dispatch prohibition.
2. **Verify locally.** A new maintainer follows documented prerequisites and runs one offline command. The report identifies scenario results and confirms that no live critic was reached.
3. **Prepare integration.** The maintainer produces a reviewable candidate and preservation report against the current live-tree snapshot.
4. **Approve and land.** Jason approves the named candidate and target snapshot. Changed target state invalidates that approval’s applicability and requires refreshed review.
5. **Start authorized work.** Once landing and clear requirements are satisfied, the operator starts a new run against an explicitly identified repository.
6. **Encounter STOP.** The run displays its terminal outcome, repository, incident reference, attribution, and evidence/restoration status. Further work is blocked as specified below.
7. **Inspect and recover.** The operator reviews available evidence and any running-work status. Shared-tree recovery remains a deliberate operator action.
8. **Clear deliberately.** The operator reviews the current incident set and authorizes clearing it. Evidence remains available. Clearing launches nothing.
9. **Start a new run.** A later invocation checks current safety status again. The stopped round remains stopped.

The maintainer’s first value is a reproducible offline safety result. The operator’s first value is preservation of concurrent work and an actionable terminal incident report.

## User Stories / Use Cases

| ID | User story | Goal alignment |
|---|---|---|
| US-0 | As a maintainer, I want a documented offline verification command and scenario report so that I can establish safety without credentials or a live critic. | G-4 |
| US-1 | As an operator, I want a debate STOP to end the affected round with a distinct outcome so that retries, synthesis, and completed-round checkpoints cannot follow it. | G-3 |
| US-2 | As an operator, I want a gauntlet STOP to prevent new sibling work and quarantine unfinished sibling results so that stopped work cannot produce accepted results. | G-3 |
| US-3 | As an operator, I want preflight to use the selected repository and obey the same safety rules so that a preliminary check cannot bypass STOP. | G-3 |
| US-4 | As an operator, I want to inspect and explicitly clear a persistent repository STOP so that restarting a process cannot resume Antigravity without my decision. | G-3, G-6 |
| US-5 | As an orchestrator agent, I want concurrent shared-tree changes preserved and labelled without unsupported attribution so that other writers do not lose work or receive false blame. | G-2 |
| US-6 | As an operator, I want provable critic-owned mutations captured and restored before containment is reported successful so that genuine mutations remain contained and failures remain visible. | G-1, G-2 |
| US-7 | As an orchestrator agent, I want legitimate tool artifacts handled without false incidents so that parallel work remains usable without creating mutation blind spots. | G-1, G-2, G-3 |
| US-8 | As an operator, I want a preservation report and explicit integration gate for the current dirty tree so that landing the repair retains every pre-existing user change. | G-5 |
| US-9 | As a consuming-project maintainer, I want the selected repository and supplied critique context identified so that a clean run reviews the intended material under the intended safety scope. | G-1, G-3, G-6 |
| US-10 | As an operator, I want incomplete safety checks, evidence capture, or restoration to produce a blocked outcome with recovery information so that uncertainty cannot silently permit dispatch. | G-1, G-2, G-3, G-6 |

No story authorizes a listed non-goal. In particular, successful offline verification does not authorize live dispatch, and successful integration does not automatically clear STOP.

## Functional Requirements

### FR-1 — Bootstrap and offline verification

- Provide one documented command, its prerequisites, supported environment, expected report, and failure interpretation.
- The suite must refuse before dispatch if any exercised critic route could reach a live provider.
- Exercise debate, gauntlet, preflight, and concurrent-writer scenarios without live model calls.
- Report each scenario by stable identifier, with observed outcome and failed acceptance condition.
- A setup failure must be distinguishable from a safety regression.

### FR-2 — Repository selection and scope

- Identify the watched repository before dispatch and in every STOP or blocked response.
- Invocation from a subdirectory or path alias must not bypass a repository STOP.
- An independently cloned repository must not inherit another repository’s STOP.
- Proposed clarification: linked worktrees belonging to one repository share its STOP scope. This interpretation requires stakeholder ratification before acceptance.
- Document which repository content is watched. Any coverage exclusion must be explicit; the product must not imply protection for content it does not observe.
- Missing or ambiguous repository identity must block dispatch.

### FR-3 — Mutation attribution and preservation

| Observed change | Required outcome |
|---|---|
| Change to a surface proven exclusively critic-owned | Preserve evidence, restore attributable changes, stop, label `critic` |
| Shared-tree change with uncertain ownership | Preserve current shared-tree state, preserve available evidence, stop, label `unattributed` |
| Change inside a nominally private surface whose exclusive ownership cannot be established | Preserve changes, stop, label `unattributed` |
| Verified legitimate tool activity | No mutation incident from that activity alone |
| Unexpected change to a tool artifact or lookalike path | No exemption based solely on pathname; apply attribution rules |
| No relevant change | Continue normally if all other safety checks pass |

- Timing alone must never establish authorship.
- A known critic in a test writing to the shared tree must still receive `unattributed` handling when the application cannot establish ownership.
- Shared-tree observation must never automatically overwrite, delete, resurrect, or revert user files.
- Pre-existing dirty content is the baseline; its mere presence is not a new incident.
- Acceptance must cover creation, modification, deletion, and changes to already-dirty files.
- Mixed incidents must describe attributable and unattributed changes separately.

### FR-4 — Terminal STOP behavior

- Establish the blocked condition when a stop-worthy event is recognized. Evidence capture or restoration failure must not reopen dispatch.
- In the affected run, STOP prevents new model work, retries, synthesis, later gauntlet processing, and checkpoints representing the stopped round as completed.
- Preserve previously completed partial results as evidence. Results arriving after STOP are quarantined and cannot become accepted round output or extracted Concerns.
- Incident evidence and terminal status reporting remain permitted after STOP.
- STOP behavior must remain intact through ordinary error handling and must not depend on message wording.
- Clean non-mutation failures retain the documented existing bounded retry policy.

### FR-5 — Concurrent work and timeouts

- Dispatch attempts competing with STOP must have a defined observable ordering. A new critic process must not start after STOP has been established.
- This guarantee applies to competing processes as well as siblings in one process.
- Proposed U-4 decision: already-running siblings may drain only within their original timeout limits. They receive no retries or deadline extensions, and their output remains quarantined.
- Each running sibling still receives the required mutation assessment.
- An operator clear is refused while affected work remains active or its completion cannot be established.
- Timeout assessment must check for mutations before reporting an ordinary timeout. Mutation plus timeout produces STOP; a clean timeout remains an ordinary failure.
- Promptly report STOP even while previously running work is draining.

### FR-6 — Persistence, inspection, and clear

- STOP must remain effective for new processes against the watched repository, including preflight and invocations that skip preflight.
- Concurrent incidents must remain discoverable; one must not silently replace another.
- Corrupt, unreadable, or indeterminate safety state must block dispatch.
- Inspection must show repository identity, unresolved incidents, attribution, evidence availability, containment status, and outstanding running work.
- Clearing requires explicit operator authorization tied to the repository and current incident set. Retries, default options, new rounds, and restarts cannot imply that authorization.
- Record who authorized the clear, when, which incidents it covers, and the stated reason.
- A new incident arising during clear must remain blocking.
- Failed or interrupted clear must not leave the repository reported as clear.
- Clearing preserves incident evidence and launches no work.
- A prior process’s STOP remains terminal even if a later operator action clears the repository for future runs.

Operator authorization is a requirement for cooperative automation in the trusted local environment. An audit entry alone must not be presented as proof of human identity.

### FR-7 — Evidence and incomplete containment

Each incident must let the operator determine:

- Which repository and invocation were affected.
- Which paths changed and their attribution.
- What existed before and after, including explicit absence for creation or deletion.
- Which available bytes and critic outputs were preserved.
- Whether evidence capture and restoration completed.
- What remains unresolved and which operator action is available.

Capture failures, interrupted processing, and restoration failures must produce a blocked outcome with explicit incomplete status. Available evidence must be retained. Destructive restoration must not destroy the only remaining copy of incident evidence.

The system must refuse to begin dispatch when it cannot establish the safety conditions needed to maintain persistent blocking.

### FR-8 — Preflight and useful critique context

- Preflight must use the selected watched repository and the same dispatch prohibition as normal critique.
- STOP during preflight must surface as STOP, followed by no critique dispatch.
- A clean preflight failure must remain distinguishable from STOP.
- An isolated critic must receive the intended prompt and authorized context.
- Context-delivery failure must be reported; the system must not silently retry through an unsafe working environment.
- Offline results must explicitly identify live Antigravity compatibility as unverified when applicable.

### FR-9 — Deliberate integration

The gate is **AGY Safety Repair Integration Approval**. Approver: Jason.

Required sequence:

1. Identify the repair candidate and its offline acceptance evidence.
2. Capture the current live-tree state, including pre-existing tracked edits, intentional deletions, and untracked file contents.
3. Reconcile the candidate in a disposable copy.
4. Produce a preservation report and resolve all overlapping-change conflicts.
5. Present the exact candidate, target snapshot, application order, verification, and recovery procedure for approval.
6. Revalidate the live tree immediately before applying. Any drift invalidates the prepared application.
7. Apply only the approved reconciliation.
8. Verify preservation and rerun the relevant offline acceptance checks.

Preservation means that every pre-existing user change remains represented exactly; moved line numbers do not constitute loss. Pre-existing untracked file contents remain byte-identical.

If an overlap cannot preserve a user change, the gate fails. Integration approval does not implicitly authorize discarding that change. Recovery must also protect work created after the original snapshot.

## Non-Functional Requirements

- **Reliability:** All mandatory safety cases must pass before integration approval is requested.
- **Offline operation:** Verification requires no network, credentials, or live model. Dependency installation is outside the timed offline run and must be documented.
- **Performance:** The complete safety suite finishes within five minutes on a documented reference environment with prerequisites already available.
- **Observability:** Successful completion, ordinary failure, STOP, and refusal due to existing or uncertain safety state have documented, machine-distinguishable outcomes and readable explanations.
- **Recoverability:** Clearing never deletes evidence. Incomplete capture or restoration remains visible.
- **Maintainability:** Acceptance verifies behavior through observable outcomes, including negative cases that demonstrate ordinary successful operation.
- **Data handling:** Incident material remains locally inspectable and is not automatically sent to another model or external service.

## Success Metrics / KPIs

| Measure | Release target | Evidence |
|---|---|---|
| Shared-tree preservation | Zero automatic reversions or lost writer changes in mandatory cases | Before/after content and deletion-state comparison |
| Attribution accuracy | Zero unsupported `critic` labels in mandatory cases | Attribution report across isolated, shared, mixed, and ownership-loss scenarios |
| STOP enforcement | Zero prohibited process starts or accepted downstream results after STOP | Ordered dispatch and artifact observations |
| Persistence | Every same-repository attempt blocks until authorized clear | Independent-process and concurrent-process cases |
| Normal operation | Every paired clean case preserves expected successful or bounded-failure behavior | Negative-oracle results |
| Offline assurance | Zero live-model invocations and zero network dependency | Independently enforced offline execution and dispatch observations |
| Bootstrap usability | A maintainer unfamiliar with the repair completes the documented workflow without undocumented steps | Walkthrough record |
| Recovery usability | Operator identifies the incident, inspects evidence, and clears only the intended incidents without deleting evidence | Recovery walkthrough |
| Integration preservation | Every pre-existing user change retained; stale snapshots rejected | Candidate-specific preservation and drift reports |
| Suite duration | Under five minutes in the reference environment | Timed report |

These are acceptance targets, not measured results. No production incident-rate improvement is claimed without subsequent evidence.

## Scope

**In scope:** Debate, gauntlet, preflight, persistent repository STOP, attribution, concurrent work, tool artifacts, evidence, operator inspection and clear, offline regression, documentation, and integration reconciliation.

**Out of scope:** The non-goals above, including the independent fizzy runner and unrelated sessions.

The user-facing guide must state that this repair covers the named application routes. It must not imply that every Antigravity entry point elsewhere in the ecosystem has been repaired.

## Dependencies and Open Decisions

| Item | Required disposition |
|---|---|
| U-1: Antigravity prompt/context compatibility | Document offline evidence and its limits. Any live validation requires approved landing and explicit operator clearance; it is not part of current authorization. |
| U-2: Unattributed shared writes | Confirmed: preserve changes and halt fail-closed. |
| U-3: Persistent repository scope | Confirmed: per watched repository. Ratify linked-worktree interpretation and the proposed clear journey. |
| U-4: Running siblings | Proposed: bounded drain under original deadlines, quarantined output, clear blocked until inactivity is established. |
| U-5: Dirty-tree landing | Require a candidate-specific reconciliation and current snapshot under FR-9. |
| U-6: Independent fizzy runner | Record as external residue with a named follow-up owner before handoff; no repair or dispatch through it is authorized here. |
| Existing retry behavior | Document the current bounded policy as the acceptance baseline rather than relying on “today’s behavior.” |
| Supporting specifications | Reconcile the technical specification and canonical tests with this PRD before implementation acceptance. |

## Risks and Mitigations

| Risk | User impact | Mitigation |
|---|---|---|
| Legitimate concurrent shared writes trigger STOP | Interrupted work | Preserve bytes, explain uncertainty, provide deliberate recovery; retain confirmed fail-closed policy |
| Ownership assumptions are false | Incorrect blame or destructive restoration | Require exclusive ownership; uncertainty receives preservation and STOP |
| STOP races with dispatch or clear | Unexpected critic activity | Acceptance covering competing processes, incident arrival during clear, and running work |
| Evidence or persistence fails | Lost recovery information or accidental restart | Explicit incomplete status, persistent refusal, no success claim |
| Tool artifacts conceal unexpected writes | Missed mutations | Validate permitted tool activity; test unexpected writes to exact tool paths |
| Isolated critic lacks intended context | Safe but useless critique | Verify context delivery and report live compatibility limits |
| Live tree changes after review | User work overwritten | Snapshot-bound approval, revalidation, drift rejection |
| Offline results are overclaimed | Premature activation | Separate offline contract acceptance, integration approval, and live compatibility status |

## Acceptance and Delivery

Retain milestones M0–M4 as delivery planning:

- **M0:** Discoverable offline bootstrap.
- **M1:** Terminal STOP throughout affected runs, including sibling handling.
- **M2:** Persistence, inspection, and explicit clear.
- **M3:** Structural attribution, preservation, evidence, and tool-artifact behavior.
- **M4:** Approved integration with verified preservation.

Intermediate milestones are not authorization for live Antigravity use.

Retain SC-1 through SC-7 and existing test identifiers. Reconcile their expectations with this PRD, particularly SC-1’s restoration boundary and TC-2.1’s sibling behavior.

Add acceptance coverage for:

- Competing-process dispatch at the STOP boundary.
- Multiple incidents and clear racing with a new incident.
- Clear attempted while affected work remains active.
- Evidence, restoration, and safety-state failures.
- Ownership loss and mixed-attribution incidents.
- Unexpected changes to exact tool-owned paths.
- Repository aliases and the ratified linked-worktree scope.
- Missing or incorrect critique context.
- Live-tree drift between review and application.
- Actual refusal to apply before approval.

Every new story must have one designated acceptance spine; failure variants must identify the step they alter. Companion test pseudocode must specify setup, action, observations, and negative outcomes sufficiently to reproduce each case.

Implementation acceptance requires the reconciled acceptance suite, operator guide, resolved product decisions, and documented compatibility limits. Live-tree application and later Antigravity use remain separate explicit operator decisions.
[/SPEC]