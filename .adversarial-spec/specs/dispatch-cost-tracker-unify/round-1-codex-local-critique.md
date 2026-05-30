# Round 1 Local Codex Critique

External Claude CLI and Gemini CLI critic dispatches were blocked by tenant policy before reports were produced. Codex performed the local participant critique.

## Findings

### R1-CX-1: `fresh_tracker` single patch point conflicts with `from token_tracking import tracker`

If production modules import the singleton with `from token_tracking import tracker`, then `monkeypatch.setattr(token_tracking, "tracker", fresh)` does not update already-bound module globals. Tests would still need per-consumer monkeypatches, defeating the fixture goal.

Resolution: require production modules to `import token_tracking` and dereference `token_tracking.tracker` at call time. Ban direct singleton imports in mutable call paths.

### R1-CX-2: Phase 3 filtering tracking is an intentional accounting change, not parity

`phase_3_filtering.py` already calls `call_model()` but was previously untracked. Moving tracking into `call_model()` will newly count phase 3 filtering. Exact before/after token-total parity is therefore contradictory unless phase 3 opts out.

Resolution: keep phase 3 tracked as an intentional undercount fix. Replace exact total parity with two checks: previously tracked call sites remain single-counted, and phase 3 filtering is now recorded once.

### R1-CX-3: Static audit for `.add(` is too broad

The audit command can match unrelated list/set/dict `.add(...)` calls. Treat broad matches as inventory, not failure.

Resolution: require investigation of broad matches and stricter failure checks for tracker-object writes.

### R1-CX-4: Direct method monkeypatch exception is too vague

The spec permits direct `record_call` monkeypatches for failure injection but does not define evidence required. This risks recreating the scattered monkeypatch pattern.

Resolution: allow direct method monkeypatch only when the test names the consumer under test and asserts call semantics, not as a general accounting reset.
