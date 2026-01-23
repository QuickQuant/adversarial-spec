# PRD: Execution Planning System

## Executive Summary

The Execution Planning System converts finalized specifications into executable plans and coordinates AI agent work. It delivers scope assessment, task decomposition with dependencies, test strategy configuration, parallel workstream guidance, and progress visibility. The system integrates with beads for git-backed task tracking and dispatches Claude Code agents for execution.

The MVP reduces failed agent runs and coordination overhead while keeping the process lightweight for small tasks. It creates a bootstrapping opportunity where the system helps design its own future monitoring dashboard.

## Problem Statement

### Current Pain Points

1. **No Clear Execution Path**: After adversarial debate produces a finalized spec, there's no systematic process to translate it into executable work
2. **Scope Misjudgment**: Single agents take on specs that are too large, or teams over-decompose simple tasks into unnecessary bureaucracy
3. **Poor Parallelization**: Work streams that could run concurrently get serialized, wasting time and context
4. **Implementation Drift**: Without tests or acceptance criteria upfront, implementation diverges from the spec's intent

### Evidence

**Qualitative** (from internal dogfooding):
- Frequent re-scoping after agent failures due to incorrect initial sizing
- Unclear dependencies causing blocked work during parallel execution
- Limited visibility into agent progress leading to late discovery of issues

**Estimated baselines** (to validate during pilot):
- Time from spec approval to first task start: ~60-90 minutes (manual planning overhead)
- Agent runs requiring re-scope: ~35% (due to incorrect initial sizing)
- Manual intervention frequency: ~50% of multi-task executions

### Opportunity

A standardized execution planning step can cut time to start, reduce rework, and improve parallel execution without heavy process overhead.

## Target Users / Personas

### Primary: Alex - AI-Augmented Developer

**Context**: IC engineer (3-7 years experience) on a 2-5 person product team. Uses Claude Code daily for features and bug fixes. Switches between 2-3 codebases weekly.

**Decision Authority**: Can start agent runs, choose task ordering, and intervene during execution. Needs clarity on scope before committing time.

**Goals**:
- Know if a spec fits a single agent session or needs decomposition
- Get a clear task plan that fits within a single focus window
- Track progress without constant monitoring
- Intervene quickly when agents go off-track

**Pain Points**:
- Wasted time when agents attempt specs that are too large and fail
- Lost context when switching between parallel work streams
- Minimal tooling overhead preferred

### Secondary: Jordan - Technical Lead

**Context**: Leads 4-10 engineers (human and AI). Accountable for delivery timelines and code quality. Balances coordination across multiple workstreams.

**Decision Authority**: Approves execution plans before agent dispatch. Can halt execution and reassign work. Must justify timelines and manage risk.

**Goals**:
- Confident scope estimates before committing to timelines
- Clear task dependencies to sequence work correctly
- Early warning on blockers

**Pain Points**:
- Scope surprises mid-implementation
- Unclear dependencies causing blocked work
- No unified view of human and agent work

## User Stories

### Scope Analysis
- **US-1**: As Alex, I want a scope recommendation (single-agent vs multi-agent vs decomposition-required) so that I don't waste time on runs likely to fail.
- **US-2**: As Jordan, I want to see the factors behind a scope recommendation so that I can approve or override it confidently.

### Task Decomposition
- **US-3**: As Alex, I want tasks with clear acceptance criteria and dependencies so that I can execute without guessing.
- **US-4**: As Alex, I want to export the plan to beads so that I can use git-backed tracking for visibility.
- **US-5**: As Alex, I want warnings when a plan is over-decomposed so that small specs stay lightweight.

### Plan Editing
- **US-15**: As Alex, I want to manually add, edit, or remove tasks and modify dependencies in the generated plan so that I can correct errors or adjust strategy before execution begins.

### Test Strategy
- **US-6**: As Alex, I want to mark high-risk tasks as "test-first" so that tests serve as executable acceptance criteria before implementation.
- **US-7**: As Alex, I want test-after and test-parallel options so that I can balance rigor with speed based on task risk.

