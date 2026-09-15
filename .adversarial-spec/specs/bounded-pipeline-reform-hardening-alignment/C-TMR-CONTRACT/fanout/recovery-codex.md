# Recovery note — candidate worktree (codex)

- worktree: /home/jason/PycharmProjects/adversarial-spec.worktrees/c-tmr-contract-cand-codex
- branch: adv-spec/c-tmr-contract-cand-codex
- frozen candidate commit: 7a29ceccc5feee9fe0af4ff2f20800dbaf9b8953
- base: b544a00 (bounded-pipeline-reform)
- custody rows: CUST-CTMR-CODEX-BRANCH, CUST-CTMR-CODEX-WORKTREE in ../custody-ledger.jsonl
- recovery: `git worktree add <path> adv-spec/c-tmr-contract-cand-codex` or `git show 7a29ceccc5feee9fe0af4ff2f20800dbaf9b8953:<path>`; the branch is the durable authority, the worktree is disposable after synthesis.
