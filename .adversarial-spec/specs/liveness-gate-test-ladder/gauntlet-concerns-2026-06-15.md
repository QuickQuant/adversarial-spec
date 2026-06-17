# Gauntlet Concern Synthesis — Liveness Gate + Test Ladder

> Session: adv-spec-202606151042-liveness-gate-test-ladder | Card 5715
> Source: 507 raw concerns (evaluations-089eb93d.json) | 7 static personas × codex/gpt-5.5 + gemini-3.1-pro
> Synthesis: ONE Opus pass over ALL 507 (verdicts advisory, not filter). Deduped by theme → 32 unique.
> Spec under attack: spec-draft-v3.md (F′ liveness gate, TMR schema, maturity ladder, MOCK falsification,
> provenance journal, version fence, 5-guardrail subagent orchestration).

Raw verdict distribution (pipeline, advisory): 466 accepted / 16 ack / 24 dismissed / 1 deferred.
Per-adversary volume: PEDA 210, FLOW 86, AUDT 76, BURN 37, MINI 36, ASSH 32, ARCH 30.

Claude is final evaluator. Verdicts below are Claude's, after dedup. "×N adv" = independent adversaries raising it.

---

## CORRECTNESS BUGS (spec contradicts itself — cheap, mandatory fixes)

**CB-1 — F′ maturity threshold self-contradiction.** §2.1 step 3 says debate→gauntlet requires every US
spine at `≥acceptance`; §4.4, §6, TC-8.2 say `nl | acceptance | concrete` passes. One blocks normal debate
output, the other allows it. **Accept.** ×7 adv (PEDA-4104423b, FLOW-5df23c6d, AUDT-96c7a568, BURN-02a2f2cb,
ASSH-ea241303, ARCH-44d5fa93, gemini). Fix: single phase→maturity matrix; pick one threshold and align §2.1.

**CB-2 — MOCK rule wording inverted in §0.2.** Goal says "force every MOCK to name the live/induced technique
or be promoted," but §4.3/INV-007 say a *justified* MOCK has `live_or_induced:null` and naming a technique means
*promote*. The goal text encodes the old wrong rule. **Accept.** ×4 (PEDA-24275e73, FLOW-98d63272, AUDT-7fd968ca,
ASSH-248a32f8). Fix: rewrite §0.2.

**CB-3 — §11 "finding without join key → rejected" contradicts §5.1.** §5.1 says only TMR-changing findings
need `target.{user_story,test_id}`; spec/contract findings use `spec_section`/`contract`. §11 regresses to a
blanket rule that would silently drop valid CONS/SCOPE/CANON findings. **Accept.** ×4 (FLOW-375a6338,
AUDT-3bf0795d, ASSH-e594e190, gemini FLOW-af932772). Fix: align §11 to scoped join-key rule.

**CB-4 — TMR field list drift inside the spec.** §4.2 omits `title` and `source_spec`; TC-1.3/TC-8.0 require
them as keystone fields. A parser following §4.2 rejects the official exemplar (or violates INV-004 by accepting
extras). **Accept.** ×4 (PEDA-071fc492, FLOW-f071201c, AUDT-eca39b7b, ARCH-9ff95a6d). Fix: one canonical field
list, referenced by §4.2.

**CB-5 — Vacuous auto-promotion via `all([])`.** §4.4 promotes `nl→acceptance` when accessors "all resolve."
`accessors: []` (as in TC-8.0 exemplar) makes `all([])` → True; an empty/unimplemented test climbs the ladder.
**Accept.** ×1 but sharp (PEDA-1847667e). Fix: require ≥1 accessor for promotion.

**CB-6 — Self-consistency: the draft would fail its own gate.** Spec §13 claims "all 15 US have a spine, F′
would pass," but tests-pseudo carries `TMR:` blocks only for TC-8.0 — F′ parses `TMR.spine:true`, not headings.
The dogfood fixture fails F′. **Accept.** ×4 (PEDA-9e4d60f0, AUDT-8ae53152, ASSH-be6e62c9, FLOW-fbbaa30e).
Fix: either generate full TMR blocks for the ladder or restate the claim honestly.

