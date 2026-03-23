# Cross References

> Call graphs, data paths, and dependency lookups.
> Generated: 2026-03-22 | Git: c3b5f8c

## Function Call Graph

### Debate Engine

```
main() (debate.py:1493)
  ├── calls: create_parser(), handle_info_command(), handle_utility_command(),
  │          handle_execution_plan(), handle_gauntlet(), apply_profile(),
  │          parse_models(), setup_bedrock(), validate_models_before_run(),
  │          handle_send_final(), handle_export_tasks(), load_or_resume_session(),
  │          run_critique()
  ├── called_by: CLI entry (__name__ == "__main__")
  └── async: no

run_critique() (debate.py:1206)
  ├── calls: call_models_parallel(), generate_diff(), save_checkpoint(),
  │          get_task_manager(), extract_spec()
  ├── called_by: main()
  └── async: no

handle_gauntlet() (debate.py:1018)
  ├── calls: run_gauntlet(), format_gauntlet_report(), load_run_manifest()
  ├── called_by: main()
  └── async: no
```

### Gauntlet Pipeline

```
run_gauntlet() (gauntlet/orchestrator.py:196)
  ├── calls: generate_attacks(), generate_big_picture_synthesis(),
  │          filter_concerns_with_explanations(), cluster_concerns_with_provenance(),
  │          evaluate_concerns_multi_model(), evaluate_concerns_single_model(),
  │          run_rebuttals(), final_adjudication(), run_final_boss_review(),
  │          save_checkpoint(), load_partial_run(), calculate_medals(),
  │          save_run_manifest()
  ├── called_by: handle_gauntlet() (debate.py), main() (gauntlet/cli.py)
  └── async: no

generate_attacks() (gauntlet/phase_1_attacks.py:24)
  ├── calls: call_model() (model_dispatch), run_adversary_with_model(),
  │          resolve_adversary_name(), generate_concern_id()
  ├── called_by: run_gauntlet()
  └── async: no (uses ThreadPoolExecutor internally)

evaluate_concerns() (gauntlet/phase_4_evaluation.py:23)
  ├── calls: call_model() (model_dispatch)
  ├── called_by: run_gauntlet()
  └── async: no
```

### Models

```
call_models_parallel() (models.py:901)
  ├── calls: call_single_model() via ThreadPoolExecutor
  ├── called_by: run_critique(), handle_send_final(), handle_export_tasks()
  └── async: no (uses ThreadPoolExecutor)

call_single_model() (models.py:626)
  ├── calls: call_codex_model(), call_gemini_cli_model(), call_claude_cli_model(),
  │          litellm.completion(), cost_tracker.add()
  ├── called_by: call_models_parallel() (via executor)
  └── async: no

cost_tracker.add() (models.py:165)
  ├── calls: MODEL_COSTS lookup (providers.py)
  ├── called_by: call_single_model() (from multiple threads)
  └── async: no (thread-safe via Lock)
```

## Data Path Summary

```
DATA_PATH                          SOURCE                    TRANSFORMS                             SINK
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
spec_critique                      stdin -> debate.py        call_models_parallel -> aggregate       stdout + checkpoint files
gauntlet_attack                    spec -> phase_1           generate_attacks -> parse concerns      concerns checkpoint JSON
concern_evaluation                 concerns -> phase_4       evaluate_concerns -> parse verdict      evaluations checkpoint JSON
big_picture_synthesis              concerns -> phase_2       generate_big_picture_synthesis          synthesis object
concern_clustering                 concerns -> phase_3.5     cluster_with_provenance                clustered checkpoint JSON
final_boss_review                  evaluations -> phase_7    run_final_boss_review                  final-boss checkpoint JSON
cost_accumulation                  each model call           cost_tracker.add() (Lock)              cost report on stdout
session_state                      SessionState              save() -> JSON                         ~/.config/.../sessions/
pre_gauntlet_context               repo + spec               collectors -> build_context             PreGauntletResult.context_markdown
task_export                        evaluations -> models.py  extract_tasks -> call_model             .claude/tasks.json
```

## Type Contracts

```
CONTRACT                    OWNER                              CONSUMED_BY                                    NOTES
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
Concern                     gauntlet/core_types.py:74          All 7 gauntlet phases                          Stable hash-based ID
Evaluation                  gauntlet/core_types.py:90          phases 5,6,7, reporting                        Verdict: dismissed|accepted|acknowledged|deferred
Rebuttal                    gauntlet/core_types.py:102         phase 7, reporting                             sustained bool
GauntletResult              gauntlet/core_types.py:220         orchestrator, reporting, persistence            Aggregates all phase outputs
GauntletConfig              gauntlet/core_types.py:409         All phases via orchestrator                    Single source of truth for CLI params
ModelResponse               models.py:142                      debate.py, cost tracking                        agreed field only set in debate
SessionState                session.py:17                      debate.py (load/resume)                        Path traversal protection
Adversary                   adversaries.py:18                  gauntlet phases, core_types                    Frozen, content_hash() for versioning
AdversaryTemplate           adversaries.py:74                  Dynamic prompt generation                       scope_guidelines validated
BigPictureSynthesis         gauntlet/core_types.py:111         Phase 2 output                                 Informational, not authoritative
Medal                       gauntlet/core_types.py:128         medals.py, reporting                           Historical adversary scoring
FinalBossResult             gauntlet/core_types.py:195         Phase 7 output                                 PASS|REFINE|RECONSIDER
GauntletConcern             execution_planner/gauntlet_concerns.py:30  Execution plan generation             Different from gauntlet Concern
PhaseMetrics                gauntlet/core_types.py:451         Run manifest telemetry                         Per-phase timing and token counts
CheckpointMeta              gauntlet/core_types.py:440         Checkpoint file envelopes                      schema_version, spec_hash, config_hash
```

