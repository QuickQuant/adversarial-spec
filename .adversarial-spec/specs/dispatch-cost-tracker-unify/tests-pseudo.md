# Test Pseudocode: Dispatch & Cost-Tracker Unification

> Canonical test source for roadmap user stories.

## US-0: Reference Audit

### TC-0.1: Full tracker reference audit finds expected call sites
**Strategy: STATIC** - Reads repository text only; no runtime behavior required.

Given the repository source tree
When the audit searches for `cost_tracker`, `CostTracker`, `(cost_tracker|tracker)\.add\(`, `token_tracking`, `TokenTracker`, `record_call`, and `call_model(`
Then the result includes implementation, tests, string monkeypatch references, and `call_model(...)` tuple-unpack shapes
And the raw audit plus interpreted import/unpack inventory is saved before production edits begin

### TC-0.2: Audit fails if phase-local tracker import remains after refactor
**Strategy: STATIC** - Import boundary can be verified by reading files.

Given the refactored gauntlet phase files
When the audit searches `skills/adversarial-spec/scripts/gauntlet/phase_*.py` for `cost_tracker`, `token_tracker`, or `from token_tracking import tracker`
Then no matches are returned
And any match blocks completion of M3

## US-1: fresh_tracker Fixture

### TC-1.1: fresh_tracker supplies an isolated tracker instance
**Strategy: SYNTHETIC** - Needs a controlled tracker with exact token values.

Given a test using the phase-1 `fresh_tracker` fixture before `token_tracking.py` exists
When the test records a model call through `models.cost_tracker`
Then `fresh_tracker` receives the call

Given a test using the phase-2 `fresh_tracker` fixture after `token_tracking.py` exists
When the test records a model call with 10 input tokens and 20 output tokens
Then `fresh_tracker.total_input_tokens` is 10
And `fresh_tracker.total_output_tokens` is 20
And `fresh_tracker.by_model` contains only that model

### TC-1.1b: Consumer modules observe patched tracker singleton
**Strategy: SYNTHETIC** - Requires controlled module imports and tracker replacement.

Given a consumer module that records token usage through `token_tracking.tracker`
And the `fresh_tracker` fixture has patched `token_tracking.tracker`
When the consumer records a model call
Then the call is visible on `fresh_tracker`
And no stale singleton imported with `from token_tracking import tracker` receives the call
And no module-level local rebind of `token_tracking.tracker` receives the call

### TC-1.2: Existing direct monkeypatch pattern is absent
**Strategy: STATIC** - Text search is the direct verification.

Given the tests after fixture migration
When the audit searches for `monkeypatch.setattr` targeting `cost_tracker.add` or `tracker.record_call`
Then no direct tracking method monkeypatch remains
And affected tests include `fresh_tracker` in their fixture list instead

## US-2: TokenTracker Rename

### TC-2.1: TokenTracker preserves read-side summary fields
**Strategy: SYNTHETIC** - Exact token and cost totals require controlled model costs.

Given a `TokenTracker`
When `record_call` is invoked for a known model with fixed input and output tokens
Then `total_cost`, `total_input_tokens`, `total_output_tokens`, `by_model`, and `summary()` return equivalent values to the old tracker contract

### TC-2.2: Old write API is removed
**Strategy: STATIC** - This is an API surface check.

Given the refactored code
When the audit searches for `.add(` calls on tracker objects and `CostTracker`
Then no old tracker write API remains
And `record_call` is the only write method used for token tracking

### TC-2.3: TokenTracker remains thread-safe
**Strategy: SYNTHETIC** - Thread interleavings need controlled concurrent calls.

Given a shared `TokenTracker`
When multiple worker threads call `record_call` concurrently with fixed token values
Then aggregate totals equal the sum of all calls
And no per-model totals are lost or corrupted

### TC-2.4: TokenTracker handles invalid token counts deliberately
**Strategy: SYNTHETIC** - Invalid inputs must be controlled and deterministic.

Given a `TokenTracker`
When `record_call` receives zero, negative, missing, or non-integer token counts according to the pre-rename audit cases
Then the result either preserves the old tracker behavior exactly
Or raises a deliberate `ValueError` covered by the spec and tests
And no invalid input silently corrupts aggregate totals

## US-3: Gauntlet Dispatch Boundary

### TC-3.1: call_model records usage for a successful mocked model response
**Strategy: MOCK-EXTERNAL** - scope: LLM provider response
**why_impossible_to_reproduce_live:** Exact provider token usage and response metadata cannot be forced deterministically across live LLM providers without replacing the provider boundary.

Given `gauntlet/model_dispatch.call_model()` with a mocked successful completion response
And a `fresh_tracker`
When `call_model` returns content, input token count, and output token count
Then `fresh_tracker.by_model` records the same model and token counts
And the phase caller does not record tokens itself

