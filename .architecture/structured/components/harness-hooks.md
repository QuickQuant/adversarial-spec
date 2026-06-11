# Component: Harness Hooks

> Added 2026-06-11 (incremental f198887). Files: .claude/hooks/*.py — the multi-agent coordination + safety plane that replaced the deleted MCP Tasks server.

| | |
|---|---|
| Entry | each hook's main() (stdin JSON in, JSON decision out) |
| Purpose | Enforce safety on Bash calls; coordinate conductor↔worker pipeline flow; log session activity; notify Telegram |
| Key files | dispatch_check.py, pipeline_continue.py, pipeline_idle_retry.py, pipeline_notifications.py, session_activity_logger.py, codex_pretool_combined.py, _resolve_config.py (shared), bash_command_check.py, deprecated_models.py, force_flag_defense.py, banned_*: safety set |
| Depends on | nothing in skills/scripts (clean boundary); _resolve_config.py shared helper |
| Used by | Claude Code / Codex / Gemini harnesses via .claude/settings.local.json registration |

## Coordination loop (pipeline workers)
1. PreToolUse(pipeline_do_next_task) → dispatch_check.py:86 — compares .conductor/dispatch/<role>/updates.jsonl line count vs /tmp/dispatch-baseline-<project>-<role>.txt; new messages injected as systemMessage (worker cannot ignore conductor signals). Roles: claude|codex|gemini|glm.
2. PostToolUse(complete_task|review|test, ok=true) → pipeline_continue.py:70 — "DO NOT STOP, call pipeline_do_next_task" systemMessage.
3. PostToolUse(do_next_task, action=idle) → pipeline_idle_retry.py:73 — synchronous sleep backoff (active 07-22h: 30/60/120/240s; overnight adds 480/960s); after 6 consecutive idles posts status to conductor dispatch log; counter in /tmp/pipeline-idle-count-*.
4. PostToolUse(pipeline_*) → pipeline_notifications.py — async Telegram + auto-dispatch (review baton); exit 0 always; config .conductor/notifications.json.

## Safety set
codex_pretool_combined.py composes banned_git/banned_filesystem/force_flag/pip_install via importlib (one invocation, first failure wins). bash_command_check.py blocks .py output piped to head/tail etc. (flexible vs strict via hook_config.json through _resolve_config.py). deprecated_models.py catches stale model names.

## Notes for LLMs
- Hooks emit {decision, systemMessage} or block via nonzero exit + stderr text.
- session_activity_logger.py appends JSONL (1MB rotation, 1 backup) read by /conductor briefings; never fails.
- Baselines/counters live in /tmp — host-scoped, reset on reboot.
- Hook source reading is forbidden during sessions when a hook blocks (token discipline rule) — this doc is the sanctioned reference.
