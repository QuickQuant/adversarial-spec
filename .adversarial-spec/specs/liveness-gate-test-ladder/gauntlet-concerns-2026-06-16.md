# Gauntlet Concerns — spec-draft-v8 (post-convergence delta attack, 2026-06-16)

> Run on the **converged v8** (spec_hash `8695e8c1`). Two attack families:
> codex/gpt-5.5 (306 concerns) + gemini-cli/gemini-3-flash-preview (74) = **380 raw**.
> (The intended gemini-3.5-flash washed out on 503s; CLI flash backfilled the family.)
> Synthesized by Opus 4.8 as final evaluator — pipeline verdicts treated as advisory only
> (the codex eval graded 86% "accepted" at uniform "medium"; re-judged from scratch here).
> 8-category taxonomy. **Cross-model** = raised independently by both codex and gemini-flash.

## Headline
The hostile pass found **~18 genuinely NEW concrete issues the R4–R7 convergence debate missed** —
including several internal contradictions/omissions that **undercut the "design LOCKED at v8" claim**.
The rest (~15) are sharp re-statements of **known, deliberately-accepted tradeoffs** (local-admin trust
model, `nl`-passes-gauntlet, "not a slice", `also_covers` non-covering). This validates running the
gauntlet on the delta: collaborative debate converged while real contradictions remained.

Verdict tally (my judgment): **~22 Accept · ~11 Acknowledge · rest dismissed/duplicate.**

---

## CORRECTNESS BUGS

- **CB-1 (ACCEPT, cross-model, NEW, HIGH) — Tombstone/status field missing from the canonical schema.**
  §7 says tombstoned/renamed TMRs no longer satisfy F′, but §4.2's canonical field list has **no**
  `status`/`tombstoned_at`/`supersedes` field, and §6 has F′ parse `tmr-registry.json` (not the journal).
  → a stale `spine:true` row keeps covering a US after its test is deleted/superseded.
  (PARA-84968ad4, PEDA-4c075715, BURN-110b0fe1, ARCH-ab488a1c)

- **CB-2 (ACCEPT, cross-model, NEW, HIGH) — `run_evidence` has 2–3 incompatible shapes; no discriminated union.**
  §3.1 `{command,cwd,repo,commit,…}`; §8.1 tier-shaped receipts (prompt/doc, judgment); TC-8.0/keystone a
  third `{ts,result,commit,env,artifact}`. Under `extra:forbid` these cannot all validate — needs an
  explicit discriminated union. (ASSH-35aac854, PEDA-70010e3d, AUDT-192c629c, FLOW-3a95fd02)

- **CB-3 (ACCEPT, NEW, HIGH — directly continues R6-C7) — `live_or_induced` regressions the convergence just "fixed".**
  (a) The TC-8.0 exemplar still uses scalar `live_or_induced: natural-wait`, not the R6-C7 tagged union.
  (b) JSON `null` is overloaded: "no live/induced technique exists (justified MOCK)" vs a normal REAL-DATA
  happy path that simply has no fault — both encode as `null`. Needs REAL-DATA-vs-MOCK disambiguation.
  (FLOW-f5255f4b, BURN-4d2b19db, AUDT-b7f32449)

- **CB-4 (ACCEPT, cross-model, NEW) — MOCK falsification rule only covers literal `MOCK`.**
  `data_strategy` also has `MOCK-EXTERNAL`, `SYNTHETIC`, `FRONTEND`, `STATIC`; a critical seam dodges the
  rule by not calling itself `MOCK`. The §4.3 rule must cover every non-REAL strategy.
  (ASSH-7b21aaab, PEDA-582429ef, PEDA-77e53731, BURN-a576c4e2)

- **CB-5 (ACCEPT, cross-model, NEW) — env-trust matrix (`criticality × env → trusted?`) referenced but absent.**
  §8.1 makes close behavior depend on this table; no table exists. Implementers will each invent one.
  (ASSH-c68caf2f, AUDT-94333c24, FLOW-fa757377)

- **CB-6 (ACCEPT, cross-model, NEW) — Duplicate JSON keys bypass validation.**
  §4.2 says reject duplicate keys, but standard JSON loaders discard earlier duplicates before schema
  validation sees them → two `spine` values, parser-dependent. `TmrParser` needs a dup-preserving parse.
  (PARA-846addca, ASSH-5c1307e5, PEDA-2dc3d240, AUDT-49b7e9b0) — same strictness lineage as R6-C7.

- **CB-7 (ACCEPT, NEW) — `tmr_uid` generation/uniqueness/collision undefined.**
  Load-bearing for rename/tombstone lineage, but who allocates it, uniqueness scope (per-session vs global),
  collision handling, and copy-paste duplication are all unspecified; anchored in an HTML comment in prose.
  (ASSH-c425b701, PEDA-c346739f, FLOW-916cb9c1, PARA-91d91e4b, ARCH-e440775e)