**CB-7 — Getting Started teaches the wrong input.** §2 step 2 tells the operator to author `[spine]` tags;
§4.2/§6 make `[spine]` display-only and parse `TMR.spine:true`. Following the bootstrap literally produces no
parseable spine. **Accept.** ×3 (PEDA-b5a94f4a, FLOW-8642ff9c, ARCH-af679127). Fix: bootstrap must show the TMR block.

---

## RACE CONDITIONS

**RC-1 — Append-only journal concurrency asserted, not designed.** §7 claims append-only JSONL gives "safe
concurrent multi-agent writes." False without atomic-append/locking/idempotency. Worse: §7.2 has *two repos*
(skill + Fizzy) appending `node` records to the same `registry.journal.jsonl` → byte interleaving / corruption.
**Accept.** ×8 (PEDA-d4f96cab, FLOW-9ecf802e/da48a2fa, AUDT-9653de51, BURN-712d60c4, ASSH-9bcf58b0,
ARCH-e658181f/e3084b0a, MINI-aba5d567). Fix: define `ProvenanceJournalWriter` — locked atomic append, record IDs,
idempotency key, `expected_from` optimistic check; OR make Fizzy the single serializing writer via MCP.

**RC-2 — Conflict state is unpersisted → lost on crash → silent bypass.** §5.1 requires conflict disposition
"before any journaled transition," but the journal stores only *accepted* changes. Crash/timeout/laptop-close →
restart reads no conflict, TMR still MOCK, proceeds clean. Fail-closed mechanism silently fails open. **Accept.**
×2 sharp (ARCH-482d7190, gemini PEDA-73894823). Fix: persist pending dispositions to a discrete state file;
main loop refuses to advance if non-empty.

**RC-3 — Subagents read mutable files mid-flight → inconsistent snapshots.** Five parallel subagents "read files
themselves" while the main loop may edit `tests-pseudo.md`. CONS reads pre-edit, TCOV post-edit; aggregator merges
inconsistent snapshots → non-reproducible findings, false conflicts. **Accept.** ×4 (PEDA-538004b4, FLOW-a059238a,
AUDT-f1d383c8, ARCH-b308957d). Fix: per-round input manifest with content hashes; subagents report the hash used;
aggregator rejects mixed snapshots.

---

## FAILURE MODES

**FM-1 — ORCH fail-closed weaponizes transient failures into a self-DoS.** §5.1 launches 5 parallel LLM subagents;
any timeout/crash/invalid-JSON → blocking ORCH. Concurrent 429s / jitter routinely kill 1–2 → deterministic
pipeline gridlock during peak hours. No backoff/retry/circuit-breaker. **Accept.** ×7 (PEDA-8e104866,
FLOW-61a1fc42, AUDT-5f665960, BURN-7b8586db/479076e3, MINI-1ae60114, gemini PEDA-354e073c). Fix: retry-with-backoff
budget + distinguish transient transport failure from real guardrail failure before emitting ORCH.

**FM-2 — Orchestrator-root failure reads as green.** Leaf subagent death is fail-closed, but if the *dispatch
loop itself* dies (token exhaustion, fan-out crash) you get 0 findings = pass. **Accept.** ×1 sharp (ASSH-b7700762).
Fix: require explicit "N subagents returned" accounting; missing returns = ORCH, not green.

**FM-3 — F′ YAML parse failure has no defined policy.** `yaml.safe_load` on LLM-authored blocks throws on a
trailing comma / unescaped quote. Crash → tool broken; fail-closed → "0 spines, exit 2" masks a YAML syntax error
as "uncovered US," trapping the operator. **Accept.** ×5 (PEDA-c228ba30, FLOW-eb32c972, BURN-18b86e64/41059345,
AUDT-f4ade9cb). Fix: distinct `schema_error` exit + named YAML-location error; never coerce parse failure to "uncovered."

