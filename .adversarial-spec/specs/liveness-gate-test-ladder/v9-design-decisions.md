# v9 Design Decisions — settling architecture before re-gauntlet

> Settled live with Jason 2026-06-16, working the post-v8-gauntlet contradiction cluster through the
> **hard-gate/soft-gate principle** ([[gate-design-hard-metadata-soft-fidelity]]):
> hard-gate validates the metadata (deterministic, fail-closed); soft-gate (LLM) validates that the
> metadata faithfully + sufficiently represents reality. These fold into spec-draft-v9. NOT yet applied.

---

## DR-1 — `run_evidence` becomes a discriminated union (fixes CB-2, part of CB-3)

**Problem:** §3.1 declared one flat receipt shape; §8.1 declared three tier shapes; TC-8.0 a fourth.
Under `extra: forbid` they cannot co-validate.

**Decision:** `run_evidence` is a discriminated union on an **explicit `tier` field, hard-gate cross-checked
against the TMR's `verification_mode`** (store it, validate it matches the mode's tier — validated
redundancy as cheap insurance). Variants:

```
{ tier: "code",                                            # automated-* / test-producer
  command, cwd, repo, commit, started_at, finished_at,
  exit, result, env, artifact_uri, artifact_sha256,
  runner, live_or_induced }                                # live_or_induced ONLY on this variant

{ tier: "system-validation",                               # live scoped skill run on a fixture
  transcript_uri, transcript_sha256, model, model_settings,
  prompt_sha256, corpus_id, run_id, result, runner, captured_at }

{ tier: "judgment",                                        # golden-case LLM eval (US-5)
  golden_manifest_id, golden_manifest_sha256, model, model_settings,
  score, threshold, per_case_results, result, runner, captured_at }
```

- **per_case_results KEPT** on the judgment variant — so a golden-eval can't pass the aggregate
  `threshold` while silently missing the one critical planted defect (PEDA-6a963eaf).
- Exempt `verification_mode`s (`artifact-sync`/`static-check`/`manual-ux`) carry **no** `run_evidence`.
  Hard rule: receipt required iff `verification_mode ∉ exempt`.
- §3.1 declares the union (the schema); §8.1 prose references it instead of repeating a flat list;
  TC-8.0 exemplar updated to the `code` variant.

