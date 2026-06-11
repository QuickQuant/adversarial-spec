# Architecture Primer: adversarial-spec

> Generated: 2026-06-11 (incremental from 9ca3ccd) | Git: f198887
> Freshness: fresh | Trust: verified at f198887; worktree carried in-flight skill-doc edits at scan time

## System Summary

adversarial-spec is a Claude Code skill that iteratively refines product specifications through multi-model adversarial debate. It dispatches specs to multiple LLMs (via LiteLLM and CLI subprocess calls), collects critiques, and drives consensus through debate rounds. For stress-testing, a 7-phase gauntlet pipeline sends specs through named adversary personas, evaluates concerns with frontier models (power-law tiered batches), and produces a pass/refine/reconsider verdict. The system is CLI-driven (no daemon), checkpoint-resumable with integrity-hashed envelopes, and uses ThreadPoolExecutor for parallel model calls. Multi-agent work (conductor + workers on the Fizzy pipeline board) is coordinated by harness hooks; the old MCP Tasks server is deleted.

## Most Important Components

| Component | Role | Runtime | Architecture |
|-----------|------|---------|--------------|
| Debate Engine | CLI + gates (pipeline-card, tests-staleness) + debate orchestration (debate.py) | implemented | active_primary |
| Gauntlet Pipeline | 7-phase stress-test; Phase 3.5 Jaccard clustering; Phase 4 batch tiering | implemented | active_primary |
| Models | LiteLLM + CLI subprocess routing + NEW parallel preflight ping | implemented | active_primary |
| Token Tracking | Extracted thread-safe cost/token singleton (`token_tracking.tracker`) | implemented | active_primary |
| Adversaries | Frozen personas + v2.0 templates + stable concern IDs | implemented | active_primary |
| Providers | Model config, MODEL_COSTS, CLI availability, Bedrock | implemented | active_primary |
| Emission Toolchain | mini_spec_emission.py — fizzy v3 plan emission + offline self-check mirror | implemented | active_primary |
| Harness Hooks | dispatch injection, forced continue, idle backoff, notifications | implemented | active_primary |
| Gauntlet Persistence | FileLock + integrity-envelope checkpoint/resume | implemented | active_primary |
| Pre-Gauntlet | Git/system context collection | implemented | active_secondary |

## Shared Contracts and Boundaries

- **Concern/Evaluation/Rebuttal chain** (`gauntlet/core_types.py`): the data model flowing through all 7 phases; verdicts normalized to accepted|dismissed|acknowledged|deferred. `GauntletConfig` centralizes all run defaults; `PhaseMetrics` feeds the run manifest.
- **ADVERSARIES dict** (`adversaries.py`): frozen persona registry; `generate_concern_id(adversary, text)` gives deterministic `PREFIX-hash8` IDs (stable cross-run linking).
- **Checkpoint envelope** (`gauntlet/persistence.py`): `{_meta:{schema_version, spec_hash, config_hash, phase, data_hash}, data}` — resume rejects any mismatch.
- **Run manifest**: per-phase metrics + (for v4+ altitude sessions, conductor-written) intensity fields `session_altitude`/`adversaries`/`foci` consumed by fizzy `pipeline_mark_gauntlet_complete`.
- **mini_spec_emission contract**: `PLAN_SCHEMA_VERSION=3` must match fizzy; `ALTITUDE_OBLIGATIONS` table; `self_check_plan()` mirrors live validation reject codes. Pattern for the incoming `validation_emission.py` (card 5604).
- **MODEL_COSTS** (`providers.py`): update when adding models; CLI-prefixed models are zero-cost.
- **Hook I/O**: hooks read stdin JSON / tool results and emit `{decision, systemMessage}`; they never import skill code.

## Non-Obvious Gotchas

- **Two gauntlet CLIs, divergent flags**: `debate.py` (`--codex-reasoning`, `--gauntlet-resume`, timeout 1200s default) vs `gauntlet/cli.py` (`--attack-codex-reasoning`, `--resume`, 1800s). Not aliased.
- **`prompts.py` shadow collision**: `gauntlet/` on sys.path shadows top-level `prompts.py`. Load `gauntlet/persistence.py` standalone via `importlib.util.spec_from_file_location`, never by appending `gauntlet/` to sys.path.
- **Phase 1 parse failure is fatal by design**: text-but-zero-concerns aborts the run with raw responses saved; recover by patching the concerns checkpoint (use `generate_concern_id` + `persistence._data_hash`) and `--resume`.
- **CLI models report 0 tokens / $0** — intentional (subscription).
- **Unattended mode monkey-patches `builtins.input`** (restored in finally).
- **Rate limiting is pre-batch sleep**, not in-pool throttling: free Gemini = 1 call per 15s window in Phase 1.
- **No "Spec" type** — plain strings + sha256 identity.
- **Intensity manifest fields are written by the skill conductor after the run**, not by the orchestrator.

## Top Actionable Concerns

See [concerns.md](concerns.md) for the full rollup (refreshed this run).

1. **CON-001: Triple litellm completion() pathway** — 3 call sites with silently different defaults; fix with a single low-level wrapper.
2. **CON-002: cost_tracker coupling** — now partially addressed by the `token_tracking` extraction, but phases still import the global singleton; finish the move into `model_dispatch.call_model()`.
3. **CON-003: orchestrator complexity** — `run_gauntlet()` remains ~700 lines; extract a phase-table.
4. **CON-007 (new class): divergent CLI flag surfaces** — `debate.py` vs `gauntlet/cli.py` defaults drift (timeout 1200 vs 1800); alias or unify.

## Escalation Guidance

- **What should I fix first?** Read [concerns.md](concerns.md).
- Read [overview.md](overview.md) for the full system narrative.
- Read [structured/flows.md](structured/flows.md) when the task crosses component boundaries.
- Read matched docs in [structured/components/](structured/components/) for a specific blast zone.
- Read [access-guide.md](access-guide.md) for guided reading paths by task type.