## Data Model / Access Boundaries

```
SURFACE                          KIND          OWNED_BY                 READERS/WRITERS                ACCESS
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
sessions/{id}.json               file-store    session.py               debate.py                      no lock (single-user assumption)
.adversarial-spec-gauntlet/      file-store    persistence.py           orchestrator, resume           FileLock guarded
~/.adversarial-spec/stats        file-store    medals.py                reporting, leaderboard         no lock
~/.adversarial-spec/resolved     file-store    phase_3_filtering.py     explanation matching           no lock
.claude/tasks.json               file-store    mcp_tasks/server.py      TaskManager, MCP tools         no lock (concurrent access risk)
~/.claude/.../config.json        file-store    providers.py             models.py, debate.py           read-only at runtime
```

## Hub Files

Files imported by many others (high-impact change targets):

```
FILE                              IMPORTED_BY_COUNT   EXPORTS
──────────────────────────────────────────────────────────────────────────────────────────────────────
gauntlet/core_types.py            12                  Concern, Evaluation, Rebuttal, GauntletConfig, GauntletResult, Medal, ...
models.py                         10                  call_models_parallel, call_single_model, cost_tracker, ModelResponse
adversaries.py                    9                   ADVERSARIES dict, Adversary, AdversaryTemplate, generate_concern_id
gauntlet/model_dispatch.py        7                   call_model, get_rate_limit_config, _validate_model_name
gauntlet/persistence.py           3                   save_checkpoint, load_partial_run, _write_json_atomic, _load_json_safe
providers.py                      3                   MODEL_COSTS, load_global_config, CODEX_AVAILABLE, GEMINI_CLI_AVAILABLE
prompts.py                        3                   get_system_prompt, FOCUS_AREAS, PERSONAS, PRESERVE_INTENT_PROMPT
```

## Shared Utilities

```
UTILITY                           FILE:LINE                USED_BY (count)
──────────────────────────────────────────────────────────────────────────────────────────────────────
generate_concern_id()             adversaries.py:~250      2 files (core_types, gauntlet_concerns)
normalize_verdict()               gauntlet/core_types.py:63  1 file (Evaluation.__post_init__)
cost_tracker.add()                models.py:165            4 call sites (codex, gemini, claude, litellm paths)
get_system_prompt()               prompts.py               2 files (models, debate)
_validate_model_name()            gauntlet/model_dispatch.py:39  2 files (model_dispatch, orchestrator)
_write_json_atomic()              gauntlet/persistence.py  1 file (internal to persistence)
_load_json_safe()                 gauntlet/persistence.py  1 file (internal to persistence)
resolve_adversary_name()          adversaries.py           3 files (orchestrator, phase_1, debate)
```

## External Dependencies

```
PACKAGE                 USED_FOR                     KEY_USAGE_SITES
──────────────────────────────────────────────────────────────────────────────────────────────────────
litellm                 LLM API abstraction          litellm.completion() (models.py, model_dispatch.py)
filelock                Atomic checkpoint I/O        FileLock() (gauntlet/persistence.py)
mcp                     MCP protocol server          FastMCP (mcp_tasks/server.py)
pydantic                Data models (implicit)       BaseModel (pre_gauntlet/models.py)
```

## Config Sources

```
CONFIG                         SOURCE              ACCESSED_BY
──────────────────────────────────────────────────────────────────────────────────────────────────────
LITELLM_LOG                    env var              models.py:17, debate.py:65 (set to "ERROR")
AWS_REGION                     env var (dynamic)    models.py:648 (set during Bedrock setup)
AWS_ACCESS_KEY_ID              env var              providers.py:269 (checked for Bedrock)
TELEGRAM_BOT_TOKEN             env var              telegram_bot.py:42
TELEGRAM_CHAT_ID               env var              telegram_bot.py:43
MCP_WORKING_DIR                env var              mcp_tasks/server.py:60
Bedrock config                 ~/.claude/.../config.json  providers.py, models.py, debate.py
Session state                  ~/.config/.../sessions/    session.py, debate.py
Profiles                       ~/.config/.../profiles/    debate.py (apply_profile)
```
