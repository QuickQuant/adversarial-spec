# Component: Retired MCP Tasks Surface

> Derived from: prior architecture references and current repository deletion evidence | Verified at: `ef18c66`
> If any derived-from file changed since `ef18c66`, trust source over this doc.

## Quick Reference

| Property | Value |
|---|---|
| Purpose | Historical record for the removed MCP Tasks server/task-manager surface |
| Entry | none; `mcp_tasks/`, `task_manager.py`, and `scope.py` are deleted |
| Runtime status | disabled |
| Architecture status | deprecated |

## Contracts

None. The current pipeline board/Fizzy integration is the task system; no active Python import should target this component.

## Invariants

- Do not reintroduce a parallel task store without an approved architecture decision.
- References to this component in old docs are historical unless a live import is reintroduced.

## Active vs Target

- **Active consumers:** none found in the current source map.
- **Target architecture:** Fizzy pipeline cards and phase-owned workflow own task state.

## LLM Notes

- This document exists to prevent stale architecture refs from misleading planners; it is not an implementation target.
