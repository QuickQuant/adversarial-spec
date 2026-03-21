# Cross References

> Call graphs, data paths, and dependency lookups.
> Generated: 2026-03-18 | Git: 0eb7ad9

## Function Call Graph

### Debate Engine

```
main() (scripts/debate.py:1443)
  ├── calls: create_parser(), handle_info_command(), handle_utility_command(),
  │          handle_execution_plan(), handle_gauntlet(), apply_profile(),
  │          parse_models(), setup_bedrock(), validate_models_before_run(),
  │          load_or_resume_session(), run_critique()
  ├── called_by: CLI invocation (__name__:1484)
  └── async: no

handle_info_command() (scripts/debate.py:610)
  ├── calls: list_providers(), list_focus_areas(), list_personas(), list_profiles(),
  │          SessionState.list_sessions(), get_adversary_leaderboard(), get_medal_leaderboard(),
  │          print_version_manifest()
  ├── called_by: main()
  └── async: no

handle_utility_command() (scripts/debate.py:682)
  ├── calls: handle_bedrock_command(), save_profile()
  ├── called_by: main()
  └── async: no

handle_gauntlet() (scripts/debate.py:989)
  ├── calls: run_gauntlet(), format_gauntlet_report()
  ├── called_by: main()
  └── async: no

run_critique() (scripts/debate.py:1156)
  ├── calls: log_input_stats(), get_task_manager(), call_models_parallel(),
  │          generate_diff(), get_critique_summary(), send_telegram_notification(),
  │          save_checkpoint(), save_critique_responses(), SessionState.save(),
  │          output_results()
  ├── called_by: main()
  └── async: no
```

### Models

```
call_models_parallel() (scripts/models.py:894)
  ├── calls: ThreadPoolExecutor, call_single_model() (per model, max_workers=len(models))
  ├── called_by: run_critique(), gauntlet phases
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

### Gauntlet

```
run_gauntlet() (scripts/gauntlet.py:3290)
  ├── calls: generate_attacks() (ThreadPoolExecutor, max_workers=5),
  │          generate_big_picture_synthesis(), filter_concerns_with_explanations(),
  │          cluster_concerns_with_provenance(), evaluate_concerns_multi_model(),
  │          format_gauntlet_report(), _track_dedup_stats()
  ├── called_by: handle_gauntlet() (debate.py), gauntlet.py:main()
  └── async: no (thread-parallel per phase)

evaluate_concerns_multi_model() (scripts/gauntlet.py:2172)
  ├── calls: ThreadPoolExecutor per model, litellm.completion(), normalize_verdict()
  ├── called_by: run_gauntlet()
  └── async: no (thread-parallel, batched 15 concerns, wave-based concurrency)
```

### Pre-Gauntlet

```
PreGauntletOrchestrator.run() (scripts/pre_gauntlet/orchestrator.py:51)
  ├── calls: extract_spec_affected_files(), GitPositionCollector.collect(),
  │          SystemStateCollector.collect(), build_context(), run_alignment_mode()
  ├── called_by: debate.py, gauntlet.py
  └── async: no

GitPositionCollector.collect() (scripts/collectors/git_position.py)
  ├── calls: GitCli.current_branch(), GitCli.diff_stat(), GitCli.log()
  ├── called_by: PreGauntletOrchestrator.run()
  └── async: no

SystemStateCollector.collect() (scripts/collectors/system_state.py)
  ├── calls: ProcessRunner.run(), file reads
  ├── called_by: PreGauntletOrchestrator.run()
  └── async: no
