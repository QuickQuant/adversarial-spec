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
                    │              (debate.py:main():1493)              │
                    │                                                   │
                    │  ┌─────────┐  ┌──────────┐  ┌──────────────┐    │
                    │  │ Session │  │ Profiles │  │  Arg Router  │    │
                    │  │ Resume  │  │  Loader  │  │  (actions)   │    │
                    │  └────┬────┘  └────┬─────┘  └──────┬───────┘    │
                    │       │            │               │             │
                    │       ▼            ▼               ▼             │
                    │  ┌─────────────────────────────────────────┐    │
                    │  │         run_critique():1206             │    │
                    │  │  one round per invocation               │    │
                    │  └──────────────┬──────────────────────────┘    │
                    └─────────────────┼───────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 ▼                  │
                    │        MODELS COMPONENT            │
                    │     (call_models_parallel:901)     │
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
                    │      GAUNTLET PIPELINE (gauntlet/)     │
                    │  orchestrator.py:run_gauntlet():116    │
                    │  GauntletConfig ─> all phases          │
                    │                                        │
                    │  Phase 1: ┌─────┐┌─────┐┌─────┐      │
                    │  Attacks  │Para ││Burn ││Dist │ x9    │
                    │  (parallel)│noid ││Oncl ││Sys  │      │
                    │           └──┬──┘└──┬──┘└──┬──┘      │
                    │              └──────┼──────┘          │
                    │                     ▼                  │
                    │  Phase 2: Big Picture Synthesis        │
                    │  Phase 3: Filter + Cluster (FileLock)  │
                    │  Phase 3.5: Checkpoint ────>  disk     │
                    │  Phase 4: Multi-model Evaluation       │
                    │  Phase 5: Adversary Rebuttals          │
                    │  Phase 6: Final Adjudication           │
                    │  Phase 7: [Optional] Final Boss (Opus) │
                    │                                        │
                    │  persistence.py ─> checkpoints/manifests│
                    │  model_dispatch.py ─> validate + route  │
                    │  reporting.py ─> leaderboard + report   │
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
    │  (templates)     (MODEL_COSTS)     (9 personas)          │
    │                  (API keys)        (frozen dataclass)     │
    │                  (Bedrock)                                │
    │                                                          │
    │  core_types.py ── GauntletConfig, Concern, Evaluation,   │
    │                   GauntletResult, PhaseMetrics, Medal     │
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
x9      9 adversary personas total
Cl/au/de Claude CLI model route
```
