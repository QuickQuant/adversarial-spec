## Critique

**Significant revision required.** The roadmap has useful acceptance detail, but it does not yet function as a standalone PRD.

Review basis: supplied documents only. Incident reproductions, deployed capabilities, board state, and test results remain **unverified**.

### 1. CRITICAL — No complete new-user journey

M0 starts with dependencies available, a sibling repository checked out, and an environment already synchronized. It describes verification, not onboarding.

The documents do not explain:

- Where a new maintainer discovers the feature.
- How they obtain prerequisites and access.
- What they do after `ready`, `degraded`, or `broken`.
- When they first complete useful work.

The `<5 min` target therefore measures an unclear portion of setup.

### 2. MAJOR — Stories exist, but important workflows are missing

The contextual requirements contain properly formatted US-1–US-12. They should not be treated as absent. The roadmap’s abbreviated story labels, however, are insufficient without that context, and US-0 lacks the required format.

Missing stories include:

- Recovering from a rejected proof without losing completed work.
- Resuming after an interrupted run or custody operation.
- Handling unavailable dependencies, reviewers, or observations.
- Adopting the feature in a downstream project.
- Maintaining compatibility as a cross-repository integration owner.

Fizzy and “downstream projects” are dependencies or organizational categories. Their responsible human or agent roles need explicit needs and responsibilities.

### 3. CRITICAL — Some permitted outcomes undermine G-1

Two evidence rules need correction:

- The test document’s introduction includes incident-derived synthetic fixtures within its definition of “real data,” although individual replay tests correctly label them synthetic.
- TC-11.1 permits legacy evidence to discharge a newly bound obligation through “an explicit operator waiver / process-failure note.”

A process-failure note cannot establish proof-target identity. A waiver may document accepted risk; it must not convert unverified evidence into verified proof.

Similarly, the bounded ruleset’s safe, substituted development environments can validate behavior without satisfying an unchanged live-boundary acceptance obligation. The PRD must distinguish those outcomes explicitly.

### 4. CRITICAL — Self-hosting and rollout requirements conflict

US-9 requires this reform’s new ORACLE behavior during this reform’s finalize operation. M5 depends on capabilities delivered by M1/M2, while G-4 prohibits shipping those capabilities before finalize. The document does not establish that the required capabilities already exist.

There is a second conflict:

- OQ-5 requires a card-version-only fence: v5 warns; v6 rejects.
- US-11 promises that in-flight work will not be retroactively failed.

Those promises cannot both hold for an already-v6, in-flight card containing newly prohibited work. Missing version metadata must also be distinguished from unavailable or malformed metadata.

The process ownership is inconsistent too: M3 and the architecture section require full Phase 4 work, while TC-12.0 describes a v6 journey without a separate target-architecture transition. The requirements also refer to “Phases 2–9.” One authoritative ownership mapping is needed.

### 5. CRITICAL — Custody acceptance contradicts its safety goal

TC-7.2 accepts another creation when four items already exist against a budget of four. That permits the creation that breaches the budget.

The correct boundary is the **projected total after creation**.

Other unresolved custody semantics include:

- Whether preserved items continue consuming budget.
- How concurrent creation requests share the remaining capacity.
- What happens when an exempt workspace survives an interrupted tool turn.
- Whether this release only validates removal requests or also executes removal.

The latter matters because INV-2 says no mechanism authorizes deletion, while US-7 and TC-7.5 discuss authorization and application. Preview validation, human authorization, and destructive execution must have separate meanings.

### 6. MAJOR — Several acceptance contracts remain ambiguous

Examples:

- TC-1.2 permits missing bindings at early maturity, while compilation and finalize tests block them. Gate-specific requirements are not stated.
- TC-1.3 lists only some expected identity fields. The complete set affecting obligation identity must be explicit.
- Strict rejection of extra fields and preservation of future fields can coexist, but their respective boundaries and version rules are unspecified.
- Any nonblank `not_applicable` reason appears sufficient to omit a cutover obligation. A rationale must establish actual inapplicability.
- A census validator cannot establish completeness merely by validating the census supplied to it. Discovery scope, independent review, and unresolved uncertainty need requirements.
- Receipt freshness and the critic scoring threshold are unspecified.

