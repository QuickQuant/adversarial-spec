# Architecture Primer: adversarial-spec

> Generated: 2026-03-22 | Git: c3b5f8c
> Freshness: fresh | Trust: Current HEAD with no relevant drift

## System Summary

adversarial-spec is a Claude Code skill that iteratively refines product specifications through multi-model adversarial debate. It dispatches specs to multiple LLMs (Claude, GPT, Gemini, Grok, Mistral, etc.) via LiteLLM and CLI subprocess calls, collects critiques, and drives consensus through debate rounds. For stress-testing, a 7-phase gauntlet pipeline sends specs through named adversary personas, evaluates concerns with frontier models, and produces a pass/refine/reconsider verdict. The system is CLI-driven (no daemon), checkpoint-resumable, and uses ThreadPoolExecutor for parallel model calls.

## Most Important Components

| Component | Role | Runtime | Architecture |
|-----------|------|---------|--------------|
| Debate Engine | CLI entrypoint + multi-round debate orchestration (debate.py) | implemented | active_primary |
| Gauntlet Pipeline | 7-phase adversarial stress-test (16-module package) | implemented | active_primary |
| Models | LLM call abstraction via LiteLLM + CLI subprocess routing | implemented | active_primary |
| Adversaries | Named attacker persona definitions with version tracking | implemented | active_primary |
| Providers | Model config, cost rates, Bedrock support, CLI availability | implemented | active_primary |
| Gauntlet Persistence | FileLock-guarded checkpoint/resume for gauntlet phases | implemented | active_primary |
| Pre-Gauntlet | Git/system context collection before gauntlet runs | implemented | active_primary |
| MCP Tasks | Cross-agent task coordination via MCP protocol | implemented | active_primary |

## Shared Contracts and Boundaries

- **Concern/Evaluation/Rebuttal chain** (`gauntlet/core_types.py`): The core data model flowing through all 7 gauntlet phases. Every phase reads and extends these types. Changing fields here affects 12+ files.
- **ADVERSARIES dict** (`adversaries.py`): Frozen dataclasses defining attacker personas. Consumed by all gauntlet phase modules and the debate engine.
- **MODEL_COSTS lookup** (`providers.py`): Static cost-per-token table. Must be updated when adding new models or prices change.
- **Checkpoint schema** (`persistence.py`): Hash-keyed JSON files in `.adversarial-spec-gauntlet/` with FileLock coordination. Spec hash + config hash combo validates checkpoint freshness.
- **SessionState** (`session.py`): Debate round state persisted to `~/.config/adversarial-spec/sessions/`. No file locking (single-user assumption).

## Non-Obvious Gotchas

- **Two gauntlet CLIs with divergent flags**: `debate.py` uses `--codex-reasoning`/`--gauntlet-resume`, while `gauntlet/cli.py` uses `--attack-codex-reasoning`/`--resume`. Not aliased.
- **CLI models are zero-cost**: Codex, Gemini CLI, and Claude CLI route through subprocess, not LiteLLM. They report 0 tokens and $0 cost. This is intentional (subscription-based).
- **scope.py is NOT dead code**: 606 lines, has active tests in `test_adversaries.py` (scope_guidelines validation). CON-002 was invalidated.
- **Unattended mode monkey-patches builtins.input**: `run_gauntlet()` replaces `input()` globally when `--unattended` is set. Restored in `finally` block.
- **Pydantic used but not in pyproject.toml**: `pre_gauntlet/models.py` uses Pydantic BaseModel as an implicit dependency.
- **No explicit "Spec" type**: Specs flow as plain `str` throughout the system. No dataclass wraps them.
- **gauntlet_monolith.py is a 12-line shim**: Delegates to `gauntlet/cli.py:main()`. Legacy compatibility only.

## Top Actionable Concerns

See [concerns.md](concerns.md) for the full rollup. Start here:

1. **CON-001: tasks.json concurrent write hazard** (now) — MCP server and TaskManager both write `.claude/tasks.json` without locking. Real data loss risk in multi-agent workflows. Fix: add FileLock wrapper.
2. ~~**CON-002: Dead code cleanup**~~ — INVALIDATED. All three files are actively used (see concerns.md for details).
3. **CON-003: Unify model dispatch** (next) — Three competing dispatch paths prevent uniform improvements.

## Escalation Guidance

- **What should I fix first?** Read [concerns.md](concerns.md).
- Read [overview.md](overview.md) when you need the full system narrative.
- Read [structured/flows.md](structured/flows.md) when the task crosses component boundaries.
- Read matched docs in [structured/components/](structured/components/) when the task touches a specific blast zone.
- Read [access-guide.md](access-guide.md) for guided reading paths by task type.