- **CB-8 (ACCEPT, cross-model, NEW) — `tests-pseudo.md` still self-declares "Canonical source of truth".**
  §4.2 demotes it to generated-view-only (registry is SoR), but the file header and TC-8.0 still claim
  canonical authority → dual-source-of-truth residue. (FLOW-59b3d811, FLOW-94de1f13, ARCH-14cc104f)

---

## SECURITY

- **SEC-1 (ACCEPT, cross-model, NEW, HIGH) — Owner-repo command execution is an unsandboxed RCE/exfil surface.**
  §8.1 skill-runner executes an owner-repo-declared `command`; no sandbox, allowlist, timeout, network/secret
  isolation, or destructive-op limits. A compromised owner repo exfiltrates tokens / forges receipts / damages
  the host. (PARA-c96f7006, PARA-71791159, BURN-0c3aa9e9, PEDA-3c51905d, PEDA-0d679958, ARCH-7cbb05d0)

- **SEC-2 (ACCEPT, cross-model, NEW) — Prompt injection into the LLM compiler and guardrail subagents.**
  Untrusted prose → compiler emits `spine:true` / drops liveness constraints; malicious test/spec text →
  guardrail returns "no findings" / downgrades severity. echo-diff+human-confirm catches shape, not semantic
  deceit. (PARA-015ba2aa, PARA-55b60e67, PARA-4a259efa, BURN-52c92f1b, ARCH-a7817fb4)

- **SEC-3 (ACCEPT, cross-model, NEW) — Fault-injection techniques can DoS the host / lack safety envelope.**
  `external-kill`, `tc-netem`, `chmod 000`, `cgroups`, state-injection without PID/namespace/resource scoping,
  capability preflight, or cleanup → can kill unrelated services or corrupt host state. (PARA-07f55833,
  BURN-5a378719, BURN-e384b995, TRAF-81c779e4)

- **SEC-4 (ACCEPT — downgrade an over-claim, cross-model) — Subagent snapshot hashing is self-attestation, not proof.**
  §5.1 has each LLM subagent report hashes of files it read; it can omit, hallucinate, or read outside the
  manifest. The "pinned snapshot" is defense-in-depth, **not** the mechanical guarantee the spec implies —
  either instrument reads at the tool layer or relabel it best-effort. (PARA-1ff63f8d, ASSH-fdaedd79,
  ASSH-4ded57df, PEDA-cb1d5e45, AUDT-30a0e5fd, ARCH-a4f9fc9f)

- **SEC-5 (ACCEPT the concrete sub-points; ACKNOWLEDGE the rest) — Local trust-anchor hardening gaps.**
  The local-admin-can-edit model is explicitly accepted (SEC-4 "raises forgery bar, not crypto"). But three
  concrete NEW issues are accept-worthy: (a) **TOCTOU** between F′ pass and lane advance — artifact bytes
  aren't pinned through the transition (PARA-b62bb1bc, ARCH-fc079685); (b) **path traversal / symlink** in
  checker `--session/--roadmap-manifest/--tmr-registry` inputs — no canonical-root check (PARA-b281b0dd);
  (c) the **checker executable itself is tamperable** (Fizzy runs `uv run gauntlet-check` from a live symlink
  to skill source) (PARA-34f570fd, BURN-fd54a0cb, AUDT-8cdb56e5).

- **SEC-6 (ACKNOWLEDGE) — ≥50-char override floor is a speed-bump, not proof.** "aaaa…"/lorem passes. The
  spec already frames SEC-3 as raising effort; just don't over-claim it. (BURN-bf8558f3, ASSH-4fd3470c, PEDA-b722c070)

---

## RACE CONDITIONS

- **RC-1 (ACCEPT, cross-model, NEW) — Snapshot manifest race on a shared branch.**
  §5.1 "main loop won't edit files while subagents run" doesn't bind the *other* agents sharing the branch.
  Files change mid-round → mixed-snapshot findings, or hash-disagreement **thrash/deadlock** (RC-3 re-dispatch
  loop). Needs a git-tree/content snapshot, not an honor-system hash report. (ASSH-0c9b6409, BURN-76485e85,
  FLOW-59eabc7b, TRAF-3f516835, BURN-49af42ae)

- **RC-2 (ACCEPT, cross-model, NEW) — Only the journal got concurrency hardening; the SoR didn't.**
  §7 filelocks `registry.journal.jsonl`, but `tmr-registry.json` (the actual SoR), `decisions.log`, and
  `pending-dispositions.json` get no locking despite concurrent readers/writers. (BURN-92f6eb90,
  TRAF-5df170e4, TRAF-552f55ea)

