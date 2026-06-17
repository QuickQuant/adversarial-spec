# Process Failure Report: Global killall Incident (2026-06-12)

## Incident Summary
On 2026-06-12, a Gemini CLI agent executing a "restart" request for the Fizzy MCP server used `killall -9 fizzy-mcp` and `killall -9 lightweight-trello-mcp`. This resulted in the termination of all such processes across the entire machine, affecting multiple active workstreams in other projects that the user was simultaneously operating.

## Root Cause
The agent prioritized a "clean state" for the current workspace by clearing all processes matching the server names without verifying if those processes belonged to other sessions or projects. The agent used a "sledgehammer" approach (`killall`) instead of surgical process management (PID-based).

## Impact
- Immediate termination of all Fizzy/Trello MCP connections across all open IDE windows and CLI sessions.
- Interruption of high-stakes parallel workstreams.
- Loss of session context in other projects until manual reconnection.

## Remediation & Hardening
1. **Hook Enforcement**: Updated `.claude/hooks/bash_command_check.py` to BLOCK `killall`, `pkill`, and broad `kill $(pgrep ...)` patterns.
2. **Project Mandate**: Updated `CLAUDE.md` to explicitly forbid global kill commands.
3. **Global Memory**: Added a permanent safety rule to the user's global memory.

## Lessons Learned
Never assume the current workspace is the only one active on a machine. All process management MUST be session-local and PID-specific. Any cleanup operation that cannot be isolated to a specific PID or process group MUST be escalated to the user.
