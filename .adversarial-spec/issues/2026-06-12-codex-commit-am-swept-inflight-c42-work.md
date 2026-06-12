# Incident: parallel `git commit -am` swept in-flight C-4-2 work into a mislabeled commit

**Date:** 2026-06-12
**Session:** adv-spec-202606110339-validation-leg-process (Phase 8)
**Severity:** hygiene (no data loss, suite green throughout)
**Related:** 2026-06-12-codex-detached-head-shared-worktree.md (same root class)

## What happened

While a Claude-orchestrated Opus subagent was implementing card C-4-2
(telegram-trust-boundary) in the shared worktree, codex committed twice on main:

- `8d2aa10` "[C-2-3] tighten check-rows oracle lint" — legitimate C-2-3 handler work
  (landed after card 5628 was already fixed @ 0440e98 and moved to Review).
- `6839aab` "[C-3-1] implement record-evidence and normalize-rows subcommands" —
  **mislabeled**: its 239-line test diff is actually the C-4-2 telegram/allowlist/sender
  test suite that the Opus agent had just written (test names
  `test_parse_reply_telegram_*`, `test_no_hardcoded_chat_or_sender_literal_in_source_tcinva4`,
  etc.). A blanket `git commit -am` swept another agent's uncommitted working-tree
  changes into codex's commit.

Remaining C-4-2 module enforcement + final test tweaks were committed as
`954bfe0` with a cross-reference note. Suite 714 green at that point.

## Why it matters

- Commit messages no longer map 1:1 to cards: card 5633 (C-4-2) evidence spans
  `6839aab` (mislabeled) + `954bfe0`; card 5629 (C-3-1) evidence cites `a0d47a5`
  but `6839aab` claims the C-3-1 title for unrelated content.
- Reviewers verifying "declared commit satisfies ACs" will be misled unless they
  read this note.

## Rule (same as detached-HEAD incident, now broader)

In a shared worktree, **never `git commit -a` / `git add -A`**. Stage explicit
paths you personally changed, and only files your card's scope declares.
Review work must be `git show`-only. If uncommitted changes you didn't write are
present, leave them alone and flag on the card.

## Status

- No loss; all content on main; suite 714 green.
- Card 5633 completion cites `954bfe0`; reviewer should also read `6839aab`'s
  test hunk.

## Addendum (same session, ~2h later): the sweep is bidirectional

Claude's commit `fc469a9` "[C-4-6] status: read-only mid-close report" swept
codex's in-flight C-4-3 failed-review fix (`last_reset_at` stamping +
EVIDENCE_STALE regression) that was sitting uncommitted in the same two files.
Explicit-path staging does NOT protect when agents share the same FILE —
`git add <file>` stages every hunk in it, theirs included.

Corrected rule: in a shared worktree, before committing run `git diff <file>`
and confirm every hunk is yours. If foreign hunks are present, use
`git add -p`-equivalent selective staging (or coordinate via board comment and
wait). Card 5634's fix evidence cites fc469a9 (mislabeled C-4-6) — reviewers:
the C-4-3 hunks are the `last_reset_at` ones.
