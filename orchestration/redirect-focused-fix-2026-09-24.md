# Operator redirect: AGY tripwire repair leaves the pipeline (2026-09-24)

Operator: Jason, confirmed 2026-09-24. Relayed by the adversarial-spec conductor session.
This supersedes `orchestration/handoff-agy-tripwire-repair.md` where the two conflict. The handoff's other rules still apply.

## Goal

Land the AGY tripwire repair as one focused, test-first change in this worktree, with your five round-2 rulings (below) built in. Stop running pipeline ceremony: the decisions that mattered are made, and the full route cannot finish today anyway, because the gauntlet runner does not yet emit an admissible altitude manifest (`skills/adversarial-spec/phases/05-gauntlet.md` on `origin/bounded-pipeline-reform`, line 150).

## Non-Goals

- **No round-3 roadmap debate, no roadmap v4 G1 gate, no D0, no v6 leaf fan-out, no gauntlet, no finalize/execution plan.** Why: operator ruling. The handoff's acceptance line "follows the full required pipeline rather than patching source ad hoc" is withdrawn. It inflated a bounded repair into system-altitude ceremony.
- **Do not park, archive, or move Fizzy card 21616 yourself.** Ask the operator first, with the exact tool call you propose. Why: card state is the operator's act.
- **No agy dispatch of any kind, preflight included, until the operator approves the supervised canary.** Why: unchanged from the handoff.
- **No edits outside this worktree** except the socket-masking requirement's own tests and code in it. No change to model routing or `current-models.md`: the conductor handles the roster separately.

## Operator rulings on your five round-2 questions

1. **Config dirs:** do not copy them; mount both real dirs read-only. Evidence: `~/.gemini` is 3.0 GB, `~/.gemini/antigravity-cli` is 996 MB, and agy wrote nothing to `~/.gemini/tmp` or `~/.gemini/history` in the last week.
   - **Throwaway (empty tmpfs):** in `~/.gemini/antigravity-cli/`: `brain`, `conversations`, `log`, `cache`, `scratch`, `presence`, `crashes`, `annotations`, `implicit`, `knowledge` (cross-run memory: a critic must not plant into it), `history.jsonl`, `conversation_summaries.db`.
   - **Read-only:** `mcp_config.json`, `settings.json`, `builtin/`, `bin/`, `updater`; everything else in `~/.gemini`, including `GEMINI.md`, `settings.json`, `skills/`, `commands/`, `trustedFolders.json`, `oauth_creds.json`; and all of `~/.antigravity`.
   - **Hidden (tmpfs):** `~/.gemini/antigravity-browser-profile` (cookies).
   - **Auth:** `antigravity-oauth-token` stays read-only. The canary determines whether token refresh must write it; if so, write back only that file after a clean dispatch.
2. **Transient writes:** narrow G-1. It covers writes still present in the workspace at the end of the dispatch, plus blocked write attempts visible in agy's stderr. No file watcher.
3. **Clear authority:** procedural plus tamper detection. A stop record that is missing without a matching logged clear is itself a STOP. No Telegram, no TTY check. Any local mechanism can be defeated by an agent running as the operator; the goal is preventing accidental auto-continue.
4. **Interrupted dispatch:** best effort, no durable reservation. With the repo and config read-only, a killed dispatch cannot damage anything outside its throwaway space. The next process cleans leftover workspaces.
5. **bwrap setup failure:** refusal only, no durable STOP, because nothing ran. This corrects item 3 of the earlier operator redirect, which wrongly listed "bwrap setup failing" as a STOP trigger.

## New hard requirement: host sockets (tested by the conductor, 2026-09-24)

`--ro-bind / /` does not block connecting to Unix sockets. Inside the earlier sandbox a critic could run `herdr agent list`, so it could drive every Herdr pane including send-keys into shells. It could also use the SSH agent (`ssh-add -l`) and the DBus session bus (`busctl --user list`). The fix, verified to block all three:
- tmpfs over `~/.config/herdr` and `/run/user/1000`;
- unset `SSH_AUTH_SOCK` and `DBUS_SESSION_BUS_ADDRESS`;
- also unset `HERDR_SOCKET_PATH` and `HERDR_*`.

Tests: three probes that must fail inside the sandbox, each paired with the same probe succeeding unmasked. Prefer an env allowlist (`--clearenv` plus the explicit variables agy needs) over unsetting variables one by one.

## Procedure

1. Record the five rulings and the socket requirement in `requirements_summary.decisions`, `do_not_ask`, and `decisions.log`. Record "left pipeline after R2 (operator)" in the journey log. Write `roadmap/roadmap-debate-r2-synthesis.md` covering R2 findings and dispositions. Update `tests-pseudo.md` to v4; it is the authorized test contract, so handoff line 12's "tests before the pipeline authorizes" is satisfied. Remove the leftover v2 appendix material. Keep your self-listed fixes: refusal for unavailable agy seats, logging blocked repo writes, and the conflicting-test fixes.
2. Ask the operator about card 21616 (see Non-Goals). Proceed with step 3 regardless of the answer.
3. Implement test-first in this worktree on `adv-spec/agy-tripwire-stop-20260924`, with local commits only:
   - Write the offline suite first, from `tests-pseudo.md` v4, with paired negative oracles and a fake critic. Capture each failing-first run to `orchestration/logs/`.
   - New test files: the global `governance_test_gate` hook requires `pipeline_create_test`. If it refuses worktree paths, STOP and report; never bypass it. Its `live_or_induced` field must be a dict with a `kind` key, and keep lines ≤120 characters.
   - Run pytest with output redirected to a file, never piped to `head` or `tail`.
4. Get one independent code review: `codex exec -m gpt-6-astra -c model_reasoning_effort=xhigh`, read-only, over the diff and suite. Fix accepted findings and record the dispositions.
5. Stop and report. The landing gate onto the dirty live tree and the supervised canary are separate operator approvals.

## Acceptance

- Suite green offline. The failing-first logs exist. Every positive case has a paired negative case that fails when the behaviour is removed.
- The socket probes pass: blocked in the sandbox, reachable unmasked.
- The codex review report and its dispositions are in `orchestration/`.
- Nothing pushed or merged. No agy dispatch. Card 21616 untouched unless the operator approved a specific call.
- Final report at `orchestration/report-agy-tripwire-repair.md`, ≤60 lines, with full file paths.
