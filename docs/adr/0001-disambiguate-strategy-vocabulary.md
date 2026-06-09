# Disambiguate the two "Strategy" vocabularies; migrate the fizzy wire key via dual-accept

The word "Strategy" was overloaded across two unrelated concepts: the Phase 2
per-test-case **data** classification (`REAL-DATA`/`SYNTHETIC`/`MOCK`/…) and the Phase 7
per-task **test-approach** field (`test-first`/`test-after`/`spike`/`refactor`). We split
them into two canonical, non-bare terms — **Data Strategy** (`data_strategy`, already the
name of the gauntlet concern category `data_strategy_mismatch`) and **Test Strategy**
(`test_strategy`) — and ban the bare word "strategy" in prose. This also serves a
repo-wide convention: no bare single-word identifiers.

## Considered options

- **2a — rename skill-side only (chosen for now).** Every skill-owned artifact (Phase 2
  `Strategy:` label, Phase 7 `**Strategy:**` markdown bullet, all prose) becomes
  `data_strategy` / `test_strategy`. The generator keeps emitting the JSON key
  `strategy`, because that key is **fizzy's schema contract**, not this repo's variable
  (fizzy validates/stores/echoes it at `pipeline.py:164/5400/6240/2633`). ~95% of the
  consistency at zero cross-repo risk.
- **2b — also rename the fizzy wire key (deferred, fizzy-led).** Reach full purity by
  renaming the JSON key to `test_strategy` via a **dual-accept migration**: (1) fizzy
  accepts `test_strategy` *or* `strategy`, normalizes to one value at ingest, writes/echoes
  both (safe because the field is write-once at `pipeline_load`, never patched, so the two
  copies cannot drift); (2) the Phase 7 generator cuts over to emit `test_strategy`;
  (3) a later fizzy version reads only `test_strategy` and drops `strategy`.

## Consequences

- **Deploy ordering is the whole risk.** Step 2b-(2) (generator emits `test_strategy`)
  must not ship until 2b-(1) (fizzy dual-accept) is **live in the running MCP** — otherwise
  every `pipeline_load` fails with `PLAN_INVALID "invalid strategy"`, the exact #12 failure.
  The gate that catches it is Phase 7 Step 9's real `pipeline_validate_plan` against the
  live MCP — never a local check. See pipeline-seams report #11/#12.
- **The collision is skill-only.** fizzy never knew about Data Strategy, so renaming
  carries no risk of conflating the two on fizzy's side; its `strategy` key is
  unambiguously Test Strategy.
- `data_strategy` is an atomic skill-internal contract: the Phase 2 producer
  (`02-roadmap.md`) and consumers (`03-debate.md`, `adversaries.py`) that match
  `Strategy: MOCK*` must rename in lockstep.
