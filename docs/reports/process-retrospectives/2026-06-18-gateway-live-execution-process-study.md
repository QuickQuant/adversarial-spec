# Gateway live execution process study

Date: 2026-06-18

Scope:
- `.adversarial-spec/specs/take-take-chunk-execution-state-machine`
- `.adversarial-spec/specs/gateway-workbench-live-detail`
- the post-pipeline Claude/Codex recovery work from 2026-06-14 through 2026-06-18

Purpose: identify what the process missed, where each class of bug should have been caught, and how the earlier-decomposition / V-and-V methodology should change before the next money-path spec.

## Executive Summary

The take/take execution state machine and gateway live workbench specs did a large amount of correct work. The state-machine spec built a serious safety model across 14 debate rounds; the workbench spec caught real interface defects during gauntlet and implementation review; the final recovery did get to a real hedged pair.

The severe process failure is narrower and more useful than "we forgot a happy-path test":

> We decomposed the system into components and verified many component claims, but no phase owned the executable system spine: `operator action -> Convex command -> gateway instruction -> live books -> decision -> exchange orders -> fills -> local state -> live UI -> cancel/terminal visibility`.

Because that spine was never made a first-class node with its own validation plan, every layer could be locally green while the whole thing failed in the seams. The post-pipeline recovery found bug after bug exactly at those seams: control-plane delivery, gateway book subscription, CLOB V2 order placement, IOC fill attribution, Kalshi order serialization, cancel lease stamping, terminal algo visibility, local Convex retention, live UI refresh, and book-liveness semantics.

The correct process improvement is not merely "test the happy path earlier." It is:

1. Model the system as a tree before task emission.
2. Give every system/subsystem/component node its own validation or verification plan.
3. Promote critical seam tests from pseudo/REAL-DATA intent into runnable evidence before closing implementation.
4. Debate only unsettled nodes; settled interface and component decisions should not be re-litigated round after round.
5. Treat "declared but unrun live acceptance" as failing, not as backlog.

The post-hoc plan `docs/plans/live-book-path-and-liveness-gate.md` already says the same thing in operational language. This report attaches that lesson to the actual artifacts and bug trail.

## Evidence Corpus

Primary spec artifacts:

- `.adversarial-spec/specs/take-take-chunk-execution-state-machine/spec-draft-v18.md`
- `.adversarial-spec/specs/take-take-chunk-execution-state-machine/test-matrix.md`
- `.adversarial-spec/specs/take-take-chunk-execution-state-machine/execution-plan.md`
- `.adversarial-spec/specs/take-take-chunk-execution-state-machine/fizzy-plan.json`
- `.adversarial-spec/specs/gateway-workbench-live-detail/spec-draft-v5.md`
- `.adversarial-spec/specs/gateway-workbench-live-detail/tests-spec.md`
- `.adversarial-spec/specs/gateway-workbench-live-detail/execution-plan.md`
- `.adversarial-spec/specs/gateway-workbench-live-detail/fizzy-plan.json`

Session logs:

- `.adversarial-spec/sessions/adv-spec-202605281906-take-take-chunk-execution-state-machine.journey.log`
- `.adversarial-spec/sessions/adv-spec-202605281906-take-take-chunk-execution-state-machine.decisions.log`
- `.adversarial-spec/sessions/adv-spec-gateway-workbench-live-detail.journey.log`
- `.adversarial-spec/sessions/adv-spec-gateway-workbench-live-detail.decisions.log`

Post-pipeline recovery documents:

- `docs/plans/live-book-path-and-liveness-gate.md`
- `docs/plans/gateway-workbench-live-detail-redesign.md`
- `docs/reports/2026-06-16-control-plane-depth-recovery-codex-brief.md`
- `docs/reports/2026-06-17-claude-catchup-for-codex.md`
- `docs/adr/0004-live-operator-data-from-gateway-not-convex.md`
- `.architecture/INDEX.md`
- `.architecture/primer.md`

Claude transcript scan:

- Indexed the 19 Claude project JSONLs under `~/.claude/projects/-home-jason-PycharmProjects-prediction-prime/` modified from 2026-06-14 through 2026-06-18.
- Searched and extracted recovery messages for the gateway/control-plane/live-execution terms: `TOKEN_GATEWAY_MISMATCH`, `FIRST-FILL`, `FIRST-HEDGED`, `WAITING_FOR_TICK`, `unresolved intents`, `control-plane`, `CLOB V2`, `IOC fill`, `depth unavailable`, `Kalshi books`, `runaway`, `invisible`, `audit_mirror_repair_blocked`, and related phrases.

Code/architecture context:

- The architecture re-scan at `.architecture/primer.md` explicitly describes gateway as the live execution runtime and Convex as control/history. It also flags that local live reads come from gateway endpoints, not Convex.
- Commit `8e12dac9` is the key committed recovery milestone: "Gateway live execution: CLOB V2 migration + runaway/invisible/IOC-fill fixes (first real fill)".

## What The Specs Were Trying To Build

### Take/take chunk execution state machine

The take/take spec was created on 2026-05-28 as a child spec for an execution-grade gateway-owned state machine. By v18, it had:

- 14 debate rounds.
- 90 behavior tests in `test-matrix.md`.
- 17 architecture invariants.
- 34 execution tasks.
- A two-plane architecture: broad Convex discovery/control/history and gateway-local execution.
- Gateway live-read endpoints on `:8090`.
- Command relay, lease fencing, local journal, mirror/outbox, decision loop, books, orders, fills, recovery, and UI/read model.

