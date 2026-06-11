# Architecture: adversarial-spec

> Generated: 2026-06-11 (incremental from 9ca3ccd) | Git: f198887 | Target: /home/jason/PycharmProjects/adversarial-spec
> Skill version: 3.8 | Model: claude-fable-5
> Freshness: fresh | Trust: verified at f198887

## System Summary

adversarial-spec is a Claude Code skill for iterative spec refinement through multi-model adversarial debate. It dispatches specifications to multiple LLMs for critique, drives consensus through debate rounds, and stress-tests specs through a 7-phase gauntlet pipeline with named adversary personas. The system is CLI-driven, checkpoint-resumable, and uses ThreadPoolExecutor for parallel model calls; multi-agent pipeline work is coordinated by harness hooks on a Fizzy board.

## Quick Start

- **Primer first:** [primer.md](primer.md) is the default small-context entrypoint for LLMs and humans.
- **Fix-first:** [concerns.md](concerns.md) answers "what should I fix first?"
- **Navigation only:** this file helps you choose what to read next — do not pass it to opponent models.
- **Need guided reading?** Start with [access-guide.md](access-guide.md).

## Components

| Component | Purpose | Runtime | Architecture | Key Files |
|-----------|---------|---------|--------------|-----------|
| Debate Engine | CLI routing, pipeline-card + staleness gates, debate orchestration | implemented | active_primary | debate.py |
| Gauntlet Pipeline | 7-phase adversarial stress-test (clustering + batch tiering) | implemented | active_primary | gauntlet/orchestrator.py, gauntlet/core_types.py, gauntlet/batch_tiering.py, gauntlet/clustering.py |
| Models | LLM call abstraction (LiteLLM + CLI subprocess) + preflight | implemented | active_primary | models.py |
| Token Tracking | Thread-safe token/cost accounting singleton | implemented | active_primary | token_tracking.py |
| Providers | Model config, cost rates, Bedrock, CLI detection | implemented | active_primary | providers.py |
| Adversaries | Named attacker persona definitions + templates | implemented | active_primary | adversaries.py |
| Prompts | Debate prompt templates (gauntlet prompts separate) | implemented | active_primary | prompts.py, gauntlet/prompts.py |
| Emission Toolchain | Fizzy v3 plan emission + offline self-check | implemented | active_primary | mini_spec_emission.py |
| Gauntlet Persistence | Integrity-envelope checkpoint/resume + stats | implemented | active_primary | gauntlet/persistence.py |
| Harness Hooks | Multi-agent pipeline coordination + safety | implemented | active_primary | .claude/hooks/*.py |
| Pre-Gauntlet | Git/system context collection before gauntlet | implemented | active_secondary | pre_gauntlet/orchestrator.py |
| Session | Debate state persistence (multi-round resume) | implemented | active_secondary | session.py |
| Execution Planner | Gauntlet concern parsing (deprecated remainder) | partial | deprecated | execution_planner/gauntlet_concerns.py |

Retired June 2026 (deleted, no dangling imports): MCP Tasks (`mcp_tasks/`), `task_manager.py`, `scope.py`, `gauntlet_monolith.py`.

## Navigation

**Understand the system:**

| Question | Read |
|----------|------|
| What does this system do? | [primer.md](primer.md) |
| What should I read next? | [access-guide.md](access-guide.md) |
| What does this system do in depth? | [overview.md](overview.md) |
| Where is code located? | [filesystem-map.md](filesystem-map.md) |

**Fix things:**

| Question | Read |
|----------|------|
| What should I fix first? | [concerns.md](concerns.md) |
| What are the architectural hazards? | [concerns.md](concerns.md) → [findings.md](findings.md) → [patterns.md](patterns.md) |

**Work on specific tasks:**

| Task | Read |
|------|------|
| Evaluate a plan against the codebase | [primer.md](primer.md) → matched [component docs](structured/components/) → [cross-references.md](structured/cross-references.md) |
| Deep-dive a component | [primer.md](primer.md) → [overview.md](overview.md) → [components/{relevant}.md](structured/components/) |
| Modify the gauntlet | [components/gauntlet.md](structured/components/gauntlet.md) → [structured/flows.md](structured/flows.md) |
| Add a model/provider | [components/providers.md](structured/components/providers.md) + [components/models.md](structured/components/models.md) (update MODEL_COSTS) |

**Deep reference:**

| Need | Read |
|------|------|
| Every entry point | [structured/entry-points.md](structured/entry-points.md) |
| Flow notation | [structured/flows.md](structured/flows.md) |
| Call graphs / hub files | [structured/cross-references.md](structured/cross-references.md) |
| Raw discovery (this run) | .work/discovery/*.md |

## Architecture Decisions (1-liners)

- Single-invocation CLI; continuity via checkpoints, not daemons.
- Deterministic code over LLM subagents for data processing (clustering, tiering, extraction).
- FileLock + integrity-hashed envelopes for all gauntlet state; resume validates everything.
- Gates enforced in code (pipeline-card, tests-staleness, Phase-1 quality, preflight), not by convention.
- Hooks are the multi-agent coordination plane; they never import skill code.

## Generation Metadata

- Generated: 2026-06-11 | Target: project root | Git: f198887 (from 9ca3ccd, 52 commits)
- Freshness: fresh | Architecture verified at f198887
- This file is for navigation only — never pass INDEX.md as `--context` to debate.py; pass the substantive docs it references.
