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
                    │              (debate.py:main():1443)              │
                    │                                                   │
                    │  ┌─────────┐  ┌──────────┐  ┌──────────────┐    │
                    │  │ Session │  │ Profiles │  │  Arg Router  │    │
                    │  │ Resume  │  │  Loader  │  │  (actions)   │    │
                    │  └────┬────┘  └────┬─────┘  └──────┬───────┘    │
                    │       │            │               │             │
                    │       ▼            ▼               ▼             │
                    │  ┌─────────────────────────────────────────┐    │
                    │  │         run_critique():1156             │    │
                    │  │  one round per invocation               │    │
                    │  └──────────────┬──────────────────────────┘    │
                    └─────────────────┼───────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 ▼                  │
                    │        MODELS COMPONENT            │
                    │     (call_models_parallel:894)     │
                    │                                    │
                    │   ┌────────┬────────┬────────┬──┐ │
                    │   │LiteLLM│ Codex  │Gemini  │Cl│ │
                    │   │ (API) │ (CLI)  │ (CLI)  │au│ │
                    │   │       │        │        │de│ │
                    │   └───┬───┴───┬────┴───┬────┴──┘ │
                    │       │       │        │          │
                    └───────┼───────┼────────┼──────────┘
                            │       │        │
                    ┌───────▼───────▼────────▼──────────┐
                    │        EXTERNAL LLM PROVIDERS      │
                    │  OpenAI  Anthropic  Google  Groq   │
                    │  Mistral  xAI  Bedrock             │
                    └───────────────────────────────────┘

                    ═══════════════════════════════════════
                    After consensus (or directly via CLI):
                    ═══════════════════════════════════════

                    ┌───────────────────────────────────────┐
                    │            GAUNTLET ENGINE             │
                    │        (gauntlet.py:run_gauntlet:3290) │
                    │                                        │
                    │  Phase 1: ┌─────┐┌─────┐┌─────┐      │
                    │  Concerns │Para ││Burn ││Dist │ ...   │
                    │  (parallel)│noid ││Oncl ││Sys  │      │
                    │           └──┬──┘└──┬──┘└──┬──┘      │
                    │              └──────┼──────┘          │
                    │                     ▼                  │
                    │  Phase 2: Big Picture Synthesis        │
                    │  Phase 3: Filter + Cluster             │
                    │  Phase 4: Multi-model Evaluation       │
                    │  Phase 5: Adversary Rebuttals          │
                    │  Phase 6: Final Adjudication           │
                    │  Phase 7: [Optional] Final Boss (Opus) │
                    └──────────────┬────────────────────────┘
                                   │
                                   ▼
                    ┌───────────────────────────────────────┐
                    │        EXECUTION PLANNING              │
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
    │                  (Bedrock)                                │
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
Cl/au/de Claude CLI model route
```
