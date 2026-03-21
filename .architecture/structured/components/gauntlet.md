# Component: Gauntlet

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | 7-phase adversarial stress-testing of specs with named attacker personas |
| Entry | `run_gauntlet()` at scripts/gauntlet.py:3290 |
| Key files | gauntlet.py (~4087 lines), adversaries.py |
| Depends on | Models (litellm), Adversaries, Providers |
| Used by | Debate Engine (handle_gauntlet), standalone CLI |

## What This Component Does

The gauntlet subjects a spec to attack from multiple adversary personas, each probing from a different angle (security, operations, distributed systems, UX, business logic). A 7-phase pipeline generates concerns, synthesizes patterns, filters/clusters duplicates, evaluates with multi-model consensus, processes rebuttals for dismissed concerns, adjudicates sustained rebuttals, and optionally runs a Final Boss holistic review. Adversary performance is tracked with a medal system.

## Data Flow

```
IN:  spec text + adversary selection + model config
     └─> run_gauntlet() (gauntlet.py:3290)

PROCESS:
     ├─> Phase 1: Generate concerns (parallel, ThreadPoolExecutor max_workers=5)
     ├─> Phase 2: Big Picture Synthesis (LLM holistic analysis)
     ├─> Phase 3: Filter against resolved concerns
     ├─> Phase 3.5: Cluster near-duplicates via LLM
     ├─> Phase 4: Multi-model evaluation (batched, wave-based concurrency)
     ├─> Phase 5: Rebuttals (dismissed adversaries argue back)
     ├─> Phase 6: Final adjudication (sustained rebuttals reviewed)
     └─> Phase 7: Optional Final Boss UX review (Opus 4.6)

OUT: GauntletResult
     + .adversarial-spec-gauntlet/concerns-{hash}.json
     + .adversarial-spec-gauntlet/raw-responses-{hash}.json
     + .adversarial-spec-gauntlet/evaluations-{hash}.json
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `run_gauntlet()` | Main 7-phase pipeline orchestrator | gauntlet.py:3290 |
| `generate_attacks()` | Phase 1: parallel adversary concern generation | gauntlet.py |
| `generate_big_picture_synthesis()` | Phase 2: holistic cross-concern analysis | gauntlet.py |
| `filter_concerns_with_explanations()` | Phase 3: filter against resolved concerns | gauntlet.py |
| `cluster_concerns_with_provenance()` | Phase 3.5: semantic deduplication | gauntlet.py |
| `evaluate_concerns_multi_model()` | Phase 4: batched multi-model verdict generation | gauntlet.py:2172 |
| `format_gauntlet_report()` | Human-readable report formatting | gauntlet.py:3710 |
| `get_adversary_leaderboard()` | Running stats across gauntlet runs | gauntlet.py |
| `get_medal_leaderboard()` | Medal rankings across runs | gauntlet.py |

## Common Patterns

### Phase Checkpoint Persistence

Each phase writes intermediate results to `.adversarial-spec-gauntlet/` JSON files immediately after completion. This enables crash recovery — if a later phase fails, earlier results survive.

### Wave-Based Concurrency (Phase 4)

Multi-model evaluation uses batched processing (15 concerns per batch) with per-provider rate limit awareness. Multiple waves are dispatched if needed.

### Verdict Normalization

`normalize_verdict()` at gauntlet.py:148 maps various model response formats to canonical verdicts: accepted, dismissed, acknowledged, deferred.

### Medal System

Medals (gold/silver/bronze) awarded based on: uniqueness of catches (concerns no other adversary found), severity of catches, and signal-to-noise ratio. Stats persist in `~/.adversarial-spec/adversary_stats.json`.

## Error Handling

- **Per-adversary failures**: Each adversary call is independent. If one fails, others continue.
- **Evaluation failures**: If eval model can't evaluate a concern, it's marked as deferred.
- **Phase errors**: try/except at phase level — logs warning, continues with partial results.

## Integration Points

**Calls out to:**
- `litellm.completion()` — LLM calls for all phases
- `ADVERSARIES` dict (adversaries.py) — persona definitions
- `cost_tracker` (models.py) — cost accumulation
- File system — JSON persistence for crash recovery

**Called by:**
- `debate.py:handle_gauntlet()` — via debate CLI
- `gauntlet.py:main()` — standalone CLI at line 3836

## LLM Notes

- gauntlet.py is ~4087 lines — the largest file. The core `run_gauntlet()` starts at line 3290.
- Adversary personas are defined in adversaries.py, not gauntlet.py. Each has name, prefix, persona fields.
- The Final Boss (FINAL_BOSS in adversaries.py) issues PASS/REFINE/RECONSIDER verdicts and is run after all other phases.
- Phase 2 (Big Picture Synthesis) was added after original design — it identifies hidden connections and meta-concerns that individual adversaries miss.
- Data classes: Concern (line 121), Evaluation (line 153), Rebuttal (line 165), BigPictureSynthesis (line 175), GauntletResult (line 192).