**FM-4 — "Delete any copy" auto-destroys legitimate artifacts.** INV-008 "if a copy appears, delete it" would
nuke test fixtures, generated docs, archived tests containing the field table. **Accept.** ×4 (PEDA-74e8273b,
FLOW-6c2aaead, ARCH-d404bd09/b87bf8eb). Fix: lint/fail-first, never auto-delete; allowlist derived artifacts with
source-hash headers.

**FM-5 — Diff-only context drops findings.** Subagents key findings to `test_id`/`user_story`, but those sit
outside the diff hunk; subagent omits the join key → finding rejected (CB-3 rule). **Accept.** ×2 (PEDA-1d18fd2e,
ARCH-1428c551). Fix: pass a structured TMR semantic-delta (`{test_id, field, old, new}`), not raw text diff.

---

## SECURITY (trust model — the spec's "non-bypassable" claim)

**SEC-1 — F′ "primary enforcement" is an honor-system, not a mechanical gate.** §6 puts the PRIMARY check
"immediately before the Fizzy gauntlet-entry transition," but this session dispatches via Fizzy *MCP* tools. A
local Python pre-check has no proxy authority over an out-of-process MCP call — it runs only if the LLM *chooses*
to run it first. An agent can call `pipeline_advance` directly. INV-003's "no dispatch path bypasses all layers"
is structurally false until a Fizzy-side state gate exists (which is out of scope here). **Accept — existential.**
×6 (FLOW-aa8fd5ff/3ff1ad25, AUDT-d4a61bf7/a182dd93, BURN-a6e6b2cb, ASSH-3c5294b2, ARCH-5cb476d4). Fix: name one
mandatory skill-owned transition function `advance_to_gauntlet_with_prechecks(...)`, forbid raw transition calls
in phase docs, AND state plainly that true non-bypassability needs the Fizzy-side backstop (coordinated spec).

**SEC-2 — Version fence enables a trivial downgrade attack.** Gate keys on `liveness_contract_version ≥ tmr.v1`,
but §12.4 admits marker storage/read is undesigned. Delete the key from `session-state.json` → session reverts to
legacy rules → F′ sleeps → MOCK-only critical seam passes, silently. **Accept.** ×7 (PEDA-5463f335, FLOW-30684c03,
AUDT-3ba1edb9, BURN-e5e243fd/8132fc6b, ASSH-a980a3a9/31dfdf80, ARCH-59ddedbc). Fix: single `ContractVersionResolver`
with defined read order + failure behavior; missing marker on a *new* session is a named setup error, not pre-fence.

**SEC-3 — Override ≥50-char check is mechanically gameable.** 50 spaces / zero-width Unicode / filler prose pass.
"Non-bypassable" gate bypassed with zero recorded justification. **Accept.** ×3 (PEDA-9722039c, AUDT-dd839a45,
gemini PEDA-09f61b4e). Fix: structured override record (non-whitespace floor + actor/affected-US/risk-acceptance).

**SEC-4 — run_evidence is trivially forged.** Local CLI trusts self-reported `{result:pass, env:dev}`. A
`@patch`/`pytest-mock` *inside* the REAL-DATA test makes it pass while crossing no network boundary; the runner
scrapes exit 0 and records "live." No AST/runtime introspection. The exact liveness hole this spec exists to close
remains open at Phase-8. **Accept.** ×4 (AUDT-1216a2b8, BURN-66939f51, gemini, ARCH-d0d085bf). Fix: typed execution
receipt (command/cwd/repo/commit/artifact_sha256/runner/technique-active evidence); acknowledge the residual
local-admin trust limit explicitly.