- **RC-3 (ACCEPT, NEW) — Journal append not transactional with the registry update.**
  §7 atomic-appends the journal but doesn't define atomic "update registry + append journal" → journal entry
  without the registry change, or vice-versa. (ASSH-96e24327)

---

## FAILURE MODES

- **FM-1 (ACCEPT, cross-model, NEW, HIGH) — Non-overridable `setup_error`/`schema_error` is a DoS / strands hotfixes.**
  One malformed TMR, an over-budget collector on a big repo, or a Fizzy timestamp outage bricks the pipeline
  with no escape. Need bounded degradation (quarantine the bad record / partial-with-explicit-loss) or a
  loud break-glass, not absolute fail-closed. (PARA-25693ee0, PARA-141db508, ASSH-4754f6e0, PEDA-c853f70c,
  BURN-76c6335c, TRAF-53434d0a, TRAF-bdd4c16c)

- **FM-2 (ACCEPT, cross-model, NEW) — Fizzy outage = version-fence outage / offline DoS.**
  §8.2 fail-closes-as-post-fence when the card timestamp is unfetchable; no cache, retry budget, or degraded
  mode → can't work offline. (BURN-b2e3206b, BURN-30132a68, PEDA-92d5aa56, TRAF-b023c577)

- **FM-3 (ACCEPT, cross-model, NEW) — Orchestrator root-death has no detector.**
  `expected_returns` accounting assumes the orchestrator survives to write it; if it dies first, nothing
  flags the missing round. Needs a parent/wrapper contract. (ASSH-6fa24dad, AUDT-275e0818, ARCH-1883d6f2)

- **FM-4 (ACCEPT the deploy-choreography gap) — Activation is a non-atomic two-repo rollout.**
  Skill + Fizzy constants + checker entry point + integration test must land together; no deploy ordering,
  rollback, or mixed-version behavior is specified (the split-brain window). The activation rule (R4-1)
  acknowledges the *hole*, not the *choreography*. (BURN-6641d5c7, BURN-8e132f5d, FLOW-c05519d1)

- **FM-5 (ACCEPT residual) — LLM compile can emit schema-valid but semantically-wrong registry records.**
  Hallucinated accessor names / wrong `user_story` pass schema; human-confirm is the only backstop. Require
  the compile to cite-resolve accessor symbols (no invention). (BURN-52c92f1b, ARCH-a7817fb4, PEDA-4f70519e)

---

## OPERABILITY

- **OP-1 (ACCEPT, cross-model, NEW) — No observability for a fail-closed gate.**
  No metrics/SLO/runbook for override rate, fan-out, retries, lock waits, checker latency, or block-reason
  distribution. Operators can't see why/how-often it blocks. (BURN-4c9651ef, TRAF-463ac548)

- **OP-2 (ACCEPT, cross-model, NEW) — `gauntlet-check` is not an exposed entry point.**
  §6 specs `uv run gauntlet-check …`; `pyproject.toml` exposes only `adversarial-spec`, and Fizzy-calls-a-
  local-skill-CLI is an unstable boundary (cwd/Python-env/MCP-prod unspecified). (FLOW-dc2d9162, ASSH-aa8e5814,
  BURN-fd54a0cb, ARCH-891b5e20)

- **OP-3 (ACKNOWLEDGE — known §13 dogfood gap) — Spec declares "converged/locked" while its own F′ data path is red.**
  §13 honestly notes 14 spine tests aren't compiled into `tmr-registry.json`, so F′ wouldn't pass this draft.
  Already documented; surface it as a visible status caveat, not buried. (BURN-e74ae4ab, FLOW-a7b70f0a, ASSH-31116edf)

---

## SCALABILITY

- **SCA-1 (ACCEPT, cross-model, NEW) — Subagent fan-out / retry thundering-herd, no fleet retry budget.**
  5 subagents × retries × concurrent sessions → API bursts / 429 cascades. (TRAF-f37b4f4f, TRAF-d6424792,
  TRAF-11552f24, FLOW-91308c33, TRAF-b7bcc886)

- **SCA-2 (ACCEPT "pick one index"; ACKNOWLEDGE hot-key) — Journal index contract undecided; registry is a hot key.**
  §7 says "rotated with retention OR indexed immutable store" — undecided; idempotency-by-scan is O(N).
  Registry read by parser/F′/guardrails/compiler/TCOV/TRACE. Likely fine at current scale; flag for scale.
  (TRAF-52ebb34b, TRAF-6e2632a9, TRAF-5df170e4, TRAF-724138ca)

- **SCA-3 (ACCEPT — folds with FM-1) — `TestInputCollector` over-budget hard-fails large repos.**
  Needs sharding/paging/partial-with-loss, not absolute `setup_error`. (TRAF-30d3263a, BURN-76c6335c, TRAF-53434d0a)

---

## DESIGN DEBT

