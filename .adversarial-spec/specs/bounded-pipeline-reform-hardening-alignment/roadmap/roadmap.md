# Roadmap: Bounded Pipeline Reform & Hardening Alignment (v2, post debate R1)

Session `adv-spec-202609150549-bounded-reform-hardening-align` · card 21537 · complexity **complex** (score 33) · root altitude **system** · doc spec/full. Source of truth: `manifest.json`; tests: `../tests-pseudo.md` (62 TCs, 17 spines). Debate R1 synthesis: `debate-r1/synthesis.md`.

## Goals
- G-1 Add proof-target identity as an orthogonal axis to REAL-DATA without weakening it.
- G-2 Surface authority divergence structurally and close cutovers as chains.
- G-3 Make temporary custody itemized and never destructive by inference.
- G-4 Land every change through the bounded pipeline itself, post-finalize, with grandfathering.

## Non-Goals
No automatic deployment or live-money action · no process supervisor · no mapcodebase replacement · no universal service-start requirement · no fixture ban for BVA · no auto-deletion of branches/worktrees/releases · no universal ledger for user-owned checkouts · no new universal Phase · no claim the gates would have prevented history.

## Operator decisions folded in
OQ-1 expected target fields join `tmr_record_hash` · OQ-2 tool-turn subagent workspaces exempt (only if the lifecycle truly ends in the turn) · OQ-3 D-2 ORACLE alignment in scope · OQ-4 Fizzy validates plan/metadata contracts only · OQ-5 pipeline_version 5 warn / 6 reject · OQ-6 codex + gemini quorum.

## Self-hosting rule (from R1)
This session finalizes using only gates that exist today. Every new gate is delivered by this session's Phase 7/8 W-tasks and exercised end-to-end by the next v6 session (US-12, US-16). No closed phase is reopened to manufacture compliance.

## Release blocker
RB-1 The version-only fence (OQ-5) conflicts with "never retroactively failed" (US-11) for cards already at pipeline_version 6 when enforcement lands. Operator approves a rollout schedule or amends the policy before enforcement is exposed.

## Milestone 0: Getting Started (Bootstrap)
US-0 documented prerequisites, one readiness command (ready/degraded/broken with named remediation), a worked non-money example. Tests: TC-0.0 (spine), TC-0.1. Depends: none.

## Milestone 1: Contract foundation — target_binding keystone step 2
US-1 target-bound obligations; US-2 progressive population; US-15 integration ownership. Success: triggered TMR compiles with binding and round-trips; legacy registry validates unchanged; expected fields in the hash (complete list owned by the spec), observed fields out; keystone-first with sha re-pin; one owner per shared contract; validate/load parity within the declared contract. Tests: TC-1.0 (spine), TC-1.1–1.4, TC-2.0 (spine), TC-2.1–2.2, TC-15.0 (spine), TC-15.1. Depends: M0.

## Milestone 2: Phase 8 observation, promotion, typed provenance, recovery
US-5 observed target; US-6 typed provenance; US-13 recovery after rejection. Success: runner-owned observation closes; harness/wrong-path/stale/owner-authored observations reject with their codes; missing evidence distinguishable from mismatch; unavailable review reported, never simulated; makeEnvelope ceilings, "no mocks" prose does not halt, BVA fixtures pay nothing. Tests: TC-5.0 (spine), TC-5.1–5.5, TC-6.0 (spine), TC-6.1–6.2, TC-13.0 (spine), TC-13.1–13.2. Depends: M1.

## Milestone 3: Authority census (D0/Phase-4 obligations) and cutover chains (Phase 7)
US-3 triggered census; US-4 cutover chains. Success: structural trigger only; declared discovery scope with independent review of completeness; census in fingerprint (rides the D0 artifact under v6); uncensused sibling and missing predecessor proof reject; role change expands into the full chain, `not_applicable(reason)` only with reviewer acceptance; strict-int schema-3 emission validated by live Fizzy; schedule postcondition; one consumer task per censused caller. Tests: TC-3.0 (spine), TC-3.1–3.3, TC-4.0 (spine), TC-4.1–4.4. Depends: M1.

## Milestone 4: Custody ledger lifecycle and interruption reconciliation
US-7 custody ledger; US-14 reconciliation after interruption. Success: row per durable pipeline-owned authority; admission by projected total (3→4 accepted, 4→5 rejected), concurrent requests never share capacity; aggregate counts close nothing; reviewer checkouts out of scope; operator exception raises the budget only; missing-row case; surviving interrupted workspaces reconciled before dependent work; interrupted runs carry no result. Tests: TC-7.0 (spine), TC-7.1–7.6, TC-14.0 (spine), TC-14.1. Depends: M0.

## Milestone 5: Prompt plane and finalize binding (Phases 3, 5, 6) — delivered here, exercised next cycle
US-8 critic/adversary prompts; US-9 ORACLE alignment. Success: seeded wrong-route test found by a real critic round (threshold per OQ-8); broker refuses cross-path answers; identity contradictions demanded; ORACLE requires an executable witness with G/M controls; unbound triggered tests and test-less concern closures fail finalize; permissive assertions caught via a declared assertion shape. Tests: TC-8.0 (spine), TC-8.1–8.2, TC-9.0 (spine), TC-9.1–9.3. Depends: M1, M2.

## Milestone 6: Golden replay, mutation proof, rollout fence
US-10 replay + mutation; US-11 rollout. Success: 15/15 incidents + 3/3 controls; every dimension mutation yields its code; 22/22 codes covered; fence keyed only on the card's pipeline_version, absent = legacy but malformed = reject; legacy registries readable and visibly unbound, waivers never discharge; unknown versioned fields survive; skill edits post-finalize as W-tasks; no new failures vs baseline. Tests: TC-10.0 (spine), TC-10.1–10.2, TC-11.0 (spine), TC-11.1–11.4. Depends: M1–M5.

## Milestone 7: Dogfood, downstream adoption, process record
US-12 dogfood; US-16 downstream adoption. Success: canonical v6 order walked with D0 adequacy on disk using existing gates; prediction-prime adopts on a v6 session exercising every delivered gate with zero burden on unaffected work; v5→v6 migration path explicit; every process failure noted with `would_have_used`; patch_state tally zero on card 21537. Tests: TC-12.0 (spine), TC-12.1–12.2, TC-16.0 (spine), TC-16.1. Depends: M6.

## Architecture impact
Verdict **new_middleware**: a shared typed reject-code catalog and a runner-owned target-observation collector, consumed by promotion, plan self-check, finalize ORACLE, and custody close; two new durable artifacts (`authority-paths.json`, `custody-ledger.jsonl`); keystone extension. Under v6 the Phase-4 obligations ride the D0 decomposition artifact. Assessed against corpus `2433efa` (HEAD `b544a00`; source trusted over docs).

## KPIs
15/15 incidents + 3/3 controls · 100% dimensions mutation-tested (denominator = spec field list) · 22/22 codes · no new failures vs baseline, skip set unchanged, known failures attributed · CTRL-002 class costs one rationale line and zero launches · recovery usability on 3 seeded rejections · 0 patch_state on card 21537 (nonzero = missed target) · released-workflow proof in the next v6 session.

## Open decisions raised by R1
OQ-7 receipt freshness window and invalidating events · OQ-8 critic criteria and threshold for the seeded wrong-route test.