This was not a trivial or sloppy spec. It caught many real design hazards during debate: write-ahead-of-send, mirror-synchronous halt mode, bounded mirror-await semantics, command authority under outages, recovery by exchange facts, and more.

The key missed fact is visible in its own test matrix. Test 46 says:

> Happy-path launch into running ... `Strategy: REAL-DATA` ... valid config + trusted books against dev infra.

That test existed as a requirement. The process failure is that this REAL-DATA test never became a runnable gate with evidence before downstream implementation work was considered successful.

### Gateway workbench live detail

The workbench spec began from the UI/operator side. The plan document was honest about the hard dependency:

- The current workbench could not show the data the operator needed.
- It needed gateway-sourced per-algo books, state, decision events, fill schedule, timeline, target tranches, and cancel survivability.
- The known backend data dependency was card 5696: gateway not applying control-plane state and not subscribing leg books.

The final workbench execution plan emitted 17 tasks. It had good component-level test shape:

- `LockedAprCalculator`
- `BookFreshnessEvaluator`
- `FillCorrelator`
- gateway `/books` envelope
- decision firehose typed join payload
- accordion workbench
- per-algo detail shell
- leg ladders
- active algorithm card
- fill schedule/timeline

Implementation review caught real bugs:

- T5 hardcoded a freshness threshold instead of using the runtime constant.
- T6 initially added types but no actual send/fill event producers.
- T11 treated missing close fields as zero and could block arms.
- T15 used mock tranche/chunk shapes that did not match real chunk IDs and residual objects.

That is the process partially working. But it still did not require an end-to-end live operator flow before declaring the wave done.

## The System Spine That Should Have Been First-Class

The live money path is a system, not a collection of screens and helpers:

1. Operator arms an algo from UI or CLI.
2. Convex accepts the command and writes the command/control record.
3. Gateway heartbeat/watch/ack loop receives the instruction.
4. Gateway persists local execution state and starts the algo worker.
5. Active market subscription manager subscribes both legs.
6. Gateway market-data feeds populate trusted local books for the specific armed outcomes.
7. Decision loop evaluates target/worst/current pair cost, freshness/liveness, opening guards, chunk sizing, offset, and schedule.
8. Gateway places IOC/marketable orders through venue connectors.
9. Exchange responses/fills are captured and normalized.
10. Gateway updates local intents/outcomes/fills/execution state.
11. Mirror/report-fill/outbox paths eventually persist historical/audit state to Convex.
12. Live workbench updates without manual refresh from gateway endpoints/SSE.
13. Terminal algos remain visible enough for audit/history.
14. Cancel works while non-terminal and is honestly disabled or replaced by acknowledge when terminal.
15. Portfolio/header/fills reflect gateway-live values or explicitly-labeled historical values.

No task or phase owned this entire chain as a validation target. That is why the failure leaked through.

## Timeline

### 2026-05-28 to 2026-05-30: state-machine spec

- 2026-05-28: child spec created for take/take chunk execution state machine.
- 2026-05-29: debate rounds add crash recovery, hybrid authority, live-read model, command relay, lease, mirror, UI knob reconciliation, and Test 46 happy-path launch.
- 2026-05-29: operator locks gateway-as-live-SoT and Convex durable/control/history model.
- 2026-05-30: v18 finalized after gauntlet plus SDK verification.
- 2026-05-30: execution plan built: 34 tasks, 6 wave-0 foundation tasks plus feature tasks.

### 2026-05-31 to 2026-06-13: implementation and hidden live-path issues

Key implementation/review findings before the workbench wave:

- Several tests used inline subjects and mocks, not real production code. G2 and T-INV016 both had this class of review failure.
- A manual gateway execution test found `TOKEN_GATEWAY_MISMATCH`: heartbeat/watch/ack were all 400, instructions stayed queued, and UI still showed green.
- Node 20 global `WebSocket` was not available under the service configuration; errors were swallowed, so connectors silently lived in polling.
- A schema version bump was missed; tests passed on fresh DBs but existing DBs would skip migration.
- PM feed/book wiring and gateway live book chain were still unproven.

### 2026-06-14: workbench spec and a direct methodology admission

The workbench spec ran quickly:

- 2026-06-14 02:38Z: session created from card 5697.
- 03:53Z: debate converged after 2 rounds.
- 14:18Z: gauntlet synthesis found 6 verified spec-vs-code breaks.
- 16:49Z: 17 task cards loaded.
- 20:23Z: all 17 cards completed/unmapped after review/fixes.

The same day, the live-book path failure was described bluntly in `docs/plans/live-book-path-and-liveness-gate.md`:

- The intended acceptance tests existed on paper.
- The automated journey tests stubbed the gateway boundary.
- The real fire-and-fill attempt had been blocked and parked.
- The gateway `bookCache` happy path was only exercised by fake-socket/unit paths.

This was the point where the process should have halted around a system validation node. Instead, the wave continued into manual recovery.

### 2026-06-15 to 2026-06-16: first real fills and the bug cascade

Manual work exposed the real system:

- Runaway rejected PM orders because failed `placeOrder` returned without durable state; every tick minted a new chunk.
- The firing algo was invisible because no execution state was persisted for all-failing runs and terminal/failed states were filtered out.
- Polymarket production was on CLOB V2; the gateway connector was V1-shaped and rejected with "invalid order version."
- On-chain checks corrected multiple wrong assumptions about funder/signature type; the configured Gnosis Safe had funds and approvals.
- First PM fill landed via CLOB V2, but the gateway did not attribute it because IOC fill data arrived synchronously in the SDK response/public tape, not as a user-fill keyed by the `exec-...` clientOrderId.
- After IOC capture, a first fully hedged pair was achieved: PM YES 12u @ $0.10 and Kalshi NO 12u @ $0.88, `signedOffset=0`.
- Follow-up defects remained: duplicated PM fill rows and implausible Kalshi fee scaling.

### 2026-06-16 to 2026-06-18: operator visibility, control-plane, and live UI recovery

After the first hedged pair, the larger system still did not behave as an operator product:

- Completed/terminal algos disappeared from live and Convex surfaces.
- Cancels still did not work because cancel acks could lack lease stamps.
- The local Convex control plane was wedged by search-index bootstrap failing outside retention.
- Missing `WORKER_SKIP_DEPTH=true` in local dev workers caused full depth churn into Convex, forcing short retention and making the bootstrap wedge recur.
- Portfolio/header/live views diverged because some surfaces still read Convex or were health-gated incorrectly while gateway live data existed.
- Gateway books and workbench views suffered stale/age false alarms, wrong book-side mapping, slow/flash behavior, and manual-refresh problems.
- Newer Codex work continued to uncover unresolved-intent/schedule mismatch behavior and UI/visual mismatches.

## Bug Ledger: What Happened, Where It Should Have Been Caught

This section is deliberately repetitive. The repetition is the point: most bugs were not exotic; they were seam-contract bugs with no owning validation node.

### 1. Declared REAL-DATA tests were not promoted and run

Observed:
- The take/take `test-matrix.md` contained Test 46, a REAL-DATA happy-path launch.
- Older acceptance specs had REAL-DATA fire-and-fill journeys.
- `docs/plans/live-book-path-and-liveness-gate.md` says the intended tests existed but were not completed.

Where it should have been caught:
- Phase 7 pseudo-to-real handoff.
- Phase 8 close gate.

Missed verification:
- A declared REAL-DATA critical-seam test was treated like documentation rather than a failing gate until executed.

Correct process:
- Every REAL-DATA or fault-induced critical seam test must have an `executed_evidence` record before implementation can close.
- If it cannot run, downstream work halts or explicitly scopes itself as a shell/mock-only artifact.

### 2. Automated E2E tests faked the gateway boundary

Observed:
- `tests/e2e/live-workbench.spec.ts` route-fulfilled gateway endpoints and aborted `/events`.
- It verified rendering, not gateway behavior.

Where it should have been caught:
- TCOV/test strategy review.
- Test promotion gate.

Missed verification:
- The test strategy labeled a UI journey as live-ish while its most important boundary was canned.

Correct process:
- Split tests into "render fixture" and "real gateway journey."
- Fixture tests can pass a component card; they cannot satisfy a system or critical-seam validation.

### 3. `bookCache` was filled in tests, not production

Observed:
- The live-book plan records the root issue: tests populated the cache; production wiring did not prove that active subscriptions delivered books.
- Claude transcripts on 2026-06-14 note comments in `gateway/src/commands.ts` diagnosing that `onPriceUpdate` had only ever been called from tests.

Where it should have been caught:
- Subsystem verification for Market Data -> Gateway Book Cache.
- First live book acceptance before first trade.

Missed verification:
- No test asserted that a real armed algo caused the gateway to subscribe both legs and receive trusted books within an SLA.

Correct process:
- Add a live/fault-induced test: arm or view a monitored pair, poll `/books`, require both books fresh/trusted within a bound.
- Make active-depth subscription manager a first-class middleware node, not incidental code.

### 4. Control-plane auth failure was hidden behind green health

Observed:
- 2026-05-31 decision log: `TOKEN_GATEWAY_MISMATCH`, 29,872 errors since 2026-05-25; heartbeat/watch/ack were all 400; instructions never left queued; UI still showed green Healthy.

Where it should have been caught:
- Control-plane subsystem verification.
- Health UI validation.

Missed verification:
- Health meant "recent heartbeat-ish signal" rather than "can heartbeat, watch instructions, ack, and receive commands for this gateway identity."

Correct process:
- Define control-plane health as a compound contract: pair identity, heartbeat success, watch success, ack success, last command poll, and last error.
- UI health is not green unless the command path is usable.

### 5. Global WebSocket support failed silently

Observed:
- Gateway used global `WebSocket` under Node 20 without the service flag; constructor failed; bare catches swallowed the problem; connectors stayed in polling.

Where it should have been caught:
- Runtime smoke under the deployed service manager, not only unit tests.
- Connector subsystem verification.

Missed verification:
- Tests did not run the connector under the same Node/service environment.
- Errors that switch transport mode were not surfaced.

Correct process:
- Every connector has a startup smoke: service-managed process, expected mode `websocket`, visible error if it falls back.
- Transport downgrade must be explicit in `/health`.

### 6. Firehose types existed before firehose producers

Observed:
- Workbench T6 initially added typed fields but the gateway emitted only `kind:decision`; no send/fill events existed.
- Review forced net-new emission at `startChunk`, hedge, and `onFill`.

Where it should have been caught:
- Task implementation review did catch it.
- Earlier target architecture should have identified "producer path" as the contract, not just the event schema.

