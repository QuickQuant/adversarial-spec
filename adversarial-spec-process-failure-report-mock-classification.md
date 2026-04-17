# Adversarial-Spec Process Failure Report

**Session:** Gateway Credential Unification (prediction-prime)
**Date:** 2026-04-17
**Session ID:** `adv-spec-202604150247-gateway-credential-unification`
**Phase at time of failure:** Verification (Phase 9) — surfaced by user audit of 6 accepted `Strategy: MOCK-EXTERNAL` tests
**Critical Gap Identified:** The `Strategy` classification requires a justification line for `MOCK`, but the justifications go unchecked. 5 of 6 MOCK-EXTERNAL tests in this session's `tests-pseudo.md` carried falsifiable impossibility claims that no phase gate caught.

---

## Executive Summary

The adversarial-spec phase docs already mandate a test data-strategy label on every test (`phases/02-roadmap.md:315`: *"Every test case MUST be annotated with its data strategy"*), with an explicit default of REAL-DATA and an explicit warning that *"Lazy classification is a process failure"* (line 330). The spec for gateway-credential-unification complied structurally — every test in `tests-pseudo.md` has a `Strategy:` line, and the 6 tests labeled `Strategy: MOCK-EXTERNAL` each declare a scope (e.g., *"scope: Kalshi REST response"*, *"scope: exchange cancel API response"*).

When the user audited those 6 tests, 5 of the 6 had impossibility claims that are trivially falsified by naming a real-world reproduction path against dev infrastructure + small real money:

| Test | Implicit impossibility claim | User's falsification |
|------|-----------------------------|---------------------|
| TC-M2.1b | Need >100 Kalshi positions for pagination | Fund dev account, open >100 sub-dollar positions |
| TC-M2.2b | Need 101 Polymarket positions for offset paging | Same — 101 hedged sub-dollar positions |
| TC-M2.6 | Cannot create a failing request | Submit to invalid ticker, revoke one API key, kill one exchange's WS |
| TC-M2.7 | Cannot rapid-fire to produce slow/hung work | Rapid-fire real orders, gain real telemetry on actual behavior |
| TC-M3.11 | Cannot generate external error codes | Submit malformed orders, bad credentials, past-settlement markets |
| TC-M4.5 | Exchange cannot cause a failed cancel | Cancel a nonexistent order, an already-filled order, or a malformed ID |

Only one (potential Kalshi 503 maintenance-mode behavior, if that were the claim) would survive the test. The test under scrutiny would pass on the mocked assumption and fail against the real exchange — exactly the failure mode the REAL-DATA default exists to prevent.

The consequence, observable in this session, was that `MockConnector` fixtures were also reflexively re-used in `instructionExecutor` replay tests that had no need for any mock at all — the tests only called `getConnectorStatus()`, a synchronous state read that `new KalshiConnector()` / `new PolymarketConnector()` serve correctly in the default disconnected state without any network, credentials, or `connect()` call. The mock was pure dead weight, and the natural reflex when the tests broke was "patch the mock" rather than "should this test use a mock at all?"

This is a systemic failure in the adversarial-spec process, not a developer-discipline failure.

---

## What Went Wrong

### 1. The Strategy label has no falsification mechanism

`phases/02-roadmap.md:319-336` defines the Strategy table and requires an annotation on every test. It does not require a falsifiable justification, and no downstream phase attacks whatever justification is written.

In this session's spec, each `Strategy: MOCK-EXTERNAL` line carries a `scope:` descriptor (e.g., *"scope: Kalshi REST response"*). That's a topic pointer, not an impossibility claim. Nothing in the debate rounds, gauntlet adversaries, or finalize step attempts to answer the question: *can this condition actually be forced live?*

### 2. The default is real-data, but laziness is structurally rewarded

The phase docs read *"Default to REAL-DATA. Lazy classification is a process failure."* But from an author's perspective at Phase 2, labeling a test `MOCK-EXTERNAL` is cheaper than designing a real-data test: no dev-infra setup, no credential handling, no real-money plumbing, no fill-ordering concerns. Without a falsification step, the cheaper choice is also the one that ships.

### 3. Grandfathered pre-existing fixtures bypass the process entirely

`MockConnector` (the class used in the broken `instructionExecutor` tests) was pre-existing in the test suite before this session started. It was never classified by any Phase 2 process, never attacked by any debate round, never labeled. When implementation encountered test failures driven by an interface change in `sendHeartbeat()`, the reflex was to extend the mock, not to re-examine its existence. The Strategy classification system only has teeth for newly-declared tests in `tests-pseudo.md` — it cannot reach fixtures born outside of a spec.

### 4. The misleading Phase 7 "Test Strategy" naming collision