These gaps allow incompatible implementations to claim success.

### 7. MAJOR — Rejection behavior lacks a recovery journey

Typed codes help workers, but a code alone does not identify the next useful action.

For each blocked outcome, users need the affected obligation, expected and observed result, evidence limitation, responsible next actor, and permitted recovery. Missing observations must remain distinguishable from observed mismatches.

Interrupted work, unavailable services, and unavailable independent review also need explicit outcomes.

### 8. MAJOR — KPIs mostly measure test inventory

Replay coverage and mutation coverage are useful release checks. They do not measure adoption, operator effort, false blocking, or recovery success.

Additional problems:

- The supplied catalog description contains **15 incident cases plus three controls**, not 18 incident cases plus three additional controls.
- “Every field” needs a defined coverage denominator.
- A zero `patch_state` tally does not establish that failures were honestly recorded.
- A process-failure note cannot turn a missed zero-tally target into a passed target.
- “Suites green” conflicts with acknowledged baseline failures unless “no new failures” is stated precisely.

### 9. MAJOR — Product requirements and implementation design are interleaved

Module names, schema encodings, hashing libraries, middleware selection, artifact formats, and commit-order checks belong in companion engineering documents.

The PRD needs product behavior, understandable terminology, dependency owners, release conditions, and risks. The supplied architecture verdict should remain a design proposal, especially since its cited architecture corpus differs from the cited source revision.

---

[SPEC]
# PRD: Bounded Pipeline Reform & Hardening Alignment

**Status:** Proposed revision for round-one review  
**Adversarial-spec Session:** `adv-spec-202609150549-bounded-reform-hardening-align`  
**Session Card:** 21537  
**Product owner:** Operator, Jason  
**Primary delivery owner:** Conductor

## 1. Executive Summary

Improve the pipeline’s ability to answer two independent questions:

1. Did this evidence satisfy the existing REAL-DATA requirements?
2. Did it exercise the intended caller, route, authority, contract, and applicable runtime?

Today, the supplied incident accounts describe tests passing against the wrong target and temporary resources being treated as resolved without itemized evidence.

This reform adds explicit proof-target expectations, trustworthy observations, complete authority-cutover obligations, and itemized custody accounting. It preserves ordinary single-path workflows, existing REAL-DATA policy, and protection for in-flight work.

Changes must ship through authorized pipeline work after finalize. The delivery process must distinguish capabilities already available from capabilities being introduced.

## 2. Problem Statement and Evidence

The supplied requirements report March–September 2026 incidents involving:

- A real execution reaching the wrong caller, route, or authority.
- A running process differing from the intended delivered version.
- Producer and consumer expectations disagreeing.
- Temporary resources being considered resolved through aggregate count changes.

The requirements report three reproduced contradictions, with two already patched and one specified but unimplemented. These are supplied claims; this review has not verified them.

The user pain is misplaced confidence: workers receive a pass that does not establish the intended outcome, while operators must reconstruct what ran, what remains authoritative, and what happened to temporary resources.

Before release evaluation, the delivery owner must link each retained incident claim to its supporting evidence. Incident-derived synthetic replays must remain labeled synthetic. They demonstrate validator behavior, not historical prevention or live-system acceptance.

## 3. Target Users

| User | Working context | Primary need |
|---|---|---|
| Conductor | Coordinates specifications and implementation across repositories and model seats | Clear obligations, progressive authoring, and an identifiable next action when blocked |
| Implementing worker | Receives a bounded Task Card with limited surrounding context | Understand exactly what must be proved and how to correct rejected evidence |
| Independent reviewer | Reviews another worker’s output using available evidence | Distinguish verified outcomes, unsupported claims, and accepted risk |
| Operator | Owns exceptions, irreversible actions, and continuity of in-flight work | Itemized decisions without inferred cleanup or retrospective enforcement surprises |
| Integration maintainer | Maintains the shared contract, skill, or Fizzy consumer | Explicit ownership and compatible behavior across releases |
| Downstream maintainer | Introduces the reform into an existing project, initially prediction-prime | A documented first-use path and minimal overhead for unaffected work |

