# Execution Planner Partial Deprecation Spec

**Status:** Final (post-debate consensus)
**Date:** 2026-02-06
**Debated with:** codex/gpt-5.3-codex, gemini-cli/gemini-3-pro-preview
**Decision:** Option B+ (keep validation code + convert generation to LLM guidelines)

---

## Problem Statement

The execution planner (`execution_planner/`) is a 13-module Python package that automates the bridge from finalized specs to implementation tasks. In practice, it fails because:

1. **Format mismatch**: The regex-based `SpecIntake` parser expects `FR-X` prefixes, numbered sections, and TypeScript blocks. The adversarial debate process produces narrative prose. Result: 0 tasks generated from a spec with 56 gauntlet concerns.

2. **LLM is strictly better at generation**: The Brainquarters project proved that Claude manually creating execution plans produces superior, more contextual results than the automated pipeline.

3. **Unused automation**: `AgentDispatcher`, `ExecutionController`, and `ProgressTracker` were never used in production - Claude Code's native capabilities supersede them.

## Decision

**Option B+: Keep validation code for structured data. Convert generation logic to LLM prompting guidelines. Remove unused automation.**

### What to KEEP (as code)

| Module | Reason |
|--------|--------|
| `gauntlet_concerns.py` | Parses structured JSON output from `debate.py gauntlet` - known, stable schema. Used by `debate.py` for concern linking. |
| Data models (`GauntletConcern`, `GauntletReport`, `LinkedConcern`) | Type-safe interchange format between gauntlet and execution phases. |

### What to CONVERT (code → guidelines in 06-execution.md)

These modules contain valuable *concepts* that work better as LLM prompting guidelines than as rigid Python code:

| Module | Concept to preserve | Guideline form |
|--------|-------------------|----------------|
| `task_planner.py` | Task decomposition with concern linking | "For each spec section, create implementation tasks. Link gauntlet concerns by section reference. Derive acceptance criteria from concern failure modes." |
| `test_strategy.py` | Risk-based test strategy assignment | "Assign test-first to tasks with 3+ concerns or high-severity concerns. Use test-after for low-risk tasks." |
| `over_decomposition.py` | Granularity guards | "Target 1-4 hour tasks. If plan exceeds 15 tasks for a simple spec, consolidate related work. Flag if task count > 2x number of spec sections." |
| `parallelization.py` | Workstream identification | "Identify independent workstreams by checking dependency graphs. Recommend merge sequence by risk level." |
| `scope_assessor.py` | Single vs multi-agent recommendation | "Small specs (< 5 tasks): single agent. Medium (5-15): single with workstreams. Large (15+): consider multi-agent with branch pattern." |

### What to REMOVE (dead code)

| Module | Reason |
|--------|--------|
| `spec_intake.py` | Regex parser that can't handle narrative specs. LLM does this natively. |
| `agent_dispatch.py` | Never used. Claude Code's Task tool supersedes this. |
| `execution_control.py` | Never used. Claude Code's native agentic loop handles this. |
| `progress.py` | Never used. TodoWrite + Tasks MCP handle progress tracking. |
| `llm_extractor.py` | Stopgap that proved the point: if you need an LLM to extract tasks, just let the LLM (Claude) do it directly with good guidelines. No wrapper needed. |
| `__main__.py` | CLI entry point for removed pipeline. |

### debate.py changes

- Keep the `execution-plan` subcommand temporarily but have it print a deprecation notice pointing to the new 06-execution.md guidelines
- Remove `EXECUTION_PLANNER_AVAILABLE` gating and the import block after migration
- Keep gauntlet concern imports (they stay)

## Implementation Plan

### Phase 1: Update 06-execution.md (this session)

Rewrite the execution phase doc to replace the pipeline-based approach with LLM guidelines. The new doc should:

1. **Keep the same phase gate** - still ask "Would you like an execution plan?"
2. **Replace pipeline steps with Claude guidelines** - Claude reads the spec + gauntlet concerns and creates the plan directly
3. **Embed the preserved concepts** - over-decomposition guards, test strategy assignment, concern linking, parallelization advice
4. **Keep gauntlet concern loading** - `debate.py` still outputs structured JSON that Claude should load and reference

### Phase 2: Remove dead modules (separate PR)

1. Delete: `spec_intake.py`, `agent_dispatch.py`, `execution_control.py`, `progress.py`, `llm_extractor.py`, `__main__.py`
2. Update `__init__.py` to only export gauntlet concern types
3. Add deprecation notice to `debate.py execution-plan`
4. Update tests

### Phase 3: Clean up (separate PR)

1. Remove `execution-plan` subcommand from `debate.py`
2. Simplify `execution_planner/` to just the gauntlet concerns module
3. Consider moving `gauntlet_concerns.py` into `scripts/` alongside `gauntlet.py`

## Validation

The new approach is validated when:
- [ ] 06-execution.md contains all preserved concepts as LLM guidelines
- [ ] A test run through Phase 6 with the new guidelines produces a comparable-quality execution plan
- [ ] No Python code is needed for the execution planning workflow (except gauntlet concern parsing)
- [ ] debate.py still works for all other subcommands after removal