Missed verification:
- A schema test was insufficient. The event source path needed a real append-path test.

Correct process:
- For every realtime contract, require producer, transport, and consumer tests. Types alone are never done.

### 7. Fill schedule/tranche UI passed with fake shapes

Observed:
- T15 tests were green but used synthetic chunk IDs and residual shapes that did not match real gateway data.
- Review found uniform tranche sizing, dead correlation join, and `[object Object]` residual rendering.

Where it should have been caught:
- Component verification review did catch it.
- Test fixture generation should have been contract-derived.

Missed verification:
- Tests invented their own data rather than consuming recorded gateway fixtures or shared schemas.

Correct process:
- UI slot tests use captured gateway payload fixtures or generated schema fixtures.
- A test defining a fake data shape cannot verify an integration slot.

### 8. Overall expiry compared duration to epoch

Observed:
- Claude transcript 2026-06-15: `overallExpiryMs=900000` was stored as a duration, but opening guard compared `now >= overallExpiryMs`, so any nonzero expiry always blocked.

Where it should have been caught:
- Component test for opening guard boundary.
- Contract test for command field semantics: duration vs absolute deadline.

Missed verification:
- The same field crossed UI/Convex/gateway with ambiguous units.

Correct process:
- All command time fields must be named by semantics: `overallExpiryDurationMs` or `overallExpiresAtMs`.
- Add a cross-runtime schema test from Convex producer -> gateway guard.

### 9. Min-depth halt measured chunk fill, not available paired depth

Observed:
- Claude transcript 2026-06-15 first suspected `min_depth_halt`, then confirmed the spec required `visiblePairedDepthAtFloor`.
- Gateway compared a chunk-sized result against the halt threshold, so a market with ample cumulative depth could block forever.

Where it should have been caught:
- Opening guard component verification.
- APR ladder/depth-at-floor subsystem verification.

Missed verification:
- The test likely asserted a local branch, not a ladder-walk semantic with multi-level depth.

Correct process:
- Depth-at-floor gets a toy test suite with shaped ladders and expected cumulative paired depth.
- The state-machine task tree must separate "chunk sizing" from "available tradeable depth."

### 10. Requested chunk units were hardcoded or stale relative to UI config

Observed:
- Claude noted `requestedChunkUnits=10` where chunk sizing should derive from total and `chunkFraction`.

Where it should have been caught:
- UI-to-command contract reconciliation.
- Decision loop component verification.

Missed verification:
- The plan had the operator knobs, but not enough end-to-end assertion that each knob reached the decision loop and affected behavior.

Correct process:
- A command round-trip test should arm with distinctive values and assert the gateway decision uses them.

### 11. Wrong-side Kalshi book pricing

Observed:
- Live workbench showed Kalshi ladder values but the algo used the wrong side/outcome in some cases; Claude verified a fix where PM + Kalshi NO should use `noAsk`, not `yesAsk`.

Where it should have been caught:
- Market-side normalization subsystem.
- Leg ladder component tests with all four buy YES / buy NO combinations.

Missed verification:
- The two-venue/two-outcome book transform was treated as display wiring rather than a critical execution contract.

Correct process:
- Build a `LegBookView` or equivalent middleware with exhaustive tests:
  - venue
  - buy side
  - outcome
  - complement token availability
  - price/size labels

### 12. Quiet Kalshi books were marked stale

Observed:
- Kalshi books had valid snapshot/integrity and live heartbeat, but `receivedAtMs` was old because the market was quiet. UI suppressed TOB current and displayed stale/depth unavailable.

Where it should have been caught:
- Book liveness/freshness subsystem design.
- UI acceptance tests against quiet markets.

Missed verification:
- The process conflated "book content changed recently" with "connection is live and book is valid."

Correct process:
- Separate:
  - book data age
  - feed connection liveness
  - snapshot readiness
  - integrity state
- Execution/display liveness should not require a quiet book to change.

### 13. Polymarket connector was V1-shaped against CLOB V2

Observed:
- Real orders failed with `invalid order version`.
- Several intermediate hypotheses were wrong: signature type only, stale funder, missing deposit wallet.
- On-chain verification later showed the configured Gnosis Safe had pUSD and approvals; the client migration was the real blocker.

Where it should have been caught:
- Exchange adapter verification against current official SDK/API.
- First live smoke order before building observer surfaces.

Missed verification:
- Static assumptions about SDK/current behavior were allowed to stand until live order placement.

Correct process:
- For exchange adapters, run a low-notional live/sandbox order test before downstream UI execution work.
- SDK contract docs/types are necessary but not sufficient; live exchange response shape must be captured.

### 14. Rejected orders caused runaway chunks

Observed:
- `startChunk` did not persist `placing_leg_a`; `continueChunk` returned on failure without writing state; durable state still had no current chunk and next tick minted another chunk every ~100ms.

Where it should have been caught:
- Decision loop + order adapter integration test.
- Fault-induced test: exchange rejects every order.

Missed verification:
- Tests did not force `placeOrder` to throw after the decision committed to a chunk.

Correct process:
- Every exchange send failure branch must prove:
  - no new chunk minted until same intent resolved or backed off
  - failure visible in live state
  - halt after configured streak
  - no unbounded external API loop

### 15. Failing executions were invisible

Observed:
- All-failing executions never persisted a useful execution state.
- `listActiveAlgoIds` filtered terminal states; once halted to `failed_needs_attention`, the operator could not see/cancel/acknowledge it.

