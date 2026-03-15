# System Overview Diagram

```
                            ┌─────────────────────────────────────┐
                            │           USER / CLAUDE CODE        │
                            │         (CLI or Skill invocation)   │
                            └──────────────┬──────────────────────┘
                                           │ spec + args
                                           ▼
                    ┌──────────────────────────────────────────────────┐
                    │                  DEBATE ENGINE                    │
                    │              (debate.py:main())                   │
                    │                                                   │
                    │  ┌─────────┐  ┌──────────┐  ┌──────────────┐    │
                    │  │ Session │  │ Profiles │  │  Arg Router  │    │
                    │  │ Resume  │  │  Loader  │  │  (18 actions)│    │
                    │  └────┬────┘  └────┬─────┘  └──────┬───────┘    │
                    │       │            │               │             │
                    │       ▼            ▼               ▼             │
                    │  ┌─────────────────────────────────────────┐    │
                    │  │         run_critique() loop              │    │
                    │  │  rounds until all models agree           │    │
                    │  └──────────────┬──────────────────────────┘    │
                    └─────────────────┼───────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 ▼                  │
                    │        MODELS COMPONENT            │
                    │     (call_models_parallel)         │
                    │                                    │
                    │   ┌──────────┬──────────┬──────┐  │
                    │   │ LiteLLM  │ Codex    │Gemini│  │
                    │   │ (API)    │ (CLI)    │(CLI) │  │
                    │   └────┬─────┴────┬─────┴──┬───┘  │
                    │        │          │        │      │
                    └────────┼──────────┼────────┼──────┘
                             │          │        │
                    ┌────────▼──────────▼────────▼──────┐
                    │        EXTERNAL LLM PROVIDERS      │
                    │  OpenAI  Anthropic  Google  Groq   │
                    │  Mistral  xAI  Bedrock             │
                    └───────────────────────────────────┘

                    ═══════════════════════════════════════
                    After consensus reached:
                    ═══════════════════════════════════════

                    ┌───────────────────────────────────────┐
                    │            GAUNTLET ENGINE             │
                    │          (gauntlet.py)                 │
                    │                                        │
                    │  Phase 1: ┌─────┐┌─────┐┌─────┐      │
                    │  Concerns │Para ││Burn ││Dist │ ...   │
                    │  (parallel)│noid ││Oncl ││Sys  │      │
                    │           └──┬──┘└──┬──┘└──┬──┘      │
                    │              └──────┼──────┘          │
                    │                     ▼                  │
                    │  Phase 2: Filter duplicates            │
                    │  Phase 3: Frontier model evaluates     │
                    │  Phase 4: Adversary rebuttals          │
                    │  Phase 5: Big Picture Synthesis        │
                    │  Phase 6: Medal Awards                 │
                    └──────────────┬────────────────────────┘
                                   │
                                   ▼
                    ┌───────────────────────────────────────┐
                    │        EXECUTION PLANNER               │
                    │   (guidelines-based, via Claude)       │
                    │                                        │
                    │   spec + concerns ──> task DAG         │
                    │   (gauntlet_concerns.py links          │
                    │    concerns to implementation tasks)   │
                    └───────────────────────────────────────┘

    ════════════════════════════════════════════════════════════
    Supporting Infrastructure:
    ════════════════════════════════════════════════════════════

    ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
    │ Session  │   │ Telegram │   │MCP Tasks │   │Pre-Gaunt │
    │ Manager  │   │   Bot    │   │  Server  │   │  let     │
    │          │   │          │   │          │   │          │
    │sessions/ │   │ HTTP API │   │tasks.json│   │collectors│
    │*.json    │   │ polling  │   │ FastMCP  │   │extractors│
    └──────────┘   └──────────┘   └──────────┘   └──────────┘

    ┌──────────────────────────────────────────────────────────┐
    │                    SHARED DATA LAYER                      │
    │                                                          │
    │  prompts.py ──── providers.py ──── adversaries.py        │
    │  (templates)     (MODEL_COSTS)     (persona defs)        │
    │                  (API keys)                               │
    └──────────────────────────────────────────────────────────┘
```

## Legend

```
──>     synchronous data flow
═══     phase boundary
[ ]     optional component
Para    ParanoidSecurity adversary
Burn    BurnedOncall adversary
Dist    DistributedSystemsNerd adversary
```
