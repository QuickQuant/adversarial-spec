# System Overview Diagram

```
                            ┌─────────────────────────────────────────────┐
                            │              CLI Entry Points               │
                            │                                             │
                            │  debate.py          gauntlet/cli.py         │
                            │  (18 actions)       (standalone)            │
                            └──────────┬──────────────────┬───────────────┘
                                       │                  │
                          ┌────────────▼─────┐   ┌───────▼────────┐
                          │  Debate Engine   │   │   Pre-Gauntlet │
                          │                  │   │                │
                          │  run_critique()  │   │  Git/System    │
                          │  Multi-round     │   │  Collectors    │
                          │  consensus loop  │   │  Context Build │
                          └────────┬─────────┘   └───────┬────────┘
                                   │                     │
                                   │              ┌──────▼────────────────────────────────┐
                                   │              │         Gauntlet Pipeline              │
                                   │              │                                       │
                                   │              │  Phase 1: Attack Generation ──────|>   │
                                   │              │  Phase 2: Big Picture Synthesis        │
                                   │              │  Phase 3: Filtering & Clustering       │
                                   │              │  Phase 4: Frontier Evaluation          │
                                   │              │  Phase 5: Adversary Rebuttals          │
                                   │              │  Phase 6: Adjudication & Medals        │
                                   │              │  Phase 7: Final Boss Review            │
                                   │              │                                       │
                                   │              │  [Checkpoint after each phase]         │
                                   │              └───────────────┬───────────────────────┘
                                   │                              │
                          ┌────────▼──────────────────────────────▼──────┐
                          │              Models Layer                     │
                          │                                              │
                          │  call_models_parallel() ──> ThreadPoolExecutor│
                          │                                              │
                          │  ┌──────────┐  ┌───────────┐  ┌──────────┐  │
                          │  │ LiteLLM  │  │ CLI Sub-  │  │  Cost    │  │
                          │  │ (7+ APIs)│  │ process   │  │ Tracker  │  │
                          │  │          │  │ (Codex,   │  │ (Lock)   │  │
                          │  │ OpenAI   │  │  Gemini,  │  │          │  │
                          │  │ Anthropic│  │  Claude)  │  │          │  │
                          │  │ Google   │  │           │  │          │  │
                          │  │ xAI      │  │  $0 cost  │  │          │  │
                          │  │ Mistral  │  │  (subs)   │  │          │  │
                          │  └──────────┘  └───────────┘  └──────────┘  │
                          └─────────────────────────────────────────────┘
                                              │
                          ┌───────────────────▼──────────────────────────┐
                          │              Support Layer                    │
                          │                                              │
                          │  ┌───────────┐  ┌──────────┐  ┌──────────┐  │
                          │  │Adversaries│  │Providers │  │ Prompts  │  │
                          │  │ 9+ named  │  │MODEL_COSTS│  │ System   │  │
                          │  │ personas  │  │ Bedrock  │  │ prompts  │  │
                          │  │ (frozen)  │  │ CLI avail│  │ Focus    │  │
                          │  └───────────┘  └──────────┘  └──────────┘  │
                          └──────────────────────────────────────────────┘

                          ┌──────────────────────────────────────────────┐
                          │              Persistence Layer                │
                          │                                              │
                          │  Session State    Gauntlet Checkpoints        │
                          │  ~/.config/...    .adversarial-spec-gauntlet/ │
                          │  (no lock)        (FileLock + atomic write)   │
                          │                                              │
                          │  MCP Tasks        Adversary Stats/Medals      │
                          │  .claude/tasks    ~/.adversarial-spec/        │
                          │  (no lock)        (no lock)                   │
                          └──────────────────────────────────────────────┘

Legend:
  ────>  Data flow (synchronous)
  ──|>   Async/parallel flow (ThreadPoolExecutor)
  [text]  Conditional or note
```

## Key Data Paths

```
Spec (stdin) ────> debate.py ────> call_models_parallel() ────> N model responses
                       │                                              │
                       │              [consensus?] ◄──────────────────┘
                       │                  │
                       │         [yes] ──> save checkpoint ──> done
                       │         [no]  ──> next round
                       │
                       └──> gauntlet ──> Phase 1 ──|> adversary × model pairs
                                              │
                                         Phase 2-7 (sequential)
                                              │
                                         checkpoint per phase
                                              │
                                         FinalBossResult
                                         (PASS / REFINE / RECONSIDER)
```
