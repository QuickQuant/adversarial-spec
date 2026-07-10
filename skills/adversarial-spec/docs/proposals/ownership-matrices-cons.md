# Ownership matrices + CONS finalize-gate

**Status:** APPROVED option (a) — operator decision 2026-07-10 (Jason, via
prediction-prime report widget `q-20260709-two-matrix-ownership`, comment
confirming this is skill-level scope). Core mechanism implemented same day;
mapcodebase baseline writer is the open follow-up (below).

## Incident this fixes

`exit_preview_records` (trade-centric-portfolio-view, 2026-07): the table was
homed in BOTH Convex (§10.5) and gateway SQLite (§18a) from spec v3 through
v4-finalize. CONS ran twice and missed it — the persona had no ownership
category, and even a catch would have been `severity=warning` at every
checkpoint including the last one, because only `action="gauntlet"` blocked.
A contradiction could survive to finalize BY DESIGN.

Two independent fixes, both adopted:

1. **CONS persona patch** (landed 2026-07-09, `adversaries.py`): category 7
   SINGLE OWNER/HOME, structural-placement-is-a-claim exclusion amendment,
   ENTITIES CHECKED tabulation forcing function. Catches *internal*
   contradictions probabilistically.
2. **This proposal**: matrices (catch consistent-but-wrong ownership and
   cross-round drift that in-document reading can't) + the finalize hard gate
   (close the last-round escape hatch).

## Design

**Two files per session**, under `.adversarial-spec/specs/<slug>/`:

- `ownership-baseline.md` — written ONLY by mapcodebase, ≤40 rows. One row per
  owned entity: `entity | kind (table/endpoint/store/config) | home component |
  source anchor`. Ground truth from code, not from the spec.
- `ownership-live.md` — starts as a copy of baseline; amended every debate
  round with a provenance note for each entity the round's spec version
  introduces or re-homes: `entity | claimed home | spec section | round |
  rationale (1 line)`.

**Per-round step** (03-debate.md invocation contract, item 2): amend live,
compute the deterministic baseline↔live A/B diff, include it in the CONS
payload. Findings: (a) one entity with two homes anywhere in live; (b) live
home ≠ baseline home with no provenance note. Mid-debate severity: warning —
the existing fix-next-round workflow is preserved (this was Jason's explicit
question and the load-bearing nuance of option a).

**Finalize gate** (06-finalize.md + `guardrail_orchestration.py`): the final
guardrail pass runs `action="finalize"`. `GuardrailAggregate.outcome` blocks
when any CONS finding is present regardless of severity, and ORCH synthesis is
fail-closed (a dead CONS subagent at finalize = blocking). Implemented
2026-07-10 with tests (`tests/test_guardrail_orchestration.py`: finalize
blocks warning-severity CONS; non-CONS warning does not block; CONS subagent
failure fail-closed; critique behavior unchanged).

## Acceptance test

Frozen trade-centric-portfolio-view spec v4 + its ownership files must produce
the blocking finding at a simulated finalize pass (the incident regression).
The 2026-07-09 persona-patch regression already catches 3 known escapes at the
persona level; this adds the gate-level assertion.

## Open follow-ups

- **mapcodebase baseline writer**: mapcodebase (skill v3.9) does not yet emit
  `ownership-baseline.md`. Until it does, sessions can hand-author the baseline
  from `.architecture/structured/components/` tables (keep ≤40 rows, cite
  anchors). Wire into mapcodebase on its next revision.
- **debate.py wiring**: `GuardrailOrchestrator` is not yet imported by
  `debate.py` (guardrails currently dispatch per the 03-debate.md prose
  contract). When debate.py adopts the module, pass `action="finalize"` from
  the finalize path.