Where it should have been caught:
- Live operator system validation.
- UI/system acceptance for failed/intervention states.

Missed verification:
- "Active list" semantics were not separated from "operator-visible list."

Correct process:
- Define views:
  - active/non-terminal
  - needs attention
  - terminal/recent
  - historical
- Failing money-path state must remain operator-visible.

### 16. Stale local commands/states could re-arm on restart

Observed:
- Before restarting the gateway for V2, the local store had non-terminal stale algos and stale Convex `algo_start` instructions. They could have placed real orders after the connector fix.

Where it should have been caught:
- Startup/recovery subsystem verification.

Missed verification:
- "Restart after failed live attempt" was not a validation case.

Correct process:
- Gateway startup test with stale local state and stale Convex instructions:
  - terminal states do not re-arm
  - stale commands are ignored/acked/terminalized safely
  - no send occurs until operator arms a fresh command

### 17. IOC fill attribution model was wrong

Observed:
- First PM V2 fill landed on-chain, but the gateway waited for a user-fill keyed by its `exec-...` clientOrderId.
- The IOC fill was available synchronously in the SDK response/public tape with a plain UUID, so `deriveExecutionId` returned null.
- Result: `pairedFilledUnits=0`, hedge did not fire, UI showed nothing, and a small PM position was unhedged/invisible.

Where it should have been caught:
- Exchange adapter verification.
- Fill-capture subsystem test with real V2 response fixtures.

Missed verification:
- The fill model assumed async user-fill shape without verifying the exchange's actual IOC response shape.

Correct process:
- For every order method, record and test:
  - request
  - response
  - user stream event if any
  - public tape event if any
  - fill normalization path

### 18. Kalshi hedge order serialization and TIF were wrong until live

Observed:
- The first PM fill that reached hedge exposed Kalshi serialization issues: integer fields sent as strings and TIF naming needing `immediate_or_cancel`.

Where it should have been caught:
- Kalshi adapter contract test using official schema and a live/sandbox low-notional order.

Missed verification:
- Connector tests did not validate actual wire shape against the venue.

Correct process:
- Venue adapter tests must include "real API accepts request" evidence for order placement methods, even if low-notional or dry-run.

### 19. Terminal completed algos disappeared after success

Observed:
- After the first hedged pair completed, both Convex and gateway surfaces filtered terminal states. The trade had succeeded, but the operator could not see it in the live workbench.

Where it should have been caught:
- System validation after first fill.
- UI acceptance for lifecycle completion.

Missed verification:
- The success terminal state was treated as "not active" rather than "operator needs recent result."

Correct process:
- A system validation pass is not done at fill. It ends when the operator can see the result, fills, position/portfolio effect, and terminal status.

### 20. Cancel accepted by UI/Convex but not applied by gateway

Observed:
- Cancel action could appear queued/accepted but not clear.
- Diagnosis found lease stamping gaps: no `account_key`/`lease_epoch` on ack under some lease-manager paths, so Convex rejected/ignored it.

Where it should have been caught:
- Control-plane command subsystem.
- Cancel journey test.

Missed verification:
- Cancel was treated as a button/command, not a full round trip: request -> command -> gateway apply -> ack -> terminal/visible state.

Correct process:
- Cancel has its own system-seam test:
  - arm
  - cancel while waiting/running
  - gateway acks with lease stamp
  - no further sends
  - UI changes without manual refresh

### 21. Local Convex control plane wedged due depth churn and retention

Observed:
- `report-fill`/heartbeat paths returned 500.
- Root cause: local dev workers lacked `WORKER_SKIP_DEPTH=true`, wrote full depth every second, caused MVCC churn, forced short retention, and starved search-index bootstrap.

Where it should have been caught:
- Dev environment/system validation.
- Ops verification plan.

Missed verification:
- Local dev was not prod-faithful on the critical setting that controlled depth retention.

Correct process:
- Environment validation checklist:
  - dev/prod parity for worker depth mode
  - Convex backend can serve functions
  - gateway heartbeat 200
  - report-fill 2xx
  - search/vector bootstrap not wedged

### 22. Live portfolio/header values diverged by source

Observed:
- Portfolio detail could show data while header quick view showed dashes.
- ADR-0004 records the principle: live operator data must come from gateway, not Convex mirror/fallback.

Where it should have been caught:
- Architecture validation of live display sources.

Missed verification:
- The source-of-truth rule was known in take/take but not fully generalized across all live money surfaces.

Correct process:
- Add an architectural lint/review rule: a live money/algo/position number cannot use Convex unless labeled historical/reference.

### 23. Live workbench required manual refresh / SSE paths were incomplete

Observed:
- User repeatedly had to hit Refresh for newly queued/running algos to appear.
- Workbench error flashes and stale panels occurred.

Where it should have been caught:
- Live UI subsystem validation.

Missed verification:
- Component tests proved rendering, not live update lifecycle.

Correct process:
- Browser or CLI-driven lifecycle test:
  - start algo
  - row appears without refresh
  - state changes without refresh
  - events/fills update without refresh
  - terminal state remains visible

### 24. Mirror namespace could collide across gateway instances

Observed:
- 2026-06-12 mirror wedge: order mirror bundles keyed by `(exchange, seq)` collided after re-pair/instance change. Same fill mirrored at the same local seq by different instances created `ACK_MISMATCH`.