These are role descriptions. Their usability assumptions require validation during the pilot.

## 4. Goals and Non-Goals

### Goals

- **G-1 — Correct proof target:** Add proof-target identity independently of REAL-DATA, preserving all existing evidence and liveness obligations.
- **G-2 — Complete authority changes:** Discover relevant alternative paths structurally and require complete, justified cutover obligations.
- **G-3 — Itemized custody:** Account for durable pipeline-owned temporary resources without inferring preservation, resolution, or destructive authorization.
- **G-4 — Safe delivery:** Deliver through the bounded pipeline after finalize, preserve protected in-flight work, and record actual process failures.

### Non-Goals

- Automatic deployment or live-money actions.
- A process supervisor or universal service-start requirement.
- Replacement of mapcodebase.
- A fixture ban for boundary-value analysis, mathematics, or isolation.
- Automatic deletion of branches, worktrees, releases, or files.
- A universal ledger for user-owned checkouts.
- A new universal pipeline Phase.
- Claims that the proposed gates would necessarily have prevented historical incidents.
- Additional model launches solely to ask the new critique questions.

## 5. User Journey

### Discovery and preparation

A new maintainer discovers the reform through the project’s getting-started documentation, release guidance, or existing pipeline entry guidance.

The documentation explains:

- Which changes trigger additional proof requirements.
- Required repositories, access, and supported tools.
- The readiness command.
- One realistic, non-money example.
- Where to find help and the responsible integration owner.

Access acquisition and dependency installation are documented separately from readiness verification.

### First interaction

The maintainer runs one documented readiness command.

| Result | Meaning | Next action |
|---|---|---|
| Ready | Required checks for the requested workflow passed | Start the example or intended work |
| Degraded | A capability is unavailable or incompatible; the affected scope is identified | Continue only with explicitly unaffected work or resolve the named issue |
| Broken | A prerequisite prevents the requested workflow | Follow the reported recovery action before proceeding |

Each failed check identifies the problem, responsible owner, and recovery action. Verification does not silently repair shared contracts or start services.

### First value

From a ready environment, the maintainer completes a non-money example that:

1. States an intended outcome and proof target.
2. Shows why evidence from a different target cannot satisfy it.
3. Produces acceptable evidence from the intended target.
4. Shows the resulting obligation status.

The value moment is understanding why the obligation is satisfied and being able to retrieve the supporting evidence.

### Productive use

For ordinary untriggered work, the maintainer records the existing applicability decision with at most one additional rationale line.

For triggered work, expectations become more detailed as the test matures. Workers receive actionable feedback before requesting closure.

For authority changes, the conductor reviews the relevant paths and cutover obligations. For temporary resources, the operator sees itemized custody and unresolved dispositions.

### Failure and return

After rejection or interruption, the user sees:

- What remains valid.
- What remains unresolved.
- Which evidence must be obtained again.
- Who owns the next action.

Resuming work does not imply that a prior run completed, a temporary resource disappeared, or an obligation passed.

## 6. User Stories

