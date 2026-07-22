# A-5 Component Mini-Spec

Title: Phase-doc spine units + 09-verification relocation

Decompose phase docs into phases/<NN>-<phase>/spine.md + reference/*.md with single-owner pointers; relocate phases/09-verification.md under the Phase 8 tree with spine-step ownership + SKILL.md router update + decisions-log entries; architecture_refs resolver writing per-step context-load-manifest.

Acceptance criteria:
- doclint pointer closure: zero dangling, exactly one owner
- 09-verification.md gone from old path; router resolves (TC-4.x/5.x)
- context-load-manifest records resolved unit identities + hashes

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task A-5.
Implementation status: partial — flat phase docs exist; 0 spine files (verified); restructure + resolver new
