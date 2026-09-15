---
date: 2026-09-15
session: adv-spec-202609150549-bounded-reform-hardening-align
card: 21560 (impl, fanout c-tmr-contract-fanout-1)
phase: debate (v6 fan-out, probe leaf C-TMR-CONTRACT)
would_have_used: candidate dispatch wrapper that stages the prompt inside the worktree and treats exit 0 + empty output + clean worktree as DISPATCH_NO_OP, not success
severity: medium
---

# agy headless run exited 0 with no output and no files

## What broke
The first antigravity candidate dispatch (`agy --print` with `--add-dir` for the keystone and packet
schemas) returned exit 0, wrote 0 bytes to stdout and stderr, and left the worktree untouched. A
naive driver would have recorded a completed candidate with no implementation.

## Mechanism
The prompt told agy to read its instructions from a file in the conductor's scratchpad
(`/tmp/claude-1000/.../cand-prompt.md`), which is outside agy's workspace and its added directories.
The read was denied and the run ended silently. Two smoke tests isolated it: a short prompt with the
same flags and timeout printed `OK`; only the out-of-workspace file read produced the silent exit.

## Workaround
Prompt file copied into the worktree (`C-TMR-CONTRACT/CANDIDATE-PROMPT.md`) and the dispatch relaunched.

## Permanent fix
A dispatch wrapper for candidate seats: stage prompt + suite inside the worktree; classify
`exit 0 ∧ empty output ∧ clean worktree` as `DISPATCH_NO_OP`; record the receipt on the impl card.
Carded post-finalize as a W-task (US-13 recovery: missing evidence must never read as a pass).

## Follow-up (same day)
Second and third dispatches, with the prompt inside the workspace, also produced no output:
`jetski: no output produced — a tool required the "command" permission ...` and then, with shell
forbidden in the prompt, `... required the "write_file" permission ...`. Headless agy auto-denies
every permissioned tool and aborts on the first denial. `--dangerously-skip-permissions` is
forbidden by operator rule (2026-07-20). No `permissions.allow` settings file exists yet
(`~/.antigravity/` holds only `argv.json` and extensions), so a scoped allow-rule would be a new
config file — an operator decision, not taken here.

Bounded workaround used for the probe: the seat runs read-only and PRINTS its implementation as a
unified diff; the conductor applies it on the seat's own branch and commits with attribution. The
seat's design independence is preserved; its ability to run the suite is not (the conductor runs
it, same as for every candidate — E.4).

Decision for Jason: approve a scoped `permissions.allow` for candidate seats (write_file + command
limited to the worktree root), or accept print-only candidates for agy going forward.