| ID | Story | Goals |
|---|---|---|
| US-0 | As a new maintainer, I want documented prerequisites, a readiness result, and a worked example so that I can complete my first useful obligation without reconstructing the toolchain. | G-4 |
| US-1 | As a conductor, I want triggered obligations to identify their intended proof target so that a successful execution of a different target cannot satisfy them. | G-1 |
| US-2 | As a conductor, I want proof expectations to develop with test maturity so that early authoring remains practical while final acceptance remains complete. | G-1 |
| US-3 | As a conductor, I want relevant outcome-equivalent paths identified and reviewed so that an authority decision does not overlook a callable alternative. | G-2 |
| US-4 | As a conductor, I want each authority change to include all applicable cutover obligations so that source changes alone cannot establish operational completion. | G-2 |
| US-5 | As an implementing worker, I want execution observations with verifiable origin compared against the intended target so that closure reflects what actually ran. | G-1 |
| US-6 | As a worker, I want substituted boundaries identified explicitly so that legitimate fixtures remain useful without being mistaken for real-boundary proof. | G-1 |
| US-7 | As an operator, I want itemized custody, enforceable creation budgets, and evidence-backed dispositions so that temporary resources cannot be resolved or removed by inference. | G-3 |
| US-8 | As a conductor, I want existing critique seats to challenge route identity, contract agreement, conflicting identities, and callable predecessors so that relevant weaknesses are examined within the existing review budget. | G-1, G-2 |
| US-9 | As a conductor, I want finalized obligations and fixed Concern dispositions tied to adequate tests and proof targets so that implementation promises cannot substitute for enforcement. | G-1, G-4 |
| US-10 | As an independent reviewer, I want incident replays, controls, and target mutations to demonstrate the declared gate behavior so that required evidence dimensions have observable effects. | G-1, G-2, G-3 |
| US-11 | As an operator, I want explicit version-based enforcement and a compatible rollout so that protected in-flight work is not unexpectedly failed. | G-4 |
| US-12 | As the delivery conductor, I want the reform delivered through the available bounded process and subsequently exercised from the start of a v6 workflow so that delivery and adoption are demonstrated honestly. | G-4 |
| US-13 | As a blocked worker, I want the failed expectation, evidence limitation, and next action explained so that I can recover without discarding unrelated completed work. | G-1, G-4 |
| US-14 | As an operator returning after interruption, I want incomplete runs and surviving temporary resources reconciled so that interruption cannot imply completion or exemption. | G-3, G-4 |
| US-15 | As an integration maintainer, I want explicit compatibility and validation ownership so that producers and consumers agree without duplicating each other’s responsibilities. | G-1, G-4 |
| US-16 | As a downstream maintainer, I want an adoption guide and an ordinary-work control example so that I can introduce the reform without unnecessary requirements on unaffected work. | G-1, G-4 |

## 7. Functional Requirements

### FR-1 — Applicability and progressive authoring

Additional proof-target requirements apply to the declared triggers: primary goal-discharge tests, critical seams, cross-runtime or separately deployed behavior, money effects, authority migration, and replacement.

Structural evidence determines authority-census applicability. Keywords alone never trigger it.

The user must see the trigger and its reason.

| Point in the workflow | Required behavior |
|---|---|
| Initial authoring | Permit incomplete expectations with explicit unresolved status and actionable warnings |
| Acceptance definition | Identify the intended outcome, caller, path, applicable contract expectations, and observable success criteria |
| Finalize under new enforcement | Require adequate binding for each triggered obligation; unresolved requirements cannot be represented as complete |
| Execution and promotion | Require all applicable expectations and sufficient observations before verified closure |

An early draft may be incomplete. It must never be silently presented as a complete binding.

Requirements irrelevant to an obligation may be marked inapplicable with a justified reason. Runtime requirements must not create a universal obligation to start a service.

### FR-2 — Obligation identity and execution evidence

All expected target properties that change what an obligation means must participate in its identity. Observations from a particular execution must not.

Changing the intended target invalidates reliance on evidence or waivers tied to the previous target. Capturing another observation alone does not change the obligation’s identity.

Evidence must have verifiable origin and association with the relevant execution. Owner-authored assertions alone are insufficient.

The user must be able to distinguish:

- Matching evidence.
- Observed mismatch.
- Missing evidence.
- Stale evidence.
- Unsupported evidence origin.

Freshness requirements must be declared before acceptance, including the applicable validity window and events that invalidate an observation.

### FR-3 — Evidence classification

REAL-DATA requirements remain unchanged.