- **DD-1 (ACCEPT, NEW, HIGH — undercuts "LOCKED") — §12.1 is still open.**
  The per-guardrail finding schema + parallel-subagent orchestration (§12.1) is unresolved, yet K, conflict
  detection, journaling, and guardrail aggregation all depend on it. Either resolve §12.1 or stop calling the
  design locked. (ASSH-81c957a0, FLOW-3aad476e, ARCH-8be02406)

- **DD-2 (ACCEPT, cross-model, NEW) — `decisions.log` format conflicts with the live project contract.**
  §7/DD-9 mandates structured JSONL with `decision_id`; the actual project convention (and `debate.py`, and
  *this very session*) appends plain text. No migration/back-compat. (ASSH-b0e2aee3, FLOW-7dd16a2e, ARCH-1c975b96, AUDT-8fe7ce7e)

- **DD-3 (ACKNOWLEDGE — known R5-C4/DD-6 tradeoff) — `also_covers` non-covering forces redundant spine designations.**
  Cross-US journeys must declare a scalar `spine:true` per US, which authors will read as "duplicate the test."
  Deliberately chosen for counting determinism; revisit only if authoring pain shows up. (ASSH-461a8f06,
  ARCH-23f53955, FLOW-16ba281c, ARCH-c6852924)

- **DD-4 (ACKNOWLEDGE + flag a sequencing option) — "Not a slice" / multi-repo platform as one card.**
  Acknowledged via §1.1 + activation rule. MINI's "ship a smaller slice first" (schema + F′ checker + stricter
  MOCK rule + Phase-8 live evidence; defer journal / parallel-subagents / classifier) is a legit phasing
  suggestion worth weighing at execution. (ASSH-d2fd8a44, MINI-8f9c1bae, MINI-c482e94d)

- **DD-5 (ACKNOWLEDGE; two worth adopting) — Over-engineering / simpler-alternative suggestions.**
  Mostly known complexity choices. Two are genuinely attractive: **reuse `decisions.log` for pending
  dispositions** instead of a separate `pending-dispositions.json` (MINI-25bbbe86), and **sequential guardrails
  with structured output** instead of parallel subagents (MINI-679797a7/18ec255e) — the latter ties to the
  still-open §12.1 (DD-1). (also MINI-d568ff15 defer-journal, MINI-e8cdb54d manual-criticality)

- **DD-6 (ACKNOWLEDGE — editorial, for finalize) — Historical clutter.**
  Changelogs/superseded notes/resolved-OQs embedded throughout; a finalize pass should emit the clean final
  contract. (ASSH-e6ba21b8)

---

## UNDERSPECIFICATION

- **US-1 (ACCEPT, cross-model, NEW) — Negative-oracle contract is vague.**
  §8.1 requires a negative oracle but not what counts — it must fail for the *same boundary* the positive test
  exercises (not a trivial bad-input). (ASSH-d594b380, PEDA-f746384c, ARCH-32ce6108, FLOW-46cd5939)

- **US-2 (ACCEPT) — F′ checker contract vs the MOCK/liveness validation it implies.**
  §6 checker = "exactly one `spine:true`" (structural), but §6 prose also implies "REAL-DATA-or-justified".
  Pin exactly what the deterministic checker validates vs what's left to the LLM guardrails (§5.2). (AUDT-f21ce082, PARA-adb49be0)

- **US-3 (ACCEPT, small) — Authoritative phase source undefined** for the §4.4/§6 maturity-threshold logic. (PEDA-9432103b)

- **US-4 (ACKNOWLEDGE) — ID hygiene: Unicode/case/zero-width in `test_id`/`user_story`/`tmr_uid`/`decision_id`.**
  Hardening; lower priority than CB-7's uid allocation. (PEDA-73b3ecd1, PEDA-e8440670, PEDA-32135c94)

---

## Dismissed (representative)
- "F′ accepts `nl` → not a real liveness gate" (AUDT-fbf86229, ASSH-09515d45, BURN-55f1c155): **by design** —
  `nl` passes debate→gauntlet; live proof is deliberately deferred to Phase 8. Known, locked.
- "Provenance journal is over-engineered DB" as a flat dismissal (ASSH-e290eb3f): captured as DD-5 acknowledge.
- "`pipeline_advance` not wired / checker doesn't exist yet" (FLOW-c05519d1): that's the activation rule (R4-1),
  not a defect — folded into FM-4's deploy-choreography point.

## Cross-model signal note
Codex and gemini-flash **independently** converged on: owner-repo RCE (SEC-1), subagent-hash self-attestation
(SEC-4), fail-closed DoS (FM-1), snapshot race (RC-1), run_evidence schema fork (CB-2), MOCK-strategy escape
(CB-4), env-trust matrix absence (CB-5), and the §12.1-still-open lock contradiction (DD-1). That agreement is
the strongest signal these are real.
