## 2026-07-30 — mirrored vocabulary (fizzy-pipeline-mcp ⟷ adversarial-spec)
Resolved: Fizzy vs fizzy-pipeline-mcp; keystone owner-repo semantics (GLOSSARY amend);
spec family (spec / system spec / spec-as-gauntleted / spec draft vN / spec record);
Brainstorm vs Debate (free-form clarification); Conductor role vs Conductor service
(GLOSSARY, replaces provisional; /conductor skill gained register-yourself step);
postponement family (exemption / deferral / residue / watchlist).
Deferred: Gauntlet definition — waits on the probe-emitter design choice (second-pass
conversion vs first-pass emission); probe/residue-production terms ride with it.
Operator caveat: definitions not memorized — correct on use, invited (in memory).
ADRs: none (terms only; keystone ownership already recorded in the contract itself).
Mechanics: mirrored sections in both CONTEXT.md files (adversarial-spec canonical,
f-p-mcp mirror); every term enrolled in vocab-rules.json under both project keys.
Transcript: ~/.claude/projects/-home-jason-PycharmProjects-fizzy-pipeline-mcp/971833fb-c243-4a24-b789-53341bbbb45d.jsonl
(Session ran in fizzy-pipeline-mcp; this repo holds the canonical vocab copies.)

Appended same day: v6 mechanics — seam (+ seam-defect reconciliation), gate vs barrier, leaf / X-node / Task disambiguation, altitude vs model effort, oracle stable-core family (oracle / oracle suite / declared oracle / acceptance criterion). Oracle production semantics remain with the gauntlet deferral.

## 2026-08-10 — carded / plan-to-Card provenance
Resolved: **Carded** means a requested change is a plan-backed Task materialized 1:1
by `pipeline_load`, carrying Session and plan provenance. A raw `add_card` card,
comment, or assignment is not carded. Phase 8 now spells out the plan amendment →
`pipeline_validate_plan` → `pipeline_load` route; fizzy-pipeline-mcp rejects an
unmanaged Task Card in an active Session.
ADRs: none (terms and workflow clarification only).
Transcript: ~/.codex/sessions/2026/08/02/rollout-2026-08-02T09-07-02-019fc2cc-b267-75c3-b287-20059423eb9a.jsonl