Incident-derived fixtures, mutations, and known-good/known-bad controls retain their actual evidence classification. They may establish that a validator behaves correctly without establishing that a live product boundary was exercised.

Boundary substitutions must be declared by the boundary replaced and the evidence they can support. Lexical references to “mock” are advisory.

A waiver records an exception or accepted risk. It does not produce a verified-proof outcome. A process-failure note provides attribution and never discharges a proof obligation.

### FR-4 — Authority census and cutover completeness

A triggered authority review must establish:

- The discovery scope and supporting evidence.
- Relevant callable paths producing equivalent outcomes.
- Current and intended authority roles.
- A single intended authority per outcome, with any coexistence policy explicit.
- Relevant callers, predecessors, and unresolved uncertainties.

An independent reviewer must assess whether the declared discovery scope supports the completeness claim. Structural validation alone cannot establish that no path was omitted.

Unresolved material uncertainty remains visible and prevents claiming a complete cutover.

Every role-changing path requires applicable obligations for production, consumption, delivery, activation, running identity, acceptance, predecessor behavior, and retirement.

A nonblank explanation alone does not justify omission. Review must establish that the obligation is actually inapplicable.

Each censused caller affected by the migration must have a corresponding consumer obligation. Completion requires the intended dependency ordering and evidence for applicable predecessor dispositions.

Planning these obligations does not authorize deployment, live-money actions, or deletion.

### FR-5 — Custody lifecycle

Every durable pipeline-owned temporary authority requires an itemized custody record identifying its ownership, location, dependencies, status, and disposition evidence.

A branch and worktree that are separately managed authorities remain separately accountable.

Budget admission uses the projected total:

> Creation is permitted only when the resulting in-scope total remains within the authorized budget.

Concurrent requests must not each consume the same remaining capacity.

A budget exception must identify its scope and authorized limit. It grants no destructive authority.

Preserved resources remain budgeted while the pipeline retains custody or depends on them. Removing an item from budget accounting requires evidence that the relevant custody or dependency ended.

Independent reviewer checkouts and user-owned resources remain outside scope unless adopted by the pipeline.

A tool-turn workspace is exempt only if its lifecycle actually ends within that turn. A surviving workspace, including one left by interruption, must be reconciled before further dependent work proceeds.

Aggregate count changes cannot establish individual dispositions.

This release provides itemized accounting and removal-preview validation. It does not execute removal. Any subsequent removal remains a separately authorized action, with the required inventory, runtime-dependency assessment, recovery reference, and exact authorization.

### FR-6 — Actionable failure and recovery

Every warning or rejection must identify:

- A stable code and plain-language explanation.
- The affected test, obligation, path, or custody item.
- Expected and observed information, where available.
- Evidence that is missing or insufficient.
- The responsible next actor and permitted recovery.

Unavailable evidence must not be reported as an observed mismatch or a pass.

After interruption, completed work remains retrievable. Incomplete operations require reconciliation before closure. Recovery must not duplicate custody accounting or assume an unobserved outcome.

Unavailable independent review must be reported as unavailable. It cannot be replaced by claimed or simulated review.

### FR-7 — Critique and finalize

The accepted critique quorum remains Codex plus Gemini. New identity questions use the existing review seats and bounded review process.

Critics examine wrong-route proof, producer/consumer disagreement, contradictory identity fields, and callable predecessors.

Evidence supplied to a critic must answer the requested target. Evidence about another target produces an explicit blocked answer with its limitation attached.

The ORACLE alignment is in scope. Scored executable oracles must demonstrate the required known-good and known-bad behavior. Unvalidated oracles remain explicit residue and cannot count toward verified reconciliation.

A Concern claimed fixed requires an enforcing test and proof target. Other permitted dispositions retain their own authority, rationale, ownership, and expiry requirements. An implementation Task Card alone cannot establish a fix.

Checks for overly permissive assertions operate on declared acceptance expectations; unrestricted interpretation of arbitrary test code is outside scope.

