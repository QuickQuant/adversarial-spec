# Architecture Action Plan

> Refreshed 2026-06-11 (incremental f198887) — remediation plan from concerns[].

## Priority: Now
### CON-001: Triple litellm completion() pathway
- **Fix approach:** direct implementation (small adversarial-spec-free refactor)
- **Files:** models.py, gauntlet/model_dispatch.py, debate.py
- **Blast zone:** every API model call; tests that monkeypatch completion
- **Estimated scope:** small-medium
### CON-003: run_gauntlet() ~700 lines
- **Fix approach:** direct implementation (phase-table extraction)
- **Files:** gauntlet/orchestrator.py
- **Blast zone:** resume logic, phase metrics capture
- **Estimated scope:** medium

## Priority: Next
### CON-002: finish token_tracking injection — direct implementation; models.py, model_dispatch.py, 7 phase files; removes ~30 test monkeypatches.
### CON-005: inline prompts in phases 5/7 — doc-sized move into gauntlet/prompts.py.
### CON-007: divergent CLI surfaces — shared defaults module + flag aliases (debate.py, gauntlet/cli.py). Grouped with CON-001 (same files).
### CON-008: dispatch baseline race — one-file hook fix (key baseline by session id). Coordinate with Brainquarters hooks if shared.
### CON-009: prompts.py shadow — rename gauntlet/prompts.py to phase_prompts.py + fix imports (mechanical, ~15 import sites).

## Priority: Later
### CON-004: dead-code remnants — re-verify phase_3_filtering remnant; prune deprecated debate.py commands.
### CON-006: sys.path manipulation — proper packaging; large blast zone, low urgency.
