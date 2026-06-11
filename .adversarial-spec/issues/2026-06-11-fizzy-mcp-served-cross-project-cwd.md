# Process failure: fizzy MCP served cross-project — local-session ops hit the wrong repo

**Date:** 2026-06-11
**Session:** adv-spec-202606110339-validation-leg-process (card 5604)
**Severity:** medium (caught immediately; one file clobbered and restored)

## What happened

`pipeline_advance` (roadmap→debate, card 5604) failed with
`LOCAL_SESSION_MISMATCH: Local active_session_id 'adv-spec-202606041400-depth-triage-v4-wave1'`.
A follow-up `pipeline_sync_local_session(mode=repair)` "fixed" the mismatch by
**overwriting `/home/jason/PycharmProjects/fizzy-pipeline-mcp/.adversarial-spec/session-state.json`**
— the fizzy repo's own active-session pointer — and dropping two of this
session's detail/journey files into that repo's sessions/ directory.

## Root cause

adversarial-spec had **no per-project `.mcp.json`**, so the session used the
GLOBAL `~/.claude.json` fizzy registration:
`uv run --directory /home/jason/PycharmProjects/fizzy-pipeline-mcp fizzy-mcp serve`
(+ `FIZZY_BOARD_ID` = the Brainquarters board, `PROJECT_KEY=BQ`).
`--directory` sets the server cwd to the fizzy repo, and fizzy resolves ALL
local-session state from `Path.cwd()` (`pipeline.py:10196`, `:10220`). Card
operations were safe only because explicit `board_id` was passed per CLAUDE.md
guardrail; anything touching local session files targeted the wrong repo.

## Remediation (same session)

1. Restored `fizzy-pipeline-mcp/.adversarial-spec/session-state.json` from its
   HEAD (`git checkout --`); removed the two misplaced session files.
2. Created `adversarial-spec/.mcp.json` following the canonical per-project
   pattern (davetrade/ETB): `uv run --project <fizzy repo> fizzy-mcp` (cwd
   inherits the project) + `FIZZY_BOARD_ID=03fw5alxw15iqwh6hq15vfdsb`,
   `PROJECT_KEY=adversarial-spec`.
3. Requires Claude Code session restart (or /mcp reconnect) to take effect —
   until then, NO fizzy local-session tools; card-only ops (comments) are safe
   with explicit board_id.

## Prevention

- `initialize-fizzy` already creates per-project configs; this project predates
  that convention and was never backfilled. Backfill check candidates: any
  project using fizzy without its own `.mcp.json`.
- Fizzy-side hardening suggestion (handoff): `sync_local_session` and
  `_validate_local_session_create_allowed` could compare PROJECT_KEY against
  the pointer's project, or refuse when cwd == the fizzy repo itself.