### FR-8 — Compatibility and integration ownership

Preserve the accepted operator decisions:

| Decision | Product requirement |
|---|---|
| OQ-1 | Expected target properties participate in obligation identity |
| OQ-2 | Workspaces fully created and cleaned within one tool turn are exempt from custody accounting |
| OQ-3 | D-2 ORACLE alignment is in scope |
| OQ-4 | Fizzy validates plan and metadata contracts; a new Fizzy-side TMR mirror is outside scope |
| OQ-5 | Enforcement follows the Session Card’s `pipeline_version`: v5 warns; v6 rejects |
| OQ-6 | Codex and Gemini provide the required critique quorum |

Genuinely grandfathered cards with an absent version retain documented legacy behavior. Failure to retrieve metadata, malformed values, and unsupported versions must not silently select legacy behavior.

Legacy evidence remains readable and visibly unbound. It cannot satisfy a newly bound obligation without appropriate new evidence.

Supported writers must preserve valid versioned extension content. If a writer cannot safely preserve it, it must report the incompatibility before rewriting. A version marker does not automatically legitimize arbitrary unknown content.

Plan validation and loading must agree on acceptance classification within their declared shared contract.

### FR-9 — Delivery and self-hosting

Live skill changes ship only through authorized post-finalize pipeline tasks. Previously sanctioned hotfixes retain their recorded exception status.

The delivery Session must use capabilities actually available to it. Newly introduced controls require acceptance evidence from legally implemented candidates and a subsequent v6 workflow that exercises them from the beginning.

No closed Phase is reopened to manufacture compliance.

D0 adequacy must be established before component-level bounded review. Required architecture review must have an explicit owner within the canonical v6 workflow; milestone ordering must not introduce another pipeline Phase.

**Release blocker:** If protected in-flight v6 cards would be newly rejected, the version-only fence and grandfathering promise conflict. Before exposing enforcement, the operator must approve a compatible rollout schedule or a policy amendment. There is no silent downgrade, additional hidden selector, or automatic exemption.

## 8. Non-Functional Requirements

- **Usability:** A new maintainer can follow the first-use example without undocumented assistance.
- **Low overhead:** Untriggered single-path work requires no new binding fields or additional model launches; its extra author input is limited to one applicability rationale line.
- **Integrity:** Missing or ambiguous evidence never becomes verified proof through fallback.
- **Recoverability:** Interrupted work remains inspectable and resumable without inferred completion.
- **Non-destructive behavior:** Readiness checks, evidence validation, and custody accounting do not repair shared contracts or delete resources.
- **Compatibility:** Existing readable evidence remains readable; supported updates preserve valid extension content.
- **Auditability:** Decisions retain the satisfying evidence and relevant quoted requirement, rather than relying on section references or cached counts.
- **Bounded operation:** Review and recovery follow the governing attempt limits. Exhausted uncertainty receives an explicit unresolved outcome.

## 9. Success Metrics and Release Acceptance

These are proposed targets, not observed results. New usability targets require stakeholder adoption.

| Measure | Target and measurement |
|---|---|
| Readiness time | Under five minutes from command invocation on a documented supported environment with prerequisites satisfied; access and installation time reported separately |
| First value | Three representative maintainers new to the feature complete the documented example within 15 minutes from a ready environment, without undocumented assistance |
| Recovery usability | The same participants correctly identify and perform the next action for a missing-target or wrong-target rejection |
| Golden regression behavior | Every case in the approved catalog produces its declared outcome; the supplied baseline describes 15 incident cases and three controls |
| Control acceptance | Every approved unaffected-work control remains accepted |
| Evidence-dimension coverage | Every applicable expected dimension has a declared mutation demonstrating its intended rejection behavior |
| Reject-code coverage | Every code in the approved contract is exercised; the supplied baseline names 22 codes |
| Custody protection | Creation that would exceed budget is rejected; reviewed interruption and missing-record scenarios remain unresolved until itemized |
| Compatibility | Protected legacy cases remain readable and are not retrospectively rejected by new rules |
| Regression health | No new failures relative to the recorded baseline; skip set unchanged; existing failures remain separately attributed |
| Process integrity | Actual process failures recorded; card 21537 targets zero `patch_state` operations, with any nonzero result reported as a missed target |
| Released-workflow proof | A subsequent v6 workflow exercises the delivered controls from initial authoring through closure using the required evidence classes |

