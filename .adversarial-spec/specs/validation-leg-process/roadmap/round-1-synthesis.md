# Roadmap Debate Round 1 — Synthesis

> 2026-06-11. Models: codex/gpt-5.5 (returned), gemini-cli/gemini-3.5-flash-preview
> (FAILED 3/3: ENETUNREACH then ModelNotFoundError 404 — see infra note).
> Raw critiques: `.adversarial-spec-checkpoints/adv-spec-202606110339-validation-leg-process-round-1-critiques.json`.
> Claude participated as critic (T1/T2 tensions were Claude-raised, posed as focus questions).

## Accepted (applied to manifest + overview + tests-pseudo)

1. **CRITICAL — N/A vs coverage gate (codex):** the close gate requires every
   `US-\d+` in ConOps to appear in ≥1 PASSING row; N/A satisfies nothing.
   → US-7 reworded: N/A is row-level only; story removal = ConOps edit +
   re-hash. New TC-3.6.
2. **CRITICAL — T1 refresh rule (codex proposal adopted):** new US-12 (M2):
   refresh only before final judgment or after approved remediation/scope
   decision; enumerated allowed/disallowed reasons; superseded-row audit
   section (reason/approver/timestamp/replacement-id). New G5, TC-2.5.
3. **MAJOR — T2 boundary (codex):** new NG5 — no row may use verification-test
   success as its oracle; dogfood validation evidence = live process artifacts
   + Jason judgments, never the pytest layer.
4. **MINOR — dependencies (codex):** dependencies array added to manifest.

## Accepted in spirit, deferred to spec drafting (Phase 3)

5. **MAJOR — Jason's validator journey under-specified:** the digest→judgment→
   remediation journey gets its own spec section; roadmap M3 criteria already
   imply it. Carry as spec-section requirement, not a new story.
6. **MAJOR — measurability:** self-check parity "100% of documented invalid
   classes" (TC-3.3 already encodes), multi-part digest fallback rule to be
   specified in the spec's digest section.

## Rejected / no action

- Codex's renumbering of stories (their US-8/US-11 shuffle): our ids are
  load-bearing (future ConOps coverage regex) — kept stable, refresh rule
  appended as US-12.

## Round 1b (gemini-cli/gemini-3.1-pro-preview, after Jason fixed CLI auth)

**Accepted:**
7. **CRITICAL — missing execution step (gemini):** M2 drafts rows, M3 digested
   them — nobody executed the scenarios. New US-13 (M3): execute each scenario
   per its evidence_type and compile a per-row evidence artifact BEFORE digest
   assembly; missing evidence blocks the digest. New TC-3.7.
8. **US-12 hindsight hole (gemini):** "approved remediation/scope decision"
   could be agent-self-approved. Now HUMAN-APPROVED explicitly; an agent may
   never approve its own scope reduction.
9. **US-5 rename (gemini):** live-walkthrough → agent-walkthrough-transcript;
   the agent walks, Jason reviews async — removes the G3 conflict reading.

**Rejected — contradicts served code:**
10. **"Empty-set trap" in anti-relabeling (gemini):** claimed empty validation
    test_targets would be a strict subset and reject. VERIFIED FALSE against
    fizzy pipeline.py (~:9226): the guard is
    `if verification_targets and validation_targets and validation_targets < verification_targets`
    — an empty validation set short-circuits and PASSES; code comment confirms
    intent. No criterion added on a wrong premise. Carry to the fizzy handoff
    retro: confirm the empty-set pass is intentional and stays.
    (Gemini's [SPEC] rewrite also silently dropped TC-2.5 and renumbered
    TC-3.6 — manifest remains source of truth, ids stable.)

## Infra note

gemini-cli/gemini-3.5-flash-preview failed all 3 attempts: first ENETUNREACH
(network), then ModelNotFoundError 404 twice. If 404 persists on next
dispatch, suspect model-id regression in the CLI — verify with Jason before
changing deprecated_models guidance.
