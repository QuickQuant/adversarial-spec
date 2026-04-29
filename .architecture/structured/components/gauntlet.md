# Component: Gauntlet Pipeline

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | 7-phase adversarial stress-test pipeline |
| Entry | `run_gauntlet()` at gauntlet/orchestrator.py:194 |
| Key files | gauntlet/orchestrator.py, gauntlet/core_types.py, gauntlet/persistence.py, gauntlet/model_dispatch.py, gauntlet/prompts.py, gauntlet/phase_1_attacks.py through phase_7_final_boss.py, gauntlet/medals.py, gauntlet/reporting.py, gauntlet/synthesis_extract.py |
| Depends on | Models, Adversaries, Providers |
| Used by | Debate Engine (debate.py), standalone CLI (gauntlet/cli.py) |
| Runtime status | implemented |
| Architecture status | active_primary |

## What This Component Does

The gauntlet is an 18-module package that stress-tests specifications through 7 sequential phases. Named adversary personas generate concerns, a frontier model evaluates them, dismissed adversaries get rebuttal chances, and a final boss issues a pass/refine/reconsider verdict. Each phase checkpoints to disk via FileLock-guarded atomic writes, enabling resume after crashes or quota exhaustion. Phase prompts are centralized in `gauntlet/prompts.py` (extracted from inline). Phase 3.5 clustering was removed after analysis showed it lost 48% of concerns.

## Data Flow

```
IN:  Spec text + GauntletConfig + adversary list
     └─> run_gauntlet() (orchestrator.py:196)

PROCESS:
     ├─> Phase 1: generate_attacks() -> Concern objects
     ├─> Phase 2: generate_big_picture_synthesis() -> BigPictureSynthesis
     ├─> Phase 3: filter concerns (clustering removed) -> filtered concerns
     ├─> Phase 4: evaluate_concerns() -> Evaluation objects (verdicts)
     ├─> Phase 5: run_rebuttals() -> Rebuttal objects
     ├─> Phase 6: final_adjudication() -> medals + report
     └─> Phase 7: run_final_boss_review() -> FinalBossResult

OUT: GauntletResult (aggregated) + checkpoint files
     └─> .adversarial-spec-gauntlet/{phase}-{hash}.json
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `run_gauntlet()` | Pipeline orchestration | orchestrator.py:196 |
| `generate_attacks()` | Phase 1: parallel adversary dispatch | phase_1_attacks.py:24 |
| `generate_big_picture_synthesis()` | Phase 2: cross-concern synthesis | phase_2_synthesis.py:30 |
| `filter_concerns_with_explanations()` | Phase 3: resolved concern matching | phase_3_filtering.py |
| `cluster_concerns_with_provenance()` | Phase 3.5: concern clustering | phase_3_filtering.py:200 |
| `evaluate_concerns()` | Phase 4: frontier model evaluation | phase_4_evaluation.py:23 |
| `run_rebuttals()` | Phase 5: adversary rebuttals | phase_5_rebuttals.py |
| `final_adjudication()` | Phase 6: verdict aggregation + medals | phase_6_adjudication.py:40 |
| `run_final_boss_review()` | Phase 7: final pass/refine/reconsider | phase_7_final_boss.py:50 |
| `save_checkpoint()` | Atomic checkpoint write | persistence.py:250 |
| `load_partial_run()` | Resume from checkpoints | persistence.py:675 |
| `calculate_medals()` | Adversary accuracy scoring | medals.py:50 |

## Contracts

### Type Contracts

| Contract | Purpose | Owner | Consumed By |
|----------|---------|-------|-------------|
| `Concern` | Adversary-raised issue with stable ID | core_types.py:74 | All phases |
| `Evaluation` | Verdict on a concern | core_types.py:90 | Phases 5,6,7 |
| `Rebuttal` | Adversary response to dismissal | core_types.py:102 | Phase 7 |
| `GauntletResult` | All phase outputs aggregated | core_types.py:220 | Reporting, persistence |
| `GauntletConfig` | CLI parameter bundle | core_types.py:409 | All phases |
| `FinalBossResult` | Final verdict (PASS/REFINE/RECONSIDER) | core_types.py:195 | Phase 7 output |
| `CheckpointMeta` | Checkpoint file envelope | core_types.py:440 | persistence.py |

## Common Patterns

### Phase-Checkpoint Pattern
Every phase follows: execute → serialize → FileLock → atomic write. On resume, load_partial_run() validates spec_hash + config_hash + data_hash before accepting a checkpoint.

### Provider Rate Limiting
Phase 1 groups adversary-model pairs by provider and batches requests with provider-specific delays to avoid quota exhaustion.

## Error Handling

- **Phase failure**: Exceptions from model calls are caught and logged, not bubbled. Partial results are acceptable.
- **KeyboardInterrupt**: Caught at orchestrator level, manifest marked as "interrupted".
- **Checkpoint corruption**: _load_json_safe() catches JSONDecodeError, returns None. Resume treats it as no checkpoint.

## Concurrency Concerns

| Resource | Callers | Synchronization | Risk |
|----------|---------|-----------------|------|
| `cost_tracker` | Phase 1 ThreadPoolExecutor workers | `threading.Lock` in CostTracker.add() | Low (guarded) |
| Checkpoint files | save_checkpoint(), load_partial_run() | `FileLock` per file | Low (guarded) |

## Configuration

| Config | Source | Default |
|--------|--------|---------|
| `timeout` | CLI `--timeout` | 900 |
| `attack_codex_reasoning` | CLI `--codex-reasoning` | None |
| `eval_codex_reasoning` | CLI `--eval-codex-reasoning` | None |
| `resume` | CLI `--gauntlet-resume` | False |
| `unattended` | CLI `--unattended` | False |

## Integration Points

**Calls out to:**
- `Models.call_models_parallel()` / `model_dispatch.call_model()` — for LLM dispatch
- `Adversaries.ADVERSARIES` — for persona definitions
- `persistence.save_checkpoint()` / `load_partial_run()` — for checkpoint I/O

**Called by:**
- `debate.py:handle_gauntlet()` — via debate CLI
- `gauntlet/cli.py:main()` — via standalone CLI

## LLM Notes

- The gauntlet has two CLI entry points with different flag names. Check which CLI you're modifying.
- Phase 3.5 has an auto-checkpoint (quota burn safeguard). This is the critical resume point.
- Unattended mode monkey-patches `builtins.input`. Phase 7 has explicit fallback for no stdin.
- gauntlet_monolith.py is a 12-line shim. All real code is in the gauntlet/ package.