A failed mandatory acceptance target remains failed unless resolved or dispositioned through an explicitly permitted release decision. Recording a failure does not make the target pass.

## 10. Scope and Delivery Sequence

### In scope

- First-use documentation and readiness reporting.
- Progressive proof-target expectations and observed-target comparison.
- Typed boundary-substitution provenance.
- Triggered authority discovery and cutover obligations.
- Durable custody accounting and budget enforcement.
- Existing critique-prompt improvements and ORACLE alignment.
- Compatibility, replay coverage, and mutation evidence.
- Process records and a subsequent released-workflow demonstration.

### Delivery sequence

1. Resolve enforcement, process ownership, and dependency readiness.
2. Establish adequate component boundaries and acceptance obligations.
3. Finalize the reform using capabilities actually available.
4. Deliver contract and behavior changes through authorized pipeline tasks.
5. Validate compatible consumers and release acceptance.
6. Expose changes only under the approved grandfathering plan.
7. Exercise the released behavior in a subsequent v6 workflow.

The roadmap manifest owns detailed sequencing. Engineering documents own schemas, modules, storage formats, algorithms, and deployment mechanics.

## 11. Dependencies

| Dependency | Responsible role | Required condition |
|---|---|---|
| Shared TMR contract | Keystone maintainer | Approved semantics and compatible consumer adoption |
| Fizzy plan and metadata validation | Fizzy maintainer | Agreed scope and demonstrated validate/load classification parity |
| Runner observations | Skill maintainer | Evidence origin, applicability, and freshness requirements demonstrable |
| ORACLE alignment | ORACLE owner and conductor | Availability and acceptance scope established before dependent closure claims |
| Codex/Gemini review | Conductor | Required independent seats reachable through the supported review path |
| Incident catalog and baselines | Delivery owner | Traceable cases, evidence labels, expected outcomes, and regression baseline |
| Downstream pilot | prediction-prime maintainer | Adoption owner and appropriate acceptance environment available |
| Governing release order | Conductor | Existing cross-workstream dependencies and shared-writer ordering reconciled |

Unmet dependencies receive an owner and an explicit blocked scope. They do not justify weakening acceptance.

## 12. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Incomplete census creates false confidence | Declare discovery scope, require independent review, retain unresolved paths |
| Fixture results are mistaken for live proof | Preserve evidence classes and separate validator acceptance from product-boundary acceptance |
| New requirements obstruct ordinary work | Progressive authoring, applicability explanations, unaffected-work controls |
| Concurrent or interrupted creation exceeds custody limits | Evaluate projected totals consistently and reconcile surviving resources |
| Self-hosting requires unavailable gates | Separate available delivery controls from subsequent released-workflow evidence |
| Enforcement breaks in-flight v6 work | Resolve the explicit release blocker before exposure |
| Shared contracts diverge | Named ownership and compatible consumer release conditions |
| Model output varies or a reviewer is unavailable | Predeclare evaluation criteria, retain actual returns, report unavailable review |
| Metrics encourage hidden exceptions | Report baseline failures, waivers, process failures, and missed targets separately |

## 13. Outstanding Decisions Before Release

- Resolve the version-only enforcement fence against protected in-flight v6 work.
- Establish one authoritative v6 owner for full architecture-review obligations.
- Confirm which ORACLE capabilities already exist and which require subsequent-cycle proof.
- Approve freshness policies, critic evaluation criteria, and the proposed usability targets.

These decisions do not reopen OQ-1–OQ-6. Any necessary amendment must be explicit and recorded through the governing process.
[/SPEC]