### Parallelization
- **US-8**: As Jordan, I want independent workstreams identified so that I can assign parallel work safely.
- **US-9**: As Jordan, I want merge order recommendations so that integration is predictable.

### Execution Control
- **US-10**: As Alex, I want agents dispatched automatically once I approve a plan so that I don't manually coordinate each task.
- **US-11**: As Alex, I want clear status reporting so that I trust when a task shows "completed".
- **US-12**: As Alex, I want to pause, skip, retry, or force-complete tasks so that I can recover from failures without restarting.

### Progress Visibility
- **US-13**: As Jordan, I want real-time status showing tasks by state (queued, running, blocked, completed, failed) so that I can intervene early.
- **US-14**: As Alex, I want execution logs persisted so that I can debug failures after the fact.

## Functional Requirements

### FR-1: Spec Intake
- Accept finalized PRD, technical specification, or debug investigation documents
- Preserve context: assumptions, risks, acceptance criteria from adversarial-spec output
- **Large specs**: If spec is too large for single execution plan, adversarial-spec should have already suggested splitting into multiple specs. Each spec maps to a beads epic; tasks within each spec become beads issues under that epic.

### FR-2: Scope Assessment
- Provide recommendation: `single-agent`, `multi-agent`, or `decomposition-required`
- Include confidence level (low/medium/high)
- Explain main drivers: component count, integration points, risk factors, estimated total effort
- **Fast-path**: If `single-agent` with high confidence, user can skip task decomposition entirely and dispatch directly. Still create a single beads issue for the record—keeps tracking simple without overhead.

### FR-3: Task Plan Generation
- Generate tasks with:
  - Title and description
  - Dependencies (blocking relationships)
  - Acceptance criteria (derived from spec)
  - Effort estimate (XS/S/M/L/XL)
  - Risk level (low/medium/high)
  - Validation strategy assignment
  - Parallel stream assignment

### FR-3.1: Plan Editing
- Allow user to modify the plan structure prior to approval:
  - Add/Delete tasks
  - Edit task details (title, description, acceptance criteria)
  - Modify dependencies
  - Change test strategy
  - Reorder tasks
- **Validation before approval**:
  - Detect circular dependencies and prompt user to resolve
  - Warn if deleting a task that others depend on (basic detection, not foolproof)
  - If user configures absurd thresholds (e.g., 500 tasks for a small spec), prompt "Are you sure?"

### FR-4: Test Strategy Configuration
- Per-task validation strategy:
  - `test-first`: Test task blocks implementation task; tests written before code
  - `test-after`: Implementation completes, then validation runs
  - `test-parallel`: Both run concurrently (for integration scenarios)
  - `none`: No automated tests (documentation, config changes)
- LLM recommends strategy per task based on risk, complexity, and task type
- User can override any recommendation during plan review
- **Vague acceptance criteria**: Tests are the primary defense against hallucinated completion. If AC is vague (e.g., "UI should be responsive"), test-first forces concrete verification before implementation is marked complete.

### FR-5: Over-Decomposition Guards
- Warn when task count exceeds threshold for spec size
- Require confirmation for large plans
- Offer consolidation suggestions
- Allow user-configurable thresholds

### FR-6: Parallelization Guidance
- Identify independent workstreams
- Recommend execution order and merge sequence
- Support single-branch, feature-branches, and stacked-branches patterns
- Suggest branch structure with unique naming (include timestamp or run ID to avoid collisions on retry)
- **Merge conflict learning**: When merge conflicts occur, record contested files. Use this history to improve future parallelization recommendations and identify files that should not be edited concurrently.
- **Excessive conflicts**: If many merge conflicts occur, this indicates a planning problem. System should suggest re-planning with better task isolation rather than continuing to resolve conflicts manually.

