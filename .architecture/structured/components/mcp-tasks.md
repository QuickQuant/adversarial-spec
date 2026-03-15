# Component: MCP Tasks

## Quick Reference

| Property | Value |
|----------|-------|
| Purpose | Cross-agent task coordination via MCP protocol |
| Entry | `mcp.run()` at mcp_tasks/server.py:365 |
| Key files | mcp_tasks/server.py, scripts/task_manager.py |
| Depends on | mcp (FastMCP), shared .claude/tasks.json storage |
| Used by | Claude Code agents, debate.py (optional task tracking) |

## What This Component Does

The MCP Tasks server provides a task management API accessible to Claude Code agents via the MCP protocol. It exposes four tools (TaskCreate, TaskGet, TaskList, TaskUpdate) that operate on a shared `.claude/tasks.json` file. The companion `task_manager.py` provides a Python API to the same storage, enabling debate.py to track round progress alongside MCP-based task management.

## Data Flow

```
IN:  MCP protocol messages (tool calls from Claude Code)
     └─> FastMCP server (server.py:365)

PROCESS:
     ├─> TaskCreate: generate ID, write to tasks.json
     ├─> TaskGet: read by ID from tasks.json
     ├─> TaskList: filter by session_id, status, owner
     └─> TaskUpdate: modify status, metadata, blockedBy

OUT: MCP protocol responses (JSON)
     + .claude/tasks.json (shared file)
```

## Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `TaskCreate` (decorator) | Create new task | server.py:98 |
| `TaskGet` (decorator) | Get task by ID | server.py:140 |
| `TaskList` (decorator) | List tasks with filters | server.py:160 |
| `TaskUpdate` (decorator) | Update task status/metadata | server.py:261 |
| `TaskManager.__init__()` | Python API initialization | task_manager.py:124 |
| `TaskManager.create_task()` | Python task creation | task_manager.py |
| `create_adversarial_spec_session()` | Creates full 5-phase task set | task_manager.py |

## Common Patterns

### Shared Storage

Both the MCP server and Python TaskManager read/write the same `.claude/tasks.json`. This enables Claude Code's MCP tools and Python scripts to see each other's tasks without a separate coordination layer.

### Working Directory Detection

`get_working_dir()` checks `MCP_WORKING_DIR` → `PWD` → `os.getcwd()` to find the project root. This ensures tasks are stored per-project.

## Error Handling

- **File locking**: No explicit locking — assumes single writer at a time
- **Missing file**: Created on first write with `{tasks: [], next_id: 1}` structure
- **Invalid JSON**: Caught and returns empty task list

## Integration Points

**Calls out to:**
- File system (`.claude/tasks.json`) — read/write

**Called by:**
- Claude Code agents via MCP protocol
- `debate.py:get_task_manager()` — lazy-loaded Python API
- `task_manager.py:create_adversarial_spec_session()` — batch task creation

## LLM Notes

- The MCP server uses FastMCP decorators, not explicit tool registration. Tools are defined as decorated functions.
- `task_manager.py` is the Python equivalent of the MCP server — same storage, different interface.
- Session-based filtering uses `metadata.session_id` field, not a top-level session property.
- The `OWNER_PREFIX = "adv-spec:"` convention identifies tasks owned by the adversarial-spec skill.
