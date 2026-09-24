# Roadmap debate R2 — synthesis (final round; the session then left the pipeline)

Critics: `codex/gpt-6-astra` (xhigh) and `claude-cli/claude-opus-5-5`, run against roadmap v3. Neither agreed.
Raw output:
- `/home/jason/PycharmProjects/adversarial-spec.worktrees/agy-tripwire-fix/.adversarial-spec/specs/agy-tripwire-stop/roadmap/roadmap-debate-r2-codex.md`
- `/home/jason/PycharmProjects/adversarial-spec.worktrees/agy-tripwire-fix/.adversarial-spec/specs/agy-tripwire-stop/roadmap/roadmap-debate-r2-claude-cli.md`

Operator rulings come from `/home/jason/PycharmProjects/adversarial-spec.worktrees/agy-tripwire-fix/orchestration/redirect-focused-fix-2026-09-24.md`.
That redirect ends the pipeline route: there is no R3, no v4 G1, and no D0/gauntlet. The test contract is `tests-pseudo.md` v4.

| # | Finding (source) | Disposition |
|---|---|---|
| 1 | Appendices contradict v3: stale restore / `unattributed` / allowlist text (opus C1, astra 8) | Accepted. `requirements.md` scenario and feature rows were rewritten. R1 synthesis rows now carry supersession markers |
| 2 | G-1 is false: `~/.antigravity` and `~/.gemini` are writable and shared (opus C2, astra 2) | **Ruling R2-1:** both dirs are read-only real mounts. Named throwaway paths are tmpfs or empty binds. The browser profile is hidden. The oauth token is read-only until the canary (TC-11.3) |
| 3 | Deleting `stop_record` via `rm` defeats the clear (opus C3) | **Ruling R2-3:** the incident dirs are the authority. A missing record without a logged clear raises a `tamper` STOP (TC-10.3) |
| 4 | No journey for the agent that receives a STOP (opus C4) | Accepted. STOP output is machine-typed (exit 4/5) and names the evidence and the clear. It contains no retry advice (TC-9.1) |
| 5 | Host service sockets reachable through `--ro-bind` (astra 3) | **Hard requirement** (the conductor tested it). tmpfs covers `~/.config/herdr`, `/run/user/<uid>` and `/tmp`, and the env is an allowlist (`--clearenv`) (TC-12.x). Abstract-namespace sockets remain residue: `--unshare-net` would break agy |
| 6 | Siblings can read each other's dispatch roots (astra 3) | Accepted. The dispatch base is tmpfs-masked inside every sandbox, and each dispatch binds back only its own paths (TC-11.2) |
| 7 | STOP not durable when evidence or record cannot be written (astra 4) | **Ruling R2-4:** best effort, no reservation. The config and repo are read-only, so a killed dispatch cannot escape its throwaway space. A failed evidence write keeps the workspace and still raises the STOP (TC-6.4) |
| 8 | Admission race weakens the no-spawn guarantee (astra 5) | Accepted in narrowed form. Admission is re-checked at the last step before spawn (TC-4.7) |
| 9 | Transient writes invisible to the final inspection (astra 6) | **Ruling R2-2:** G-1 is narrowed to retained workspace writes plus blocked attempts visible in stderr. No watcher. Blocked attempts are logged and do not halt (TC-6.1) |
| 10 | Clear authority is only a name (astra 7) | **Ruling R2-3:** procedural plus tamper detection. The clear must name the full uncleared incident set (TC-10.1) |
| 11 | Test conflicts: probe unlink vs. no-unlink, dispatch-root removal vs. evidence retention, "nothing follows" vs. sibling inspection (astra 8) | Accepted. The probe removes only its own nonce file. The root is kept when evidence fails. Sibling inspection and quarantine are defined (TC-2.1, TC-1.2) |
| 12 | A canary with unexplained byproducts is not a pass (astra 8) | Accepted. It moves into the operator-gated canary scope |
| 13 | Integration preservation needs deletions, permissions, untracked files, and live-tree freeze (astra 9) | Deferred to the separate operator landing gate, per the redirect |
| 14 | Round when the agy seat is unavailable (opus H2) | Accepted. The round refuses before any launch, naming the seat (exit 6, TC-3.4) |
| 15 | Blocked repo-write attempts are invisible (opus H3) | Accepted. They are logged in `windows.jsonl` (TC-6.1) |
| 16 | No outcome KPIs, no latency NFR (opus H4, M2) | Deferred to the canary report: time per dispatch and false-STOP count over the first live dispatches |
| 17 | bwrap setup failure over-halts (opus M1) | **Ruling R2-5:** it is a refusal only and writes no record (TC-7.1) |
| 18 | Journey after a clear; PRD vs. technical depth (opus H1, astra 1/10) | Out of scope for the focused fix. After a clear the operator re-runs the round. No state repair is needed, because a stopped round writes no checkpoint |
