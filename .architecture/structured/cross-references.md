# Cross References

> Call graphs, data paths, and dependency lookups.
> Generated: 2026-02-06T20:35:00Z | Git: e94ebfe

## Function Call Graph

### Debate Engine

```
main() (scripts/debate.py:1933)
  ├── calls: create_parser(), handle_info_command(), handle_utility_command(),
  │          handle_execution_plan(), handle_gauntlet(), apply_profile(),
  │          parse_models(), setup_bedrock(), validate_models_before_run(),
  │          load_or_resume_session(), run_critique()
  ├── called_by: CLI invocation
  └── async: no

handle_info_command() (scripts/debate.py:607)
  ├── calls: list_providers(), list_focus_areas(), list_personas(), list_profiles(),
  │          SessionState.list_sessions(), get_adversary_leaderboard(), get_medal_leaderboard()
  ├── called_by: main()
  └── async: no

handle_utility_command() (scripts/debate.py:675)
  ├── calls: handle_bedrock_command(), save_profile(), generate_diff()
  ├── called_by: main()
  └── async: no

handle_execution_plan() (scripts/debate.py:724)
  ├── calls: SpecIntake.parse(), ScopeAssessor.assess(), TaskPlanner.generate_from_tech_spec(),
  │          TaskPlanner.auto_generate(), TestStrategyManager.assign_strategies(),
  │          OverDecompositionGuard.check(), ParallelizationAdvisor.analyze(), get_task_manager()
  ├── called_by: main()
  └── async: no

handle_gauntlet() (scripts/debate.py:1553)
  ├── calls: run_gauntlet(), format_gauntlet_report()
  ├── called_by: main()
  └── async: no

run_critique() (scripts/debate.py:1689)
  ├── calls: get_task_manager(), _create_round_task(), call_models_parallel(),
  │          send_telegram_notification(), save_checkpoint(), SessionState.save(),
  │          _complete_round_task(), output_results()
  ├── called_by: main()
  └── async: no
```

### Models

```
call_models_parallel() (scripts/models.py)
  ├── calls: ThreadPoolExecutor, call_single_model() (per model)
  ├── called_by: run_critique()
  └── async: no (thread-parallel)

call_single_model() (scripts/models.py:470)
  ├── calls: call_codex_model(), call_gemini_cli_model(), litellm.completion(),
  │          cost_tracker.add()
  ├── called_by: call_models_parallel()
  └── async: no

call_codex_model() (scripts/models.py)
  ├── calls: subprocess.run("codex exec --json")
  ├── called_by: call_single_model()
  └── async: no (subprocess blocks)

call_gemini_cli_model() (scripts/models.py)
  ├── calls: subprocess.run("gemini -m")
  ├── called_by: call_single_model()
  └── async: no (subprocess blocks)
```

### Gauntlet

```
run_gauntlet() (scripts/gauntlet.py)
  ├── calls: ThreadPoolExecutor (adversary calls), litellm.completion() (evaluation),
  │          format_gauntlet_report(), generate_medal_report()
  ├── called_by: handle_gauntlet(), gauntlet.py:main()
  └── async: no (thread-parallel for adversaries)
```

### Pre-Gauntlet

```
PreGauntletOrchestrator.run() (scripts/pre_gauntlet/orchestrator.py:51)
  ├── calls: GitPositionCollector.collect(), SystemStateCollector.collect(),
  │          extract_spec_affected_files(), build_context(), run_alignment_mode()
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
gauntlet_review         stdin spec                adversary_gen → filter → eval → rebuttal gauntlet JSON report
execution_plan          spec + concerns           intake → scope → tasks → tests → parallel stdout JSON/markdown
cost_tracking           model responses           token_count → rate_lookup → accumulate   stdout summary
telegram_notify         round results             format → split_chunks → api_call         Telegram HTTP API
session_persist         round completion          serialize → validate_path → write         sessions/*.json
checkpoint_save         round completion          spec → markdown                          checkpoints/round-N.md
config_load             env vars + files          env_read → profile_merge → validate      in-memory config
```

## Hub Files

Files imported by many others (high-impact change targets):

