# Cross References

> Call graphs, data paths, and dependency lookups.
> Generated: 2026-03-21 | Git: 12c5d3f

## Function Call Graph

### Debate Engine

```
main() (scripts/debate.py:1493)
  ├── calls: create_parser(), handle_info_command(), handle_utility_command(),
  │          handle_execution_plan(), handle_gauntlet(), apply_profile(),
  │          parse_models(), setup_bedrock(), validate_models_before_run(),
  │          load_or_resume_session(), run_critique()
  ├── called_by: CLI invocation (__name__)
  └── async: no

handle_info_command() (scripts/debate.py:610)
  ├── calls: list_providers(), list_focus_areas(), list_personas(), list_profiles(),
  │          SessionState.list_sessions(), get_adversary_leaderboard(), get_medal_leaderboard(),
  │          print_version_manifest()
  ├── called_by: main()
  └── async: no

handle_gauntlet() (scripts/debate.py:989)
  ├── calls: run_gauntlet(), format_gauntlet_report(), load_run_manifest(), format_run_manifest()
  ├── called_by: main()
  └── async: no
  NOTES: Handles --show-manifest [HASH] before gauntlet run.
         Maps --codex-reasoning -> attack_codex_reasoning in run_gauntlet() call.

run_critique() (scripts/debate.py:1206)
  ├── calls: log_input_stats(), get_task_manager(), call_models_parallel(),
  │          generate_diff(), get_critique_summary(), send_telegram_notification(),
  │          save_checkpoint(), save_critique_responses(), SessionState.save(),
  │          output_results()
  ├── called_by: main()
  └── async: no
```

### Models

```
call_models_parallel() (scripts/models.py:901)
  ├── calls: ThreadPoolExecutor, call_single_model() (per model, max_workers=len(models))
  ├── called_by: run_critique(), gauntlet phase modules
  └── async: no (thread-parallel)

call_single_model() (scripts/models.py:619)
  ├── calls: call_codex_model(), call_gemini_cli_model(), call_claude_cli_model(),
  │          litellm.completion(), cost_tracker.add(), detect_agreement(), extract_spec()
  ├── called_by: call_models_parallel()
  └── async: no

call_codex_model() (scripts/models.py:351)
  ├── calls: subprocess.run("codex exec --json --full-auto"), parse JSONL events
  ├── called_by: call_single_model()
  └── async: no (subprocess blocks)

call_gemini_cli_model() (scripts/models.py:451)
  ├── calls: subprocess.run("gemini -m <model> -y"), filter noise prefixes
  ├── called_by: call_single_model()
  └── async: no (subprocess blocks)

call_claude_cli_model() (scripts/models.py:536)
  ├── calls: subprocess.run("claude -p --json-out"), parse JSON formats
  ├── called_by: call_single_model()
  └── async: no (subprocess blocks)
```

### Gauntlet Package

```
run_gauntlet() (scripts/gauntlet/orchestrator.py:116)
  ├── calls: GauntletConfig(), _validate_model_name(), select_adversary_model(),
  │          select_eval_model(), get_spec_hash(), get_config_hash(),
  │          generate_attacks(), generate_big_picture_synthesis(),
  │          filter_concerns_with_explanations(), cluster_concerns_with_provenance(),
  │          evaluate_concerns_multi_model(), run_rebuttals(), final_adjudication(),
  │          run_final_boss_review(), save_gauntlet_run(), update_adversary_stats(),
  │          calculate_medals(), save_medal_reports(), update_run_manifest(),
  │          _build_phase_metrics(), _start_phase_capture()
  ├── called_by: handle_gauntlet() (debate.py), gauntlet/cli.py:main()
  └── async: no (thread-parallel per phase)

generate_attacks() (scripts/gauntlet/phase_1_attacks.py)
  ├── calls: ThreadPoolExecutor, _call_gauntlet_model() via model_dispatch,
  │          config.timeout, config.attack_codex_reasoning
  ├── called_by: run_gauntlet()
  └── async: no (thread-parallel per adversary)

generate_big_picture_synthesis() (scripts/gauntlet/phase_2_synthesis.py)
  ├── calls: _call_gauntlet_model(), config.eval_codex_reasoning, config.timeout
  ├── called_by: run_gauntlet()
  └── async: no

cluster_concerns_with_provenance() (scripts/gauntlet/phase_3_filtering.py)
  ├── calls: _call_gauntlet_model(), choose_clustering_model(),
  │          save_partial_clustering(), config.timeout
  ├── called_by: run_gauntlet()
  └── async: no
  NOTES: Raises GauntletClusteringError on failure (no silent fallback)

evaluate_concerns_multi_model() (scripts/gauntlet/phase_4_evaluation.py)
  ├── calls: ThreadPoolExecutor per model, _call_gauntlet_model(),
  │          normalize_verdict(), config.eval_codex_reasoning, config.timeout
  ├── called_by: run_gauntlet()
  └── async: no (thread-parallel, batched 15 concerns, wave-based)

run_rebuttals() (scripts/gauntlet/phase_5_rebuttals.py)
  ├── calls: ThreadPoolExecutor, _call_gauntlet_model(),
  │          config.attack_codex_reasoning, config.timeout
  ├── called_by: run_gauntlet()
  └── async: no (thread-parallel per batch)

final_adjudication() (scripts/gauntlet/phase_6_adjudication.py)
  ├── calls: _call_gauntlet_model(), config.eval_codex_reasoning, config.timeout
  ├── called_by: run_gauntlet()
  └── async: no

run_final_boss_review() (scripts/gauntlet/phase_7_final_boss.py)
  ├── calls: litellm.completion() (always Opus 4.6), FinalBossVerdict
  ├── called_by: run_gauntlet() [conditional]
  └── async: no
```

