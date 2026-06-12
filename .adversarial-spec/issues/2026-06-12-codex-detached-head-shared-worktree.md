# Codex detached-HEAD reviews in the shared worktree (2026-06-12)

**Severity:** high (near-miss data loss; zero actual loss)
**Phase:** 8 (implementation), Wave 0 → Wave 1 boundary

## What happened
Codex reviewed the Wave-0 commits by running `git checkout <hash>` for each commit
(a93f622 → 6de349f → 8ad1ee2) **in the shared worktree**, detaching HEAD. It then
committed 6 fix/feature commits (27cf670, 155c26d, 553b77b, c43584d, 0b557c8) onto
the detached HEAD and was mid-edit on C-2-2 normalize-rows when Jason stopped it.

Meanwhile claude's commit 3146ba4 (session state, checkpoints, C-* spec dirs,
execution-plan, payload-guard hook) sat on `main` — invisible to codex's chain, and
the detached checkout reverted all session artifacts on disk to their pre-3146ba4
state. The two agents were effectively on divergent histories in one working tree.

## Blast radius
- No commits lost: `main` still pointed at 3146ba4; everything else was reachable.
- Codex's uncommitted C-2-2 WIP (~550 lines) snapshotted as 7334cb6.
- `.mcp.json` (live Fizzy token) was briefly captured by the WIP `git add -A`
  (the gitignore entry lived only in 3146ba4) — amended out before merge; never pushed.
- Board state stayed coherent (codex used pipeline tools for reviews/completes);
  recorded commit hashes preserved by merging instead of rebasing.
- One latent red test from codex's C-2-3 (invalid fixture row expected draft-mode
  exit 0; draft relaxes coverage only) — fixed in 6ddf719.

## Resolution
1. Safety branch at the detached tip; WIP committed as 7334cb6 (token amended out).
2. `git merge codex-wave0-work` into main (99e0c76); single conflict
   (.claude/session-activity.jsonl, append-only) union-merged.
3. Full suite green after test fix: 640 passed.
4. Stale branches `codex-detached-rescue` / `codex-wave0-work` left for manual
   deletion (branch-delete is hook-gated).

## Root cause
Reviewing by `git checkout <hash>` is a single-agent habit applied to a
**shared worktree**. Review must be worktree-neutral: `git show <hash>`,
`git diff <a>..<b>`, `git log -p`. Nothing in the protocol or hooks blocked the
checkout.

## Prevention candidates (for backlog / protocol doc)
- 08-implementation.md review recipe: state explicitly — NEVER `git checkout` a
  hash/branch in the shared worktree; review with `git show`/`git diff` only.
- Hook candidate: destructive_git_gate already exists — extend to block
  `git checkout <commit-ish>` when `.conductor/agents/` shows >1 registered agent.
- Worker bootstrap prompt (codex/gemini) should carry the same rule.