```
FILE                              IMPORTED_BY_COUNT   EXPORTS
──────────────────────────────────────────────────────────────────────────────────
scripts/prompts.py                4+                  FOCUS_AREAS, PERSONAS, get_system_prompt(), REVIEW_PROMPT_TEMPLATE,
                                                      EXPORT_TASKS_PROMPT, get_doc_type_name(), PRESERVE_INTENT_PROMPT
scripts/providers.py              4+                  MODEL_COSTS, validate_model_credentials(), load_profile(),
                                                      save_profile(), list_providers(), list_focus_areas(), list_personas(),
                                                      list_profiles(), get_default_model(), handle_bedrock_command(),
                                                      DEFAULT_CODEX_REASONING
scripts/models.py                 3+                  ModelResponse, call_models_parallel(), cost_tracker, extract_tasks(),
                                                      generate_diff(), get_critique_summary(), is_o_series_model(),
                                                      load_context_files()
scripts/adversaries.py            3+                  ADVERSARIES, FINAL_BOSS, generate_concern_id(), ADVERSARY_PREFIXES
scripts/session.py                2+                  SessionState, SESSIONS_DIR, save_checkpoint()
execution_planner/__init__.py     2+                  SpecIntake, ScopeAssessor, TaskPlanner, TestStrategyManager,
                                                      OverDecompositionGuard, ParallelizationAdvisor,
                                                      GauntletConcernParser, load_concerns_for_spec (30+ total re-exports)
pre_gauntlet/models.py            4+                  CompatibilityConfig, PreGauntletResult, PreGauntletStatus,
                                                      DocType, Timings, ContextSummary, DiscoverySummary
```

## Shared Utilities

```
UTILITY                           FILE:LINE                              USED_BY (count)
──────────────────────────────────────────────────────────────────────────────────────────
get_system_prompt()               scripts/prompts.py                     2+ (models, debate)
validate_model_credentials()      scripts/providers.py                   2+ (debate, providers)
cost_tracker.add()                scripts/models.py:101                  3+ (call_single_model, codex, gemini)
generate_concern_id()             scripts/adversaries.py                 2+ (gauntlet, gauntlet_concerns)
build_context()                   scripts/pre_gauntlet/context_builder   2+ (orchestrator, tests)
get_tasks_file()                  scripts/task_manager.py:51             2+ (TaskManager, MCP server)
```

## External Dependencies

```
PACKAGE                 USED_FOR                                    KEY_USAGE_SITES
──────────────────────────────────────────────────────────────────────────────────────────
litellm                 Universal LLM API wrapper                   models.py:20 (completion()), gauntlet.py
mcp (fastmcp)           MCP server framework                        mcp_tasks/server.py:15 (FastMCP)
pydantic                Data validation (pre-gauntlet models)       pre_gauntlet/models.py:12 (BaseModel)
concurrent.futures      Parallel model calls                        models.py:5 (ThreadPoolExecutor)
subprocess              CLI tool invocation (Codex, Gemini, git)    models.py:9, integrations/git_cli.py
argparse                CLI argument parsing                        debate.py:51, gauntlet.py, telegram_bot.py
urllib                  Telegram Bot API HTTP calls                 telegram_bot.py:30 (urlopen, Request)
pytest                  Test framework                              scripts/tests/*.py
ruff                    Linting                                     pyproject.toml
```

## Config Sources

```
CONFIG                          SOURCE              ACCESSED_BY
──────────────────────────────────────────────────────────────────────────────────
OPENAI_API_KEY                  env var             providers.py (validate_model_credentials)
ANTHROPIC_API_KEY               env var             providers.py (validate_model_credentials)
GEMINI_API_KEY                  env var             providers.py (validate_model_credentials)
GROQ_API_KEY                    env var             providers.py (validate_model_credentials)
DEEPSEEK_API_KEY                env var             providers.py (validate_model_credentials)
TELEGRAM_BOT_TOKEN              env var             telegram_bot.py:42 (get_config)
TELEGRAM_CHAT_ID                env var             telegram_bot.py:43 (get_config)
MCP_WORKING_DIR                 env var             task_manager.py:47 (get_working_dir)
LITELLM_LOG                     env var (set)       models.py:16 (hardcoded to "ERROR")
CLAUDE_PAID_TIER                env var             providers.py (cost estimation)
AWS_REGION/PROFILE/ROLE_ARN     env vars            providers.py (Bedrock config)
~/.claude/adv-spec/config.json  file                providers.py:15 (global Bedrock config)
~/.config/adv-spec/profiles/    directory           providers.py:14 (saved profiles)
~/.config/adv-spec/sessions/    directory           session.py:12 (session persistence)
.claude/settings.local.json     file                Claude Code (hook registrations)
.adversarial-spec/session-state file                SKILL.md (active session pointer)
```