### Gauntlet Persistence

```
save_checkpoint() (scripts/gauntlet/persistence.py)
  ├── calls: FileLock, json.dump, atomic write via tempfile
  ├── called_by: run_gauntlet() after each phase
  └── async: no

load_partial_run() (scripts/gauntlet/persistence.py)
  ├── calls: FileLock, json.load, verify schema_version + config_hash
  ├── called_by: run_gauntlet() when resume=True
  └── async: no

update_run_manifest() (scripts/gauntlet/persistence.py)
  ├── calls: FileLock, json.load/dump
  ├── called_by: run_gauntlet() after each phase
  └── async: no

load_run_manifest() (scripts/gauntlet/persistence.py)
  ├── calls: glob for manifest files, optional hash prefix match
  ├── called_by: handle_gauntlet() in debate.py (--show-manifest)
  └── async: no
```

### Pre-Gauntlet

```
PreGauntletOrchestrator.run() (scripts/pre_gauntlet/orchestrator.py:51)
  ├── calls: extract_spec_affected_files(), GitPositionCollector.collect(),
  │          SystemStateCollector.collect(), build_context(), run_alignment_mode()
  ├── called_by: debate.py, gauntlet/cli.py
  └── async: no

GitPositionCollector.collect() (scripts/collectors/git_position.py)
  ├── calls: GitCli.current_branch(), GitCli.diff_stat(), GitCli.log()
  ├── called_by: PreGauntletOrchestrator.run()
  └── async: no
```

## Data Path Summary

```
DATA_PATH               SOURCE                    TRANSFORMS                              SINK
──────────────────────────────────────────────────────────────────────────────────────────────────────────
spec_critique           stdin/file                prompt_build -> model_call -> agree_check stdout JSON + session file
gauntlet_review         stdin spec                attack -> synth -> filter -> cluster ->  gauntlet JSON + manifest + stdout
                                                  eval -> rebuttal -> adjudicate -> boss
cost_tracking           model responses           token_count -> rate_lookup -> accumulate stdout summary + PhaseMetrics
gauntlet_checkpoint     phase completion           serialize -> FileLock -> atomic write    .adversarial-spec-gauntlet/*.json
gauntlet_manifest       phase metrics             PhaseMetrics -> update_run_manifest()    run-manifest-{hash}-{ts}.json
telegram_notify         round results             format -> split_chunks -> api_call       Telegram HTTP API
session_persist         round completion          serialize -> validate_path -> write       sessions/*.json
checkpoint_save         round completion          spec -> markdown + critiques -> JSON      checkpoints/round-N.*
config_load             env vars + files          env_read -> profile_merge -> validate     in-memory config
pre_gauntlet_ctx        git + system state        collect -> build_context -> align         context markdown
medal_awards            gauntlet run              calculate_medals -> save_medal_reports   ~/.adversarial-spec/medals/
adversary_stats         gauntlet run              update_adversary_stats -> FileLock        ~/.adversarial-spec/adversary_stats.json
```

## Hub Files

Files imported by many others (high-impact change targets):

```
FILE                              IMPORTED_BY_COUNT   EXPORTS
──────────────────────────────────────────────────────────────────────────────────
scripts/adversaries.py            9+                  Adversary, ADVERSARIES, FINAL_BOSS, PRE_GAUNTLET, PARANOID_SECURITY,
                                                      BURNED_ONCALL, generate_concern_id(), ADVERSARY_PREFIXES
scripts/models.py                 8+                  ModelResponse, call_models_parallel(), cost_tracker, extract_tasks(),
                                                      generate_diff(), get_critique_summary(), is_o_series_model(),
                                                      load_context_files(), call_codex_model(), call_gemini_cli_model(),
                                                      call_claude_cli_model()
scripts/providers.py              5+                  MODEL_COSTS, validate_model_credentials(), load_profile(),
                                                      CODEX_AVAILABLE, GEMINI_CLI_AVAILABLE, CLAUDE_CLI_AVAILABLE,
                                                      DEFAULT_CODEX_REASONING, DEFAULT_COST
scripts/prompts.py                5+                  FOCUS_AREAS, PERSONAS, get_system_prompt(), REVIEW_PROMPT_TEMPLATE,
                                                      PRESS_PROMPT_TEMPLATE, EXPORT_TASKS_PROMPT, get_doc_type_name(),
                                                      PRESERVE_INTENT_PROMPT
scripts/gauntlet/core_types.py    8+                  GauntletConfig, GauntletResult, Concern, Evaluation, Rebuttal,
                                                      BigPictureSynthesis, Medal, FinalBossResult, FinalBossVerdict,
                                                      PhaseMetrics, CheckpointMeta, GauntletClusteringError,
                                                      normalize_verdict()
pre_gauntlet/models.py            5+                  CompatibilityConfig, PreGauntletResult, PreGauntletStatus,
                                                      DocType, ContextSummary
```