### TC-3.2: Failed call_model response does not double-record usage
**Strategy: MOCK-EXTERNAL** - scope: LLM provider failure
**why_impossible_to_reproduce_live:** A provider failure with exact exception shape and no usage metadata cannot be induced reliably against live services.

Given `gauntlet/model_dispatch.call_model()` with a mocked provider failure
When the call returns or raises according to current error semantics
Then token usage is not recorded unless a successful response with usage metadata exists
And no phase-level fallback call records duplicate usage

### TC-3.3: Deterministic mocked dispatch parity preserves by_model totals
**Strategy: MOCK-EXTERNAL** - scope: LLM provider response
**why_impossible_to_reproduce_live:** Live LLM tokenization and response lengths vary; parity requires exact repeated token metadata.

Given a fixed list of mocked model responses with known token usage for each phase file listed in spec Section 6.3
And mocked responses cover LiteLLM plus `codex/`, `gemini-cli/`, and `claude-cli/` model prefixes
When the old tracking placement and new dispatch-boundary placement are exercised in deterministic test harnesses
Then `by_model` totals match exactly for those previously tracked call sites
And `total_input_tokens` and `total_output_tokens` match exactly for those previously tracked call sites
And CLI-prefixed calls remain zero-cost

### TC-3.4: Phase 3 filtering is newly tracked once
**Strategy: MOCK-EXTERNAL** - scope: LLM provider response
**why_impossible_to_reproduce_live:** Live LLM tokenization and response lengths vary; exact token metadata requires provider replacement.

Given `phase_3_filtering.py` calls `gauntlet/model_dispatch.call_model()` with a mocked successful response
When the refactored dispatch boundary records token usage
Then the phase 3 filtering model call is recorded exactly once
And this expected new count is not treated as a parity failure

## US-4: Verification and Status Capture

### TC-4.1: Durable artifacts record CON-002 target and CON-001 drift
**Strategy: STATIC** - Verifies persisted session/spec artifacts.

Given the session detail file and roadmap artifacts
When a future agent reads `requirements_summary` and `manifest.json`
Then CON-002 is the only active remediation concern
And CON-001 is explicitly marked out of scope due to generated concern drift

### TC-4.2: Full test suite passes at commit boundaries
**Strategy: STATIC** - Local command result is the acceptance evidence.

Given each planned commit boundary
When `uv run pytest` runs
Then the command exits successfully
And failures block phase completion until resolved

### TC-4.3: Deployed skill copy matches repo changes or deferral is recorded
**Strategy: STATIC** - File checksum or session decision artifact is enough evidence.

Given production changes under `skills/adversarial-spec/`
When final verification runs
Then `readlink ~/.claude/skills/adversarial-spec` is recorded and resolves to this repo's `skills/adversarial-spec/`
Or the changed files are copied to `~/.claude/skills/adversarial-spec/`
Or the user has explicitly deferred deployment in the session decisions log
And the final status reports which path was taken

<!-- P4_INVARIANT_TESTS_START -->
## Invariant Tests (Phase 4)

### TC-INV-001: Gauntlet token accounting is single-counted at dispatch boundary
**Strategy: DYNAMIC** - Deterministic mocked parity test; no real model calls.

Given mocked `gauntlet/model_dispatch.call_model()` paths for LiteLLM, Codex CLI, Gemini CLI, and Claude CLI
And representative gauntlet phase call patterns from phases 1, 2, 3, 4, 5, 6, and 7
When each successful model call returns fixed `(content, input_tokens, output_tokens)` values
Then `token_tracking.tracker.record_call(...)` records each successful call exactly once
And phase 3 filtering is recorded once through the dispatch boundary
And the public `call_model(...)` return value remains `(content, input_tokens, output_tokens)`
And total input tokens, output tokens, cost, and `by_model` equal the expected deterministic totals

### TC-INV-002: Production tracker access resolves through token_tracking module
**Strategy: STATIC** - Boundary audit.

Given production paths under `skills/adversarial-spec/scripts`
When the post-rename static audit runs
Then no production file contains `from token_tracking import tracker`
And no production file binds `token_tracking.tracker` to a module-level local variable
And no production file contains `CostTracker`, `cost_tracker`, `cost_tracker.add(`, or `tracker.add(`
And all tracker reads and writes resolve through `token_tracking.tracker` at call time

### TC-INV-003: fresh_tracker is the default accounting isolation mechanism
**Strategy: STATIC + TARGETED TESTS** - Fixture migration audit.

Given tests that need isolated token accounting state
When the fixture migration is complete
Then tests use `fresh_tracker` for normal accounting isolation
And phase-local monkeypatches of `cost_tracker.add` are removed
And direct monkeypatches of `record_call` remain only for narrow failure-injection tests that name the consumer under test
And targeted gauntlet/model tests pass with the fixture-owned tracker state
<!-- P4_INVARIANT_TESTS_END -->
