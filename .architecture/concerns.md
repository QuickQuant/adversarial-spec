# Actionable Concerns: adversarial-spec

> Refreshed 2026-06-11 (incremental, git f198887). Fix-first rollup over hazards, patterns, and findings.

## Top 3
1. **CON-001** Triple litellm completion() pathway — one low-level wrapper ends silent default divergence.
2. **CON-002** Finish the token_tracking move — extraction landed; phases still import the global singleton.
3. **CON-009** prompts.py shadow collision — renamed module or proper packaging; it already bit a live session (2026-06-11).

## Priority: next
### CON-001: Triple litellm completion() pathway
- **Severity:** warning | **Component:** model-dispatch | **Confidence:** high
- **Why:** 3 files call litellm.completion() with silently divergent defaults
- **Do:** Create single _call_litellm() wrapper in model_dispatch.py
- **Files:** skills/adversarial-spec/scripts/models.py, skills/adversarial-spec/scripts/gauntlet/model_dispatch.py, skills/adversarial-spec/scripts/debate.py
- **Sources:** FIND-001, FIND-014

### CON-002: cost_tracker coupling forces 30+ test monkeypatches
- **Severity:** warning | **Component:** gauntlet-pipeline | **Confidence:** high
- **Why:** token_tracking extraction landed (half the fix); phases still import the global singleton, keeping the layer coupling and test monkeypatching burden.
- **Do:** Move tracking into model_dispatch.call_model(); phases stop importing the singleton.
- **Files:** skills/adversarial-spec/scripts/gauntlet/model_dispatch.py, skills/adversarial-spec/scripts/models.py
- **Sources:** FIND-006

### CON-003: orchestrator run_gauntlet() is ~695 lines
- **Severity:** warning | **Component:** gauntlet-pipeline | **Confidence:** high
- **Why:** Single function mixes phase orchestration with checkpoint/manifest/medal/stats logic
- **Do:** Extract phase-table pattern
- **Files:** skills/adversarial-spec/scripts/gauntlet/orchestrator.py
- **Sources:** FIND-011

### CON-007: Divergent CLI surfaces drift independently
- **Severity:** warning | **Component:** debate-engine | **Confidence:** high
- **Why:** Two CLIs drive run_gauntlet with different flag names and timeout defaults; config changes (like the 1200s bump) land on one surface only.
- **Do:** Shared defaults constants + flag aliases between debate.py and gauntlet/cli.py.
- **Files:** skills/adversarial-spec/scripts/debate.py, skills/adversarial-spec/scripts/gauntlet/cli.py
- **Sources:** FIND-017, divergent-cli-flag-surfaces

### CON-008: Same-role workers can drop conductor dispatch messages
- **Severity:** warning | **Component:** harness-hooks | **Confidence:** medium
- **Why:** dispatch_check baselines are shared per (project, role) in /tmp; parallel same-role workers race and one silently misses messages.
- **Do:** Key the baseline by session id (or per-worker offset file).
- **Files:** .claude/hooks/dispatch_check.py
- **Sources:** HAZ-005, FIND-018

### CON-009: prompts.py shadow collision bites standalone loaders
- **Severity:** warning | **Component:** gauntlet | **Confidence:** high
- **Why:** sys.path-based shadowing of prompts.py by gauntlet/prompts.py forces importlib workarounds (hit live on 2026-06-11) and is a packaging landmine.
- **Do:** Rename gauntlet/prompts.py or eliminate sys.path insertion (proper package imports).
- **Files:** skills/adversarial-spec/scripts/gauntlet/prompts.py, skills/adversarial-spec/scripts/prompts.py
- **Sources:** FIND-016, sys-path-insertion-in-scripts

## Priority: later
### CON-004: Dead code accumulation (~750 lines)
- **Severity:** warning | **Component:** infrastructure | **Confidence:** high
- **Why:** Shrunk by deletions (scope.py, gauntlet_monolith.py gone). Remaining: possible clustering remnant in phase_3_filtering.py (re-verify) and ~80 lines of deprecated CLI commands.
- **Do:** Delete in single cleanup commit
- **Files:** skills/adversarial-spec/scripts/gauntlet/phase_3_filtering.py, skills/adversarial-spec/scripts/debate.py
- **Sources:** FIND-002, FIND-003, FIND-004, FIND-010

### CON-005: Inline prompts in phases 5 and 7 undermine centralization
- **Severity:** warning | **Component:** gauntlet-pipeline | **Confidence:** high
- **Why:** gauntlet/prompts.py was created but phases 5-7 still use inline prompts
- **Do:** Extract to gauntlet/prompts.py
- **Files:** skills/adversarial-spec/scripts/gauntlet/phase_5_rebuttals.py, skills/adversarial-spec/scripts/gauntlet/phase_7_final_boss.py, skills/adversarial-spec/scripts/gauntlet/prompts.py
- **Sources:** FIND-005

### CON-006: sys.path manipulation prevents proper packaging
- **Severity:** warning | **Component:** infrastructure | **Confidence:** high
- **Why:** 6 files use sys.path.insert instead of proper package structure
- **Do:** Configure pyproject.toml packages, use relative imports
- **Files:** skills/adversarial-spec/scripts/debate.py, skills/adversarial-spec/scripts/pre_gauntlet/orchestrator.py
- **Sources:** FIND-007
