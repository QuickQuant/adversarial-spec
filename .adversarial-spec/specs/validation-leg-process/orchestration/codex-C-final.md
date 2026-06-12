Route (b): kept dotted internal/artifact paths, normalized final plan IDs in driver; `fix_task_ids.py` is now no-op.

Re-emitted `fizzy-plan.json`; `self_check_plan()` returned `{"valid": true, "issues": []}`.

Assertions passed: 25 status values all in enum, 21 top-level `verify_commands` checked, max command length 95, dotted task IDs 0.

Artifact/hash checks passed for 57 spec/verification paths; report section appended.

`uvx ruff check .../emit_driver.py` passed. No deviations; no MCP/board/commit.