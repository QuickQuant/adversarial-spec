# Component: MCP Tasks

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Cross-agent task coordination via MCP protocol |
| Entry | `mcp.run()` at mcp_tasks/server.py:404 |
| Key files | mcp_tasks/server.py, skills/adversarial-spec/scripts/task_manager.py |
| Depends on | mcp (FastMCP), filelock |
| Used by | Claude Code agents, Codex agents (cross-agent coordination) |
| Runtime status | implemented |
| Architecture status | active_primary |

## What This Component Does

Provides a task CRUD API via the MCP (Model Context Protocol). Four tools — TaskCreate, TaskGet, TaskList, TaskUpdate — manage tasks stored in `.claude/tasks.json`. MCP server now uses FileLock (`_mutate_tasks()`) for concurrent access safety. Used for cross-agent coordination between Claude and Codex working on the same project. task_manager.py provides a Python-native TaskManager class with the same storage format.

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `TaskCreate()` | Create task with subject/description | mcp_tasks/server.py:98 |
| `TaskGet()` | Retrieve task by ID | mcp_tasks/server.py:140 |
| `TaskList()` | List tasks with filtering | mcp_tasks/server.py:160 |
| `TaskUpdate()` | Update task status/metadata | mcp_tasks/server.py:261 |
| `load_tasks()` | Read .claude/tasks.json | mcp_tasks/server.py |
| `save_tasks()` | Write .claude/tasks.json | mcp_tasks/server.py |

## Contracts

### Type Contracts

| Contract | Purpose | Owner | Consumed By |
|----------|---------|-------|-------------|
| Task | Task object (id, subject, status, owner, blocks/blockedBy) | server.py + task_manager.py | Cross-agent workflows |

## Error Handling

- **No file locking on tasks.json**: Both MCP server and TaskManager read/write without locking. Known risk for concurrent access.

## Concurrency Concerns

| Resource | Callers | Synchronization | Risk |
|----------|---------|-----------------|------|
| `.claude/tasks.json` | MCP server, TaskManager | None | Medium — last-write-wins on concurrent access |

## Configuration

| Config | Source | Default |
|--------|--------|---------|
| `MCP_WORKING_DIR` | env var | None (falls back to PWD) |

## LLM Notes

- Task JSON uses `blockedBy` (camelCase) in storage but `blocked_by` (snake_case) in Python. Watch for key name mismatches.
- task_manager.py has a `__name__ == "__main__"` demo block — don't confuse it with a real entry point.
