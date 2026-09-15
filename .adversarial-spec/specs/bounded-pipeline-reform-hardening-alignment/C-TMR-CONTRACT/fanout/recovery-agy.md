# Recovery note — candidate worktree (agy)

- worktree: /home/jason/PycharmProjects/adversarial-spec.worktrees/c-tmr-contract-cand-agy
- branch: adv-spec/c-tmr-contract-cand-agy
- frozen candidate commit: 687b42936faaf98b5add163f7d8b8a9a455c417e
- base: b544a00 (bounded-pipeline-reform)
- custody rows: CUST-CTMR-AGY-BRANCH, CUST-CTMR-AGY-WORKTREE in ../custody-ledger.jsonl
- recovery: `git worktree add <path> adv-spec/c-tmr-contract-cand-agy` or `git show 687b42936faaf98b5add163f7d8b8a9a455c417e:<path>`; the branch is the durable authority, the worktree is disposable after synthesis.
