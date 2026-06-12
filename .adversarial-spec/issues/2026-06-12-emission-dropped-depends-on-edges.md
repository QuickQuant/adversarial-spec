---
would_have_used: pipeline_reload_plan (upsert task metadata from a corrected fizzy-plan.json without recreating cards)
severity: high
discovered: 2026-06-12 (Phase 8 first pickup)
session: adv-spec-202606110339-validation-leg-process
---

# Emission dropped 18 of 19 depends_on edges — board offered C-4-4 before SS-1 existed

## What broke

The 2026-06-11 Step-9b emission lost nearly all scheduling edges from the
Gate-V4-approved execution plan. `fizzy-plan.json` (plan_hash `59fa826f0409f56a`)
carried exactly one edge (C-4-5 → C-4-4); the loaded cards 5616–5640 therefore
showed 18 components ready-parallel, and `pipeline_do_next_task` correctly computed
the only remaining chain (C-4-4 → C-4-5) as the critical path and handed out
**C-4-4 emit-system-validation as the first card** — a feature component that cannot
be built before the SS-1 ledger-core foundation (C-1.1–C-1.4) exists.

## Root cause (proven, three layers)

1. **Plan encoding:** `execution-plan.md` expressed the Wave-0 and SS-5 edges as a
   prose paragraph (line 72), not per-node fields. Only C-4.5 (`depends_on: C-4.4`)
   and C-5.3 (`depends_on: (all)`) had machine-readable fields.
2. **Driver fail-silent:** `orchestration/emit_driver.py` parses `depends_on:` only
   from per-node `- altitude:` lines AND explicitly skipped the `(all)` sentinel
   without expansion or warning (`if dep_text and dep_text != "(all)"`).
3. **No fidelity gate:** `self_check_plan`, the live-contract shim, and
   `pipeline_validate_plan` all treat `depends_on` as optional — 3 validate rounds
   passed a plan missing 18 approved edges.

## Resolution (this incident — RESOLVED 2026-06-12)

- Edges encoded per-node in `execution-plan.md` (same semantics Jason approved at
  Gate V4 — no scope change); driver fixed to expand `(all)`, emit
  `DEPENDS_ON_UNPARSEABLE` on unparseable dep text, and stamp `tested_by`
  (previously a separate post-step, `add_tested_by.py` — second silent seam in
  the same chain). Plan regenerated; per-node artifact hashes unchanged.
- `pipeline_patch_state` correctly refuses `depends_on` (in `_ALTITUDE_PROTECTED`,
  pipeline.py ~7708): schedule/critical_path/plan_hash are derived from it at
  load, so an ad-hoc edit would silently invalidate the stored schedule. The
  bookkeeper's earlier conclusion that no tool can fix this was WRONG — the
  sanctioned path is re-running `pipeline_load`, which dedups by task_id and has
  an explicit repair pass that re-resolves and rewrites deps on existing cards.
- Re-load executed: 0 created / 25 matched / 19 repaired
  (plan_hash `sha256:5f7893a24fa8d0cd`), schedule re-derived —
  waves `[C-1-1..C-1-4] → [11 features] → [C-4-5] → [C-5-1,C-5-2] → [C-5-3]`,
  critical path `C-1-1 → C-4-4 → C-4-5 → C-5-1 → C-5-3`.

## Permanent fix planned

- Per-node `depends_on:` is now the normative encoding in the plan doc (prose
  paragraph annotated as non-machine-read).
- Backlog (extends the existing self_check ⊂ validate ⊂ load parity-gap item from
  2026-06-11): (a) edge-fidelity check — `pipeline_validate_plan` should expose
  the parsed edge count so Gate V3 can assert it against the approved plan;
  (b) close the validate/load asymmetry on `tested_by`
  (MISSING_OR_INVALID_TESTED_BY is load-only — validate passed a plan load
  rejected, again).
- NO new tool needed for dep repair (`pipeline_set_depends_on` withdrawn) —
  re-`pipeline_load` is the designed mechanism and works. Skill-doc follow-up:
  document re-load-as-repair in 07/08 phase docs so the next agent doesn't
  reach for patch_state.