**SEC-5 — "local-only / no untrusted input / security N/A" is false.** The tool parses LLM/human-authored YAML
(= untrusted input). Unsafe YAML loaders + anchors/aliases → parser blowup / object construction (local DoS). Live
run artifacts may capture credentials/account IDs with no redaction policy before commit. **Accept.** ×4
(PEDA-7bf8648f/23188407, AUDT-6f77355a/7bae1b98). Fix: mandate `yaml.safe_load`, ban anchors, define artifact
redaction + commit policy; restate the threat model.

---

## SCALABILITY

**SCA-1 — TCOV "ingest ALL test files for owner paths" is unbounded.** No owner-path resolution, glob, ignore
rules, language patterns (`*.test.*` misses `test_*.py`), or token budget. Big repos → context exhaustion → silent
truncation → invalid JSON → ORCH (couples to FM-1). **Accept.** ×7 (PEDA-a28a0034/136eba60, FLOW-90dadc4d,
AUDT-8f29e751, BURN-a32fbf69, ASSH-415cc279, ARCH-b2aa47f3). Fix: explicit test-input collector + manifest with
include/exclude + TMR binding; reason over the manifest, not raw FS discovery.

**SCA-2 — Journal memory growth / no retention.** Per-US replay (TC-9.0) loads the whole growing JSONL into
memory; long sessions → slowdowns / OOM (couples to RC-1). **Accept.** ×2 (PEDA-055db2bb, gemini PEDA-b5103a5d).
Fix: retention/rotation or indexed store (MINI-3577abbc suggests SQLite immutable rows).

---

## DESIGN DEBT

**DD-1 — YAML-in-Markdown is a split-brain, fragile source of truth.** `TMR:` YAML embedded in LLM-authored
`tests-pseudo.md` is simultaneously human prose and machine schema. LLMs drift indentation, wrap in backticks,
write `spine:"true"`/`True`/`yes`, duplicate keys, allow multiple `TMR:` blocks per header (merge-conflict
last/first-writer ambiguity). Also: §3 calls tests-pseudo a "feeder/view, never system of record," yet §4.2/§6
make its embedded YAML the authoritative gate input — a direct source-of-truth contradiction. **Accept — top
structural.** ×7 (PEDA-c3d1dda9/7b5185a4, FLOW-eb32c972, AUDT-f4ade9cb, BURN-41059345, MINI-c2c81441/70c20be1,
ASSH-a4025573, ARCH-1e6f9941/3ca03ad2). Fix options: (a) external structured `tmr-registry.json` + prose stays
prose, or (b) one shared `TmrParser` normalizing to a canonical record validated before any gate trusts it.

**DD-2 — Critical-seam classifier paradox.** INV-009: consumers read only normalized `critical_seam`, never
re-derive. §3.3: if explicit ≠ architecture-derived, "fail closed + emit finding." But *detecting* disagreement
requires a consumer to re-derive from `architecture_link` — which INV-009 forbids. No named single-writer
classifier exists. **Accept.** ×6 (FLOW-1f93f547/ce639a2a, AUDT-1b5cb7ef/b011c5c9, ASSH-2a020c3a, ARCH-aca22fd7,
MINI-8e66a7da). Fix: add one `CriticalityClassifier` (sole writer of `critical_seam`+`criticality_source`,
runs before guardrails); consumers reject unclassified records.

**DD-3 — Strict MOCK falsification is bypassable prose.** §4.3 accepts MOCK when "no technique exists" against a
*hardcoded* enum. (a) Prose denial with no citation institutionalizes convenience-mocking. (b) Enum incomplete →
"no technique" = "no *listed* technique"; app-level fault injection / clock-stub / cgroups / chmod 000 force most
"impossible" cases. (c) `natural-wait` baked into VALID_LIVENESS_TECHNIQUES is itself a loophole. (d) scale/cost/
time excuses ("2^31 items", "exhaust rate limit") rubber-stamped by LLM. (e) `tc-netem` needs NET_ADMIN — may be
un-runnable. **Accept.** ×6 (PEDA-c7533b84, AUDT-a08fb02c/edf6190c, BURN-c798f00d/a2278772, ASSH-094863e9/cce8ab32,
gemini PEDA-eeaea8e4). Fix: require a citation/technical-constraint for impossibility; reject scale/cost/time
excuses; reconsider `natural-wait`; promote via state-injection/clock-stub.

