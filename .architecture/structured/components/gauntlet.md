# Component: Gauntlet

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Adversarial stress-testing of specs with named attacker personas |
| Entry | `run_gauntlet()` at scripts/gauntlet.py |
| Key files | gauntlet.py (~3500 lines), adversaries.py |
| Depends on | Models (litellm), Adversaries, Providers |
| Used by | Debate Engine (handle_gauntlet), standalone CLI |

## What This Component Does

The gauntlet subjects a finalized spec to attack from five adversary personas, each probing from a different angle (security, operations, distributed systems, UX, business logic). A frontier model evaluates whether each concern is valid, adversaries can rebut dismissed concerns, and a Final Boss performs a holistic review. Adversary performance is tracked with a medal system.

## Data Flow

```
IN:  spec text + adversary selection
     └─> run_gauntlet() (gauntlet.py)

PROCESS:
     ├─> Phase 1: Generate concerns (parallel per adversary via ThreadPoolExecutor)
     ├─> Phase 2: Filter duplicates and low-signal
     ├─> Phase 3: Evaluate each concern (frontier model verdict)
     ├─> Phase 4: Rebuttal (dismissed adversaries argue back)
     ├─> Phase 5: Big Picture Synthesis (holistic analysis)
     └─> Phase 6: Medal Awards (rank adversary performance)

OUT: GauntletResult JSON report
     └─> ~/.adversarial-spec-gauntlet/run-{uuid}.json
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `run_gauntlet()` | Main 6-phase pipeline orchestrator | gauntlet.py |
| `format_gauntlet_report()` | Human-readable report formatting | gauntlet.py |
| `generate_medal_report()` | Medal award computation and display | gauntlet.py |
| `get_adversary_leaderboard()` | Running stats across gauntlet runs | gauntlet.py |
| `get_medal_leaderboard()` | Medal rankings across runs | gauntlet.py |

## Common Patterns

### Parallel Adversary Execution

Phase 1 uses ThreadPoolExecutor to call all adversary personas simultaneously. Each adversary gets its own system prompt derived from its persona definition in adversaries.py.

### Verdict Evaluation

Phase 3 sends each concern to a frontier model with a structured evaluation prompt. The model returns one of: accepted (real issue), acknowledged (minor/known), dismissed (not valid), deferred (out of scope).

### Medal System

Medals (gold/silver/bronze) are awarded based on: uniqueness of catches (concerns no other adversary found), severity of catches, and signal-to-noise ratio.

## Error Handling

- **Per-adversary failures**: Each adversary call is independent. If one fails, others continue. Error count tracked in adversary_stats.
- **Evaluation failures**: If frontier model can't evaluate a concern, it's marked as deferred.
- **Cost overruns**: Cost tracking alerts shown in report summary.

## Integration Points

**Calls out to:**
- `litellm.completion()` — for LLM calls (adversary generation + evaluation)
- `ADVERSARIES` dict (adversaries.py) — persona definitions
- `cost_tracker` (models.py) — cost accumulation

**Called by:**
- `debate.py:handle_gauntlet()` — via debate CLI
- `gauntlet.py:main()` — standalone CLI

## LLM Notes

- gauntlet.py is ~3500 lines. The core `run_gauntlet()` function is the key entry.
- Adversary personas are defined in adversaries.py, not gauntlet.py. Each has a name, description, attack focus, and prompt template.
- The Final Boss (FINAL_BOSS in adversaries.py) issues PASS/REFINE/RECONSIDER verdicts and is run after all other adversaries.
- Medal stats persist in `~/.adversarial-spec-gauntlet/` across runs for leaderboard tracking.