```

## Data Path Summary

```
DATA_PATH               SOURCE                    TRANSFORMS                              SINK
──────────────────────────────────────────────────────────────────────────────────────────────────────────
spec_critique           stdin/file                prompt_build → model_call → agree_check  stdout JSON + session file
gauntlet_review         stdin spec                adversary_gen → filter → cluster → eval  gauntlet JSON files + stdout
cost_tracking           model responses           token_count → rate_lookup → accumulate   stdout summary
telegram_notify         round results             format → split_chunks → api_call         Telegram HTTP API
session_persist         round completion          serialize → validate_path → write         sessions/*.json
checkpoint_save         round completion          spec → markdown + critiques → JSON       checkpoints/round-N.*
config_load             env vars + files          env_read → profile_merge → validate      in-memory config
pre_gauntlet_ctx        git + system state        collect → build_context → align          context markdown
```

## Hub Files

Files imported by many others (high-impact change targets):

```
FILE                              IMPORTED_BY_COUNT   EXPORTS
──────────────────────────────────────────────────────────────────────────────────
scripts/prompts.py                5+                  FOCUS_AREAS, PERSONAS, get_system_prompt(), REVIEW_PROMPT_TEMPLATE,
                                                      PRESS_PROMPT_TEMPLATE, EXPORT_TASKS_PROMPT, get_doc_type_name(),
                                                      PRESERVE_INTENT_PROMPT
scripts/providers.py              3+                  MODEL_COSTS, validate_model_credentials(), load_profile(),
                                                      save_profile(), list_providers(), list_focus_areas(), list_personas(),
                                                      list_profiles(), handle_bedrock_command(), DEFAULT_CODEX_REASONING
scripts/models.py                 3+                  ModelResponse, call_models_parallel(), cost_tracker, extract_tasks(),
                                                      generate_diff(), get_critique_summary(), is_o_series_model(),
                                                      load_context_files(), detect_agreement(), extract_spec()
scripts/adversaries.py            3+                  Adversary, ADVERSARIES, FINAL_BOSS, PRE_GAUNTLET, PARANOID_SECURITY,
                                                      BURNED_ONCALL, generate_concern_id(), ADVERSARY_PREFIXES
pre_gauntlet/models.py            5+                  CompatibilityConfig, PreGauntletResult, PreGauntletStatus,
                                                      DocType, ContextSummary
```

## Shared Utilities

```
UTILITY                           FILE:LINE                              USED_BY (count)
──────────────────────────────────────────────────────────────────────────────────────────
get_system_prompt()               scripts/prompts.py:125                 2+ (models, debate)
validate_model_credentials()      scripts/providers.py:436               2+ (debate, providers)
cost_tracker.add()                scripts/models.py:163                  3+ (call_single_model routes, gauntlet)
generate_concern_id()             scripts/adversaries.py                 2+ (gauntlet, gauntlet_concerns)
build_context()                   scripts/pre_gauntlet/context_builder   2+ (orchestrator, tests)
get_tasks_file()                  scripts/task_manager.py                2+ (TaskManager, MCP server)
load_context_files()              scripts/models.py:207                  2+ (debate, models)
```

## External Dependencies

```
PACKAGE                 USED_FOR                                    KEY_USAGE_SITES
──────────────────────────────────────────────────────────────────────────────────────────
litellm                 Universal LLM API wrapper                   models.py (completion()), gauntlet.py
mcp (fastmcp)           MCP server framework                        mcp_tasks/server.py (FastMCP)
pydantic                Data validation (pre-gauntlet models)       pre_gauntlet/models.py (BaseModel)
concurrent.futures      Parallel model calls                        models.py (ThreadPoolExecutor), gauntlet.py
subprocess              CLI tool invocation (Codex, Gemini, Claude) models.py, integrations/git_cli.py, process_runner.py
argparse                CLI argument parsing                        debate.py, gauntlet.py, telegram_bot.py
urllib                  Telegram Bot API HTTP calls                 telegram_bot.py (urlopen, Request)
hashlib                 Spec hashing, concern IDs                   debate.py, adversaries.py, gauntlet.py
pytest                  Test framework                              tests/*.py
ruff                    Linting                                     pyproject.toml
```

## Config Sources

```
CONFIG                          SOURCE              ACCESSED_BY
──────────────────────────────────────────────────────────────────────────────────
OPENAI_API_KEY                  env var             providers.py, gauntlet.py
ANTHROPIC_API_KEY               env var             providers.py, gauntlet.py
GEMINI_API_KEY                  env var             providers.py, gauntlet.py
XAI_API_KEY                     env var             providers.py
GROQ_API_KEY                    env var             providers.py, gauntlet.py
DEEPSEEK_API_KEY                env var             gauntlet.py
MISTRAL_API_KEY                 env var             providers.py
TELEGRAM_BOT_TOKEN              env var             telegram_bot.py
TELEGRAM_CHAT_ID                env var             telegram_bot.py
MCP_WORKING_DIR                 env var             task_manager.py, mcp_tasks/server.py
LITELLM_LOG                     env var (set)       debate.py:65, models.py:16 (hardcoded to "ERROR")
AWS_REGION/PROFILE/ROLE_ARN     env vars            providers.py (Bedrock config)
CLAUDE_CODE, CC_WORKSPACE       env var             gauntlet.py (environment detection)
GEMINI_PAID_TIER, CLAUDE_PAID_TIER env var          gauntlet.py (pricing detection)
~/.claude/adv-spec/config.json  file                providers.py (global Bedrock config)
~/.config/adv-spec/profiles/    directory           providers.py (saved profiles)
~/.config/adv-spec/sessions/    directory           session.py (session persistence)
~/.cache/adv-spec/knowledge/    directory           integrations/knowledge_service.py (cache)
.claude/tasks.json              file                task_manager.py, mcp_tasks/server.py
```