Where it should have been caught:
- Mirror/outbox subsystem architecture.
- Re-pair/restart/recovery tests.

Missed verification:
- Mirror identity was treated as per-exchange sequence rather than per gateway/account/epoch.

Correct process:
- Mirror bundle identity includes gateway/account/lease epoch or equivalent.
- Test re-pair with existing local DB and prior mirrored seq.

### 25. Filled/scheduled state mismatches and unresolved intents persisted into late recovery

Observed:
- Later Codex recovery showed `decision blocked - unresolved intents`, filled/remaining mismatches, and schedule mismatch warnings after partial/live runs.

Where it should have been caught:
- State-machine system verification after partial fills and recovery.

Missed verification:
- The process validated many state-machine branches in isolation, but not repeated live/recovery cycles with real exchange fill shapes.

Correct process:
- Add replayable flight-recorder scenarios:
  - partial PM fill then hedge
  - filled > target rounding
  - duplicated fill row
  - unresolved intent after restart
  - cancel after partial fill

## What Went Right

This should not be read as "the pipeline did nothing."

It did useful work:

- Debate produced a much better safety model than an ad hoc implementation would have produced.
- The take/take spec caught many hard edge cases before code: write-ahead-of-send, halt-mode mirror semantics, recovery, command authority, outbox ordering, and lease fencing.
- The workbench gauntlet found real spec-vs-code breaks before implementation: phantom `commandVersion`, ISO `fetchedAt`, wrong APR source, missing join data, and liveness/freshness confusion.
- Implementation review caught real bugs that tests missed: no send/fill producers, wrong tranche shapes, residual object rendering, and missing close handling.
- The live-fill gate, once enforced manually, immediately exposed the actual blockers and produced a real hedged pair.

The improvement should preserve this rigor while changing where it spends attention.

## What Failed In The Process

### Failure 1: The debated spec grew around hard problems, but did not isolate settled sections

The take/take spec went through 14 rounds because critics kept finding bugs in the latest fix. That was valuable for the mirror/lease/durability safety model. But many sections became settled and should have stopped consuming debate bandwidth.

Examples of sections that did not need repeated full-spec debate after stabilization:

- Basic leave-one semantics after operator decision.
- Gateway-as-live-SoT once locked.
- Read-only UI descriptions.
- Already validated fixed-point money rules.

The hard problems were concentrated:

- durable local journal plus exchange-authoritative recovery
- mirror/outbox ordering under outages
- command authority under Convex partitions
- book trust/freshness and live data wiring
- exchange adapter order/fill behavior

A settled/unsettled structure would have kept critics on the hard nodes.

### Failure 2: Component tests were allowed to stand in for subsystem/system evidence

Many cards had legitimate component tests. The problem is that the system needed proofs at higher levels:

- Market data feed -> book cache.
- Command queue -> gateway apply.
- Gateway order send -> exchange accepted order.
- Exchange fill -> gateway attribution.
- Gateway state -> live UI update.
- Cancel -> gateway stop and ack.

Those are not component tests. They are subsystem or system tests.

### Failure 3: "Mock justification" was too permissive

The process let "hard to make deterministic" become a reason to mock. For money-path seams, that is not enough.

For critical seams, the question should be:

- Can we make it live?
- If not, can we induce the real fault with toxiproxy, service restart, network partition, process kill, stale DB, or a low-notional exchange call?
- If not, can we use a recorded real fixture captured from the live boundary?

Only after those fail should a pure mock count, and even then it cannot satisfy system validation.

### Failure 4: UI shell work advanced despite known backend data dependency

The workbench plan explicitly said the live data was not currently produced. Building the shell in parallel can be useful, but it should have been labeled and closed as "shell only." It should not have implied the operator surface was ready.

The right gate:

- A shell task can close with fixture tests.
- The live workbench subsystem cannot close until `/algos`, `/execution-state`, `/books`, `/events`, fills, terminal states, and cancel behavior are proven against a real gateway.

### Failure 5: Review caught defects, but only within card scope

The multi-agent review model caught many local issues. It was not designed to ask: "Can the operator run one real trade and see it complete?"

That question needs to be its own card or gate, with authority to block completion.

## A Better Decomposition For This Work

If we had applied the V-model methodology earlier, the tree would have looked like this.

### System

**System: Live take/take execution and operator control**

Validation plan:
- Run a tiny live/dev-account arbitrage from arm to terminal.
- Evidence bundle includes:
  - command accepted
  - gateway instruction applied
  - both leg books live/trusted
  - decision event allowing send
  - PM order accepted
  - Kalshi hedge accepted
  - fills attributed to the algo
  - `signedOffset=0` or bounded residual explicitly shown
  - live workbench updates without manual refresh
  - terminal algo visible
  - portfolio/header source consistency
  - cancel test on a separate non-terminal run

### Subsystem 1: Control Plane

Components:
- gateway pairing/identity
- heartbeat
- watch-instructions
- ack
- command CAS
- lease stamping
- cancel delivery

Verification plan:
- CLI or integration test creates command, gateway receives and acks.
- Fault test for token mismatch.
- Cancel round trip test.
- Health UI distinguishes paired, command-connected, query-server-live, and degraded states.

### Subsystem 2: Gateway Market Data and Active Depth

Components:
- PM feed adapter
- Kalshi feed adapter
- subscription manager
- book cache
- outcome/side transform
- liveness/freshness/trust state

