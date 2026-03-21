# Component: Gauntlet

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | 7-phase adversarial stress-testing of specs with named attacker personas |
| Entry | `run_gauntlet()` in `scripts/gauntlet/orchestrator.py` |
| Key files | `gauntlet/` package (16 modules), `adversaries.py` |
| Depends on | Models (litellm), Adversaries, Providers |
| Used by | Debate Engine (handle_gauntlet), standalone CLI (`gauntlet/cli.py`) |

## Package Structure

```
scripts/gauntlet/
├── __init__.py          # Public API: 5 re-exported symbols
├── __main__.py          # python -m gauntlet support
├── cli.py               # Standalone CLI entry point (argparse)
├── orchestrator.py      # run_gauntlet() — phase sequencing, resume, checkpoints
├── core_types.py        # All dataclasses, enums, config (GauntletConfig, GauntletResult, etc.)
├── model_dispatch.py    # LLM calling, model selection, rate limiting
├── persistence.py       # JSON I/O, stats, checkpoints, run manifests
├── medals.py            # Medal calculation, reports, leaderboard
├── reporting.py         # Human-readable reports, adversary leaderboard, synergy
├── phase_1_attacks.py   # Parallel adversary concern generation
├── phase_2_synthesis.py # Big Picture holistic analysis
├── phase_3_filtering.py # Explanation matching, clustering, dedup
├── phase_4_evaluation.py # Multi-model verdict generation
├── phase_5_rebuttals.py # Adversary rebuttals to dismissals
├── phase_6_adjudication.py # Final decisions on challenged dismissals
└── phase_7_final_boss.py   # Opus 4.6 UX/user story review
```

## What This Component Does

The gauntlet subjects a spec to attack from multiple adversary personas, each probing from a different angle (security, operations, distributed systems, UX, business logic). A 7-phase pipeline generates concerns, synthesizes patterns, filters/clusters duplicates, evaluates with multi-model consensus, processes rebuttals for dismissed concerns, adjudicates sustained rebuttals, and optionally runs a Final Boss holistic review. Adversary performance is tracked with a medal system.

## Data Flow

```
IN:  spec text + adversary selection + model config
     └─> run_gauntlet() (orchestrator.py)

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
     + .adversarial-spec-gauntlet/evaluations-{hash}.json
     + .adversarial-spec-gauntlet/run-manifest-{hash}-{ts}.json
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `run_gauntlet()` | Main 7-phase pipeline orchestrator | `orchestrator.py` |
| `generate_attacks()` | Phase 1: parallel adversary concern generation | `phase_1_attacks.py` |
| `generate_big_picture_synthesis()` | Phase 2: holistic cross-concern analysis | `phase_2_synthesis.py` |
| `filter_concerns_with_explanations()` | Phase 3: filter against resolved concerns | `phase_3_filtering.py` |
| `cluster_concerns_with_provenance()` | Phase 3.5: semantic deduplication | `phase_3_filtering.py` |
| `evaluate_concerns_multi_model()` | Phase 4: batched multi-model verdict generation | `phase_4_evaluation.py` |
| `format_gauntlet_report()` | Human-readable report formatting | `reporting.py` |
| `get_adversary_leaderboard()` | Running stats across gauntlet runs | `reporting.py` |
| `get_medal_leaderboard()` | Medal rankings across runs | `medals.py` |

## Common Patterns

### GauntletConfig (Central Configuration)

All phase functions accept a `GauntletConfig` dataclass instead of individual timeout/reasoning params. Built once at the top of `run_gauntlet()` from CLI parameters. Fields: `timeout`, `attack_codex_reasoning`, `eval_codex_reasoning`, `auto_checkpoint`, `resume`, `unattended`.

### Phase Checkpoint Persistence

Each phase writes intermediate results to `.adversarial-spec-gauntlet/` JSON files. When `--unattended` is set, auto-checkpoints are written after Phases 3.5, 4, and 7. The `--gauntlet-resume` flag loads these checkpoints to skip completed phases.

### Wave-Based Concurrency (Phase 4)

Multi-model evaluation uses batched processing (15 concerns per batch) with per-provider rate limit awareness. Multiple waves are dispatched if needed.

### Verdict Normalization

`normalize_verdict()` in `core_types.py` maps various model response formats to canonical verdicts: accepted, dismissed, acknowledged, deferred.

### Medal System

Medals (gold/silver/bronze) awarded based on: uniqueness of catches, severity, and signal-to-noise ratio. Stats persist in `~/.adversarial-spec/adversary_stats.json`.

## Error Handling

- **Per-adversary failures**: Each adversary call is independent. If one fails, others continue.
- **Clustering failures**: Retry once, then raise `GauntletClusteringError` (no silent swallowing).
- **Evaluation failures**: If eval model can't evaluate a concern, it's marked as deferred.
- **KeyboardInterrupt**: Writes manifest status `"interrupted"`, exits with code 130.
- **Unattended mode**: Monkey-patches `builtins.input` to prevent stdin hangs.

## Integration Points

**Calls out to:**
- `litellm.completion()` / `call_model()` — LLM calls for all phases
- `ADVERSARIES` dict (adversaries.py) — persona definitions
- `cost_tracker` (models.py) — cost accumulation
- File system — JSON persistence for crash recovery and run manifests

**Called by:**
- `debate.py:handle_gauntlet()` — via debate CLI
- `gauntlet/cli.py:main()` — standalone CLI
- `python -m gauntlet` — via `__main__.py`

## LLM Notes

- The package was extracted from a ~4087-line monolith into 16 focused modules.
- `gauntlet_monolith.py` still exists as a thin backwards-compatibility shim.
- Adversary personas are defined in `adversaries.py`, not in the gauntlet package.
- The Final Boss (FINAL_BOSS in adversaries.py) issues PASS/REFINE/RECONSIDER verdicts.
- Core data classes are in `core_types.py`: Concern, Evaluation, Rebuttal, GauntletConfig, GauntletResult, etc.
