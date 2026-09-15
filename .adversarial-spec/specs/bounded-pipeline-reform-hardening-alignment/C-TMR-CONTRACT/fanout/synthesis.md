# C-TMR-CONTRACT — synthesis (Phase S, v6 probe)

Synthesizer: claude conductor (Fable 5.1), a different vendor from both candidates. Inputs: both candidate branches, the E matrix (`observation-matrix.json`), both full-suite runs, the bound A/B suite (sha 6ea0aa5f…). No mechanical scoring participated (S.1).

## Candidates

| seat | card | commit | bound suite | full suite |
|---|---|---|---|---|
| codex/gpt-6-astra @xhigh | 21559 | 7a29cec | 6/6 | 1032 passed, 2 skipped, no new failures |
| antigravity/gemini-3.8-flash-high (print-only, diff applied by conductor) | 21560 | see card (amended to drop swept-in build output) | 5/6 | 1032 passed, 2 skipped, no new failures |

## Convergence (E.2)

Both seats, from the same prompt, arrived at the same shape: strict nested pydantic models for the binding, contract refs, terminal oracle, and fixture provenance; `target_binding: TargetProofBinding | None = None` on the record; a derived `target_binding_status` that is accepted on input and rejected on disagreement; concrete-maturity completeness enforced in a model validator naming the missing field; `TargetObservation` on `CodeRunEvidence` with typed `pid`; `target_binding` added to `OBLIGATION_IDENTITY_FIELDS` and projected as its JSON dump so observations stay outside the hash; a regenerated machine schema; a keystone patch; a contract-ownership record. Convergence on all five design points says the problem forces this shape.

## Divergence and what it bought

- **O-5 (packaging).** Antigravity's `keystone-patch.diff` has wrong hunk counts and does not apply cleanly. Cause: a print-only seat emitting a diff of a file it never wrote. The obligation is right to be strict (a keystone patch that needs `--recount` is not a shippable patch). Nothing to merge; risk R-1 recorded.
- **Typing rigor.** Codex uses `Annotated` stable-id, non-empty-string, and sha256 types with unique-item validators and a `binding_version` guard against `True`/`1.0`; antigravity uses plain `str` with patterns on the ids only. Codex's is the safer contract surface and costs nothing.
- **Concrete completeness.** Codex additionally requires every binding field to be *explicitly supplied* at `concrete` (`model_fields_set`) and `runtime_slots` non-empty when `runtime_chain_required`. Antigravity requires only non-null values. Codex's reading matches the packet schema, where all fields are `required`; it is stricter than O-2's text but not in conflict with it. Kept, and recorded here so the Phase 3 spec states it explicitly.
- **Status derivation.** Codex derives in a `before` validator over the raw payload; antigravity in an `after` validator via `object.__setattr__`. Equivalent behavior; codex's avoids the private-attr write.

## Decision

Codex candidate 7a29cec is selected as the canonical implementation with **zero code changes** (S.2: obviously and completely right against the bound suite and the full suite). The synthesized *design record* above is the artifact the Phase 3 spec draft consumes; the antigravity divergence contributed one risk discovery and no code.

## F-gate (F.2/F.3)

`BASELINE(7a29cec)` — hashes match the E matrix; allocation coverage of this leaf's six obligations 100%; the single E failure (antigravity O-5) is dispositioned `REBASE` for that candidate (not carried); open actions: R-1 and R-2 owned by the conductor, dated 2026-09-15, routed to post-finalize W-tasks; reviewer independence: winner authored by codex, judged and synthesized by claude, locally challenged by antigravity; this record is the decision on disk.

## Custody

Branches `adv-spec/c-tmr-contract-cand-codex` and `adv-spec/c-tmr-contract-cand-agy` stay `preserved` until the leaf is promoted and the barrier freezes the closure manifest; worktrees are disposable after that. Rows updated in `../custody-ledger.jsonl` at promotion.