Verification plan:
- Real market subscription populates both books within SLA.
- Quiet market remains live if feed connection/snapshot/integrity are good.
- Sequence/control messages do not break Kalshi books.
- Viewing a market registers interest and releases it by TTL.
- Armed algo registers interest independently of UI view.

### Subsystem 3: Decision and State Machine

Components:
- opening guard
- APR/target/worst/current pair cost
- min-depth-at-floor
- chunk sizing
- leave-one
- offset/unhedge
- residual and retries
- state transitions

Verification plan:
- Toy ladder tests for each guard.
- Cross-runtime command fixture with distinctive knob values.
- Fault-induced rejected send test.
- Restart with unresolved intents.
- No state transition can make a failed send invisible.

### Subsystem 4: Exchange Order and Fill Adapters

Components:
- Polymarket CLOB V2 connector
- Kalshi order connector
- IOC/FOK/FAK methods
- request serialization
- response parsing
- fill normalization
- fee normalization

Verification plan:
- Official docs/types verification.
- Low-notional live/sandbox order or dry-run where supported.
- Recorded response fixtures.
- Fill capture proves client order, exchange order, fill key, units, price, fee, and side.

### Subsystem 5: Gateway Local Store, Mirror, and Recovery

Components:
- order intents
- order outcomes
- fills
- execution states
- terminal/recent indexes
- mirror bundles
- outbox ACK handling
- schema migrations

Verification plan:
- Previous-version DB migration test.
- Restart after failed order.
- Restart after partial fill.
- Re-pair with prior mirror seq.
- Terminal states remain queryable.
- Mirror identity cannot collide across gateway/account/epoch.

### Subsystem 6: Live Operator Workbench

Components:
- live workbench index
- per-algo detail
- leg ladders
- active algorithm card
- target tranche pills
- actual fill schedule
- execution timeline
- terminal/completed/failed panel
- filters
- cancel/acknowledge controls

Verification plan:
- Fixture render tests with recorded gateway payloads.
- Real gateway lifecycle test: no manual refresh from queued to running to terminal.
- Per-slot failure isolation.
- Terminal/failed visibility.
- Cancel remains accessible where legal and disabled/acknowledge where terminal.

### Subsystem 7: Dev/Runtime Environment

Components:
- local Convex backend
- worker containers
- gateway service
- retention/depth config
- search/vector bootstrap
- port/origin/Sec-Fetch gating

Verification plan:
- Dev parity check: local workers TOB-only when prod is TOB-only.
- `report-fill` returns 2xx.
- search/vector bootstrap healthy.
- gateway restart safe-state check.
- services run with the same Node flags/modules as tests assume.

## Where The Verification Artifacts Should Live

The methodology discussion around systems engineering suggests three durable documents. For this work, they would contain:

### `system-validation-plan.md`

Purpose: prove the operator goal works in the real environment.

For live take/take:
- one real tiny trade
- one cancel while pending/waiting
- one terminal/recent visibility check
- one portfolio/header consistency check
- one control-plane degraded display check

These are user-visible, end-to-end outcomes.

### `system-verification-plan.md`

Purpose: prove the integrated system satisfies its technical contracts without necessarily spending live money every run.

For live take/take:
- local gateway + fake exchange adapters that still use real command/state/fill paths
- recorded PM/Kalshi response fixtures
- startup/restart/recovery tests
- end-to-end SSE/live endpoint update tests
- environment health checks

### `subsystem-verification-plan.md`

Purpose: prove each subsystem contract before system assembly.

Examples:
- Control Plane: command/cancel/ack lease-stamped round trip.
- Market Data: active subscription -> trusted book.
- Exchange Adapter: CLOB V2 IOC response -> normalized fill.
- Decision: opening guard blocks/allows on shaped ladders.
- Store/Mirror: prior DB version migrates and re-pair cannot collide mirror seq.
- Workbench: recorded gateway payloads render and update correctly.

### `component-verification-procedure.md`

Purpose: targeted tests for individual functions/classes/components.

Examples:
- `LockedAprCalculator`
- `FillCorrelator`
- `opening-guard`
- `LegLadder`
- `PlaceOrder` request serializer
- `listVisibleAlgoIds`

The old process had many component procedures. It was missing the higher-level plans.

## How This Should Change Adversarial Spec

### 1. Build the node tree before debate rounds get expensive

Before broad debate, extract a system tree:

- system node
- subsystem nodes
- component nodes
- critical seams
- current implementation status
- validation/verification artifact required per node

Then debate can target unsettled nodes.

### 2. Split specs into settled and unsettled sections

The debated spec should not be a monolith. A better structure:

- `settled-decisions.md`: operator decisions and agreed contracts, only reopened by explicit contradiction.
- `unsettled-questions.md`: active debate targets.
- `node-registry.json`: system/subsystem/component nodes, owners, tests, artifacts.
- `traceability.md`: requirement -> node -> verification artifact -> task.
- `execution-plan.md`: emitted from nodes, not from prose sections alone.

For this case, the mirror/lease model needed heavy debate. The UI shell did not need to be dragged through the same rounds once its data dependency was identified.

### 3. Make "critical seam" a first-class type

A seam is critical if failure can make money move, hide money movement, or mislead the operator.

Critical seams here:

- Convex command -> gateway instruction
- active algo -> book subscription
- book -> decision eligibility
- decision -> exchange order
- exchange response -> fill attribution
- fill -> local state
- local state -> live workbench
- cancel -> gateway stop
- gateway -> Convex mirror/report-fill

