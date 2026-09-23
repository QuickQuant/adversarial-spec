# Finalize (Phase 6)

Enter after the pipeline has recorded successful `pipeline_finalize_debate_round`, with the completed round's convergence and altitude floor satisfied, and required gauntlet/reconciliation gates complete. An agreement marker alone is not the gate. If debate remains open, use [Phase 3](03-debate.md) to close it in the legal lane with explicit `board_id`; never patch convergence state.

Use a local milestone worklist:

```text
TodoWrite([
  {content: "Verify quality and promote test intent", status: "in_progress", activeForm: "Preparing final artifacts"},
  {content: "Run final CONS/SCOPE/TRACE/CANON/TCOV [GATE]", status: "pending", activeForm: "Checking final artifacts"},
  {content: "Write final document and artifact paths", status: "pending", activeForm: "Saving final artifacts"},
  {content: "Obtain user review and acceptance [GATE]", status: "pending", activeForm: "Awaiting user review"},
  {content: "Record approval and execution handoff", status: "pending", activeForm: "Recording finalization"},
])
```

## Quality and Test Promotion

Require substantive sections, consistent terminology, unambiguous claims and actionable instructions. Use [reference/document-types.md](../reference/document-types.md) for document structure.

| Document/depth | Check |
|---|---|
| Product spec | Executive summary, personas with goals/pain points, user stories with benefits, measurable success targets, explicit in/out scope |
| Technical/full spec | Components/interactions; endpoint request/response/error contracts; field types/constraints/indexes/relations; security boundaries; measurable performance targets; Getting Started; story and semantic test coverage |
| Debug investigation | Evidence before hypotheses; simple explanations ruled out; proven root-cause mechanism; proportional fix; concrete verification and prevention steps |

When `tests_pseudo_path` exists:

1. Read the refined `tests-pseudo.md` and validate schema references against actual source/type definitions.
2. Write `tests-spec.md` in the active spec directory with concrete field names, validated references and complete error cases.
3. Require every user story to map to at least one test and every test to a story; resolve uncovered stories and orphan tests.
4. Require falsifying oracles for formulas, parameter causality, payload meanings, UI/display claims, state changes and negative/counterfactual paths, or an explicit approved deferral. Field-presence, HTTP 200, non-null and range-only checks remain supplemental smoke coverage.
5. Retain `tests-pseudo.md` as the audit trail and set `tests_spec_path` in active detail. Include the promoted tests in the final guardrail bundle.

## Final Guardrail Delta

Run **CONS, SCOPE, TRACE, CANON, TCOV** with `action="finalize"`. See [03-debate.md — Checkpoint Guardrails](03-debate.md#checkpoint-guardrails-after-each-round-incorporation) for the shared five-call payload, independent dispatch, retry, result and remediation mechanics. Prompts have one editable source: [adversaries.py](../scripts/adversaries.py); seats come from [current-models.md](../reference/current-models.md).

Finalization adds these blocking conditions:

- **CONS:** Any unresolved finding, including warning severity, blocks finalize (`GuardrailAggregate.outcome` in `guardrail_orchestration.py`). Include ownership-baseline/live A/B differences when those matrices exist; unresolved ownership differences count. Fix and rerun. An explicit operator override requires a written process-failure note; never silently warn and continue.
- **SCOPE boundary bundle:** Supply approved requirements, subject project/repository, allowed write roots, authoritative session/card, external dependencies, linked sibling sessions/cards, and out-of-boundary work performed or proposed since the prior round. `SCOPE INPUT GAP` blocks until evidence is supplied, external work is transferred to its linked owner, or an explicit operator override with a process-failure note is recorded.
- **Test scope and adequacy:** Tests cannot introduce behavior outside approved requirements. Run TCOV on the final tests; weak or missing oracles require correction or explicit user-approved deferral of the uncovered claim. Include every affected user-facing parameter, metric, display label, state and formula.

Fix CANON drift or document an approved migration; restore TRACE coverage or obtain explicit descoping approval; present SCOPE additions for approval/removal. A failed reviewer call is never a pass. CONS failure stops; SCOPE/TRACE unavailability needs explicit user approval; CANON is blocking before execution when owner excerpts exist; TCOV is blocking when test artifacts exist. Retry or switch to an independent current seat as the shared contract permits. Re-run affected checks after later edits.

## Final Artifacts

Write the complete document to the active spec directory using the appropriate filename: `spec-output.md` or `debug-output.md`. Present its actual path, document type, rounds/cycles, participating reviewers and key refinements. Do not announce finalization success while guardrails remain unresolved.

Record `spec_path`, `tests_spec_path` when produced, `manifest_path` when a manifest exists, and `gauntlet_concerns_path` when gauntlet ran. Preserve architecture and reviewed-spec evidence links. Keep `current_phase: finalize` with the pending user-review step until accepted; record the finalized-artifact event.

See SKILL.md § [Journey Log](../SKILL.md).

See SKILL.md § [Decisions Log](../SKILL.md).

## User Review

Present the actual final artifact path and document type with three choices:

1. **Accept as-is.** Record acceptance; offer Phase 7 execution planning.
2. **Request changes.** Apply changes, show affected sections, update artifacts and rerun affected checks before presenting again.
3. **Another review cycle.** Use the current document and Phase 3's tracked rounds; select seats through current-models, track cycle count separately from rounds, then return through final checks and user review.

If materializable middleware candidates exist, explain that the optional middleware-creator pass follows Phase 7's validated, approved and loaded source task cards. Do not create implementation cards during finalization.

Only after acceptance and the user's direction to proceed, follow the active card's legal transition. When advancement is due, call `pipeline_advance(session_id=SESSION_ID, card_id=CARD_ID, agent=AGENT, board_id=BOARD_ID)`. A gate rejection stays blocked; never use `pipeline_patch_state` to bypass it.

See SKILL.md § [Fizzy Card Comment Convention](../SKILL.md).

See SKILL.md § [Phase Transition Protocol](../SKILL.md).