### FR-7: Agent Dispatch & Status
- Dispatch agents via available Claude Code environment
- Pass context: task description, acceptance criteria, **full spec** (no trimming), dependency status
- Track status: queued, running, completed, failed, blocked
- Provide clear completion indicators users can trust
- Assign unique agent number at dispatch for branch naming (agent-1, agent-2, etc.)
- **Coordination**: Integrate with mcp_agent_mail for file reservations to prevent concurrent edits on same files
- **Context security**: Before dispatch, scan spec for potential secrets (API keys, passwords, connection strings). Warn user and redact before sending to non-local LLMs (Gemini). Claude/OpenAI contexts are acceptable per user's data settings.

**TODO (Process Test)**: Verify N concurrent Claude Code instances can run in same directory without session file conflicts.

### FR-8: Execution Control
- Approve plan before execution starts
- Pause all execution on demand
- Skip individual tasks (defer)
- Retry failed tasks with optional context update
- Force-complete tasks manually
- Resume from interruption

### FR-9: Progress Visibility
- Real-time task status view
- Log execution decisions and agent outputs
- Track branch status and merge readiness
- Expose via CLI and beads integration
- Persist state to disk to enable external monitoring
- **Dedicated logging module**: Centralized logging with rotation, retention, and structured output. Logging is central to the log + test development workflow. If logs become noise, it indicates a workflow problem that needs addressing—not just a disk space issue.

### FR-10: Beads + mcp_agent_mail Integration
Follow the established mcp_agent_mail conventions for beads integration:
- **Single source of truth**: Beads owns task status/priority/dependencies; mcp_agent_mail owns conversation, file reservations, and audit trail
- **Shared identifiers**: Use beads issue id (`bd-123`) as Mail `thread_id` and prefix message subjects with `[bd-123]`
- **File reservations**: When starting a task, call `file_reservation_paths()` with issue id in `reason`; release on completion
- **Conflict prevention**: Pre-commit guard blocks commits on files with active reservations by other agents
- **Status sync**: Agent sends message to orchestrator thread on task completion; orchestrator updates beads status

**User guidance**: Do not manually edit beads files while the execution system is running. Concurrent edits may cause sync conflicts.

## Non-Functional Requirements

### NFR-1: Performance
- Scope assessment: <30 seconds for typical specs
- Plan generation: <60 seconds
- Agent dispatch latency: <5 seconds per task

### NFR-2: Reliability
- Execution state persists across crashes using atomic writes (temp file + rename)
- Resume without losing history
- Automatic retry for transient failures
- Critical file operations (state, migrations) use safe write wrappers

**TODO (Test Case)**: Verify agents can be reliably stopped mid-execution. Must be able to halt an agent even during long-running operations.

