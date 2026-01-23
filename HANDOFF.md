# Execution Planner Implementation Handoff

## Quick Start

You are continuing implementation of the **Execution Planning System** - a feature that bridges finalized PRDs and implementation by decomposing specs into tasks, assigning test strategies, and dispatching Claude Code agents.

**Your task list should persist across sessions via `CLAUDE_CODE_TASK_LIST_ID=execution-planner`.**

---

## Key Files

| File | Purpose |
|------|---------|
| `spec-output.md` | The approved PRD (passed Final Boss review) |
| `tests/execution_planner/test_spec_intake.py` | Real failing tests for FR-1 |
| `tests/execution_planner/test_scope_assessor.py` | Real failing tests for FR-2 |
| `tests/execution_planner/test_task_planner.py` | Real failing tests for FR-3, FR-3.1 |
| `tests/execution_planner/test_agent_dispatch.py` | Real failing tests for FR-7 |

Other test files (`test_test_strategy.py`, `test_over_decomposition.py`, etc.) are stubs - not yet converted to real tests.

---

## Architecture Decisions (Final)

### Stack
| Need | Solution |
|------|----------|
| Task graph + dependencies | **CC Tasks** (native, this session) |
| File reservations (soft locking) | **mcp_agent_mail** (extract just this piece if needed) |
| Memory/audit trail | **Git** (branches, commits, PRs) |

### Why Not Beads?
CC Tasks replaces beads for task tracking. Git commit messages serve as "memory compaction" - no need for separate summarization system.

### Why Not Full mcp_agent_mail?
Most features (messaging, contact permissions, build slots) are nice-to-haves that CC will likely add. Only **file reservations** (soft locking) is unique and potentially needed for parallel agents editing same files.

---

## Implementation Plan

### Critical Path (in order)
1. **spec_intake.py** - Parse PRD markdown, extract FRs, user stories, risks, dependencies
2. **scope_assessor.py** - Analyze spec complexity, recommend single-agent/multi-agent/decomposition
3. **task_planner.py** - Generate task DAG with dependencies, effort estimates, test strategies
4. **agent_dispatch.py** - Launch Claude Code CLI agents, track status, integrate file reservations

### Module Structure to Create
```
execution_planner/
├── __init__.py
├── spec_intake.py      # FR-1: Parse specs
├── scope_assessor.py   # FR-2: Assess scope
├── task_planner.py     # FR-3, FR-3.1: Generate/edit task plans
├── test_strategy.py    # FR-4: Configure test strategies
├── agent_dispatch.py   # FR-7: Dispatch agents
├── execution_control.py # FR-8: Start/stop/pause
└── progress.py         # FR-9: Logging and visibility
```

### Test-First Approach
Tests are written with real assertions that will fail until implementation exists. Run tests to see what needs to be implemented:
```bash
pytest tests/execution_planner/test_spec_intake.py -v
```

---

## PRD Summary (from spec-output.md)

### Core Functional Requirements
- **FR-1**: Spec Intake - Accept markdown PRD, parse structure
- **FR-2**: Scope Assessment - Recommend execution scope with confidence
- **FR-3**: Task Plan Generation - Create DAG with dependencies
- **FR-3.1**: Plan Editing - User can modify tasks before approval
- **FR-4**: Test Strategy - Assign test-first/test-after/test-parallel/none per task
- **FR-5**: Over-Decomposition Guards - Warn on excessive task counts
- **FR-6**: Parallelization Guidance - Suggest git branch strategies
- **FR-7**: Agent Dispatch - Launch Claude Code agents via CLI
- **FR-8**: Execution Control - Start/stop/pause buttons
- **FR-9**: Progress Visibility - Real-time logs
- **FR-10**: Beads + mcp_agent_mail Integration (now: CC Tasks + file reservations)

### Key Constraints
- Use Claude Code CLI (not SDK) - leverages Pro/Max subscription
- Full spec passed to agents (no trimming)
- Atomic writes for state persistence (temp file + rename)
- Scan for secrets before dispatch to non-local LLMs

---

## What's Already Done

1. In-depth interview for requirements
2. PRD drafted and refined through adversarial debate
3. Gauntlet with 72 concerns from 5 adversary personas - all addressed
4. Final Boss (UX Architect) review - **APPROVED**
5. Test specifications written for critical path FRs (4 files, ~100 tests)
6. Stack decision: CC Tasks + optional file reservations from mcp_agent_mail
7. This handoff document

---

## Next Steps

1. Create `execution_planner/` module directory
2. Implement `spec_intake.py` to make tests pass
3. Implement `scope_assessor.py` to make tests pass
4. Implement `task_planner.py` to make tests pass
5. Implement `agent_dispatch.py` to make tests pass
6. (Optional) Extract file reservation functionality from mcp_agent_mail

---

## File Reservations from mcp_agent_mail

If you need file locking for parallel agents, the relevant tools from mcp_agent_mail are:
- `file_reservation_paths()` - Reserve files with TTL
- `release_file_reservations()` - Release when done
- `renew_file_reservations()` - Extend TTL
- Pre-commit guard that blocks commits on reserved files

The mcp_agent_mail project is at: `/data/projects/mcp_agent_mail` (if accessible) or can be installed via the MCP server.

---

## Running Tests

```bash
# All execution planner tests
pytest tests/execution_planner/ -v

# Just spec intake
pytest tests/execution_planner/test_spec_intake.py -v

# With coverage
pytest tests/execution_planner/ --cov=execution_planner --cov-report=term-missing
```

---

## Session Continuity

This handoff was created from a session that:
- Used the `/adversarial-spec` skill to develop the PRD
- Ran gauntlet with `--final-boss` flag for UX approval
- Evaluated CC Tasks vs beads vs mcp_agent_mail
- Created test-first specifications

All context is preserved in the files above. You should be able to continue implementation without re-running any discovery or planning.

**Start with**: `pytest tests/execution_planner/test_spec_intake.py -v` to see failing tests, then implement `execution_planner/spec_intake.py`.