**DD-4 — Phase-8 "writes a real executable test" is a phantom producer.** TC-11.0 wants it pytested as code, but
the blast zone restricts Phase 8 to markdown phase-docs — no Python script defined. It also crosses into arbitrary
target repos while the concept-accessor façade is out of scope (NG-2), and there's no negative-oracle requirement
(green can be smoke-only). **Accept.** ×5 (FLOW-85827b3a, BURN-7675b2ce, ASSH-8daf98ad, ARCH-a801c621,
PEDA-e44743fc). Fix: split into `promotion_request` (skill emits TMR-id/repo/accessors/command/expected-evidence)
vs executable realization (owner repo/Fizzy); require negative oracle; make accessor binding a blocking dependency,
not an out-of-scope note.

**DD-5 — Markdown canonical schema can't do field-for-field; "referenced never copied" self-violated.** §3 names a
Markdown file as the single contract, but Markdown can't enforce unknown-field rejection / round-trip; meanwhile
§3.1 copies the enum tables *into this spec*, the exact drift vector INV-008 forbids. And fizzy's validator is
*assumed* strict — popular Python validators default to silently ignoring extras (Pydantic `extra='ignore'`).
**Accept.** ×5 (MINI-54658763, ASSH-f97db1de/ddff953c, ARCH-2596a2de, AUDT-7c8902a7). Fix: machine-readable schema
(JSON Schema/Pydantic `extra='forbid'`) as source of truth; spec tables marked non-normative snapshots with a hash;
verify fizzy actually rejects unknown fields (send a bad payload).

**DD-6 — Exactly-one-spine-per-US breaks cross-cutting journeys.** Scalar `user_story` + "exactly one spine"
can't represent a happy path spanning US-A+US-B or a US with multiple role/platform journeys → authors duplicate
tests for false coverage. **Accept.** ×4 (PEDA-6af70334/bd7c851e, BURN-7c724069, MINI-af56783b). Fix: one canonical
spine *designation* + multiple linked concrete tests; define duplicate-concept vs duplicate-coverage.

**DD-7 — Authoring lint / F′ / TRACE / TCOV duplicate the spine-coverage rule.** Four mechanisms enforce
"one happy-path spine per US" with different wording/bypass behavior → duplicated logic, inconsistent remediation,
copy-the-easiest-check drift. **Accept.** ×2 (ASSH-8daf98ad, ARCH-2596a2de). Fix: one `SpineCoverageChecker`
consumed by all; assign each mechanism a crisp role.

**DD-8 — No deletion/tombstone/rename model.** Append-only journal tracks field changes but not delete/supersede/
split/merge/rename; an identity-tuple rename (`TC-0`→`TC-8.0`, US renumber) fragments lineage; stale TMRs keep
satisfying F′. **Accept.** ×3 (PEDA-dc1077fa/7cfd09d3, FLOW-4a7910bd). Fix: tombstone records + stable identity.

**DD-9 — Override audit split with no durable join.** F′ overrides live in `decisions.log`; field changes in the
journal; no stable `decision_id` schema to join "gate bypassed" ↔ "field corrected later." **Accept.** ×4
(PEDA-3d53c7fd, BURN-e188dd88/be8f67da, ASSH-f061cae0, ARCH-3fc90d03). Fix: structured `decisions.log` (JSONL with
`decision_id`); journal driver refs cite it.

---

## UNDERSPECIFICATION