### NFR-3: Security & Privacy
- Respect repository access permissions
- Redact sensitive data in logs
- Support user-controlled retention
- **LLM data policies**: Claude and OpenAI do not train on user data (per user's account settings). Gemini may expose content to human reviewers. Scan for secrets before dispatch to non-local LLMs; warn and redact if found.

### NFR-4: Usage Monitoring
- Track message/request counts during execution
- Surface usage metrics in status output
- Enable detailed monitoring via Phase 2 dashboard
- **Rate limiting**: If rate limits are encountered, develop throttling strategy at that time. No preemptive complexity.

### NFR-5: Usability
- Outputs are concise and reviewable
- No additional tooling required to understand plan
- Actionable within 5 minutes of review

## Success Metrics

### Primary Metrics

| Metric | Target | Baseline (est.) | Measurement | Window |
|--------|--------|-----------------|-------------|--------|
| Time to first task start | 50% reduction | ~75 min | Spec approval to first agent dispatch | Per plan, rolling 30-day avg |
| Task completion without re-scope | >80% | ~65% | Tasks completed without plan edits after start | Per plan |
| Scope accuracy | <25% variance | ~40% | \|Estimated - actual effort\| / actual | Per task, aggregated monthly |

### Secondary Metrics

| Metric | Target | Measurement | Window |
|--------|--------|-------------|--------|
| Plan acceptance rate | >80% approved with ≤2 edits | User edits before approval | Per plan |
| Over-decomposition rate | <15% | Plans where user collapses tasks | Per plan |
| Parallel efficiency | >50% utilization | Concurrent runtime / total runtime | Per multi-stream plan |
| Trust indicator | >85% | Completed tasks accepted without manual override | Per plan, rolling 30-day avg |

## Scope

### In Scope (MVP)
- Spec intake and scope assessment with rationale
- Task plan generation with dependencies, acceptance criteria, and test strategy
- Plan editing (Add/Edit/Delete/Reorder) prior to execution
- Over-decomposition guardrails
- Parallelization guidance with branch suggestions
- Agent dispatch with Claude Code
- Execution control (approve, pause, skip, retry, force-complete)
- Progress visibility via CLI and beads integration
- Local state persistence

### Out of Scope (MVP)
- Custom web dashboard (use beads UIs or CLI)
- Automatic branch creation or merging
- Support for non-Claude agents (Codex, Gemini)
- CI/CD integration
- Historical analytics beyond current plan
- Execution-plan-specific adversary personas

### Future Phases

**Phase 2: Dashboard** - Web-based monitoring (React), real-time visualization, intervention controls, "agent in flight" warnings before pause (shows what each agent is currently doing so user can decide whether to interrupt)

**Phase 3: Extended Agents** - Codex CLI, Gemini CLI, custom adapters

**Phase 4: Execution Adversaries** - resource-scheduler, dependency-analyst, risk-assessor, efficiency-critic, reality-checker personas

## Dependencies

### Required
- Claude Code (installed, authenticated)
- Git
- Python 3.10+ with litellm
- Beads for task tracking
- mcp_agent_mail for multi-agent coordination

### Optional
- LLM API keys for planning (uses Claude Code by default)

### Organizational
- Security review for execution log handling
- Access to target repositories

## Risks and Mitigations

### R-1: Over-Decomposition (HIGH)
**Risk**: Creates too many tasks, adding overhead.
**Mitigations**: Guardrails, consolidation prompts, user-configurable thresholds.

### R-2: Under-Scoping (MEDIUM)
**Risk**: Recommends single-agent for specs that are too complex, leading to failures.
**Mitigations**: Conservative sizing, confidence indicators, checkpoint prompts.

### R-3: Low Trust in Recommendations (MEDIUM)
**Risk**: Users ignore scope recommendations if rationale is unclear.
**Mitigations**: Transparent explanations, easy override, track recommendation accuracy.

### R-4: Agent Divergence (MEDIUM)
**Risk**: Agents implement something different from spec intent.
**Mitigations**: Per-task acceptance criteria, test-first for high-risk, human checkpoints.

### R-5: Beads Integration Volatility (MEDIUM)
**Risk**: Beads evolves with breaking changes.
**Mitigations**: Use stable CLI interface, version awareness, local fallback.

### R-6: Rate Limit Exhaustion (LOW)
**Risk**: Heavy execution hits subscription rate limits.
**Mitigations**: Usage monitoring, throttling between tasks, visibility in dashboard.

### R-7: Sensitive Data Exposure (LOW)
**Risk**: Logs contain credentials or PII.
**Mitigations**: Redaction, access controls, retention policies.

## Decisions

1. **Opinionated stack**: Beads for task tracking, mcp_agent_mail for coordination (not pluggable).
2. **Agent dispatch**: System utilizes the user's local authenticated Claude Code environment (optimizing for existing Pro/Max subscriptions over API credits).
3. **Test strategy defaults**: LLM recommends per task; user can override.
4. **Merge conflicts**: System detects merge conflicts in the workspace, pauses affected tasks, and alerts user for resolution. No auto-resolution.
5. **Spec updates mid-execution**: Not supported in MVP. Cancel and regenerate required.
6. **Cost model**: Relies on user's existing subscription; monitor usage, not dollars.

---

*Document revised after Round 4 adversarial debate. Incorporated plan editing capability from Gemini's feedback. Gauntlet review completed: 72 concerns addressed, security concerns dismissed (personal use), mitigations added for state persistence, circular dependency detection, context security, logging, and mcp_agent_mail integration.*