**Hard gate:** receipt matches its `tier` variant exactly, required fields present, `result ∈ {pass,fail}`,
`tier` consistent with `verification_mode`. Fail-closed on mismatch.
**Soft gate (already correct in §8.1):** mock-detection lint = flag-not-block (can't mechanically prove a
test isn't secretly mocked); "named fault technique actually applied" = judgment.

## DR-2 — `live_or_induced: null` disambiguated by a hard cross-field rule (fixes CB-3b)
`null` reads as both "justified MOCK, no technique" and "plain REAL-DATA, no fault." The sibling
`data_strategy` disambiguates. Hard rule: **`data_strategy = MOCK ∧ live_or_induced = null ⇒
why_impossible_to_reproduce_live present and non-empty`.** Deterministic; ambiguity gone. Also: update the
TC-8.0 exemplar to the R6-C7 tagged form (it still uses the old scalar `live_or_induced: natural-wait`).

## DR-3 — TMR lifecycle field so F′ can exclude dead records (fixes CB-1)
**Problem:** §7 says tombstoned/renamed TMRs don't satisfy F′, but §4.2 has no lifecycle field and §6 has
F′ read the registry directly → a deleted test's `spine:true` row keeps counting.
**Decision (option a):**
- Add to §4.2 canonical fields: **`status: active | tombstoned`** (default `active`), plus
  **`supersedes: <tmr_uid> | null`** (a replacement points at what it replaces; the replaced row goes
  `tombstoned`). A rename/replace = tombstone old + new record `supersedes` it.
- Add **`tombstoned_at`** on the record (denormalized; keeps F′/queries off the journal). [recommended
  default — Jason didn't object; flag if wrong]
- **F′ hard rule:** count only `status: active` records when checking "exactly one `spine:true` per US."
- **Journal vs registry:** §7 journal records the tombstone *event* (history); the registry `status` is
  the *current state* F′ reads → F′ stays a pure registry read, no journal replay (kills PARA-84968ad4).
- **Dependency:** the `supersedes` link rides on `tmr_uid` being a reliable unique identity → DR-4 (CB-7).

## DR-4 (ADR-4) — `tmr_uid` allocation/uniqueness/identity (fixes CB-7)
- **Compiler allocates**, not the LLM: a new TMR authored with no uid → the deterministic compile step
  mints one and writes it to the registry record (authoritative) + the prose `<!-- tmr_uid -->` anchor.
- **Format: ULID** (globally unique + sortable by creation → free lineage/journal ordering).
- **Uniqueness (hard gate):** unique across the whole registry; parser rejects duplicate uids or duplicate
  prose anchors as `schema_error`. **Immutable** once allocated (a compile changing an existing uid = error).
- **Copy-paste dup = hard error, human disambiguates** — rare process/authoring slip, not normal flow;
  the backstop against silent lineage corruption. Authoring guidance: author new tests without a uid (or
  strip the anchor when copying a block); the compiler mints it. (Don't over-build rare-event handling.)
- **Two-identity model (explicit):** `tmr_uid` = immutable primary key (uniqueness + all lineage);
  `session·user_story·test_id` = mutable human locator (F′ groups coverage by `user_story`; `test_id` may
  change under a stable uid).
- Hard/soft: essentially all **hard-gate** — no soft role; pure mechanical identity.

## DR-5 — Coverage = metadata diff, not source-ingestion (fixes SCA-3, redesigns TCOV §5.2/§5.3)
- A test carries its **`user_story` link** (already a TMR field), established at **roadmap time** (when the
  US + its `nl` tests are first written) — mapping exists from the start, not reconstructed.
- **Coverage = deterministic metadata diff (hard gate):** every US has ≥1 linked `active` test of adequate
  maturity/strategy. Extends F′'s existing "exactly one spine per US."
- The **`.architecture/` causality graph validates** a claimed test→US link (test exercises module M;
  architecture associates M with the US's area) — same pattern `critical_seam` uses with `architecture_link`.
  Validate where the code→US mapping is reliable; advisory-flag where it isn't (don't gold-plate).
- **Kill `TestInputCollector` raw-source ingestion + token budget** → deletes SCA-3 and "operate blind."
- **Soft gate (LLM) shrinks** to targeted per-test **adequacy** only ("is THIS flagged test's oracle real /
  not smoke / not secretly mocking the boundary") — never "read all test source to judge global coverage."

## DR-6 — Guardrail orchestration: delete the snapshot machinery, keep parallel + typed findings (fixes DD-1; deletes SEC-4/RC-1/RC-3/FM-3/SCA-1)
- **Delete** the frozen-manifest / self-reported-hash / snapshot protocol entirely. Guardrails are
  **read-only** — they don't mutate anything, so they can't cause a race. The only thing that could change
  inputs mid-round is another agent editing the branch, which is **operational guidance, not a hard gate**:
  *don't modify the spec/tests from another context while a debate round is in flight.*
- **Parallel** dispatch (NOT sequential): the orchestrator reads inputs **once** and passes **identical
  content** to all 5 guardrails at once. Race-free (everyone gets the same bytes) AND fast
  (`max` not `sum` of guardrail times — a big perf win every round). No fan-out concern at this scale.
- **Keep** the typed finding schema (the real §12.1 substance): each guardrail returns
  `{guardrail, severity, join_key (target TMR/section/field), finding_type, description, disposition}`.
  Aggregation + conflict-detection = one deterministic pass over join_keys (hard gate). The judgment inside
  each finding is the soft gate.
- Closes §12.1. SEC-4 (self-attested hashes), RC-1 (snapshot race), RC-3 (hash-disagreement thrash),
  FM-3 (orchestrator-death accounting), SCA-1 (fan-out storm) are **deleted as non-threats**, not patched.

## DR-7 — NO security threat model; strip the security apparatus (see [[threat-model-local-dev-tool-no-security]])
Local dev tool, trusted operator + trusted own-ecosystem owner repos. The gate catches **honest mistakes**,
not a malicious actor. Per-concern disposition for everything security-flavored:

**DELETE (operator/repo-adversary → out of scope):**
- SEC-1 owner-repo command "RCE" — repos trusted; a *buggy* (not malicious) command is already caught by
  the receipt + negative-oracle ("did the right test actually run / fail correctly").
- SEC-2 prompt injection (LLM compiler + guardrails) — trusted inputs; the honest-misread residue is FM-5
  (semantic-wrong compile), handled by the soft gate (echo-diff + human confirm).
- SEC-4 self-attested hashes — already deleted in DR-6.
- SEC-5 TOCTOU / path-traversal / checker-tamper — pure operator-adversary.
- SEC-6 override floor as a *bypass-prevention* control — keep only a plain reason-string for the audit
  log (honest record); drop the "≥50 char proves intentionality / prevents bypass" framing.
- §8.1 "SEC-4/SEC-5 trust model stated honestly" prose + yaml-hardening (safe_load/anchors-rejected) +
  misc PARA (other:<detail> injection, golden-case poisoning, journal idempotency suppression,
  pending-dispositions DoS, dup-key "hide a value", secrets-as-attack) — **strip from the spec.**

**KEEP but RE-CLASSIFY (real on non-security grounds):**
- CB-6 duplicate JSON keys → **correctness** (deterministic parse), not security. Keep.
- SEC-3 fault-injection blast radius (external-kill/tc-netem/cgroups) → **operational safety** ("don't nuke
  your dev box by accident") → light operational guidance (scope to the test's process; clean up). Not a gate.
- Redact secrets before commit → **hygiene** (don't accidentally commit secrets to Fizzy), already in §8.1; keep light.
- Version fence (`created_at`) → was mislabeled SEC; it's **migration/compat** (don't retroactively fail
  in-flight sessions). Keep on compat grounds.

Net: the spec carries **zero** security machinery after v9.

## DR-8 — MOCK falsification covers all non-REAL strategies (fixes CB-4)
Hard rule keys on real-ness, not the label: **`critical_seam = true ∧ data_strategy ∉ {REAL-DATA,
REAL-DATA + PROPERTY} ⇒ why_impossible_to_reproduce_live present and non-empty`** (covers MOCK,
MOCK-EXTERNAL, SYNTHETIC, STATIC, FRONTEND). Soft gate judges whether the justification is honest.

## DR-9 — Write the env→"real pass" rule, de-securitized (fixes CB-5)
Strip "trust matrix" framing; it's a **correctness** rule (did the test hit the real boundary). Tabulate
what §8.1 only referenced: **a critical seam's `run_evidence` must be `env: live` OR carry a recorded
`live_or_induced` technique; `env: dev`/`ci` with no technique does NOT count as a real pass for a critical
seam.** Lower-criticality tiers accept `dev`/`ci`. Two rows; no longer "referenced but absent."

## DR-10 — decisions.log stays plain text (fixes DD-2)
Drop the "structured JSONL with `decision_id`" mandate — it conflicts with the live convention (and this
session). **decisions.log = plain-text human ledger (unchanged).** Structured decision/override records
(`decision_id`, join keys) live in the **provenance journal** (already JSONL). The override→journal link
(§12.10) keys off the journal record. Two artifacts, each native format; no migration.

## DR-11 — tests-pseudo header de-canonicalized (fixes CB-8)
§4.2 makes `tmr-registry.json` the SoR and tests-pseudo.md the generated view, but the file header still
says "Canonical source of truth." Update header → **"prose authoring surface + generated view; registry is
SoR."** Doc-consistency only; no mechanism. (Same dual-SoR residue FLOW flagged.)

---

## Status: DR-1..11 ALL APPLIED to spec-draft-v9.md + tests-pseudo.md (2026-06-16).
Sections touched: §3.1 (receipt union ptr), §4.2 (status/supersedes/tmr_uid/ULID), §4.3 (DR-8 MOCK + DR-2 null),
§5.1 (DR-6 parallel, snapshot deleted, de-securitized override), §5.3 (DR-5 metadata coverage), §6 (active
filter + override de-sec), §7 (DR-10 decisions.log + tombstone/status link), §8.1 (receipt union + security
stripped + env rule), §9 (TestInputCollector ref removed), §12.1/12.2 (RESOLVED by DR-6), §12 item-12 (v9
supersession note); tests-pseudo header (DR-11) + TC-8.0 exemplar (tagged live_or_induced, run_evidence:null,
tmr_uid, status). Consistency check passed (deleted machinery 0 live refs). The ~11 acknowledge tradeoffs need
no spec change (already documented as deliberate). **Next: re-converge debate round on v9; reconcile card gauntlet state.**