## Shared Utilities

```
UTILITY                           FILE:LINE                              USED_BY (count)
──────────────────────────────────────────────────────────────────────────────────────────
get_system_prompt()               scripts/prompts.py                     2+ (models, debate)
validate_model_credentials()      scripts/providers.py                   2+ (debate, providers)
cost_tracker.add()                scripts/models.py:204                  8+ (call_single_model, all gauntlet phases)
generate_concern_id()             scripts/adversaries.py                 2+ (gauntlet core_types, gauntlet_concerns)
_validate_model_name()            scripts/gauntlet/model_dispatch.py     2+ (orchestrator, cli)
normalize_verdict()               scripts/gauntlet/core_types.py         3+ (phase_4, phase_6, persistence)
get_spec_hash()                   scripts/gauntlet/persistence.py        2+ (orchestrator, phases)
get_config_hash()                 scripts/gauntlet/persistence.py        2+ (orchestrator, persistence)
load_context_files()              scripts/models.py                      2+ (debate, models)
```

## External Dependencies

```
PACKAGE                 USED_FOR                                    KEY_USAGE_SITES
──────────────────────────────────────────────────────────────────────────────────────────
litellm                 Universal LLM API wrapper                   models.py, gauntlet/model_dispatch.py, gauntlet/phase_7_final_boss.py
filelock                Atomic file writes for checkpoints          gauntlet/persistence.py (FileLock)
mcp (fastmcp)           MCP server framework                        mcp_tasks/server.py (FastMCP)
concurrent.futures      Parallel model calls                        models.py, gauntlet/phase_1_attacks.py, phase_4, phase_5
subprocess              CLI tool invocation (Codex, Gemini, Claude) models.py, integrations/git_cli.py, process_runner.py
argparse                CLI argument parsing                        debate.py, gauntlet/cli.py, telegram_bot.py
urllib                  Telegram Bot API HTTP calls                 telegram_bot.py (urlopen, Request)
hashlib                 Spec hashing, concern IDs, config hashing   debate.py, adversaries.py, gauntlet/persistence.py
pytest                  Test framework                              scripts/tests/*.py
ruff                    Linting                                     pyproject.toml
```

## Config Sources

```
CONFIG                          SOURCE              ACCESSED_BY
──────────────────────────────────────────────────────────────────────────────────
OPENAI_API_KEY                  env var             providers.py
ANTHROPIC_API_KEY               env var             providers.py, gauntlet/model_dispatch.py, gauntlet/phase_7_final_boss.py
GEMINI_API_KEY                  env var             providers.py, gauntlet/model_dispatch.py
XAI_API_KEY                     env var             providers.py
GROQ_API_KEY                    env var             providers.py, gauntlet/model_dispatch.py
DEEPSEEK_API_KEY                env var             providers.py, gauntlet/model_dispatch.py
MISTRAL_API_KEY                 env var             providers.py
TELEGRAM_BOT_TOKEN              env var             telegram_bot.py
TELEGRAM_CHAT_ID                env var             telegram_bot.py
MCP_WORKING_DIR                 env var             task_manager.py, mcp_tasks/server.py
LITELLM_LOG                     env var (set)       debate.py:65, models.py:16 (hardcoded to "ERROR")
AWS_REGION/PROFILE/ROLE_ARN     env vars            providers.py (Bedrock config)
CLAUDE_CODE, CC_WORKSPACE       env var             gauntlet/model_dispatch.py (environment detection)
GEMINI_PAID_TIER, CLAUDE_PAID_TIER env var          gauntlet/model_dispatch.py (pricing detection)
~/.claude/adv-spec/config.json  file                providers.py (global Bedrock config)
~/.config/adv-spec/profiles/    directory           providers.py (saved profiles)
~/.config/adv-spec/sessions/    directory           session.py (session persistence)
~/.cache/adv-spec/knowledge/    directory           integrations/knowledge_service.py (cache)
.claude/tasks.json              file                task_manager.py, mcp_tasks/server.py
```