**US-1 — Schema-first handshake / cross-repo rollout ordering undecided.** §3.2/§12.7 leave "which repo lands
constants first" open, while §4–§9 assume validators exist. Skill-first → fizzy rejects new fields; fizzy-first →
skill can't emit them. **Accept.** ×6 (PEDA-100726e0, FLOW-a51b9e4d, AUDT-32d9f2ed, BURN-e337fa6b, ASSH-955808a8,
ARCH-695da067). Fix: negotiated capability handshake on `tmr_schema_version`+hash before post-fence behavior enables.

**US-2 — Exit-code / error taxonomy undefined.** `exit 2` overloaded (missing spine, duplicate, setup, YAML); no
machine-readable codes; setup-error vs policy-violation vs ORCH undistinguished; CLI-only (MCP returns structured
errors, not process exits). **Accept.** ×4 (PEDA-a96e0e44/bf434975, FLOW-0c1d1619, ARCH-b6553472). Fix: shared
`GateResult` model {pass, warn, block, setup_error, schema_error, orch_error} + exit-code map + override eligibility.

**US-3 — `acceptance` maturity depends on out-of-scope concept-accessor façade.** §4.4 defines `acceptance` as
executable against the façade, but NG-2 excludes it → tests stuck at `nl` or "acceptance" is a label with no
executable meaning. **Accept.** ×3 (PEDA-af261c1b, FLOW-d505fc16, AUDT-ca6de25f). Fix: define what `acceptance`
verifies without the façade, or make the façade a declared dependency.

**US-4 — Run_evidence shape under-defined for non-code tiers & debugging.** `{result,env,commit,artifact}` (and
sometimes `ts`) can't capture LLM/system-validation evidence (transcript/model/prompt-hash/corpus-id) and lacks
command/exit/duration/runner for reproducing a pass or diagnosing a fail. `env:dev` may not be "live" for external
seams. **Accept.** ×5 (PEDA-c9cd7045, FLOW-7a40cafc, AUDT-65c9aae2, BURN-e6d39df5, ARCH-d0d085bf). Fix: tier-aware
typed receipt; env-trust matrix by criticality.

**US-5 — Golden-case corpus is load-bearing but undefined.** §12.6 leaves corpus location/size open, while
TC-3.1/6.0/7.1 depend on it → LLM-judgment tests not reproducible/versioned. **Accept.** ×4 (PEDA-e3872e9c,
FLOW-7a40cafc, AUDT-13f2604d, ASSH-67ccb762, ARCH-fe4ce392). Fix: `golden_cases/manifest.json` schema (stable IDs,
expected findings, negatives, model settings, threshold, hashes) before calling judgment gates complete.

**US-6 — Conflict detection too narrow + no deterministic resolution in a headless loop.** Detects only identical
`required_action` on same `target`+field; misses cross-field semantic conflicts (promote vs delete; critical_seam
vs altitude). And "human disposition" in a headless CLI has no tie-breaker → re-trigger loop → permanent deadlock.
**Accept.** ×5 (PEDA-f694f619, FLOW-d936d77d, AUDT-1397ac15, BURN-ccaf7a28, ASSH-cb92a5ff). Fix: typed transition
model `{subject,field,from,to,action}`; conflict over transitions; deterministic force-accept-with-reason path.

**US-7 — YAML coercion / null / boolean / duplicate-key handling undefined.** `null` vs `~` vs `"null"` vs `Null`
can bypass `criticality_unknown` fail-closed; `spine:"true"`/`yes`/`1` ambiguous; duplicate keys & anchors
library-dependent; `REAL-DATA + PROPERTY` (spaces+plus) un-quoted splits. **Accept.** ×5 (PEDA-c3d1dda9/702cfe4f,
FLOW-650b067a, gemini PEDA-b144f331, AUDT-f4be9ec5). Fix: strict typed coercion rules + reject ambiguous scalars.

**US-8 — Version-string comparison undefined.** `liveness_contract_version ≥ tmr.v1` with no comparator: `tmr.v10`
vs `tmr.v2`, prereleases, null. **Accept.** ×1 (PEDA-dfa0366b). Fix: semantic comparator.

