# Roadmap debate R1 — synthesis

> **Superseded in part.** The G1 redirect (bwrap) and R2 rulings replace rows 1, 2, 3 (restore), 11, 12 (restore/reservation), 13 and 15.
> Current dispositions live in `roadmap-debate-r2-synthesis.md` and `tests-pseudo.md` v4.

Critics: `codex/gpt-6-astra` (xhigh) and `claude-cli/claude-fable-5-1`. Raw output: `roadmap-debate-r1.json`, `roadmap-debate-r1-{codex,claude-cli}.md`.
Neither critic agreed; the author seat (Claude) accepted the findings listed below. There was also an aborted first attempt
(`roadmap-debate-r1-aborted-opus-relcwd.*`). That attempt put Opus in a critic seat, which is banned, and passed a relative
`--cwd`, which codex then resolved a second time. It produced no critique and none was used.

| # | Finding (source) | Disposition |
|---|---|---|
| 1 ~~superseded~~ | Routine writers such as hooks and session-state make a fail-closed halt fire on every round (fable C1) | **Operator ruling:** a per-repo exact-path allowlist. Changes to allowlisted paths are recorded but do not halt. Tool-owned outputs are hash-verified, so bytes the tool did not write count as an ordinary delta (US-5, TC-5.4, TC-5.5) |
| 2 ~~superseded~~ | Unattributed halt vs durable record is ambiguous (fable C2) | **Operator ruling U-7:** every STOP, attributed or not, writes the durable record. G-2, T4 and TC-5.0 updated |
| 3 | The operator journey ends at the STOP, and there is no clear act and no restore oracle (fable C3, astra 1) | Accepted: added US-9 (inspect evidence, restore) and US-10 (explicit clear), TC-9.0 (restore round-trip) and TC-10.x |
| 4 | "Per watched repo" is undefined for worktrees (fable C4) | **Operator ruling U-8:** the record lives in the git common dir. TC-4.1 gains a worktree variant, TC-4.6 |
| 5 | A test has two outcomes, TC-2.1 (fable H) | **Operator ruling U-4:** let the sibling finish, check it, quarantine its output. TC-2.1 is now single-outcome |
| 6 | The 5-minute budget conflicts with the timeout tests (fable H) | Accepted: an injectable dispatch timeout and retry delay are now M0 success criteria |
| 7 | Nothing proves independence from string matching (fable H) | Accepted: added TC-1.4, which randomises the STOP message |
| 8 | Persona coverage: the co-tenant session owner (fable M) | Accepted: added persona; the refusal must name the record and the incident (TC-4.0) |
| 9 | No Risks section and no post-repair endpoint (fable M, astra 8) | Accepted: added Risks, and made the post-landing supervised canary a named handoff with U-1 as residue |
| 10 | Integrations count (fable L) | Accepted: the agy CLI counts as an external integration, so the score is 16 and the tier stays complex |
| 11 ~~superseded~~ | Restoring on location alone is unsafe; exclusive ownership is required (astra 2) | Accepted: restore happens only inside a surface created exclusively for that dispatch (TC-6.4) |
| 12 | Races (check vs spawn), evidence-write failure, failed restore, interrupted persistence (astra 3) | Accepted: added TC-4.7 (admission race), TC-6.5 (evidence write fails → no restore, still STOP), TC-6.6 (failed restore still STOPs) |
| 13 ~~superseded~~ | Exact tool paths can hide mutations (astra 4) | Accepted: tool-owned outputs are content-hash verified (TC-5.4) |
| 14 | Offline proof is not live compatibility (astra 5) | Accepted: U-1 is a named release limitation, and the first live dispatch after landing is a supervised canary behind operator approval (US-8, TC-8.2) |
| 15 | Integration approval can go stale (astra 6) | Accepted: the gate binds candidate diff hash + live snapshot hash, and drift invalidates it (TC-8.2). Hunk preservation is defined by content |
| 16 | Network isolation, static gate proof, underspecified variants (astra 7) | Accepted: the network-deny run is optional-but-recorded (TC-0.2). TC-8.1 is now behavioural (the apply step refuses without a matching approval). Variants gained setup lines |
| 17 | Wants a product PRD rather than a technical roadmap (astra 8) | Partially accepted: added operator journey, personas and risks. Depth stays `technical` per the session doc depth, and the pseudocode stays in the companion tests-pseudo |
