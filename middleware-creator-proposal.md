# Proposal: middleware-creator — Multi-LLM Competitive Middleware Implementation

## Problem Statement

When a spec defines middleware interfaces (standalone classes with clear inputs/outputs), the implementation quality varies significantly by model. We want to:
1. Get the simplest correct implementation
2. Measure model efficiency at middleware creation
3. Build a benchmark dataset ("middlewarecreator") for evaluating LLMs on implementation tasks

## Proposed Workflow

### Phase 1: Test Suite Agreement (Consensus)

All 3 models receive:
- Middleware spec (name, purpose, inputs, outputs, edge cases) — from Fizzy card description
- No architecture context needed (middleware is self-contained by design)

Each model independently proposes a test suite. Then:
1. Union all test cases
2. Models vote on each test: keep/drop (2/3 majority keeps)
3. Any model can add "mandatory" tests (edge cases the others missed)
4. Final test suite saved to disk as pytest file

**Output:** `tests/middleware/test_{name}.py` — agreed-upon test suite

### Phase 2: Competitive Implementation

All 3 models receive:
- The agreed test suite (from Phase 1)
- The middleware spec (same as Phase 1)
- Instruction: "Implement the simplest class that passes all tests"

Each model works independently. All implementations must:
- Pass the EXACT same test suite (no test modifications allowed)
- Be a single Python file with one class
- Have no external dependencies beyond stdlib + project deps

**Output:** 3 implementations: `impl_codex.py`, `impl_gemini.py`, `impl_claude.py`

### Phase 3: Selection (Claude as Judge)

Claude receives all 3 implementations + test results. Selection criteria (ordered):
1. **All tests pass** — any failing impl is eliminated
2. **Simplest** — usually fewest lines, but Claude judges: fewer abstractions, clearer control flow, less indirection
3. **Tiebreaker** — fewer characters, then alphabetical by model name

**Output:** Selected implementation + rationale

### Phase 4: Metrics Capture

For each run, save:
```json
{
  "middleware_name": "PacingBudget",
  "spec_hash": "abc123",
  "test_suite": {
    "total_tests": 12,
    "agreed_by_consensus": 10,
    "added_as_mandatory": 2
  },
  "implementations": {
    "codex": {"lines": 45, "chars": 1823, "tests_passed": 12, "tests_failed": 0, "time_seconds": 34},
    "gemini": {"lines": 62, "chars": 2541, "tests_passed": 12, "tests_failed": 0, "time_seconds": 28},
    "claude": {"lines": 38, "chars": 1502, "tests_passed": 11, "tests_failed": 1, "time_seconds": 41}
  },
  "selected": "claude",  // wait, claude failed 1 test — so codex wins (45 lines, all pass)
  "selected_reason": "Simplest passing implementation (45 lines vs 62)",
  "timestamp": "2026-04-09T16:00:00Z"
}
```

### Goal: middlewarecreator Benchmark

Over time, accumulate runs across projects. Each middleware spec + test suite + 3 implementations becomes a benchmark entry. Metrics tracked:
- **Pass rate** by model (does it even produce correct code?)
- **Simplicity score** by model (lines / chars when correct)
- **Speed** by model (wall clock to working implementation)
- **Win rate** by model (how often is it selected?)

This lets Jason test new/cheaper models: "Can haiku do middleware as well as opus for half the cost?"

## Integration with adversarial-spec

### Where it fits in the pipeline

```
debate → gauntlet → finalize → [middleware-creator] → execution → implementation
```

The middleware-creator phase runs AFTER spec finalization but BEFORE card-level implementation. It:
1. Reads the execution plan to identify all middleware interfaces
2. Creates one Fizzy card per middleware (blocks implementation cards)
3. Runs the 3-phase process per middleware
4. After ALL middleware cards pass tests → runs integration test wave
5. After integration wave passes → unblocks implementation cards

### New debate.py subcommand

```bash
cat middleware-spec.md | python3 debate.py middleware-create \
  --models "codex/gpt-5.5,gemini-cli/gemini-3.1-pro-preview,claude-cli/claude-opus-4-7" \
  --test-consensus-threshold 0.67 \
  --output-dir middlewares/ \
  --benchmark-log .adversarial-spec/middleware-benchmark.jsonl
```

### Fizzy card lifecycle

```
[Middleware: PacingBudget] — card in "New Todo"
  ↓ picked up by middleware-creator
[Test Suite Agreement] — 3 models agree on tests
  ↓ tests saved to disk
[Competitive Implementation] — 3 models implement
  ↓ all run against tests
[Selection] — simplest passing impl chosen
  ↓ card moves to "Review"
[Review] — human or agent reviews selected impl
  ↓ card moves to "Passed Test"
[Integration Wave] — after ALL middleware cards pass
  ↓ run full integration test suite
[Completed-Unmapped] — middleware ready for use
  ↓ unblocks implementation cards
```

## Questions to Resolve in Brainstorm

1. **What counts as "middleware"?** Proposed: any class that (a) has clear input types and output types, (b) can be tested without the rest of the system, (c) is used by 2+ other components. Examples from ETB v15: `PacingBudget`, `EngineSnapshot`, `AccountState`, `BrokerAdapter`, `DataPullService`.

2. **How do we handle middleware that depends on other middleware?** Example: `DataPullService` uses `PacingBudget` and `BrokerAdapter`. Proposed: create in dependency order. Earlier middleware become fixtures for later tests.

3. **Should models see each other's test proposals before voting?** Proposed: yes (transparency reduces gaming). Each model sees all 3 proposals and votes.

4. **What if no model passes all tests?** Proposed: models get ONE retry with the failing test output. If still failing, the middleware spec is probably underspecified — escalate to human.

5. **How to handle async middleware?** Proposed: test suite uses `pytest-asyncio`. Models are told whether the middleware is sync or async in the spec.

6. **Integration test wave scope.** Should it test all middleware together (true integration), or just verify each middleware's interface compatibility (contract tests)? Proposed: contract tests first, then one happy-path integration test per workflow.

7. **Benchmark data format.** Should we publish this? Open-source the benchmark entries? Could be valuable for the LLM evaluation community.

8. **Cost tracking.** Each competitive implementation costs 3x (one per model). Is this worth it for all middleware, or only for complex ones? Proposed: always run 3-model for the benchmark value. Can later add a "fast path" that skips competition for trivial middleware.