---

## ACKNOWLEDGE (valid, but out-of-scope / known tradeoff / deliberate scope)

- **ACK-1 — Fizzy-side enforcement is the real terminal gate, but NG-1 excludes it.** The "three-layer defense"
  is at best 1–2 layers until the coordinated Fizzy spec lands. Real, and *deliberately* out of scope — but SEC-1
  means the spec must stop *claiming* non-bypassability it can't deliver alone. ×5 (PEDA-2674672a, FLOW-02b108e0,
  BURN-8bdb72a9, AUDT-0bca5fb4, ASSH-a45d0ad0). Credit BURN/ASSH.
- **ACK-2 — Prompt/doc behavior is irreducibly probabilistic.** system-validation live runs vary by model/context.
  Inherent; mitigate with deterministic post-run lints over fixed fixtures, don't pretend it's deterministic.
  ×3 (PEDA-7e1eb298/ed08949f, AUDT-9a174b01). Credit PEDA.
- **ACK-3 — MVP-scoping (the minimalist thesis).** "F′ + Phase-8 run-evidence close is the incident-prevention
  MVP; journal/5-subagent-orchestration/altitude-telemetry/SQLite-vs-JSONL are observability ambitions" is a
  legitimate critique — but the broader scope was a deliberate session choice. Surface, don't silently adopt.
  ×8 MINI cluster (MINI-ff2ea941/1ae60114/41c49622/3577abbc/…). Credit MINI.
- **ACK-4 — Cross-repo canonical file unreadable in isolated checkouts.** `Brainquarters/shared-context/...` may
  not exist for every operator/CI. Real portability concern; mitigated by generated checked-in constants + hash.
  ×3 (PEDA-819f0474/678260d0, FLOW-941247f4).

---

## DISMISS (not valid for this spec)

- **DIS-1 — 2^31 / integer-overflow manifests** (PEDA-4666f205): absurd-scale, Python ints; not a real path.
- **DIS-2 — Leap-second / DST clock boundaries** (PEDA-341b2bf8): out of this spec's domain.
- **DIS-3 — External error-code taxonomy capture** (PEDA-067c91cb): subsumed by DD-3 (MOCK falsification); not separate.
- **DIS-4 — Quadratic spine cross-reference performance** (PEDA-2ef904ae): premature; corpus is small; SCA-1 covers real scaling.
- **DIS-5 — `nl` gauntlet "defeats the purpose"** (ASSH-c673e26a, pipeline-dismissed): the maturity-aware design
  *intends* `nl` at gauntlet with the real liveness demand at Phase-8 close. Legitimate design *tension* (the hole
  moves to Phase-8, where SEC-4 then bites), but not a contradiction — folded into CB-1 (resolve the threshold) +
  SEC-4 (close the Phase-8 forgery gap). Noting rather than accepting as a standalone build item.

---

## Synthesis verdict

**32 unique concerns** from 507 raw. **27 Accept · 4 Acknowledge · 5 Dismiss** (some raw concerns fold into multiple).

The spec's *core promise* — "impossible to reach the gauntlet without a phase-appropriate live happy-path spine,
non-bypassable" — is challenged at its foundation by **SEC-1 (honor-system enforcement)**, **SEC-2 (version-fence
downgrade)**, **SEC-4 (run_evidence forgery)**, and **DD-1 (fragile YAML-in-MD source of truth)**. These four are
not nitpicks; they're whether the gate is real. They need *design decisions* (and likely one more debate round),
not just spec-text edits.

The CORRECTNESS cluster (CB-1..7) is cheap and mandatory — pure self-contradiction, fix immediately.

Recommended order: (1) fix CB-1..7 self-contradictions; (2) make the design calls on DD-1/DD-2/SEC-1/SEC-2 trust
model; (3) re-run CONS guardrail; (4) decide whether the trust-model change warrants a debate round before finalize.
