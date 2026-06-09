# adversarial-spec

The domain language of the adversarial-spec skill — a Claude Code skill that refines
specs through multi-model adversarial debate and drives them through a phased pipeline
(requirements → roadmap → debate → target-architecture → gauntlet → finalize →
execution → implementation).

## Language

**Test Strategy** (`test_strategy`):
A Phase 7 per-task choice of testing approach: `test-first`, `test-after`, `spike`
(ship with no automated-test commitment), or `refactor` (restructure existing code,
behavior unchanged). Decoupled from whether tests are actually enforced — that is the
job of `verification_mode`.
_Avoid_: bare "strategy" (collides with Data Strategy); "skip" (not a valid value — use
`spike` for no-test tasks).

**Data Strategy** (`data_strategy`):
A Phase 2 per-test-case classification of *what data* a test exercises: `REAL-DATA`,
`REAL-DATA + PROPERTY`, `SYNTHETIC`, `MOCK`, `MOCK-EXTERNAL`, `FRONTEND`, `STATIC`.
The gauntlet flags violations as the concern category `data_strategy_mismatch`.
_Avoid_: bare "strategy" (collides with Test Strategy).