`phases/07-execution.md` Step 4 is called "Test Strategy Assignment," but it means *test-first vs. test-after scheduling per implementation card* — a completely different concept from the Phase 2 *data-strategy* label. Any reader who searched for "Test Strategy" in phase docs without reading carefully would land in the wrong phase and form the wrong mental model about when classification is meant to happen.

---

## Root Cause

Strategy labels are written in Phase 2 as prose declarations. The adversarial process currently critiques the *spec* (is the system design correct?) but does not critique the *test-design defenses* (are these classifications defensible?). A claim labeled `MOCK` goes unchallenged as long as it looks plausible in isolation. The 6 accepted MOCK-EXTERNAL tests in this session are not aberrant — they are exactly what the current process produces by default.

---

## Proposed Fix (design only, pending user approval)

### A. Phase 2 schema addition

Require a `why_impossible_to_reproduce_live:` field on every test with `Strategy: MOCK*`. The value must be a specific technical condition that cannot be forced with dev infrastructure + small real money. Examples:

- **Valid:** *"Kalshi maintenance-mode 503 (controlled outage only; dev account has no mechanism to induce)"*
- **Valid:** *"Network partition between gateway host and exchange (no dev hook to simulate without disabling host networking)"*
- **Invalid:** *">100 positions required"* (fund dev, open >100 sub-dollar positions)
- **Invalid:** *"rate-limit behavior under burst"* (rapid-fire real orders, gain real telemetry)
- **Invalid:** *"error-code generation"* (malformed orders, invalid tickers, bad credentials)

Empty / hand-wavy / trivially falsifiable → plan-gen rejects.

### B. Phase 3 debate directive

Add one sentence to the debate prompt template — no new adversary role:

> *"For any test with `Strategy: MOCK*`, challenge the `why_impossible_to_reproduce_live` claim. If you can name one plausible live reproduction path against dev infrastructure or small real money, report it as a correction."*

Both debaters see it. Zero extra adversary launches.

### C. Phase 5 gauntlet tagging

Extend the per-adversary prompts for **PEDA** (pedantic_nitpicker — data-level correctness), **BURN** (burned_oncall — production pain), and **AUDT** (assumption_auditor — unverified assumptions) to include the same directive. PEDA and BURN already receive `tests-pseudo.md`; AUDT needs a one-line context addition. No new launches, no new batches.

Rejected: adding a dedicated Mock Buster adversary. Cost without benefit — field visibility plus three existing semantically-fit adversaries is sufficient. An `ASSH` (asshole_loner — design abstractions) tag was also considered and rejected — mock choice is a tactical testing concern, not a contract-level abstraction concern.

### D. Retroactive: grandfathered fixtures

The Strategy classification can only be applied to tests born inside an adversarial-spec session. Tests and fixtures pre-dating the process (e.g., `MockConnector` across 4 remaining test files in prediction-prime) require a one-time audit: *"for each `class Mock*` / `vi.mock(` / `jest.mock(` in `tests/**`, what's the `why_impossible_to_reproduce_live`?"* Open follow-up card post-verification-sweep. This sits outside the adversarial-spec project per se but is the same failure mode.

### E. Naming disambiguation

Rename `phases/07-execution.md` Step 4 from "Test Strategy Assignment" to "Test Scheduling Assignment" (or "Test-First / Test-After Assignment") to eliminate the collision with Phase 2's data-strategy label.

---

## Why This Matters Beyond This One Session

The 6 falsifiable MOCK-EXTERNAL labels in this session would have each passed in CI and each failed in production the moment an exchange behaved differently from the mock author's imagination. On a system that trades real money, a mock-vs-prod divergence in a connector test is not a test hygiene problem — it is a direct financial loss with no CI signal to forewarn. The existing MOCK classification was designed to be a safety rail and instead became a fast-lane for classifications that nobody attacks.

The fix is small (a required field + three prompt additions) and targets the precise moment in the workflow where mock-first thinking is still cheap to reverse: Phase 2, before debate begins, before gauntlet runs, before implementation commits.

---

## Status

- **Discovered:** 2026-04-17, during verification phase of `adv-spec-202604150247-gateway-credential-unification`.
- **Immediate remediation in this session:** 2 pre-existing `instructionExecutor` tests switched from `MockConnector` to real `KalshiConnector` / `PolymarketConnector` in default disconnected state. Full gateway suite 72/72 pass.
- **Process changes:** not yet applied. This report exists to capture the diagnosis; edits to phase docs and adversary prompts are pending user approval.
- **Related retrospectives in prediction-prime** (same class of mock-vs-reality failure):
  - `2026-02-15-kalshi-ws-channels-missed.md` (docmaster-incomplete assumption, not mock-specific but same epistemic failure mode)
  - Memory entry `Small-sample tests hide real problems`