Each critical seam needs at least one live, induced, or recorded-real-fixture test.

### 4. Replace "mock justification" with "live impossibility proof"

A mock-only critical seam should be rejected unless the spec names why live/fault-induced/recorded-real cannot work.

Bad justification:
- "Hard to make deterministic."

Good justification:
- "Exchange-internal matching state cannot be forced; we use a recorded real IOC response fixture plus one periodic low-notional live smoke."

### 5. Add a pseudo-to-real promotion gate

Debate-time tests are often pseudocode. That is fine. The missing gate is later:

Before implementation closes:

- every pseudo test tagged `REAL-DATA`, `FAULT-INDUCED`, or `CRITICAL-SEAM` is either:
  - implemented and run, or
  - explicitly blocked with downstream work halted, or
  - reclassified with an accepted rationale.

No "declared but not run" state should count as pass.

### 6. Add evidence bundles to task completion

For money-path work, a task/card should not only say tests passed. It should record:

- command run
- environment
- data source
- fixture/live
- observed output
- linked artifact/log
- what the evidence does not prove

The "what it does not prove" line would have prevented many false closures.

### 7. Ground tasks in implementation status

The take/take pipeline already surfaced this as a process issue. Each task should say:

- greenfield
- partial
- already built, needs verification
- shell only
- data producer missing
- blocked by live validation

The workbench shell should have been "shell only until gateway data producer passes."

## Concrete Gates To Add For The Next Money-Path Spec

### Gate A: First live book before first execution UI

Before building rich execution UI, prove:

- viewing a pair subscribes both books
- arming an algo subscribes both books
- `/books` shows both legs with correct outcome/side
- quiet but live markets remain valid

### Gate B: First low-notional fill before completion

Before marking execution implementation complete:

- place one tiny live/dev order
- capture response/fill
- attribute it to the algo
- show it in live UI

### Gate C: First hedged pair before "take/take works"

Before claiming take/take:

- both legs fill or residual policy explicitly handles the miss
- offset is flat or bounded and visible
- terminal state visible
- portfolio updates from gateway source

### Gate D: Cancel path before operator release

Before release to operator:

- cancel pending/waiting algo
- cancel in-flight or after one side fills, as applicable
- no further sends after cancel
- cancel ack has lease stamp
- UI reflects result without manual refresh

### Gate E: Restart/recovery before trust

Before trusting local gateway:

- restart with stale commands
- restart with terminal states
- restart after partial fill
- no duplicate send
- no hidden unresolved intent

### Gate F: Dev environment health

Before live tests:

- gateway control plane connected
- report-fill 2xx
- local Convex bootstrap healthy
- workers in prod-faithful depth mode
- gateway service running the same built code under same runtime constraints

## Implications For The Multi-Venue Future

The user's later multi-venue questions make this even more important. Moving from two venues to N venues multiplies seam risk:

- side/outcome transform is no longer binary PM/Kalshi
- tradeable depth depends on balances per venue
- best venue can change mid-trade
- leave-one applies per venue
- unhedge is dollar max-loss, not contracts
- fill schedule visualization needs venue colors and side-of-stripe semantics
- cancel/hedge recovery must sum child orders rather than trust a single pair counter

This should not be bolted onto the old two-leg shape. It needs a system tree early:

- `VenueBookSet`
- `TradeableDepthTransform`
- `BestPriceRouter`
- `DollarUnhedgeCalculator`
- `MultiVenueFillAggregator`
- `HedgeRecoveryAlgo`
- `MultiVenueScheduleVisual`

Each of those should get toy scenarios before the middleware API is accepted. The user's request for at least 20 tradeable-table scenarios is exactly the right instinct.

## The Core Learning

The process did not fail because agents were lazy, or because debate was useless, or because tests were absent.

It failed because the system boundary was never represented as a thing to verify.

The old process had:

- requirements
- debated spec
- target architecture
- gauntlet
- execution tasks
- component tests
- review

It needed, between architecture and task emission:

- a system/subsystem/component node tree
- a validation/verification plan per node
- critical-seam labels
- evidence requirements
- a pseudo-to-real promotion gate
- run evidence before completion

If we had done that, we probably still would have produced many tasks. But they would have organized differently. Some UI shell tasks would have been explicitly shell-only. The live book path would have been a subsystem predecessor. Exchange adapter verification would have blocked observer work. The first-fill test would not have been parked. Cancel and terminal visibility would have been system validation criteria, not late operator complaints.

That is the useful change to carry forward.

## Suggested Follow-Up Artifacts

For the next revision of the adversarial-spec pipeline, create these templates:

1. `node-registry.json`
   - node id
   - altitude: system/subsystem/component
   - owner files
   - critical seams in/out
   - implementation status
   - required verification artifact

2. `system-validation-plan.md`
   - user journeys
   - live/fault-induced evidence
   - exit criteria

3. `system-verification-plan.md`
   - integrated non-live tests
   - recorded-real fixtures
   - environment checks

4. `subsystem-verification-plan.md`
   - subsystem contracts
   - producers/consumers
   - fault cases

5. `component-verification-procedure.md`
   - precise function/component tests
   - fixtures
   - commands

6. `evidence-ledger.md`
   - every critical-seam test
   - whether it ran
   - command/artifact/log
   - result
   - gaps

The gateway live execution path is the canonical example for why these should exist.
